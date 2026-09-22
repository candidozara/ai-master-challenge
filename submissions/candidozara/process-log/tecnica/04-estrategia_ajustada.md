## Checkpoint: Estratégia Ajustada + Gaps Técnicos (pós-revisão cruzada)

Esse documento fecha o ciclo de planejamento antes de mexer em código. Ele nasce da revisão que fiz cruzando suas 8 notas, o `churn_engine` atual e os 5 CSVs reais — e do que você definiu na conversa: Python com pandas/numpy/scikit-learn primeiro, 100% determinístico, exportando CSV/JSON/PDF, funcionando sozinho ou acoplado (G4 OS, Databricks, SQL Server, Power BI), com a IA entrando só numa fase 2 para ler e ajustar dados novos.

---

### 1. O que os dados realmente mostram (correção)

Taxa de churn (22%, 110/500 contas) e a distribuição de motivos (features 19%, support 17,3%, budget+pricing+competitor ~47,8%) — confirmados, seus números estavam certos.

O que estava errado: **MRR perdido não é $1,17M, é ~$255 mil**. O $1,17M somava todas as assinaturas com `churn_flag=True` em `subscriptions.csv` sem deduplicar por conta — isso mistura fim de assinatura por upgrade/downgrade de plano com cancelamento real. O número certo é a MRR da última assinatura das 110 contas que `accounts.csv` marca como churned. Bônus: a MRR média de quem cancelou é levemente **menor** que a de quem ficou (não há concentração de perda em contas grandes).

Segmentos de risco que ainda faltavam (o desafio pede "contas específicas", isso ainda não existia): indústria **DevTools churna a 31%** (quase o dobro de Cybersecurity, 16%), e contas vindas do canal **"event" churnam a 30%** contra 14,6% de "partner" — mais que o dobro. `plan_tier` sozinho não segmenta nada (Basic/Pro/Enterprise estão todos em ~22%).

Limitação a documentar no relatório final: 352 contas têm eventos em `churn_events.csv`, mas só 110 estão marcadas como churned em `accounts.csv` — indício de reativações. Vale citar como limitação dos dados, não esconder.

---

### 2. Arquitetura técnica ajustada

O desenho em camadas que você já tinha (`tecnica/01-funcionamento.md` e `tecnica/03-mapeamento.md`) continua correto na essência. Ajustei para incluir uma camada que faltava e corrigir o que estava quebrado:

**Camada 0 — Perfilamento automático (nova).** Antes de aplicar qualquer regra de negócio, o motor "olha" o dado sozinho: lê schema, tipos de coluna, % de nulos, cardinalidade, detecta candidatos a chave primária/estrangeira. É isso que te dá a independência de fonte que você descreveu — o sistema entende a forma dos dados antes de qualquer mapeamento fixo, então quando a fonte mudar (SQL Server, Databricks, outro CSV) ele já chega sabendo o que está vendo, em vez de quebrar silenciosamente.

**Camada 1 — Ingestão + Mapeamento (corrigida).** O `mapper.py` e o JSON de configuração continuam certos como ideia. O bug: `mrr_amount` está mapeado dentro do bloco `"accounts"` no `mapping_ravenstack.json`, mas essa coluna não existe em `accounts.csv` — ela está em `subscriptions.csv`. E `subscriptions` nunca entra no pipeline (nem está listada em `paths_arquivos` no `main.py`). Sem isso, o motor não tem MRR, plano de cobrança nem upgrade/downgrade — que são a base da pergunta 3 do desafio (impacto financeiro).

**Camada 2 — Motor Analítico (Core), com 3 peças novas.** O `engine.py` atual só soma totais (`total_uso`, `total_erros`) — falta exatamente a parte que você mais descreveu em `07-acoes.md`: detecção de queda de uso comparando período recente com anterior por conta (o "desengajamento silencioso"), um score de risco determinístico (regras primeiro: uso caindo + erro em beta + ticket escalado = risco alto; scikit-learn depois, quando tiver rótulo suficiente para treinar), e segmentação por indústria/canal/plano com taxa de churn — os números da seção 1 que hoje só existem porque eu rodei fora do seu pipeline.

