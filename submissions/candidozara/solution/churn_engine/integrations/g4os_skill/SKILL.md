---
name: "Diagnóstico de Churn"
description: "Analisa risco de churn, contas em risco, segmentos e qualidade do modelo usando o Churn Engine (source MCP 'churn-engine')."
---

# Diagnóstico de Churn (Churn Engine)

Quando o usuário perguntar sobre churn, cancelamento de clientes, contas em
risco, MRR perdido, segmentos que mais cancelam, ou pedir pra rodar/atualizar
esse diagnóstico, use as ferramentas do source **churn-engine** (MCP) em vez
de tentar calcular ou adivinhar por conta própria -- os números já vêm
calculados e validados por um motor determinístico + modelo de ML testado.

## Quando usar

- "quais contas estão em risco de cancelar?"
- "qual segmento/indústria/canal mais cancela?"
- "roda o diagnóstico de churn com [nova fonte de dados]"
- "o que eu faço com a conta X?"
- "esse modelo de previsão de churn é confiável?"

## Como usar

1. Se o usuário quer ver o estado atual: chame `listar_contas_risco`,
   `obter_segmentos_risco` ou `obter_metricas_modelo` diretamente (dados já
   existem em `outputs/`).
2. Se o usuário trouxe uma fonte de dados NOVA (arquivo diferente, nomes de
   coluna desconhecidos): primeiro `sugerir_mapeamento_coluna` para cada uma
   das 5 tabelas (accounts, subscriptions, usage, tickets, churn), mostre o
   resultado pro usuário revisar as colunas marcadas como incertas, só
   depois chame `rodar_diagnostico` com os caminhos reais.
3. Depois de `rodar_diagnostico`, sempre rode `validar_saida` antes de
   apresentar os resultados como definitivos.
4. Para recomendar uma ação por conta, use `decidir_acoes_recomendadas` --
   NUNCA execute a ação você mesmo (não é uma ferramenta de e-mail/ticket).

## Regras importantes

- O **score de risco por regra** é o critério principal (determinístico,
  auditável). O score do **modelo de ML tem sinal fraco** (ROC-AUC ~0.56
  neste dataset) -- sempre mencione isso se for usar o score do modelo pra
  qualquer decisão, nunca apresente como certeza.
- `rodar_diagnostico` e `decidir_acoes_recomendadas` escrevem arquivos --
  avise o usuário antes de rodar contra uma pasta de output que ele já usa,
  pra não sobrescrever sem querer (por padrão elas usam pastas novas/`outputs`).
- Todos os detalhes de arquitetura, limitações e o processo de construção
  estão documentados em `tecnica/churn_engine/README.md` e
  `tecnica/05-process_log.md` na pasta do projeto (Desktop\backup\Trabalho\Teste IA Master\01).
