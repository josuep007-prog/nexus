"""
main.py
--------
Ponto de entrada do sistema. Roda:
    python main.py

Isso inicializa o banco SQLite (cria as tabelas se não existirem) e abre a
janela principal do PyQt5.
"""

import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from database.db_manager import inicializar_banco
from utils.logger import obter_logger
from ui.main_window import MainWindow
from ui.dialogo_login import DialogoLogin

log = obter_logger(__name__)


def main():
    log.info("Iniciando sistema de Automação DP...")
    inicializar_banco()

    app = QApplication(sys.argv)

    folha_estilo = Path(__file__).resolve().parent / "ui" / "estilo.qss"
    if folha_estilo.exists():
        app.setStyleSheet(folha_estilo.read_text(encoding="utf-8"))

    # Exige login antes de abrir a janela principal. Cancelar encerra o app.
    dialogo = DialogoLogin()
    if dialogo.exec_() != DialogoLogin.Accepted:
        log.info("Login cancelado; encerrando.")
        sys.exit(0)

    janela = MainWindow(usuario=dialogo.usuario_autenticado)
    janela.show()

    log.info("Interface carregada para %s.", dialogo.usuario_autenticado.login)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
