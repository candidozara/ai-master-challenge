# Churn Engine — RavenStack

Motor analítico de diagnóstico de churn, desenhado para ser **agnóstico de fonte de dados**: hoje lê os 5 CSVs da RavenStack, amanhã pode ler de SQL Server, Databricks ou qualquer outra fonte — basta trocar o arquivo de mapeamento em `configs/`, sem tocar na lógica de negócio.

## Como rodar

Não precisa instalar nada à parte -- na primeira vez numa máquina nova,
`main.py` instala sozinho o que faltar.

```bash
python main.py            # menu no terminal, explica cada opção (dados de exemplo, dados próprios, painel, validar, sair)
python main.py --painel   # pula o menu, abre o painel gráfico direto no navegador
```

Os 5 arquivos CSV originais (`ravenstack_*.csv`) precisam estar em `data/` -- já vêm no projeto. A opção 4 do menu (ou `python validar_outputs.py`) confere se as 4 saídas estão corretas e consistentes entre si.

### Nem sempre são 5 tabelas

`accounts`, `subscriptions` e `churn` são obrigatórias -- sem elas não dá pra saber quem é cliente, quanto paga e quem cancelou, e não existe diagnóstico de churn possível. `usage` e `tickets` são **opcionais**: cada uma alimenta um pedaço do score de risco (queda de uso, taxa de erro, escalonamento de suporte), então quanto mais você tiver, mais completa a análise -- mas o motor roda com só as 3 obrigatórias. Nesse caso:

- O score de regra (`risco_score_regra`) fica em 0 pra todo mundo -- ele é somado inteiramente a partir de sinais de uso/suporte que não existem. Isso é esperado, não um bug, e fica avisado no terminal.
- O exportador percebe isso sozinho e usa `risco_score_modelo` (o modelo de ML) pra montar a lista de contas em risco e o relatório, em vez de devolver uma lista vazia.
- `python main.py --usage "" --tickets ""` (ou pular esses dois arquivos no menu/painel) roda só com as 3 obrigatórias.

Testado de ponta a ponta (ver `05-process_log.md`, Rodada 16): rodando só com `accounts`+`subscriptions`+`churn`, o pipeline completa normalmente e as 18 checagens do `validar_outputs.py` passam.

Isso vale também **dentro** das 3 tabelas obrigatórias: no mapeamento (De/Para), cada campo individual pode ser deixado como "não tenho essa informação" -- por exemplo, "data de início do contrato" dentro de Contratos -- mesmo a tabela em si sendo obrigatória. O motor (`src/core/engine.py`) trata cada um desses ~15 campos individualmente opcionais da mesma forma: usa se veio, avisa no log e segue sem ele se não veio, em vez de travar (ver `05-process_log.md`, Rodada 21).

### Formatos de arquivo aceitos (pode misturar)

Cada uma das tabelas pode vir num formato diferente das outras -- CSV, Excel
(`.xlsx`/`.xls`) ou JSON (lista de registros, ou um dict com uma lista dentro).
Quem lê é `leitor_arquivos.py`, usado tanto pelo menu de terminal (`opcao
Rodar com os seus dados`) quanto pelo painel gráfico (aba **📥 Meus dados**),
pra não ter duas lógicas de leitura diferentes.

`.sql` e `.pdf` não são aceitos, de propósito: um dump `.sql` pode ter
qualquer estrutura de banco (não é uma tabela simples), e extrair uma tabela
de dentro de um PDF é heurística visual que erra fácil (colunas que se
misturam, texto quebrado em duas linhas). Os dois ficam como possível
próximo passo, não como suposição no código.

### Rodando contra outra fonte de dados

`main.py` aceita os caminhos por linha de comando -- nada fica hardcoded:

