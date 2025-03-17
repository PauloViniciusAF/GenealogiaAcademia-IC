import json
from playwright.sync_api import sync_playwright, TimeoutError

def read_json(filename):
    """
    Lê o arquivo JSON e retorna os dados. Se o arquivo não existir ou ocorrer erro, retorna dicionário vazio.
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
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

def extract_lattes_info(page, docente_id):
    """
    Extrai informações da página Lattes.
    - Nome: localizado em um elemento <h2> com classe "nome"
    - Instituição do doutorado: procurado na seção de formação acadêmica
    - Orientador: extraído se houver a string "Orientador:" na mesma seção
    Retorna um dicionário com os dados extraídos e o id do orientador (se encontrado).
    """
    info = {}
    # Extrair o nome do pesquisador
    try:
        nome_elem = page.wait_for_selector("h2.nome", timeout=20000)
        nome = nome_elem.text_content().strip() if nome_elem else ""
        info["Nome"] = nome
    except TimeoutError:
        print("Erro: Nome não encontrado na página.")
        info["Nome"] = ""
    
    # Constrói o link lattes com base no ID informado, não utilizando a URL atual
    info["link_lattes"] = f"http://lattes.cnpq.br/{docente_id}"

    # Inicializa campos vazios
    info["Instituição_doutorado"] = ""
    orientador_id = ""

    try:
        # Espera pela seção de formação acadêmica
        anchor = page.wait_for_selector("a[name='FormacaoAcademicaTitulacao']", timeout=40000)
        container = anchor.locator("xpath=following-sibling::div[contains(@class, 'layout-cell-12 data-cell')]")
        blocks = container.locator(".layout-cell-pad-5")
        count = blocks.count()
        for i in range(count):
            block_text = blocks.nth(i).text_content()
            if "Doutorado" in block_text:
                parts = block_text.split('.')
                if len(parts) >= 2:
                    info["Instituição_doutorado"] = parts[1].strip()
                if "Orientador:" in block_text:
                    orientador_parts = block_text.split("Orientador:")
                    if len(orientador_parts) >= 2:
                        orientador_id = orientador_parts[1].strip().split()[0]
                break
    except TimeoutError:
        print("Erro: Seção de Formação Acadêmica não encontrada.")

    info["orientador_id"] = orientador_id
    return info

def main():
    # Solicita que o usuário informe o ID Lattes (pivô)
    pivot_id = input("Digite o ID Lattes para extrair as informações: ").strip()
    if not pivot_id:
        print("ID inválido!")
        return

    url = f"http://lattes.cnpq.br/{pivot_id}"
    
    with sync_playwright() as p:
        # Abre o navegador (modo não headless para possibilitar a resolução do CAPTCHA)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        print(f"Acessando: {url}")
        page.goto(url)
        print("Caso apareça um CAPTCHA, por favor, resolva-o manualmente no navegador.")
        input("Após resolver o CAPTCHA e a página carregar completamente, pressione Enter para continuar...")

        # Extrai as informações da página, passando o ID do docente
        lattes_info = extract_lattes_info(page, pivot_id)
        browser.close()

    # Cria o registro no formato do arquivo registro_lattes.json
    registro = {
        pivot_id: {
            "role": "docente",
            "link_lattes": lattes_info.get("link_lattes", ""),
            "Instituição_doutorado": lattes_info.get("Instituição_doutorado", ""),
            "id_pai": "",
            "Nome": lattes_info.get("Nome", ""),
            "orientações": {
                "Nome" : "",
                "id_lattes" : lattes_info.get("orientador_id", ""),
                "Instituição_doutorado" : ""
            }
        }
    }

    # Lê os registros existentes (se houver) e atualiza com o novo dado
    filename = "registro_lattes.json"
    existing_data = read_json(filename)
    existing_data.update(registro)
    write_json(filename, existing_data)

if __name__ == "__main__":
    main()
