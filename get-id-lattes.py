import requests
from bs4 import BeautifulSoup

def parse_lattes_url(lattes_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    
    # Realiza a requisição HTTP para obter o conteúdo da página com cabeçalho de User-Agent
    response = requests.get(lattes_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Erro ao acessar o Lattes: {lattes_url}")
        return None

    # Usa BeautifulSoup para parsear o conteúdo HTML
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Cria um dicionário para armazenar as informações extraídas
    data = {}

    # Nome do titular do currículo
    name_tag = soup.find('span', {'class': 'nome'})
    if name_tag:
        data['nome'] = name_tag.get_text(strip=True)

    # Titulação
    titulation_tag = soup.find('span', {'class': 'titulacao'})
    if titulation_tag:
        data['titulacao'] = titulation_tag.get_text(strip=True)

    # Formação acadêmica e informações sobre a instituição e orientador
    education_section = soup.find_all('section', {'class': 'titulo_secao'})
    for section in education_section:
        if "Formação Acadêmica" in section.get_text():
            # Dentro dessa seção, procure detalhes como curso, instituição e orientador
            education_details = section.find_next('div', {'class': 'dados_secao'})
            if education_details:
                for item in education_details.find_all('p'):
                    if "Instituição:" in item.get_text():
                        data['instituicao'] = item.get_text(strip=True).replace("Instituição:", "").strip()
                    if "Orientador:" in item.get_text():
                        data['orientador'] = item.get_text(strip=True).replace("Orientador:", "").strip()

    return data

def parse_multiple_lattes(urls):
    # Recebe uma lista de URLs do Lattes e retorna um dicionário com todas as informações
    parsed_data = []
    for url in urls:
        data = parse_lattes_url(url)
        if data:
            parsed_data.append(data)
    return parsed_data

# Lista de links do Lattes
lattes_links = [
    "https://lattes.cnpq.br/1234567890123456",  # Substitua com links reais
    "https://lattes.cnpq.br/6543210987654321",
    "http://lattes.cnpq.br/2252524078791196",
    "http://lattes.cnpq.br/1299755265131677",
    "http://lattes.cnpq.br/2737250182959127",
    "http://lattes.cnpq.br/4313823172445184",
    "http://lattes.cnpq.br/9168416334175028"
]

# Chama a função para processar os links
curriculos = parse_multiple_lattes(lattes_links)

# Exibe os resultados
for curriculo in curriculos:
    print(curriculo)
