"""
scripts/rodar_producao.py
--------------------------
Sobe a versão web com o WAITRESS (servidor WSGI de produção para Windows),
no lugar do servidor de desenvolvimento do Flask (app.run).

Uso:
    pip install waitress
    set SECRET_KEY=uma-chave-longa-e-aleatoria
    python scripts/rodar_producao.py            # porta 5000
    python scripts/rodar_producao.py 8080       # outra porta

A porta pode vir também da variável de ambiente PORT (é assim que hospedagens
como Render/Railway informam a porta) — o argumento da linha de comando tem
prioridade, senão usa $PORT, senão 5000.

Se DEMO_SEED estiver definida (=1), popula contas e dados de exemplo no 1º boot
(ideal pra um ambiente de DEMONSTRAÇÃO na nuvem) — ver scripts/seed_demo.py.

Diferenças pro modo dev (python web/app.py):
- aguenta várias requisições simultâneas (threads) sem travar;
- sem debug/reloader (nada de stack trace exposto pro usuário);
- é o jeito certo de deixar rodando 24h no PC-host junto com o worker.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from waitress import serve
except ImportError:
    print("Instale primeiro:  pip install waitress")
    sys.exit(1)

from web.app import app

# Ambiente de DEMONSTRAÇÃO: popula contas/dados de exemplo no 1º boot.
if os.environ.get("DEMO_SEED") == "1":
    try:
        from scripts.seed_demo import semear
        semear()
    except Exception as exc:  # noqa: BLE001 - seed nunca impede o servidor de subir
        print(f"[seed] aviso: não foi possível semear a demo: {exc}")

if __name__ == "__main__":
    # Prioridade da porta: argumento > $PORT (hospedagens) > 5000
    if len(sys.argv) > 1:
        porta = int(sys.argv[1])
    else:
        porta = int(os.environ.get("PORT", "5000"))
    if os.environ.get("SECRET_KEY") is None:
        print("AVISO: defina a variável SECRET_KEY antes de expor em produção "
              "(sem ela, as sessões caem a cada reinício e a chave é a de desenvolvimento).")
    print(f"Automação DP (produção/waitress) em http://0.0.0.0:{porta}")
    serve(app, host="0.0.0.0", port=porta, threads=8)