```bash
python main.py \
  --config configs/mapping_fonte_b.json \
  --accounts data/fonte_b/clientes.csv \
  --subscriptions data/fonte_b/planos.csv \
  --usage data/fonte_b/uso_produto.csv \
  --tickets data/fonte_b/chamados.csv \
  --churn data/fonte_b/cancelamentos.csv \
  --output-dir outputs_fonte_b
```

`data/fonte_b/` é uma prova, não um enfeite: os mesmos 500 clientes, mas com nomes de coluna e de arquivo totalmente diferentes (`client_uuid` em vez de `account_id`, `monthly_recurring_rev` em vez de `mrr_amount`, etc. -- ver `configs/mapping_fonte_b.json`). Rodar o comando acima entrega **exatamente os mesmos números** (500 contas, 22% de churn, ROC-AUC 0.562) sem que uma linha de `engine.py`, `analytics.py` ou `exporter.py` tenha mudado. Isso é a arquitetura "agnóstica de fonte" funcionando de verdade, não só descrita.

### Sugerindo o mapeamento automaticamente (Fase 2, MVP)

Em vez de escrever o JSON De/Para na mão pra cada fonte nova, `sugerir_mapping.py` compara os nomes de coluna do CSV contra um dicionário de sinônimos e monta um rascunho:

```bash
python sugerir_mapping.py --tabela accounts --csv data/fonte_b/clientes.csv --saida configs/mapping_sugerido.json
python sugerir_mapping.py --tabela subscriptions --csv data/fonte_b/planos.csv --saida configs/mapping_sugerido.json
# ... repita para usage, tickets, churn
```

Testado às cegas contra a Fonte B (fingindo não saber o mapeamento real): acertou **46 de 50 colunas automaticamente**, com confiança ≥ 0.9. As 4 restantes (`is_trial`, `auto_renew_flag`, `feature_name`, `had_upgrade`/`had_downgrade`) ficaram marcadas para revisão humana em vez de mapeadas às cegas -- inclusive um caso instrutivo: `usage_id` bateu 0.78 de confiança com `canonical_usage_date` só por semelhança de texto, e teria mapeado errado se o limite de auto-aceite fosse mais baixo. `outputs_sugerido/` mostra o pipeline rodando com o JSON gerado automaticamente, sem nenhuma edição manual, produzindo o mesmo resultado.

Isso é heurística (comparação de texto), não uma IA generativa de verdade -- é determinístico, roda offline e não custa nada. `--usar-ia` liga a Fase 2 completa: chama a API da Anthropic só pras colunas que a heurística não resolveu com confiança (nunca reprocessa o que já foi aceito). Sem `ANTHROPIC_API_KEY` no ambiente, cai de volta pro modo sem IA avisando o motivo -- nunca quebra.

**Terceira fonte testada (`data/fonte_c/`, em português):** os mesmos 500 clientes, mas com arquivos e colunas 100% em português (`clientes_ativos.csv`, `id_cliente`, `valor_mensal_brl`...). Testado às cegas: o dicionário original (só em inglês) acertou só 16/50 (32%); depois de ampliado com sinônimos em português, acertou **42/50 (84%)**, e o mapeamento gerado automaticamente -- sem edição manual -- já foi suficiente pra rodar o pipeline inteiro e passar nas 18 checagens do `validar_outputs.py` (`outputs_fonte_c/`). Documentado como achado real, não escondido: a cobertura de sinônimos importa, e ampliar o dicionário é o jeito mais barato de melhorar isso antes de precisar de IA.

## Painel, decisão com IA e integração com o G4 OS

