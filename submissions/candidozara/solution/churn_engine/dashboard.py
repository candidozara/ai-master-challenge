"""
Painel local (Streamlit) para o Churn Engine.

Roda no seu computador, lê os arquivos que `main.py` já gera em
outputs/processed/ -- não duplica cálculo nenhum, só visualiza o que o
motor determinístico + modelo já produziram. Funciona:

- JUNTO com o motor: rode `python main.py` (menu, opção 1 ou 2) e dê
  refresh no painel pra ver o resultado mais recente.
- SEPARADO do motor: aponte pra qualquer pasta de output antiga (ex:
  outputs_fonte_b/) e explore sem rodar nada de novo.

Uso normal (não precisa instalar nada à parte -- `main.py` instala
sozinho o que faltar):
    python main.py --painel
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import historico_analises
import ia_provedores
import leitor_arquivos
import sugerir_mapping
from rotulos_pt import TABELAS, CAMPOS_POR_TABELA, TABELAS_OBRIGATORIAS

# Paleta validada (dataviz skill) -- não trocar sem rodar o validador de novo.
AZUL = "#2a78d6"
STATUS = {"Baixo": "#0ca30c", "Médio": "#fab219", "Alto": "#ec835a", "Crítico": "#d03b3b"}
TEXTO_SECUNDARIO = "#52514e"
GRADE = "#e1e0d9"

st.set_page_config(page_title="Churn Engine — RavenStack", layout="wide")


@st.cache_data
def carregar_dados(output_dir: str):
    processed = os.path.join(output_dir, "processed")
    caminhos = {
        "super_tabela": os.path.join(processed, "super_tabela_churn.csv"),
        "segmentos": os.path.join(processed, "segmentos_risco.csv"),
        "risco_json": os.path.join(processed, "risco_churn_api.json"),
        "importancia": os.path.join(processed, "importancia_features_modelo.csv"),
        "metricas": os.path.join(processed, "metricas_modelo.json"),
    }
    faltando = [nome for nome, c in caminhos.items() if not os.path.exists(c)]
    if faltando:
        return None, faltando

    df = pd.read_csv(caminhos["super_tabela"])
    segmentos = pd.read_csv(caminhos["segmentos"])
    importancia = pd.read_csv(caminhos["importancia"])
    with open(caminhos["risco_json"], "r", encoding="utf-8") as f:
        risco = pd.DataFrame(json.load(f))
    with open(caminhos["metricas"], "r", encoding="utf-8") as f:
        metricas = json.load(f)

    return {"super_tabela": df, "segmentos": segmentos, "risco": risco, "importancia": importancia, "metricas": metricas}, []


def abrir_pasta_no_sistema(caminho: str) -> tuple:
    """
    Abre o Explorador de Arquivos (Windows) / Finder (macOS) / gerenciador
    de arquivos (Linux) direto na pasta de resultados. Isso só é possível
    porque o painel roda NO SEU computador -- o processo do Streamlit, por
    trás da página do navegador, tem acesso normal ao sistema de arquivos
    local, então consegue mandar o sistema operacional abrir uma janela.
    """
    caminho_abs = os.path.abspath(caminho)
    try:
        if sys.platform.startswith("win"):
            os.startfile(caminho_abs)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", caminho_abs], check=True)
        else:
            subprocess.run(["xdg-open", caminho_abs], check=True)
        return True, caminho_abs
    except Exception as e:
        return False, str(e)


def escolher_pasta_no_sistema(pasta_inicial: str = None) -> str:
    """
    Abre o seletor de pastas NATIVO do sistema operacional -- a mesma
    janela que qualquer programa instalado usa pra "Salvar como" ou
    "Escolher pasta". Só funciona porque o painel roda no seu computador:
    o processo por trás da página do navegador consegue abrir uma janela
    de verdade no sistema operacional, não é uma caixa de texto simulada.

    Tenta o mecanismo mais nativo de cada sistema primeiro (PowerShell +
    .NET no Windows, AppleScript no macOS, zenity/kdialog no Linux) e só
    cai pro `tkinter` como reserva -- porque o `tkinter` nem sempre vem
    junto com o Python (em especial em instalações do Windows via
    Microsoft Store), enquanto PowerShell e o .NET Framework vêm com
    qualquer Windows.

    No Windows, a janela é dona de um Form escondido com TopMost=true --
    sem isso, o FolderBrowserDialog pode abrir ATRÁS da janela do
    navegador, sem nenhum aviso, e parecer que o programa travou (foi
    reportado assim: clique não fazia nada aparente por vários minutos,
    porque a janela real estava escondida atrás do Chrome o tempo todo).
    Com o owner TopMost, a janela vem sempre pra frente.

    Devolve o caminho escolhido, ou None se a pessoa cancelou. Levanta
    RuntimeError com uma mensagem amigável só se NENHUM mecanismo
    funcionar (bem raro) -- quem chama trata isso com `st.error` em vez
    de quebrar a página.
    """
    inicial_abs = os.path.abspath(pasta_inicial) if pasta_inicial else os.getcwd()

    if sys.platform.startswith("win"):
        script_ps = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            # Form escondido só pra servir de "dono" da janela de escolha de
            # pasta -- TopMost=true garante que ela vem pra frente do
            # navegador em vez de abrir escondida atrás dele.
            "$owner = New-Object System.Windows.Forms.Form;"
            "$owner.TopMost = $true;"
            "$owner.StartPosition = 'CenterScreen';"
            "$owner.Width = 0; $owner.Height = 0;"
            "$owner.ShowInTaskbar = $false;"
            "$owner.Show();"
            "$owner.Activate();"
            "$f = New-Object System.Windows.Forms.FolderBrowserDialog;"
            "$f.Description = 'Escolha a pasta';"
            f"$f.SelectedPath = '{inicial_abs}';"
            "$resultado = $f.ShowDialog($owner);"
            "$owner.Close();"
            "if ($resultado -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.SelectedPath }"
        )
        try:
            resultado = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script_ps],
                capture_output=True, text=True, timeout=180,
            )
            caminho = resultado.stdout.strip()
            if caminho:
                return caminho
            if resultado.returncode == 0:
                return None  # janela abriu e a pessoa cancelou -- não é erro
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # PowerShell não disponível ou travou -- tenta tkinter abaixo

    elif sys.platform == "darwin":
        try:
            resultado = subprocess.run(
                ["osascript", "-e",
                 f'POSIX path of (choose folder with prompt "Escolha a pasta" default location "{inicial_abs}")'],
                capture_output=True, text=True, timeout=180,
            )
            caminho = resultado.stdout.strip()
            if caminho:
                return caminho
            if resultado.returncode == 0:
                return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    else:
        for comando in (
            ["zenity", "--file-selection", "--directory", f"--filename={inicial_abs}/"],
            ["kdialog", "--getexistingdirname", inicial_abs],
        ):
            try:
                resultado = subprocess.run(comando, capture_output=True, text=True, timeout=180)
                caminho = resultado.stdout.strip()
                if caminho:
                    return caminho
                if resultado.returncode == 0:
                    return None
            except FileNotFoundError:
                continue

    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as e:
        raise RuntimeError(
            "Não consegui abrir o seletor de pastas nativo por nenhum "
            "mecanismo disponível nesta máquina."
        ) from e

    raiz = tk.Tk()
    raiz.withdraw()
    raiz.attributes("-topmost", True)  # senão a janela pode abrir atrás do navegador
    pasta = filedialog.askdirectory(initialdir=inicial_abs, title="Escolha a pasta")
    raiz.destroy()
    return pasta or None


def grafico_barra_horizontal(df: pd.DataFrame, eixo_y: str, eixo_x: str, titulo: str, sufixo: str = "%"):
    df_ordenado = df.sort_values(eixo_x, ascending=True)
    valor_max = df_ordenado[eixo_x].max() if len(df_ordenado) else 1
    fig = go.Figure(go.Bar(
        y=df_ordenado[eixo_y], x=df_ordenado[eixo_x], orientation="h",
        marker=dict(color=AZUL),
        text=[f"{v:.1f}{sufixo}" for v in df_ordenado[eixo_x]],
        textposition="outside",
        cliponaxis=False,
    ))
    fig.update_layout(
        title=titulo, height=max(220, 34 * len(df_ordenado)),
        margin=dict(l=10, r=45, t=40, b=10),
        xaxis=dict(showgrid=True, gridcolor=GRADE, title=None, range=[0, valor_max * 1.22]),
        yaxis=dict(title=None),
        plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
        font=dict(color=TEXTO_SECUNDARIO),
    )
    return fig


def revisar_mapeamento_ui(nome_tabela: str, colunas_raw: list) -> dict:
    """
    Mostra, por CONCEITO DE NEGÓCIO (em português simples), qual coluna do
    arquivo enviado corresponde a ele -- já vem pré-preenchido com o palpite
    automático, a pessoa só confirma ou corrige no menu. Devolve o
    mapeamento final {coluna_original: conceito_canonico}.
    """
    sugestoes = sugerir_mapping.sugerir_para_tabela(colunas_raw, nome_tabela)
    melhor_por_conceito = {}
    for s in sugestoes:
        if s["sugestao_canonica"]:
            atual = melhor_por_conceito.get(s["sugestao_canonica"])
            if atual is None or s["confianca"] > atual[1]:
                melhor_por_conceito[s["sugestao_canonica"]] = (s["coluna_original"], s["confianca"])

    opcoes = ["(não tenho essa informação)"] + colunas_raw
    mapeamento_final = {}
    for conceito, pergunta in CAMPOS_POR_TABELA[nome_tabela].items():
        default_col, _ = melhor_por_conceito.get(conceito, (None, 0))
        indice = opcoes.index(default_col) if default_col in opcoes else 0
        escolha = st.selectbox(pergunta, opcoes, index=indice, key=f"map_{nome_tabela}_{conceito}")
        if escolha != "(não tenho essa informação)":
            mapeamento_final[escolha] = conceito
    return mapeamento_final


def rodar_com_dados_proprios(arquivos: dict, mapeamentos: dict, output_dir: str = "outputs_meus_dados"):
    """
    Salva os arquivos enviados, grava o mapeamento revisado num JSON e roda
    o motor de verdade (main.py) contra eles -- os MESMOS passos que
    rodariam por linha de comando, só que a pessoa não digita nada.

    Cada arquivo pode ter vindo num formato diferente (CSV, Excel, JSON) --
    todos são normalizados pra CSV aqui, antes de chamar main.py, que só
    sabe ler CSV. Assim o motor nunca precisa saber de onde veio o dado.
    """
    pasta_entrada = os.path.join(output_dir, "_entrada")
    # Limpa a pasta de entrada antes de escrever de novo -- importante pro
    # "Rodar de novo nesta análise": se da primeira vez você mandou uso.csv
    # e tickets.csv e desta vez não mandou (campos opcionais), sem isso os
    # arquivos antigos ficariam esquecidos aqui, contradizendo o mapping.json
    # novo (achado ao testar o "Rodar de novo" com menos tabelas que antes).
    shutil.rmtree(pasta_entrada, ignore_errors=True)
    os.makedirs(pasta_entrada, exist_ok=True)

    caminhos = {}
    for nome_tabela, arquivo in arquivos.items():
        arquivo.seek(0)
        df_tabela = leitor_arquivos.ler_qualquer_formato(arquivo)
        caminho = os.path.join(pasta_entrada, f"{nome_tabela}.csv")
        df_tabela.to_csv(caminho, index=False)
        caminhos[nome_tabela] = caminho

    caminho_config = os.path.join(pasta_entrada, "mapping.json")
    with open(caminho_config, "w", encoding="utf-8") as f:
        json.dump(mapeamentos, f, ensure_ascii=False, indent=2)

    # Roda o motor num PROCESSO SEPARADO (não import direto) de propósito:
    # se o motor travar com algum dado maluco, quem quebra é esse
    # processo-filho, não o painel inteiro -- você só vê a mensagem de
    # erro na tela, o painel continua de pé.
    #
    # `[sys.executable, "main.py", ...]` funciona rodando `python
    # dashboard.py` (sys.executable é um Python de verdade, "main.py" é o
    # arquivo que ele deve rodar). Só que se o PAINEL estiver rodando
    # dentro de um .exe compilado, `sys.executable` já É o próprio .exe
    # compilado -- não tem "main.py" nenhum pra apontar por fora, e passar
    # esse nome como argumento só faria o .exe reclamar de "argumento
    # desconhecido". Nesse caso, chamar só `sys.executable` com as MESMAS
    # flags (sem o "main.py") dá exatamente no mesmo resultado, porque o
    # próprio .exe compilado já É o main.py por dentro.
    executavel_compilado = getattr(sys, "frozen", False)
    comando = [sys.executable] if executavel_compilado else [sys.executable, "main.py"]
    comando += [
        "--config", caminho_config,
        "--accounts", caminhos["accounts"],
        "--subscriptions", caminhos["subscriptions"],
        "--usage", caminhos.get("usage", ""),
        "--tickets", caminhos.get("tickets", ""),
        "--churn", caminhos["churn"],
        "--output-dir", output_dir,
    ]
    # PYTHONIOENCODING=utf-8 aqui é uma segunda camada de proteção contra o
    # mesmo problema que o `main.py` já resolve sozinho (reconfigure de
    # stdout/stderr no topo do arquivo): quando este processo roda como
    # subprocesso (sem console de verdade), o Windows pode tentar usar uma
    # codificação regional sem emoji (cp1252) e travar com
    # UnicodeEncodeError no primeiro print com emoji.
    ambiente = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ambiente)
    return resultado.returncode == 0, resultado.stdout, resultado.stderr


# ---------------------------------------------------------------------------
st.title("📊 Churn Engine")
st.caption("Painel local. Lê os arquivos gerados por `main.py` — não recalcula nada sozinho.")

ABAS = ["📊 Painel", "📥 Meus dados", "🧠 IA de ação", "❓ Como usar"]
if "aba_ativa" not in st.session_state:
    st.session_state["aba_ativa"] = ABAS[0]
if "output_dir_ativo" not in st.session_state:
    st.session_state["output_dir_ativo"] = "outputs"
if "upload_versao" not in st.session_state:
    st.session_state["upload_versao"] = 0
# O widget de navegação (key="aba_ativa") já vai ser instanciado mais
# abaixo nesta mesma rodada -- depois disso, o Streamlit não deixa mais
# mudar st.session_state["aba_ativa"] diretamente (erro
# StreamlitWidgetAlreadyInstantiatedError). Por isso, quem quiser trocar
# de aba (ex: o botão "Nova análise") escreve em "proxima_aba" em vez
# disso, e resolvemos aqui em cima, ANTES do widget existir nesta rodada.
if "proxima_aba" in st.session_state:
    st.session_state["aba_ativa"] = st.session_state.pop("proxima_aba")

# A análise do desafio (pasta `outputs/`, os dados de exemplo da RavenStack
# que já vêm prontos no projeto) também vira uma sessão de verdade na barra
# lateral -- com os mesmos poderes de qualquer outra análise (apagar, rodar
# de novo com outros dados, trocar pasta) -- em vez de ficar de fora do
# sistema de sessões. Só é criada uma vez (na primeira vez que o painel
# abre nesta máquina); depois disso, sempre reaproveita a mesma entrada.
if os.path.exists(os.path.join("outputs", "processed", "super_tabela_churn.csv")):
    _sessao_desafio = next(
        (a for a in historico_analises.carregar_historico() if a["output_dir"] == "outputs"), None,
    )
    if _sessao_desafio is None:
        _sessao_desafio = historico_analises.registrar_analise(
            "Diagnóstico do desafio (dados RavenStack)",
            "outputs",
            "Dados de exemplo do desafio -- accounts, subscriptions, usage, tickets, churn",
        )
    if "analise_ativa_id" not in st.session_state:
        st.session_state["analise_ativa_id"] = _sessao_desafio["id"]

with st.sidebar:
    st.header("Análises")
    st.caption(
        "Cada vez que você roda o diagnóstico com seus dados (aba Meus "
        "dados), ele vira uma análise aqui embaixo -- igual a uma "
        "conversa: clique numa pra ver o painel completo daquela vez."
    )
    if st.button("➕ Nova análise", width="stretch", type="primary"):
        st.session_state["analise_ativa_id"] = None
        st.session_state["proxima_aba"] = "📥 Meus dados"
        st.session_state["upload_versao"] += 1
        st.session_state["pasta_destino_override"] = None
        st.session_state["reeditando_analise_id"] = None
        st.rerun()

    historico = historico_analises.carregar_historico()
    if historico:
        for entrada in historico:
            ativa = st.session_state.get("analise_ativa_id") == entrada["id"]
            rotulo = ("● " if ativa else "") + entrada["nome"]
            if st.button(rotulo, key=f"hist_{entrada['id']}", width="stretch"):
                st.session_state["analise_ativa_id"] = entrada["id"]
                st.session_state["output_dir_ativo"] = entrada["output_dir"]
                st.session_state["proxima_aba"] = "📊 Painel"
                st.cache_data.clear()
                st.rerun()
            data_legivel = entrada["data_criacao"][:16].replace("T", " ")
            st.caption(f"{data_legivel} · {entrada['resumo_fonte']}")
    else:
        st.caption("Nenhuma análise feita pelo painel ainda -- clique em **➕ Nova análise** pra começar.")

    st.divider()
    if st.button("🔄 Recarregar dados"):
        st.cache_data.clear()
    st.caption("Primeira vez usando isso? Abra a aba **❓ Como usar** ao lado.")

output_dir = st.session_state["output_dir_ativo"]

aba_ativa = st.radio(
    "Navegação", ABAS, key="aba_ativa", horizontal=True, label_visibility="collapsed",
)

if aba_ativa == "📥 Meus dados":
    st.markdown(
        "### Rodar com os dados da sua empresa\n"
        "Envie os arquivos abaixo — aceita **CSV, Excel (.xlsx/.xls) ou "
        "JSON**, pode misturar formatos (uma tabela em CSV, outra em Excel, "
        "sem problema). Pode ter qualquer nome de arquivo e qualquer nome "
        "de coluna — na próxima etapa você confirma o que é o quê, num "
        "menu, sem precisar editar nada por fora.\n\n"
        "**Clientes, Contratos e Cancelamentos são obrigatórios.** Uso da "
        "plataforma e Chamados de suporte são opcionais — mas quanto mais "
        "você enviar, mais completa fica a análise de risco (sem eles, o "
        "score de regra fica mais simples)."
    )

    arquivos_enviados = {}
    for chave, titulo, explicacao in TABELAS:
        opcional = chave not in TABELAS_OBRIGATORIAS
        st.markdown(f"**{titulo}**")
        st.caption(explicacao)
        arquivo = st.file_uploader(
            f"Arquivo — {titulo} (CSV, Excel ou JSON)" + (" (opcional)" if opcional else ""),
            type=leitor_arquivos.FORMATOS_SUPORTADOS,
            key=f"upload_{chave}_{st.session_state['upload_versao']}",
        )
        if arquivo is not None:
            arquivos_enviados[chave] = arquivo

    obrigatorias_ok = TABELAS_OBRIGATORIAS.issubset(arquivos_enviados.keys())

    if obrigatorias_ok:
        st.divider()
        st.markdown("### Confirme o que é cada coluna")
        st.caption(
            "Já preenchi com o palpite automático. Só troque no menu se "
            "estiver errado, ou deixe \"(não tenho essa informação)\" se o "
            "seu arquivo não tiver aquele dado."
        )
        mapeamentos = {}
        for chave, titulo, _ in TABELAS:
            if chave not in arquivos_enviados:
                continue
            with st.expander(titulo, expanded=False):
                try:
                    df_preview_completo = leitor_arquivos.ler_qualquer_formato(arquivos_enviados[chave])
                    arquivos_enviados[chave].seek(0)
                    df_preview = df_preview_completo.head(5)
                    st.caption("Prévia do seu arquivo:")
                    st.dataframe(df_preview, width="stretch", hide_index=True)
                    mapeamentos[chave] = revisar_mapeamento_ui(chave, list(df_preview.columns))
                except Exception as e:
                    st.error(f"Não consegui ler esse arquivo ({e}). Confira se é um CSV, Excel ou JSON válido.")
                    mapeamentos[chave] = {}

        tabelas_puladas = [t for t, titulo, _ in TABELAS if t not in arquivos_enviados]
        if tabelas_puladas:
            nomes_pulados = ", ".join(titulo for t, titulo, _ in TABELAS if t in tabelas_puladas)
            st.caption(f"ℹ️ Rodando sem: {nomes_pulados}. O diagnóstico funciona, só que com um score de risco mais simples.")

        st.divider()
        st.markdown("**Onde salvar essa análise**")
        if st.session_state.get("reeditando_analise_id"):
            st.caption(
                "Rodando de novo dentro desta mesma sessão -- por padrão vai "
                "sobrescrever a pasta de resultados que essa análise já tinha. "
                "Quer salvar em outro lugar desta vez? Escolha abaixo."
            )
        pasta_override = st.session_state.get("pasta_destino_override")
        if pasta_override:
            st.code(pasta_override, language=None)
            col_trocar, col_padrao = st.columns(2)
            with col_trocar:
                if st.button("📁 Escolher outra pasta"):
                    with st.spinner("Abrindo o seletor de pastas do sistema... (pode levar alguns segundos na primeira vez)"):
                        try:
                            escolhida = escolher_pasta_no_sistema(pasta_override)
                        except RuntimeError as e:
                            escolhida = None
                            st.error(str(e))
                    if escolhida:
                        st.session_state["pasta_destino_override"] = escolhida
                        st.rerun()
            with col_padrao:
                if st.button("↩️ Usar a pasta padrão do projeto"):
                    st.session_state["pasta_destino_override"] = None
                    st.rerun()
        else:
            st.caption(
                "Por padrão, cria uma pasta nova em `outputs_analises/analise_<data e "
                "hora>` dentro do projeto -- assim cada análise fica separada, sem "
                "sobrescrever a anterior. Quer salvar em outro lugar? Escolha abaixo "
                "(abre o seletor de pastas normal do Windows):"
            )
            if st.button("📁 Escolher outra pasta pra salvar (em vez da padrão)"):
                with st.spinner("Abrindo o seletor de pastas do sistema... (pode levar alguns segundos na primeira vez)"):
                    try:
                        escolhida = escolher_pasta_no_sistema("outputs_analises")
                    except RuntimeError as e:
                        escolhida = None
                        st.error(str(e))
                if escolhida:
                    st.session_state["pasta_destino_override"] = escolhida
                    st.rerun()

        nome_analise = st.text_input(
            "Nome dessa análise (opcional)",
            placeholder="ex: Dados de setembro, Cliente X...",
            help="Só pra você identificar depois na lista da barra lateral. Se deixar em branco, uso a data e hora.",
        )
        if st.button("🚀 Rodar diagnóstico com esses dados", type="primary"):
            if st.session_state.get("pasta_destino_override"):
                pasta_analise = st.session_state["pasta_destino_override"]
            else:
                id_pasta = datetime.now().strftime("%Y%m%d_%H%M%S")
                pasta_analise = os.path.join("outputs_analises", f"analise_{id_pasta}")
            with st.spinner("Rodando o motor contra os seus dados..."):
                sucesso, saida, erro = rodar_com_dados_proprios(arquivos_enviados, mapeamentos, output_dir=pasta_analise)
            if sucesso:
                resumo_fonte = ", ".join(titulo for chave, titulo, _ in TABELAS if chave in arquivos_enviados)
                if tabelas_puladas:
                    resumo_fonte += f" (sem {nomes_pulados})"
                reeditando_id = st.session_state.get("reeditando_analise_id")
                if reeditando_id:
                    # Rodando de novo dentro da MESMA sessão -- atualiza a
                    # entrada que já existia em vez de criar um card novo na
                    # barra lateral.
                    entrada = historico_analises.atualizar_analise(reeditando_id, resumo_fonte=resumo_fonte, nome=nome_analise)
                    if entrada is None:
                        # A entrada sumiu do histórico entre um clique e outro
                        # (ex: foi apagada em outra aba) -- não trava, cria
                        # uma análise nova em vez de referenciar algo que não
                        # existe mais.
                        entrada = historico_analises.registrar_analise(nome_analise, pasta_analise, resumo_fonte)
                    mensagem_sucesso = f"Pronto! Análise \"{entrada['nome']}\" atualizada -- indo pro painel..."
                else:
                    entrada = historico_analises.registrar_analise(nome_analise, pasta_analise, resumo_fonte)
                    mensagem_sucesso = f"Pronto! Análise \"{entrada['nome']}\" criada -- indo pro painel..."
                st.session_state["analise_ativa_id"] = entrada["id"]
                st.session_state["output_dir_ativo"] = pasta_analise
                st.session_state["proxima_aba"] = "📊 Painel"
                st.session_state["pasta_destino_override"] = None
                st.session_state["reeditando_analise_id"] = None
                st.cache_data.clear()
                st.success(mensagem_sucesso)
                st.rerun()
            else:
                st.error("Algo deu errado ao rodar. Detalhe técnico abaixo (mande pra quem construiu o painel se precisar de ajuda):")
                st.code(erro or saida)
    else:
        faltando = TABELAS_OBRIGATORIAS - arquivos_enviados.keys()
        nomes_faltando = ", ".join(titulo for t, titulo, _ in TABELAS if t in faltando)
        st.info(f"Envie os arquivos obrigatórios pra continuar. Faltam: {nomes_faltando}.")

if aba_ativa == "🧠 IA de ação":
    st.markdown(
        "### IA decidindo a ação por conta em risco\n"
        "Camada de **decisão**, não de execução: pra cada conta em risco, uma IA "
        "sugere uma ação (ex: \"priorizar fila de suporte\"), a urgência e os "
        "motivos -- nada aqui envia e-mail, abre ticket ou aplica desconto sozinho. "
        "É sempre uma sugestão que uma pessoa ainda revisa."
    )

    dados_ia, faltando_ia = carregar_dados(output_dir)
    if dados_ia is None:
        st.warning(f"Rode o motor primeiro (aba **📥 Meus dados**, ou opção 1/2 do menu no terminal) -- faltam arquivos em `{output_dir}/processed/`.")
    elif dados_ia["risco"].empty:
        st.info("Nenhuma conta ativa com risco Alto/Crítico em `risco_churn_api.json` agora -- nada pra decidir ação.")
    else:
        risco_df = dados_ia["risco"]
        st.caption(f"{len(risco_df)} conta(s) em risco disponíveis em `{output_dir}`.")

        caminho_ia_salva = os.path.join(output_dir, "processed", "acoes_recomendadas_ia.json")
        if os.path.exists(caminho_ia_salva):
            with open(caminho_ia_salva, "r", encoding="utf-8") as f:
                acoes_salvas = json.load(f)
            with st.container(border=True):
                st.markdown("##### ✅ Ações já calculadas nesta análise")
                st.caption("Salvas da última vez que você rodou a IA pra esta análise específica -- rodar de novo abaixo substitui.")
                st.dataframe(pd.DataFrame(acoes_salvas), width="stretch", hide_index=True)
            st.divider()

        origem = st.radio(
            "Onde a IA roda?",
            ["API da Anthropic", "IA local (Ollama, LM Studio, LocalAI...)"],
            horizontal=True, key="ia_origem",
        )

        provedor_pronto = False
        config_provedor = {}

        if origem == "API da Anthropic":
            api_key = st.text_input(
                "Cole sua API key da Anthropic", type="password", key="ia_api_key",
                help="Fica só nesta sessão do navegador -- não é salva em nenhum arquivo.",
            )
            modelo_anthropic = st.text_input("Modelo", value="claude-sonnet-4-5", key="ia_modelo_anthropic")
            if api_key.strip():
                provedor_pronto = True
                config_provedor = {"tipo": "anthropic", "api_key": api_key, "modelo": modelo_anthropic}
            else:
                st.caption("Cole a API key acima pra continuar.")

        else:
            if st.button("🔍 Detectar IA local"):
                with st.spinner("Procurando Ollama, LM Studio e outras ferramentas rodando nesta máquina..."):
                    st.session_state["ia_detectados"] = ia_provedores.detectar_provedores_locais()

            detectados = st.session_state.get("ia_detectados")
            if detectados is None:
                st.caption("Clique em \"Detectar IA local\" pra procurar automaticamente (Ollama, LM Studio, LocalAI, Text Generation WebUI, Jan).")
            elif not detectados:
                st.warning(
                    "Não encontrei nada rodando nas portas comuns. Confirme que a ferramenta está "
                    "aberta e com o servidor local ligado, ou use \"Endereço customizado\" abaixo."
                )
            else:
                mapa_opcoes = {
                    f"{d['nome']} — {m}": (d["base_url"], m)
                    for d in detectados for m in (d["modelos"] or [])
                }
                if mapa_opcoes:
                    escolha = st.selectbox("IA local detectada", list(mapa_opcoes.keys()), key="ia_local_escolha")
                    base_url_escolhida, modelo_escolhido = mapa_opcoes[escolha]
                    provedor_pronto = True
                    config_provedor = {"tipo": "local", "base_url": base_url_escolhida, "modelo": modelo_escolhido}
                else:
                    st.warning("Encontrei um servidor local rodando, mas sem nenhum modelo instalado nele.")

            with st.expander("Endereço customizado (se sua ferramenta não apareceu acima)"):
                endereco_custom = st.text_input("Endereço (ex: http://localhost:8000)", key="ia_endereco_custom")
                if st.button("Testar esse endereço", key="ia_testar_custom_btn"):
                    with st.spinner("Testando..."):
                        st.session_state["ia_modelos_custom"] = ia_provedores.testar_endereco_customizado(endereco_custom)
                        st.session_state["ia_endereco_custom_testado"] = endereco_custom

                modelos_custom = st.session_state.get("ia_modelos_custom")
                if st.session_state.get("ia_endereco_custom_testado") and modelos_custom is None:
                    st.error("Não consegui falar com esse endereço. Confirme que o servidor está ligado e fala a API da OpenAI (/v1/chat/completions).")
                elif modelos_custom:
                    modelo_custom_escolhido = st.selectbox("Modelo", modelos_custom, key="ia_modelo_custom_escolha")
                    provedor_pronto = True
                    config_provedor = {
                        "tipo": "local",
                        "base_url": st.session_state.get("ia_endereco_custom_testado"),
                        "modelo": modelo_custom_escolhido,
                    }

        st.divider()

        top_n = st.slider(
            "Quantas contas (as de maior risco primeiro)", 1, min(20, len(risco_df)), min(5, len(risco_df)),
            key="ia_top_n",
        )
        contas_selecionadas = risco_df.head(top_n).to_dict(orient="records")

        def _chamar_ia(conta):
            if config_provedor["tipo"] == "anthropic":
                return ia_provedores.decidir_acao_anthropic(conta, config_provedor["api_key"], config_provedor["modelo"])
            return ia_provedores.decidir_acao_local(conta, config_provedor["base_url"], config_provedor["modelo"])

        col_testar, col_rodar = st.columns(2)
        with col_testar:
            testar = st.button(
                "🧪 Testar com 1 conta", disabled=not provedor_pronto,
                help="Roda só na 1ª conta -- pra você ver se esse modelo entende o formato pedido antes de rodar em todas.",
            )
        with col_rodar:
            rodar_todas = st.button("▶️ Rodar e salvar", disabled=not provedor_pronto, type="primary")

        if testar and contas_selecionadas:
            with st.spinner("Chamando a IA..."):
                resultado = _chamar_ia(contas_selecionadas[0])
            if "erro" in resultado:
                st.error(resultado["erro"])
            else:
                st.success("O modelo respondeu no formato esperado -- compatível com esta análise:")
                st.json(resultado)

        if rodar_todas and contas_selecionadas:
            progresso = st.progress(0.0)
            resultados = []
            for i, conta in enumerate(contas_selecionadas):
                decisao = _chamar_ia(conta)
                nome = str(conta.get("canonical_name", conta.get("canonical_id", "?")))
                resultados.append({"conta": nome, "id": conta.get("canonical_id"), **decisao})
                progresso.progress((i + 1) / len(contas_selecionadas))

            erros = [r for r in resultados if "erro" in r]
            if erros:
                st.error(f"{len(erros)} de {len(resultados)} conta(s) falharam -- veja o detalhe na tabela abaixo.")

            destino = os.path.join(output_dir, "processed", "acoes_recomendadas_ia.json")
            with open(destino, "w", encoding="utf-8") as f:
                json.dump(resultados, f, ensure_ascii=False, indent=2)
            st.success(f"Salvo em `{destino}`.")
            st.dataframe(pd.DataFrame(resultados), width="stretch", hide_index=True)

if aba_ativa == "❓ Como usar":
    st.markdown("""
