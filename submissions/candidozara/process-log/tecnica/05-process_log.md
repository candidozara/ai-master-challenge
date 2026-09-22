## Process Log (rascunho vivo)

Este arquivo vai sendo atualizado a cada etapa relevante do trabalho com a IA. Quando chegar a hora do fork/PR real, ele vira a base de `process-log/` (junto com prints/chat export), seguindo o formato pedido no `templates/submission-template.md`.

---

### Ferramentas usadas

| Ferramenta | Para que usei |
|------------|----------------|
| Claude (Cowork) | Revisão cruzada das minhas notas + código contra os dados reais e a spec oficial do desafio; correção de cálculos; implementação completa do pipeline (`churn_engine`) rodando contra os 5 CSVs reais |

### Workflow (o que aconteceu até aqui)

1. Escrevi minhas notas (01 a 07) e a parte técnica (`tecnica/`) sozinho primeiro, incluindo um diagnóstico com números e um esqueleto de código (`churn_engine`).
2. Pedi para a IA analisar tudo junto: minhas notas + o repositório oficial do desafio no GitHub + o código que eu já tinha escrito.
3. A IA achou um erro real no meu diagnóstico (MRR perdido) e dois segmentos de risco que eu não tinha visto, além de 3 bugs no código (`churn_engine`) nunca tinha rodado de verdade.
4. Documentei a estratégia ajustada e os gaps antes de mexer em código (`tecnica/04-estrategia_ajustada.md`), pra não ir direto pro "vibe coding".
5. Pedi pra IA implementar as correções e "ver o projeto inteiro" -- ela reescreveu o `churn_engine` (mapping, engine, um módulo novo `analytics.py`, exporter com PDF) e **rodou de fato** contra os 5 CSVs reais, não só escreveu código teórico.
6. Durante essa implementação, a IA achou e corrigiu **3 bugs novos** que só apareceram ao rodar de verdade (ver abaixo).
7. Pedi validação cruzada do modelo de Machine Learning (não confiar num único resultado) -- a IA percebeu que o resultado inicial (ROC-AUC 0.52 num único split) podia ser sorte/azar com só 500 linhas, e rodou validação cruzada de verdade pra confirmar.
8. Todos os arquivos foram commitados na minha pasta local (`tecnica/churn_engine/`), incluindo os outputs gerados (CSV, JSON, PDF, Markdown) como prova de que o pipeline roda de ponta a ponta.

### Onde a IA errou / onde eu (com ajuda dela) achei erros no meu próprio trabalho anterior, e como corrigi

**Erro 1 (já registrado antes):** MRR perdido que eu tinha estava errado por ~4,8x ($1,17M vs. $255 mil real). Corrigido e reproduzido pelo pipeline agora (`relatorio_executivo_churn.md` mostra $254.952,00).

**Erro 2 (achado ao implementar o código, não só ao ler):** o `mapping_ravenstack.json` original tentava mapear `account_id` dentro da tabela de uso (`feature_usage.csv`) -- mas essa coluna **não existe** nesse CSV (ele só tem `subscription_id`). Se o `main.py` original tivesse sido descomentado sem essa correção, teria quebrado na primeira linha de agregação. Corrigido fazendo o `engine.py` juntar `feature_usage` com `subscriptions` primeiro (via `subscription_id`) pra herdar o `account_id`, só depois agregar por conta.

**Erro 3 (achado rodando o código pela primeira vez):** um bug de `pandas` bobo mas real -- ao pegar a última assinatura de cada conta, eu (a IA) incluí `canonical_id` duas vezes (uma como chave de agrupamento, outra na lista de colunas selecionadas), o que quebrava o `reset_index()`. Só apareceu ao rodar; não seria visível só lendo o código.

**Erro 4 (o mais importante, achado com validação cruzada):** a primeira versão do modelo de Machine Learning (RandomForest) mostrou uma separação enorme entre contas churned e ativas quando eu simplesmente reajustei o modelo com todos os dados e comparei a média do score -- parecia um modelo excelente. Mas isso é **viés de avaliar o modelo nos mesmos dados que ele usou pra aprender** (overfitting mascarado de sucesso). Pedi validação cruzada de verdade (5 folds, dados nunca vistos em cada fold) e o resultado caiu pra ROC-AUC ~0.52 -- ou seja, **o modelo não tem sinal preditivo real neste dataset**. Ao invés de esconder isso ou trocar de modelo até "dar certo", documentei como um achado legítimo (ver `tecnica/churn_engine/README.md`, seção "Achado importante") e mudei os exports pra priorizar o score de regra (determinístico) em vez do score do modelo. Isso é exatamente o tipo de disciplina que separa "usar IA bem" de "aceitar o primeiro número que a IA cospe".

### O que eu adicionei que a IA sozinha não faria

A decisão estratégica de tratar isso como uma ferramenta reaproveitável (G4 OS, Databricks, Power BI) em vez de um script de desafio único foi minha, desde o início. E a exigência de rodar contra os dados reais e desconfiar de resultados bons demais (o caso do modelo) veio de eu pedir validação cruzada em vez de aceitar o primeiro ROC-AUC -- é o tipo de ceticismo que o desafio explicitamente valoriza ("cuidado com conclusões apressadas").

### Rodada 5 — tentando melhorar o modelo (e sendo honesto sobre o resultado)

Depois de reportar o ROC-AUC ~0.52 (sinal quase nulo), pedi pra IA continuar em vez de aceitar isso como resposta final. Ela testou duas direções concretas:

1. **Usar `feedback_text` (o comentário de texto livre do cliente no churn)** — antes de usar, ela checou se o campo tinha informação real: só tem 3 frases fixas, e a distribuição delas é praticamente igual dentro de qualquer motivo de cancelamento (`reason_code`), inclusive onde não fazia sentido (contas que cancelaram por "problema no suporte" tinham a mesma chance de ter o texto "muito caro" que "faltam funcionalidades"). Conclusão: é ruído do gerador sintético, não sinal real. **Decisão: não usar.** Achei importante que ela tenha checado isso _antes_ de tentar usar, em vez de jogar no modelo e ver o que acontece.

2. **Engenharia de features temporais/normalizadas** (dias desde o último uso, dias desde o último ticket, taxa de erro em vez de total bruto, taxa de escalonamento) — essas melhoraram o ROC-AUC de 0.52 para ~0.56. Ainda fraco (abaixo do corte de confiança de 0.65 que o próprio projeto define), mas uma melhora real e mensurada com o mesmo rigor (validação cruzada, não um split único).

O resultado final continua honesto: o modelo é um sinal secundário, não a base da priorização. O que mudou foi o processo de tentar melhorar de forma criteriosa e documentar tanto o que funcionou quanto o que não funcionou (feedback_text).

### Rodada 6 — provar que funciona, não só afirmar

Perguntei se o processo realmente funciona, se dava pra trocar os dados, e sobre a Fase 2 (IA sugerindo o mapeamento). Em vez de só responder "sim, funciona", pedi (e a IA construiu) 3 provas concretas:

1. **`validar_outputs.py`** -- um script que confere as 4 saídas (CSV, JSON, PDF, Markdown) depois de cada execução: existência dos arquivos, número de contas, unicidade de ID, taxa de churn plausível, JSON ordenado por risco, PDF legível com o número certo de contas, seções do relatório presentes. 18 checagens, todas passando.

2. **Prova de troca de fonte** -- parametrizei `main.py` (antes tinha os caminhos fixos no código) e criei uma "Fonte B" simulada: os mesmos 500 clientes, mas com nomes de coluna e de arquivo 100% diferentes (`client_uuid` em vez de `account_id`, `monthly_recurring_rev` em vez de `mrr_amount`, arquivo `clientes.csv` em vez de `ravenstack_accounts.csv`). Rodei o motor apontando pra essa fonte nova, só trocando o arquivo de mapeamento -- resultado idêntico (500 contas, 22% churn, ROC-AUC 0.562), sem tocar em `engine.py`/`analytics.py`/`exporter.py`. Isso é a "arquitetura agnóstica de fonte" comprovada rodando, não só descrita em markdown.

3. **MVP da Fase 2 (`sugerir_mapping.py`)** -- em vez de escrever o mapeamento na mão, um script compara os nomes de coluna de um CSV novo contra um dicionário de sinônimos e sugere o De/Para automaticamente. Testei às cegas contra a Fonte B (fingindo não saber a resposta): acertou 46 de 50 colunas com confiança alta, e -- importante -- errou de um jeito seguro: quando achei um falso positivo (`usage_id` batendo com `canonical_usage_date` por semelhança de texto), ajustei o limite de auto-aceite pra esse tipo de caso ficar marcado pra revisão humana em vez de entrar errado silenciosamente. Rodei o pipeline inteiro usando só o mapeamento gerado automaticamente, sem editar nada -- resultado idêntico ao mapeamento feito na mão. Isso é a Fase 2 funcionando de ponta a ponta, não um esboço teórico.

Deixei claro no código e no README que isso é heurística (comparação de texto), não uma IA generativa de verdade -- o upgrade natural seria plugar a API da Anthropic no mesmo ponto de decisão, pros casos de confiança média que a heurística não resolve sozinha.

### Rodada 7 — painel, Power BI, G4 OS e o modo com IA

Perguntei sobre painel, integração com outras plataformas e a parte de IA que tinha ficado pra trás. Pontos que valem registrar:

- Antes de construir o painel, pedi pra IA ler a estrutura do meu G4 OS instalado (`AppData\Local\Programs\G4 OS`) em vez de assumir a stack. Ela descobriu que já roda sobre Claude Agent SDK + servidores MCP + sistema de skills -- e mudou a recomendação de "construir uma API REST genérica" para "empacotar como skill do G4 OS", que é o caminho nativo. Isso só foi possível porque ela checou antes de recomendar, em vez de assumir a partir do que eu lembrava (Electron/Ruby/Python/React) -- inclusive não achou Ruby na instalação real.
- O painel (Streamlit) foi testado de verdade: ela rodou um servidor local, tirou screenshot com um navegador automatizado, viu que os rótulos dos gráficos estavam cortados, corrigiu e testou de novo antes de me entregar.
- O modo `--usar-ia` do `sugerir_mapping.py` foi testado sem chave de API (ela não tem a minha), e confirmei que cai pro modo sem IA educadamente em vez de quebrar.

### Rodada 8 — auditoria da documentação e consolidação do README de submissão

Perguntei se tudo que estávamos fazendo estava documentado, porque eu ia precisar disso na hora de subir (fork/PR). Em vez de responder só "sim", a IA:

1. Releu a pasta inteira no meu computador (`device_list_dir` recursivo) pra confirmar o estado real de cada arquivo, não confiar em memória de conversa.
2. Separou duas coisas que eu estava tratando como uma só: a documentação de **processo/trabalho** (que já estava completa -- `04-estrategia_ajustada.md`, `05-process_log.md`, `06-integracoes.md`, o `README.md` do `churn_engine`) e o **README de submissão no formato que o desafio pede** (`templates/submission-template.md`), que ainda não existia como documento único -- estava espalhado.
3. Montou `tecnica/07-submissao_preview.md` seguindo a estrutura exata do template oficial (Sobre mim, Executive Summary, Solução, Process Log condensado, Evidências), puxando os números já verificados nas rodadas anteriores em vez de recalcular ou inventar nada novo.
4. Deixou marcado com `[preencher]` só o que realmente depende de mim (LinkedIn) ou só existe depois do fork de verdade (git history, data da submissão) -- não fingiu que essas partes já estavam prontas.

