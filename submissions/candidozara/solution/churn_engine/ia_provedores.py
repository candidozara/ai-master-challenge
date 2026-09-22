"""
Provedores de IA para a camada de decisão (ação recomendada por conta em
risco) -- a mesma camada que já existia em `demo_ia_gestao.py`, só que
chamável de dentro do painel gráfico (aba "🧠 IA de ação"), com duas
opções de onde a IA roda:

  - "anthropic" -- API da Anthropic, com uma chave colada no painel.
  - "local"     -- qualquer servidor rodando na SUA máquina que fale o
                    formato de chat da OpenAI. É o que Ollama e LM Studio
                    (entre outros) já oferecem prontos -- por isso dá pra
                    detectar sozinho nas portas mais comuns, sem você
                    precisar saber o endereço de cor. Se o seu não estiver
                    na lista, dá pra apontar o endereço na mão.

Em ambos os casos, a decisão final volta no MESMO formato
({"acao_recomendada", "urgencia", "motivos", "fonte"}) -- pra quem usa não
importar qual IA está por trás. Nada aqui escreve de volta nos dados nem
dispara ação real (e-mail, desconto, ticket): é sempre uma sugestão que
uma pessoa ainda revisa.
"""

import json
import urllib.error
import urllib.request

# Endereços padrão das ferramentas de IA local mais comuns. Se você usa uma
# porta diferente ou uma ferramenta que não está aqui, use "Endereço
# customizado" no painel -- qualquer servidor que fale a API da OpenAI
# (endpoint /v1/chat/completions) funciona, mesmo sem estar nesta lista.
PORTAS_LOCAIS_CONHECIDAS = [
    ("Ollama", "http://localhost:11434"),
    ("LM Studio", "http://localhost:1234"),
    ("LocalAI", "http://localhost:8080"),
    ("Text Generation WebUI (oobabooga)", "http://localhost:5000"),
    ("Jan", "http://localhost:1337"),
]


def _post_json(url: str, payload: dict, timeout: float = 6, headers: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str, timeout: float = 3) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _listar_modelos_local(base_url: str):
    """
    Tenta descobrir quais modelos esse servidor local tem carregados.
    Primeiro tenta o padrão OpenAI (/v1/models -- funciona em LM Studio,
    Ollama recente, LocalAI, etc.), depois cai pro formato nativo do
    Ollama (/api/tags) se o primeiro não responder. Devolve None se o
    servidor não respondeu em nenhum dos dois formatos (provavelmente não
    é nada disso, ou não está rodando nesse endereço).
    """
    base_url = base_url.rstrip("/")
    try:
        dados = _get_json(f"{base_url}/v1/models")
        return [m.get("id", "?") for m in dados.get("data", [])]
    except Exception:
        pass

    try:
        dados = _get_json(f"{base_url}/api/tags")
        return [m.get("name", "?") for m in dados.get("models", [])]
    except Exception:
        pass

    return None


def detectar_provedores_locais() -> list:
    """Bate em cada endereço conhecido (rápido, timeout curto) e devolve só
    os que responderam de verdade, já com a lista de modelos instalados."""
    encontrados = []
    for nome, base_url in PORTAS_LOCAIS_CONHECIDAS:
        modelos = _listar_modelos_local(base_url)
        if modelos is not None:
            encontrados.append({"nome": nome, "base_url": base_url, "modelos": modelos})
    return encontrados


def testar_endereco_customizado(base_url: str):
    """Pra quando a ferramenta local não está na lista conhecida -- testa
    um endereço digitado na mão. Devolve a lista de modelos (pode ser
    vazia) ou None se não conseguiu falar com esse endereço."""
    return _listar_modelos_local(base_url)


def _prompt_decisao(conta: dict) -> str:
    return f"""Você é um analista de Customer Success. Dado o perfil de risco desta conta
(dados já calculados por um motor determinístico, não invente números novos),
decida UMA ação recomendada, a urgência (Baixa/Média/Alta) e liste os motivos
observados nos dados.

Dados da conta:
{json.dumps(conta, ensure_ascii=False, indent=2, default=str)}

Responda SOMENTE um JSON válido, sem nenhum texto antes ou depois:
{{"acao_recomendada": "...", "urgencia": "...", "motivos": ["..."]}}"""


def _parsear_decisao(texto: str, fonte: str) -> dict:
    texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        decisao = json.loads(texto)
    except json.JSONDecodeError:
        return {"erro": f"Esse modelo não respondeu um JSON válido -- resposta bruta: {texto[:300]}"}
    if not isinstance(decisao, dict) or "acao_recomendada" not in decisao:
        return {"erro": f"JSON veio num formato inesperado (sem 'acao_recomendada'): {texto[:300]}"}
    decisao["fonte"] = fonte
    return decisao


def decidir_acao_local(conta: dict, base_url: str, modelo: str, timeout: float = 45) -> dict:
    """
    Chama um servidor local no formato de chat da OpenAI (Ollama e LM
    Studio, entre outros, já falam esse formato em /v1/chat/completions)
    pra decidir a ação recomendada pra essa conta.
    """
    payload = {
        "model": modelo,
        "messages": [{"role": "user", "content": _prompt_decisao(conta)}],
        "temperature": 0,
        "stream": False,
    }
    try:
        resposta = _post_json(f"{base_url.rstrip('/')}/v1/chat/completions", payload, timeout=timeout)
        texto = resposta["choices"][0]["message"]["content"]
        return _parsear_decisao(texto, fonte=f"IA local ({modelo})")
    except urllib.error.URLError as e:
        return {"erro": f"Não consegui falar com {base_url} -- ele está rodando? ({e})"}
    except Exception as e:
        return {"erro": f"Chamada falhou: {e}"}


def decidir_acao_anthropic(conta: dict, api_key: str, modelo: str = "claude-sonnet-4-5", timeout: float = 45) -> dict:
    """Chama a API da Anthropic de verdade, com a chave que a pessoa colou
    no painel (nunca salva em disco -- fica só na sessão do navegador)."""
    try:
        import anthropic
    except ImportError:
        return {"erro": "Pacote 'anthropic' não instalado (rode: pip install anthropic)."}

    if not api_key or not api_key.strip():
        return {"erro": "Cole sua API key da Anthropic no campo acima primeiro."}

    try:
        client = anthropic.Anthropic(api_key=api_key.strip())
        resposta = client.messages.create(
            model=modelo, max_tokens=512, timeout=timeout,
            messages=[{"role": "user", "content": _prompt_decisao(conta)}],
        )
        texto = resposta.content[0].text
        return _parsear_decisao(texto, fonte=f"IA real ({modelo})")
    except Exception as e:
        return {"erro": f"Chamada à API da Anthropic falhou: {e}"}
