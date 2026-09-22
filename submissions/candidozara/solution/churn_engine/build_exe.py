"""
Gera o executável Windows (.exe) do churn_engine.

RODE ISSO NO SEU WINDOWS DE VERDADE (não dentro de nenhuma VM/container):
    python build_exe.py

O que esse script faz, em ordem:
  1. Confere se está rodando em Windows e insere um aviso se não estiver.
  2. Garante que o pacote `pyinstaller` está instalado (instala se faltar).
  3. Apaga qualquer `dist/churn_engine` e `build/churn_engine` de uma
     compilação anterior, pra nunca misturar lixo de uma rodada velha com a
     nova (ver nota sobre EXCLUSOES_TELEMETRIA abaixo -- isso já aconteceu
     uma vez: sobrou 5 GB de bibliotecas inúteis de uma primeira compilação).
  4. Compila `main.py` com PyInstaller no modo --onedir, com a flag
     --collect-all streamlit (necessária -- sem ela o painel gráfico dá
     "PackageNotFoundError" ou HTTP 404 ao abrir, testado e confirmado) e
     uma lista de --exclude-module (ver EXCLUSOES_TELEMETRIA abaixo).
  5. Copia pra dentro da pasta compilada (dist/churn_engine/) os arquivos
     que o painel gráfico (dashboard.py) precisa como arquivo .py solto de
     verdade (o Streamlit lê o arquivo do disco a cada interação, não dá
     pra embutir só ele dentro do binário) -- dashboard.py e os módulos
     que ele importa direto -- além de data/, outputs/ (resultado já
     calculado dos dados de exemplo) e .streamlit/ inteiras. De configs/,
     só o mapeamento dos dados de exemplo vai -- NÃO vai o seu histórico
     pessoal de testes (configs/historico_analises.json nasce limpo, do
     zero, pra quem receber essa cópia não ver nenhuma análise sua).
  6. Imprime onde ficou o resultado e como testar.

Por que esse script existe (em vez do Claude compilar direto): o ambiente
que o Claude usa pra mexer nos seus arquivos aqui roda dentro de uma VM
Linux isolada -- ele NÃO tem acesso a um Python/PowerShell de Windows de
verdade. Compilar por lá geraria um binário Linux, não um .exe. Por isso
esse script foi deixado pronto pra você rodar localmente, no seu Windows
de verdade, com um único comando.
"""

import os
import shutil
import subprocess
import sys

PASTA_PROJETO = os.path.dirname(os.path.abspath(__file__))

# Módulos que dashboard.py importa direto e que por isso precisam continuar
# como arquivo .py solto do lado do .exe (ver main.py:pasta_base() pra mais
# detalhes de por que isso é necessário com Streamlit).
ARQUIVOS_SOLTOS = [
    "dashboard.py",
    "historico_analises.py",
    "ia_provedores.py",
    "leitor_arquivos.py",
    "sugerir_mapping.py",
    "rotulos_pt.py",
]

