"""
Fase 2 (MVP): sugestão automática do arquivo De/Para.

Isto NÃO chama nenhuma API de IA generativa -- é heurística determinística
(comparação de nomes de coluna contra um dicionário de sinônimos + palavras-
chave), então roda offline, de graça, e sempre dá o mesmo resultado pro
mesmo input. É o "andar de bicicleta" antes de plugar um LLM: numa fase 3,
o mesmo lugar onde este script decide (a função `sugerir_para_tabela`)
poderia chamar a API da Anthropic pra resolver os casos de baixa confiança
-- a estrutura já separa "sugestão" de "aplicação", então trocar o motor de
sugestão não exige mexer no resto do pipeline.

Uso:
    python sugerir_mapping.py --tabela accounts --csv data/fonte_b/clientes.csv
    python sugerir_mapping.py --tabela subscriptions --csv data/fonte_b/planos.csv --saida configs/mapping_sugerido.json

Sempre revise o JSON gerado antes de usar em produção -- por isso ele nunca
sobrescreve configs/mapping_*.json direto, só grava em --saida (default:
configs/mapping_sugerido.json) e nunca é lido automaticamente pelo main.py.
"""

import argparse
import difflib
import json
import os

import pandas as pd

# Para cada tabela canônica, quais conceitos existem e quais palavras/
# fragmentos costumam aparecer no nome da coluna original (em qualquer
# fonte). Alimentado com os dois mapeamentos que já construímos
# (RavenStack + Fonte B) + variações comuns de mercado.
DICIONARIO_CANONICO = {
    "accounts": {
        "canonical_id": ["account_id", "client_uuid", "customer_id", "id_cliente", "client_id", "customer_uuid"],
        "canonical_name": ["account_name", "client_name", "customer_name", "nome_cliente", "company_name", "nome_empresa", "razao_social"],
        "canonical_industry": ["industry", "vertical", "segmento", "sector", "setor_atuacao", "ramo_atividade"],
        "canonical_country": ["country", "country_code", "pais", "pais_sede"],
        "canonical_signup_date": ["signup_date", "created_at", "data_cadastro", "start_date", "onboarded_at", "data_criacao"],
        "canonical_referral_source": ["referral_source", "lead_channel", "acquisition_channel", "canal_aquisicao", "utm_source", "origem_lead", "canal_origem"],
        "canonical_plan": ["plan_tier", "tier", "plano", "plan_name", "subscription_tier", "nivel_plano"],
        "canonical_seats": ["seats", "licenses", "assentos", "licencas", "num_users", "qtd_licencas"],
        "canonical_is_trial": ["is_trial", "trialing", "em_trial", "trial_flag", "em_periodo_teste"],
        "canonical_is_churn_account": ["churn_flag", "is_cancelled", "is_churned", "cancelado", "status_churn", "cliente_cancelou"],
    },
    "subscriptions": {
        "canonical_sub_id": ["subscription_id", "contract_id", "id_assinatura", "subscription_uuid", "id_contrato"],
        "canonical_id": ["account_id", "client_uuid", "customer_id", "id_cliente"],
        "canonical_sub_start": ["start_date", "contract_start", "data_inicio", "data_inicio_contrato"],
        "canonical_sub_end": ["end_date", "contract_end", "data_fim", "data_fim_contrato"],
        "canonical_sub_plan": ["plan_tier", "tier", "plano", "nivel_plano"],
        "canonical_sub_seats": ["seats", "licenses", "assentos", "qtd_licencas"],
        "canonical_revenue": ["mrr_amount", "monthly_recurring_rev", "mrr", "receita_mensal", "valor_mensal", "valor_mensal_brl"],
        "canonical_arr": ["arr_amount", "annual_recurring_rev", "arr", "receita_anual", "valor_anual", "valor_anual_brl"],
        "canonical_billing_frequency": ["billing_frequency", "invoice_cycle", "ciclo_cobranca", "periodicidade_cobranca"],
        "canonical_upgrade": ["upgrade_flag", "upgraded", "fez_upgrade", "houve_upgrade"],
        "canonical_downgrade": ["downgrade_flag", "downgraded", "fez_downgrade", "houve_downgrade"],
        "canonical_is_churn_sub": ["churn_flag", "is_cancelled", "cancelado", "contrato_cancelado"],
    },
    "usage": {
        "canonical_sub_id": ["subscription_id", "contract_id", "id_assinatura", "id_contrato"],
        "canonical_usage_date": ["usage_date", "event_date", "data_uso"],
        "canonical_volume": ["usage_count", "hits", "eventos", "qtd_uso", "qtd_utilizacoes"],
        "canonical_duration": ["usage_duration_secs", "duration_seconds", "duracao_segundos"],
        "canonical_errors": ["error_count", "errors", "erros", "qtd_erros"],
        "canonical_is_beta": ["is_beta_feature", "beta_flag", "eh_beta", "e_funcionalidade_beta", "funcionalidade_beta"],
    },
    "tickets": {
        "canonical_id": ["account_id", "client_uuid", "customer_id", "id_cliente"],
        "canonical_ticket_id": ["ticket_id", "case_id", "id_chamado"],
        "canonical_ticket_date": ["submitted_at", "opened_at", "data_abertura", "aberto_em"],
        "canonical_resolution_hours": ["resolution_time_hours", "resolution_hours", "horas_resolucao"],
        "canonical_priority": ["priority", "severity", "prioridade"],
        "canonical_first_response": ["first_response_time_minutes", "sla_minutes", "minutos_primeira_resposta"],
        "canonical_satisfaction": ["satisfaction_score", "csat", "nota_satisfacao"],
        "canonical_escalation": ["escalation_flag", "was_escalated", "foi_escalado"],
    },
    "churn": {
        "canonical_id": ["account_id", "client_uuid", "customer_id", "id_cliente"],
        "canonical_churn_date": ["churn_date", "cancel_date", "data_cancelamento"],
        "canonical_churn_reason": ["reason_code", "cancel_reason", "motivo_cancelamento", "motivo_codigo"],
        "canonical_refund": ["refund_amount_usd", "refund_usd", "valor_reembolso", "valor_reembolso_brl"],
        "canonical_feedback": ["feedback_text", "customer_note", "comentario_cliente"],
        "canonical_is_reactivation": ["is_reactivation", "is_winback", "eh_reativacao", "e_reativacao"],
    },
}


