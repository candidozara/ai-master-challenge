import os
import json
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)


class ChurnExporter:
    """
    Camada de Exportação Multicanal. Recebe a Super Tabela (já com os
    scores de risco calculados) e entrega o mesmo resultado em 3
    formatos, para 3 públicos diferentes:

    - CSV  -> BI / Power BI / Databricks / SQL Server (carga em lote)
    - JSON -> APIs / agentes / G4 OS (consumo programático)
    - PDF  -> o CEO, que não vai abrir um CSV
    """

    def __init__(self, super_tabela: pd.DataFrame, output_dir: str = "outputs"):
        self.df = super_tabela
        self.output_dir = output_dir
        os.makedirs(f"{output_dir}/processed", exist_ok=True)
        os.makedirs(f"{output_dir}/reports", exist_ok=True)

    def _escolher_coluna_score(self) -> str:
        """
        Normalmente usa risco_score_regra (determinístico, auditável) como
        critério principal. MAS: esse score é somado inteiramente a partir
        de sinais de uso e suporte (queda de uso, erros beta, escalonamento,
        tempo de resposta) -- se essas duas tabelas não vieram (rodando só
        com accounts/subscriptions/churn), o score de regra fica 0 pra
        TODO MUNDO, e a lista de contas em risco sairia vazia por engano.
        Nesse caso específico, cai pro risco_score_modelo em vez de mentir
        que "ninguém está em risco".
        """
        tem_regra = "risco_score_regra" in self.df.columns
        tem_modelo = "risco_score_modelo" in self.df.columns

        if tem_regra:
            sem_sinal = self.df["risco_score_regra"].max() == 0 and self.df["risco_score_regra"].nunique() <= 1
            if sem_sinal and tem_modelo:
                print(
                    "⚠️  [exporter] risco_score_regra não teve nenhum sinal (sem dados de uso/suporte) "
                    "-- usando risco_score_modelo pra montar a lista/relatório de risco."
                )
                return "risco_score_modelo"
            return "risco_score_regra"
        return "risco_score_modelo"

    # ------------------------------------------------------------------
    def exportar_csv_bi(self, nome_arquivo: str = "super_tabela_churn.csv") -> str:
        caminho = os.path.join(self.output_dir, "processed", nome_arquivo)
        self.df.to_csv(caminho, index=False, encoding="utf-8")
        print(f"📊 Tabela de BI exportada: {caminho}")
        return caminho

    # ------------------------------------------------------------------
    def exportar_api_json(
        self,
        nome_arquivo: str = "risco_churn_api.json",
        apenas_ativos_em_risco: bool = True,
        risco_minimo: int = 50,
    ) -> str:
        """
        Por padrão, exporta só as contas ATIVAS com risco Alto/Crítico --
        é a lista que um agente (ou o CS) realmente precisa consumir
        amanhã de manhã. Passe apenas_ativos_em_risco=False para exportar
        a base inteira.
        """
        caminho = os.path.join(self.output_dir, "processed", nome_arquivo)

        df_export = self.df
        if apenas_ativos_em_risco and "canonical_is_churn_account" in self.df.columns:
            # risco_score_regra é o score determinístico/auditável -- usado como critério
            # principal porque o modelo de ML (risco_score_modelo) validou com sinal fraco
            # neste dataset (ver metricas_modelo['interpretacao']). Ambos ficam na tabela.
            # (cai pro score do modelo se o de regra não teve nenhum sinal -- ver _escolher_coluna_score)
            score_col = self._escolher_coluna_score()
            df_export = self.df[
                (self.df["canonical_is_churn_account"] == False)  # noqa: E712
                & (self.df.get(score_col, 0) >= risco_minimo)
            ].sort_values(score_col, ascending=False)

        dados_json = json.loads(df_export.to_json(orient="records", date_format="iso"))

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados_json, f, ensure_ascii=False, indent=2)

        print(f"🔌 JSON para API/Agente exportado: {caminho} ({len(dados_json)} contas)")
        return caminho

    # ------------------------------------------------------------------
    def exportar_pdf(
        self,
        nome_arquivo: str = "relatorio_executivo_churn.pdf",
        metricas_modelo: dict | None = None,
        segmentos: pd.DataFrame | None = None,
        motivos_churn: pd.DataFrame | None = None,
        top_n_risco: int = 15,
    ) -> str:
        caminho = os.path.join(self.output_dir, "reports", nome_arquivo)

        estilos = getSampleStyleSheet()
        estilo_titulo = ParagraphStyle("TituloG4", parent=estilos["Title"], fontSize=18, spaceAfter=6)
        estilo_secao = ParagraphStyle("SecaoG4", parent=estilos["Heading2"], spaceBefore=14, spaceAfter=6)
        estilo_corpo = ParagraphStyle("CorpoG4", parent=estilos["BodyText"], fontSize=10, leading=14)

        doc = SimpleDocTemplate(
            caminho, pagesize=A4,
            topMargin=1.6 * cm, bottomMargin=1.6 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        )
        elementos = []

        total_contas = len(self.df)
        total_churns = int(self.df["canonical_is_churn_account"].sum()) if "canonical_is_churn_account" in self.df.columns else 0
        taxa_churn = (total_churns / total_contas * 100) if total_contas else 0

        mrr_perdido = 0.0
        mrr_total = 0.0
        if "canonical_revenue" in self.df.columns and "canonical_is_churn_account" in self.df.columns:
            mrr_perdido = self.df.loc[self.df["canonical_is_churn_account"] == True, "canonical_revenue"].sum()  # noqa: E712
            mrr_total = self.df["canonical_revenue"].sum()

        elementos.append(Paragraph("Diagnóstico de Churn — RavenStack", estilo_titulo))
        elementos.append(Paragraph("Relatório gerado automaticamente pelo Motor Analítico Determinístico + modelo preditivo (scikit-learn)", estilo_corpo))
        elementos.append(Spacer(1, 0.4 * cm))

        elementos.append(Paragraph("1. Visão Geral de Impacto", estilo_secao))
        tabela_resumo = Table(
            [
                ["Total de contas analisadas", f"{total_contas}"],
                ["Total de contas com churn", f"{total_churns}"],
                ["Taxa de churn geral", f"{taxa_churn:.1f}%"],
                ["MRR perdido (contas churned)", f"${mrr_perdido:,.2f}"],
                ["MRR total da base (ativos + churned)", f"${mrr_total:,.2f}"],
            ],
            colWidths=[9 * cm, 6 * cm],
        )
        tabela_resumo.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elementos.append(tabela_resumo)

        if motivos_churn is not None and not motivos_churn.empty:
            elementos.append(Paragraph("2. Causas Raiz Declaradas (reason_code, apenas contas confirmadas como churned)", estilo_secao))
            linhas_motivos = [["Motivo", "% dos eventos"]] + [
                [r.motivo, f"{r.pct}%"] for r in motivos_churn.itertuples()
            ]
            tabela_motivos = Table(linhas_motivos, colWidths=[9 * cm, 6 * cm])
            tabela_motivos.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]))
            elementos.append(tabela_motivos)

        if segmentos is not None and not segmentos.empty:
            elementos.append(Paragraph("3. Segmentos Mais em Risco", estilo_secao))
            top_segmentos = segmentos.sort_values("taxa_churn_pct", ascending=False).head(8)
            linhas_seg = [["Dimensão", "Segmento", "Contas", "Taxa de churn"]]
            for _, r in top_segmentos.iterrows():
                linhas_seg.append([r["dimensao"], str(r["valor"]), int(r["contas"]), f"{r['taxa_churn_pct']}%"])
            tabela_seg = Table(linhas_seg, colWidths=[3.5 * cm, 5.5 * cm, 2.5 * cm, 3.5 * cm])
            tabela_seg.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]))
            elementos.append(tabela_seg)

        score_col = self._escolher_coluna_score()
        if score_col in self.df.columns and "canonical_is_churn_account" in self.df.columns:
            elementos.append(Paragraph("4. Contas Ativas com Maior Risco (para o CS ligar amanhã)", estilo_secao))
            ativos_risco = self.df[self.df["canonical_is_churn_account"] == False].sort_values(score_col, ascending=False).head(top_n_risco)  # noqa: E712
            linhas_risco = [["Conta", "Indústria", "MRR", "Score de risco"]]
            for _, r in ativos_risco.iterrows():
                nome = r.get("canonical_name", r.get("canonical_id", "?"))
                linhas_risco.append([
                    str(nome)[:28],
                    str(r.get("canonical_industry", "-")),
                    f"${r.get('canonical_revenue', 0):,.0f}",
                    f"{r.get(score_col, 0):.0f}",
                ])
            tabela_risco = Table(linhas_risco, colWidths=[6.5 * cm, 4 * cm, 3 * cm, 2.5 * cm])
            tabela_risco.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]))
            elementos.append(tabela_risco)

        if metricas_modelo and metricas_modelo.get("treinado"):
            elementos.append(Paragraph("5. Qualidade do Modelo Preditivo (scikit-learn)", estilo_secao))
            elementos.append(Paragraph(
                f"RandomForest validado com validação cruzada (5 folds) sobre as {metricas_modelo['n_contas']} contas. "
                f"ROC-AUC médio: {metricas_modelo['roc_auc']} ± {metricas_modelo['roc_auc_std']} "
                "(1.0 = perfeito, 0.5 = chute aleatório). "
                f"{metricas_modelo['interpretacao']}",
                estilo_corpo,
            ))

        elementos.append(Paragraph("6. Ações Recomendadas", estilo_secao))
        elementos.append(Paragraph(
            "1) Ativar contato do CS com as contas do item 4 nesta semana, priorizando por MRR. "
            "2) Congelar liberação de features beta para toda a base até o índice de erros cair. "
            "3) Mudar a régua de atendimento: contas Enterprise/Pro com ticket urgente não podem "
            "esperar mais que 2h para o primeiro contato. "
            "4) Revisar o onboarding dos canais de aquisição com maior taxa de churn (ver seção 3).",
            estilo_corpo,
        ))

        doc.build(elementos)
        print(f"📄 Relatório executivo em PDF gerado: {caminho}")
        return caminho

    # ------------------------------------------------------------------
    def gerar_relatorio_markdown(
        self,
        nome_arquivo: str = "relatorio_executivo_churn.md",
        segmentos: pd.DataFrame | None = None,
        motivos_churn: pd.DataFrame | None = None,
    ) -> str:
        """Versão em texto puro do mesmo relatório -- fácil de colar num PR, Notion ou e-mail."""
        caminho = os.path.join(self.output_dir, "reports", nome_arquivo)

        total_contas = len(self.df)
        total_churns = int(self.df["canonical_is_churn_account"].sum()) if "canonical_is_churn_account" in self.df.columns else 0
        taxa_churn = (total_churns / total_contas * 100) if total_contas else 0

        mrr_perdido = 0.0
        if "canonical_revenue" in self.df.columns and "canonical_is_churn_account" in self.df.columns:
            mrr_perdido = self.df.loc[self.df["canonical_is_churn_account"] == True, "canonical_revenue"].sum()  # noqa: E712

        segmentos_md = ""
        if segmentos is not None and not segmentos.empty:
            top = segmentos.sort_values("taxa_churn_pct", ascending=False).head(8)
            linhas = "\n".join(
                f"| {r.dimensao} | {r.valor} | {int(r.contas)} | {r.taxa_churn_pct}% |" for r in top.itertuples()
            )
            segmentos_md = f"""
## 3. Segmentos Mais em Risco

| Dimensão | Segmento | Contas | Taxa de churn |
|---|---|---|---|
{linhas}
"""

        motivos_md = "_Sem dados de motivo disponíveis._"
        if motivos_churn is not None and not motivos_churn.empty:
            motivos_md = "\n".join(f"* **{r.motivo}:** {r.pct}%" for r in motivos_churn.itertuples())

        conteudo_md = f"""# Relatório Executivo de Diagnóstico de Churn
*Gerado automaticamente pelo Motor Analítico Determinístico*

## 1. Visão Geral de Impacto
* **Total de Contas Analisadas:** {total_contas}
* **Total de Churns Registrados:** {total_churns}
* **Taxa de Churn Geral:** {taxa_churn:.1f}%
* **MRR Perdido (contas churned):** ${mrr_perdido:,.2f}

## 2. Principais Causas Raiz Declaradas (contas confirmadas como churned)
{motivos_md}
{segmentos_md}
## 4. Próximas Ações Recomendadas para o CS
* Priorizar contato proativo com as contas ativas de maior score de risco (ver `risco_churn_api.json`).
* Congelar features beta instáveis até o índice de erros cair.
* Mudar a régua de atendimento para contas Enterprise/Pro.
"""

        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo_md)

        print(f"📄 Relatório executivo em Markdown gerado: {caminho}")
        return caminho
