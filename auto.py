import pdfplumber
import json

def extrair_tabela_pdf(pdf_path):
    # Abre o PDF
    with pdfplumber.open(pdf_path) as pdf:
        tabela = []
        
        # Itera sobre as páginas do PDF
        for page in pdf.pages:
            # Extrai a tabela da página
            tabelas = page.extract_tables()

            for tabela_page in tabelas:
                for linha in tabela_page:
                    # Verifica se a linha tem o número esperado de colunas (Nome, Departamento, Link)
                    if len(linha) >= 3:
                        nome_docente = linha[0].strip()
                        departamento = linha[1].strip()
                        link_lattes = linha[2].strip()
                        
                        # Adiciona as informações na lista
                        tabela.append({
                            "docente": nome_docente,
                            "departamento": departamento,
                            "link_lattes": link_lattes
                        })
    
    return tabela

def criar_json_com_tabela(pdf_path, json_path):
    # Extrai a tabela do PDF
    tabela = extrair_tabela_pdf(pdf_path)
    
    # Cria o dicionário com a lista de docentes
    dados = {
        "Semente": tabela
    }
    
    # Salva os dados no formato JSON
    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(dados, json_file, ensure_ascii=False, indent=4)

# Caminhos dos arquivos PDF e JSON
pdf_path = "docentes_cc.pdf"  # Substitua pelo caminho do seu arquivo PDF
json_path = "docentes-cc.json"  # Caminho para salvar o arquivo JSON

# Cria o JSON com os dados extraídos
criar_json_com_tabela(pdf_path, json_path)
