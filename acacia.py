import time
import json
from logger_util import get_logger
from databaseAcacia import driver, create_pesquisador, cria_relacao
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

logger = get_logger()

entrada = "docentes-usp-formatados.list"
saida_json = "pesquisadores-extraidos-usp.json"
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

def nome_formatado(nome_url):
    partes = nome_url.replace("-", " ").split()
    minusculas = {"de", "da", "do", "das", "dos", "e"}
    return " ".join([p.capitalize() if p not in minusculas else p for p in partes])

def extrai_pesquisador(nome, page, grupo):
    nome_chave = nome_formatado(nome)
    if nome_chave in pesquisadores_dict:
        return 
    url = base_url + nome
    tentativas = 0
    max_tentativas = 5
    while tentativas < max_tentativas:
        try:
            page.goto(url, timeout=20000)
            html = page.content()
            if "<h1>Not Found</h1>" in html or "The requested resource was not found on this server." in html:
                logger.warning(f"Pesquisador '{nome_chave}' não encontrado na plataforma. Pulando.")
                return
            if "503" in html or "Service Temporarily Unavailable" in html:
                raise Exception("Erro 503 detectado no HTML")
            area, universidade, ascendentes, descendentes = extrai_info(html)
            if area or universidade or ascendentes or descendentes:
                pesquisadores_dict[nome_chave] = {
                    "grupo": grupo,
                    "grande-area": area,
                    "universidade": universidade,
                    "ascendentes": nome_formatado(ascendentes[0]) if ascendentes else "",
                    "descendentes": [nome_formatado(d) for d in descendentes]
                }
                logger.info(f"Extraído: {nome_chave} ({grupo}) - universidade: {universidade} - ascendentes: {ascendentes} - descendentes: {descendentes}")
            break
        except Exception as e:
            tentativas += 1
            logger.warning(f"Tentativa {tentativas} falhou para {nome_chave}: {e}")
            if tentativas < max_tentativas:
                logger.info(f"Recarregando página para {nome_chave} em 5 segundos...")
                time.sleep(5)
    time.sleep(6)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    for nome in nomes:
        # Extrai pivô
        extrai_pesquisador(nome, page, grupo="pivo")
        nome_chave = nome_formatado(nome)
        if nome_chave not in pesquisadores_dict:
            continue  # Não achou o pivô, pula

        # Extrai pai (ascendente)
        asc = pesquisadores_dict[nome_chave]["ascendentes"]
        if asc:
            asc_url = asc.replace(" ", "-").lower()
            extrai_pesquisador(asc_url, page, grupo="pai")
            # Se o pai existir, extrai seus descendentes como filhos
            pai_chave = nome_formatado(asc)
            if pai_chave in pesquisadores_dict:
                for desc in pesquisadores_dict[pai_chave]["descendentes"]:
                    if desc:
                        desc_url = desc.replace(" ", "-").lower()
                        extrai_pesquisador(desc_url, page, grupo="filho")

        # Extrai filhos (descendentes) do pivô normalmente
        for desc in pesquisadores_dict[nome_chave]["descendentes"]:
            if desc:
                desc_url = desc.replace(" ", "-").lower()
                extrai_pesquisador(desc_url, page, grupo="filho")

    browser.close()

with open(saida_json, "w", encoding="utf-8") as f:
    json.dump(pesquisadores_dict, f, ensure_ascii=False, indent=2)

# --- INSERÇÃO DIRETA NO NEO4J ---
with driver.session() as session:
    # Cria vértices
    for nome, dados in pesquisadores_dict.items():
        grande_area = dados.get("grande-area", "")
        universidade = dados.get("universidade", "")
        session.write_transaction(create_pesquisador, nome, grande_area, universidade)

    # Cria relações ascendentes
    for nome, dados in pesquisadores_dict.items():
        asc = dados.get("ascendentes", "")
        if asc and asc in pesquisadores_dict:
            session.write_transaction(cria_relacao, nome, asc, "ASCENDENTE")
        # Cria relações descendentes
        for desc in dados.get("descendentes", []):
            if desc and desc in pesquisadores_dict:
                session.write_transaction(cria_relacao, nome, desc, "DESCENDENTE")

print("Importação para Neo4j concluída.")