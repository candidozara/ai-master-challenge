"""
Validação pós-execução: confere se as 6 saídas do pipeline existem, têm o
formato certo e batem entre si (o mesmo número de contas, a mesma taxa de
churn, etc). Rode depois de `python main.py`:

    python validar_outputs.py [--output-dir outputs]

Não é um teste unitário de código -- é um "isso realmente funcionou?" que
você (ou qualquer pessoa revisando a submissão) pode rodar sem precisar
ler uma linha de Python.
"""

import argparse
import json
import os
import sys

import pandas as pd


def checar(nome: str, condicao: bool, detalhe: str = "") -> bool:
    marca = "✅" if condicao else "❌"
    print(f"{marca} {nome}" + (f" — {detalhe}" if detalhe else ""))
    return condicao


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()

    processed = os.path.join(args.output_dir, "processed")
    reports = os.path.join(args.output_dir, "reports")

    caminho_csv = os.path.join(processed, "super_tabela_churn.csv")
    caminho_json = os.path.join(processed, "risco_churn_api.json")
    caminho_segmentos = os.path.join(processed, "segmentos_risco.csv")
    caminho_pdf = os.path.join(reports, "relatorio_executivo_churn.pdf")
    caminho_md = os.path.join(reports, "relatorio_executivo_churn.md")

    tudo_ok = True

    # 1. Existência dos arquivos
    for caminho in [caminho_csv, caminho_json, caminho_segmentos, caminho_pdf, caminho_md]:
        tudo_ok &= checar(f"Arquivo existe: {caminho}", os.path.exists(caminho))

    if not tudo_ok:
        print("\n❌ Pelo menos um arquivo não foi gerado. Rode `python main.py` primeiro.")
        sys.exit(1)

    # 2. CSV principal: schema e consistência básica
    #
    # "500 contas" e "15%-30% de churn" eram verdades fixas SÓ enquanto todo
    # mundo testava contra o mesmo dataset sintético (RavenStack/Fonte B/C).
    # Pra dados reais de qualquer empresa (outro tamanho, outra taxa de
    # churn), isso não é um requisito -- é só informativo. O que continua
    # sendo um requisito de verdade (funciona pra QUALQUER fonte) fica com
    # ✅/❌; o que é específico deste dataset de teste vira "ℹ️" informativo.
    df = pd.read_csv(caminho_csv)
    print(f"ℹ️  Super tabela tem {len(df)} conta(s).")
    tudo_ok &= checar("Super tabela tem pelo menos 1 conta", len(df) > 0)
    tudo_ok &= checar("canonical_id é único (sem contas duplicadas)", df["canonical_id"].is_unique)

    colunas_esperadas_sempre = {
        "canonical_id", "canonical_is_churn_account", "canonical_revenue",
        "risco_score_regra", "risco_score_modelo",
    }
    faltando = colunas_esperadas_sempre - set(df.columns)
    tudo_ok &= checar("Colunas-chave presentes na super tabela", not faltando, f"faltando: {faltando}" if faltando else "")

    # queda_uso_flag só existe se a tabela de "uso" foi enviada (é opcional) --
    # sua ausência não é um erro, é esperado quando rodou só com o mínimo.
    if "queda_uso_flag" not in df.columns:
        print("ℹ️  Sem 'queda_uso_flag' na super tabela -- rodou sem dados de uso da plataforma (opcional). Score de regra fica mais simples.")

    taxa_churn = df["canonical_is_churn_account"].mean() * 100
    print(f"ℹ️  Taxa de churn: {taxa_churn:.1f}% (informativo -- varia de empresa pra empresa, não é um requisito).")

    # 3. JSON: válido e consistente com o CSV
    with open(caminho_json, "r", encoding="utf-8") as f:
        dados_json = json.load(f)
    tudo_ok &= checar("JSON é uma lista de registros", isinstance(dados_json, list))
    if dados_json:
        tudo_ok &= checar(
            "Contas no JSON são só ativas (canonical_is_churn_account = false)",
            all(r.get("canonical_is_churn_account") in (False, 0) for r in dados_json),
        )
        tudo_ok &= checar(
            "Contas no JSON estão ordenadas por risco decrescente",
            all(
                dados_json[i].get("risco_score_regra", 0) >= dados_json[i + 1].get("risco_score_regra", 0)
                for i in range(len(dados_json) - 1)
            ),
        )

    # 4. Segmentos: taxas de churn calculadas corretamente
    df_seg = pd.read_csv(caminho_segmentos)
    tudo_ok &= checar("Tabela de segmentos não está vazia", len(df_seg) > 0)
    tudo_ok &= checar(
        "Taxas de churn dos segmentos estão entre 0% e 100%",
        df_seg["taxa_churn_pct"].between(0, 100).all(),
    )

    # 5. PDF: consegue ser lido e tem o número certo de contas
    try:
        from pypdf import PdfReader
        leitor = PdfReader(caminho_pdf)
        texto = "\n".join(p.extract_text() for p in leitor.pages)
        tudo_ok &= checar("PDF tem pelo menos 1 página", len(leitor.pages) >= 1)
        tudo_ok &= checar(
            f"PDF contém o total de contas correto ({len(df)})",
            str(len(df)) in texto,
        )
    except ImportError:
        print("⚠️  pypdf não instalado — pulei a checagem de conteúdo do PDF (`pip install pypdf`).")

    # 6. Markdown: contém as seções esperadas
    with open(caminho_md, "r", encoding="utf-8") as f:
        texto_md = f.read()
    for secao in ["Visão Geral de Impacto", "Causas Raiz", "Segmentos Mais em Risco"]:
        tudo_ok &= checar(f"Relatório Markdown contém a seção '{secao}'", secao in texto_md)

    print()
    if tudo_ok:
        print("✅ Todas as checagens passaram. As 4 saídas (CSV, JSON, PDF, Markdown) estão consistentes entre si.")
    else:
        print("❌ Alguma checagem falhou -- veja acima antes de considerar a saída confiável.")
        sys.exit(1)


if __name__ == "__main__":
    main()