def _normalizar(texto: str) -> str:
    return texto.lower().replace("_", " ").replace("-", " ").strip()


def sugerir_para_tabela(
    colunas_raw: list,
    nome_tabela: str,
    limite_confianca: float = 0.55,
    limite_auto_aceite: float = 0.9,
) -> list:
    """
    Para cada coluna do CSV novo, acha o melhor conceito canônico
    candidato (por similaridade de texto contra os sinônimos conhecidos) e
    devolve uma lista de sugestões com uma nota de confiança 0-1.

    Importante (achado ao testar contra a Fonte B): similaridade de texto
    tem falso positivo real -- "usage_id" bateu com "canonical_usage_date"
    a 0.78 de confiança só por compartilhar fragmentos de texto, mesmo
    sendo colunas completamente diferentes. Por isso só confiança >=
    `limite_auto_aceite` (0.9) entra automaticamente no JSON final;
    qualquer coisa abaixo disso é sugestão, sempre marcada pra revisão --
    mesmo que passe do `limite_confianca` mínimo pra aparecer na lista.
    """
    dicionario = DICIONARIO_CANONICO.get(nome_tabela, {})
    sugestoes = []

    for col_raw in colunas_raw:
        col_norm = _normalizar(col_raw)
        melhor_conceito, melhor_score = None, 0.0

        for conceito, sinonimos in dicionario.items():
            for sinonimo in sinonimos:
                score = difflib.SequenceMatcher(None, col_norm, _normalizar(sinonimo)).ratio()
                if score > melhor_score:
                    melhor_conceito, melhor_score = conceito, score

        tem_sugestao = melhor_score >= limite_confianca
        sugestoes.append({
            "coluna_original": col_raw,
            "sugestao_canonica": melhor_conceito if tem_sugestao else None,
            "confianca": round(melhor_score, 2),
            "auto_aceito": tem_sugestao and melhor_score >= limite_auto_aceite,
            "precisa_revisao_humana": (not tem_sugestao) or melhor_score < limite_auto_aceite,
        })

    return sugestoes


