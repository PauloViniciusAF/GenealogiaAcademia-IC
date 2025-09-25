def normalizar_nome(nome: str) -> str:
    nome = nome.lower()
    nome = nome.replace(" ", "-")
    return nome

def processar_arquivo(entrada: str, saida: str):
    with open(entrada, "r", encoding="utf-8") as f:
        nomes = f.readlines()

    nomes_formatados = [normalizar_nome(n.strip()) for n in nomes if n.strip()]

    with open(saida, "w", encoding="utf-8") as f:
        f.write("\n".join(nomes_formatados))

processar_arquivo("docentes-usp.list", "docentes-usp-formatados.list")
