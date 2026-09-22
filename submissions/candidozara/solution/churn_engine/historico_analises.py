"""
Registro das análises rodadas pelo painel gráfico -- cada vez que você roda
o diagnóstico com dados próprios pela aba "Meus dados", uma entrada nova
é adicionada aqui. É isso que alimenta a lista "tipo conversas" na barra
lateral do painel: clicar numa análise antiga mostra de novo o painel
inteiro (KPIs, segmentos, score) da forma como ficou naquela rodada,
incluindo as ações de IA que tiverem sido salvas pra ela.

Fica em configs/historico_analises.json -- só o painel (dashboard.py) lê e
escreve nesse arquivo. Pastas antigas rodadas pelo terminal (outputs/,
outputs_fonte_b/, etc.) não entram aqui automaticamente -- continuam
acessíveis pelo modo "Avançado" do painel, só não viram uma "análise" com
nome e data.
"""

import json
import os
from datetime import datetime

CAMINHO_REGISTRO = os.path.join("configs", "historico_analises.json")


def carregar_historico() -> list:
    """Devolve a lista de análises, mais recente primeiro. Lista vazia se
    o arquivo não existe ainda ou está corrompido (não derruba o painel)."""
    if not os.path.exists(CAMINHO_REGISTRO):
        return []
    try:
        with open(CAMINHO_REGISTRO, "r", encoding="utf-8") as f:
            historico = json.load(f)
        return sorted(historico, key=lambda a: a.get("data_criacao", ""), reverse=True)
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def salvar_historico(historico: list):
    os.makedirs(os.path.dirname(CAMINHO_REGISTRO), exist_ok=True)
    with open(CAMINHO_REGISTRO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def registrar_analise(nome: str, output_dir: str, resumo_fonte: str) -> dict:
    """Cria e salva uma nova entrada de análise, devolvendo ela pronta pra
    já ativar no painel (sem precisar reler o arquivo)."""
    agora = datetime.now()
    entrada = {
        "id": agora.strftime("%Y%m%d_%H%M%S"),
        "nome": nome.strip() or f"Análise {agora.strftime('%d/%m %H:%M')}",
        "data_criacao": agora.isoformat(timespec="seconds"),
        "output_dir": output_dir,
        "resumo_fonte": resumo_fonte,
    }
    historico = carregar_historico()
    historico.append(entrada)
    salvar_historico(historico)
    return entrada


def atualizar_analise(analise_id: str, resumo_fonte: str = None, nome: str = None) -> dict:
    """
    Atualiza uma análise JÁ EXISTENTE no lugar (mesmo id, mesma pasta) em
    vez de criar uma nova -- usado quando a pessoa manda dados novos
    "na mesma sessão" (botão Rodar de novo nesta análise) em vez de
    começar uma análise separada. Atualiza a data pra agora, pra subir
    pro topo da lista.
    """
    historico = carregar_historico()
    entrada_atualizada = None
    for a in historico:
        if a["id"] == analise_id:
            a["data_criacao"] = datetime.now().isoformat(timespec="seconds")
            if resumo_fonte is not None:
                a["resumo_fonte"] = resumo_fonte
            if nome:
                a["nome"] = nome.strip() or a["nome"]
            entrada_atualizada = a
    salvar_historico(historico)
    return entrada_atualizada


def remover_analise(analise_id: str):
    """Remove a entrada do registro (não mexe na pasta em disco -- quem
    chama decide se também apaga os arquivos)."""
    historico = carregar_historico()
    historico_novo = [a for a in historico if a["id"] != analise_id]
    salvar_historico(historico_novo)


def buscar_analise(analise_id: str) -> dict:
    """Devolve a entrada com esse id, ou None se não existir."""
    for a in carregar_historico():
        if a["id"] == analise_id:
            return a
    return None
