import os
import re

docentes_dir = "docentes"
saida = "docentes-fei.list"
linhas_novas = []

# Lista de títulos a remover
titulos = [
    "prof.", "profª.", "profº.", "prof", "profª", "profº",
    "dr.", "dra.", "dr", "dra", "msc.", "msc", "phd", "doutor", "doutora",
    "me"
]

def limpa_nome(nome):
    nome = nome.lower()
    for titulo in titulos:
        nome = re.sub(rf"\b{re.escape(titulo)}\b", "", nome)
    nome = re.sub(r"\d+", "", nome)
    nome = re.sub(r"[^\w\s-]", "", nome)
    nome = re.sub(r"\s+", " ", nome).strip()
    nome = nome.replace(" ", "-")
    return nome

for filename in os.listdir(docentes_dir):
    if filename.endswith(".list"):
        path = os.path.join(docentes_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            for linha in f:
                partes = linha.strip().split(",")
                if len(partes) > 1:
                    nome = limpa_nome(partes[1].strip())
                    nova_linha = f"{nome}\n"
                    linhas_novas.append(nova_linha)
                else:
                    # Se não houver vírgula, tenta limpar a linha inteira
                    nome = limpa_nome(linha.strip())
                    if nome:
                        linhas_novas.append(f"{nome}\n")

with open(saida, "w", encoding="utf-8") as f:
    f.writelines(linhas_novas)