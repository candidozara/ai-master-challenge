## Resumo do Problema: O Paradoxo do Churn na RavenStack
O desafio simula uma empresa SaaS B2B com ~500 contas onde o churn está subindo, 
mas os indicadores de vaidade dizem o oposto (o time de produto vê o uso geral crescendo e o CS acha que a satisfação está boa). 
O objetivo central é cruzar dados de contas, assinaturas, uso de features, 
tickets de suporte e eventos de churn para descobrir a causa raiz real da perda de clientes, identificar contas em risco e propor ações concretas.

## Visão Estratégica: De Análise Pontual para Arquitetura Recorrente
O ponto mais crítico da engenharia de dados aplicada a negócios: 
O problema do churn é vivo e recorrente, e as origens dos dados mudam com o tempo 
(hoje são CSVs do Kaggle, amanhã pode ser SQL Server, Databricks ou um banco NoSQL).

Em vez de criar um script engessado para este case, a sacada genial é desenhar uma lógica de pipeline desacoplada. 
Ou seja, criar uma arquitetura conceitual onde a regra de negócio do churn é agnóstica à fonte de dados.

## A Lógica Abstrata em 3 Camadas (Aplicável em Qualquer Ferramenta)
Para que essa lógica funcione em um software próprio, em Python, em um Dashboard do Power BI ou em uma API, podemos dividi-la em três camadas modulares:

1. Camada de Ingestão e Normalização (Adaptadores): Uma interface ou rotina responsável por traduzir diferentes origens (seja um arquivo CSV, uma tabela no SQL Server ou um lakehouse no Databricks) para um esquema canônico unificado (uma estrutura padrão de IDs de clientes, datas, métricas financeiras e eventos).

2. Camada de Cruzamento e Feature Store (O Motor Analítico): A inteligência que une o histórico financeiro (MRR/ARR), o comportamento de uso (queda de logins ou erros em features) e o atrito operacional (tickets de suporte sem solução) em uma visão consolidada por conta e linha do tempo.

3. Camada de Decisão e Risco (Motor de Regras / ML): A lógica que pontua o cliente (Score de Churn) com base em desvios de comportamento padrão (ex: queda acentuada de uso combinada com alto tempo de resposta no suporte), gerando alertas acionáveis para o CS.