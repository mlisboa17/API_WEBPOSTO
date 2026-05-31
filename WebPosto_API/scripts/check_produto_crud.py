"""Verifica permissões da chave WebPosto nos endpoints de produto (sem alterar dados)."""
import json
import urllib.error
import urllib.request
from urllib.parse import urlencode

key = None
base = "https://web.qualityautomacao.com.br"
for line in open(".env", encoding="utf-8"):
    line = line.strip()
    if line.startswith("WEBPOSTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
    elif line.startswith("WEBPOSTO_BASE_URL="):
        base = line.split("=", 1)[1].strip().rstrip("/")
        if base.startswith("http://"):
            base = "https://" + base[len("http://") :]


def probe(method, path, params=None, body=None):
    url = base + path
    q = dict(params or {})
    q["CHAVE"] = key
    url += "?" + urlencode(q)
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode("utf-8", errors="replace")[:500]
            return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")[:500]
        return e.code, raw
    except Exception as e:
        return "ERR", str(e)


def interpret(status):
    if status == 401:
        return "SEM permissão"
    if status == 403:
        return "Proibido"
    if status in (400, 422):
        return "Permitido (payload inválido — chave aceita escrita)"
    if status in (200, 201, 204):
        return "Permitido (OK)"
    if status == 405:
        return "Método não aceito"
    if status == "ERR":
        return "Erro de rede"
    return "Outro — ver corpo"


tests = [
    ("GET", "/INTEGRACAO/PRODUTO", {"pagina": 0, "tamanhoPagina": 3}, None, "Listar (Read)"),
    ("GET", "/INTEGRACAO/PRODUTO", {"pagina": 0, "tamanhoPagina": 3}, None, "Lista de itens (PRODUTO)"),
    ("GET", "/INTEGRACAO/RETORNO_CADASTRO_PRODUTO", {"pagina": 0, "tamanhoPagina": 3}, None, "Retorno cadastro"),
    ("POST", "/INTEGRACAO/PRODUTO", None, {}, "Criar (POST)"),
    ("PUT", "/INTEGRACAO/ALTERAR_PRODUTO/1", None, {}, "Atualizar (PUT)"),
    ("POST", "/INTEGRACAO/REAJUSTAR_PRODUTO", None, {}, "Reajustar preço"),
    ("POST", "/INTEGRACAO/TROCA_PRECO_PRODUTO", None, {}, "Trocar preço"),
    ("POST", "/INTEGRACAO/AJUSTE_ESTOQUE_PRODUTO", None, {}, "Ajuste estoque"),
]

print("Base:", base)
print("Chave:", (key[:8] + "..." + key[-4:]) if key else "NAO ENCONTRADA")
print()
print(f"{'Operação':<28} {'HTTP':<6} Interpretação")
print("-" * 72)
for method, path, params, body, label in tests:
    status, raw = probe(method, path, params, body)
    print(f"{label:<28} {str(status):<6} {interpret(status)}")
    if status == 200 and method == "GET" and "/PRODUTO" in path:
        try:
            data = json.loads(raw) if raw.startswith("{") or raw.startswith("[") else {}
            n = len(data.get("resultados", data if isinstance(data, list) else []))
            print(f"  -> {n} registro(s) na amostra")
        except json.JSONDecodeError:
            pass
    elif status not in (200, 401, 403) and len(raw) < 200:
        print(f"  -> {raw.replace(chr(10), ' ')[:120]}")
