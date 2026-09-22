churn_engine/
│
├── data/                       # Onde ficam os dados brutos de entrada (CSVs, exports)
│   ├── ravenstack_accounts.csv
│   ├── ravenstack_feature_usage.csv
│   └── ...
│
├── outputs/                    # Onde a ferramenta despeja os resultados gerados
│   ├── reports/                # Relatórios em Markdown / PDF para o C-Level
│   └── processed/              # Super tabelas geradas em CSV ou JSON para APIs/BI
│
├── src/                        # O código-fonte principal do motor
│   ├── __init__.py
│   │
│   ├── core/                   # O "Cérebro" analítico (agnóstico e imutável)
│   │   ├── __init__.py
│   │   ├── engine.py           # Classe principal que faz o cruzamento e a lógica de churn
│   │   └── analytics.py        # Funções de cálculo estatístico e identificação de causas raiz
│   │
│   ├── adapters/               # Camada de Ingestão e Mapeamento (De/Para)
│   │   ├── __init__.py
│   │   ├── base_adapter.py     # Lógica base de leitura dos arquivos/bancos
│   │   └── mapper.py           # O motor do dicionário de configuração (mapeamento determinístico)
│   │
│   └── outputs/                # Camada de Exportação (Multicanal)
│       ├── __init__.py
│       ├── exporter_csv.py     # Gera as tabelas limpas para BI
│       ├── exporter_api.py     # Prepara os dados em formato JSON (pronto para FastAPI / G4 OS)
│       └── exporter_report.py  # Monta o relatório executivo (Markdown/PDF)
│
├── configs/                    # Arquivos de Configuração (Metadados e De/Para)
│   ├── mapping_ravenstack.json # Dicionário de colunas da RavenStack
│   └── mapping_future_db.json  # Exemplo de mapeamento para uma futura base de dados (Fase 2)
│
├── main.py                     # O ponto de entrada (Orquestrador: chama o adapter, o core e o exporter)
├── requirements.txt            # Dependências do projeto (pandas, numpy, etc.)
└── README.md                   # Documentação do projeto (o esqueleto do GitHub que você montou)