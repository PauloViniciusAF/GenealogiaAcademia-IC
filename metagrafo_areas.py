from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import json

# Carrega variáveis de ambiente
load_dotenv()
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
driver = GraphDatabase.driver(URI, auth=AUTH)

def cria_area(tx, area):
    query = """
    MERGE (a:Area {nome: $area})
    """
    tx.run(query, area=area)

def cria_relacao_area(tx, area1, area2):
    query = """
    MATCH (a:Area {nome: $area1})
    MATCH (b:Area {nome: $area2})
    MERGE (a)-[:INFLUENCIA]->(b)
    """
    tx.run(query, area1=area1, area2=area2)

def main():
    with open("pesquisadores-extraidos.json", "r", encoding="utf-8") as f:
        pesquisadores = json.load(f)

    areas_set = set()
    relacoes = set()

    # Cria vértices de áreas e relações de influência
    for nome, dados in pesquisadores.items():
        area_pesq = dados.get("grande-area", "").strip()
        asc = dados.get("ascendentes", "")
        if not area_pesq:
            continue
        areas_set.add(area_pesq)
        # Se o ascendente existe e está no JSON, cria relação de influência
        if asc and asc in pesquisadores:
            area_asc = pesquisadores[asc].get("grande-area", "").strip()
            if area_asc and area_asc != area_pesq:
                areas_set.add(area_asc)
                relacoes.add((area_asc, area_pesq))

    with driver.session() as session:
        # Cria vértices de áreas
        for area in areas_set:
            session.write_transaction(cria_area, area)
        # Cria arestas de influência
        for area1, area2 in relacoes:
            session.write_transaction(cria_relacao_area, area1, area2)

    print("Metagrafo de áreas criado no Neo4j.")

if __name__ == "__main__":
    main()