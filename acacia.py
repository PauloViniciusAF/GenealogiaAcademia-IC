from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import json
from logger_util import get_logger

logger = get_logger()

entrada = "docentes-fei.list"
saida_json = "pesquisadores-extraidos.json"
base_url = "https://plataforma-acacia.org/profile/"

with open(entrada, "r", encoding="utf-8") as f:
    nomes = [linha.strip() for linha in f if linha.strip()]

pesquisadores_dict = {}

def extrai_info(html):
    soup = BeautifulSoup(html, "html.parser")
    # Extrai área
    h3 = soup.find("h3", class_="subtitle is-size-6 mb-0")
    if h3:
        area = " ".join(h3.stripped_strings)
        area = area.replace("\n", " ").replace("\r", " ")
        area = " / ".join([part.strip() for part in area.split("/")])
        area = " ".join(area.split())
    else:
        area = ""
    # Universidade
    universidade = ""
    span_uni = soup.find("span", itemprop="name", class_="is-size-6")
    if span_uni:
        universidade = span_uni.text.strip()
    # Ascendentes
    ascendentes = []
    asc_table = soup.find("table", id="table-profile-ascendants")
    if asc_table:
        for tr in asc_table.find("tbody").find_all("tr"):
            tags = tr.find_all("span", class_="tag is-d")
            if tags:
                nome_asc = tr.find("span", itemprop="name")
                if nome_asc:
                    ascendentes.append(nome_asc.text.strip())
    # Descendentes
    descendentes = []
    desc_table = soup.find("table", id="table-profile-descendants")
    if desc_table:
        for tr in desc_table.find("tbody").find_all("tr"):
            tags = tr.find_all("span", class_="tag is-d")
            if tags:
                nome_desc = tr.find("span", itemprop="name")
                if nome_desc:
                    descendentes.append(nome_desc.text.strip())
    return area, universidade, ascendentes, descendentes

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    for nome in nomes:
        url = base_url + nome
        logger.info(f"Acessando: {url}")
        tentativas = 0
        max_tentativas = 5
        while tentativas < max_tentativas:
            try:
                page.goto(url, timeout=20000)
                html = page.content()
                # Verifica se a página retornou erro 503 ou não tem área
                if "503" in html or "Service Temporarily Unavailable" in html:
                    raise Exception("Erro 503 detectado no HTML")
                area, universidade, ascendentes, descendentes = extrai_info(html)
                if not area and not universidade and not ascendentes and not descendentes:
                    raise Exception("Informações não encontradas na página")
                pesquisadores_dict[nome] = {
                    "grande-area": area,
                    "universidade": universidade,
                    "ascendentes": ascendentes[0] if ascendentes else "",
                    "descendentes": descendentes
                }
                logger.info(f"Extraído: {nome} - universidade: {universidade} - ascendentes: {ascendentes} - descendentes: {descendentes}")
                break  # Sai do laço se deu certo
            except Exception as e:
                tentativas += 1
                logger.warning(f"Tentativa {tentativas} falhou para {nome}: {e}")
                if tentativas < max_tentativas:
                    logger.info(f"Recarregando página para {nome} em 5 segundos...")
                    time.sleep(5)
                else:
                    logger.error(f"Falha ao extrair dados de {nome} após {max_tentativas} tentativas.")
                    pesquisadores_dict[nome] = {
                        "grande-area": "",
                        "universidade": "",
                        "ascendentes": "",
                        "descendentes": []
                    }
        time.sleep(3)  # Aguarda 3 segundos entre pesquisadores

    browser.close()

with open(saida_json, "w", encoding="utf-8") as f:
    json.dump(pesquisadores_dict, f, ensure_ascii=False, indent=2)