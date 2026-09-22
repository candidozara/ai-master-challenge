**Abaixo estão os principais mapeamentos de campos e o que cada cruzamento revela:**

**1. Chaves de Ligação (Onde tudo se conecta)**
account_id: É o elo principal. Conecta a tabela de contas (accounts) com o suporte (support_tickets) e com os eventos de cancelamento (churn_events).

subscription_id: Conecta a tabela de assinaturas (subscriptions) com o uso diário do produto (feature_usage). Como uma conta pode ter várias assinaturas ao longo do tempo (mudanças de plano, renovações), esse ID detalha o comportamento exato em cada fase.

**2. Os Cruzamentos Críticos (O que eles provam)**
**A. Contas (accounts) + Assinaturas (subscriptions)**
Campos cruzados: plan_tier, seats, mrr_amount, churn_flag.

O que revela: Mostra qual plano e tamanho de conta (quantos assentos) trazem mais receita e onde o dinheiro está saindo. Permite calcular o impacto financeiro real (MRR/ARR perdido) em vez de olhar apenas para a quantidade de clientes que saíram.

**B. Assinaturas (subscriptions) + Uso de Features (feature_usage)**
Campos cruzados: error_count, is_beta_feature, usage_count, usage_duration_secs.

O que revela: Responde à dúvida do CEO sobre o uso estar crescendo. Ao cruzar isso, descobrimos se o aumento de uso está concentrado em funcionalidades normais enquanto as features em beta (is_beta_feature = True) geram picos de erros (error_count), afugentando os usuários antes do cancelamento.

**C. Contas (accounts) + Suporte (support_tickets)**
Campos cruzados: first_response_time_minutes, resolution_time_hours, escalation_flag, satisfaction_score.

O que revela: Desmascara a visão do time de CS de que "a satisfação está ok". Permite cruzar clientes que deram churn com o tempo que demoraram a ser atendidos e quantas vezes os tickets precisaram ser escalados por falta de resolução rápida.

**D. Contas (accounts) + Eventos de Churn (churn_events)**
Campos cruzados: reason_code, feedback_text, preceding_upgrade_flag, preceding_downgrade_flag.

O que revela: Conecta o perfil do cliente (indústria, canal de aquisição) com o motivo real da saída (reason_code como support ou features) e os comentários deixados em texto livre, provando se o cliente teve problemas recentes de mudança de plano antes de cancelar.