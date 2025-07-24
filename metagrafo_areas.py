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

def cria_relacao_area(tx, area1, area2, peso):
    query = """
    MATCH (a:Area {nome: $area1})
    MATCH (b:Area {nome: $area2})
    MERGE (a)-[r:INFLUENCIA]->(b)
    SET r.peso = $peso
    """
    tx.run(query, area1=area1, area2=area2, peso=peso)

def main():
    with open("pesquisadores-extraidos.json", "r", encoding="utf-8") as f:
        pesquisadores = json.load(f)

    areas_set = set()
    relacoes = {}

    # Conta as influências entre áreas (incluindo laços)
    for nome, dados in pesquisadores.items():
        area_pesq = dados.get("grande-area", "").strip()
        asc = dados.get("ascendentes", "")
        if not area_pesq:
            continue
        areas_set.add(area_pesq)
        if asc and asc in pesquisadores:
            area_asc = pesquisadores[asc].get("grande-area", "").strip()
            if area_asc:
                areas_set.add(area_asc)
                key = (area_asc, area_pesq)
                relacoes[key] = relacoes.get(key, 0) + 1

    with driver.session() as session:
        # Cria vértices de áreas
        for area in areas_set:
            session.write_transaction(cria_area, area)
        # Cria arestas de influência ponderadas (incluindo laços)
        for (area1, area2), peso in relacoes.items():
            session.write_transaction(cria_relacao_area, area1, area2, peso)

    print("Metagrafo de áreas ponderado criado no Neo4j (incluindo laços de auto-influência).")

if __name__ == "__main__":
    main()