Isso importa porque documentar "o processo" e documentar "a entrega no formato pedido" são coisas diferentes, e só a segunda é o que vai de fato pro PR -- eu não tinha essa distinção clara até pedir a auditoria.

### Rodada 9 — teste completo (painel + terceira fonte + IA simulada) e integração real com o G4 OS

Antes de fazer qualquer coisa nesta rodada, parei e perguntei -- o pedido anterior tinha várias decisões que não eram minhas pra tomar sozinho (modo de teste, nível de documentação, começar ou não a integração G4 OS agora, se eu podia ou não procurar a pasta real do G4 OS no computador). Só depois de ter as respostas é que montei o que segue.

**1. Painel gráfico testado de verdade, com aba de ajuda embutida.** Adicionei uma segunda aba (`❓ Como usar`) dentro do próprio `dashboard.py`, com passo a passo completo (instalar, rodar o motor, abrir o painel, usar dados próprios, o que cada número significa, o que fazer se der erro) -- pensado pra alguém que nunca viu o projeto conseguir se virar sozinho, sem precisar ler código. Testei as duas abas de verdade (servidor local + screenshot automatizado), confirmando que renderizam certo antes de sincronizar com o computador.

**2. Terceira fonte de dados -- desta vez em português, simulando o cenário real do seu amigo.** As fontes anteriores (RavenStack e Fonte B) tinham nomes de coluna em inglês. Criei uma "Fonte C" com os mesmos 500 clientes, mas em arquivos e colunas 100% em português (`clientes_ativos.csv`, `contratos.csv`, `id_cliente`, `valor_mensal_brl` etc.) -- o tipo de nome que um sistema brasileiro real usaria. **Achado real**: com o dicionário de sinônimos como estava, o sugestor de mapeamento só acertou 16 de 50 colunas às cegas (32%) -- muito pior que os 46/50 da Fonte B, porque o dicionário só tinha sinônimos em inglês. Em vez de esconder isso, ampliei o `DICIONARIO_CANONICO` em `sugerir_mapping.py` com os termos em português que apareceram (e variações prováveis), retestei às cegas: **42/50 (84%)**, e o mapeamento gerado automaticamente -- sem eu editar uma linha -- já foi suficiente pra rodar `main.py` de ponta a ponta e passar nas 18 checagens do `validar_outputs.py` (500 contas, ROC-AUC 0.562, idêntico às outras fontes). Isso é uma prova concreta e honesta de "o sistema entende independente do arquivo", não só uma afirmação.

**3. Simulação do modo "com IA fazendo a gestão".** Criei `demo_ia_gestao.py`: uma camada nova (separada do mapeamento) que decide uma ação recomendada por conta em risco (ex: "engenharia investigar bugs", "priorizar fila de suporte"), com dois modos -- `--modo simulado` (regras determinísticas, sem custo, sem precisar de credencial de ninguém) e `--modo real` (chamaria a API da Anthropic de verdade, com o mesmo formato de saída). Testei os dois: o modo simulado gerou recomendações plausíveis pras 5 contas de maior risco; o modo real, sem `ANTHROPIC_API_KEY` no ambiente (não tenho uma chave sua, e não deveria pedir pra digitar aqui), caiu pro modo simulado de forma limpa e avisada -- confirmando de novo o padrão "nunca quebra sem IA" que já valia pro mapeamento, agora também pra camada de decisão.

**4. Integração real com o G4 OS (não só recomendação em markdown).** Você pediu pra eu estudar o G4 OS de verdade antes de acoplar, e que a IA de lá tivesse acesso "a tudo". Com sua permissão, explorei `~/.g4os` (quase vazio -- só log de erro) e `~/.g4os-public` (aqui sim: config, workspaces, docs internos). **Achado que corrige o que eu tinha documentado antes**: a documentação interna do G4 OS (`docs/skills.md`, `docs/sources.md`) descreve os caminhos como `~/.g4os/workspaces/{id}/...`, mas na prática, neste computador, tudo (sessões, skills, sources reais) está em `~/.g4os-public/workspaces/my-workspace/...` -- é o que eu confirmei existir e ser usado de verdade (20+ sessões reais, skills como `skill-creator`, `session-checkpoint`, e dezenas de sources tipo `g4os-slack`, `g4os-github`). Fica documentado como achado porque contraria o texto oficial do próprio G4 OS.

A partir dos docs internos (`sources.md`), o G4 OS aceita fontes do tipo `mcp` com transporte `stdio` -- comando local que ele mesmo inicia. Construí `integrations/g4os_mcp_server.py`: um servidor MCP de verdade (biblioteca `mcp` do Python) que expõe 7 ferramentas tipadas do motor (`rodar_diagnostico`, `listar_contas_risco`, `obter_segmentos_risco`, `obter_metricas_modelo`, `sugerir_mapeamento_coluna`, `decidir_acoes_recomendadas`, `validar_saida`) -- não é "leia o README e adivinhe o comando", é chamada de função direta pro agente do G4 OS. Testei com um cliente MCP real (protocolo stdio de verdade, não simulado): listei as 7 ferramentas e chamei várias contra os dados reais (inclusive contra a Fonte C), tudo funcionando. Um erro real apareceu no meio do teste -- instalei a versão mais nova da biblioteca `mcp` (2.x) e o código quebrou porque a v2 renomeou a API (`FastMCP` → `MCPServer`); fixei a versão em `mcp>=1.0,<2.0` no `requirements.txt` e documentei o motivo.

Depois de testado, registrei de verdade -- com sua autorização explícita de "começar agora" -- o source `churn-engine` (`config.json` + `guide.md` + `permissions.json`, seguindo exatamente o formato descrito em `docs/sources.md`) e a skill `churn-diagnostico` (`SKILL.md`, seguindo `docs/skills.md`) na sua área real do G4 OS (`~/.g4os-public/workspaces/my-workspace/`). As permissões do modo Explorar liberam só as ferramentas de leitura (listar contas, segmentos, métricas, sugerir mapeamento, validar) -- `rodar_diagnostico` e `decidir_acoes_recomendadas` (que escrevem arquivo ou podem chamar API paga) ficam fora da liberação automática, exigindo confirmação. Uma cópia de tudo isso também fica dentro do projeto (`integrations/g4os_source/`, `integrations/g4os_skill/`) como referência e documentação -- não só escondido dentro da pasta de dados do G4 OS.

**Nota honesta sobre o que eu NÃO consegui testar**: não tenho como abrir o G4 OS de verdade e conversar com o agente dele daqui -- só posso validar que o servidor MCP funciona (testado, ver acima) e que os arquivos de registro seguem exatamente o formato documentado. A primeira vez que você abrir o G4 OS depois disso, vale conferir se o source "Churn Engine" aparece conectado; se o G4 OS não achar o comando `python`, o ajuste é trocar `command` em `integrations/g4os_source/config.json` (e no arquivo real dentro de `.g4os-public`) pelo caminho completo do python que você usa pra rodar `main.py`.

### Rodada 10 — corrigindo confusão real de uso (múltiplas pastas de output, guia complicado)

Você testou sozinho pela primeira vez e achou 2 problemas reais de UX que eu não tinha visto pela ótica de quem só quer rodar: (1) 4 pastas `outputs*` na raiz do projeto, parecendo bagunça e com arquivos repetidos entre si -- eram provas de teste (fontes diferentes) que eu deixei espalhadas junto com o output normal; (2) o guia `08-como_rodar.md` estava longo demais pra quem só queria "rodar 1 comando".

Corrigido:
- As 3 pastas de teste (`outputs_fonte_b`, `outputs_fonte_c`, `outputs_sugerido`) foram movidas pra `evidencias_outras_fontes/` (com um `LEIA-ME.md` explicando o que são), fora do caminho principal. `outputs/` voltou a ser a única pasta que `main.py` usa por padrão -- roda de novo, sobrescreve, não acumula.
- `08-como_rodar.md` reescrito pra 2 comandos e nada mais (`pip install` + `python main.py`; painel é um terceiro comando opcional). O resto (dados próprios, validação, IA, G4 OS) ficou só referenciado, não explicado ali.
- Revalidei depois da mudança: `python main.py` + `validar_outputs.py` rodando de novo contra `outputs/` sozinho, 18/18 checagens passando, dashboard só listando `outputs` na barra lateral.

### Rodada 11 — painel virou um menu, sem terminal, sem nomear arquivo

Reclamação direta e correta: o jeito de rodar com dados próprios (passo 3 do
`08-como_rodar.md`) exigia digitar 5 flags de comando com nomes de arquivo
específicos (`contas.csv`, `assinaturas.csv`...) sem explicar de onde vêm
esses arquivos nem o que fazer com eles -- inutilizável pra alguém leigo.

Troquei o comando por um menu de verdade, dentro do próprio painel
(`dashboard.py`, aba nova **📥 Meus dados**):

1. Cinco caixas de upload, uma por tabela, com legenda em português simples
   (sem "canonical_x", sem jargão).