- **`dashboard.py`** (Streamlit): painel local com aba **❓ Como usar** embutida -- passo a passo pra alguém sem contexto nenhum conseguir instalar, rodar e interpretar os números sozinho. `python main.py --painel`.
- **Aba 📊 Painel → caixa "📂 Onde estão os seus resultados"**: mostra o caminho completo da pasta de saída, um botão que abre essa pasta direto no Explorador de Arquivos do Windows, e um botão de download por arquivo (PDF, Markdown, CSV, JSON) -- pra quem não é técnico achar o resultado sem precisar entender a estrutura de pastas do projeto.
- **Barra lateral "Análises"**: cada vez que você roda o diagnóstico pela aba 📥 Meus dados, ele vira uma entrada na barra lateral -- igual a uma lista de conversas (nome, data, quais tabelas foram usadas). Clicar numa análise antiga mostra o painel inteiro daquela vez de novo (KPIs, segmentos, score), incluindo as ações de IA que tiverem sido salvas especificamente pra ela. Botão **➕ Nova análise** começa do zero, direto na aba de upload, numa pasta nova criada automaticamente (`outputs_analises/analise_<data>_<hora>/`) -- não precisa escolher pasta na mão pra isso. O registro (nome, data, pasta, resumo da fonte) fica em `configs/historico_analises.json`. Pastas rodadas pelo terminal (`outputs/`, `--output-dir outra_pasta`) não entram automaticamente nessa lista -- o painel abre com os dados de exemplo (`outputs/`) até você criar sua primeira análise por aqui; não existe mais nenhum jeito de escolher pasta fora do fluxo de uma análise (a barra lateral só tem a lista de análises, "➕ Nova análise" e "🔄 Recarregar dados").
- **Controle total dentro de uma análise** (aba 📊 Painel → caixa "📥 Dados de origem desta análise" → "Gerenciar esta análise"): **🔁 Rodar de novo nesta análise** manda dados novos pra essa MESMA sessão (mesma pasta por padrão, ou escolha outra pelo seletor nativo do sistema) sem criar um card duplicado na lista -- atualiza a entrada existente no lugar. **🗑️ Apagar esta análise** remove a pasta de resultados do computador e tira ela do histórico, com confirmação em 2 cliques antes de apagar de vez.
- **Escolher pasta = sempre o seletor nativo do sistema operacional** (PowerShell/.NET no Windows, AppleScript no macOS, zenity/kdialog no Linux, `tkinter` como último recurso) -- nunca um campo de texto pra digitar caminho na mão. No Windows, a janela é forçada a ficar na frente do navegador (owner `TopMost`), pra nunca abrir escondida sem nenhum aviso na tela.
- **Aba 🧠 IA de ação (dentro do painel)**: pra cada conta em risco, decide uma ação recomendada (ex: "priorizar fila de suporte") chamando uma IA de verdade -- sem precisar de terminal. Dois jeitos de escolher onde essa IA roda:
  - **API da Anthropic**: cola a chave direto no painel (fica só na sessão do navegador, nunca é salva em arquivo).
  - **IA local**: detecta sozinho o que estiver rodando na sua máquina (Ollama, LM Studio, LocalAI, Text Generation WebUI, Jan -- qualquer servidor que fale a API da OpenAI em `/v1/chat/completions`), lista os modelos instalados, e tem um botão **🧪 Testar com 1 conta** pra você conferir se aquele modelo entende o formato pedido antes de rodar em todas. Ferramenta fora da lista? Tem um campo de "Endereço customizado".
  - Implementação em `ia_provedores.py` -- testado de ponta a ponta contra um servidor local real (padrão OpenAI) simulando Ollama, incluindo pela interface gráfica (não só a função isolada).
  - `demo_ia_gestao.py` continua existindo como a versão por terminal da mesma camada (`--modo simulado` / `--modo real`), pra quem preferir rodar por linha de comando.
