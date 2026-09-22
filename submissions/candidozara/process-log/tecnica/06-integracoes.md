## Integrações: painel local, Power BI e G4 OS

Esse documento fecha o pedido de "uso real": como o `churn_engine` roda sozinho, como conecta em ferramentas de fora, e como ele poderia se acoplar no G4 OS de verdade.

---

### 1. Painel local (Streamlit) — já funciona

`tecnica/churn_engine/dashboard.py`. Roda no seu computador, lê os arquivos que `main.py` já gera (não recalcula nada sozinho — só visualiza). Testei rodando de verdade (servidor local + captura de tela) antes de entregar: KPIs, segmentação por indústria/canal/plano, distribuição de risco, top contas em risco, e a seção do modelo preditivo com o ROC-AUC explicado em português simples.

```bash
cd tecnica/churn_engine
pip install -r requirements.txt
streamlit run dashboard.py
```

Ele tem um seletor de pasta na barra lateral (`outputs`, `outputs_fonte_b`, `outputs_sugerido`, ou qualquer pasta nova que você gerar) — funciona **junto** com o motor (roda `main.py`, aperta "recarregar" no painel) e **separado** dele (abre uma pasta de resultado antiga sem rodar nada de novo).

### 2. Power BI — conectar direto, sem eu reinventar um dashboard

Como você já pediu pra não reinventar isso: o motor já exporta `outputs/processed/super_tabela_churn.csv` (a Super Tabela, 1 linha por conta com todos os scores) e `segmentos_risco.csv`. No Power BI Desktop:

1. **Página Inicial → Obter Dados → Texto/CSV** → aponte para `super_tabela_churn.csv`. Repita para `segmentos_risco.csv` e `risco_churn_api.json` (esse último via **Obter Dados → JSON**).
2. No Poder Query, marque `canonical_id` como chave e confirme os tipos (`canonical_is_churn_account` como booleano, `canonical_revenue` como decimal).
3. Crie um relacionamento entre `super_tabela_churn` e `risco_churn_api` por `canonical_id`, se quiser cruzar as duas visualmente.
4. Para os dados **atualizarem sozinhos** toda vez que você rodar `main.py` de novo: no Power BI, configure a pasta `outputs/processed/` como fonte e use "Atualizar" — ou, se quiser automatizar de verdade, o `main.py` pode ser agendado (Agendador de Tarefas do Windows) pra rodar toda manhã e o Power BI só precisa dar refresh na hora certa.

Isso é literalmente o que a arquitetura em camadas foi desenhada pra permitir desde o início: o motor não sabe (nem precisa saber) que existe um Power BI do outro lado — ele só entrega CSV/JSON num contrato estável.

### 3. G4 OS — integração real, feita e testada (não é mais só recomendação)

Na primeira rodada eu tinha olhado só `AppData\Local\Programs\G4 OS` (a instalação, Program Files) e tinha ficado nisso: confirmei Electron, runtime com Node/Bun/Python-via-uv (sem Ruby), e a presença de `claude-agent-sdk` + servidores MCP + um sistema de skills — o suficiente pra recomendar "empacotar como skill" em vez de API REST, mas sem poder fazer isso de fato porque eu não sabia onde ficava sua área de dados real.

Com sua autorização explícita ("Começar agora" + "pode procurar"), localizei essa área de verdade: **`~/.g4os-public/workspaces/my-workspace/`** (não `~/.g4os`, que está praticamente vazio — só log de erro; e a documentação interna do próprio G4 OS, em `docs/skills.md` e `docs/sources.md`, descreve o caminho como `~/.g4os/...`, mas na prática, neste computador, é `~/.g4os-public/...` que tem as 20+ sessões reais, as skills de verdade e as dezenas de sources conectadas — achado que registrei porque contraria o texto oficial). Essa pasta tem, entre outras coisas, os próprios manuais internos do G4 OS (`docs/skills.md`, `docs/sources.md`) explicando exatamente o formato de skill e de "source" (conector) que o agente dele entende.

**O que foi feito, testado e já está no seu G4 OS:**

