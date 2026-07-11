"""
scripts/worker_dominio.py
--------------------------
Worker que roda 24h no PC-HOST (a máquina que tem o Domínio instalado e aberto).
Fica olhando a fila de automação e, para cada solicitação que o analista mandou
"processar automaticamente", aciona o RPA no Domínio (integracao/dominio_rpa.py).

IMPORTANTE (pré-requisitos no PC-host, iguais aos do seu DominioAutoFill):
- Windows com o Domínio instalado, LOGADO e ABERTO na tela certa;
- a máquina precisa ficar ligada, logada e DESBLOQUEADA;
- enquanto o RPA digita, ninguém pode mexer no mouse/teclado da máquina;
- processa UMA solicitação por vez (o RPA usa a tela).

Uso:
    python scripts/worker_dominio.py            # intervalo padrão (10s)
    python scripts/worker_dominio.py 30         # verifica a fila a cada 30s

Se o RPA falhar (integração ainda não pronta, popup inesperado, etc.), a
solicitação NÃO é dada como concluída: o erro é registrado e ela cai para
"atendimento manual", pro analista resolver na mão pela web.
"""

import sys
import time
from pathlib import Path

# Garante que a raiz do projeto (dp_automacao/) está no sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

from database.db_manager import inicializar_banco
from database import db_manager
from core.solicitacao import Solicitacao
from core.workflow import NA_FILA_AUTOMACAO
from modules import fila_processamento
from utils import backup as backup_util


def registrar_heartbeat():
    """Marca no banco que o robô está vivo agora (a web usa pra mostrar online/offline)."""
    db_manager.definir_valor_sistema("worker_heartbeat", datetime.now().isoformat(timespec="seconds"))


def rodar_uma_rodada(log=print) -> int:
    """Processa todas as solicitações que estão na fila de automação agora.

    `log` é uma função que recebe uma linha de texto — por padrão imprime no
    console, mas o painel PyQt5 (ui/painel_worker.py) passa a própria função
    pra mostrar o mesmo log ao vivo na tela. Assim a lógica de processamento
    mora só aqui e é compartilhada entre o console e o painel.
    """
    registrar_heartbeat()
    backup_util.fazer_backup_diario()  # só copia 1x por dia; chamadas extras são baratas
    pendentes = sorted(Solicitacao.listar(status=NA_FILA_AUTOMACAO), key=lambda s: s.id)
    for sol in pendentes:
        log(f"processando #{sol.id} ({sol.tipo})...")
        ok, info = fila_processamento.processar_automatico(sol)
        if ok:
            log(f"#{sol.id} OK — {info}")
        else:
            log(f"#{sol.id} FALHOU — {info} (caiu p/ atendimento manual)")
    return len(pendentes)


def main(intervalo_segundos: int = 10):
    inicializar_banco()
    print(f"[worker] Iniciado. Verificando a fila a cada {intervalo_segundos}s. Ctrl+C para parar.", flush=True)
    prefixo = lambda linha: print(f"[worker] {linha}", flush=True)
    while True:
        try:
            processadas = rodar_uma_rodada(log=prefixo)
            if processadas == 0:
                print("[worker] fila vazia.", flush=True)
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001 - o worker não pode morrer por um erro pontual
            print(f"[worker] erro na rodada (segue rodando): {exc}", flush=True)
        time.sleep(intervalo_segundos)


if __name__ == "__main__":
    intervalo = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    try:
        main(intervalo)
    except KeyboardInterrupt:
        print("\n[worker] encerrado pelo usuário.")
