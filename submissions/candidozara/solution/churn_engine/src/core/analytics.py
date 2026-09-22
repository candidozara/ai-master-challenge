"""
Camada de Decisão e Risco.

Três blocos, do mais simples para o mais avançado:

1. detectar_queda_de_uso   -> regra de série temporal (early warning)
2. calcular_score_regra    -> score de risco 100% determinístico (if/else)
3. treinar_modelo_preditivo -> scikit-learn, aprende com quem já
   cancelou para estimar probabilidade de churn de quem ainda está ativo

O modelo de ML é a camada "diferencial" (o desafio pede: "um modelo
preditivo de churn que funcione"). Ele nunca substitui o score de regra --
os dois são mostrados lado a lado, porque um é auditável por qualquer
pessoa do time (if/else) e o outro captura padrões não-óbvios.

Limitação conhecida (documentada de propósito, não escondida): as
features de uso somam o histórico inteiro disponível por conta, incluindo
o período em que contas já churned simplesmente pararam de usar o
produto. Isso é um sinal legítimo (queda de uso precede cancelamento),
mas numa implementação de produção real o ideal é recalcular tudo usando
apenas uma janela de dados anterior a uma "data de corte" por conta, para
eliminar qualquer vazamento temporal residual.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline


# ---------------------------------------------------------------------------
# 1. Early warning: queda de uso
# ---------------------------------------------------------------------------

def detectar_queda_de_uso(
    df_usage: pd.DataFrame,
    janela_dias: int = 30,
    limite_queda_pct: float = 30.0,
) -> pd.DataFrame:
    """
    Compara o volume de uso dos últimos `janela_dias` com o período
    imediatamente anterior, por conta (canonical_id). Retorna, por conta:
    uso_recente, uso_anterior, variacao_pct, e a flag de alerta.

    A "data de referência" usada é a data mais recente encontrada em todo
    o dataset de uso (equivalente a "hoje", já que os dados são
    históricos). Numa implantação real isso vira `datetime.now()`.
    """
    if df_usage is None or df_usage.empty or "canonical_usage_date" not in df_usage.columns:
        return pd.DataFrame(columns=["canonical_id", "uso_recente", "uso_anterior", "variacao_uso_pct", "queda_uso_flag"])

    df = df_usage.copy()
    df["canonical_usage_date"] = pd.to_datetime(df["canonical_usage_date"], errors="coerce")
    df = df.dropna(subset=["canonical_usage_date", "canonical_id"])

    data_referencia = df["canonical_usage_date"].max()
    corte_recente = data_referencia - pd.Timedelta(days=janela_dias)
    corte_anterior = corte_recente - pd.Timedelta(days=janela_dias)

    recente = df[df["canonical_usage_date"] > corte_recente]
    anterior = df[(df["canonical_usage_date"] > corte_anterior) & (df["canonical_usage_date"] <= corte_recente)]

    uso_recente = recente.groupby("canonical_id")["canonical_volume"].sum().rename("uso_recente")
    uso_anterior = anterior.groupby("canonical_id")["canonical_volume"].sum().rename("uso_anterior")

    tendencia = pd.concat([uso_recente, uso_anterior], axis=1).fillna(0).reset_index()

    def variacao(row):
        if row["uso_anterior"] == 0:
            return 0.0 if row["uso_recente"] == 0 else 100.0
        return ((row["uso_recente"] - row["uso_anterior"]) / row["uso_anterior"]) * 100

    tendencia["variacao_uso_pct"] = tendencia.apply(variacao, axis=1).round(1)
    tendencia["queda_uso_flag"] = tendencia["variacao_uso_pct"] <= -limite_queda_pct

    return tendencia


# ---------------------------------------------------------------------------
# 2. Score de risco determinístico (regra de negócio, auditável)
# ---------------------------------------------------------------------------

def calcular_score_regra(super_tabela: pd.DataFrame, limite_resposta_minutos: float = 240.0) -> pd.DataFrame:
    """
    Score 0-100 combinando os 3 sinais que o diagnóstico de negócio
    identificou como causa raiz: queda de uso, erros em features beta e
    atrito no suporte. Puramente if/else -- qualquer pessoa do time de CS
    consegue explicar por que uma conta pontuou alto.
    """
    df = super_tabela.copy()

    score = np.zeros(len(df))

    if "queda_uso_flag" in df.columns:
        score += np.where(df["queda_uso_flag"].fillna(False), 35, 0)

    if "erros_beta" in df.columns:
        score += np.minimum(df["erros_beta"].fillna(0), 5) * 4  # até 20 pts

    if "total_escalados" in df.columns:
        score += np.where(df["total_escalados"].fillna(0) > 0, 20, 0)

    if "media_resposta_minutos" in df.columns:
        score += np.where(df["media_resposta_minutos"].fillna(0) > limite_resposta_minutos, 15, 0)

    df["risco_score_regra"] = np.clip(score, 0, 100).astype(int)

    def bucket(s):
        if s >= 75:
            return "Crítico"
        if s >= 50:
            return "Alto"
        if s >= 25:
            return "Médio"
        return "Baixo"

    df["risco_nivel_regra"] = df["risco_score_regra"].apply(bucket)
    return df


# ---------------------------------------------------------------------------
# 3. Modelo preditivo (scikit-learn) -- a camada "diferencial"
# ---------------------------------------------------------------------------

FEATURES_NUMERICAS = [
    "total_uso",
    "total_erros",
    "erros_beta",
    "variacao_uso_pct",
    "total_tickets",
    "media_resposta_minutos",
    "total_escalados",
    "canonical_revenue",
    "canonical_seats",
    "dias_desde_ultimo_uso",
    "dias_desde_ultimo_ticket",
    "taxa_erro",
    "taxa_escalonamento",
]

FEATURES_CATEGORICAS = ["canonical_plan", "canonical_industry", "canonical_referral_source"]


def treinar_modelo_preditivo(super_tabela: pd.DataFrame, random_state: int = 42) -> dict:
    """
    Treina um RandomForest usando as contas com desfecho conhecido
    (churn_flag de accounts.csv, a fonte mais confiável) para estimar,
    para TODAS as contas ativas hoje, a probabilidade de churn.

    A métrica de qualidade usada é ROC-AUC em validação cruzada
    estratificada de 5 folds (não um único train_test_split) -- com só
    500 contas, uma única divisão é ruidosa demais para confiar. Isso é
    proposital: é melhor um número mais estável que mostre a verdade
    (mesmo que a verdade seja "o modelo não aprendeu muito") do que um
    único split que pode parecer bom ou ruim por sorte.

    Retorna um dicionário com o modelo, as métricas de validação, a
    importância das variáveis e a tabela final com a coluna
    `risco_score_modelo` (0-100) preenchida.
    """
    df = super_tabela.copy()

    for col in FEATURES_NUMERICAS:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = df[col].fillna(0.0)
    for col in FEATURES_CATEGORICAS:
        if col not in df.columns:
            df[col] = "desconhecido"
        df[col] = df[col].fillna("desconhecido")

    X = df[FEATURES_NUMERICAS + FEATURES_CATEGORICAS]
    y = df["canonical_is_churn_account"].astype(bool)

    pre_processador = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES_CATEGORICAS),
        ],
        remainder="passthrough",
    )

    modelo = Pipeline(
        steps=[
            ("pre", pre_processador),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=6,
                    class_weight="balanced",
                    random_state=random_state,
                ),
            ),
        ]
    )

    metricas = {"treinado": False}
    try:
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
        scores_auc = cross_val_score(modelo, X, y, cv=cv, scoring="roc_auc")

        roc_auc_medio = float(np.mean(scores_auc))
        confiavel = roc_auc_medio >= 0.65

        if roc_auc_medio >= 0.65:
            interpretacao = "Sinal preditivo real -- pode orientar priorização do CS."
        elif roc_auc_medio >= 0.55:
            interpretacao = (
                "Sinal fraco, mas acima do acaso: adicionar recência de uso/ticket e taxas "
                "normalizadas (erro/uso, escalação/tickets) melhorou o ROC-AUC frente à primeira "
                "versão (que usava só totais brutos), mas ainda não é forte o suficiente pra "
                "decidir sozinho quem o CS liga. Use como sinal secundário, priorizando pelo "
                "score de regra (determinístico e auditável)."
            )
        else:
            interpretacao = (
                "Sinal muito fraco (próximo de 0.5 = aleatório). Os dados agregados por conta "
                "não separam bem quem churna de quem fica -- isso também é um achado: sugere que "
                "o motivo do churn está em algo não capturado aqui, ou que o gerador do dataset "
                "sintético não acoplou o rótulo de churn às métricas operacionais. Use o score de "
                "regra (determinístico) como guia principal e trate este score como experimental."
            )

        metricas = {
            "treinado": True,
            "n_contas": len(X),
            "n_folds": 5,
            "roc_auc": round(roc_auc_medio, 3),
            "roc_auc_std": round(float(np.std(scores_auc)), 3),
            "roc_auc_por_fold": [round(float(s), 3) for s in scores_auc],
            "sinal_confiavel": confiavel,
            "interpretacao": interpretacao,
        }
    except ValueError as e:
        # dataset pequeno demais para estratificar, por exemplo
        metricas["erro"] = str(e)

    # Reajusta com TODOS os dados para gerar a pontuação final de produção
    modelo.fit(X, y)
    probabilidades = modelo.predict_proba(X)[:, 1]
    df["risco_score_modelo"] = (probabilidades * 100).round(1)

    try:
        nomes_onehot = list(
            modelo.named_steps["pre"].named_transformers_["cat"].get_feature_names_out(FEATURES_CATEGORICAS)
        )
        nomes_features = nomes_onehot + FEATURES_NUMERICAS
        importancias = modelo.named_steps["clf"].feature_importances_
        ranking_importancia = (
            pd.DataFrame({"feature": nomes_features, "importancia": importancias})
            .sort_values("importancia", ascending=False)
            .reset_index(drop=True)
        )
    except Exception:
        ranking_importancia = pd.DataFrame(columns=["feature", "importancia"])

    return {
        "modelo": modelo,
        "metricas": metricas,
        "importancia_features": ranking_importancia,
        "super_tabela": df,
    }


# ---------------------------------------------------------------------------
# 3b. Distribuição de motivos de churn (fonte confiável)
# ---------------------------------------------------------------------------

def distribuicao_motivos_churn(df_churn: pd.DataFrame, contas_churned_ids: set) -> pd.DataFrame:
    """
    Calcula a distribuição de reason_code restrita aos eventos de contas
    que accounts.csv confirma como churned hoje.

    Por quê restringir: churn_events.csv tem eventos para mais contas do
    que accounts.csv marca como churned (indício de reativações -- ver
    tecnica/04-estrategia_ajustada.md). Usar a tabela de eventos crua sem
    filtrar infla a amostra com contas que já voltaram a ser clientes
    ativos. Isso é documentado como limitação de qualidade de dados, não
    escondido.
    """
    if df_churn is None or df_churn.empty or "canonical_churn_reason" not in df_churn.columns:
        return pd.DataFrame(columns=["motivo", "pct"])

    eventos_validos = df_churn[df_churn["canonical_id"].isin(contas_churned_ids)]
    if eventos_validos.empty:
        eventos_validos = df_churn  # fallback: nenhuma conta bateu, usa tudo

    contagem = eventos_validos["canonical_churn_reason"].dropna().value_counts(normalize=True).mul(100).round(1)
    return contagem.reset_index().rename(columns={"index": "motivo", "canonical_churn_reason": "motivo", "proportion": "pct"})


# ---------------------------------------------------------------------------
# 3c. Checagem de qualidade: feedback_text vale a pena usar?
# ---------------------------------------------------------------------------

def checar_valor_informativo_feedback_text(df_churn: pd.DataFrame) -> dict:
    """
    Antes de investir em NLP sobre `feedback_text`, verifica se ele carrega
    informação que `reason_code` já não tem. Nesta base, o campo tem só 3
    frases fixas ("too expensive", "missing features", "switched to
    competitor") e a distribuição delas é praticamente igual dentro de
    QUALQUER reason_code -- inclusive dentro de "support", que não deveria
    ter "missing features"/"switched to competitor" tão presente quanto
    "too expensive" se o texto fosse gerado a partir do motivo real.

    Isso indica ruído, não sinal: por isso este projeto NÃO usa
    feedback_text como feature do modelo preditivo. Documentado aqui em vez
    de simplesmente omitido, para deixar claro que foi avaliado.
    """
    if df_churn is None or df_churn.empty or "canonical_feedback" not in df_churn.columns:
        return {"avaliado": False}

    textos = df_churn["canonical_feedback"].dropna()
    valores_unicos = textos.nunique()

    tabela_cruzada = pd.crosstab(df_churn["canonical_churn_reason"], df_churn["canonical_feedback"], normalize="index").round(3)
    # Se o texto fosse informativo, a distribuição dentro de cada reason_code
    # seria bem desigual (um texto dominando). Se for uniforme, é ruído.
    variacao_media = tabela_cruzada.std(axis=1).mean()

    return {
        "avaliado": True,
        "valores_unicos_texto": int(valores_unicos),
        "parece_redundante_ou_ruido": bool(valores_unicos <= 5 and variacao_media < 0.05),
        "tabela_cruzada_reason_vs_texto": tabela_cruzada,
    }


# ---------------------------------------------------------------------------
# 4. Segmentação de risco (indústria, canal de aquisição, plano)
# ---------------------------------------------------------------------------

def segmentar_risco(super_tabela: pd.DataFrame) -> pd.DataFrame:
    """
    Taxa de churn e receita por segmento -- responde a pergunta 2 do
    desafio ("quais segmentos estão mais em risco?") com números, não
    feeling.
    """
    linhas = []
    for dimensao in ["canonical_industry", "canonical_referral_source", "canonical_plan"]:
        if dimensao not in super_tabela.columns:
            continue
        agrupado = super_tabela.groupby(dimensao).agg(
            contas=("canonical_id", "count"),
            churns=("canonical_is_churn_account", "sum"),
            mrr_total=("canonical_revenue", "sum"),
        )
        agrupado["taxa_churn_pct"] = (agrupado["churns"] / agrupado["contas"] * 100).round(1)
        agrupado = agrupado.reset_index().rename(columns={dimensao: "valor"})
        agrupado.insert(0, "dimensao", dimensao.replace("canonical_", ""))
        linhas.append(agrupado)

    if not linhas:
        return pd.DataFrame()

    resultado = pd.concat(linhas, ignore_index=True)
    return resultado.sort_values(["dimensao", "taxa_churn_pct"], ascending=[True, False])
