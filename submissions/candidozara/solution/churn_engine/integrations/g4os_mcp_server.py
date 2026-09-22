"""
Servidor MCP (stdio) do churn_engine, para o G4 OS (ou qualquer agente
compatível com MCP) acoplar via "source" do tipo mcp/stdio.

Isto dá ao agente do G4 OS acesso DIRETO ao motor, como ferramentas
tipadas -- não é "leia o README e adivinhe o comando", é chamada de função:

    rodar_diagnostico(...)            -> executa main.py e resume o resultado
    listar_contas_risco(...)          -> le risco_churn_api.json
    obter_segmentos_risco(...)        -> le segmentos_risco.csv
    obter_metricas_modelo(...)        -> le metricas_modelo.json
    sugerir_mapeamento_coluna(...)    -> mapeamento De/Para pra uma fonte nova
    decidir_acoes_recomendadas(...)   -> camada de decisao (simulada ou com IA real)
    validar_saida(...)                -> roda as 18 checagens de qualidade

Cada ferramenta le/escreve só dentro da pasta do projeto -- nunca fora
dela, nunca no sistema, nunca sem que o caminho seja explicito. Nenhuma
ferramenta manda e-mail, abre ticket ou aplica desconto: a camada de
execucao de verdade continua sendo uma pessoa.

Uso (registrado como source "local command / stdio" no G4 OS):
    command: python
    args: ["integrations/g4os_mcp_server.py"]
    cwd: <pasta do churn_engine>

Rodar sozinho pra testar (sem G4 OS):
    python integrations/g4os_mcp_server.py
    (fica esperando um cliente MCP conectar via stdio -- Ctrl+C pra sair)
"""

import json
import os
import subprocess
import sys

# Garante que "import sugerir_mapping" e "import demo_ia_gestao" funcionem
# não importa de onde o G4 OS chamar este script.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP  # noqa: E402

import sugerir_mapping  # noqa: E402
import demo_ia_gestao  # noqa: E402

mcp = FastMCP("churn-engine")


def _output_path(output_dir: str, *parts: str) -> str:
    return os.path.join(PROJECT_ROOT, output_dir, *parts)


@mcp.tool()
def rodar_diagnostico(
    config: str = "configs/mapping_ravenstack.json",
    accounts: str = "",
    subscriptions: str = "",
    usage: str = "",
    tickets: str = "",
    churn: str = "",
    output_dir: str = "outputs",
) -> dict:
    """Roda o motor de diagnostico de churn (main.py) contra uma fonte de dados
    e devolve um resumo (taxa de churn, MRR perdido, qualidade do modelo).
    Deixe accounts/subscriptions/usage/tickets/churn em branco para usar os
    caminhos padrao (dataset de exemplo RavenStack)."""
    args = [sys.executable, "main.py", "--config", config, "--output-dir", output_dir]
    for flag, valor in [
        ("--accounts", accounts), ("--subscriptions", subscriptions),
        ("--usage", usage), ("--tickets", tickets), ("--churn", churn),
    ]:
        if valor:
            args += [flag, valor]

    resultado = subprocess.run(args, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=300)
    if resultado.returncode != 0:
        return {"sucesso": False, "erro": resultado.stderr[-2000:]}

    metricas_path = _output_path(output_dir, "processed", "metricas_modelo.json")
    metricas = {}
    if os.path.exists(metricas_path):
        with open(metricas_path, "r", encoding="utf-8") as f:
            metricas = json.load(f)

    return {
        "sucesso": True,
        "output_dir": output_dir,
        "log": resultado.stdout[-1500:],
        "metricas_modelo": metricas,
    }


@mcp.tool()
def listar_contas_risco(output_dir: str = "outputs", top_n: int = 20, risco_minimo: int = 0) -> list:
    """Lista as contas ATIVAS com maior risco de churn (score de regra, 0-100),
    ordenadas do maior risco pro menor. Use para priorizar quais contas o time
    de Customer Success deve olhar primeiro."""
    caminho = _output_path(output_dir, "processed", "risco_churn_api.json")
    if not os.path.exists(caminho):
        return [{"erro": f"Nao encontrei {caminho}. Rode rodar_diagnostico primeiro."}]
    with open(caminho, "r", encoding="utf-8") as f:
        contas = json.load(f)
    contas = [c for c in contas if c.get("risco_score_regra", 0) >= risco_minimo]
    return contas[:top_n]