### O que é isto?

Este painel mostra o resultado de um motor de diagnóstico de churn (Python).
Ele **não coleta dados sozinho** — alguém roda o motor (`main.py`) contra os
CSVs da empresa, e este painel só lê e exibe o que foi calculado, guardado
numa pasta `outputs*/`.

### Passo a passo para rodar do zero

Não precisa instalar nada antes -- na primeira vez que rodar numa máquina
nova, o próprio `main.py` instala sozinho o que faltar.

Abra um terminal dentro da pasta do projeto e escolha um dos dois comandos:

1. ```
   python main.py
   ```
   Abre um menu no terminal explicando cada opção (dados de exemplo, seus
   dados, ver este painel, conferir relatórios, sair). A opção **1** roda
   com os dados de exemplo (RavenStack); a opção **2** te guia pra usar os
   seus próprios arquivos. Depois de rodar, escolha a opção **3** pra abrir
   este painel.
2. ```
   python main.py --painel
   ```
   Pula o menu e abre este painel direto no navegador -- útil se você já
   rodou o motor antes e só quer ver os gráficos de novo. Se não abrir
   sozinho, copie o endereço que aparecer no terminal (algo como
   `http://localhost:8501`).

### A barra lateral (Análises)

A barra lateral guarda a lista das análises que você já rodou por aqui
pelo painel — igual a uma lista de conversas: cada vez que você roda o
diagnóstico na aba **📥 Meus dados**, uma entrada nova aparece lá, com
nome, data e quais tabelas foram usadas. Clique em qualquer uma pra ver
o painel completo daquela vez de novo (incluindo as ações de IA, se você
rodou alguma pra ela). Clique em **➕ Nova análise** pra começar do zero
(pasta nova, criada automaticamente).

