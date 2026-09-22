# Submissão — Alessandro Candido Silva — Challenge 001

## Sobre mim

- **Nome:** Alessandro Candido Silva
- **LinkedIn:** https://www.linkedin.com/in/alessandro-candido-silva/
- **Challenge escolhido:** 001 — Diagnóstico de Churn

---

## Executive Summary

A RavenStack está perdendo 22% das contas (110 de 500), com ~$255 mil de MRR realmente em risco — não os $1,17 milhões que uma primeira leitura dos dados sugeria; o erro nesse cálculo foi encontrado e corrigido durante o processo (ver Process Log). A causa raiz não é preço: quase metade do churn (~47%) tem raiz em orçamento/concorrência, mas isso esconde uma quebra de promessa entre marketing e produto — bugs em features beta e atrito no suporte aparecem tão fortes quanto pricing quando se olha só as contas confirmadas como churned. Construí um motor determinístico (`churn_engine`, Python/pandas/scikit-learn) que cruza as 5 tabelas, calcula um score de risco auditável, exporta em CSV/JSON/PDF, roda comprovadamente contra qualquer fonte de dados (testei com uma segunda fonte simulada, nomes de coluna 100% diferentes, mesmo resultado), e vem com um painel local e um MVP de sugestão automática de mapeamento (com e sem IA). A recomendação central: parar de olhar uso agregado (que cresce) e monitorar quedas de uso por conta — é o sinal mais forte de churn silencioso que os dados mostram.

---

## Solução

### Abordagem

Antes de qualquer cálculo, cruzei minhas anotações e o código que eu já tinha escrito contra o README oficial do desafio e os 5 CSVs reais — não para confirmar o que eu já achava, mas para verificar. Isso imediatamente achou um erro real (MRR perdido inflado em ~4,8x) e dois gaps que o desafio pede explicitamente (segmentação por indústria/canal com contas específicas). Só depois disso parti pra arquitetura: um motor em camadas (ingestão/mapeamento → cruzamento → risco → exportação) desenhado pra ser agnóstico de fonte de dados, porque o problema de churn é recorrente e as origens de dados mudam — não faria sentido um script engessado pra um desafio que simula um problema real de negócio. Cada peça (score de regra, modelo preditivo, segmentação, sugestão automática de mapeamento) foi implementada e **rodada de verdade** contra os dados antes de ser considerada pronta — inclusive o painel, testado com captura de tela real, não só descrito.

### Resultados / Findings

- **Taxa de churn:** 22,0% (110/500 contas) — confirmado direto de `accounts.csv`.
- **MRR realmente perdido:** ~$254.952 (não $1,17M — esse número inicial somava assinaturas encerradas por upgrade/downgrade junto com cancelamento real, sem deduplicar por conta; ver Process Log).
- **Causas raiz** (só contas confirmadas como churned, não a tabela crua de eventos): budget, features e support empatados em 20% cada; pricing 17%; competitor 13,3%.
- **Segmentos em risco que os dados escondiam:** indústria **DevTools churna a 31%** (quase o dobro de Cybersecurity, 16%); canal de aquisição **"event" churna a 30,2%** contra 14,6% de "partner". `plan_tier` sozinho não segmenta nada (Basic/Pro/Enterprise ~22% cada).
- **Modelo preditivo (scikit-learn, RandomForest):** testado com validação cruzada (não um único split, que seria enganoso com só 500 linhas). ROC-AUC ~0,52 na primeira versão (quase aleatório); subiu pra ~0,56 depois de features de recência e taxas normalizadas — ainda um sinal fraco, documentado como tal, não maquiado.
- **`feedback_text` avaliado e descartado** como feature: só 3 frases fixas, sem correlação real com o motivo de cancelamento — ruído do gerador sintético, não sinal.
- **Motor testado contra uma segunda fonte de dados** (nomes de coluna e arquivo 100% diferentes): resultado idêntico, provando a arquitetura agnóstica de fonte na prática, não só no papel.
- **Sugestão automática de mapeamento** (heurística, sem custo de API): 46 de 50 colunas mapeadas corretamente às cegas contra a fonte simulada; as ambíguas ficam marcadas pra revisão humana em vez de mapeadas errado silenciosamente. Modo opcional com IA (API da Anthropic) para os casos que a heurística não resolve.
- **Painel local (Streamlit)** e **exportação em CSV/JSON/PDF/Markdown**, testados rodando de verdade.

### Recomendações

1. **Alerta de desengajamento silencioso:** monitorar semanalmente queda de uso por conta (>30% vs. período anterior) — o cliente raramente cancela do dia pra noite.
2. **Congelar features beta instáveis:** isolar da base principal até o índice de erro cair a zero; bugs em beta aparecem fortemente nas causas de churn.
3. **Régua de atendimento por valor de conta:** contas Enterprise/Pro com ticket urgente não podem cair em fila comum — resposta em até 2h.
4. **Revisar onboarding por canal de aquisição:** o canal "event" perde clientes a mais que o dobro da taxa do canal "partner" — provável desalinhamento de expectativa na venda.

### Limitações

- O modelo preditivo tem sinal fraco (ROC-AUC ~0,56) neste dataset — usado como sinal secundário, nunca como critério principal (isso é o score de regra determinístico).
- `churn_events.csv` tem eventos para mais contas (352) do que `accounts.csv` marca como churned hoje (110) — indício de reativações não totalmente reconciliado.
- As features do modelo usam o histórico total por conta; numa implantação real, o ideal seria uma janela de corte temporal por conta pra eliminar viés residual.
- `is_trial`, `preceding_upgrade_flag` e `preceding_downgrade_flag` ainda não entraram no score de risco.
- O modo "com IA" do sugestor de mapeamento não foi testado com uma chave de API real nesta sessão (sem acesso a uma).

