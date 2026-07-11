"""
main.py
--------
Ponto de entrada da versão DESKTOP, que hoje é o PAINEL DO ROBÔ.
Roda na máquina-host (a que tem o Domínio aberto):

    python main.py

Diferente da web (que recebe e valida solicitações em qualquer lugar), este
painel só OPERA a automação: liga/desliga o robô, mostra a fila, o log ao vivo
e os erros. Toda a lógica de negócio continua compartilhada (core/, modules/,
database/) — o painel é só a "casca" de operação.

Não pede login: é um quadro de controle local da máquina do escritório. O
acesso com contas (funcionário/cliente) é papel da web.
"""

import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from database.db_manager import inicializar_banco
from utils.logger import obter_logger
from ui.painel_worker import PainelWorker

log = obter_logger(__name__)


def main():
    log.info("Iniciando o Painel do Robô (desktop)...")
    inicializar_banco()

    app = QApplication(sys.argv)

    folha_estilo = Path(__file__).resolve().parent / "ui" / "estilo.qss"
    if folha_estilo.exists():
        app.setStyleSheet(folha_estilo.read_text(encoding="utf-8"))

    painel = PainelWorker()
    painel.show()

    log.info("Painel do Robô carregado.")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
