# Relatório Executivo de Diagnóstico de Churn
*Gerado automaticamente pelo Motor Analítico Determinístico*

## 1. Visão Geral de Impacto
* **Total de Contas Analisadas:** 500
* **Total de Churns Registrados:** 110
* **Taxa de Churn Geral:** 22.0%
* **MRR Perdido (contas churned):** $254,952.00

## 2. Principais Causas Raiz Declaradas (contas confirmadas como churned)
* **budget:** 20.0%
* **features:** 20.0%
* **support:** 20.0%
* **pricing:** 17.0%
* **competitor:** 13.3%
* **unknown:** 9.6%

## 3. Segmentos Mais em Risco

| Dimensão | Segmento | Contas | Taxa de churn |
|---|---|---|---|
| industry | DevTools | 113 | 31.0% |
| referral_source | event | 96 | 30.2% |
| referral_source | other | 103 | 24.3% |
| referral_source | ads | 98 | 23.5% |
| industry | FinTech | 112 | 22.3% |
| plan | Enterprise | 154 | 22.1% |
| plan | Basic | 168 | 22.0% |
| industry | HealthTech | 96 | 21.9% |

## 4. Próximas Ações Recomendadas para o CS
* Priorizar contato proativo com as contas ativas de maior score de risco (ver `risco_churn_api.json`).
* Congelar features beta instáveis até o índice de erros cair.
* Mudar a régua de atendimento para contas Enterprise/Pro.
