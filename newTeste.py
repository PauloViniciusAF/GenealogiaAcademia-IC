#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para processar currículos Lattes e gerar um JSON no seguinte formato:

{
    "<id_docente>": {
        "link_lattes": "http://lattes.cnpq.br/<id_docente>",
        "Instituição_doutorado": "<instituição do doutorado>",
        "id_pai": "<id do orientador>",
        "Instituição_orientador": "<instituição do orientador>",
        "orientações": {
            "<id_tese1>": {
                "nome": "<nome ou título da tese>",
                "link_lattes": "http://lattes.cnpq.br/<id_tese1>",
                "Instituição_doutorado": "<instituição da orientação>"
            }
        }
    }
}

Passos do código:
1. Extrai as informações do id do usuário.
2. Extrai as informações de "orientações" (se não tiver nenhuma, salva como 'None').
3. Extrai as informações do id_pai (orientador, se houver).

ATENÇÃO: O usuário deverá resolver manualmente o CAPTCHA.
"""

import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------- Funções de I/O ----------

def write_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Dados salvos em: {filename}")
    except Exception as e:
        print(f"Erro ao escrever o arquivo {filename}: {e}")

# ---------- Funções Selenium ----------

def initialize_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    service = Service("chromedriver")  # Ajuste conforme necessário
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def open_lattes_page(driver, url):
    driver.get(url)
    print(f"Acessando: {url}")
    print("Se aparecer um CAPTCHA, resolva-o manualmente.")
    input("Quando a página estiver carregada, pressione Enter para continuar...")

# ---------- Extração de dados do currículo ----------

def extract_cv_info(driver, seed_link):
    """
    Extrai informações básicas do currículo Lattes:
    - Nome
    - Instituição de doutorado
    - ID do orientador (id_pai)
    Retorna um dicionário com essas informações.
    """
    info = {"link_lattes": seed_link, "Instituição_doutorado": "", "id_pai": ""}

    # Extrai o nome do pesquisador
    try:
        nome_elem = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(@class, 'nome')]"))
        )
        info["Nome"] = nome_elem.text.strip()
    except Exception:
        info["Nome"] = None

    # Extrai informações do bloco de formação acadêmica
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
                info["Instituição_doutorado"] = parts[1].strip() if len(parts) >= 2 else ""

                # Tenta extrair o link do orientador
                try:
                    orientador_link_elem = block.find_element(By.XPATH, ".//a[contains(@href, 'lattes.cnpq.br')]")
                    link_orient = orientador_link_elem.get_attribute("href")
                    id_match = re.search(r"lattes\.cnpq\.br/(\d+)", link_orient)
                    if id_match:
                        info["id_pai"] = id_match.group(1)
                except Exception:
                    pass
                break
    except Exception:
        pass

    return info

def extract_orientacoes(driver):
    """
    Extrai todas as orientações (tese de doutorado) em que o pesquisador participou.
    Retorna um dicionário onde cada chave é o id da tese e os valores são:
    - nome
    - link_lattes
    - Instituição_doutorado
    Se não houver orientações, retorna `None`.
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
            if id_match:
                tese_id = id_match.group(1)
                tese_info = extract_cv_info_tese(driver, link)
                orientacoes[tese_id] = tese_info

    except Exception:
        return None  # Se não houver orientações, retorna None

    return orientacoes

def extract_cv_info_tese(driver, seed_link):
    """
    Extrai informações básicas de uma tese de doutorado.
    Retorna um dicionário com:
    - nome (do orientado ou título da tese)
    - link_lattes
    - Instituição_doutorado
    """
    info = {"link_lattes": seed_link, "Instituição_doutorado": ""}

    try:
        nome_elem = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(@class, 'nome')]"))
        )
        info["nome"] = nome_elem.text.strip()
    except Exception:
        info["nome"] = None

    return info

# ---------- Processo principal ----------

def main():
    cv_id = input("Digite o id do Lattes (ex.: 4231401119207209): ").strip()
    if not cv_id:
        print("ID não informado. Encerrando.")
        return

    driver = initialize_driver()
    seed_link = f"http://lattes.cnpq.br/{cv_id}"

    # 1. Extrai informações do id do usuário
    open_lattes_page(driver, seed_link)
    registro = extract_cv_info(driver, seed_link)

    # 2. Extrai informações das orientações
    print("Extraindo orientações...")
    registro["orientações"] = extract_orientacoes(driver)

    # 3. Extrai informações do id_pai (se houver)
    if registro["id_pai"]:
        print(f"Processando currículo do orientador (pai): {registro['id_pai']}")
        seed_link_pai = f"http://lattes.cnpq.br/{registro['id_pai']}"
        open_lattes_page(driver, seed_link_pai)
        registro_pai = extract_cv_info(driver, seed_link_pai)
        registro["Instituição_orientador"] = registro_pai["Instituição_doutorado"]

    driver.quit()

    write_json("registro_lattes.json", {cv_id: registro})

if __name__ == "__main__":
    main()