- **`integrations/g4os_mcp_server.py`**: servidor MCP (protocolo real, testado com cliente MCP) que expõe 7 ferramentas do motor (`rodar_diagnostico`, `listar_contas_risco`, `obter_segmentos_risco`, `obter_metricas_modelo`, `sugerir_mapeamento_coluna`, `decidir_acoes_recomendadas`, `validar_saida`) para um agente (G4 OS ou qualquer cliente MCP) chamar diretamente. Registrado como source + skill reais em `~/.g4os-public/workspaces/my-workspace/` -- cópia de referência em `integrations/g4os_source/` e `integrations/g4os_skill/`. As 7 ferramentas estão liberadas sem precisar de confirmação a cada chamada (`permissions.json` do source) -- a pedido explícito do dono do workspace, pro agente do G4 OS conseguir trabalhar com a ferramenta por conta própria.
  - **Pra testar dentro do G4 OS**: abra um chat novo, e ou pergunte naturalmente (ex: "quais contas estão em risco de cancelar?") ou digite `@` pra abrir a lista de skills do workspace e escolha `@churn-diagnostico`. Não é pela aba "Marketplace" -- essa é só pra instalar skills públicos novos; a nossa já está registrada direto no workspace. Testado ao vivo (Rodada 18): o agente achou a fonte `churn-engine` e ativou ela sozinho, sem pedir confirmação nas ferramentas de leitura -- só travou num aviso de "créditos de IA" da própria conta do G4 OS (Workspace > Uso), sem relação com o código daqui.

Saídas geradas em `outputs/`:

| Arquivo | Formato | Para quem |
|---|---|---|
| `outputs/processed/super_tabela_churn.csv` | CSV | Power BI, Looker, Databricks, qualquer BI |
| `outputs/processed/risco_churn_api.json` | JSON | APIs, agentes, G4 OS — só as contas ativas em risco Alto/Crítico |
| `outputs/processed/segmentos_risco.csv` | CSV | Taxa de churn por indústria/canal/plano |
| `outputs/processed/importancia_features_modelo.csv` | CSV | Quais variáveis mais pesam no modelo preditivo |
| `outputs/reports/relatorio_executivo_churn.pdf` | PDF | CEO / C-level |
| `outputs/reports/relatorio_executivo_churn.md` | Markdown | Colar em PR, Notion, Slack |

## Arquitetura (4 camadas)

```
CSV (ou SQL/Databricks amanhã)
        │
        ▼
configs/mapping_*.json  ──▶  src/adapters/mapper.py      (Camada 1: De/Para → Contrato Canônico)
        │
        ▼
src/core/engine.py                                        (Camada 2: cruza as 5 tabelas por conta)
        │
        ▼
src/core/analytics.py                                      (Camada 3: risco -- regra + ML)
        │
        ▼
src/outputs/exporter.py  ──▶  CSV / JSON / PDF / Markdown  (Camada 4: entrega multicanal)
```

**Por que o mapeamento fica num JSON separado do código:** se amanhã a RavenStack trocar `mrr_amount` por `mrr`, ou se plugarmos uma segunda empresa com nomes de coluna diferentes, o ajuste é uma linha no JSON — o `engine.py` e o `analytics.py` nunca mudam, porque só enxergam nomes canônicos (`canonical_revenue`, `canonical_id`, etc.). É o mesmo princípio por trás de rodar isso dentro do G4 OS, acoplado a um Databricks ou a um Power BI: quem consome os exports não precisa saber nada sobre RavenStack.

## Risco de churn: dois scores, de propósito

- **`risco_score_regra`** (0-100, determinístico): soma pontos por queda de uso >30%, erros em features beta e atrito no suporte. Qualquer pessoa do time de CS consegue abrir uma conta e explicar por que ela pontuou alto — é auditável por design.
- **`risco_score_modelo`** (0-100, RandomForest via scikit-learn): tenta aprender padrões não-óbvios a partir do histórico de quem já churnou.

**Achado importante, documentado ao invés de escondido:** a primeira versão do modelo (só com totais brutos: uso, erros, tickets, MRR) teve ROC-AUC médio de **~0.52** em validação cruzada (5 folds) — praticamente aleatório (0.5). Testamos duas hipóteses pra melhorar isso:

