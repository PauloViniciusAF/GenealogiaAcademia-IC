import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def read_json(filename):
    """
    Lê o arquivo JSON e retorna o dicionário de dados.
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print("Erro ao ler o arquivo JSON:", e)
        return {}

def write_json(filename, data):
    """
    Escreve o dicionário 'data' no arquivo JSON indicado.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Arquivo atualizado salvo em: {filename}")
    except Exception as e:
        print("Erro ao escrever o arquivo JSON:", e)

def initialize_driver():
    """
    Inicializa o WebDriver do Chrome.
    Como precisamos resolver o CAPTCHA manualmente, não usamos headless.
    """
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    service = Service("chromedriver")  # ajuste conforme seu ambiente (Linux/Mac: "chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def open_lattes_page(driver, url):
    """
    Abre a página do Lattes com a URL dada e pausa para que o usuário resolva o CAPTCHA, se necessário.
    """
    driver.get(url)
    print(f"Acessando: {url}")
    print("Caso apareça um CAPTCHA, por favor, resolva-o manualmente no navegador.")
    input("Depois de resolver o CAPTCHA e a página estiver carregada, pressione Enter para continuar...")

def extract_lattes_info(driver, role="docente"):
    """
    Extrai informações básicas da página atual do Lattes.
    Dependendo do parâmetro role:
      - Se role=="docente":
            Armazena a instituição extraída em "Instituição_doutorado"
            e o texto do orientador em "orientador_doutorado"
      - Se role=="orientador":
            Armazena a instituição extraída em "Instituição_orientador"
            e define "Orientador_doutorado" como vazio (ou conforme extraído, se disponível)
    Retorna um dicionário com as chaves:
       "docente", "link_lattes", "Instituição_doutorado"/"Instituição_orientador",
       "Orientador_doutorado", "orientados"
    """
    info = {}
    # Extrai o nome (geralmente em <h2 class="nome">)
    try:
        nome_elem = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(@class, 'nome')]"))
        )
        info["docente"] = nome_elem.text.strip() if nome_elem else ""
    except Exception as e:
        print("Erro ao extrair o nome:", e)
        info["docente"] = ""
    info["link_lattes"] = driver.current_url

    # Extrai dados da seção de formação (para o doutorado)
    try:
        anchor = WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.XPATH, "//a[@name='FormacaoAcademicaTitulacao']"))
        )
        container = anchor.find_element(By.XPATH, "following::div[contains(@class, 'layout-cell-12 data-cell')]")
        blocks = container.find_elements(By.CLASS_NAME, "layout-cell-pad-5")
        extracted = False
        for block in blocks:
            text = block.text
            if "Doutorado" in text:
                parts = text.split('.')
                if role == "docente":
                    info["Instituição_doutorado"] = parts[1].strip() if len(parts) >= 2 else ""
                    orientador = ""
                    for part in parts:
                        if "Orientador:" in part:
                            orientador = part.split("Orientador:")[-1].strip()
                            break
                    info["Orientador_doutorado"] = orientador
                elif role == "orientador":
                    info["Instituição_orientador"] = parts[1].strip() if len(parts) >= 2 else ""
                    # Para o orientador, se houver informação sobre seu orientador, pode-se extrair;
                    # caso contrário, deixamos vazio.
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
    """
    Dado o ID do orientador, abre a página correspondente e extrai as informações
    com a mesma estrutura (usando role="orientador").
    Retorna o dicionário de informações do orientador.
    """
    orientador_url = f"http://lattes.cnpq.br/{orientador_id}"
    open_lattes_page(driver, orientador_url)
    orient_info = extract_lattes_info(driver, role="orientador")
    return orient_info

def update_json_with_orientador(data, driver):
    """
    Para cada registro do JSON (assumido como dicionário, não lista),
    se existir o campo "Orientador_doutorado", extrai as informações do orientador
    e adiciona um novo item no dicionário com a mesma estrutura.
    """
    # Cria uma cópia dos dados para atualizar
    updated = data.copy()
    for docente_id, record in data.items():
        if not isinstance(record, dict):
            print(f"Registro inesperado para {docente_id}: {record}")
            continue
        orientador_id = record.get("Orientador_doutorado", "").strip()
        if orientador_id:
            print(f"\nProcessando orientador para o docente: {record.get('docente')}")
            orient_info = extract_orientador_info(driver, orientador_id)
            # Atualiza o registro do docente (se desejar, pode manter os dados originais)
            # E adiciona um novo item no JSON para o orientador com a mesma estrutura:
            orientador_record = {
                "docente": orient_info.get("docente", ""),
                "link_lattes": orient_info.get("link_lattes", f"http://lattes.cnpq.br/{orientador_id}"),
                "Instituição_doutorado": orient_info.get("Instituição_doutorado", ""),
                "Orientador_doutorado": orient_info.get("Orientador_doutorado", ""),
                "Instituição_orientador": orient_info.get("Instituição_orientador", "")
            }
            updated[orientador_id] = orientador_record
        else:
            print(f"\nNenhum ID de orientador para o docente: {record.get('docente')}")
    return updated

def main():
    # Lê o arquivo JSON com os dados
    data = read_json("testeCharles.json")
    if not data:
        print("Nenhum dado lido do JSON.")
        return

    driver = initialize_driver()
    
    # Atualiza o JSON adicionando um novo item para o orientador (se existir)
    updated_data = update_json_with_orientador(data, driver)
    
    driver.quit()
    
    print("\n=== Dados Atualizados ===")
    print(json.dumps(updated_data, indent=4, ensure_ascii=False))
    write_json("testeCharles_updated.json", updated_data)

if __name__ == "__main__":
    main()
