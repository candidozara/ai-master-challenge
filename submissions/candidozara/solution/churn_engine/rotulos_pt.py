"""
Textos em português simples, compartilhados entre o painel gráfico
(dashboard.py) e o menu de terminal (main.py) -- pra não ter duas versões
da mesma explicação que podem ficar diferentes com o tempo.
"""

# Nomes das 5 tabelas em português simples, na ordem que aparecem na tela.
TABELAS = [
    ("accounts", "1) Clientes", "Uma linha por cliente/empresa (quem são os seus clientes)."),
    ("subscriptions", "2) Contratos", "Uma linha por contrato/assinatura (valores, datas, plano)."),
    ("usage", "3) Uso da plataforma (opcional)", "Registros de uso: quem usou o quê e quando. Sem isso, o risco por queda de uso e por erro não entra na conta."),
    ("tickets", "4) Chamados de suporte (opcional)", "Chamados abertos pelos clientes. Sem isso, o risco por atrito no suporte não entra na conta."),
    ("churn", "5) Cancelamentos", "Clientes que já cancelaram, com data e motivo."),
]

# 3 são obrigatórias (sem elas não dá pra saber quem é cliente, quanto paga,
# nem quem cancelou -- não tem diagnóstico de churn possível). "uso" e
# "chamados de suporte" são opcionais: o motor roda sem eles, só que com um
# score de risco mais simples (menos sinais) -- documentado no relatório
# gerado, não escondido. Quanto mais dessas 5 tabelas você tiver, melhor a
# análise -- cada uma alimenta um pedaço diferente do score de risco.
TABELAS_OBRIGATORIAS = {"accounts", "subscriptions", "churn"}
TABELAS_OPCIONAIS = {"usage", "tickets"}

# Para cada tabela, quais informações o motor precisa e como explicar isso
# em português simples -- sem termos técnicos ("canonical_x").
CAMPOS_POR_TABELA = {
    "accounts": {
        "canonical_id": "Identificador do cliente (ID, código, CNPJ, e-mail... algo único pra cada um)",
        "canonical_name": "Nome do cliente ou da empresa",
        "canonical_industry": "Setor/ramo de atividade",
        "canonical_country": "País",
        "canonical_signup_date": "Data em que o cliente começou (cadastro/início)",
        "canonical_referral_source": "Como o cliente chegou até vocês (canal de origem)",
        "canonical_plan": "Plano contratado",
        "canonical_seats": "Quantidade de usuários/licenças",
        "canonical_is_trial": "Está em período de teste? (verdadeiro/falso ou sim/não)",
        "canonical_is_churn_account": "Esse cliente já cancelou? (verdadeiro/falso ou sim/não)",
    },
    "subscriptions": {
        "canonical_sub_id": "Identificador do contrato/assinatura",
        "canonical_id": "Identificador do cliente (o mesmo da tabela de Clientes)",
        "canonical_sub_start": "Data de início do contrato",
        "canonical_sub_end": "Data de fim do contrato",
        "canonical_sub_plan": "Plano do contrato",
        "canonical_sub_seats": "Quantidade de usuários/licenças do contrato",
        "canonical_revenue": "Valor pago por mês (mensalidade)",
        "canonical_arr": "Valor pago por ano (se tiver essa coluna separada)",
        "canonical_billing_frequency": "De quanto em quanto tempo cobra (mensal/anual)",
        "canonical_upgrade": "Fez upgrade de plano? (verdadeiro/falso)",
        "canonical_downgrade": "Fez downgrade de plano? (verdadeiro/falso)",
        "canonical_is_churn_sub": "Esse contrato foi cancelado? (verdadeiro/falso)",
    },
    "usage": {
        "canonical_sub_id": "Identificador do contrato/assinatura (o mesmo da tabela de Contratos)",
        "canonical_usage_date": "Data do uso",
        "canonical_volume": "Quantidade de vezes que usou",
        "canonical_duration": "Tempo de uso (em segundos)",
        "canonical_errors": "Quantidade de erros nesse uso",
        "canonical_is_beta": "É uma funcionalidade beta/experimental? (verdadeiro/falso)",
    },
    "tickets": {
        "canonical_id": "Identificador do cliente (o mesmo da tabela de Clientes)",
        "canonical_ticket_id": "Identificador do chamado",
        "canonical_ticket_date": "Data de abertura do chamado",
        "canonical_resolution_hours": "Quantas horas levou para resolver",
        "canonical_priority": "Prioridade do chamado",
        "canonical_first_response": "Minutos até a primeira resposta",
        "canonical_satisfaction": "Nota de satisfação do cliente",
        "canonical_escalation": "Esse chamado foi escalado? (verdadeiro/falso)",
    },
    "churn": {
        "canonical_id": "Identificador do cliente (o mesmo da tabela de Clientes)",
        "canonical_churn_date": "Data do cancelamento",
        "canonical_churn_reason": "Motivo do cancelamento",
        "canonical_refund": "Valor reembolsado (se houve)",
        "canonical_feedback": "Comentário/feedback do cliente ao cancelar",
        "canonical_is_reactivation": "Esse cliente voltou depois (reativação)? (verdadeiro/falso)",
    },
}
