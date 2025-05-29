import json
import csv
from collections import defaultdict

# Carregar o novo arquivo JSON
with open('tabelas/exemplo-area-table.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Dicionário para armazenar relações de influência
relacoes = defaultdict(lambda: defaultdict(int))

# Processar cada entrada do JSON
for entry in data:
    # Extrair área do orientador
    orientador = entry['p']['properties']
    grande_area_orientador = orientador.get('grandeArea')
    if not grande_area_orientador or not str(grande_area_orientador).strip():
        grande_area_orientador = 'Área não informada'
    
    # Extrair área do orientado
    orientado = entry['orientado']['properties']
    grande_area_orientado = orientado.get('grandeArea')
    if not grande_area_orientado or not str(grande_area_orientado).strip():
        grande_area_orientado = 'Área não informada'

    relacoes[grande_area_orientador][grande_area_orientado] += 1

# Gerar lista de resultados
resultado = []
for area_orientador, influencias in relacoes.items():
    for area_orientado, quantidade in influencias.items():
        resultado.append({
            'Área Influenciadora': area_orientador,
            'Área Influenciada': area_orientado,
            'Ocorrências': quantidade
        })

# Ordenar por número de ocorrências
resultado_ordenado = sorted(resultado, key=lambda x: x['Ocorrências'], reverse=True)

# Salvar em CSV
with open('relacoes_influencia_areas-tradadas.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Área Influenciadora', 'Área Influenciada', 'Ocorrências']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in resultado_ordenado:
        writer.writerow(row)

print("Arquivo 'relacoes_influencia_areas.csv' gerado com sucesso!")