def resolver_com_ia(colunas_ambiguas: list, nome_tabela: str, amostra_df: pd.DataFrame, modelo: str = "claude-sonnet-4-5") -> dict:
    """
    Versão COM IA (Fase 2 completa): só é chamada para as colunas que a
    heurística marcou como ambíguas -- nunca reprocessa o que já foi
    auto-aceito, pra manter custo e latência mínimos. Precisa de
    ANTHROPIC_API_KEY no ambiente; se não tiver, avisa e devolve vazio
    (o script continua funcionando 100% no modo sem IA).
    """
    try:
        import anthropic
    except ImportError:
        print("⚠️  Pacote 'anthropic' não instalado (pip install anthropic). Seguindo só com a heurística.")
        return {}

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY não definida no ambiente. Seguindo só com a heurística (modo sem IA).")
        return {}

    conceitos = DICIONARIO_CANONICO.get(nome_tabela, {})
    descricao_conceitos = "\n".join(f"- {c}: exemplos de nomes conhecidos {v}" for c, v in conceitos.items())
    amostras = {
        col: amostra_df[col].dropna().astype(str).head(3).tolist()
        for col in colunas_ambiguas if col in amostra_df.columns
    }

    prompt = f"""Você está ajudando a mapear colunas de um CSV novo para um esquema canônico de análise de churn.

Tabela: {nome_tabela}
Conceitos canônicos possíveis:
{descricao_conceitos}

Colunas do CSV que a heurística de texto NÃO conseguiu mapear com confiança:
{json.dumps(amostras, ensure_ascii=False, indent=2)}

Para cada coluna, decida qual conceito canônico (da lista acima) ela representa, OU responda null se
a coluna não corresponde a nenhum conceito canônico (ex: um ID técnico interno, uma coluna irrelevante).
Responda SOMENTE um JSON válido no formato {{"nome_da_coluna": "conceito_canonico_ou_null"}}, sem texto
antes ou depois."""

    try:
        client = anthropic.Anthropic()
        resposta = client.messages.create(
            model=modelo,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        texto = resposta.content[0].text.strip()
        # tolera a IA ter envolvido em ```json ... ```
        texto = texto.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        sugestoes_ia = json.loads(texto)
        return {k: v for k, v in sugestoes_ia.items() if v and v != "null"}
    except Exception as e:
        print(f"⚠️  Chamada à IA falhou ({e}). Seguindo só com a heurística.")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Sugere o mapeamento De/Para para uma fonte de dados nova")
    parser.add_argument("--tabela", required=True, choices=list(DICIONARIO_CANONICO.keys()))
    parser.add_argument("--csv", required=True, help="CSV da fonte nova")
    parser.add_argument("--saida", default="configs/mapping_sugerido.json")
    parser.add_argument("--limite-confianca", type=float, default=0.55)
    parser.add_argument(
        "--usar-ia", action="store_true",
        help="Fase 2 completa: chama a API da Anthropic só para as colunas que a heurística não resolveu. "
             "Requer ANTHROPIC_API_KEY no ambiente. Sem essa flag, o script roda 100%% offline (Fase 2 MVP).",
    )
    parser.add_argument("--modelo-ia", default="claude-sonnet-4-5")
    args = parser.parse_args()

    df_amostra = pd.read_csv(args.csv, nrows=5)
    colunas_raw = list(df_amostra.columns)
    sugestoes = sugerir_para_tabela(colunas_raw, args.tabela, args.limite_confianca)

    if args.usar_ia:
        colunas_ambiguas = [s["coluna_original"] for s in sugestoes if not s["auto_aceito"]]
        if colunas_ambiguas:
            print(f"\n🤖 Modo COM IA ativado -- consultando a API para {len(colunas_ambiguas)} coluna(s) ambígua(s)...")
            sugestoes_ia = resolver_com_ia(colunas_ambiguas, args.tabela, df_amostra, args.modelo_ia)
            for s in sugestoes:
                if s["coluna_original"] in sugestoes_ia:
                    s["sugestao_canonica"] = sugestoes_ia[s["coluna_original"]]
                    s["auto_aceito"] = True
                    s["confianca"] = "IA"
                    s["precisa_revisao_humana"] = True  # IA também é revisada, nunca aplicada calada

    print(f"\n📋 Sugestão de mapeamento para '{args.tabela}' ({args.csv}):\n")
    print(f"{'Coluna original':<28} {'Sugestão canônica':<32} {'Confiança':<10} {'Status'}")
    print("-" * 95)
    for s in sugestoes:
        if s["confianca"] == "IA":
            status = "🤖 sugestão da IA (revisar)"
        elif s["auto_aceito"]:
            status = "✅ auto-aceito (heurística)"
        elif s["sugestao_canonica"] is not None:
            status = "⚠️  revisar (confiança média)"
        else:
            status = "❓ sem sugestão"
        print(f"{s['coluna_original']:<28} {str(s['sugestao_canonica']):<32} {str(s['confianca']):<10} {status}")

    n_auto = sum(1 for s in sugestoes if s["auto_aceito"] and s["confianca"] != "IA")
    n_ia = sum(1 for s in sugestoes if s["confianca"] == "IA")
    print(f"\n{n_auto}/{len(sugestoes)} colunas auto-aceitas pela heurística (confiança ≥ 0.9). "
          f"{n_ia} resolvidas pela IA (sempre marcadas para revisão). "
          f"{len(sugestoes) - n_auto - n_ia} ainda sem sugestão confiável.")

    # heurística de alta confiança entra direto; sugestão da IA entra marcada, mas
    # SEMPRE precisa de revisão humana antes de rodar em produção (nunca é silenciosa)
    bloco_mapeamento = {
        s["coluna_original"]: s["sugestao_canonica"]
        for s in sugestoes
        if s["auto_aceito"] or s["confianca"] == "IA"
    }

    mapping_existente = {}
    if os.path.exists(args.saida):
        with open(args.saida, "r", encoding="utf-8") as f:
            mapping_existente = json.load(f)
    mapping_existente[args.tabela] = bloco_mapeamento

    os.makedirs(os.path.dirname(args.saida) or ".", exist_ok=True)
    with open(args.saida, "w", encoding="utf-8") as f:
        json.dump(mapping_existente, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Rascunho salvo em {args.saida} -- REVISE antes de usar em main.py --config.")


if __name__ == "__main__":
    main()