2. Depois do upload, um menu por PERGUNTA DE NEGÓCIO ("qual é a coluna do
   identificador do cliente?", "qual é a coluna do valor pago por mês?"),
   já vindo preenchido com o palpite automático (a mesma heurística de
   `sugerir_mapping.py`) -- a pessoa só confirma ou troca, sem editar JSON.
3. Um botão "🚀 Rodar diagnóstico com esses dados" que salva os arquivos,
   monta o mapeamento e roda o motor sozinho.

Testado de ponta a ponta com upload real (Fonte B, 5 arquivos, navegador
automatizado): os campos vieram pré-preenchidos certos, o botão rodou o
motor de verdade e os resultados apareceram no Painel com os números já
conhecidos (500 contas, 22% de churn, $254.952) -- confirmando que o menu
produz exatamente o mesmo resultado que rodar por linha de comando, só que
sem exigir que a pessoa digite nada.

### Rodada 12 — corrigindo de verdade: o problema era o terminal, não o painel

Entendi errado na rodada 11 -- a reclamação era sobre a linha de comando
(`main.py --config ... --accounts ... --output-dir ...`), não sobre o
painel gráfico. Criei `rodar.py`: um menu de terminal, um comando só
(`python rodar.py`, ou 2 cliques em `RODAR.bat` no Windows -- nem terminal
precisa abrir). Ele pergunta o que fazer (1 a 5) e, na opção "meus dados",
pede a pasta com os CSVs, lista os arquivos achados, pergunta qual é qual
(por número, não por nome de arquivo) e confirma cada coluna com a mesma
heurística do painel -- a pessoa só aperta Enter na maioria das vezes.

Testado de ponta a ponta no seu computador de verdade (não só na nuvem):
rodei `python rodar.py` simulando alguém digitando as respostas, com os
dados da Fonte C (nomes em português) -- achou os 5 arquivos, os campos
vieram certos, o motor rodou, 500 contas e ROC-AUC 0.562 batendo com o
esperado, e as 18 checagens do `validar_outputs.py` passaram no final.
`dashboard.py` e `rodar.py` agora compartilham os mesmos textos em
português simples (`rotulos_pt.py`), pra não ter duas explicações
diferentes da mesma coisa.

### Rodada 13 — variação do ROC-AUC entre máquinas (achado, não bug)

Você rodou `python main.py` direto no seu Windows (Python 3.14, scikit-learn
1.9.0) e o ROC-AUC saiu 0.551, diferente do 0.562 que eu vinha reportando
(testado em Linux). Antes de assumir que era sinal de algo errado, conferi
o que já era garantido no código: `random_state=42` fixo tanto no split de
validação cruzada quanto no `RandomForestClassifier` -- não é problema de
semente aleatória. A diferença vem da implementação interna do
`RandomForest` mudando entre versões do scikit-learn (mesmo código, mesmos
dados, resultado ligeiramente diferente por causa da biblioteca). Documentei
isso na seção "Limitações conhecidas" do `README.md` em vez de esconder ou
"ajustar" o número pra bater -- e a conclusão não muda: sinal fraco (~0.55),
abaixo do corte de confiança de 0.65 que o próprio projeto define. Você
achou isso sem importância no momento ("quem falou em ponto bate"), então
ficou só registrado, sem virar trabalho extra.

### Rodada 14 — 1 comando de verdade: instala sozinho, menu explica cada opção, painel tem comando próprio

Você corrigiu três coisas que eu não tinha entendido direito da rodada 12,
tudo sobre o `rodar.py`/`RODAR.bat`:

1. **"1 comando que rode tudo, instale ou não as dependências"** -- antes,
   `RODAR.bat` ainda exigia rodar `pip install -r requirements.txt` à parte
   pelo menos uma vez. Adicionei `garantir_dependencias()` em `rodar.py`:
   ao abrir, ele checa se `pandas`, `numpy`, `sklearn` e `reportlab` já
   estão instalados (sem tentar importar e sem barulho, se já estiverem);
   se faltar algo, instala sozinho na hora (só acontece na primeira vez
   naquela máquina) e só depois abre o menu. Testei a detecção de módulo
   faltando de propósito (nome inventado) pra confirmar que a lógica pega
   o caso de máquina zerada, e testei o caminho normal (tudo já instalado)
   rodando o menu de ponta a ponta de novo.

2. **"o menu tem que explicar o que cada opção faz"** -- o menu antigo só
   listava "1) Rodar com dados de exemplo" sem dizer o que isso significa
   pra quem nunca viu o projeto. Reescrevi como `mostrar_menu()`, com uma
   frase em português simples embaixo de cada opção explicando o que ela
   faz e quando usar (ex: opção 3 agora diz "Abre uma tela no navegador
   com os gráficos do último resultado gerado (opção 1 ou 2)").

3. **"outro comando separado só pra abrir o painel gráfico"** -- criei
   `VER_PAINEL.bat` (2 cliques, sem passar pelo menu) e `python rodar.py
   --painel` como equivalente por terminal. Testei os dois caminhos:
   `rodar.py --painel` abre o painel direto sem mostrar o menu numerado.

Sincronizei os dois arquivos (`rodar.py`, `VER_PAINEL.bat`) no seu
computador e, por causa do episódio anterior em que o `08-como_rodar.md`
tinha sido "salvo com sucesso" mas o conteúdo antigo continuou lá, dessa
vez **li de volta direto do seu computador** (não confiei só na resposta
de sucesso da ferramenta) pra confirmar que o conteúdo novo realmente
chegou, antes de dizer que estava pronto. `08-como_rodar.md` também foi
atualizado pra mencionar o `VER_PAINEL.bat` e o fato de não precisar mais
rodar `pip install` à parte.

### Rodada 15 — sem `.bat`: tudo em `main.py`, dois comandos, nada mais

Você corrigiu de novo, dessa vez a raiz do problema: eu tinha criado
`rodar.py` + `RODAR.bat` + `VER_PAINEL.bat` como arquivos separados do
motor (`main.py`), e você não queria `.bat` nenhum -- queria dois comandos
Python, e o comando do menu tinha que ser o mesmo `python main.py` que já
existia, não um script novo pra decorar.

Fundi tudo num arquivo só. `rodar.py` deixou de existir -- toda a lógica
do menu (as mesmas 5 opções com explicação, a instalação automática de
dependência, a revisão de mapeamento no terminal) entrou dentro do próprio
`main.py`. O comportamento agora é:

- `python main.py` **sem nenhum argumento** → abre o menu no terminal.
- `python main.py --painel` → pula o menu, abre o painel gráfico direto
  (equivalente ao que era `VER_PAINEL.bat`).
- `python main.py --config ... --accounts ...` (com argumentos, do jeito
  que já funcionava desde o início) → continua rodando o motor direto,
  sem menu -- é o que o painel e o próprio menu (opções 1 e 2) chamam por
  baixo dos panos, e é o mesmo comando que aponta pra uma fonte de dados
  nova.

Apaguei `rodar.py`, `RODAR.bat` e `VER_PAINEL.bat` -- tanto daqui quanto do
seu computador -- pra não sobrar um jeito antigo confundindo com o novo.
Atualizei `dashboard.py` (aba **❓ Como usar**), `README.md` e
`08-como_rodar.md` pros mesmos dois comandos, sem nenhuma menção a `.bat`.

Testado de ponta a ponta, incluindo no seu computador de verdade: rodei
`python main.py` com as dependências do painel (`streamlit`, `plotly`)
propositalmente ausentes -- ele instalou sozinho, mostrou o menu com
explicação em cada opção, e saí pela opção 5, tudo numa única chamada.
Testei também `--painel` (confirma que chama exatamente `streamlit run
dashboard.py`, sem passar pelo menu) e o caminho com argumentos (Fonte B,
500 contas, ROC-AUC 0.562 idêntico a antes) pra garantir que nada que já
funcionava quebrou.

### Rodada 16 — menos de 5 tabelas, IA no painel (local ou API) e G4 OS com acesso total

Três pedidos concretos nesta rodada, depois de eu explicar o estado atual de cada ponto e perguntar o que fazer (nenhum dos três eu simplesmente assumi):

**1. Rodar com menos de 5 arquivos.** Fui conferir o código antes de prometer algo: `engine.py` e `analytics.py` já eram defensivos (checavam `if coluna in df.columns` antes de usar cada sinal) -- só um bug pontual em `_agregar_uso` quebrava quando "uso" vinha vazio (retornava 2 valores em vez dos 3 que quem chama esperava). Corrigi isso e tornei `usage` e `tickets` oficialmente opcionais em todo o pipeline: `accounts`, `subscriptions` e `churn` continuam obrigatórias (sem elas não tem diagnóstico possível), as outras duas não.

Achado real ao testar com só 3 tabelas: o score de regra (`risco_score_regra`) é somado inteiramente a partir de sinais de uso/suporte -- sem eles, ele fica **0 pra todo mundo**, e a lista de contas em risco saía vazia por causa disso (não porque ninguém estava em risco, mas porque o critério de corte não tinha dado nenhum pra trabalhar). Corrigi o exportador (`_escolher_coluna_score`) pra perceber esse caso e usar `risco_score_modelo` em vez de devolver uma lista vazia, avisando no terminal que fez essa troca.

Também achei (e corrigi) um problema de honestidade no `validar_outputs.py`: ele exigia "exatamente 500 contas" e "churn entre 15%-30%" -- números que só valiam porque todo mundo testava contra o mesmo dataset sintético. Pra dados reais de qualquer empresa (que é o objetivo aqui, é pro seu amigo), isso ia dar falso alarme sempre. Virou informativo (mostra o número real) em vez de exigir um valor específico.

Testado de ponta a ponta, incluindo no seu computador: rodei só com `accounts`+`subscriptions`+`churn` (Fonte B), confirmei que passa nas 18 checagens do validador, e reconfirmei que rodar com as 5 tabelas continua idêntico a antes (500 contas, ROC-AUC 0.562) -- a mudança não quebrou o caminho que já funcionava.

**2. Botão de IA no painel, local ou por API.** Criei `ia_provedores.py` com duas formas de ligar uma IA de verdade na camada de decisão (ação recomendada por conta em risco), e uma aba nova no painel (**🧠 IA de ação**):

- **API da Anthropic**: campo pra colar a chave direto no painel (fica só na sessão do navegador, nunca salva em arquivo).
- **IA local**: detecção automática nas portas mais comuns (Ollama, LM Studio, LocalAI, Text Generation WebUI, Jan) -- qualquer servidor que fale o formato de chat padrão da OpenAI (`/v1/chat/completions`) funciona, mesmo sem estar nessa lista, através do campo "Endereço customizado". Um botão **🧪 Testar com 1 conta** deixa você ver se aquele modelo específico entende o formato pedido antes de rodar em todas as contas -- foi exatamente o que você pediu ("testar os modelos pra ver se são compatíveis").

Não dava pra testar isso contra o seu Ollama de verdade daqui (a ponte com o seu computador não alcança serviços que só escutam no `localhost` dele) -- mas montei um servidor local dentro do ambiente de nuvem simulando exatamente a API do Ollama, e testei o fluxo inteiro através da interface gráfica de verdade (não só a função isolada): cliquei em "IA local", "Detectar IA local" achou o servidor simulado, listou o modelo, e "Testar com 1 conta" chamou de verdade e mostrou o resultado no formato esperado. O código que roda na sua máquina é o mesmo -- só muda o endereço que ele encontra.

**3. G4 OS com acesso total.** Fui direto no arquivo `permissions.json` real do source `churn-engine` (não assumi o que estava lá). Das 7 ferramentas do MCP, 5 já estavam liberadas (só leitura); `rodar_diagnostico` e `decidir_acoes_recomendadas` (as duas que escrevem/chamam API paga) exigiam confirmação manual a cada chamada em modo Explorar. A pedido explícito seu, liberei as 7 sem exigir confirmação -- alterei tanto a cópia de referência no projeto quanto o arquivo real dentro do seu G4 OS (`~/.g4os-public/workspaces/my-workspace/sources/churn-engine/permissions.json`), e conferi lendo os dois de volta.

### Rodada 17 — múltiplos formatos de arquivo, achar a pasta de resultados e resposta às suas 4 dúvidas

Nesta rodada você aprovou o estado atual ("ta perfeito, simplesmente funcional") e trouxe 4 pontos novos. Os itens 2 (multi-formato) e 3 (achar o output) viraram código; os itens 1 e 4 eram dúvidas conceituais, respondidas no chat (resumo abaixo) sem mexer em código além do necessário.

**1. Múltiplos formatos de arquivo (CSV + Excel + JSON misturados).** Você perguntou se dava pra ter um arquivo em CSV, outro em `.json`, outro em `.sql` e outro em PDF, tudo na mesma análise. Criei `leitor_arquivos.py`, um módulo único usado tanto pelo menu de terminal quanto pelo painel gráfico (pra não ter duas versões da mesma lógica), que lê CSV, Excel (`.xlsx`/`.xls`) e JSON e sempre devolve uma tabela — você pode misturar os três formatos livremente entre as 5 tabelas.

`.sql` e `.pdf` ficaram de fora de propósito, não por esquecimento: um dump `.sql` pode ter qualquer estrutura de banco (não é simplesmente "uma tabela"), e extrair uma tabela de um PDF é heurística visual que erra fácil (colunas que se misturam, texto que quebra em duas linhas). Os dois merecem uma conversa específica sobre o que exatamente você tem nesses arquivos antes de virar código — fica como próximo passo se você quiser.

No menu de terminal (`opcao_dados_proprios`), agora ele varre a pasta procurando qualquer combinação de `.csv`/`.xlsx`/`.xls`/`.json` (mínimo 3 arquivos, não mais 5 fixos) e normaliza cada um pra CSV internamente antes de rodar o motor. No painel gráfico, o upload de cada tabela aceita os mesmos 4 formatos e mostra a prévia das colunas não importa o formato original.

Testado de ponta a ponta: rodei o menu de terminal de verdade (entrada simulada, não só a função isolada) com uma pasta contendo `clientes.csv`, `planos.xlsx` e `cancelamentos.json` juntos — leu os 3 formatos, sugeriu o mapeamento de colunas certo, terminou os 500 registros e apontou corretamente o aviso de tabelas opcionais faltando. Repeti o mesmo teste pelo painel gráfico de verdade (Playwright clicando na interface real, não simulação) e confirmei que a prévia mostra as colunas certas vindas do Excel e do JSON (por exemplo `cancel_reason`, `refund_usd`, `is_winback` vieram certinho do `.json`).

**2. Achar a pasta de resultados no painel gráfico.** Você tinha razão em cobrar isso — um botão que só te leva a ver os outputs dentro do navegador não ajuda quem não é técnico a achar o arquivo de verdade no computador. Adicionei uma caixa fixa no topo da aba **📊 Painel** ("📂 Onde estão os seus resultados") com três coisas: (1) o caminho completo da pasta em texto, pra copiar e colar no Explorador de Arquivos se precisar; (2) um botão **"📂 Abrir essa pasta no computador"** que abre a pasta de verdade no Explorador do Windows (`os.startfile`, o mesmo mecanismo de dar duplo-clique numa pasta); (3) um botão de download pra cada arquivo final (PDF, Markdown, CSV da tabela completa, JSON de contas em risco, CSV de segmentos) que usa o download nativo do navegador — o arquivo vai pra pasta de Downloads normal do Windows, sem precisar entender a estrutura de pastas do projeto.

Testado com Playwright de verdade: cliquei no botão de abrir pasta e no botão de baixar o CSV, e confirmei que o download realmente disparou (não só que o botão existe).

**3. Suas 4 perguntas — respondidas no chat, sem mudança de código nesta rodada** (fica registrado aqui pra não perder o histórico da decisão):

- *A IA vai reavaliar o churn? Que parâmetro ela usa?* Não — o score de risco (regra + modelo de ML) continua sendo calculado 100% de forma determinística, sem IA, e é isso que fica no CSV/PDF/JSON principal. A camada de IA (aba 🧠) entra depois, só pra sugerir uma ação prática por conta já classificada como risco (ex.: "oferecer desconto", "ligar do suporte") — ela recebe os dados já calculados daquela conta, não decide o score. Separar assim foi proposital: o diagnóstico de churn (a parte que decide quem está em risco) precisa ser auditável e repetível, e IA generativa não é — ela pode mudar de resposta a cada chamada.
- *Dava pra ter uma comparação "com IA" vs "sem IA" no painel?* Isso é uma decisão de escopo real (o que exatamente seria comparado, já que a IA não recalcula o score) — não decidi sozinho, deixei como pergunta em aberto pra você no chat.
- *SQL e PDF como fonte de dados?* Resposta no item 1 acima — de propósito fora por enquanto, oferecido como possível próximo passo.
- *Como testar no G4 OS?* Expliquei o caminho concreto no chat: abrir o workspace, confirmar que o source `churn-engine` aparece conectado, e perguntar algo natural tipo "quais contas estão em risco de cancelar?" (ou chamar a skill direto com `@churn-diagnostico`) — o agente usa as ferramentas do MCP automaticamente, e as duas que antes pediam confirmação a cada chamada (`rodar_diagnostico`, `decidir_acoes_recomendadas`) já não pedem mais, por causa da mudança da Rodada 16.

### Rodada 18 — testado o G4 OS ao vivo e construído o histórico de análises tipo "conversas"

Você aprovou o estado geral e trouxe mais dois pontos concretos: onde achar o churn engine dentro do G4 OS (com print de tela mostrando confusão real -- procurou "churn" na aba errada, Marketplace, e não achou nada), e uma reformulação da barra lateral do painel pra funcionar como uma lista de conversas, uma análise por vez, com histórico.

**1. Testado o G4 OS ao vivo (não só documentação lida).** Pedi permissão pra controlar a tela do seu computador e naveguei de verdade dentro do G4 OS: `Ctrl+N` (Novo Chat) → digitar `@` mostra a lista de skills do workspace, e `@churn-diagnostico` aparece nela com a descrição certa. Mandei a pergunta "quais contas estão em risco alto ou crítico agora?" de verdade -- o agente localizou a fonte `churn-engine`, pediu permissão pra ativar ela (permiti), e foi direto pra consultar as ferramentas de leitura sem pedir confirmação extra (confirma que a liberação da Rodada 16 funcionou). Só não terminou porque bateu num aviso de "créditos de IA" da sua conta G4 OS (orçamento do ciclo atingido, resolve em Workspace > Uso) -- isso é um limite de conta, não um bug daqui. Documentei o passo a passo exato no README.

**2. Histórico de análises na barra lateral (tipo lista de conversas).** Você comparou com como este próprio chat funciona -- cada conversa guardada, clicável, mostrando o que foi feito nela. Antes de mexer, perguntei 3 coisas que mudavam a estrutura de dados do projeto (não assumi sozinho): (a) importar pastas antigas de output pro histórico ou só as novas -- você escolheu só as novas a partir de agora; (b) o que o botão "+" deveria fazer -- você escolheu ir direto pra aba Meus dados, sem perguntar nome antes; (c) se as ações de IA deveriam ficar salvas por análise e voltar ao reabrir -- você escolheu que sim.

Implementado:
- `historico_analises.py` (novo): registro em `configs/historico_analises.json`, uma entrada por análise rodada pelo painel (nome, data, pasta de saída, resumo de quais tabelas foram usadas).
- Cada análise agora grava numa pasta própria e única (`outputs_analises/analise_<data>_<hora>/`) em vez de sempre sobrescrever `outputs_meus_dados/` -- é isso que permite ter várias análises distintas ao mesmo tempo, sem uma apagar a outra.
- Barra lateral trocada de "Fonte de dados" (um dropdown solto que não levava a nada) pra "Análises": botão **➕ Nova análise** (vai direto pra Meus dados), lista das análises já rodadas (clicável, mostra qual está ativa), e um modo "⚙️ Avançado" pra ainda acessar pastas antigas rodadas pelo terminal.
- Campo opcional "Nome dessa análise" na aba Meus dados, antes do botão de rodar -- se deixar em branco, vira a data/hora.
- Depois de rodar com sucesso, o painel pula sozinho pra aba 📊 Painel já mostrando o resultado daquela análise (antes, a mensagem pedia pra você escolher a pasta manualmente -- não precisa mais).
- Aba 🧠 IA de ação agora mostra uma caixa "✅ Ações já calculadas nesta análise" quando você reabre uma análise que já teve IA rodada nela -- volta a tabela salva automaticamente, sem precisar rodar de novo (só se quiser atualizar).
- Troquei `st.tabs()` (que não pode ser controlado por código) por um seletor (`st.radio`) ligado ao estado da sessão, especificamente pra permitir os botões da barra lateral pularem de aba sozinhos -- achado e corrigido um erro real nesse meio do caminho (`StreamlitWidgetAlreadyInstantiatedError`, por tentar mudar a aba ativa depois do seletor já ter sido desenhado na mesma rodada): resolvido com uma variável intermediária (`proxima_aba`) resolvida no topo do script, antes do seletor existir naquela rodada.

Testado de ponta a ponta pela interface gráfica de verdade (Playwright clicando, não só função isolada): criei duas análises com nomes diferentes a partir dos mesmos arquivos mistos (CSV+Excel+JSON) da Rodada 17, confirmei que cada uma foi pra sua própria pasta, cliquei entre elas na barra lateral e confirmei que o painel troca de conteúdo corretamente (caminho da pasta, KPIs), rodei a IA numa delas contra um servidor mock, saí pra "Nova análise" e voltei -- a caixa de ações já calculadas apareceu com os dados certos.

### Rodada 19 — removido o campo de texto de pasta, corrigido o travamento aparente do seletor nativo, e adicionado controle total dentro da sessão (apagar / rodar de novo)

Você reportou três problemas concretos depois de testar a Rodada 18 de verdade na sua máquina: (1) ainda tinha campo de texto pra digitar caminho de pasta na mão (rejeitado — nenhum software pede isso pro usuário comum escolher onde salvar); (2) o botão solto "Escolher pasta no computador..." dentro de "Avançado" não fazia sentido fora do contexto de uma análise específica; (3) ao clicar nesse botão, a tela pareceu travar por ~9 minutos antes da janela de escolha de pasta aparecer.

**1. Removido todo campo de texto manual pra pasta.** Tirei as três ocorrências: o campo "Ou digite o caminho direto" da barra lateral (Avançado), o campo equivalente em "Onde salvar essa análise" (aba Meus dados), e junto com eles o botão solto "📁 Escolher pasta no computador..." da barra lateral (ficou só o dropdown de pastas já existentes no projeto + "Usar essa pasta", que você não questionou). O único jeito de escolher uma pasta fora da padrão agora é o seletor nativo do sistema operacional — igual a qualquer programa de verdade.

**2. Diagnóstico e correção do "travamento" de 9 minutos.** A causa mais provável (não pude confirmar ao vivo na sua máquina, só corrigir o mecanismo e te pedir pra testar de novo): o `FolderBrowserDialog` do PowerShell não tinha uma janela "dona" (owner) definida, então a janela de escolha de pasta podia abrir ATRÁS do navegador, sem nenhum aviso na tela — parecendo que nada aconteceu, quando na real só estava escondida. Corrigido criando uma janelinha invisível com `TopMost = $true` só pra servir de dona da caixa de diálogo, forçando ela a sempre vir pra frente. Também adicionei um `st.spinner()` visível enquanto a janela está carregando, pra nunca mais parecer que travou sem nenhum feedback na tela.

**3. Controle total dentro de uma análise (as 3 capacidades que você pediu).** Adicionada uma seção "Gerenciar esta análise" na aba 📊 Painel (dentro da caixa "📥 Dados de origem desta análise"), visível só quando a análise ativa é uma das rodadas pelo painel (não aparece nos dados de exemplo `outputs/`):
   - **🔁 Rodar de novo nesta análise**: leva pra aba Meus dados com a pasta de destino já pré-preenchida com a MESMA pasta da análise atual — mandar dados novos aqui atualiza a mesma entrada na barra lateral (mesmo nome, mesmo id, só a data e o resumo das tabelas mudam) em vez de criar um card novo. Se quiser trocar a pasta nessa hora, o botão "📁 Escolher outra pasta" (seletor nativo) continua disponível normalmente.
   - **🗑️ Apagar esta análise**: remove a entrada do histórico E a pasta de resultados inteira do computador, com confirmação em 2 cliques (mostra o caminho exato que vai ser apagado antes de confirmar, com botão de Cancelar).
   - **📥 Baixar os arquivos**: já existia (caixa "Onde estão os seus resultados", topo da aba Painel) — não precisou de mudança.
   Implementado com duas funções novas em `historico_analises.py`: `atualizar_analise()` (atualiza uma entrada existente no lugar, sem criar outra) e `remover_analise()` (tira do registro — quem chama decide se também apaga a pasta em disco, que é o que `dashboard.py` faz com `shutil.rmtree`).

**Testado de ponta a ponta com Playwright (cliques reais na interface, não só leitura de código)**, simulando uma análise já existente: cliquei em "🔁 Rodar de novo nesta análise", confirmei que a tela de upload abre limpa (sem arquivos antigos) com a pasta de destino já mostrando a mesma da análise original, enviei os 5 arquivos de novo e rodei — confirmado no `historico_analises.json` que a MESMA entrada foi atualizada (mesmo id, mesma pasta, só data e resumo mudaram), sem duplicar card na barra lateral. Testei também apagar: primeiro clique mostra o aviso com o caminho exato, "Cancelar" não apaga nada (confirmado no disco e no JSON), "✅ Sim, apagar de vez" remove a pasta do disco de verdade e tira a entrada do histórico (barra lateral volta a mostrar "Nenhuma análise feita ainda"). Também confirmei que o campo de texto e o botão solto sumiram de vez (busquei no arquivo sincronizado no seu computador, não só no código daqui).

**O que não pude testar ao vivo, de novo:** a correção do PowerShell (item 2) só pode ser confirmada rodando de verdade no Windows — o ambiente daqui não tem PowerShell pra testar, e não consegui clicar na sua tela nesta rodada (mesma limitação de ferramentas da Rodada 18: navegador Chrome só em modo leitura, terminal só em modo clique sem digitação). O mecanismo (`FolderBrowserDialog` com owner `TopMost`) é uma técnica padrão e documentada do .NET/WinForms, mas peço que teste de novo na sua máquina e me avise se ainda demorar ou aparecer atrás de alguma janela.


### Rodada 20 — removida de vez a seção "Avançado", análise do desafio virou uma sessão de verdade, e corrigido um `UnicodeEncodeError` real no Windows

Três correções nesta rodada, cada uma a partir de um problema concreto reportado por você depois de testar ao vivo.

**1. Removida a seção inteira "⚙️ Avançado: escolher pasta manualmente".** Mesmo já sem o botão solto de seletor nativo (Rodada 19), você apontou (com print, círculo amarelo) que o dropdown + "Usar essa pasta" que sobrou ali continuava sendo, na prática, a mesma coisa que você já tinha rejeitado: uma forma de escolher pasta fora do contexto de qualquer análise específica. Tirado de vez -- a barra lateral agora só tem a lista de análises, "➕ Nova análise" e "🔄 Recarregar dados". Testado com Playwright de verdade (não só lido o código): sidebar renderizada sem nenhum traço da seção, "Recarregar dados" preservado como você pediu ("o resto não mexa").

**2. A análise do desafio (RavenStack) virou uma sessão de verdade.** Você apontou uma inconsistência real: a barra lateral tratava "sessão" como algo que só existe pra dados enviados por você (aba Meus dados), mas os dados de exemplo do desafio (pasta `outputs/`, que abre quando você roda o projeto) ficavam de fora desse sistema -- sem poder apagar, rodar de novo ou trocar a pasta dela. Corrigido: agora, na primeira vez que o painel abre (e só nessa vez), ele registra essa pasta como a primeira entrada de `configs/historico_analises.json` -- com nome "Diagnóstico do desafio (dados RavenStack)" -- e ela passa a ter exatamente os mesmos poderes de qualquer outra análise (🔁 rodar de novo, 🗑️ apagar, baixar arquivos). Não é mais um caso especial fora do sistema de sessões. Testado com Playwright: app abrindo do zero (histórico vazio) cria a entrada automaticamente, recarregar a página várias vezes não duplica ela, e o botão "Rodar de novo nesta análise" navega certo com a pasta `outputs` pré-preenchida como destino.

**3. Corrigido um bug real de codificação (`UnicodeEncodeError`), não relacionado a sessão nenhuma.** Você reportou o erro ao tentar rodar uma análise pelo painel: `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680'` (o emoji 🚀 do primeiro print do `main.py`). Causa: quando você roda `python main.py` direto no terminal, a saída vai pra um console de verdade e o Windows lida com emoji sem problema -- mas quando o painel roda esse mesmo `main.py` por baixo dos panos (via `subprocess`, pra processar os dados que você envia), a saída passa a ir por um "cano" (pipe) em vez de um console, e nessa condição o Python no Windows cai pra codificação regional (cp1252, sem emoji nenhum) em vez de UTF-8 -- travando no primeiro `print` com emoji. Reproduzi o erro exato aqui (forçando `PYTHONIOENCODING=cp1252`, mesmo em Linux, já que cp1252 é uma codificação padrão do Python, não específica do Windows) antes de mexer em qualquer coisa, pra confirmar a causa antes de tentar a correção. Corrigido em duas camadas: `main.py` força UTF-8 em `stdout`/`stderr` logo no início (resolve na origem, funciona rodando de qualquer jeito); `dashboard.py` também passa `PYTHONIOENCODING=utf-8` explicitamente pro subprocesso, como segunda camada de proteção. Testado de ponta a ponta com Playwright rodando o painel inteiro sob a MESMA condição de erro forçada (`PYTHONIOENCODING=cp1252` no processo do Streamlit) -- upload dos 5 arquivos, clique em "Rodar diagnóstico", análise concluída com sucesso e aparecendo na barra lateral, sem nenhum traço do erro.

Os três itens sincronizados com o seu computador e conferidos por hash (md5sum) direto no arquivo real, não só na resposta do envio.


### Rodada 21 — corrigido `KeyError` de campos opcionais deixados sem mapear (não só o que travou pra você, os outros três parecidos também)

Você reportou outro erro real ao testar a Rodada 20: `KeyError: 'canonical_sub_start'`, ao rodar o diagnóstico com dados próprios pelo painel. Diferente do erro anterior (esse já tinha sido corrigido -- essa é uma trava NOVA, mais adiante no processamento).

**Causa raiz.** Na tela de conferência do mapeamento (De/Para), TODO campo de TODA tabela pode ser deixado como "(não tenho essa informação)" -- inclusive dentro de tabelas que são obrigatórias (Contas, Contratos, Cancelamentos). "Data de início do contrato" é um exemplo: a tabela Contratos é obrigatória, mas esse campo específico dela, não. O problema é que `src/core/engine.py` tinha 4 funções que acessavam colunas específicas (`canonical_sub_start`, `canonical_ticket_id`, `canonical_first_response`, `canonical_escalation`, `canonical_satisfaction`, `canonical_churn_reason`, `canonical_is_reactivation`, entre outras) sem checar se elas realmente vieram -- então bastava deixar QUALQUER uma dessas ~15 colunas sem mapear pra travar o pipeline inteiro com `KeyError`, mesmo a pessoa tendo preenchido tudo que é de fato obrigatório.

**Correção: todas as 4 funções agora lidam com campo ausente sem travar**, seguindo o mesmo padrão que já existia em outras partes do código (só usar a coluna se ela existir):
   - `_ultima_assinatura_por_conta()` (a que travou pra você): sem "data de início do contrato", não ordena mais por data -- pega a última assinatura na ordem em que veio no arquivo, e avisa no log.
   - `_agregar_uso()`: cada uma das 3 métricas de uso (volume, erros, é-beta) e a recência de uso (data do uso) agora são somadas/calculadas só se vieram -- sem trocar, o resto continua funcionando.
   - `_agregar_suporte()`: cada uma das 4 métricas de chamados (id do chamado, tempo de resposta, escalação, satisfação) e a recência (data do chamado) agora são calculadas só se vierem.
   - `_resumo_churn()`: motivo do cancelamento e "já reativou" agora são calculados só se vierem -- a contagem de eventos de churn (que não depende de nenhum campo opcional) sempre funciona.
   Em todos os casos, quando um campo opcional falta, aparece um aviso no log explicando o que foi pulado e por quê -- não é um erro escondido, é uma decisão visível.

**Testado com dados reais simulando exatamente o seu cenário** (script Python isolado, sem depender do painel): rodei a Super Tabela inteira com TODOS os ~15 campos opcionais faltando ao mesmo tempo (incluindo o "canonical_sub_start" que travou pra você) -- terminou sem nenhum `KeyError`, com os avisos certos no log. Rodei de novo com uma mistura -- alguns campos opcionais presentes, outros não, em tabelas diferentes -- pra confirmar que os caminhos "tenho o campo" e "não tenho o campo" funcionam corretamente lado a lado, não só o caso extremo de tudo faltando. E por último rodei o pipeline completo com os dados reais do desafio (RavenStack, todos os campos presentes) do zero, pra confirmar que nada quebrou no caminho normal: mesmo resultado de sempre, 500 contas, 35 colunas, relatórios em PDF/Markdown gerados normalmente.

Arquivo sincronizado com o seu computador e conferido por hash (md5sum) direto no arquivo real (`bfdd7418a375ccd734f31661983f8d94`), igual às rodadas anteriores.


### Rodada 22 — revisão final completa (testado de ponta a ponta) + investigação de executável Windows e integração com G4 OS

Você pediu pra revisar tudo, testar cada elemento, e só depois disso investigar (sem construir ainda) se dá pra gerar um executável do painel e como isso se relaciona com o G4 OS enxergar (ou não) a ferramenta.

**1. Revisão completa -- o que foi testado de verdade nesta rodada:**
   - Sintaxe e importação de TODOS os módulos Python do projeto (`py_compile` + import real de cada um) -- sem erros.
   - `main.py` (CLI completo, incluindo o menu de terminal navegado de verdade com respostas simuladas) e `validar_outputs.py` rodando do zero contra os dados do desafio -- as 18 checagens passam, 500 contas, 98 em risco.
   - `dashboard.py` testado com Playwright de ponta a ponta (navegador de verdade, não simulado): sessão do desafio presente no estado limpo; criação de uma análise nova com os 5 arquivos corretos (bate com o desafio: 98 contas em risco, confirmando de novo que o mapeamento automático reproduz o mapeamento correto quando os arquivos não são trocados de lugar); "Rodar de novo nesta análise" com só as 3 tabelas obrigatórias (reproduzindo o cenário que gerou o `KeyError` da Rodada 21, agora sem erro); apagar uma análise com confirmação em 2 cliques; abas "Como usar" e "IA de ação" carregando sem erro de console.
   - `demo_ia_gestao.py` (modo simulado e modo "com IA" caindo educadamente pro simulado sem chave), `ia_provedores.py` (detecção de IA local sem travar quando não tem nada rodando) e `sugerir_mapping.py` -- todos testados isoladamente.
   - `integrations/g4os_mcp_server.py`: as 7 ferramentas MCP registram corretamente e 4 delas (`listar_contas_risco`, `obter_metricas_modelo`, `obter_segmentos_risco`, `validar_saida`) foram chamadas de verdade contra os dados reais do desafio, com resultado correto. Os arquivos registrados no G4 OS (`~/.g4os-public/workspaces/my-workspace/sources/churn-engine/config.json`, `permissions.json`, `guide.md` e a skill `SKILL.md`) continuam idênticos, byte a byte, às cópias dentro do projeto.

   **Dois problemas reais achados e corrigidos nesta revisão** (nenhum reportado por você -- achados testando):
   - `dashboard.py` usava `use_container_width=True` (14 vezes) -- parâmetro do Streamlit descontinuado desde 31/12/2025 (já vencido). Ainda funciona (é só um aviso, não erro), mas trocado por `width="stretch"` (a forma nova recomendada) pra não quebrar numa atualização futura do Streamlit.
   - `dashboard.py`: ao clicar "Rodar de novo nesta análise" enviando MENOS tabelas do que da primeira vez (ex: sem "Uso" e "Chamados", que são opcionais), os arquivos antigos de uso/chamados ficavam esquecidos na pasta `_entrada/` daquela análise, contradizendo o `mapping.json` novo (que não os menciona mais). Corrigido: a pasta `_entrada/` agora é limpa antes de escrever os arquivos de cada rodada.

   Nenhum outro problema real sobreviveu à investigação -- alguns falsos alarmes apareceram nos meus próprios testes automatizados (o teste fechava o navegador ou lia o resultado cedo demais, antes do motor terminar de rodar em segundo plano) e foram descartados depois de confirmar, com evidência direta em disco e no log do servidor, que o comportamento real do painel estava correto.

**2. Investigação: dá pra gerar um `.exe` do painel pro Windows?**

   Testei de verdade com PyInstaller (não só pesquisei) -- compilei o motor (`main.py`) como executável e rodei o binário gerado, sem Python nenhum instalado por fora.

   - **Achado crítico, corrigido**: `main.py` tem uma função (`garantir_dependencias`) que checa se falta alguma biblioteca e, se faltar, roda `sys.executable -m pip install -r requirements.txt` sozinho -- pensada pra quando alguém roda `python main.py` puro. Só que dentro de um `.exe` compilado, `sys.executable` deixa de ser um Python de verdade e passa a ser O PRÓPRIO `.exe` -- ou seja, ele tentava rodar "ele mesmo" como se fosse pip, o que fazia o programa se chamar de novo, detectar "falta" de novo, e se chamar de novo -- uma cascata de processos se multiplicando sem parar (eu vi isso acontecer ao vivo aqui no teste: dezenas de processos filhos em poucos segundos, indo de 7% a mais de 100% de CPU cada). **Corrigi isso** (checando `sys.frozen`, a forma padrão de saber se está rodando compilado, e pulando a auto-instalação nesse caso) e testei de novo: o `.exe` recompilado rodou limpo, sem nenhum processo grudado, com o resultado certo (98 contas em risco). Essa correção já foi sincronizada com o seu `main.py` -- vale mesmo se você nunca gerar o `.exe`, porque remove uma armadilha real do código.
   - **Achado que ainda falta resolver antes de compilar o painel gráfico**: o mesmo padrão -- `main.py` chamando `sys.executable -m streamlit run dashboard.py` pra abrir o painel, e `dashboard.py` chamando `sys.executable main.py ...` toda vez que você roda com dados próprios pelo painel -- quebra do mesmo jeito num `.exe` compilado (testei e confirmei: `--painel` tentando abrir o navegador dá erro "unrecognized arguments" e não abre nada, porque o `.exe` não entende "rodar `streamlit` como módulo" -- ele só entende os argumentos que o PRÓPRIO `main.py` já conhece). Pra funcionar de verdade como `.exe`, esses pontos de "chamar um Python separado por fora" precisam virar "chamar a própria lógica por dentro" (import direto em vez de subprocess) ou "chamar a si mesmo com uma flag conhecida" -- é um trabalho real de adaptação, não é automático, mas também não é enorme.
   - **Tamanho**: só o motor (sem o painel Streamlit) compilado ficou em 158 MB -- isso já inclui pandas/numpy/scikit-learn/reportlab. Com o painel (Streamlit + os arquivos estáticos dele) o executável final deve ficar bem maior, provavelmente na faixa de 250-400 MB.
   - **Conclusão**: é possível, mas não é "compilar e pronto" -- precisa antes resolver os pontos de "chamar um Python separado" listados acima. Fica pra quando você decidir seguir com isso.

**3. Investigação: o G4 OS vai "ver" o painel só quando ele estiver aberto?**

   Fui direto na fonte: os manuais internos do próprio G4 OS (`~/.g4os-public/docs/sources.md`, que também dão acesso porque essa pasta está conectada nesta sessão) e o `config.json` real do source "Churn Engine" já registrado.

   **Hoje, a resposta é: não, o G4 OS já enxerga a ferramenta o tempo todo, painel aberto ou fechado -- e isso não muda com um `.exe`.** O motivo: a integração usa o transporte `"stdio"` (comando local). Isso significa que é o PRÓPRIO G4 OS quem chama `python integrations/g4os_mcp_server.py` como um processozinho descartável, por conta própria, toda vez que o agente dele precisa usar uma das 7 ferramentas -- e não algo que fica "escutando" esperando ser encontrado. Esse comando roda, responde, e pode morrer de novo em segundos. Ele não tem NENHUMA relação com o painel gráfico (`dashboard.py`) estar aberto no navegador ou não -- são dois programas completamente separados hoje. Um `.exe` do painel não mudaria nada nessa dinâmica, porque o G4 OS nem aponta pro painel -- ele aponta direto pro servidor MCP.

   **Se você quer de verdade a dinâmica "só aparece com o app aberto"**, isso é possível, mas é outro desenho: o manual do G4 OS também documenta um segundo tipo de conexão, por HTTP/SSE (uma URL, tipo `http://localhost:PORTA`), em vez do comando local. Nesse modelo, o G4 OS se CONECTA num servidor que precisa estar rodando de verdade -- se você fechar o app, a porta para de responder e o G4 OS perde a conexão. Isso exigiria: (a) transformar o servidor MCP num servidor HTTP de verdade (em vez do modo "comando que roda e morre"), rodando junto do painel dentro do mesmo `.exe`, e (b) trocar o `config.json` registrado no G4 OS de `"transport": "stdio"` pra uma URL local. É mais trabalho que simplesmente compilar, e eu não testei esse caminho ainda (não sei se o G4 OS aceita uma URL `localhost`, só vi documentado o uso com URLs `https://` de serviços de verdade).

   **Ponto solto que vale saber**: o `config.json` registrado mostra `"connectionStatus": "untested"` -- ou seja, mesmo a conexão atual (via comando local) nunca foi confirmada de dentro do G4 OS de verdade (só testei o servidor MCP sozinho, como já estava documentado desde a Rodada 6). Vale abrir o G4 OS e conferir se o source "Churn Engine" aparece conectado, independente de qualquer decisão sobre o `.exe`.

**Pergunta em aberto pra você decidir antes de eu construir qualquer coisa**: quer manter a dinâmica atual (G4 OS sempre enxerga a ferramenta, painel aberto ou fechado -- mais simples, já funciona hoje) ou prefere a dinâmica "só quando o app está aberto" (exige o redesenho pro modo HTTP local, mais trabalho e não testado ainda)? A resposta muda o que eu construo a seguir.


### Rodada 23 — os dois pontos que faltavam do `.exe` corrigidos e testados de verdade, e um limite real descoberto sobre onde dá pra compilar

Você escolheu manter a dinâmica atual do G4 OS ("sempre visível, como já é hoje" -- não vale a pena o trabalho extra do modo HTTP) e autorizou seguir com o `.exe` de verdade ("pode prosseguir").

**1. Os dois pontos que a Rodada 22 tinha deixado como "falta resolver" -- resolvidos e testados.**

   A Rodada 22 achou que `main.py --painel` (abrir o painel) e `dashboard.py` rodando o motor pra dados próprios quebravam num `.exe` compilado, porque os dois chamavam `sys.executable` como se fosse um Python de verdade por fora (`-m streamlit run dashboard.py`, ou `main.py` como argumento) -- e dentro de um `.exe`, `sys.executable` já É o próprio `.exe`, sem ter Python nem `main.py` separado pra apontar.

   Corrigido dos dois lados:
   - `main.py`: `opcao_painel()` agora chama o Streamlit por dentro do próprio processo (`from streamlit.web import cli as stcli; stcli.main(args=["run", caminho_dashboard, ...], standalone_mode=False)`) em vez de abrir um processo novo. O `standalone_mode=False` importa de verdade: sem ele, a chamada encerra o programa inteiro sozinha assim que você fecha o navegador e aperta Ctrl+C -- o que quebraria o menu interativo (que precisa voltar pro menu depois, não sair). Testei isso isolado antes de confiar (script só pra provar que a chamada retorna normal depois do Ctrl+C, em vez de derrubar tudo).
   - `main.py`: `opcao_validar()` idem -- chama `validar_outputs.main()` direto por import, em vez de abrir `validar_outputs.py` como programa separado.
   - `dashboard.py`: `rodar_com_dados_proprios()` monta o comando do subprocesso checando `sys.frozen` -- rodando compilado, chama só `sys.executable` com as flags (sem "main.py" no meio, que só faz sentido rodando `python main.py`); rodando normal, continua como antes.
   - Criei também `pasta_base()` em `main.py`: rodando `python main.py`, é a pasta do projeto de sempre; rodando compilado, vira a pasta onde o `.exe` está (é lá que `data/`, `configs/` e `dashboard.py` moram ao lado do binário).

   **Testado de verdade, não só compilado e torcido pra dar certo**: montei um `.exe` de teste (ainda em Linux, ver item 2) com essas correções e rodei uma bateria completa por navegador automatizado contra o binário compilado de verdade -- abri o painel pelo `--painel`, confirmei que a sessão do desafio aparece (prova que `pasta_base()` funciona compilado), fui em "📥 Meus dados", subi os 5 CSVs reais do RavenStack, rodei o diagnóstico -- e o botão disparou corretamente um SEGUNDO processo do mesmo `.exe` compilado (a correção do `dashboard.py`) pra processar os dados. Resultado: sucesso, sem nenhum erro de JavaScript, mesmo resultado de sempre (98 contas em risco).

**2. Dois problemas novos de empacotamento, achados só ao compilar com o Streamlit incluído (a Rodada 22 só tinha compilado o motor sozinho, sem o painel).**
   - `PackageNotFoundError: No package metadata was found for streamlit` -- o Streamlit lê sua própria versão internamente a partir de metadado de pacote que o PyInstaller não inclui por padrão. Corrigido com a flag `--copy-metadata streamlit`.
   - Depois de corrigir isso, o servidor subia mas devolvia HTTP 404 na página inicial -- faltavam os arquivos estáticos do frontend (JS/CSS) do Streamlit, que também não vêm por padrão. Resolvido trocando pra uma flag mais abrangente, `--collect-all streamlit` (inclui dados, binários e submódulos de uma vez), confirmado com `curl` (HTTP 200) e com o navegador automatizado renderizando a interface de verdade, sem nenhum erro no console.

**3. Achado importante sobre ONDE dá pra compilar -- muda o que eu consigo fazer sozinho a partir daqui.**

   Antes de gerar o `.exe` "de verdade" no seu computador, conferi onde o comando que uso pra mexer nos seus arquivos (`device_bash`) realmente roda -- e não é o Windows. É uma VM Linux isolada dentro do seu computador (confirmei com `uname`: Ubuntu 22.04), que só enxerga as pastas conectadas através de um "compartilhamento" -- não tem PowerShell, não tem `cmd.exe`, não tem Python de Windows. Compilar por ali geraria outro binário Linux (ELF), do mesmo jeito que os testes das Rodadas 22 e 23 -- não um `.exe` de Windows de verdade, mesmo que o arquivo confirmasse "rodando no seu computador".

   Testei também a outra ferramenta que tenho pra mexer na sua tela de verdade (controle remoto de mouse/teclado) como alternativa -- mas ao pedir acesso a um terminal (pra rodar os comandos de compilação de verdade, no Windows de verdade), o próprio sistema avisou que terminais e IDEs só podem ser liberados em "modo clique": consigo ver a tela e clicar, mas não digitar nem apertar tecla nenhuma ali -- trava de propósito, como proteção contra automação de comandos arbitrários no seu computador. Não tentei contornar essa trava (ex: dar duplo-clique num script pra fugir de "digitar num terminal") porque é claramente um limite de segurança posto ali de propósito, não uma limitação técnica boba.

   **Conclusão honesta**: não tem como eu compilar o `.exe` de Windows de verdade sozinho, daqui, com as ferramentas que tenho. O que eu ARRUMEI e TESTEI de verdade (item 1) é real e vale independente disso -- só a compilação final precisa acontecer com você apertando o botão.

**4. O que ficou pronto pra você rodar.** Criei `build_exe.py` (script Python, sem `.bat`, seguindo a regra de sempre) com a receita inteira já validada nos testes das Rodadas 22-23: confere se você está mesmo no Windows, instala o PyInstaller sozinho se estiver faltando, compila com `--onedir --collect-all streamlit`, e depois copia pra dentro da pasta compilada os arquivos que o painel precisa como `.py` solto (`dashboard.py` e os módulos que ele importa direto), mais `data/` e `configs/` inteiras. Um comando só: `python build_exe.py`, rodando dentro da pasta `churn_engine` no seu Windows de verdade. Sincronizado e conferido por hash (md5sum) direto no arquivo do seu computador, igual sempre: `main.py` (`3e8dc3d77d1d0eef0807152c8eab35be`), `dashboard.py` (`a1ffcbd07ba3ae8773ceee7d86f5c23a`) e `build_exe.py` (`6cba116804ed08b4dfa7732f9d987940`) -- os três batendo com o que está aqui.

**Pendente**: você rodar `python build_exe.py` no seu Windows. Depois disso eu confiro o resultado lendo a pasta gerada direto do seu computador (não só confiando que "rodou sem erro"), e testamos o `.exe` de verdade -- incluindo os pontos que só existem no Windows real (o botão "abrir pasta no Explorador", por exemplo) que a bateria de testes em Linux não cobre.


### Rodada 24 — removido o botão "Deploy" do painel

Você pediu pra tirar a parte de "Deploy" do painel gráfico. Não era nada escrito no código do projeto (procurei em todos os arquivos, não achei "deploy" em lugar nenhum) -- é um botão que o próprio Streamlit desenha sozinho no canto superior direito de qualquer app, servindo pra publicar no Streamlit Community Cloud. Não faz sentido aqui (é um programa local, não tem "nuvem" pra mandar publicar), e também não era algo que eu tinha colocado -- vem de fábrica.

Testei três formas antes de decidir: o Streamlit tem uma opção (`toolbarMode`) com 4 valores possíveis. Escolhi `"minimal"` depois de testar ao vivo (servidor local + captura de tela) -- ela tira a barra inteira (Deploy E o menu de três pontinhos do lado, que só tinha itens de desenvolvedor tipo "Clear cache"/"Print"/"About", sem uso real pra quem só quer ver o diagnóstico). Conferi que o "Deploy" não aparece nem escondido no HTML da página, não só visualmente.

Implementado como um arquivo de configuração do Streamlit (`.streamlit/config.toml`, com `toolbarMode = "minimal"`), não uma flag passada na hora de chamar -- assim vale tanto rodando `python main.py --painel` quanto `streamlit run dashboard.py` direto quanto dentro do `.exe` compilado, sem precisar repetir a mesma flag em três lugares. Atualizei também `build_exe.py` pra copiar essa pasta `.streamlit/` pra dentro da distribuição final, do lado de `data/` e `configs/` -- senão o botão voltaria a aparecer só no `.exe`.

Testado de ponta a ponta com o painel de verdade (não só o teste isolado): rodei `dashboard.py` do jeito que ele roda normalmente, tirei print da tela inteira -- canto superior direito limpo, sidebar e abas normais, nada quebrado.

Arquivos sincronizados e conferidos por hash direto no seu computador: `.streamlit/config.toml` (`5900bb7b615674335c2d18de8400af26`) e `build_exe.py` (`be4f04bdc397bf7bd0ec990c96b403cb`).


### Rodada 25 — você compilou de verdade, e um achado grande: o `.exe` saiu com 5 GB (bibliotecas de IA que não têm nada a ver com o projeto)

Você rodou `python build_exe.py` no seu Windows de verdade -- primeira compilação real, fora de qualquer proxy Linux. Conferi direto no seu computador (não só na sua palavra): a pasta `dist/churn_engine/` existe, o `churn_engine.exe` começa com os bytes `MZ` (assinatura real de executável do Windows -- não é um binário Linux disfarçado), o `.streamlit/config.toml` da Rodada 24 foi copiado certinho pra dentro. **Confirmado: o build funcionou.**

Só que a pasta inteira deu **5 GB** -- bem acima da faixa de 250-400 MB que eu tinha estimado na Rodada 22. Antes de você perguntar sobre mandar pra outra pessoa, isso já merecia investigação: 5 GB não é algo que dá pra mandar por e-mail, Drive lento, nem nada prático.

**Causa raiz, achada olhando o tamanho de cada pasta dentro de `_internal/`**: 4 GB sozinhos eram da biblioteca **PyTorch**, mais 113 MB de OpenCV, 102 MB de uma biblioteca de compilação (`llvmlite`), 84 MB de processamento de vídeo, 46 MB da biblioteca `transformers` (Hugging Face), 34 MB de `onnxruntime` -- nenhuma dessas bibliotecas tem QUALQUER relação com o `churn_engine` (conferi com `grep` em todos os arquivos do projeto -- nenhum importa nada disso). A explicação real: o Streamlit tem um arquivo interno (`runtime/metrics_util.py`) com uma lista de ~170 nomes de bibliotecas populares de IA/dados/nuvem que ele *verifica se estão instaladas* só pra fins de telemetria (reportar quais bibliotecas o app usa, nunca são exigidas pra rodar) -- e o seu Python (instalado direto no sistema, sem um ambiente isolado por projeto) tem instalado, pra outros usos seus, coisas como PyTorch. O PyInstaller, ao empacotar o Streamlit inteiro (`--collect-all`), acaba enxergando essas checagens e leva junto qualquer uma dessas ~170 bibliotecas que por acaso estiver instalada na máquina -- mesmo sem nenhuma relação real com o programa.

**Corrigido em `build_exe.py`**: adicionei uma lista explícita (`EXCLUSOES_TELEMETRIA`, as ~170 bibliotecas do `metrics_util.py` do Streamlit, menos as que a gente realmente usa -- numpy, pandas, plotly, sklearn, streamlit, e `openpyxl`, que `leitor_arquivos.py` precisa de verdade pra ler `.xlsx`) e passei cada uma como `--exclude-module` pro PyInstaller. Também fiz o script limpar sozinho qualquer `dist/`/`build/` de uma compilação anterior antes de compilar de novo -- pra nunca misturar lixo de uma rodada velha com a nova.

**Testado antes de mandar pra você rebuildar**: refiz o build (ainda em Linux, mesmo processo de sempre) com as exclusões, numa máquina que tinha OpenCV e `onnxruntime` instalados de propósito pra reproduzir o problema -- confirmei que os dois sumiram da pasta compilada, e testei de ponta a ponta pelo navegador automatizado: painel abrindo, e dessa vez **de propósito enviei um arquivo `.xlsx` de verdade** (não só CSV) pra confirmar que excluir tudo isso não quebrou a leitura de Excel (`openpyxl` continua funcionando) -- upload dos 5 arquivos (1 Excel + 4 CSV), diagnóstico rodado, 98 contas em risco, gráfico de risco e tabela de contas renderizando certo, ROC-AUC 0.562 idêntico ao de sempre, zero erro de JavaScript real (só ruído esperado de telemetria do Streamlit bloqueada pela rede daqui, sem relação com o app). Achado de processo: minha primeira tentativa de checar "terminou com sucesso" deu falso positivo (achei o texto "98" na tela cedo demais, antes do processamento realmente terminar) -- corrigi esperando de verdade o aviso "Pronto!" sumir do spinner antes de considerar concluído, mesmo cuidado que já tinha documentado como necessário nas Rodadas 20-22.

Com as exclusões, essa mesma pasta de teste caiu de "seria 5 GB+" pra **624 MB** (nessa máquina de teste, que só tinha 2 das bibliotecas grandes instaladas -- na sua, que tem o PyTorch de 4 GB sozinho, a redução real deve ser ainda maior).

**Sobre "mandar pra qualquer pessoa rodar no PC dela"**: sim, é exatamente pra isso que serve um `.exe` compilado desse jeito (`--onedir`) -- quem recebe NÃO precisa ter Python instalado, só um Windows de 64 bits (o mesmo tipo do seu; não funciona em Mac, Linux, nem Windows ARM). Duas coisas reais pra saber antes de mandar, que já deixei escritas no final do próprio `build_exe.py` (ele agora imprime isso depois de compilar):
- **Tem que mandar a pasta inteira compactada num `.zip`**, não só o `.exe` -- ele depende de tudo ao lado dele (`_internal/`, `data/`, `configs/`, `.streamlit/`, os `.py` soltos). Com milhares de arquivos, sem compactar é inviável de mandar.
- **É esperado que o Windows Defender (ou outro antivírus) avise "Windows protegeu seu PC"** na primeira vez que a pessoa abrir o `.exe`, mesmo sem nada de errado -- é comum em programas feitos com PyInstaller, por não ter uma assinatura digital paga por trás (isso custa dinheiro e não faz sentido pra um projeto de desafio). A pessoa clica em "Mais informações" → "Executar assim mesmo". Não tem como eu evitar esse aviso sem comprar um certificado de assinatura de código -- é uma limitação real, não um bug.

`build_exe.py` sincronizado e conferido por hash direto no seu computador: `ca4b3fb150682980eb14682aedcce9a6`.

**Pendente**: você rodar `python build_exe.py` de novo (o script já limpa a pasta de 5 GB antiga sozinho) pra gerar a versão enxuta de verdade no seu Windows -- aí eu confiro o tamanho final real e testamos o `.exe` enxuto no seu computador antes de considerar isso pronto pra mandar pra alguém.

**Atualização, mesma rodada -- você já rodou de novo.** Conferi direto no seu computador: **336 MB** (contra os 5 GB de antes), `churn_engine.exe` continua com a assinatura real de executável do Windows (`MZ`), e `_internal/` já não tem mais `torch`, `cv2`, `transformers`, `onnxruntime` nem `llvmlite` -- só sobrou o que o projeto realmente usa (`pyarrow` 80 MB, `scipy` 49 MB, `streamlit` 29 MB, `pandas` 17 MB, `sklearn` 14 MB, `plotly` 13 MB, `PIL` 11 MB, e mais alguns pequenos). A correção da exclusão de bibliotecas funcionou de verdade, não só na minha simulação em Linux.

Tentei abrir o `.exe` eu mesmo, com o controle remoto de tela, só pra te mostrar rodando -- mas sem poder digitar (mesma trava de segurança da Rodada 23), navegar até `dist\churn_engine\` só no clique, pasta por pasta, não deu certo em duas tentativas. Pedi pra você testar direto (dar 2 cliques no `.exe`) -- resposta registrada assim que chegar.


### Rodada 26 — corrigido o que abre quando dá 2 cliques no `.exe`

Você testou o `.exe` enxuto (336 MB) e achou um problema de comportamento: dando 2 cliques nele, abria o menu de terminal, em vez do painel gráfico direto -- e como hoje dá pra fazer tudo pelo painel (rodar com dados de exemplo ou próprios, ver histórico de análises, IA de ação), não fazia sentido mais mostrar o menu primeiro.

Isso não era um bug -- era o comportamento pedido explicitamente lá na Rodada 15 (`python main.py` sem argumento → menu; `python main.py --painel` → painel direto). Fazia sentido na época, quando o painel ainda não cobria tudo. Agora que cobre, sem argumento nenhum passou a abrir o painel direto -- e como dar 2 cliques no `.exe` é exatamente "rodar sem nenhum argumento", o comportamento do clique duplo muda junto, de graça.

Não apaguei o menu de terminal (ainda é útil pra rodar rapidinho sem abrir navegador, ou conferir `outputs/` depois) -- só deixou de ser o padrão. Agora fica atrás de um `--menu` explícito (`python main.py --menu`, ou `churn_engine.exe --menu`).

**Testado antes de sincronizar**: rodei `python main.py` sem nenhum argumento e confirmei que abre o painel direto (servidor respondendo, `HTTP 200`) sem passar pelo menu; rodei `python main.py --menu` e confirmei que o menu de terminal antigo continua funcionando normalmente (as 5 opções aparecem, "5) Sair" funciona); e rodei com os argumentos explícitos de sempre (`--config`, `--accounts`...) pra confirmar que esse caminho (usado pelo painel e por quem quiser apontar pra outra fonte de dados) não foi afetado -- 500 contas, 98 em risco, ROC-AUC 0.562, idêntico ao de sempre.

`main.py` sincronizado e conferido por hash direto no seu computador: `897d680c625df1210fa9a661e73c2d0e`.

**Pendente**: como isso é uma mudança de código-fonte (`main.py`), só vale de verdade depois de recompilar -- rode `python build_exe.py` mais uma vez pra gerar o `.exe` com esse comportamento novo.


### Rodada 27 — dois bugs reais no `.exe` recompilado: a análise do desafio vinha sem resultado, e o seu histórico pessoal de testes vazava pra quem recebesse o programa

Você recompilou e rodou o `.exe` de verdade -- e apareceu um erro ("Faltam arquivos em outputs/processed/...") junto com DUAS sessões na barra lateral, quando deveria ter só uma (a do desafio). Isso não era frescura de UX, eram dois bugs reais em `build_exe.py`, os dois meus.

**Causa raiz, achada lendo direto os arquivos do `.exe` no seu computador (não só a mensagem de erro na tela):**

1. **`outputs/` nunca era copiado pro `.exe`.** A pasta `outputs/` do projeto tem os resultados JÁ CALCULADOS dos dados de exemplo do desafio (`super_tabela_churn.csv`, `risco_churn_api.json`, os 98 em risco, etc.) -- é o que a sessão "Diagnóstico do desafio" mostra. `build_exe.py` copiava `data/` (os CSVs brutos) e `configs/` mas esquecia de copiar `outputs/` (o resultado pronto) -- então na cópia compilada, a sessão do desafio existia na lista mas apontava pra uma pasta vazia. Daí o erro.

2. **`configs/historico_analises.json` ia inteiro, do jeito que estava na sua máquina.** Esse arquivo guarda o HISTÓRICO PESSOAL de análises que você já rodou -- inclusive testes seus de 20/09 (uma "Análise 20/09 19:47", de quando você testou com dados próprios direto pelo `python main.py`, antes de qualquer `.exe`). `build_exe.py` copiava esse arquivo inteiro pro `.exe`, o que significa que **qualquer pessoa que recebesse o programa veria o SEU histórico de testes** na barra lateral dela -- e, pior, a entrada apontava pra uma pasta (`outputs_analises\analise_20260920_194750\`) que nunca foi copiada, dando o mesmo erro de "faltam arquivos" nela também.

**Corrigido nos dois pontos, em `build_exe.py`:**
- `outputs/` (o resultado calculado) agora é copiado igual `data/`, `configs/` e `.streamlit/` já eram.
- `configs/` deixou de ir inteira -- só o arquivo de mapeamento dos dados de exemplo (`mapping_ravenstack.json`) é copiado; `historico_analises.json` é recriado do zero, vazio (`[]`), dentro do `.exe`. Isso também tira de quebra uma pilha de arquivos de mapeamento de teste (`mapping_fonte_b.json`, `mapping_fonte_c*.json` etc. -- sobras de fontes de teste de rodadas bem anteriores) que não tinham motivo nenhum de ir pra uma cópia distribuída.

Com o histórico vazio e `outputs/` presente, o próprio painel recria sozinho, na primeira vez que abre, EXATAMENTE uma sessão -- "Diagnóstico do desafio (dados RavenStack)" -- e mais nenhuma. É o que você pediu: uma sessão com a análise dos arquivos do desafio, e fim.

**Resolvido em duas camadas, pra não te deixar esperando um rebuild inteiro:**
1. **Hotfix imediato, direto na cópia que já estava rodando no seu computador**: copiei `outputs/` pra dentro do `.exe` já compilado e zerei o `historico_analises.json` dele, sem precisar recompilar -- só arquivo sendo copiado/trocado no disco, o `.exe` em si não muda. Testado antes de mexer (simulei a mesma estrutura aqui e rodei de ponta a ponta com navegador automatizado): sem erro, uma sessão só, resultado aparecendo certo.
2. **Correção definitiva em `build_exe.py`**, testada com a mesma simulação antes de sincronizar, pra qualquer rebuild futuro sair limpo sozinho, sem precisar desse hotfix manual de novo.

`build_exe.py` sincronizado e conferido por hash direto no seu computador: `68be0105db6c3ed4523ebc5b9786d73b`.

**Você não precisa recompilar agora** -- o hotfix já deixou a cópia atual funcionando. Só dê F5 no navegador. Se quiser gerar uma cópia 100% limpa do zero mais tarde (por exemplo, pra mandar pra outra pessoa), `python build_exe.py` já vai sair certo sozinho a partir de agora.


### Iterações

Pelo menos 27 rodadas até aqui: (1) análise cruzada inicial, (2) ajuste de estratégia documentado, (3) implementação do código com 3 bugs corrigidos ao rodar de verdade, (4) correção da avaliação do modelo de ML depois de pedir validação cruzada, (5) tentativa de melhorar o modelo com duas hipóteses testadas, (6) prova concreta de que tudo funciona (validação automatizada + troca de fonte real + Fase 2 funcionando de ponta a ponta), (7) painel/Power BI/G4 OS investigados e testados de verdade, (8) auditoria da documentação e consolidação do README de submissão, (9) painel com ajuda embutida + terceira fonte (português) + simulação da camada de decisão com IA + integração MCP real e testada com o G4 OS, (10) limpeza das pastas de output e guia simplificado, (11) tentativa (corrigida na rodada seguinte) de menu gráfico pro upload de dados próprios, (12) menu de terminal real (`rodar.py`/`RODAR.bat`), (13) achado documentado sobre variação do ROC-AUC entre versões do scikit-learn, (14) instalação automática de dependências + menu explicado + `VER_PAINEL.bat` (rodada revertida na seguinte), (15) tudo fundido em `main.py` -- `python main.py` (menu) e `python main.py --painel` (painel direto), sem nenhum arquivo `.bat`, (16) tabelas opcionais (com achado sobre o score de regra zerando) + aba de IA no painel (local ou API, com teste de compatibilidade) + G4 OS com acesso total às 7 ferramentas, (17) leitura de CSV/Excel/JSON misturados (menu e painel) + caixa de "onde estão os resultados" no painel (caminho, botão de abrir pasta, download de cada arquivo) + respostas sobre o papel da IA e como testar no G4 OS, (18) testado o G4 OS ao vivo (skill achado e ativado, achado real sobre créditos de conta) + histórico de análises na barra lateral do painel (tipo lista de conversas, uma pasta própria por análise, ações de IA salvas por análise), (19) removido campo de texto manual de pasta e botão solto de escolher pasta (fora do contexto de uma análise), diagnóstico e correção do seletor nativo do Windows aparentando travar (owner TopMost + spinner visível), e controle total dentro de uma sessão de análise (rodar de novo atualizando a mesma entrada, apagar com confirmação em 2 cliques), (20) removida de vez a seção "Avançado" da barra lateral, a análise do desafio (RavenStack) virou uma sessão de verdade com os mesmos poderes de qualquer outra, e corrigido um UnicodeEncodeError real no Windows (emoji em print + subprocess sem console = trava em cp1252; corrigido forçando UTF-8 em stdout/stderr), (21) corrigido um KeyError real (campo opcional individual deixado sem mapear travando o pipeline inteiro, em 4 funções diferentes do motor), (22) revisão final testada de ponta a ponta (2 problemas reais achados e corrigidos: `use_container_width` descontinuado e arquivos órfãos em `_entrada/`) + investigação de executável Windows (achado e corrigido um risco real de cascata de processos num `.exe` compilado; mapeado o que falta pra funcionar de verdade) + investigação da integração com G4 OS (confirmado que hoje ele já enxerga a ferramenta com o painel aberto ou fechado, e o que mudaria isso), (23) corrigidos e testados de ponta a ponta (contra um `.exe` compilado de verdade) os dois pontos que faltavam pro painel funcionar compilado; achados e corrigidos 2 problemas novos de empacotamento do Streamlit (metadado faltando, depois arquivos estáticos faltando); descoberto e documentado um limite real -- a ferramenta que uso pra mexer no seu computador roda numa VM Linux isolada, sem PowerShell nem Python de Windows, então não dá pra compilar o `.exe` de Windows de verdade sozinho daqui; testada e descartada a alternativa de controle de tela (terminais só em modo clique, trava de segurança de propósito); entregue `build_exe.py`, um comando só (`python build_exe.py`) pra você compilar de verdade no seu Windows com a receita já validada, (24) removido o botão "Deploy" nativo do Streamlit (não era código do projeto, vem de fábrica) via `.streamlit/config.toml` com `toolbarMode = "minimal"`, testado ao vivo e propagado também pra dentro do `.exe` (atualizado `build_exe.py` pra incluir essa pasta na distribuição), (25) primeira compilação real no Windows confirmada (bytes `MZ`, .exe de verdade) -- mas achado um problema grande: 5 GB de bibliotecas de IA (PyTorch sozinho com 4 GB, mais OpenCV, transformers, onnxruntime) sendo empacotadas por engano, sem nenhuma relação com o projeto (vêm de uma lista de telemetria interna do Streamlit combinada com o Python global do usuário ter essas bibliotecas instaladas pra outros fins); corrigido excluindo explicitamente ~170 bibliotecas não usadas do build, testado de ponta a ponta com upload de Excel de propósito (conferindo que `openpyxl` não foi quebrado pela exclusão) -- pasta de teste caiu de potencialmente 5 GB+ pra 624 MB, e no rebuild real no seu Windows caiu pra 336 MB; documentado também o que é preciso saber pra mandar o `.exe` pra qualquer pessoa (compactar em `.zip`, aviso esperado do Windows Defender), (26) corrigido o ponto de entrada padrão do programa (sem argumento nenhum, que é o que 2 cliques no `.exe` fazem) -- antes caía no menu de terminal, agora abre direto o painel gráfico, já que hoje dá pra fazer tudo por lá; o menu antigo continua existindo, só que atrás de um `--menu` explícito, em vez de ser o padrão, (27) dois bugs reais achados no `.exe` recompilado: a sessão "Diagnóstico do desafio" abria com erro (`outputs/`, o resultado já calculado, nunca era copiado pro `.exe`) e o seu histórico pessoal de testes (`configs/historico_analises.json`, com análises que você rodou direto por `python main.py`) vazava inteiro pra dentro de qualquer cópia distribuída, causando uma segunda sessão quebrada na barra lateral de quem recebesse o programa; corrigido `build_exe.py` nos dois pontos (agora copia `outputs/`, e `historico_analises.json` nasce vazio em toda compilação nova) e aplicado um hotfix imediato direto na cópia que já estava rodando no seu computador, sem precisar recompilar.

---

*Este documento continua sendo escrito conforme o trabalho avança -- não é a versão final do process log da submissão.*
