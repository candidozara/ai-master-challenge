import json
import pandas as pd


class DataMapper:
    """
    Camada de Ingestão e Normalização.

    Traduz qualquer fonte de dados (CSV da RavenStack hoje, SQL Server ou
    Databricks amanhã) para o Contrato Canônico interno, usando um
    dicionário de configuração (De/Para) em JSON. O motor de cálculo
    (core/) nunca precisa saber o nome original das colunas.
    """

    def __init__(self, config_path: str):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def transformar(self, df: pd.DataFrame, nome_tabela: str) -> pd.DataFrame:
        """
        Recebe um DataFrame bruto e renomeia as colunas de acordo com o
        contrato canônico. Colunas que não existem no mapeamento (ou que o
        mapeamento espera mas não existem no DataFrame) são ignoradas sem
        quebrar o pipeline -- isso é registrado para quem quiser auditar.
        """
        if nome_tabela not in self.config:
            raise ValueError(
                f"Tabela '{nome_tabela}' não encontrada no arquivo de configuração."
            )

        mapa_colunas = self.config[nome_tabela]

        colunas_esperadas_ausentes = [
            col_original
            for col_original in mapa_colunas
            if col_original not in df.columns
        ]
        if colunas_esperadas_ausentes:
            print(
                f"⚠️  [mapper] Tabela '{nome_tabela}': colunas no mapeamento "
                f"que não existem no arquivo de origem (ignoradas): "
                f"{colunas_esperadas_ausentes}"
            )

        df_mapeado = df.rename(columns=mapa_colunas)
        return df_mapeado

    def colunas_canonicas_esperadas(self, nome_tabela: str) -> list:
        """Lista as colunas canônicas que este mapeamento promete gerar."""
        if nome_tabela not in self.config:
            return []
        return list(self.config[nome_tabela].values())