---

## Estrutura desta pasta

| Pasta | Conteúdo |
|-------|----------|
| [`solution/churn_engine/`](solution/churn_engine/) | Motor de diagnóstico de churn (Python) — código, dados de exemplo, outputs gerados. Detalhes no [README do motor](solution/churn_engine/README.md) |
| [`solution/relatorio_executivo_churn.pdf`](solution/relatorio_executivo_churn.pdf) | Relatório executivo gerado pelo motor |
| [`solution/dashboard_v2.png`](solution/dashboard_v2.png) | Captura do painel (Streamlit) rodando |
| [`process-log/notas/`](process-log/notas/) | Minhas notas iniciais, escritas antes de usar IA (diagnóstico, hipóteses, ações) |
| [`process-log/tecnica/`](process-log/tecnica/) | Documentação técnica e o process log completo com IA |
| [`docs/como_rodar.md`](docs/como_rodar.md) | Como rodar o motor e o painel |

> Observação: no process log, caminhos citados como `tecnica/churn_engine/...` correspondem a `solution/churn_engine/...` nesta submissão; `tecnica/*.md` estão em `process-log/tecnica/`. O executável Windows não vai dentro do PR (≈150 MB, acima do limite do GitHub): está publicado na Release do fork e pode ser regerado com `build_exe.py`.

### Como rodar (resumo)

**Sem instalar nada (Windows):** baixe o executável na [Release `churn-engine-v1.0`](https://github.com/candidozara/ai-master-challenge/releases/tag/churn-engine-v1.0) (`churn_engine_windows.zip`), extraia e dê dois cliques em `churn_engine.exe` — o painel abre no navegador.

**Pelo código-fonte:**

```bash
cd solution/churn_engine
pip install -r requirements.txt
python main.py            # abre o painel no navegador
python main.py --menu     # menu no terminal, sem navegador
```

**Gerar o executável:** no Windows, `pip install -r requirements.txt` e depois `python build_exe.py` (de preferência num venv) → `dist/churn_engine/churn_engine.exe`.

Passo a passo completo (executável, código-fonte, como gerar e distribuir o `.exe`, aviso do Windows SmartScreen): [`docs/como_rodar.md`](docs/como_rodar.md).

---

## Process Log — Como usei IA

> **Este bloco é obrigatório.**

### Ferramentas usadas

| Ferramenta | Para que usei |
|------------|----------------|
| Claude (Cowork) | Revisão cruzada de notas/código/dados reais contra a spec oficial; correção de cálculos; implementação e execução completa do `churn_engine`; construção e teste real do painel; leitura da instalação do G4 OS pra planejar integração |

### Workflow

1. Escrevi diagnóstico e esqueleto de código sozinho primeiro (notas em `process-log/notas/` e documentação técnica em `process-log/tecnica/`).
2. Pedi revisão cruzada contra o repositório oficial do desafio e os dados reais — não só uma leitura, rodei os CSVs em pandas pra verificar cada número antes de aceitar.
3. Corrigi a estratégia técnica documentando os gaps antes de mexer em código (evitar "vibe coding").
4. Implementei o motor corrigido e rodei contra os dados reais até funcionar de ponta a ponta — 3 bugs só apareceram nessa etapa, não na leitura do código.
5. Pedi validação cruzada do modelo de ML em vez de aceitar o primeiro resultado (que parecia bom por overfitting mascarado).
6. Pedi prova concreta de que tudo funciona: script de validação automática, troca real de fonte de dados, e o sugestor de mapeamento testado às cegas.
7. Pedi painel, integração com Power BI e G4 OS — a IA leu a instalação real do G4 OS antes de recomendar uma arquitetura de integração, em vez de assumir.

### Onde a IA errou e como corrigi

O maior erro não foi da IA nesta sessão, mas de um cálculo anterior que a IA ajudou a verificar: o MRR perdido estava inflado ~4,8x. A IA reproduziu o cálculo em pandas, testou hipóteses até achar exatamente qual soma gerava o número errado, e mostrou o certo lado a lado. Também: a primeira leitura do modelo de ML parecia mostrar separação forte entre contas churned e ativas — isso era avaliação no próprio conjunto de treino (viés). Pedi validação cruzada de verdade e o resultado caiu para "sinal fraco", que é o número honesto que ficou na entrega.

### O que eu adicionei que a IA sozinha não faria

A decisão estratégica de tratar isso como ferramenta reaproveitável (G4 OS, Databricks, Power BI) em vez de script de desafio único, e a exigência de verificar tudo rodando de verdade em vez de aceitar descrições — inclusive pedir validação cruzada do modelo e teste às cegas do sugestor de mapeamento — vieram de mim, questionando resultados bons demais em vez de aceitá-los.

---

## Evidências

- [x] Narrativa escrita detalhada — [`process-log/tecnica/05-process_log.md`](process-log/tecnica/05-process_log.md) (log completo, rodada a rodada)
- [ ] Screenshots das conversas com IA
- [ ] Screen recording do workflow
- [ ] Chat export
- [x] Git history (commits desta branch)
- [x] Outro: outputs gerados de verdade (CSV/JSON/PDF) em 3 fontes de dados diferentes, em `solution/churn_engine/outputs/` e `solution/churn_engine/evidencias_outras_fontes/`

---

*Submissão enviada em: 22/09/2026*
