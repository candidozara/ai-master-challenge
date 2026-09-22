"""
Lê CSV, Excel (.xlsx/.xls) ou JSON (lista de registros) e devolve sempre um
DataFrame -- usado tanto pelo painel gráfico (arquivo enviado no upload, tem
`.name`) quanto pelo menu de terminal (caminho de arquivo em disco), pra não
ter duas versões da mesma lógica de leitura.

Isto resolve "meus arquivos não são todos CSV" -- mas só até onde dá pra
fazer de forma confiável: CSV, Excel e JSON são formatos tabulares (uma
lista de registros), então convertem pra tabela sem ambiguidade. Um dump
`.sql` ou um `.pdf` NÃO entram aqui de propósito: extrair uma tabela de um
PDF é uma heurística visual que erra fácil (colunas que se misturam, texto
que quebra em duas linhas...), e um dump SQL pode ter qualquer estrutura --
os dois merecem uma conversa específica antes de virar código, não uma
suposição.
"""

import json

import pandas as pd

FORMATOS_SUPORTADOS = ["csv", "xlsx", "xls", "json"]


def ler_qualquer_formato(origem) -> pd.DataFrame:
    """
    `origem` pode ser um caminho de arquivo (str) ou um arquivo enviado no
    Streamlit (tem `.name` e é lido como stream). Decide o formato pelo
    nome do arquivo.
    """
    nome = getattr(origem, "name", None) or str(origem)
    nome = nome.lower()

    if nome.endswith(".csv"):
        return pd.read_csv(origem)
    if nome.endswith((".xlsx", ".xls")):
        return pd.read_excel(origem)
    if nome.endswith(".json"):
        arquivo_texto = origem if hasattr(origem, "read") else open(origem, "r", encoding="utf-8")
        try:
            dados = json.load(arquivo_texto)
        finally:
            if not hasattr(origem, "read"):
                arquivo_texto.close()
        if isinstance(dados, dict):
            # Alguns exports vêm como {"registros": [...]} em vez de uma lista
            # direto -- pega a primeira lista que achar dentro do dict.
            for valor in dados.values():
                if isinstance(valor, list):
                    dados = valor
                    break
        return pd.DataFrame(dados)

    raise ValueError(f"Formato de \"{nome}\" não suportado -- use CSV, Excel (.xlsx/.xls) ou JSON.")