1. **Servidor MCP de verdade** (`tecnica/churn_engine/integrations/g4os_mcp_server.py`) — expõe 7 ferramentas tipadas do motor pro agente do G4 OS chamar diretamente (não é "leia o README", é chamada de função):
   - `rodar_diagnostico`, `listar_contas_risco`, `obter_segmentos_risco`, `obter_metricas_modelo`, `sugerir_mapeamento_coluna`, `decidir_acoes_recomendadas`, `validar_saida`.
   - Testado com um cliente MCP real (protocolo stdio, não simulado): as 7 ferramentas aparecem, e várias foram chamadas de verdade contra os dados (inclusive a Fonte C). Um bug real apareceu (a versão mais nova da lib `mcp`, 2.x, quebra a API usada) e foi corrigido fixando `mcp>=1.0,<2.0` no `requirements.txt`.
2. **Source registrado** em `~/.g4os-public/workspaces/my-workspace/sources/churn-engine/` (`config.json` + `guide.md` + `permissions.json`, no formato exato de `docs/sources.md`) — aparece pro agente do G4 OS como um conector chamado "Churn Engine", com as ferramentas de leitura liberadas no modo Explorar e as que escrevem dados (`rodar_diagnostico`, `decidir_acoes_recomendadas`) exigindo confirmação.
3. **Skill registrada** em `~/.g4os-public/workspaces/my-workspace/skills/churn-diagnostico/SKILL.md` — ensina o agente do G4 OS QUANDO usar essas ferramentas (perguntas sobre churn, contas em risco, segmentos) e em que ordem (mapear → rodar → validar → só depois decidir ação).
4. Uma **cópia de tudo isso** fica também dentro do projeto, em `tecnica/churn_engine/integrations/` (`g4os_source/`, `g4os_skill/`) — documentado, não escondido só dentro da pasta de dados do G4 OS.

**O que eu não consegui testar daqui**: não tenho como abrir o G4 OS de verdade e conversar com o agente dele — só validei que o servidor MCP funciona sozinho e que os arquivos de registro seguem exatamente o formato que a documentação interna do G4 OS pede. Na primeira vez que você abrir o G4 OS depois disso, vale conferir se o source "Churn Engine" aparece conectado. Se ele não achar o comando `python`, o ajuste é trocar o campo `command` em `integrations/g4os_source/config.json` (e no arquivo real dentro de `.g4os-public`) pelo caminho completo do Python que você usa pra rodar `main.py` normalmente (`where python` no terminal mostra isso).

### 4. "Com IA" e "sem IA" — os dois modos já existem no código

Você lembrou certo: a Fase 2 precisa ter uma versão com e sem IA. Isso já está implementado em `sugerir_mapping.py`:

- **Sem IA (padrão):** só a heurística de comparação de texto — determinística, offline, de graça. É o que testei e validou 46/50 colunas certas contra a Fonte B.
- **Com IA (`--usar-ia`):** chama a API da Anthropic (`anthropic` SDK) **só** para as colunas que a heurística não resolveu com confiança — nunca reprocessa o que já foi aceito, pra manter custo e latência baixos. Precisa de uma `ANTHROPIC_API_KEY` seu no ambiente. Testei sem a chave (não tenho uma sua aqui) e confirmei que cai de volta pro modo sem IA educadamente, sem quebrar nada, avisando o motivo. Toda sugestão da IA fica marcada como "revisar" — nunca entra direto em produção sem alguém olhar, mesmo vindo da IA.

Isso responde literalmente ao "o sistema deve ter uma versão sem e com IA": é a mesma ferramenta, um parâmetro liga a segunda camada.

---

### Resumo do que ficou provado nesta rodada

Rodei e testei de verdade (não só descrevi): o painel Streamlit com captura de tela real mostrando os números corretos; o modo `--usar-ia` caindo pro modo sem IA de forma segura na ausência de chave; e a stack do G4 OS mapeada o suficiente pra saber que "empacotar como skill" é o caminho certo, não "construir uma API genérica do zero".
