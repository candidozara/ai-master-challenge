# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['MySQLdb', 'agno', 'ai21', 'airflow', 'aisuite', 'alpa', 'annoy', 'anthropic', 'assemblyai', 'authlib', 'autogen_agentchat', 'av', 'azure', 'baml_client', 'bentoml', 'bokeh', 'boto3', 'browser_use', 'cassandra', 'catboost', 'celery', 'chromadb', 'clarifai', 'cohere', 'comet_llm', 'comet_ml', 'crawl4ai', 'crewai', 'cudf', 'cv2', 'daft', 'dagster', 'dask', 'databricks', 'datachain', 'datasets', 'diffusers', 'docling', 'docx', 'dspy', 'duckdb', 'elasticsearch', 'embedchain', 'evidently', 'faiss', 'fastchat', 'faster_whisper', 'fastplotlib', 'folium', 'geopandas', 'graphviz', 'great_expectations', 'groq', 'guardrails', 'guidance', 'haystack', 'hegel', 'hf_xet', 'highcharts_core', 'httpx', 'huggingface_hub', 'ibis', 'imageio_ffmpeg', 'instructor', 'jax', 'jinaai', 'keras', 'lancedb', 'langchain', 'langfuse', 'langgraph', 'librosa', 'lightgbm', 'litellm', 'litserve', 'llama_api_client', 'llama_cpp', 'llama_index', 'llvmlite', 'luigi', 'mars', 'marvin', 'matplotlib', 'mediapipe', 'mem0', 'memori', 'mistralai', 'mlflow', 'modal', 'modin', 'mysql', 'neo4j', 'nltk', 'nomic', 'numba', 'ollama', 'onnxruntime', 'openai', 'openllm', 'opensearchpy', 'optuna', 'orjson', 'outlines', 'pdfplumber', 'pgvector', 'pinecone', 'playwright', 'plost', 'polars', 'prefect', 'promptflow', 'psycopg2', 'psycopg3', 'pydantic', 'pydantic_ai', 'pyecharts', 'pygfx', 'pygwalker', 'pyllamacpp', 'pymilvus', 'pymongo', 'pymssql', 'pymysql', 'pyodbc', 'pypdf', 'pyspark', 'qdrant_client', 'ragas', 'redis', 'reka', 'replicate', 'rich', 'safetensors', 'sagemaker', 'seaborn', 'semantic_kernel', 'semantic_router', 'sentence_transformers', 'sentencepiece', 'shap', 'skimage', 'smolagents', 'snowflake', 'soundfile', 'spacy', 'sqlalchemy', 'streamlit_extras', 'streamlit_pydantic', 'supabase', 'swarm', 'tables', 'tensorflow', 'tiktoken', 'together', 'tokenizers', 'torch', 'torchaudio', 'torchvision', 'transformers', 'trubrics', 'ultralytics', 'unsloth', 'uvloop', 'vaex', 'vertexai', 'vllm', 'wandb', 'weaviate', 'xai_sdk', 'xarray', 'xgboost', 'xlsxwriter', 'zarr'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='churn_engine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='churn_engine',
)