# Achado real (rodei o build de verdade e o resultado veio com 5 GB, em vez
# dos ~250-400 MB esperados): o Streamlit tem um arquivo interno
# (`runtime/metrics_util.py`) com uma lista de ~170 bibliotecas de ML/dados/
# nuvem que ele CHECA se estão instaladas, só pra telemetria (reportar quais
# bibliotecas o app usa) -- nunca são exigidas pra rodar. O PyInstaller, ao
# analisar o Streamlit inteiro (`--collect-all`), acaba enxergando essas
# checagens e empacotando cada uma dessas bibliotecas que POR ACASO estava
# instalada na sua máquina (Python global, sem venv) -- coisa como PyTorch
# (sozinho, 4 GB), OpenCV, Transformers, ONNX Runtime -- nada disso tem
# QUALQUER relação com o churn_engine (conferido: nenhum arquivo do projeto
# importa nada disso). Essa lista abaixo exclui explicitamente cada uma
# (a lista inteira do metrics_util, menos o que a gente realmente usa:
# numpy, pandas, plotly, sklearn, streamlit, openpyxl -- esse último porque
# leitor_arquivos.py precisa dele de verdade pra ler .xlsx).
EXCLUSOES_TELEMETRIA = [
    "MySQLdb", "agno", "ai21", "airflow", "aisuite", "alpa", "annoy", "anthropic",
    "assemblyai", "authlib", "autogen_agentchat", "av", "azure", "baml_client", "bentoml", "bokeh",
    "boto3", "browser_use", "cassandra", "catboost", "celery", "chromadb", "clarifai", "cohere",
    "comet_llm", "comet_ml", "crawl4ai", "crewai", "cudf", "cv2", "daft", "dagster",
    "dask", "databricks", "datachain", "datasets", "diffusers", "docling", "docx", "dspy",
    "duckdb", "elasticsearch", "embedchain", "evidently", "faiss", "fastchat", "faster_whisper", "fastplotlib",
    "folium", "geopandas", "graphviz", "great_expectations", "groq", "guardrails", "guidance", "haystack",
    "hegel", "hf_xet", "highcharts_core", "httpx", "huggingface_hub", "ibis", "imageio_ffmpeg", "instructor",
    "jax", "jinaai", "keras", "lancedb", "langchain", "langfuse", "langgraph", "librosa",
    "lightgbm", "litellm", "litserve", "llama_api_client", "llama_cpp", "llama_index", "llvmlite", "luigi",
    "mars", "marvin", "matplotlib", "mediapipe", "mem0", "memori", "mistralai", "mlflow",
    "modal", "modin", "mysql", "neo4j", "nltk", "nomic", "numba", "ollama",
    "onnxruntime", "openai", "openllm", "opensearchpy", "optuna", "orjson", "outlines", "pdfplumber",
    "pgvector", "pinecone", "playwright", "plost", "polars", "prefect", "promptflow", "psycopg2",
    "psycopg3", "pydantic", "pydantic_ai", "pyecharts", "pygfx", "pygwalker", "pyllamacpp", "pymilvus",
    "pymongo", "pymssql", "pymysql", "pyodbc", "pypdf", "pyspark", "qdrant_client", "ragas",
    "redis", "reka", "replicate", "rich", "safetensors", "sagemaker", "seaborn", "semantic_kernel",
    "semantic_router", "sentence_transformers", "sentencepiece", "shap", "skimage", "smolagents", "snowflake", "soundfile",
    "spacy", "sqlalchemy", "streamlit_extras", "streamlit_pydantic", "supabase", "swarm", "tables", "tensorflow",
    "tiktoken", "together", "tokenizers", "torch", "torchaudio", "torchvision", "transformers", "trubrics",
    "ultralytics", "unsloth", "uvloop", "vaex", "vertexai", "vllm", "wandb", "weaviate",
    "xai_sdk", "xarray", "xgboost", "xlsxwriter", "zarr",
]


def linha():
    print("-" * 70)


def checar_ambiente():
    linha()
    print(f"Python: {sys.version.split()[0]}  |  Plataforma: {sys.platform}")
    if not sys.platform.startswith("win"):
        print("⚠️  Isso não parece ser um Windows de verdade (sys.platform="
              f"{sys.platform!r}). Se você rodar assim mesmo, o executável "
              "gerado só vai funcionar nesta mesma plataforma -- não será um "
              ".exe utilizável no Windows.")
        resposta = input("Continuar mesmo assim? [s/N] ").strip().lower()
        if resposta != "s":
            sys.exit(1)


def garantir_pyinstaller():
    linha()
    try:
        import PyInstaller  # noqa: F401
        print("PyInstaller já está instalado.")
    except ImportError:
        print("Instalando PyInstaller (não estava presente)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)


def limpar_build_anterior():
    linha()
    for pasta in (os.path.join(PASTA_PROJETO, "dist", "churn_engine"),
                  os.path.join(PASTA_PROJETO, "build", "churn_engine")):
        if os.path.isdir(pasta):
            print(f"Removendo build anterior: {pasta}")
            shutil.rmtree(pasta)


def compilar():
    linha()
    print("Compilando main.py com PyInstaller (--onedir --collect-all streamlit)...")
    print("Isso pode levar alguns minutos na primeira vez.")
    linha()
    comando = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--noconfirm",
        "--name", "churn_engine",
        "--collect-all", "streamlit",
    ]
    for nome in EXCLUSOES_TELEMETRIA:
        comando += ["--exclude-module", nome]
    comando.append("main.py")
    resultado = subprocess.run(comando, cwd=PASTA_PROJETO)
    if resultado.returncode != 0:
        print("❌ PyInstaller terminou com erro (veja o log acima). Nada foi copiado.")
        sys.exit(1)


