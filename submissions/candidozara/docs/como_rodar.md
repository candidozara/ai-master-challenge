# Como rodar o Churn Engine

Há três formas: **1)** usar o executável pronto (sem instalar nada), **2)** rodar pelo código-fonte, **3)** gerar o executável você mesmo.

---

## Forma 1 — Executável Windows (sem instalar nada)

1. Baixe o arquivo **`churn_engine_windows.zip`** (~150 MB) na página de Release:
   **https://github.com/candidozara/ai-master-challenge/releases/tag/churn-engine-v1.0**
2. Clique com o botão direito no zip → **Extrair tudo…** (não rode de dentro do zip — o programa precisa das pastas ao lado dele).
3. Abra a pasta extraída → pasta **`churn_engine`** → dê **dois cliques em `churn_engine.exe`**.
4. Uma janela preta abre e, em alguns segundos (a primeira vez pode levar ~30 s), o **painel abre sozinho no navegador**.
   - Se o navegador não abrir, copie o endereço `http://localhost:...` que aparece na janela preta e cole no navegador.
5. **Deixe a janela preta aberta** enquanto usa o painel. Para encerrar, é só fechá-la.

> **Aviso do Windows ("O Windows protegeu o computador")**: aparece porque o executável não tem assinatura digital paga. Clique em **Mais informações → Executar assim mesmo**.

### O que dá pra fazer no painel

- **Ver o diagnóstico do desafio** — já vem calculado com os dados da RavenStack (contas em risco, segmentos, motivos de churn, qualidade do modelo).
- **Rodar com os seus próprios dados** — aba **📥 Meus dados**: envie seus arquivos (CSV, Excel ou JSON), faça o De/Para das colunas na tela e gere uma nova análise.
- **🧠 IA de ação** — sugestão de próxima ação por conta (opcional). No executável funciona com modelo local (Ollama / LM Studio); a opção com chave de API da Anthropic só funciona rodando pelo código-fonte (Forma 2).
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

---

## Forma 3 — Gerar o executável você mesmo

O `.exe` publicado na Release foi gerado exatamente assim. As pastas `build/` e `dist/` não vão para o repositório (são geradas e passam de 100 MB).

### Pré-requisitos

- **Windows 64 bits** (o executável só roda no mesmo tipo de sistema em que foi gerado — não sai `.exe` de Linux/Mac).
- **Python 3.10 ou mais novo** instalado (o da Release foi gerado com Python 3.14).

### Passo a passo

Abra o **PowerShell** dentro de `solution\churn_engine` e rode:

```powershell
# 1. Ambiente isolado (recomendado — ver "Por que o venv" abaixo)
py -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass   # libera a ativação do venv só nesta janela
.venv\Scripts\activate

# 2. Dependências do projeto (o PyInstaller empacota o que estiver instalado aqui)
pip install -r requirements.txt

# 3. Gerar o executável (instala o PyInstaller sozinho se faltar)
python build_exe.py
```

O `build_exe.py` faz tudo sozinho, nesta ordem:

1. Confere se está no Windows e instala o **PyInstaller** se faltar.
2. Apaga qualquer `build/` e `dist/` de uma geração anterior.
3. Compila o `main.py` em modo `--onedir` com `--collect-all streamlit` (sem isso o painel não abre) e exclui ~170 bibliotecas que o Streamlit só "procura" para telemetria.
4. Copia para dentro de `dist\churn_engine\` o que o painel precisa ao lado do `.exe`: `dashboard.py` e os módulos que ele importa, `data/`, `outputs/` (diagnóstico já calculado), `.streamlit/` e o mapeamento `configs/mapping_ravenstack.json`. O histórico de análises (`configs/historico_analises.json`) é criado **vazio**, para quem recebe não ver os testes de quem gerou.

Leva alguns minutos. No fim aparece **"✅ Pronto!"** com o caminho da pasta.

### Resultado

- Pasta **`dist\churn_engine\`** (~330 MB, ~3.900 arquivos), com o `churn_engine.exe` dentro.
- **Teste:** dois cliques em `dist\churn_engine\churn_engine.exe` → o painel abre no navegador (a mesma coisa que `python main.py`).
- **O `.exe` não funciona sozinho**: ele depende de `_internal\`, `data\`, `configs\`, `outputs\` e dos `.py` que ficam ao lado dele. Para mover ou mandar para alguém, leve a **pasta inteira**.

### Para distribuir

1. Compacte a pasta **`dist\churn_engine`** inteira em um `.zip` (botão direito → Compactar para arquivo ZIP) — dá ~150 MB.
2. Quem recebe **não precisa de Python**: só extrai e dá dois cliques no `churn_engine.exe` (ver Forma 1).
3. O zip passa do limite de 100 MB por arquivo do Git, então não vai dentro de commit: publique como **Release** do GitHub (aceita até 2 GB por arquivo), como foi feito aqui.

### Por que o venv

O PyInstaller empacota as bibliotecas **instaladas no Python que roda o build**. Num Python "global" cheio de outras coisas (PyTorch, OpenCV etc.), a primeira geração deste projeto chegou a **5 GB**. Com o venv só com o `requirements.txt`, fica nos ~330 MB acima. O `build_exe.py` já exclui as bibliotecas mais comuns, mas o venv é o jeito garantido.

### Limitação conhecida do executável

A biblioteca `anthropic` fica de fora do `.exe` (está na lista de exclusões). Por isso, dentro do executável, a aba **🧠 IA de ação** funciona só com **modelo local** (Ollama / LM Studio); com chave da Anthropic, use a Forma 2. O painel mostra uma mensagem clara nesse caso, sem travar.