A própria análise do desafio (os dados de exemplo da RavenStack que já
vêm prontos no projeto, em `outputs/`) também aparece como a primeira
entrada da lista, com os mesmos poderes de qualquer outra — não é um
caso especial fora do sistema de sessões.

Dentro de uma análise (aba **📊 Painel**, caixa **📥 Dados de origem desta
análise**), você tem controle total daquela sessão específica:

- **🔁 Rodar de novo nesta análise**: manda dados novos (ex: uma tabela a
  mais ou a menos, arquivo atualizado) pra essa MESMA sessão, sem criar
  um card novo na lista — por padrão sobrescreve a mesma pasta, mas você
  também pode escolher outra pasta ali na hora, se quiser.
- **🗑️ Apagar esta análise**: remove a pasta de resultados do computador
  e tira ela da lista (pede confirmação antes, não tem como desfazer).
- **📥 Baixar os arquivos**: os botões de download no topo da aba Painel.

Pastas rodadas pelo terminal (os dados de exemplo em `outputs/`, ou
`python main.py --output-dir ...`) não entram automaticamente nessa
lista -- o painel abre com os dados de exemplo (`outputs/`) até você
criar sua primeira análise por aqui.

### Onde ficam os arquivos gerados

No topo da aba **📊 Painel** tem uma caixa **📂 Onde estão os seus
resultados** com o caminho completo da pasta, um botão que abre essa pasta
direto no Explorador de Arquivos do seu computador, e um botão de download
pra cada arquivo (PDF, Markdown, CSV, JSON) -- o navegador pergunta onde
salvar (ou usa a pasta de Downloads padrão). Não precisa procurar pasta
nenhuma na mão.

