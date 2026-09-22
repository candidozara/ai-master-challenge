# Churn Engine

Motor de diagnóstico de churn (Python/pandas/scikit-learn), construído por
Alessandro Candido Silva para o desafio G4 AI Master e mantido como ferramenta real. Roda
local, não depende de nenhum serviço externo, e expõe as ferramentas abaixo
via MCP para o agente usar diretamente -- sem precisar rodar comandos no
terminal por fora.

## Escopo

Hoje ele já rodou (e foi validado com 18 checagens automáticas) contra três
fontes de dados diferentes: o dataset de exemplo RavenStack (`outputs/`),
uma "Fonte B" com nomes de coluna em inglês diferentes (`outputs_fonte_b/`)
e uma "Fonte C" com nomes de coluna em português (`outputs_fonte_c/`) --
prova de que ele não é amarrado a um formato de arquivo específico.

## Ferramentas disponíveis

- `rodar_diagnostico` -- roda o motor contra uma fonte de dados (padrão ou
  customizada via `config`/`accounts`/`subscriptions`/`usage`/`tickets`/`churn`)
  e devolve o resumo (taxa de churn, MRR perdido, qualidade do modelo).
- `listar_contas_risco` -- lista as contas ativas com maior risco (score
  0-100, determinístico), ordenadas do maior pro menor.
- `obter_segmentos_risco` -- taxa de churn por indústria / canal de
  aquisição / plano.
- `obter_metricas_modelo` -- qualidade do modelo preditivo (ROC-AUC por
  validação cruzada), com interpretação honesta mesmo quando o sinal é fraco.
- `sugerir_mapeamento_coluna` -- para uma fonte de dados NOVA (arquivo com
  nomes de coluna desconhecidos), sugere o mapeamento De/Para automaticamente.
- `decidir_acoes_recomendadas` -- decide uma ação recomendada por conta em
  risco (contato do CS, escalar pra engenharia, revisar SLA). Por padrão usa
  regras simuladas (sem custo); com `usar_ia_real=true` tenta a API da
  Anthropic de verdade se `ANTHROPIC_API_KEY` estiver no ambiente.
- `validar_saida` -- roda as checagens automáticas de qualidade sobre uma
  saída já gerada.

## Limites conhecidos (documentados no README do projeto)

- O score de risco por REGRA (determinístico) é o critério principal.
- O modelo de Machine Learning tem sinal fraco (ROC-AUC ~0.56) neste
  dataset -- é sinal secundário, nunca decide sozinho.
- Nenhuma ferramenta aqui executa ação de verdade (não manda e-mail, não
  abre ticket, não aplica desconto) -- `decidir_acoes_recomendadas` só
  recomenda; uma pessoa decide se aplica.
- `rodar_diagnostico` e `decidir_acoes_recomendadas` ESCREVEM arquivos na
  pasta de output (novos, não sobrescrevem dados originais) -- por isso
  ficam fora da permissão automática do modo Explorar (ver permissions.json).

## Exemplos

- "quais as 10 contas ativas com maior risco agora?" -> `listar_contas_risco`
- "roda o diagnóstico de novo com os dados que estão em D:\dados_amigo" ->
  `sugerir_mapeamento_coluna` pra cada tabela primeiro, depois
  `rodar_diagnostico` com os caminhos
- "o modelo de churn é confiável?" -> `obter_metricas_modelo`
- "o que eu faço com a Company_66?" -> `decidir_acoes_recomendadas`
