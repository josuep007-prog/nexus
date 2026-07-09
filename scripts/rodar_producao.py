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

if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    if os.environ.get("SECRET_KEY") is None:
        print("AVISO: defina a variável SECRET_KEY antes de expor em produção "
              "(sem ela, as sessões caem a cada reinício e a chave é a de desenvolvimento).")
    print(f"Automação DP (produção/waitress) em http://0.0.0.0:{porta}")
    serve(app, host="0.0.0.0", port=porta, threads=8)
