import json
import csv
from collections import defaultdict


with open('tabelas/exemplo-geral-table.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

relacoes = defaultdict(lambda: defaultdict(int))

for entry in data:
    try:
        # Obter informações do orientador (start node)
        orientador = entry['p']['start']['properties']
        grande_area_orientador = orientador.get('grandeArea')
        if not grande_area_orientador:
            grande_area_orientador = orientador.get('area')
        if not grande_area_orientador:
            grande_area_orientador = 'Área não informada'

        # Obter informações do orientado (end node)
        orientado = entry['p']['end']['properties']
        grande_area_orientado = orientado.get('grandeArea')
        if not grande_area_orientado:
            grande_area_orientado = orientado.get('area')
        if not grande_area_orientado:
            grande_area_orientado = 'Área não informada'
       
        # Contabilizar a relação
        relacoes[grande_area_orientador][grande_area_orientado] += 1
        
    except KeyError:
        continue
    
resultado = []
for area_orientador, influencias in relacoes.items():
    for area_orientado, quantidade in influencias.items():
        resultado.append({
            'Área Influenciadora': area_orientador,
            'Área Influenciada': area_orientado,
            'Ocorrências': quantidade
        })


resultado_ordenado = sorted(resultado, key=lambda x: x['Ocorrências'], reverse=True)


with open('relacoes_influencia_areas.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Área Influenciadora', 'Área Influenciada', 'Ocorrências']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in resultado_ordenado:
        # Não há filtro, salva todas as relações, mesmo as não informadas
        writer.writerow(row)

print("Arquivo CSV 'relacoes_influencia_areas.csv' gerado com sucesso!")