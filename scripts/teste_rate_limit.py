"""Dispara várias requisições ao mesmo tempo para ver o rate limiting do Nginx agir.

Uso:  python scripts/teste_rate_limit.py            (padrão: 60 requisições em http://localhost:8080/health)
      python scripts/teste_rate_limit.py 100 http://localhost:8080/registros
"""

import sys
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

TOTAL = int(sys.argv[1]) if len(sys.argv) > 1 else 60
URL = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8080/health"


def requisitar(_):
    try:
        with urllib.request.urlopen(URL, timeout=5) as resp:
            return resp.status, resp.headers.get("X-Instancia")
    except urllib.error.HTTPError as erro:
        return erro.code, None
    except urllib.error.URLError:
        return "sem conexão", None


with ThreadPoolExecutor(max_workers=30) as pool:
    resultados = list(pool.map(requisitar, range(TOTAL)))

status = Counter(codigo for codigo, _ in resultados)
instancias = Counter(inst for _, inst in resultados if inst)

print(f"{TOTAL} requisições para {URL}")
for codigo, qtd in sorted(status.items(), key=lambda item: str(item[0])):
    print(f"  HTTP {codigo}: {qtd}")
if instancias:
    print("Respondidas por:", dict(instancias))
