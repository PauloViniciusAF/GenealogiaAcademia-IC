import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def ler_json(arquivo_json):
    """
    Lê o arquivo JSON e retorna o dicionário com os dados.
    Exemplo de estrutura:
    {
      "9346953261085205": [
         {
            "docente": "Charles Henrique Porto Ferreira",
            "departamento": "Ciência da Computação",
            "link_lattes": "http://lattes.cnpq.br/9346953261085205",
            "Instituição_doutorado" : "Universidade Federal do ABC",
            "Orientador_doutorado" : "0803731316406727",
            "Orientados" : ""
         }
      ]
    }
    """
    try:
        with open(arquivo_json, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados
    except Exception as e:
        print("Erro ao ler o arquivo JSON:", e)
        return {}

def obter_link_lattes_do_json(registro):
    """
    Recebe um registro (dicionário) e retorna o link Lattes.
    """
    return registro.get("link_lattes")

def inicializar_driver():
    """
    Inicializa o Selenium WebDriver para o Chrome.
    """
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    # Não usamos o modo headless pois precisamos resolver o CAPTCHA manualmente.
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def abrir_lattes(driver, link):
    """
    Abre o link Lattes com o Selenium e aguarda o usuário resolver o CAPTCHA.
    """
    driver.get(link)
    print(f"Acessando: {link}")
    print("Caso apareça um CAPTCHA, por favor, resolva-o manualmente no navegador.")
    input("Depois de resolver o CAPTCHA e a página estiver carregada, pressione Enter para continuar...")

def extrair_info_lattes(driver):
    """
    Utiliza o Selenium para extrair as informações da seção "Formação acadêmica/titulação".
    Retorna um dicionário com:
      - "instituicao": a instituição extraída (segunda linha)
      - "orientador": o nome extraído da linha que começa com "Orientador:"
    """
    try:
        # Procura o elemento que contenha o texto "Doutorado em" na div com a classe "layout-cell-pad-5"
        elemento = WebDriverWait(driver, 40).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class, 'layout-cell-pad-5') and contains(., 'Doutorado em')]")
            )
        )
        texto = elemento.text
        partes = texto.split('.')
        doutorado = partes[0].strip() if len(partes) > 0 else ""
        instituicao = partes[1].strip() if len(partes) > 1 else ""

        return {
            "instituicao": instituicao,
            "doutorado": doutorado
        }
    except Exception as e:
        print("Erro durante a extração com Selenium:", e)
        return {}

def processar_docente(registro, driver):
    """
    Processa um registro do docente:
      - Abre o site Lattes do docente e extrai as informações.
      - A partir do ID do orientador (campo "Orientador_doutorado"), constrói o link do orientador,
        abre a página do orientador, solicita a resolução do CAPTCHA e extrai as informações.
      - Retorna um dicionário formatado conforme desejado.
    """
    # Obter dados do docente
    docente = registro.get("docente", "")
    departamento = registro.get("departamento", "")
    link_docente = obter_link_lattes_do_json(registro)
    
    if not link_docente:
        print("Link Lattes do docente não encontrado no registro.")
        return None
    
    # Processa o docente
    print("\n=== Processando Docente ===")
    abrir_lattes(driver, link_docente)
    info_docente = extrair_info_lattes(driver)
    
    # Processa o orientador
    orientador_id = registro.get("Orientador_doutorado", "")
    if orientador_id:
        orientador_link = "http://lattes.cnpq.br/" + orientador_id
        print("\n=== Processando Orientador ===")
        abrir_lattes(driver, orientador_link)
        info_orientador = extrair_info_lattes(driver)
    else:
        info_orientador = {}
    
    # Monta o dicionário final utilizando o ID do docente como chave
    docente_id = link_docente.rstrip('/').split('/')[-1]
    resultado = {
        docente_id: {
            "docente": docente,
            "departamento": departamento,
            "link_lattes": link_docente,
            "Instituição_doutorado": info_docente.get("instituicao", ""),
            "Orientador_doutorado": orientador_id,
            "link_orientador": orientador_link if orientador_id else "",
            "Instituição_orientador": info_orientador.get("instituicao", ""),
            "Orientados": registro.get("Orientados", "")
        }
    }
    
    # Atualiza o arquivo JSON com os novos dados
    with open("testeCharles.json", "r+", encoding="utf-8") as f:
        dados_existentes = json.load(f)
        dados_existentes.update(resultado)
        f.seek(0)
        json.dump(dados_existentes, f, indent=4, ensure_ascii=False)
        f.truncate()
    return resultado

def main():
    # Lê os dados do JSON (arquivo com a estrutura especificada)
    dados = ler_json("testeCharles.json")
    if not dados:
        return

    # Inicializa o Selenium WebDriver
    driver = inicializar_driver()
    
    resultados_finais = {}
    
    # Itera sobre cada chave do JSON (cada docente)
    for docente_id, lista_registros in dados.items():
        # Aqui, supomos que há um registro por chave (pode ser adaptado se houver mais de um)
        for registro in lista_registros:
            resultado = processar_docente(registro, driver)
            if resultado:
                resultados_finais.update(resultado)
    
    driver.quit()
    
    print("\n=== Resultado Final ===")
    print(json.dumps(resultados_finais, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()
