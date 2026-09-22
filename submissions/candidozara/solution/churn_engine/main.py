"""
Motor Analítico de Churn -- RavenStack

Sem nenhum argumento (é o que acontece dando 2 cliques no .exe compilado),
abre direto o painel gráfico no navegador -- hoje dá pra fazer tudo por lá
(rodar com dados de exemplo ou com dados próprios, ver o histórico de
análises, IA de ação, etc.), então não faz sentido mais mostrar um menu de
terminal por padrão antes de chegar lá.

    python main.py            -> abre direto o painel gráfico no navegador
    python main.py --painel   -> mesma coisa (mantido por compatibilidade)
    python main.py --menu     -> abre o menu de terminal antigo (rodar sem
                                  abrir navegador, conferir outputs/ etc.)

Passar `--config` e os 5 caminhos de dados (como o menu faz sozinho na
opção 2) aponta o mesmo motor para QUALQUER outra fonte, sem mudar uma
linha de engine.py/analytics.py -- essa é a prova de que a arquitetura é
agnóstica de fonte.
"""

import glob
import importlib
import json
import os
import subprocess
import sys

# Os prints deste arquivo (e dos módulos que ele chama) usam emojis pra
# ficar mais legível no terminal. Isso funciona sem problema quando você
# roda `python main.py` direto -- mas quando o painel gráfico chama este
# mesmo main.py por baixo dos panos (subprocess, pra rodar com os dados
# que você envia pela aba "Meus dados"), a saída deixa de ir pra um
# console de verdade e passa a ir por um "cano" (pipe) -- e no Windows,
# sem console de verdade, o Python volta pra codificação padrão da
# região (cp1252 em instalações em português, que não tem emoji nenhum),
# e trava com UnicodeEncodeError no primeiro emoji que tentar imprimir.
# Forçar UTF-8 aqui resolve nos dois casos, sem trocar nada na aparência
# de quem roda pelo terminal normalmente.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PASTA_PROJETO = os.path.dirname(os.path.abspath(__file__))


