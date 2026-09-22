# Como rodar o Churn Engine

Há duas formas. A **Forma 1** não exige Python nem nenhuma instalação.

---

## Forma 1 — Executável Windows (sem instalar nada)

1. Baixe o arquivo **`churn_engine_windows.zip`** (~150 MB) na página de Release:
   **https://github.com/candidozara/ai-master-challenge/releases/tag/churn-engine-v1.0**
2. Clique com o botão direito no zip → **Extrair tudo…** (não rode de dentro do zip — o programa precisa das pastas ao lado dele).
3. Abra a pasta extraída e dê **dois cliques em `churn_engine.exe`**.
4. Uma janela preta abre e, em alguns segundos (a primeira vez pode levar ~30 s), o **painel abre sozinho no navegador**.
   - Se o navegador não abrir, copie o endereço `http://localhost:...` que aparece na janela preta e cole no navegador.
5. **Deixe a janela preta aberta** enquanto usa o painel. Para encerrar, é só fechá-la.

> **Aviso do Windows ("O Windows protegeu o computador")**: aparece porque o executável não tem assinatura digital paga. Clique em **Mais informações → Executar assim mesmo**.

### O que dá pra fazer no painel

- **Ver o diagnóstico do desafio** — já vem calculado com os dados da RavenStack (contas em risco, segmentos, motivos de churn, qualidade do modelo).
- **Rodar com os seus próprios dados** — aba **📥 Meus dados**: envie seus arquivos (CSV, Excel ou JSON), faça o De/Para das colunas na tela e gere uma nova análise.
- **🧠 IA de ação** — sugestão de próxima ação por conta (opcional; usa um modelo local, como Ollama ou LM Studio, ou uma chave de API da Anthropic).
- **Histórico de análises** — cada rodada fica salva e pode ser reaberta.
- Aba **❓ Como usar** — explica cada gráfico e cada número.

Os relatórios (CSV, JSON, PDF, Markdown) ficam na pasta `outputs/`, ao lado do `.exe`.

---

## Forma 2 — Pelo código-fonte (Python 3.10+)

```bash
cd solution/churn_engine
pip install -r requirements.txt
python main.py
```

| Comando | O que faz |
|---------|-----------|
| `python main.py` | Abre o **painel** no navegador (mesma tela do executável) |
| `python main.py --menu` | Menu no terminal (rodar com dados de exemplo, com dados próprios, validar, sair) — sem navegador |
| `python main.py --output-dir outputs` | Roda o motor direto com os dados de exemplo e gera os relatórios em `outputs/` |
| `python validar_outputs.py` | Confere se as 4 saídas (CSV / JSON / PDF / Markdown) estão corretas e consistentes entre si |

> Se faltar alguma biblioteca, o `main.py` tenta instalar sozinho na primeira execução — mas o `pip install -r requirements.txt` acima é o caminho garantido.

### Gerar o executável você mesmo (opcional)

No Windows, dentro de `solution/churn_engine`:

```bash
python build_exe.py
```

O resultado fica em `dist/churn_engine/churn_engine.exe` (as pastas `build/` e `dist/` não vão para o repositório por serem geradas e grandes).
