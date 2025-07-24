from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import json

# Carrega variáveis de ambiente
load_dotenv()
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))

driver = GraphDatabase.driver(URI, auth=AUTH)

def create_pesquisador(tx, nome, grande_area, universidade):
    query = """
    MERGE (p:Pesquisador {nome: $nome})
    SET p.grandeArea = $grande_area,
        p.universidade = $universidade
    """
    tx.run(query, nome=nome, grande_area=grande_area, universidade=universidade)

def cria_relacao(tx, nome1, nome2, relacao):
    query = f"""
    MATCH (a:Pesquisador {{nome: $nome1}})
    MATCH (b:Pesquisador {{nome: $nome2}})
    MERGE (a)-[:{relacao.upper()}]->(b)
    """
    tx.run(query, nome1=nome1, nome2=nome2)

def main():
    with open("pesquisadores-extraidos.json", "r", encoding="utf-8") as f:
        pesquisadores = json.load(f)

    with driver.session() as session:
        # Cria vértices
        for nome, dados in pesquisadores.items():
            grupo = dados.get("grupo", "")
            grande_area = dados.get("grande-area", "")
            universidade = dados.get("universidade", "")
            session.write_transaction(create_pesquisador, nome, grupo, grande_area, universidade)

        # Cria relações ascendentes
        for nome, dados in pesquisadores.items():
            asc = dados.get("ascendentes", "")
            if asc and asc in pesquisadores:
                session.write_transaction(cria_relacao, nome, asc, "ASCENDENTE")
            # Cria relações descendentes
            for desc in dados.get("descendentes", []):
                if desc and desc in pesquisadores:
                    session.write_transaction(cria_relacao, nome, desc, "DESCENDENTE")

    print("Importação concluída.")

if __name__ == "__main__":
    main()