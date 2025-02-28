#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para extrair informações do currículo Lattes, identificando
o orientador de doutorado e repetindo o processo para o próprio orientador.
Se o registro do orientador não possuir um link Lattes, o script passa para o próximo ID.
O usuário deverá resolver manualmente o CAPTCHA, se necessário.
"""

import json
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def read_json(filename):
    """Lê o arquivo JSON e retorna o dicionário de dados."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print("Erro ao ler o arquivo JSON:", e)
        return {}

def write_json(filename, data):
    """Escreve o dicionário 'data' no arquivo JSON indicado."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Arquivo atualizado salvo em: {filename}")
    except Exception as e:
        print("Erro ao escrever o arquivo JSON:", e)

def initialize_driver():
    """Inicializa o WebDriver do Chrome (modo não headless para permitir a resolução do CAPTCHA)."""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    service = Service("chromedriver")  # Altere o caminho conforme necessário
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def open_lattes_page(driver, url):
    """
    Abre a página do Lattes com a URL dada e aguarda que o usuário
    resolva o CAPTCHA manualmente, caso apareça.
    """
    driver.get(url)
    print(f"Acessando: {url}")
    print("Caso apareça um CAPTCHA, resolva-o manualmente no navegador.")
    input("Após resolver o CAPTCHA e a página carregar completamente, pressione Enter para continuar...")

def extract_lattes_info(driver, role="docente"):
    """
    Extrai informações do currículo Lattes a partir da página atual.
    Para 'docente': extrai o nome, a instituição de doutorado e o orientador.
    Para 'orientador': extrai o nome e a instituição (armazenada em 'Instituição_orientador').
    
    Retorna um dicionário com as chaves:
      - docente
      - link_lattes
      - Instituição_doutorado (ou Instituição_orientador)
      - Orientador_doutorado
    """
    info = {}
    
    # Extrai o nome (geralmente em <h2 class="nome">)
    try:
        nome_elem = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(@class, 'nome')]"))
        )
        info["docente"] = nome_elem.text.strip()
    except Exception as e:
        print("Erro ao extrair o nome:", e)
        info["docente"] = ""
    
    # Tenta extrair o link do Lattes a partir de um elemento que contenha o padrão "http://lattes.cnpq.br/"
    try:
        link_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'http://lattes.cnpq.br/')]"))
        )
        link_text = link_elem.text.strip()
        if re.search(r"http://lattes\.cnpq\.br/\d+", link_text):
            info["link_lattes"] = link_text
        else:
            info["link_lattes"] = driver.current_url
    except Exception:
        info["link_lattes"] = driver.current_url

    # Inicializa os campos conforme o papel
    if role == "docente":
        info["Instituição_doutorado"] = ""
        info["Orientador_doutorado"] = ""
    else:
        info["Instituição_orientador"] = ""
        info["Orientador_doutorado"] = ""
    
    # Procura a seção de formação acadêmica
    try:
        anchor = WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.XPATH, "//a[@name='FormacaoAcademicaTitulacao']"))
        )
        container = anchor.find_element(By.XPATH, "following::div[contains(@class, 'data-cell')]")
        blocks = container.find_elements(By.XPATH, ".//div[contains(@class, 'layout-cell-pad-5')]")
        for block in blocks:
            text = block.text
            if "Doutorado" in text:
                parts = text.split('.')
                if len(parts) >= 2:
                    instituicao = parts[1].strip()
                    if role == "docente":
                        info["Instituição_doutorado"] = instituicao
                    else:
                        info["Instituição_orientador"] = instituicao
                orientador_match = re.search(r"Orientador:\s*(.+)", text)
                if orientador_match:
                    orientador_extracao = orientador_match.group(1).strip()
                    try:
                        orientador_link = block.find_element(By.XPATH, ".//a[contains(@href, 'lattes.cnpq.br')]")
                        orientador_extracao = orientador_link.get_attribute("href")
                    except Exception:
                        pass
                    info["Orientador_doutorado"] = orientador_extracao
                break
    except Exception as e:
        print("Erro ao extrair informações de formação:", e)
    
    return info

def extract_orientador_info(driver, orientador_id):
    """
    Dado o ID do orientador, monta a URL do currículo e abre a página,
    aguardando a resolução do CAPTCHA. Em seguida, extrai as informações
    com o papel de 'orientador'.
    """
    orientador_url = f"http://lattes.cnpq.br/{orientador_id}"
    open_lattes_page(driver, orientador_url)
    orient_info = extract_lattes_info(driver, role="orientador")
    return orient_info

def update_json_with_orientador(data, driver):
    """
    Para cada registro no JSON, verifica se existe o campo "Orientador_doutorado"
    com link válido (contendo "lattes.cnpq.br"). Se existir, extrai o ID do orientador,
    abre sua página, extrai as informações e adiciona um novo registro no JSON.
    Caso o campo não contenha um link válido, o registro é ignorado.
    """
    updated = data.copy()
    for docente_id, record in data.items():
        if not isinstance(record, dict):
            print(f"Registro inesperado para {docente_id}: {record}")
            continue
        orientador_info = record.get("Orientador_doutorado", "").strip()
        # Verifica se há um link válido para o orientador
        if orientador_info and "lattes.cnpq.br" in orientador_info:
            orientador_id_match = re.search(r"lattes\.cnpq\.br/(\d+)", orientador_info)
            if orientador_id_match:
                orientador_id = orientador_id_match.group(1)
                print(f"\nProcessando orientador para o docente: {record.get('docente')}")
                orient_info = extract_orientador_info(driver, orientador_id)
                orientador_record = {
                    "docente": orient_info.get("docente", ""),
                    "link_lattes": orient_info.get("link_lattes", f"http://lattes.cnpq.br/{orientador_id}"),
                    "Instituição_orientador": orient_info.get("Instituição_orientador", ""),
                    "Orientador_doutorado": orient_info.get("Orientador_doutorado", "")
                }
                updated[orientador_id] = orientador_record
            else:
                print(f"Não foi possível extrair o ID do orientador para {record.get('docente')}")
        else:
            print(f"\nOrientador sem link Lattes para o docente: {record.get('docente')}. Verificando próximo registro.")
            continue  # Passa para o próximo registro se o link não for válido
    return updated

def main():
    data = read_json("testeCharles.json")
    if not data:
        print("Nenhum dado lido do JSON.")
        return

    # Obtém o primeiro registro (supondo que a chave seja o ID)
    primeiro_id = next(iter(data))
    primeiro_record = data[primeiro_id]
    
    driver = initialize_driver()

    open_lattes_page(driver, primeiro_record.get("link_lattes"))
    docente_info = extract_lattes_info(driver, role="docente")
    data[primeiro_id].update({
        "docente": docente_info.get("docente", ""),
        "link_lattes": docente_info.get("link_lattes", ""),
        "Instituição_doutorado": docente_info.get("Instituição_doutorado", ""),
        "Orientador_doutorado": docente_info.get("Orientador_doutorado", "")
    })

    updated_data = update_json_with_orientador(data, driver)

    driver.quit()

    print("\n=== Dados Atualizados ===")
    print(json.dumps(updated_data, indent=4, ensure_ascii=False))
    write_json("testeCharles.json", updated_data)

if __name__ == "__main__":
    main()