### Usando seus próprios dados (arquivos com nomes diferentes)

O motor não depende dos nomes de coluna do exemplo -- e também não exige
as 5 tabelas. **Clientes, Contratos e Cancelamentos são obrigatórios**
(sem eles não dá pra saber quem é cliente, quanto paga e quem cancelou).
**Uso da plataforma e Chamados de suporte são opcionais**: se faltar um
dos dois, o motor roda do mesmo jeito, só que com um score de risco mais
simples (menos sinais disponíveis) -- e isso fica avisado no terminal e
no relatório gerado. Quanto mais tabelas você tiver, melhor a análise.

Para uma fonte nova:

1. Rode o sugestor de mapeamento para cada uma das 5 tabelas (contas,
   assinaturas, uso, tickets, cancelamentos):
   ```
   python sugerir_mapping.py --tabela accounts --csv caminho/seu_arquivo.csv --saida configs/mapping_novo.json
   ```
   Repita trocando `--tabela` (accounts/subscriptions/usage/tickets/churn) e
   `--csv`, sempre com `--saida configs/mapping_novo.json` (mesmo arquivo,
   ele vai completando).
2. Abra `configs/mapping_novo.json` e confira: colunas marcadas como
   `null` ou que faltam precisam ser preenchidas manualmente — o script
   avisa no terminal quantas ficaram pendentes.