**Camada 3 — Exportação multicanal.** `exporter.py` já faz CSV (BI) e JSON (API/G4 OS) e um Markdown simples. Falta PDF — que é o formato que fecha o pedido do desafio de "o CEO não-técnico consegue ler". E o cálculo de receita perdida no relatório está zerado hoje porque depende de `canonical_revenue`, que nunca é criado (efeito do bug da camada 1).

**Camada 4 — IA (fase 2, não agora).** Só entra depois que a Camada 0+1 estiverem rodando sozinhas: a IA lê um dataset novo, sugere o dicionário de mapeamento, e um humano aprova antes dele virar regra. O motor de cálculo continua 100% determinístico — a IA nunca calcula churn, só ajuda a plugar fontes novas mais rápido.

---

### 3. Por que isso funciona "sozinho ou acoplado"

A peça chave é o contrato canônico (as colunas `canonical_*`). Qualquer sistema de fora — G4 OS, um dashboard Power BI, um pipeline Databricks — não precisa saber nada sobre RavenStack; ele só consome um dos três exports (CSV, JSON ou PDF) ou lê a tabela canônica diretamente. Trocar a fonte de dados significa trocar só o arquivo de mapeamento (Camada 1); o Core, os exports e quem consome tudo isso não mudam uma linha.

---

### 4. Fases do projeto

**Fase 1 (agora):** pandas + numpy + scikit-learn, pipeline determinístico, sem chamada de API de IA nenhuma no cálculo.
**Fase 2 (depois, fora do escopo desta entrega):** IA lendo datasets novos e propondo o `mapping_*.json`.

---

### 5. Checklist de gaps antes de codar

- [ ] Mover `mrr_amount`, `arr_amount`, `plan_tier`, `billing_frequency` para o bloco `"subscriptions"` no `mapping_ravenstack.json`
- [ ] Adicionar `subscriptions` em `paths_arquivos` e no fluxo do `main.py`
- [ ] Descomentar e rodar o `main.py` de verdade contra os 5 CSVs (hoje ele nunca executa)
- [ ] Colocar os 5 CSVs dentro de `churn_engine/data/` (pasta está vazia hoje)
- [ ] `engine.py`: agregar `subscriptions` (MRR real por conta, última assinatura)
- [ ] `engine.py`: detecção de queda de uso por período (early warning)
- [ ] `engine.py` ou novo `analytics.py`: score de risco determinístico
- [ ] `engine.py`: segmentação por `industry` / `referral_source` / `plan_tier` com taxa de churn
- [ ] `exporter.py`: adicionar `exportar_pdf`
- [ ] `exporter.py`: corrigir `receita_perdida` (usar `canonical_revenue` vindo de subscriptions, deduplicado por conta)
- [ ] Criar `requirements.txt` e `README.md` dentro de `churn_engine/`

---

### 6. Padrão de submissão no GitHub (lembrete, pra não esquecer na hora de entregar)

A submissão do repositório `ai-master-challenge` só é aceita via **Pull Request**, e só se pode mexer dentro da sua própria pasta:

```
submissions/seu-nome/
├── README.md            ← segue o templates/submission-template.md
├── solution/             ← a solução (análise + código do churn_engine)
├── process-log/          ← prints, chat exports, narrativa de como usou IA
└── docs/                 ← documentação extra (esse tipo de nota, por exemplo)
```

Passo a passo: fork → clone → branch `submission/seu-nome` → criar a pasta → commit/push → abrir PR pra `main` com título `[Submission] Seu Nome — Challenge 001`.

O `README.md` da submissão precisa seguir a estrutura do template oficial (Sobre mim, Executive Summary, Abordagem, Resultados, Recomendações, Limitações) e o **bloco de Process Log é obrigatório** — sem ele a submissão é desclassificada. Esse é o lugar certo pra contar, por exemplo, que a IA errou o cálculo de MRR perdido e você (com minha ajuda) recalculou — isso é exatamente o tipo de evidência de julgamento que o critério "O que você adicionou que a IA sozinha não faria" está pedindo.

---

### 7. Próximos passos

Com isso documentado, partimos para o código: corrigir o mapping, plugar `subscriptions` no pipeline, implementar a detecção de queda de uso + score de risco, a segmentação, o export em PDF, rodar o pipeline ponta a ponta contra os CSVs reais e gerar o relatório executivo corrigido.
