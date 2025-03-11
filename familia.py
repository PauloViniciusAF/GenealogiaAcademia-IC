#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para processar currículos Lattes e gerar um JSON hierárquico com as seguintes roles:
- "pivo": é o ID informado pelo usuário. Do currículo do pivo, extrai:
     * link_lattes (http://lattes.cnpq.br/<id_pivo>)
     * Instituição_doutorado (do pivo)
     * id_pai (ID do orientador do pivo)
     * orientações: as teses (orientações concluídas) do pivo – os orientados serão classificados como role "filho"
- "pai": é o orientador do pivo. Do currículo do pai, extrai seus dados básicos e os orientados (exceto o pivo) classificados como "irmão".
- "filho": são os orientados diretamente pelo pivo.
- "irmão": são os orientados pelo pai (exceto o pivo). Para cada "irmão", o script extrai seus orientados como "sobrinho".
- "sobrinho": são os orientados pelos "irmãos".

O usuário deverá resolver manualmente o CAPTCHA sempre que solicitado.
"""

import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -------- Funções de I/O --------

def write_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Dados salvos em: {filename}")
    except Exception as e:
        print(f"Erro ao escrever o arquivo {filename}: {e}")

# -------- Selenium --------

def initialize_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    service = Service("chromedriver")  # Ajuste conforme necessário
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def open_lattes_page(driver, url):
    driver.get(url)
    print(f"Acessando: {url}")
    print("ATENÇÃO: Se aparecer um CAPTCHA, resolva-o manualmente.")
    input("Quando a página estiver carregada, pressione Enter para continuar...")

# -------- Extração de Dados do Currículo --------

def extract_cv_info(driver, seed_link, role):
    """
    Extrai informações básicas do currículo Lattes.
    Para role "pivo" ou "pai": extrai:
       - Nome
       - Instituição_doutorado (do bloco de formação)
       - id_pai (ID do orientador extraído do link)
    Para roles "filho", "irmão" ou "sobrinho": extrai:
       - Nome, link_lattes e Instituição_doutorado
    Retorna um dicionário com os dados extraídos.
    """
    info = {
        "role": role,
        "link_lattes": seed_link,
        "Instituição_doutorado": "",
        "id_pai": ""
    }
    try:
        nome_elem = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(@class, 'nome')]"))
        )
        info["Nome"] = nome_elem.text.strip()
    except Exception:
        info["Nome"] = ""

    try:
        anchor = WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.XPATH, "//a[@name='FormacaoAcademicaTitulacao']"))
        )
        container = anchor.find_element(By.XPATH, "following::div[contains(@class, 'layout-cell-12 data-cell')]")
        blocks = container.find_elements(By.CLASS_NAME, "layout-cell-pad-5")
        for block in blocks:
            text = block.text
            if "Doutorado" in text:
                parts = text.split('.')
                # Para "pivo" ou "pai", usamos Instituição_doutorado e extraímos id_pai
                info["Instituição_doutorado"] = parts[1].strip() if len(parts) >= 2 else ""
                if role in ["pivo", "pai"]:
                    try:
                        orientador_link_elem = block.find_element(By.XPATH, ".//a[contains(@href, 'lattes.cnpq.br')]")
                        link_orient = orientador_link_elem.get_attribute("href")
                        id_match = re.search(r"lattes\.cnpq\.br/(\d+)", link_orient)
                        if id_match:
                            info["id_pai"] = id_match.group(1)
                    except Exception:
                        info["id_pai"] = ""
                break
    except Exception:
        pass

    return info

def extract_cv_info_tese(driver, seed_link):
    """
    Extrai informações básicas de uma orientação (tese concluída).
    Retorna um dicionário com:
       - nome: Nome ou título da orientação,
       - link_lattes: seed_link,
       - Instituição_doutorado: extraída do bloco de formação (se disponível)
    """
    info = {
        "link_lattes": seed_link,
        "Instituição_doutorado": ""
    }
    try:
        nome_elem = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(@class, 'nome')]"))
        )
        info["nome"] = nome_elem.text.strip()
    except Exception:
        info["nome"] = ""
    try:
        anchor = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//a[@name='FormacaoAcademicaTitulacao']"))
        )
        container = anchor.find_element(By.XPATH, "following::div[contains(@class, 'data-cell')]")
        blocks = container.find_elements(By.CLASS_NAME, "layout-cell-pad-5")
        for block in blocks:
            text = block.text
            if "Doutorado" in text or "Mestrado" in text:
                parts = text.split('.')
                info["Instituição_doutorado"] = parts[1].strip() if len(parts) >= 2 else ""
                break
    except Exception:
        info["Instituição_doutorado"] = ""
    return info

def extract_orientacoes(driver, role):
    """
    Extrai as orientações (teses de doutorado concluídas) do currículo.
    Para cada orientação, acessa seu link e extrai as informações usando extract_cv_info_tese.
    A role definida será:
       - "filho" para orientados do pivo,
       - "irmão" para orientados do pai,
       - "sobrinho" para orientados dos irmãos.
    Retorna um dicionário mapeando o id da tese ao dicionário de dados.
    Se não houver orientações, retorna None.
    """
    orientacoes = {}
    try:
        anchor = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//a[@name='Orientacoesconcluidas']"))
        )
        container = anchor.find_element(By.XPATH, "following::div[contains(@class, 'data-cell')]")
        items = container.find_elements(By.XPATH, ".//a[contains(@href, 'lattes.cnpq.br')]")
        for item in items:
            link = item.get_attribute("href")
            id_match = re.search(r"lattes\.cnpq\.br/(\d+)", link)
            if not id_match:
                continue
            tese_id = id_match.group(1)
            open_lattes_page(driver, link)
            tese_info = extract_cv_info_tese(driver, link)
            tese_info["role"] = role
            orientacoes[tese_id] = tese_info
        if not orientacoes:
            return None
    except Exception as e:
        print("Erro ao extrair orientações:", e)
        return None
    return orientacoes

def process_cv(driver, cv_id, role):
    """
    Processa o currículo com o id cv_id.
    Constrói o link, acessa a página e extrai as informações básicas.
    Se o role for "pivo" ou "pai", extrai também as orientações:
      - Para o pivo: as orientações serão classificadas como role "filho".
      - Para o pai: as orientações serão classificadas como role "irmão".
    Retorna um dicionário no formato:
       { cv_id: { ... dados extraídos ... , "orientações": { ... } } }
    """
    seed_link = f"http://lattes.cnpq.br/{cv_id}"
    open_lattes_page(driver, seed_link)
    cv_info = extract_cv_info(driver, seed_link, role)
    registro = { cv_id: cv_info }
    if role in ["pivo", "pai"]:
        orient_role = "filho" if role == "pivo" else "irmão"
        print(f"Extraindo orientações ({orient_role}) do {role} {cv_id}...")
        registro[cv_id]["orientações"] = extract_orientacoes(driver, orient_role)
    return registro

def process_hierarquia(driver, pivo_id):
    """
    Processa a hierarquia completa:
      - Processa o currículo do pivo (role "pivo").
      - A partir do pivo, se houver id_pai, processa o currículo do pai (role "pai").
      - Do currículo do pai, extrai os orientados (exceto o pivo) como "irmão".
      - Para cada "irmão", processa seu currículo para extrair seus orientados como "sobrinho".
    Retorna um dicionário com todos os registros.
    """
    registros = {}
    # Processa o pivo
    pivo_data = process_cv(driver, pivo_id, "pivo")
    registros.update(pivo_data)
    
    # Processa o pai (orientador do pivo)
    pai_id = pivo_data[pivo_id].get("id_pai", "").strip()
    if pai_id:
        print(f"\nProcessando currículo do pai (orientador do pivo): {pai_id}")
        pai_data = process_cv(driver, pai_id, "pai")
        registros.update(pai_data)
        
        # Processa os orientados do pai: esses serão os "irmãos" do pivo.
        irmaos = {}
        orientados_pai = pai_data[pai_id].get("orientações")
        if orientados_pai:
            for ori_id, ori in orientados_pai.items():
                if ori_id == pivo_id:
                    continue  # ignora se for o pivo
                ori["role"] = "irmão"
                # Para cada irmão, processa seu currículo para extrair seus orientados ("sobrinho")
                sobrinhos_data = process_cv(driver, ori_id, "sobrinho")
                ori["orientações"] = sobrinhos_data.get(ori_id, {}).get("orientações")
                irmaos[ori_id] = ori
        pai_data[pai_id]["orientações"] = irmaos
        registros[pai_id] = pai_data[pai_id]
    else:
        print("Nenhum pai (orientador) identificado para o pivo.")
    
    return registros

def main():
    pivo_id = input("Digite o id do Lattes (pivo) (ex.: 4231401119207209): ").strip()
    if not pivo_id:
        print("ID não informado. Encerrando.")
        return

    driver = initialize_driver()
    registros = process_hierarquia(driver, pivo_id)
    driver.quit()

    print("\n=== Registro Final ===")
    print(json.dumps(registros, indent=4, ensure_ascii=False))
    write_json("registro_lattes.json", registros)

if __name__ == "__main__":
    main()