3. Rode o motor apontando pra esse mapeamento e pros seus arquivos:
   ```
   python main.py --config configs/mapping_novo.json --accounts caminho/contas.csv --subscriptions caminho/assinaturas.csv --usage caminho/uso.csv --tickets caminho/tickets.csv --churn caminho/cancelamentos.csv --output-dir outputs_novo
   ```
4. Valide que a saída está correta:
   ```
   python validar_outputs.py --output-dir outputs_novo
   ```
   Se as 18 checagens passarem, os dados são confiáveis.
5. Volte aqui, escolha `outputs_novo` na barra lateral e clique em Recarregar.

### O que cada número significa

- **Score de risco (regra)**: 0–100, calculado por uma fórmula fixa e
  auditável (não é IA) — é o critério principal de priorização.
- **ROC-AUC do modelo**: mede se o modelo de Machine Learning consegue
  prever churn melhor que o acaso (0.5 = acaso, 1.0 = perfeito). Neste
  projeto ele é reportado com honestidade: se o sinal for fraco, o painel
  diz isso em vez de esconder.
- **feedback_text**: campo de texto livre do cliente; foi checado e
  descartado como sinal (ver aba Painel → seção do modelo) — mantido aqui
  só como exemplo de checagem de qualidade de dado.

### Se algo der errado