1. **Enriquecer com `feedback_text`** (o comentário livre do cliente no cancelamento). Verificamos antes de usar: o campo só tem 3 frases fixas ("too expensive", "missing features", "switched to competitor") e a distribuição delas é quase idêntica dentro de qualquer `reason_code` — inclusive contas que cancelaram por "support" têm a mesma chance de ter o texto "missing features" que "too expensive". Isso é ruído, não sinal (o gerador do dataset não acoplou o texto ao motivo real). **Decisão: não usar essa coluna no modelo** — usá-la teria sido otimizar em cima de aleatoriedade. A checagem que levou a essa decisão está em `analytics.checar_valor_informativo_feedback_text`.

2. **Engenharia de features temporais/normalizadas**: dias desde o último uso, dias desde o último ticket, taxa de erro (erros/uso, não o total bruto) e taxa de escalonamento (escalações/tickets). Essas, sim, ajudaram: ROC-AUC médio subiu de 0.52 para **~0.56** (± 0.04), e `taxa_erro` e `dias_desde_ultimo_uso` viraram as duas features mais importantes do modelo (ver `outputs/processed/importancia_features_modelo.csv`).

**0.56 ainda é um sinal fraco** (o corte que este projeto usa pra considerar um modelo confiável é 0.65) — não é forte o suficiente pra guiar decisões sozinho. Por isso os exports e o relatório continuam usando `risco_score_regra` (determinístico, auditável) como critério principal de priorização, e tratam `risco_score_modelo` como um sinal secundário/experimental. Reportar um ROC-AUC de 0.52-0.56 como "modelo funcionando muito bem" seria exatamente o tipo de conclusão apressada que o desafio pede pra evitar — o valor aqui está em mostrar o processo de tentar melhorar, medir com rigor (validação cruzada, não um único split) e ser honesto sobre o resultado.

## Limitações conhecidas

- `churn_events.csv` tem eventos para mais contas (352) do que `accounts.csv` marca como churned hoje (110) — sinal de reativações. Os cálculos de motivo de churn usam só os eventos das 110 contas confirmadas, não a tabela crua.
- `feedback_text` foi avaliado e descartado como feature (ver seção acima) — só 3 valores fixos, sem correlação real com `reason_code`.
- O modelo preditivo usa o histórico total disponível por conta, incluindo o período em que contas já churned simplesmente pararam de usar o produto. Numa implantação real, o ideal é recalcular as features usando só uma janela anterior a uma data de corte por conta, para eliminar qualquer viés temporal residual.
- `is_trial`, `preceding_upgrade_flag` e `preceding_downgrade_flag` estão disponíveis nos dados mas ainda não entraram no score de risco nem no modelo — próximo incremento natural.
- O ROC-AUC pode variar um pouco (~0.55-0.56) dependendo da versão do scikit-learn instalada, mesmo com `random_state` fixo -- confirmado rodando o mesmo `main.py`, mesmos dados, em duas máquinas diferentes (0.562 vs 0.551). Isso é esperado (implementação interna do RandomForest muda entre versões da biblioteca) e não muda a conclusão: sinal fraco, abaixo do corte de confiança de 0.65.

## Próxima fase (fora do escopo desta entrega)

O que já está implementado e testado: sugestão automática de mapeamento (com e sem IA), camada de decisão de ação por conta (com e sem IA), painel local, e integração real via MCP com o G4 OS. Em ambos os modos com IA, a IA nunca calcula o churn em si — isso continua 100% determinístico em `engine.py` e `analytics.py`; a IA só participa de mapeamento e de sugestão de ação, sempre marcada para revisão humana.

Fica de fato fora do escopo por enquanto: testar o modo `--usar-ia` / `--modo real` com uma `ANTHROPIC_API_KEY` de verdade (só foi possível testar o fallback sem chave); confirmar dentro do próprio G4 OS que o agente reconhece e usa o source/skill registrados (só foi possível testar o servidor MCP isoladamente, com um cliente de teste); e mover as features do modelo preditivo para uma janela temporal por conta (ver Limitações).
