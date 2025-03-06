#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para extrair informações do currículo Lattes, identificando
o orientador de doutorado e repetindo o processo para o próprio orientador.
Antes de acessar o currículo do docente, verifica se o orientador já existe
no arquivo JSON (ou seja, se o link do orientador já aparece como link_lattes
em outro registro). Se sim, passa para o próximo id.
O usuário deverá resolver manualmente o CAPTCHA, se necessário.
"""

import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def read_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Erro ao ler o arquivo {filename}: {e}")
        return {}

def write_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Arquivo atualizado salvo em: {filename}")
    except Exception as e:
        print(f"Erro ao escrever o arquivo {filename}: {e}")

def initialize_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    service = Service("chromedriver")  # ajuste conforme seu ambiente
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def open_lattes_page(driver, url):
    driver.get(url)
    print(f"Acessando: {url}")
    print("Caso apareça um CAPTCHA, resolva-o manualmente no navegador.")
    input("Depois de resolver o CAPTCHA e a página estiver carregada, pressione Enter para continuar...")

def check_orientador_existe_no_json(data, orientador_link):
    """
    Verifica se o orientador já existe no JSON, isto é, se algum registro possui
    o "link_lattes" igual a orientador_link.
    Retorna True se existir, False caso contrário.
    """
    if not orientador_link:
        return False
    for key, record in data.items():
        if record.get("link_lattes", "").strip() == orientador_link:
            return True
    return False

def extract_orientador_link(driver):
    """
    Percorre os blocos de formação acadêmica procurando por um orientador que possua link Lattes.
    Retorna o link do orientador (string) se encontrado; caso contrário, retorna None.
    """
    try:
        anchor = WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.XPATH, "//a[@name='FormacaoAcademicaTitulacao']"))
        )
        container = anchor.find_element(By.XPATH, "following::div[contains(@class, 'layout-cell-12 data-cell')]")
        blocks = container.find_elements(By.XPATH, ".//div[contains(@class, 'layout-cell-pad-5')]")
        for block in blocks:
            text = block.text
            if "Orientador:" in text:
                try:
                    orientador_link_elem = block.find_element(By.XPATH, ".//a[contains(@href, 'lattes.cnpq.br')]")
                    link = orientador_link_elem.get_attribute("href")
                    if link and re.search(r"lattes\.cnpq\.br/\d+", link):
                        return link
                except Exception:
                    continue
        return None
    except Exception as e:
        print("Erro ao extrair o link do orientador:", e)
        return None

def extract_lattes_info(driver, seed_link, role="docente"):
    """
    Extrai informações do currículo Lattes a partir da página atual.
    O campo info["link_lattes"] recebe o seed_link (link do id conforme o JSON).
    Para role=="docente": extrai o nome, a instituição de doutorado e o orientador.
    Para role=="orientador": extrai a instituição em "Instituição_orientador".
    Retorna um dicionário com as chaves:
       "docente", "link_lattes", "Instituição_doutorado"/"Instituição_orientador",
       "Orientador_doutorado", "orientados"
    """
    info = {}
    try:
        nome_elem = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(@class, 'nome')]"))
        )
        info["docente"] = nome_elem.text.strip() if nome_elem else ""
    except Exception as e:
        print("Erro ao extrair o nome:", e)
        info["docente"] = ""
    
    info["link_lattes"] = seed_link

    if role == "docente":
        info["Instituição_doutorado"] = ""
        info["Orientador_doutorado"] = ""
    else:
        info["Instituição_orientador"] = ""
        info["Orientador_doutorado"] = ""
    
    try:
        anchor = WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.XPATH, "//a[@name='FormacaoAcademicaTitulacao']"))
        )
        container = anchor.find_element(By.XPATH, "following::div[contains(@class, 'layout-cell-12 data-cell')]")
        blocks = container.find_elements(By.CLASS_NAME, "layout-cell-pad-5")
        extracted = False
        for block in blocks:
            text = block.text
            if "Doutorado" in text or "Mestrado" in text:
                parts = text.split('.')
                if role == "docente":
                    info["Instituição_doutorado"] = parts[1].strip() if len(parts) >= 2 else ""
                    orientador_link = None
                    try:
                        orientador_link = block.find_element(By.XPATH, ".//a[contains(@href, 'lattes.cnpq.br')]")
                    except Exception:
                        pass
                    if orientador_link:
                        info["Orientador_doutorado"] = orientador_link.get_attribute("href")
                    else:
                        orientador = ""
                        for part in parts:
                            if "Orientador:" in part:
                                orientador = part.split("Orientador:")[-1].strip()
                                break
                        info["Orientador_doutorado"] = orientador
                elif role == "orientador":
                    info["Instituição_orientador"] = parts[1].strip() if len(parts) >= 2 else ""
                    orientador_text = ""
                    for part in parts:
                        if "Orientador:" in part:
                            orientador_text = part.split("Orientador:")[-1].strip()
                            break
                    info["Orientador_doutorado"] = orientador_text
                extracted = True
                break
        if not extracted:
            if role == "docente":
                info["Instituição_doutorado"] = ""
                info["Orientador_doutorado"] = ""
            elif role == "orientador":
                info["Instituição_orientador"] = ""
                info["Orientador_doutorado"] = ""
    except Exception as e:
        print("Erro ao extrair informações de formação:", e)
        if role == "docente":
            info["Instituição_doutorado"] = ""
            info["Orientador_doutorado"] = ""
        elif role == "orientador":
            info["Instituição_orientador"] = ""
            info["Orientador_doutorado"] = ""
    info["orientados"] = ""
    return info

def extract_orientador_info(driver, orientador_id):
    seed_link = f"http://lattes.cnpq.br/{orientador_id}"
    open_lattes_page(driver, seed_link)
    orient_info = extract_lattes_info(driver, seed_link, role="orientador")
    return orient_info

def orientador_ja_existe(orientador_id, orientadores_file="orientadores.json"):
    orientadores = read_json(orientadores_file)
    if orientador_id in orientadores:
        print(f"Orientador {orientador_id} já consta no arquivo {orientadores_file}.")
        return True
    return False

def update_json_with_orientador(data, driver, orientadores_file="orientadores.json"):
    updated = data.copy()
    for docente_id, record in data.items():
        if not isinstance(record, dict):
            print(f"Registro inesperado para {docente_id}: {record}")
            continue
        orientador_info = record.get("Orientador_doutorado", "").strip()
        # Antes de processar, verifica se o orientador já existe no JSON com base no link
        if check_orientador_existe_no_json(data, orientador_info):
            print(f"O orientador {orientador_info} já está registrado. Pulando o id {docente_id}.")
            continue
        if orientador_info:
            orientador_id_match = re.search(r"lattes\.cnpq\.br/(\d+)", orientador_info)
            if orientador_id_match:
                orientador_id = orientador_id_match.group(1)
                if orientador_ja_existe(orientador_id, orientadores_file):
                    print(f"Pular acesso para o orientador {orientador_id} pois já consta.")
                    continue
                # Verifica se há pelo menos um orientador com link na página do docente
                orientador_link = extract_orientador_link(driver)
                if not orientador_link:
                    print(f"Não foi encontrado nenhum orientador com link Lattes para o docente: {record.get('docente')}. Pulando este registro.")
                    continue
                orientador_id_match = re.search(r"lattes\.cnpq\.br/(\d+)", orientador_link)
                if orientador_id_match:
                    orientador_id = orientador_id_match.group(1)
                orient_info = extract_orientador_info(driver, orientador_id)
                orientador_record = {
                    "docente": orient_info.get("docente", ""),
                    "link_lattes": orient_info.get("link_lattes", f"http://lattes.cnpq.br/{orientador_id}"),
                    "Instituição_doutorado": orient_info.get("Instituição_doutorado", ""),
                    "Orientador_doutorado": orient_info.get("Orientador_doutorado", ""),
                    "Instituição_orientador": orient_info.get("Instituição_orientador", "")
                }
                updated[orientador_id] = orientador_record
                orientadores = read_json(orientadores_file)
                orientadores[orientador_id] = orientador_record
                write_json(orientadores_file, orientadores)
            else:
                print(f"Não foi possível extrair o ID do orientador para {record.get('docente')}")
        else:
            print(f"\nNenhum orientador para o docente: {record.get('docente')}")
    return updated

def main():
    data = read_json("orientadores.json")
    if not data:
        print("Nenhum dado lido do JSON.")
        return

    driver = initialize_driver()
    
    for docente_id, record in data.items():
        link = record.get("link_lattes", "")
        if link:
            open_lattes_page(driver, link)
            docente_info = extract_lattes_info(driver, link, role="docente")
            data[docente_id].update({
                "docente": docente_info.get("docente", ""),
                "link_lattes": docente_info.get("link_lattes", link),
                "Instituição_doutorado": docente_info.get("Instituição_doutorado", ""),
                "Orientador_doutorado": docente_info.get("Orientador_doutorado", "")
            })
        else:
            print(f"Docente {docente_id} não possui link_lattes.")
    
    updated_data = update_json_with_orientador(data, driver)
    
    driver.quit()
    
    print("\n=== Dados Atualizados ===")
    print(json.dumps(updated_data, indent=4, ensure_ascii=False))
    write_json("orientadores.json", updated_data)

if __name__ == "__main__":
    main()
