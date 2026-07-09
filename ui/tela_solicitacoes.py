"""
ui/tela_solicitacoes.py
---------------------------
Aba "Solicitações": lista tudo que está no banco, com filtro por status/bloco,
e um botão para criar uma solicitação de teste (útil pra você testar o fluxo
inteiro sem precisar montar uma tela de cadastro completa ainda).
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLabel, QMessageBox,
)

from core.solicitacao import Solicitacao
from modules.bloco1 import recebimento as bloco1_recebimento
from config import BLOCO_1


class TelaSolicitacoes(QWidget):
    def __init__(self, usuario, parent=None):
        super().__init__(parent)
        self.usuario = usuario
        self._montar_ui()
        self.atualizar_lista()

    def _montar_ui(self):
        layout = QVBoxLayout(self)

        barra = QHBoxLayout()
        self.filtro_status = QComboBox()
        self.filtro_status.addItem("Todos os status", None)
        barra.addWidget(QLabel("Filtrar por status:"))
        barra.addWidget(self.filtro_status)

        btn_atualizar = QPushButton("Atualizar lista")
        btn_atualizar.clicked.connect(self.atualizar_lista)
        barra.addWidget(btn_atualizar)

        # Botão de teste é ferramenta interna (CNPJ fixo de exemplo): só funcionário.
        if self.usuario.eh_funcionario:
            btn_nova_teste = QPushButton("+ Nova solicitação de teste (férias)")
            btn_nova_teste.clicked.connect(self._criar_solicitacao_teste)
            barra.addWidget(btn_nova_teste)

        barra.addStretch()
        layout.addLayout(barra)

        self.tabela = QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Bloco", "Tipo", "Cliente", "Status", "Atualizado em"]
        )
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)

        self.filtro_status.currentIndexChanged.connect(self.atualizar_lista)

    def atualizar_lista(self):
        status_selecionado = self.filtro_status.currentData()
        # Cliente só enxerga as próprias solicitações; funcionário vê todas.
        filtro_cnpj = None if self.usuario.eh_funcionario else self.usuario.cliente_cnpj
        solicitacoes = Solicitacao.listar(status=status_selecionado, cliente_cnpj=filtro_cnpj)

        self.tabela.setRowCount(len(solicitacoes))
        for linha, sol in enumerate(solicitacoes):
            self.tabela.setItem(linha, 0, QTableWidgetItem(str(sol.id)))
            self.tabela.setItem(linha, 1, QTableWidgetItem(sol.bloco))
            self.tabela.setItem(linha, 2, QTableWidgetItem(sol.tipo))
            self.tabela.setItem(linha, 3, QTableWidgetItem(sol._row.get("cliente_nome") or "-"))
            self.tabela.setItem(linha, 4, QTableWidgetItem(sol.status))
            self.tabela.setItem(linha, 5, QTableWidgetItem(sol._row.get("atualizado_em")))

        self.tabela.resizeColumnsToContents()

    def _criar_solicitacao_teste(self):
        """
        Cria uma solicitação de férias de exemplo e já roda a triagem automática,
        só pra você ver o fluxo (recebida -> triagem -> aguardando validação/ajuste)
        funcionando ponta a ponta.
        """
        sol = bloco1_recebimento.unificar_solicitacao(
            tipo="ferias",
            canal_origem="whatsapp",
            cliente_cnpj="00.000.000/0001-00",
            cliente_nome="Cliente Exemplo Ltda",
            funcionario_nome="Funcionário Exemplo",
            dados={"dias_solicitados": 30, "saldo_dias_direito": 30},
        )
        ok, erros = bloco1_recebimento.rodar_triagem(sol)

        self.atualizar_lista()

        if ok:
            QMessageBox.information(self, "Solicitação criada",
                                     f"Solicitação #{sol.id} criada e aprovada na triagem automática.\n"
                                     f"Status atual: {sol.status}")
        else:
            QMessageBox.warning(self, "Solicitação criada com pendências",
                                 f"Solicitação #{sol.id} criada, mas a triagem encontrou pendências:\n\n"
                                 + "\n".join(erros))
