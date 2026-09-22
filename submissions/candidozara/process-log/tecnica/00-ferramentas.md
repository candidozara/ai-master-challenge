Vamos usar o `Python` com algumas bibliotecas:

1. pandas
Para que serve: É a biblioteca principal para manipulação, limpeza e cruzamento de dados tabulares (ela transforma arquivos CSV, tabelas SQL ou dados de APIs em tabelas virtuais chamadas DataFrames).

O porquê: É o coração de qualquer análise de dados. Sem ela, você teria que escrever centenas de linhas de código em loop para juntar a tabela de contas (accounts), assinaturas (subscriptions), uso (feature_usage), suporte (support_tickets) e churn (churn_events). Com o pandas, fazemos isso com comandos simples de merge (junção) e groupby (agrupamento).

2. numpy
Para que serve: Biblioteca focada em computação matemática e estatística de alta performance para arrays e matrizes numéricas.

O porquê: É usada por baixo dos panos pelo pandas e serve para calcular métricas rápidas (médias, medianas, desvio padrão do uso, somatórios de MRR perdido) e lidar com operações numéricas pesadas sem travar o código.

3. scikit-learn (Opcional para Evolução)
Para que serve: A biblioteca padrão de Machine Learning em Python (contém algoritmos de classificação, regressão e árvores de decisão).

O porquê: Se a empresa quiser transformar a análise em um modelo preditivo (para prever quais clientes ativos têm mais chance de cancelar antes que o churn aconteça), o scikit-learn fornece os modelos prontos para treinar com os dados históricos de cancelamento.


