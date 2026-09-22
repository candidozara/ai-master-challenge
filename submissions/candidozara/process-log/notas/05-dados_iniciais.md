
**O Contexto e o Problema (Paradoxo do CEO):** 
A RavenStack é uma startup SaaS B2B com ~500 contas onde o CEO percebeu o churn subindo, mas o time de produto achava que o uso estava crescendo e o CS achava que a satisfação estava boa.

**O Diagnóstico Financeiro e Geral:**
O churn de contas está em 22% (110 de 500 contas canceladas).
Financeiramente, isso representa uma perda de mais de $1.17 milhão em MRR.


**As Razões do Churn (Os Motivos Oficiais):**
Problemas de Produto / Features: 19% (falhas, limitações e bugs, especialmente em recursos beta).
Frustração com o Suporte: 17.3% (demora na primeira resposta e tickets urgentes escalados sem resolução adequada).
Orçamento / Preço / Concorrência: ~47% somados (o cliente sente que o produto não entrega o valor prometido e migra para concorrentes).

**Os 5 Datasets Disponíveis para Análise:**
ravenstack_accounts.csv: Cadastro central de contas, indústria, canal de aquisição e planos.
ravenstack_subscriptions.csv: Histórico financeiro, MRR, ARR e mudanças de plano (upgrades/downgrades).
ravenstack_feature_usage.csv: Comportamento diário de uso das 40 features, incluindo contagem de erros e flags de features beta.
ravenstack_support_tickets.csv: Histórico de atendimento, tempo de primeira resposta, prioridade e taxa de escalação.
ravenstack_churn_events.csv: Registro de quem cancelou, razão oficial, reembolsos e feedback em texto.


**Ação de Negócio Direta (Pós-Venda): Corrigir o pós-venda garantindo que a experiência entregue corresponda à promessa (eliminar bugs em features, acelerar o suporte para contas críticas e monitorar a queda de engajamento antes que o cliente cancele).**