def montar_distribuicao():
    linha()
    pasta_dist = os.path.join(PASTA_PROJETO, "dist", "churn_engine")
    if not os.path.isdir(pasta_dist):
        print(f"❌ Não encontrei {pasta_dist} -- a compilação parece não ter gerado a pasta esperada.")
        sys.exit(1)

    print(f"Copiando arquivos soltos pra dentro de {pasta_dist} ...")
    for nome in ARQUIVOS_SOLTOS:
        origem = os.path.join(PASTA_PROJETO, nome)
        destino = os.path.join(pasta_dist, nome)
        shutil.copy2(origem, destino)
        print(f"  copiado: {nome}")

    # data/, outputs/ (resultado já calculado dos dados de exemplo -- sem
    # isso, a sessão "Diagnóstico do desafio" abre sem nenhum arquivo por
    # trás, achado testando de verdade) e .streamlit/ vão inteiras, como
    # vieram.
    for pasta in ("data", "outputs", ".streamlit"):
        origem = os.path.join(PASTA_PROJETO, pasta)
        destino = os.path.join(pasta_dist, pasta)
        if not os.path.exists(origem):
            print(f"  ⚠️  {pasta}/ não existe em {PASTA_PROJETO} -- pulando (pode fazer falta).")
            continue
        if os.path.exists(destino):
            shutil.rmtree(destino)
        shutil.copytree(origem, destino)
        print(f"  copiada: {pasta}/")

    # configs/ NÃO vai inteira -- ela também guarda o SEU histórico pessoal
    # de testes (configs/historico_analises.json, com toda análise que você
    # já rodou nesta máquina) e isso não tem nada a ver com quem for abrir
    # essa cópia distribuída (achado ao vivo: um "Análise 20/09 19:47" seu
    # apareceu na barra lateral de quem recebesse o .exe, apontando pra uma
    # pasta de resultado que nem foi copiada, dando erro). Só o arquivo de
    # mapeamento (o "De/Para" dos dados de exemplo) precisa ir; o histórico
    # nasce limpo -- o próprio painel recria sozinho a sessão "Diagnóstico
    # do desafio" na primeira vez que abre (usando o outputs/ copiado acima).
    pasta_configs_dist = os.path.join(pasta_dist, "configs")
    os.makedirs(pasta_configs_dist, exist_ok=True)
    shutil.copy2(
        os.path.join(PASTA_PROJETO, "configs", "mapping_ravenstack.json"),
        os.path.join(pasta_configs_dist, "mapping_ravenstack.json"),
    )
    with open(os.path.join(pasta_configs_dist, "historico_analises.json"), "w", encoding="utf-8") as f:
        f.write("[]")
    print("  copiado: configs/mapping_ravenstack.json")
    print("  criado:  configs/historico_analises.json (limpo, sem o seu histórico de testes)")

    return pasta_dist


def resumo_final(pasta_dist):
    linha()
    tamanho_total = 0
    contagem_arquivos = 0
    for raiz, _dirs, arquivos in os.walk(pasta_dist):
        for nome in arquivos:
            tamanho_total += os.path.getsize(os.path.join(raiz, nome))
            contagem_arquivos += 1
    print(f"✅ Pronto! Distribuição gerada em:\n   {pasta_dist}")
    print(f"   ({contagem_arquivos} arquivos, {tamanho_total / (1024*1024):.0f} MB)")
    linha()
    print("Como testar:")
    print(f'  1. Abra o Prompt de Comando ou PowerShell na pasta "{pasta_dist}"')
    print("  2. Dois cliques em churn_engine.exe  -> abre o painel gráfico no navegador")
    print("     ou no terminal: churn_engine.exe --menu -> menu no terminal, sem navegador")
    linha()
    print("Pra distribuir/mover pra outro lugar: copie a pasta inteira")
    print(f'"{os.path.basename(pasta_dist)}" (não só o .exe -- ele depende dos')
    print("arquivos e pastas ao lado dele: _internal/, data/, configs/, e os .py soltos).")
    linha()
    print("Pra mandar pra outra pessoa (computador diferente do seu):")
    print(f'  1. Compacte a pasta inteira "{os.path.basename(pasta_dist)}" num .zip')
    print("     (com milhares de arquivos soltos, mandar sem compactar é inviável).")
    print("  2. Não precisa ter Python instalado no PC de quem recebe -- o .exe já")
    print("     carrega tudo que precisa junto. Só precisa ser um Windows (o mesmo")
    print("     tipo do seu -- 64 bits; não funciona em Mac, Linux ou Windows ARM).")
    print("  3. É esperado que o Windows Defender (ou outro antivírus) avise")
    print('     "Windows protegeu seu PC" na primeira vez que a pessoa abrir o')
    print("     .exe, mesmo sem ter nada de errado -- é comum com programas feitos")
    print('     com PyInstaller, por não ter uma "assinatura digital" paga por trás.')
    print('     A pessoa clica em "Mais informações" -> "Executar assim mesmo".')


def main():
    checar_ambiente()
    garantir_pyinstaller()
    limpar_build_anterior()
    compilar()
    pasta_dist = montar_distribuicao()
    resumo_final(pasta_dist)


if __name__ == "__main__":
    main()
