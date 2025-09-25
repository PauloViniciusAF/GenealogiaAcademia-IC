import unicodedata

def normalizar_nome(nome: str) -> str:
    # converte para minúsculas
    nome = nome.lower()
    # remove acentos
    nome = ''.join(
        c for c in unicodedata.normalize('NFD', nome)
        if unicodedata.category(c) != 'Mn'
    )
    # substitui espaços por hífens
    nome = nome.replace(" ", "-")
    # remove caracteres que não sejam letras, números ou hífen
    nome = ''.join(c for c in nome if c.isalnum() or c == "-")
    return nome

def processar_arquivo(entrada: str, saida: str):
    with open(entrada, "r", encoding="utf-8") as f:
        nomes = f.readlines()

    nomes_formatados = [normalizar_nome(n.strip()) for n in nomes if n.strip()]

    with open(saida, "w", encoding="utf-8") as f:
        f.write("\n".join(nomes_formatados))

if __name__ == "__main__":
    processar_arquivo("docentes-usp.list", "docentes-usp-formatados.list")
    print("Arquivo convertido com sucesso!")