- **"Faltam arquivos em outputs/processed/"** → o motor ainda não rodou
  pra essa pasta. Rode `python main.py` e escolha a opção 1 (ou 2, pros
  seus dados) primeiro.
- **Erro ao instalar dependências** → `python main.py` tenta instalar
  sozinho na primeira vez; se falhar, confirme que está usando Python
  3.10+ (`python --version`) e tente `pip install -r requirements.txt`
  manualmente.
- **Painel não atualiza depois de rodar o motor de novo** → clique em
  🔄 Recarregar na barra lateral (o painel guarda os dados em cache).
""")

if aba_ativa == "📊 Painel":
    dados, faltando = carregar_dados(output_dir)
    if dados is None:
        st.error(f"Faltam arquivos em `{output_dir}/processed/`: {faltando}. Rode `python main.py --output-dir {output_dir}` primeiro.")
        st.stop()

    df = dados["super_tabela"]
    segmentos = dados["segmentos"]
    risco = dados["risco"]
    importancia = dados["importancia"]
    metricas = dados["metricas"]

    # --- Onde estão os resultados -------------------------------------------
    with st.container(border=True):
        st.markdown("#### 📂 Onde estão os seus resultados")
        caminho_abs_output = os.path.abspath(output_dir)
        st.code(caminho_abs_output, language=None)

        col_abrir, col_aviso = st.columns([1, 2])
        with col_abrir:
            if st.button("📂 Abrir essa pasta no computador"):
                sucesso, detalhe = abrir_pasta_no_sistema(output_dir)
                if sucesso:
                    st.success("Pasta aberta -- confira a janela que abriu.")
                else:
                    st.error(f"Não consegui abrir sozinho ({detalhe}). Copie o caminho acima e cole no Explorador de Arquivos.")

        st.caption("Ou baixe cada arquivo direto por aqui (o navegador pergunta onde salvar, ou vai pra pasta de Downloads):")

        arquivos_para_baixar = [
            ("📄 PDF (relatório)", os.path.join(output_dir, "reports", "relatorio_executivo_churn.pdf"), "application/pdf"),
            ("📝 Markdown (relatório)", os.path.join(output_dir, "reports", "relatorio_executivo_churn.md"), "text/markdown"),
            ("📊 CSV (tabela completa)", os.path.join(output_dir, "processed", "super_tabela_churn.csv"), "text/csv"),
            ("🔌 JSON (contas em risco)", os.path.join(output_dir, "processed", "risco_churn_api.json"), "application/json"),
            ("🧭 CSV (segmentos)", os.path.join(output_dir, "processed", "segmentos_risco.csv"), "text/csv"),
        ]
        cols_download = st.columns(len(arquivos_para_baixar))
        for col, (rotulo, caminho_arquivo, mime) in zip(cols_download, arquivos_para_baixar):
            with col:
                if os.path.exists(caminho_arquivo):
                    with open(caminho_arquivo, "rb") as f:
                        st.download_button(
                            rotulo, f.read(), file_name=os.path.basename(caminho_arquivo),
                            mime=mime, key=f"baixar_{os.path.basename(caminho_arquivo)}_{output_dir}",
                            width="stretch",
                        )
                else:
                    st.caption(f"{rotulo}: não encontrado")

    # --- Dados de origem desta análise ---------------------------------------
    pasta_entrada = os.path.join(output_dir, "_entrada")
    with st.container(border=True):
        st.markdown("#### 📥 Dados de origem desta análise")
        entrada_atual = next((a for a in historico_analises.carregar_historico() if a["id"] == st.session_state.get("analise_ativa_id")), None)
        if entrada_atual:
            st.caption(f"Tabelas usadas: {entrada_atual['resumo_fonte']}")
        if os.path.isdir(pasta_entrada):
            st.code(os.path.abspath(pasta_entrada), language=None)
            st.caption(
                "Aqui ficam os arquivos que essa análise usou (já convertidos pra "
                "CSV, um por tabela) -- abra essa pasta pra conferir os dados."
            )
            if st.button("📂 Abrir a pasta dos dados de origem"):
                sucesso, detalhe = abrir_pasta_no_sistema(pasta_entrada)
                if sucesso:
                    st.success("Pasta aberta -- confira a janela que abriu.")
                else:
                    st.error(f"Não consegui abrir sozinho ({detalhe}). Copie o caminho acima e cole no Explorador de Arquivos.")
        else:
            st.caption(
                "Os dados de entrada desta análise são os CSVs de exemplo do "
                "desafio (RavenStack), que já vêm prontos no projeto em `data/` "
                "-- não foram enviados por aqui."
            )
            if st.button("📂 Abrir a pasta data/"):
                sucesso, detalhe = abrir_pasta_no_sistema("data")
                if sucesso:
                    st.success("Pasta aberta -- confira a janela que abriu.")
                else:
                    st.error(f"Não consegui abrir sozinho ({detalhe}). Copie o caminho acima e cole no Explorador de Arquivos.")

        if entrada_atual:
            st.divider()
            st.caption("Gerenciar esta análise:")
            col_rerun, col_del = st.columns(2)
            with col_rerun:
                if st.button("🔁 Rodar de novo nesta análise", width="stretch",
                              help="Enviar dados novos (ou trocar a pasta) sem criar uma análise separada -- atualiza esta mesma sessão."):
                    st.session_state["reeditando_analise_id"] = entrada_atual["id"]
                    st.session_state["pasta_destino_override"] = entrada_atual["output_dir"]
                    st.session_state["upload_versao"] += 1
                    st.session_state["proxima_aba"] = "📥 Meus dados"
                    st.rerun()
            with col_del:
                confirmando = st.session_state.get("confirmar_apagar_id") == entrada_atual["id"]
                if not confirmando:
                    if st.button("🗑️ Apagar esta análise", width="stretch"):
                        st.session_state["confirmar_apagar_id"] = entrada_atual["id"]
                        st.rerun()
            if confirmando:
                st.warning(
                    f"Apagar \"{entrada_atual['nome']}\" de vez? Isso remove a "
                    f"pasta `{output_dir}` inteira do computador -- não dá pra desfazer."
                )
                col_sim, col_nao = st.columns(2)
                with col_sim:
                    if st.button("✅ Sim, apagar de vez", type="primary", width="stretch"):
                        historico_analises.remover_analise(entrada_atual["id"])
                        if os.path.isdir(output_dir):
                            shutil.rmtree(output_dir, ignore_errors=True)
                        st.session_state["analise_ativa_id"] = None
                        st.session_state["output_dir_ativo"] = "outputs"
                        st.session_state["confirmar_apagar_id"] = None
                        st.cache_data.clear()
                        st.success("Análise apagada.")
                        st.rerun()
                with col_nao:
                    if st.button("Cancelar", width="stretch"):
                        st.session_state["confirmar_apagar_id"] = None
                        st.rerun()

    st.divider()

    # --- KPIs -------------------------------------------------------------
    total_contas = len(df)
    total_churns = int(df["canonical_is_churn_account"].sum())
    taxa_churn = total_churns / total_contas * 100
    mrr_perdido = df.loc[df["canonical_is_churn_account"] == True, "canonical_revenue"].sum()
    contas_risco_alto = len(risco) if not risco.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Contas analisadas", f"{total_contas}")
    c2.metric("Taxa de churn", f"{taxa_churn:.1f}%", f"{total_churns} contas")
    c3.metric("MRR perdido", f"${mrr_perdido:,.0f}")
    c4.metric("Contas ativas em risco Alto/Crítico", f"{contas_risco_alto}")

    st.divider()

    # --- Segmentação --------------------------------------------------------
    st.subheader("Segmentos mais em risco")
    col_a, col_b, col_c = st.columns(3)
    for col, dimensao, titulo in [
        (col_a, "industry", "Por indústria"),
        (col_b, "referral_source", "Por canal de aquisição"),
        (col_c, "plan", "Por plano"),
    ]:
        sub = segmentos[segmentos["dimensao"] == dimensao]
        if not sub.empty:
            col.plotly_chart(grafico_barra_horizontal(sub, "valor", "taxa_churn_pct", titulo), width="stretch")

    st.divider()

    # --- Risco: nível e contas -----------------------------------------------
    st.subheader("Contas ativas com maior risco (score de regra, determinístico)")

    col_risco1, col_risco2 = st.columns([1, 2])
    with col_risco1:
        if "risco_nivel_regra" in df.columns:
            contagem_nivel = df[df["canonical_is_churn_account"] == False]["risco_nivel_regra"].value_counts()
            ordem = ["Baixo", "Médio", "Alto", "Crítico"]
            contagem_nivel = contagem_nivel.reindex(ordem).fillna(0)
            fig = go.Figure(go.Bar(
                x=ordem, y=contagem_nivel.values,
                marker=dict(color=[STATUS[n] for n in ordem]),
                text=[int(v) for v in contagem_nivel.values], textposition="outside",
            ))
            fig.update_layout(
                title="Contas ativas por nível de risco", height=320,
                margin=dict(l=10, r=10, t=40, b=10),
                plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
                font=dict(color=TEXTO_SECUNDARIO),
                yaxis=dict(showgrid=True, gridcolor=GRADE),
            )
            st.plotly_chart(fig, width="stretch")

    with col_risco2:
        if not risco.empty:
            colunas_tabela = [c for c in ["canonical_name", "canonical_industry", "canonical_plan", "canonical_revenue", "risco_score_regra", "risco_nivel_regra"] if c in risco.columns]
            tabela = risco[colunas_tabela].head(20).rename(columns={
                "canonical_name": "Conta", "canonical_industry": "Indústria", "canonical_plan": "Plano",
                "canonical_revenue": "MRR", "risco_score_regra": "Score", "risco_nivel_regra": "Nível",
            })
            st.dataframe(tabela, width="stretch", hide_index=True)
            st.caption("Lista completa em outputs/processed/risco_churn_api.json — pronta pro CS consumir.")
        else:
            st.info("Nenhuma conta ativa cruzou o limite de risco definido na exportação.")

    st.divider()

    # --- Modelo preditivo -----------------------------------------------------
    st.subheader("Modelo preditivo (scikit-learn) — honesto sobre a qualidade")
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        if metricas.get("treinado"):
            st.metric("ROC-AUC (validação cruzada, 5 folds)", f"{metricas['roc_auc']} ± {metricas['roc_auc_std']}")
            cor_sinal = "🟢" if metricas.get("sinal_confiavel") else "🟡"
            st.write(f"{cor_sinal} {metricas['interpretacao']}")
        else:
            st.warning("Modelo não pôde ser validado nesta execução.")
    with col_m2:
        if not importancia.empty:
            top_importancia = importancia.head(8).rename(columns={"feature": "variavel", "importancia": "peso"})
            top_importancia["peso"] = top_importancia["peso"] * 100
            st.plotly_chart(
                grafico_barra_horizontal(top_importancia, "variavel", "peso", "Variáveis mais importantes do modelo", sufixo=""),
                width="stretch",
            )

    st.divider()
    st.caption(
        "Score de regra = determinístico e auditável (usado como critério principal). "
        "Score de modelo = experimental (sinal fraco neste dataset, ver README). "
        "Dados: RavenStack (sintético, MIT-like license, via Kaggle)."
    )