@mcp.tool()
def obter_segmentos_risco(output_dir: str = "outputs") -> list:
    """Devolve a taxa de churn por segmento (industria, canal de aquisicao,
    plano) -- usado para identificar QUAIS grupos de clientes estao mais em
    risco, nao so quais contas individuais."""
    import pandas as pd
    caminho = _output_path(output_dir, "processed", "segmentos_risco.csv")
    if not os.path.exists(caminho):
        return [{"erro": f"Nao encontrei {caminho}. Rode rodar_diagnostico primeiro."}]
    return pd.read_csv(caminho).to_dict(orient="records")


@mcp.tool()
def obter_metricas_modelo(output_dir: str = "outputs") -> dict:
    """Devolve a qualidade do modelo preditivo (ROC-AUC validado por
    validacao cruzada) com uma interpretacao honesta -- inclusive quando o
    sinal e fraco. Use antes de confiar no score do modelo para qualquer
    decisao."""
    caminho = _output_path(output_dir, "processed", "metricas_modelo.json")
    if not os.path.exists(caminho):
        return {"erro": f"Nao encontrei {caminho}. Rode rodar_diagnostico primeiro."}
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


@mcp.tool()
def sugerir_mapeamento_coluna(tabela: str, csv_path: str) -> dict:
    """Sugere automaticamente o mapeamento De/Para (nomes de coluna reais ->
    nomes canonicos) para uma fonte de dados NOVA, antes de rodar o
    diagnostico. tabela deve ser: accounts, subscriptions, usage, tickets ou
    churn. Colunas com confianca baixa vem marcadas para revisao humana --
    nunca aplicadas silenciosamente."""
    import pandas as pd
    caminho_completo = csv_path if os.path.isabs(csv_path) else os.path.join(PROJECT_ROOT, csv_path)
    df_amostra = pd.read_csv(caminho_completo, nrows=5)
    sugestoes = sugerir_mapping.sugerir_para_tabela(list(df_amostra.columns), tabela)
    return {
        "tabela": tabela,
        "sugestoes": sugestoes,
        "auto_aceitas": sum(1 for s in sugestoes if s["auto_aceito"]),
        "precisam_revisao": sum(1 for s in sugestoes if s["precisa_revisao_humana"]),
    }


@mcp.tool()
def decidir_acoes_recomendadas(output_dir: str = "outputs", top_n: int = 10, usar_ia_real: bool = False) -> list:
    """Decide uma acao recomendada por conta em risco (contato do CS,
    escalar para engenharia, revisar SLA, etc.), com urgencia e motivos.
    usar_ia_real=False (padrao) usa regras deterministicas simuladas, sem
    custo de API. usar_ia_real=True tenta usar a API da Anthropic de
    verdade (precisa de ANTHROPIC_API_KEY no ambiente do G4 OS) e cai pro
    modo simulado automaticamente se nao tiver chave. NUNCA executa a acao
    sozinho -- so decide e devolve a recomendacao."""
    contas = listar_contas_risco(output_dir=output_dir, top_n=top_n)
    if contas and "erro" in contas[0]:
        return contas
    resultados = []
    for conta in contas:
        decisao = (
            demo_ia_gestao.decidir_acao_real(conta) if usar_ia_real
            else demo_ia_gestao.decidir_acao_mock(conta)
        )
        resultados.append({
            "conta": conta.get("canonical_name", conta.get("canonical_id")),
            "score": conta.get("risco_score_regra"),
            **decisao,
        })
    return resultados


@mcp.tool()
def validar_saida(output_dir: str = "outputs") -> dict:
    """Roda as checagens automaticas de qualidade sobre a saida do motor
    (existencia dos arquivos, contagens, JSON ordenado, PDF legivel, etc.).
    Use depois de rodar_diagnostico para confirmar que os resultados sao
    confiaveis antes de repassar para outra pessoa ou sistema."""
    resultado = subprocess.run(
        [sys.executable, "validar_outputs.py", "--output-dir", output_dir],
        cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60,
    )
    return {
        "sucesso": resultado.returncode == 0,
        "saida": resultado.stdout[-3000:],
        "erro": resultado.stderr[-1000:] if resultado.returncode != 0 else None,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
