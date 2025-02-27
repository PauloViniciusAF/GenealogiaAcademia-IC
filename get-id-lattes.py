from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def extrair_info_lattes(driver):
    """
    Após o CAPTCHA ser resolvido e a página estar carregada,
    extrai as informações da seção "Formação acadêmica/titulação".
    """
    try:
        # Aguarda até que a âncora com name "FormacaoAcademicaTitulacao" esteja presente
        formacao_anchor = WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.XPATH, "//a[@name='FormacaoAcademicaTitulacao']"))
        )
        print("Anchora encontrada:", formacao_anchor.get_attribute("outerHTML"))
        
        # A partir dela, procura o container com os dados
        container = formacao_anchor.find_element(By.XPATH, "following::div[contains(@class, 'layout-cell-12 data-cell')]")
        print("Container encontrado:", container.get_attribute("outerHTML")[:300])
        
        # Dentro do container, busca o primeiro <div> com a classe "layout-cell-pad-5"
        info_div = container.find_element(By.CLASS_NAME, "layout-cell-pad-5")
        texto_extraido = info_div.text
        print("Texto extraído do info_div:")
        print(texto_extraido)
        
        linhas = texto_extraido.splitlines()
        print("Linhas extraídas:", linhas)
        
        if len(linhas) < 3:
            print("Informações insuficientes extraídas.")
            return {}
        
        titulacao = linhas[0]
        instituicao = linhas[1]
        orientador = "Não encontrado"
        for linha in linhas:
            if linha.startswith("Orientador:"):
                orientador = linha.split("Orientador:")[-1].strip()
                break

        return {
            "titulacao": titulacao,
            "instituicao": instituicao,
            "orientador": orientador
        }
    except Exception as e:
        print("Erro durante a extração com Selenium:", e)
        return {}

def main():
    # Configuração das opções do Chrome
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    # Não usar modo headless para que seja possível resolver o CAPTCHA
    # chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # URL do currículo Lattes (exemplo: Valter Fernandes Avelino)
    url = "http://lattes.cnpq.br/8003431098276221"
    driver.get(url)
    
    print("Caso apareça um CAPTCHA, por favor, resolva-o manualmente no navegador.")
    input("Depois de resolver o CAPTCHA e a página estiver carregada, pressione Enter para continuar...")

    info = extrair_info_lattes(driver)
    print("\n=== Informações Extraídas ===")
    print("Titulação/Formação Acadêmica:", info.get("titulacao"))
    print("Instituição Acadêmica:", info.get("instituicao"))
    print("Orientador:", info.get("orientador"))
    
    time.sleep(5)  # Tempo para visualização dos dados extraídos
    driver.quit()

if __name__ == "__main__":
    main()