def pasta_base() -> str:
    """
    Pasta de referência pra tudo que é relativo (data/, configs/,
    dashboard.py, outputs/...). Rodando `python main.py`, é a pasta do
    projeto (PASTA_PROJETO, calculada a partir deste arquivo .py). Rodando
    como executável compilado (.exe, PyInstaller), este arquivo não existe
    mais como .py separado -- está todo dentro do binário -- então a
    referência vira a pasta onde o .exe está, porque é lá que a pessoa
    distribuindo o programa deixa `data/`, `configs/` e `dashboard.py` (o
    painel gráfico continua como arquivo .py solto do lado do .exe, porque
    o Streamlit precisa ler o arquivo de verdade pra rodar -- só o motor
    em si, e os módulos que ele importa direto, vão dentro do binário).
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return PASTA_PROJETO


def _tem_modulo(nome):
    try:
        importlib.import_module(nome)
        return True
    except ImportError:
        return False


def garantir_dependencias():
    """Se for a primeira vez rodando aqui, instala o que falta sozinho --
    a pessoa não precisa saber que existe um comando de instalação.

    Isso só faz sentido rodando como script Python normal (`python main.py`),
    onde `sys.executable` é um Python de verdade com `pip`. Num executável
    compilado (PyInstaller, `sys.frozen == True`), `sys.executable` é o
    PRÓPRIO programa compilado -- ele já vem com tudo empacotado dentro,
    não tem "pip" nenhum pra chamar. Sem essa checagem, rodar o .exe
    dispararia `<o próprio .exe> -m pip install ...` como subprocesso, que
    por sua vez roda esse MESMO código de novo (todo .exe empacotado
    executa o programa inteiro ao ser chamado, não só o "-m pip"), detecta
    "falta" de novo e chama outro subprocesso -- uma cascata de processos
    se multiplicando sem parar (achado testando um build de verdade, não
    suposição)."""
    if getattr(sys, "frozen", False):
        return
    necessarios = ["pandas", "numpy", "sklearn", "reportlab", "streamlit", "plotly", "openpyxl"]
    faltando = [m for m in necessarios if not _tem_modulo(m)]
    if faltando:
        print("Primeira vez rodando aqui -- instalando o que falta (só acontece essa vez)...")
        print()
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", os.path.join(PASTA_PROJETO, "requirements.txt")],
            cwd=PASTA_PROJETO,
        )
        print()


garantir_dependencias()

# só importa o resto (pandas, sklearn etc.) depois de garantir que está instalado
import argparse  # noqa: E402

import pandas as pd  # noqa: E402

from src.adapters.mapper import DataMapper  # noqa: E402
from src.core.engine import ChurnDiagnosticEngine  # noqa: E402
from src.core import analytics  # noqa: E402
from src.outputs.exporter import ChurnExporter  # noqa: E402

sys.path.insert(0, PASTA_PROJETO)
import leitor_arquivos  # noqa: E402
import sugerir_mapping  # noqa: E402
from rotulos_pt import TABELAS, CAMPOS_POR_TABELA, TABELAS_OBRIGATORIAS  # noqa: E402


def parse_args(argv=None):
    """
    Tudo tem um default que reproduz o comportamento de sempre (RavenStack).
    Passar --config e os 5 caminhos de dados aponta o mesmo motor para
    QUALQUER outra fonte, sem mudar uma linha de engine.py/analytics.py --
    essa é a prova de que a arquitetura é agnóstica de fonte.
    """
    parser = argparse.ArgumentParser(description="Motor Analítico de Churn")
    parser.add_argument("--config", default="configs/mapping_ravenstack.json", help="Arquivo De/Para (JSON)")
    parser.add_argument("--accounts", default="data/ravenstack_accounts.csv")
    parser.add_argument("--subscriptions", default="data/ravenstack_subscriptions.csv")
    parser.add_argument(
        "--usage", default="data/ravenstack_feature_usage.csv",
        help="Opcional -- passe --usage \"\" (vazio) se não tiver esse dado.",
    )
    parser.add_argument(
        "--tickets", default="data/ravenstack_support_tickets.csv",
        help="Opcional -- passe --tickets \"\" (vazio) se não tiver esse dado.",
    )
    parser.add_argument("--churn", default="data/ravenstack_churn_events.csv")
    parser.add_argument("--output-dir", default="outputs", help="Pasta onde salvar CSV/JSON/PDF/Markdown")
    return parser.parse_args(argv)


# accounts, subscriptions e churn são obrigatórias -- sem elas não tem
# diagnóstico de churn possível (não dá pra saber quem é cliente, quanto
# paga, nem quem cancelou). usage e tickets são opcionais: cada uma
# alimenta um pedaço do score de risco, mas o motor roda sem elas -- só
# com um score mais simples, e isso fica registrado no relatório gerado.
TABELAS_OBRIGATORIAS_MOTOR = {"accounts", "subscriptions", "churn"}


def rodar_motor(args):
    print("🚀 Iniciando o Motor Analítico de Churn (Modo Determinístico + Preditivo)...")
    print(f"   Fonte de dados: {args.config}")

    path_config = args.config

    paths_arquivos = {
        "accounts": args.accounts,
        "subscriptions": args.subscriptions,
        "usage": args.usage,
        "tickets": args.tickets,
        "churn": args.churn,
    }

    if not os.path.exists(path_config):
        print(f"❌ Erro: Arquivo de configuração não encontrado em {path_config}")
        return

    tabelas_faltando_opcionais = []
    for nome, caminho in paths_arquivos.items():
        tem_caminho = bool(caminho) and caminho.strip() != ""
        if not tem_caminho or not os.path.exists(caminho):
            if nome in TABELAS_OBRIGATORIAS_MOTOR:
                print(f"❌ Erro: Arquivo de dados '{nome}' não encontrado em {caminho!r} (essa tabela é obrigatória).")
                return
            tabelas_faltando_opcionais.append(nome)

    if tabelas_faltando_opcionais:
        print(
            f"⚠️  Rodando SEM {', '.join(tabelas_faltando_opcionais)} (opcional). "
            "O score de risco fica mais simples -- os sinais que vêm dessas tabelas "
            "não entram na conta. Quanto mais dados, melhor a análise."
        )

    print("📂 Carregando regras de mapeamento (De/Para)...")
    mapper = DataMapper(path_config)

    try:
        print("🔄 Lendo e traduzindo fontes de dados para o Contrato Canônico...")
        df_accounts = mapper.transformar(pd.read_csv(paths_arquivos["accounts"]), "accounts")
        df_subscriptions = mapper.transformar(pd.read_csv(paths_arquivos["subscriptions"]), "subscriptions")
        df_usage = (
            mapper.transformar(pd.read_csv(paths_arquivos["usage"]), "usage")
            if "usage" not in tabelas_faltando_opcionais else None
        )
        df_tickets = (
            mapper.transformar(pd.read_csv(paths_arquivos["tickets"]), "tickets")
            if "tickets" not in tabelas_faltando_opcionais else None
        )
        df_churn = mapper.transformar(pd.read_csv(paths_arquivos["churn"]), "churn")

        print("⚙️  Processando e cruzando dados na Super Tabela...")
        engine = ChurnDiagnosticEngine(df_accounts, df_subscriptions, df_usage, df_tickets, df_churn)
        super_tabela = engine.construir_super_tabela()
        print(f"   Super Tabela construída: {len(super_tabela)} contas, {len(super_tabela.columns)} colunas.")

        print("🧮 Calculando score de risco determinístico (regra de negócio)...")
        super_tabela = analytics.calcular_score_regra(super_tabela)

        print("🤖 Treinando modelo preditivo (scikit-learn)...")
        resultado_modelo = analytics.treinar_modelo_preditivo(super_tabela)
        super_tabela = resultado_modelo["super_tabela"]
        if resultado_modelo["metricas"].get("treinado"):
            m = resultado_modelo["metricas"]
            print(f"   ROC-AUC (média de 5 folds): {m['roc_auc']} (± {m['roc_auc_std']}) — {m['interpretacao'][:70]}...")
        else:
            print(f"   ⚠️  Modelo não pôde ser validado: {resultado_modelo['metricas'].get('erro')}")

        print("🧭 Calculando segmentação de risco (indústria / canal / plano)...")
        segmentos = analytics.segmentar_risco(super_tabela)

        print("🔎 Calculando distribuição de motivos de churn (fonte: accounts.csv)...")
        contas_churned_ids = set(super_tabela.loc[super_tabela["canonical_is_churn_account"] == True, "canonical_id"])
        motivos_churn = analytics.distribuicao_motivos_churn(df_churn, contas_churned_ids)

        checagem_texto = analytics.checar_valor_informativo_feedback_text(df_churn)
        if checagem_texto.get("avaliado") and checagem_texto.get("parece_redundante_ou_ruido"):
            print(
                f"   ⚠️  feedback_text tem só {checagem_texto['valores_unicos_texto']} valores únicos e "
                "distribuição quase idêntica em todos os reason_code -- parece ruído, não sinal. "
                "Não foi usado como feature do modelo (ver README)."
            )

        print(f"📤 Exportando resultados multicanal (CSV / JSON / PDF / Markdown) em {args.output_dir}/...")
        exporter = ChurnExporter(super_tabela, output_dir=args.output_dir)
        exporter.exportar_csv_bi()
        exporter.exportar_api_json()
        exporter.exportar_pdf(metricas_modelo=resultado_modelo["metricas"], segmentos=segmentos, motivos_churn=motivos_churn)
        exporter.gerar_relatorio_markdown(segmentos=segmentos, motivos_churn=motivos_churn)

        segmentos.to_csv(os.path.join(args.output_dir, "processed", "segmentos_risco.csv"), index=False, encoding="utf-8")
        resultado_modelo["importancia_features"].to_csv(
            os.path.join(args.output_dir, "processed", "importancia_features_modelo.csv"), index=False, encoding="utf-8"
        )
        with open(os.path.join(args.output_dir, "processed", "metricas_modelo.json"), "w", encoding="utf-8") as f:
            json.dump(resultado_modelo["metricas"], f, ensure_ascii=False, indent=2)

        print(f"✅ Pipeline executado com sucesso! Veja {args.output_dir}/processed/ e {args.output_dir}/reports/.")

    except Exception as e:
        print(f"⚠️  Erro no processamento dos dados: {e}")
        raise


# ---------------------------------------------------------------------------
# Menu de terminal -- python main.py, sem argumentos, cai aqui.
# ---------------------------------------------------------------------------

def linha():
    print("-" * 60)


def perguntar_numero(pergunta: str, minimo: int, maximo: int) -> int:
    while True:
        resposta = input(pergunta).strip()
        if resposta.isdigit() and minimo <= int(resposta) <= maximo:
            return int(resposta)
        print(f"   Digite um número entre {minimo} e {maximo}.")


def escolher_arquivo_para_tabela(titulo: str, explicacao: str, csvs: list, opcional: bool = False) -> str | None:
    print()
    print(titulo)
    print(f"   {explicacao}")
    for i, caminho in enumerate(csvs, start=1):
        print(f"   {i}) {os.path.basename(caminho)}")
    if opcional:
        print("   0) Não tenho esse arquivo -- pular (a análise roda sem esse pedaço)")
    nome_tabela = titulo.split(') ', 1)[-1]
    minimo = 0 if opcional else 1
    indice = perguntar_numero(f"   Qual desses é o arquivo de {nome_tabela}? Digite o número: ", minimo, len(csvs))
    if indice == 0:
        return None
    return csvs[indice - 1]


def revisar_mapeamento_terminal(nome_tabela: str, colunas_raw: list) -> dict:
    """Mesma lógica do painel gráfico, só que perguntando no terminal em vez de mostrar um menu clicável."""
    sugestoes = sugerir_mapping.sugerir_para_tabela(colunas_raw, nome_tabela)
    melhor_por_conceito = {}
    for s in sugestoes:
        if s["sugestao_canonica"]:
            atual = melhor_por_conceito.get(s["sugestao_canonica"])
            if atual is None or s["confianca"] > atual[1]:
                melhor_por_conceito[s["sugestao_canonica"]] = (s["coluna_original"], s["confianca"])

    mapeamento_final = {}
    for conceito, pergunta in CAMPOS_POR_TABELA[nome_tabela].items():
        default_col, _ = melhor_por_conceito.get(conceito, (None, 0))
        if default_col:
            resposta = input(f"   {pergunta}\n     -> achei \"{default_col}\" (Enter pra confirmar, ou digite outro nome de coluna, ou \"0\" pra pular): ").strip()
        else:
            resposta = input(f"   {pergunta}\n     -> não achei nada parecido. Digite o nome exato da coluna, ou Enter pra pular: ").strip()
            default_col = None

        if resposta == "0":
            continue
        coluna_escolhida = resposta if resposta else default_col
        if coluna_escolhida:
            if coluna_escolhida not in colunas_raw:
                print(f"     ⚠️  \"{coluna_escolhida}\" não existe nesse arquivo -- pulando esse campo.")
                continue
            mapeamento_final[coluna_escolhida] = conceito
    return mapeamento_final


def opcao_dados_exemplo():
    linha()
    print("Rodando com os dados de exemplo (RavenStack)...")
    linha()
    rodar_motor(parse_args([]))
    input("\nPronto. Os relatórios estão na pasta outputs/. Pressione Enter pra voltar ao menu.")


def opcao_dados_proprios():
    linha()
    print("Rodar com os SEUS dados")
    linha()
    print("Coloque seus arquivos numa pasta (pode ter qualquer nome de arquivo).")
    print("Aceita CSV, Excel (.xlsx/.xls) e JSON -- pode misturar formatos,")
    print("cada tabela pode vir num formato diferente.")
    print("Precisa de pelo menos 3: clientes, contratos e cancelamentos.")
    print("Uso da plataforma e chamados de suporte são opcionais -- mas quanto mais")
    print("você tiver, mais completa fica a análise de risco.")
    pasta = input("Cole aqui o caminho completo dessa pasta: ").strip().strip('"')

    if not os.path.isdir(pasta):
        print(f"\n⚠️  Não encontrei a pasta \"{pasta}\". Confira o caminho e tente de novo.")
        input("Pressione Enter pra voltar ao menu.")
        return

    arquivos_achados = []
    for extensao in leitor_arquivos.FORMATOS_SUPORTADOS:
        arquivos_achados += glob.glob(os.path.join(pasta, f"*.{extensao}"))
    arquivos_achados = sorted(arquivos_achados)

    if len(arquivos_achados) < 3:
        print(
            f"\n⚠️  Encontrei só {len(arquivos_achados)} arquivo(s) (CSV/Excel/JSON) nessa pasta. "
            "Preciso de pelo menos 3 (clientes, contratos, cancelamentos)."
        )
        input("Pressione Enter pra voltar ao menu.")
        return

    print(f"\nEncontrei {len(arquivos_achados)} arquivo(s) nessa pasta. Agora me diga qual é qual:")

    pasta_normalizada = os.path.join(PASTA_PROJETO, "configs", "_entrada_terminal")
    os.makedirs(pasta_normalizada, exist_ok=True)

    caminhos_escolhidos = {}
    mapeamentos = {}
    tabelas_puladas = []
    for chave, titulo, explicacao in TABELAS:
        opcional = chave not in TABELAS_OBRIGATORIAS
        caminho_original = escolher_arquivo_para_tabela(titulo, explicacao, arquivos_achados, opcional=opcional)
        if caminho_original is None:
            tabelas_puladas.append(chave)
            continue
        try:
            df_tabela = leitor_arquivos.ler_qualquer_formato(caminho_original)
        except Exception as e:
            print(f"     ⚠️  Não consegui ler \"{os.path.basename(caminho_original)}\" ({e}) -- pulando essa tabela.")
            tabelas_puladas.append(chave)
            continue

        # Normaliza pra CSV -- o motor (main.py) sempre lê CSV; assim quem
        # veio de Excel ou JSON passa pelo MESMO caminho de código de quem
        # já mandou CSV, sem precisar duplicar lógica de leitura no motor.
        caminho_normalizado = os.path.join(pasta_normalizada, f"{chave}.csv")
        df_tabela.to_csv(caminho_normalizado, index=False)
        caminhos_escolhidos[chave] = caminho_normalizado

        print(f"\n   Agora confirme as colunas de \"{os.path.basename(caminho_original)}\":")
        mapeamentos[chave] = revisar_mapeamento_terminal(chave, list(df_tabela.columns))

    pasta_config = os.path.join(PASTA_PROJETO, "configs")
    os.makedirs(pasta_config, exist_ok=True)
    caminho_mapping = os.path.join(pasta_config, "mapping_meus_dados.json")
    with open(caminho_mapping, "w", encoding="utf-8") as f:
        json.dump(mapeamentos, f, ensure_ascii=False, indent=2)

    linha()
    print("Rodando o motor com os seus dados...")
    linha()
    rodar_motor(parse_args([
        "--config", caminho_mapping,
        "--accounts", caminhos_escolhidos["accounts"],
        "--subscriptions", caminhos_escolhidos["subscriptions"],
        "--usage", caminhos_escolhidos.get("usage", ""),
        "--tickets", caminhos_escolhidos.get("tickets", ""),
        "--churn", caminhos_escolhidos["churn"],
    ]))
    input("\nPronto. Os relatórios estão na pasta outputs/. Pressione Enter pra voltar ao menu.")


def opcao_painel():
    linha()
    print("Abrindo o painel gráfico no navegador...")
    print("(pra voltar aqui, feche o navegador e aperte Ctrl+C nesta janela)")
    linha()

    caminho_dashboard = os.path.join(pasta_base(), "dashboard.py")
    if not os.path.exists(caminho_dashboard):
        print(f"❌ Não encontrei {caminho_dashboard} -- o painel gráfico (dashboard.py) precisa estar "
              "na mesma pasta que este programa.")
        return

    # Roda o Streamlit DENTRO deste mesmo processo (em vez de abrir um
    # `python -m streamlit` separado) -- funciona igual rodando
    # `python main.py` OU compilado como .exe. A diferença importa só num
    # .exe: lá, `sys.executable` é o PRÓPRIO programa compilado, não um
    # Python de verdade com o pacote `streamlit` instalável por fora --
    # então "abrir um Python separado pra rodar o Streamlit" não existe
    # mais como opção. Chamando a função do Streamlit diretamente (é a
    # mesma que o comando `streamlit run` chama por baixo dos panos), o
    # binário compilado consegue subir o painel sozinho, sem depender de
    # mais nada instalado na máquina.
    from streamlit.web import cli as stcli

    cwd_original = os.getcwd()
    try:
        os.chdir(pasta_base())
        # standalone_mode=False é o que faz essa chamada RETORNAR pra cá
        # depois que a pessoa fecha o navegador e aperta Ctrl+C, em vez de
        # encerrar o programa inteiro sozinha -- importante porque essa
        # mesma função também é chamada de dentro do menu interativo
        # (opção 3), onde precisa voltar pro menu depois, não sair do
        # programa (testado: sem isso, dar Ctrl+C aqui fecharia o menu
        # inteiro em vez de só o painel).
        stcli.main(
            args=["run", caminho_dashboard, "--global.developmentMode=false"],
            standalone_mode=False,
        )
    finally:
        os.chdir(cwd_original)


def opcao_validar():
    linha()
    print("Conferindo se os relatórios em outputs/ estão corretos...")
    linha()
    # Chama a função de validação diretamente (em vez de abrir
    # `validar_outputs.py` como programa separado) -- pelo mesmo motivo do
    # painel acima: num .exe compilado não tem Python separado pra chamar.
    # Também simplifica o caso normal (python main.py): um processo a
    # menos pra abrir por algo tão rápido quanto essa checagem.
    import validar_outputs
    argv_original = sys.argv
    try:
        sys.argv = ["validar_outputs.py", "--output-dir", os.path.join(pasta_base(), "outputs")]
        validar_outputs.main()
    except SystemExit:
        pass
    finally:
        sys.argv = argv_original
    input("\nPressione Enter pra voltar ao menu.")


def mostrar_menu():
    print()
    linha()
    print("CHURN ENGINE — o que você quer fazer?")
    linha()
    print("1) Rodar com dados de exemplo")
    print("   Usa os dados de teste que já vêm no projeto -- é só pra ver o sistema funcionando.")
    print()
    print("2) Rodar com os meus dados")
    print("   Você mostra a pasta com os SEUS arquivos CSV e o sistema gera o diagnóstico com eles.")
    print()
    print("3) Ver o painel gráfico")
    print("   Abre uma tela no navegador com os gráficos do último resultado gerado (opção 1 ou 2).")
    print("   Esse é o padrão rodando sem nenhuma opção (ou dando 2 cliques no .exe) -- você só está")
    print("   vendo este menu agora porque abriu com --menu.")
    print()
    print("4) Conferir se os relatórios estão corretos")
    print("   Confere se os arquivos do último resultado (opção 1 ou 2) foram gerados sem erro.")
    print()
    print("5) Sair")


def menu_interativo():
    while True:
        mostrar_menu()
        escolha = input("\nDigite o número e Enter: ").strip()

        if escolha == "1":
            opcao_dados_exemplo()
        elif escolha == "2":
            opcao_dados_proprios()
        elif escolha == "3":
            opcao_painel()
        elif escolha == "4":
            opcao_validar()
        elif escolha == "5":
            print("Até mais.")
            break
        else:
            print("Não entendi. Digite um número de 1 a 5.")


def main():
    # Sem nenhum argumento (2 cliques no .exe compilado cai aqui) -> abre
    # direto o painel gráfico. Já dá pra fazer tudo por lá, então o menu de
    # terminal deixou de ser o ponto de entrada padrão (ver --menu abaixo).
    if len(sys.argv) == 1 or "--painel" in sys.argv:
        opcao_painel()
        return

    # python main.py --menu -> o menu de terminal antigo (rodar sem abrir
    # navegador, conferir outputs/, etc.) continua existindo, só não é mais
    # o padrão.
    if "--menu" in sys.argv:
        menu_interativo()
        return

    # Qualquer outro argumento (--config, --accounts, --output-dir...) ->
    # roda o motor direto, sem menu nem painel. É o que o painel e o menu
    # (opções 1 e 2) usam por baixo dos panos, e é o jeito de apontar pra
    # qualquer fonte de dados nova.
    args = parse_args()
    rodar_motor(args)


if __name__ == "__main__":
    main()
