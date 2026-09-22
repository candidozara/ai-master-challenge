"""
Demo: IA "fazendo a gestão" -- decidindo ação recomendada por conta em risco.

Isto é uma CAMADA NOVA, separada do sugerir_mapping.py (que resolve nomes de
coluna). Aqui a pergunta é outra: dado o que o motor determinístico já
calculou (risco_churn_api.json), o que uma IA acoplada via API faria com
isso na prática -- decidir/priorizar uma ação por conta, não só descrever.

Dois modos, igual ao sugerir_mapping.py:

  --modo simulado (padrão)  -- NÃO chama nenhuma API. Usa uma função mock
                                (`decidir_acao_mock`) que aplica as mesmas
                                regras que estão documentadas nas
                                Recomendações do projeto, só que por conta
                                individual. Serve pra testar o *formato* da
                                integração (o que entra, o que sai, onde
                                plugar) sem gastar nada e sem precisar de
                                credencial de ninguém.

  --modo real                -- chama de verdade a API da Anthropic
                                (`anthropic` SDK), com o MESMO formato de
                                saída do modo simulado. Requer
                                ANTHROPIC_API_KEY no ambiente. Sem a chave,
                                cai pro modo simulado avisando o motivo --
                                nunca quebra.

Em ambos os modos, a decisão final some SEMPRE marcada como sugestão --
isto não escreve nada de volta nos dados nem dispara nenhuma ação real
(e-mail, desconto, ticket). É a camada de decisão, não a camada de execução.

Uso:
    python demo_ia_gestao.py --output-dir outputs --top-n 5
    python demo_ia_gestao.py --output-dir outputs --top-n 5 --modo real
"""

import argparse
import json
import os


def decidir_acao_mock(conta: dict) -> dict:
    """
    Modo simulado -- NÃO é IA generativa, é uma função determinística que
    imita o FORMATO de saída que uma IA real devolveria, aplicando as
    mesmas regras de negócio documentadas nas Recomendações do projeto.
    Serve pra testar a integração (schema de entrada/saída, onde plugar)
    sem gastar tokens nem precisar de credencial.
    """
    score = conta.get("risco_score_regra", 0)
    industry = conta.get("canonical_industry", "")
    dias_uso = conta.get("dias_desde_ultimo_uso", 0)
    taxa_erro = conta.get("taxa_erro", 0) or 0
    ticket_escalado = conta.get("taxa_escalonamento", 0) or 0

    motivos = []
    acao = "Monitorar"
    urgencia = "Baixa"

    if dias_uso and dias_uso >= 30:
        motivos.append(f"sem uso há {int(dias_uso)} dias")
        acao = "Contato proativo do CS perguntando se há bloqueio de uso"
        urgencia = "Alta"
    if taxa_erro and taxa_erro > 0.05:
        motivos.append(f"taxa de erro em uso de {taxa_erro*100:.1f}%")
        acao = "Engenharia investigar bugs na conta antes do CS ligar"
        urgencia = "Alta"
    if ticket_escalado and ticket_escalado > 0.3:
        motivos.append(f"{ticket_escalado*100:.0f}% dos tickets escalados")
        acao = "Priorizar fila de suporte / revisar SLA da conta"
        urgencia = "Alta" if urgencia != "Alta" else urgencia
    if industry == "DevTools":
        motivos.append("segmento DevTools (31% de churn histórico)")
        if urgencia == "Baixa":
            urgencia = "Média"
    if not motivos:
        motivos.append("risco elevado sem causa específica identificada nos dados disponíveis")

    return {
        "acao_recomendada": acao,
        "urgencia": urgencia,
        "motivos": motivos,
        "fonte": "simulado (regras, não IA generativa)",
    }


def decidir_acao_real(conta: dict, modelo: str = "claude-sonnet-4-5"):
    """
    Modo real -- chama a API da Anthropic de verdade. Mesma forma de saída
    do modo simulado, pra quem tiver ANTHROPIC_API_KEY poder trocar um
    pelo outro sem mudar o resto do pipeline.
    """
    try:
        import anthropic
    except ImportError:
        print("⚠️  Pacote 'anthropic' não instalado. Caindo para o modo simulado.")
        return decidir_acao_mock(conta) | {"fonte": "simulado (fallback: anthropic não instalado)"}

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY não definida. Caindo para o modo simulado.")
        return decidir_acao_mock(conta) | {"fonte": "simulado (fallback: sem API key)"}

    prompt = f"""Você é um analista de Customer Success. Dado o perfil de risco desta conta
(dados já calculados por um motor determinístico, não invente números novos),
decida UMA ação recomendada, a urgência (Baixa/Média/Alta) e liste os motivos
observados nos dados.

Dados da conta:
{json.dumps(conta, ensure_ascii=False, indent=2, default=str)}

Responda SOMENTE um JSON válido: {{"acao_recomendada": "...", "urgencia": "...", "motivos": ["..."]}}"""

    try:
        client = anthropic.Anthropic()
        resposta = client.messages.create(
            model=modelo, max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        texto = resposta.content[0].text.strip()
        texto = texto.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        decisao = json.loads(texto)
        decisao["fonte"] = f"IA real ({modelo})"
        return decisao
    except Exception as e:
        print(f"⚠️  Chamada à IA falhou ({e}). Caindo para o modo simulado.")
        return decidir_acao_mock(conta) | {"fonte": f"simulado (fallback: erro na API - {e})"}


def main():
    parser = argparse.ArgumentParser(description="Demo: IA decidindo ação por conta em risco (simulado ou real)")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--modo", choices=["simulado", "real"], default="simulado")
    args = parser.parse_args()

    caminho = os.path.join(args.output_dir, "processed", "risco_churn_api.json")
    if not os.path.exists(caminho):
        print(f"❌ Não achei {caminho}. Rode main.py --output-dir {args.output_dir} primeiro.")
        return

    with open(caminho, "r", encoding="utf-8") as f:
        contas = json.load(f)

    top = contas[: args.top_n]
    print(f"\n🤖 Modo: {args.modo.upper()} -- decidindo ação para {len(top)} conta(s) em risco\n")
    print(f"{'Conta':<16} {'Score':<7} {'Urgência':<9} {'Ação recomendada'}")
    print("-" * 100)

    resultados = []
    for conta in top:
        decisao = decidir_acao_real(conta) if args.modo == "real" else decidir_acao_mock(conta)
        nome = str(conta.get("canonical_name", conta.get("canonical_id", "?")))[:15]
        print(f"{nome:<16} {conta.get('risco_score_regra', '?'):<7} {decisao['urgencia']:<9} {decisao['acao_recomendada']}")
        resultados.append({"conta": nome, "id": conta.get("canonical_id"), **decisao})

    destino = os.path.join(args.output_dir, "processed", "acoes_recomendadas_ia.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Salvo em {destino}")
    print(
        "\n⚠️  Isto é uma camada de DECISÃO, não de EXECUÇÃO: nada aqui envia e-mail, "
        "abre ticket ou aplica desconto sozinho -- cada ação ainda passa por uma pessoa."
    )


if __name__ == "__main__":
    main()
