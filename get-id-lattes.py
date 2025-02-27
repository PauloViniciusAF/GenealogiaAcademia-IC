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
    Estrutura esperada:
    {
        "9346953261085205" : [
            {
                "docente": "Charles Henrique Porto Ferreira",
                "departamento": "Ciência da Computação",
                "link_lattes": "http://lattes.cnpq.br/9346953261085205",
                "Instituição_doutorado": "Universidade Federal do ABC",
                "Orientador_doutorado": "0803731316406727",
                "orientados": ""
            }
        ]
    }
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
    Como é necessário resolver o CAPTCHA manualmente, não usamos modo headless.
    """
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    service = Service("chromedriver.exe")  # ajuste conforme seu ambiente (Linux/Mac: "chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def open_lattes_page(driver, url):
    """
    Abre a página do Lattes com a URL dada e pausa para que o usuário resolva o CAPTCHA.
    """
    driver.get(url)
    print(f"Acessando: {url}")
    print("Caso apareça um CAPTCHA, por favor, resolva-o manualmente no navegador.")
    input("Depois de resolver o CAPTCHA e a página estiver carregada, pressione Enter para continuar...")

def extract_lattes_info(driver):
    """
    Extrai informações básicas da página do Lattes atual.
    Retorna um dicionário com as chaves:
      "docente", "link_lattes", "Instituição_doutorado", "orientador_doutorado", "orientados"
    A extração é feita a partir da seção "FormacaoAcademicaTitulacao" e do elemento <h2 class="nome">.
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
    # Extrai dados da seção de formação (considera que o bloco de doutorado contém o texto "Doutorado")
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
                orientador = ""
                for part in parts:
                    if "Orientador:" in part:
                        orientador = part.split("Orientador:")[-1].strip()
                        break
                info["orientador_doutorado"] = orientador
                break
        if "Instituição_doutorado" not in info:
            info["Instituição_doutorado"] = ""
        if "orientador_doutorado" not in info:
            info["orientador_doutorado"] = ""
    except Exception as e:
        print("Erro ao extrair informações de formação:", e)
        info["Instituição_doutorado"] = ""
        info["orientador_doutorado"] = ""
    info["orientados"] = ""
    return info

def extract_orientador_info(driver, orientador_id):
    """
    Dado o ID do orientador, abre a página correspondente e extrai as informações usando extract_lattes_info.
    Retorna o dicionário de informações do orientador.
    """
    orientador_url = f"http://lattes.cnpq.br/{orientador_id}"
    open_lattes_page(driver, orientador_url)
    orient_info = extract_lattes_info(driver)
    return orient_info

def update_record_with_orientador(data, driver):
    """
    Para cada registro do JSON, se existir o campo "Orientador_doutorado" (ID do orientador),
    extrai as informações do orientador e adiciona (ou atualiza) uma nova chave "orientador_info" com os dados extraídos.
    Retorna o dicionário atualizado.
    """
    for key, records in data.items():
        for record in records:
            orientador_id = record.get("Orientador_doutorado", "").strip()
            if orientador_id:
                print(f"\nProcessando orientador para o docente: {record.get('docente')}")
                orient_info = extract_orientador_info(driver, orientador_id)
                # Atualiza o registro com os dados do orientador extraídos
                record["orientador_info"] = orient_info
            else:
                print(f"\nNenhum ID de orientador para o docente: {record.get('docente')}")
    return data

def main():
    # Lê os dados do JSON original
    data = read_json("testeCharles.json")
    if not data:
        print("Nenhum dado lido do JSON.")
        return

    # Inicializa o driver (para navegar nas páginas do Lattes)
    driver = initialize_driver()
    
    # Atualiza os registros com as informações do orientador
    updated_data = update_record_with_orientador(data, driver)
    
    driver.quit()
    
    # Exibe o resultado final (pode ser escrito em um novo arquivo)
    print("\n=== Dados Atualizados ===")
    print(json.dumps(updated_data, indent=4, ensure_ascii=False))
    
    # Opcional: escreva os dados atualizados em um novo arquivo JSON
    write_json("testeCharles_updated.json", updated_data)

if __name__ == "__main__":
    main()
