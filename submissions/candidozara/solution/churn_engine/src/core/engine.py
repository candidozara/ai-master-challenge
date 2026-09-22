import pandas as pd

from src.core import analytics


class ChurnDiagnosticEngine:
    """
    O Cérebro: cruza as fontes (já traduzidas pelo DataMapper para o
    Contrato Canônico) e devolve uma única Super Tabela, 1 linha por
    conta, com tudo que o motor de risco (analytics.py) precisa.

    accounts, subscriptions e churn são obrigatórias (sem elas não dá pra
    saber quem é cliente, quanto paga, nem quem cancelou). usage e tickets
    são OPCIONAIS -- passe None (ou um DataFrame vazio) quando não tiver
    esse dado; o score de risco resultante fica mais simples (menos sinais
    disponíveis), mas o pipeline roda normalmente.
    """

    def __init__(
        self,
        df_accounts: pd.DataFrame,
        df_subscriptions: pd.DataFrame,
        df_usage: pd.DataFrame | None,
        df_tickets: pd.DataFrame | None,
        df_churn: pd.DataFrame,
    ):
        self.accounts = df_accounts
        self.subscriptions = df_subscriptions
        self.usage = df_usage
        self.tickets = df_tickets
        self.churn = df_churn

    # -- assinatura mais recente por conta (MRR, ARR, plano de cobrança) --
    def _ultima_assinatura_por_conta(self) -> pd.DataFrame:
        if self.subscriptions is None or self.subscriptions.empty:
            return pd.DataFrame(columns=["canonical_id"])

        subs = self.subscriptions.copy()
        if "canonical_sub_start" in subs.columns:
            subs["canonical_sub_start"] = pd.to_datetime(subs["canonical_sub_start"], errors="coerce")
            subs = subs.sort_values("canonical_sub_start")
        else:
            # "Data de início do contrato" é um campo OPCIONAL dentro da
            # tabela de Contratos (a pessoa pode deixar "não tenho essa
            # informação" no mapeamento) -- sem ele, não dá pra ordenar por
            # data, mas o pipeline segue: pega a última linha de cada conta
            # na ordem em que veio no arquivo, em vez de travar por causa de
            # UM campo que não pôde ser mapeado.
            print("⚠️  [engine] \"canonical_sub_start\" não mapeado -- pegando a última assinatura na ordem do arquivo (sem ordenar por data).")

        colunas = [
            "canonical_revenue",
            "canonical_arr",
            "canonical_sub_plan",
            "canonical_billing_frequency",
            "canonical_upgrade",
            "canonical_downgrade",
            "canonical_is_churn_sub",
        ]
        colunas = [c for c in colunas if c in subs.columns]
        ultima = subs.groupby("canonical_id")[colunas].last().reset_index()
        return ultima

    # -- uso: primeiro herda o account_id via subscription_id, depois agrega --
    def _agregar_uso(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        if self.usage is None or self.usage.empty or self.subscriptions is None:
            # "uso" é opcional -- se não veio, devolve 3 tabelas vazias (mesma
            # forma do caminho normal) em vez de quebrar quem chama isso.
            vazio = pd.DataFrame(columns=["canonical_id"])
            return vazio, vazio, vazio

        if "canonical_sub_id" not in self.subscriptions.columns or "canonical_sub_id" not in self.usage.columns:
            # Sem o campo que liga uso -> assinatura -> conta, não dá pra
            # cruzar esse dado com segurança. "Uso" é opcional -- trata como
            # se não tivesse vindo, em vez de travar o pipeline inteiro por
            # causa de um campo não mapeado.
            print("⚠️  [engine] \"canonical_sub_id\" não mapeado em Contratos e/ou Uso -- pulando o cruzamento de uso (dado opcional).")
            vazio = pd.DataFrame(columns=["canonical_id"])
            return vazio, vazio, vazio

        mapa_sub_conta = self.subscriptions[["canonical_sub_id", "canonical_id"]].drop_duplicates()
        usage_com_conta = self.usage.merge(mapa_sub_conta, on="canonical_sub_id", how="left")

        sem_conta = usage_com_conta["canonical_id"].isna().sum()
        if sem_conta:
            print(f"⚠️  [engine] {sem_conta} linhas de uso não encontraram subscription_id correspondente e foram descartadas.")
        usage_com_conta = usage_com_conta.dropna(subset=["canonical_id"])

        # Cada uma dessas 3 colunas de Uso é opcional no mapeamento (a
        # pessoa pode não ter "quantidade de vezes que usou", ou "erros",
        # ou "é beta" no arquivo dela) -- só agrega o que realmente veio,
        # em vez de travar no primeiro campo que faltar.
        agregacoes_uso = {}
        if "canonical_volume" in usage_com_conta.columns:
            agregacoes_uso["total_uso"] = ("canonical_volume", "sum")
        if "canonical_errors" in usage_com_conta.columns:
            agregacoes_uso["total_erros"] = ("canonical_errors", "sum")
        if "canonical_is_beta" in usage_com_conta.columns:
            agregacoes_uso["erros_beta"] = ("canonical_is_beta", lambda x: (x == True).sum())  # noqa: E712
        if agregacoes_uso:
            usage_agg = usage_com_conta.groupby("canonical_id").agg(**agregacoes_uso).reset_index()
        else:
            usage_agg = usage_com_conta[["canonical_id"]].drop_duplicates()

        tendencia_uso = analytics.detectar_queda_de_uso(usage_com_conta)

        # Recência: há quanto tempo (em relação à data mais recente do dataset)
        # a conta usou o produto pela última vez. Sinal fraco isoladamente, mas
        # ajudou um pouco o modelo preditivo em teste com validação cruzada.
        # "Data do uso" também é um campo opcional no mapeamento -- sem ele,
        # não dá pra calcular recência, mas total_uso/total_erros (que não
        # dependem de data) continuam valendo.
        if "canonical_usage_date" in usage_com_conta.columns:
            usage_com_conta["canonical_usage_date"] = pd.to_datetime(usage_com_conta["canonical_usage_date"], errors="coerce")
            data_referencia = usage_com_conta["canonical_usage_date"].max()
            ultimo_uso = usage_com_conta.groupby("canonical_id")["canonical_usage_date"].max()
            recencia_uso = (data_referencia - ultimo_uso).dt.days.rename("dias_desde_ultimo_uso").reset_index()
        else:
            print("⚠️  [engine] \"canonical_usage_date\" não mapeado -- pulando recência de uso (campo opcional).")
            recencia_uso = pd.DataFrame(columns=["canonical_id"])

        return usage_agg, tendencia_uso, recencia_uso

    def _agregar_suporte(self) -> pd.DataFrame:
        if self.tickets is None or self.tickets.empty:
            return pd.DataFrame(columns=["canonical_id"])

        # Cada uma dessas 4 colunas de Tickets é opcional no mapeamento (a
        # pessoa pode não ter "id do chamado", "tempo de primeira resposta",
        # "foi escalado" ou "satisfação" no arquivo dela) -- só agrega o que
        # realmente veio, em vez de travar no primeiro campo que faltar.
        agregacoes_tickets = {}
        if "canonical_ticket_id" in self.tickets.columns:
            agregacoes_tickets["total_tickets"] = ("canonical_ticket_id", "count")
        if "canonical_first_response" in self.tickets.columns:
            agregacoes_tickets["media_resposta_minutos"] = ("canonical_first_response", "mean")
        if "canonical_escalation" in self.tickets.columns:
            agregacoes_tickets["total_escalados"] = ("canonical_escalation", lambda x: (x == True).sum())  # noqa: E712
        if "canonical_satisfaction" in self.tickets.columns:
            agregacoes_tickets["satisfacao_media"] = ("canonical_satisfaction", "mean")
        if agregacoes_tickets:
            tickets_agg = self.tickets.groupby("canonical_id").agg(**agregacoes_tickets).reset_index()
        else:
            tickets_agg = self.tickets[["canonical_id"]].drop_duplicates()

        if "canonical_ticket_date" in self.tickets.columns:
            tickets_com_data = self.tickets.copy()
            tickets_com_data["canonical_ticket_date"] = pd.to_datetime(tickets_com_data["canonical_ticket_date"], errors="coerce")
            data_referencia = tickets_com_data["canonical_ticket_date"].max()
            ultimo_ticket = tickets_com_data.groupby("canonical_id")["canonical_ticket_date"].max()
            recencia_ticket = (data_referencia - ultimo_ticket).dt.days.rename("dias_desde_ultimo_ticket")
            tickets_agg = tickets_agg.merge(recencia_ticket, on="canonical_id", how="left")
        else:
            # "Data de abertura do chamado" é opcional no mapeamento -- sem
            # ela não dá pra calcular recência, mas o resto de tickets_agg
            # (total, tempo de resposta, escalação, satisfação) continua.
            print("⚠️  [engine] \"canonical_ticket_date\" não mapeado -- pulando recência de chamados (campo opcional).")

        return tickets_agg

    def _resumo_churn(self) -> pd.DataFrame:
        if self.churn is None or self.churn.empty:
            return pd.DataFrame(columns=["canonical_id"])

        churn = self.churn.copy()
        if "canonical_churn_date" in churn.columns:
            churn["canonical_churn_date"] = pd.to_datetime(churn["canonical_churn_date"], errors="coerce")
            churn = churn.sort_values("canonical_churn_date")
        else:
            # "Data do cancelamento" é opcional no mapeamento -- sem ela,
            # "motivo mais recente" vira "motivo na ordem do arquivo" em vez
            # de travar por causa de UM campo que não pôde ser mapeado.
            print("⚠️  [engine] \"canonical_churn_date\" não mapeado -- motivo de churn segue a ordem do arquivo (sem ordenar por data).")

        # "eventos_churn" só depende de canonical_id (a chave do groupby, sempre
        # presente). "motivo_churn_mais_recente" e "ja_reativou" dependem de
        # colunas individualmente opcionais no mapeamento -- só agrega o que
        # realmente veio, em vez de travar no primeiro campo que faltar.
        agregacoes_churn = {"eventos_churn": ("canonical_id", "count")}
        if "canonical_churn_reason" in churn.columns:
            agregacoes_churn["motivo_churn_mais_recente"] = ("canonical_churn_reason", "last")
        if "canonical_is_reactivation" in churn.columns:
            agregacoes_churn["ja_reativou"] = ("canonical_is_reactivation", lambda x: (x == True).any())  # noqa: E712

        resumo = churn.groupby("canonical_id").agg(**agregacoes_churn).reset_index()

        return resumo

    def construir_super_tabela(self) -> pd.DataFrame:
        super_tabela = self.accounts.copy()

        assinatura = self._ultima_assinatura_por_conta()
        if not assinatura.empty:
            super_tabela = super_tabela.merge(assinatura, on="canonical_id", how="left")

        usage_agg, tendencia_uso, recencia_uso = self._agregar_uso()
        if not usage_agg.empty:
            super_tabela = super_tabela.merge(usage_agg, on="canonical_id", how="left")
        if not tendencia_uso.empty:
            super_tabela = super_tabela.merge(
                tendencia_uso[["canonical_id", "uso_recente", "uso_anterior", "variacao_uso_pct", "queda_uso_flag"]],
                on="canonical_id",
                how="left",
            )
        if not recencia_uso.empty:
            super_tabela = super_tabela.merge(recencia_uso, on="canonical_id", how="left")

        tickets_agg = self._agregar_suporte()
        if not tickets_agg.empty:
            super_tabela = super_tabela.merge(tickets_agg, on="canonical_id", how="left")

        resumo_churn = self._resumo_churn()
        if not resumo_churn.empty:
            super_tabela = super_tabela.merge(resumo_churn, on="canonical_id", how="left")

        # A verdade sobre quem churnou vem de accounts.csv (canonical_is_churn_account),
        # não da contagem bruta de churn_events -- ver tecnica/04-estrategia_ajustada.md
        # sobre a inconsistência entre as duas fontes.
        if "canonical_is_churn_account" in super_tabela.columns:
            super_tabela["canonical_is_churn_account"] = super_tabela["canonical_is_churn_account"].fillna(False)

        colunas_para_zerar = [
            "total_uso", "total_erros", "erros_beta",
            "total_tickets", "total_escalados", "eventos_churn",
            "canonical_revenue", "canonical_arr",
        ]
        for col in colunas_para_zerar:
            if col in super_tabela.columns:
                super_tabela[col] = super_tabela[col].fillna(0)

        if "queda_uso_flag" in super_tabela.columns:
            super_tabela["queda_uso_flag"] = super_tabela["queda_uso_flag"].fillna(False)

        # Conta sem nenhum registro de uso/ticket -> recência "infinita" (999 dias),
        # não zero, para não confundir "nunca usou" com "usou hoje".
        for col in ["dias_desde_ultimo_uso", "dias_desde_ultimo_ticket"]:
            if col in super_tabela.columns:
                super_tabela[col] = super_tabela[col].fillna(999)

        # Taxas normalizadas: erros/uso e escalações/tickets. Cru (total_erros)
        # favorece quem usa mais o produto -- a taxa é o sinal mais justo.
        if {"total_erros", "total_uso"}.issubset(super_tabela.columns):
            super_tabela["taxa_erro"] = (
                super_tabela["total_erros"] / super_tabela["total_uso"].replace(0, pd.NA)
            ).fillna(0).astype(float)
        if {"total_escalados", "total_tickets"}.issubset(super_tabela.columns):
            super_tabela["taxa_escalonamento"] = (
                super_tabela["total_escalados"] / super_tabela["total_tickets"].replace(0, pd.NA)
            ).fillna(0).astype(float)

        return super_tabela
