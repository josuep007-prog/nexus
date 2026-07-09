"""
ui/main_window.py
---------------------
Janela principal: reúne as abas do sistema. Conforme os módulos forem
ganhando telas próprias (ex: tela de upload de anexo do Bloco 2, tela de
configuração de CCT por cliente), é só adicionar uma nova aba aqui.
"""

from PyQt5.QtWidgets import QMainWindow, QTabWidget

from ui.tela_solicitacoes import TelaSolicitacoes
from ui.tela_validacao import TelaValidacao
from ui.tela_alertas import TelaAlertas


class MainWindow(QMainWindow):
    def __init__(self, usuario):
        super().__init__()
        self.usuario = usuario
        self.setWindowTitle(f"Automação DP - Departamento Pessoal ({usuario.nome_exibicao})")
        self.resize(1000, 650)

        abas = QTabWidget()
        abas.addTab(TelaSolicitacoes(usuario), "Solicitações")
        # Validações e Alertas são visão interna do escritório: só funcionário.
        if usuario.eh_funcionario:
            abas.addTab(TelaValidacao(), "Validações")
            abas.addTab(TelaAlertas(), "Alertas")

        self.setCentralWidget(abas)
