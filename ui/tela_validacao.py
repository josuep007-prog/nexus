"""
ui/tela_validacao.py
------------------------
Aba "Validações": fila de solicitações aguardando aprovação humana (a
validação obrigatória do Bloco 1, ou qualquer uma das 3 aprovações do Bloco 2).
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QTextEdit, QLabel, QMessageBox,
)

from core.solicitacao import Solicitacao
from core.workflow import StatusBloco1, StatusBloco2
from modules.bloco1 import recebimento as bloco1_recebimento

STATUS_AGUARDANDO_ACAO_HUMANA = [
    StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA,
    StatusBloco1.AGUARDANDO_APROVACAO_DISTRIBUICAO,
    StatusBloco2.AGUARDANDO_APROVACAO_1,
    StatusBloco2.AGUARDANDO_APROVACAO_2,
    StatusBloco2.AGUARDANDO_APROVACAO_3,
]


class TelaValidacao(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._montar_ui()
        self.atualizar_fila()

    def _montar_ui(self):
        layout = QHBoxLayout(self)

        col_esquerda = QVBoxLayout()
        col_esquerda.addWidget(QLabel("Fila aguardando validação humana:"))
        self.lista = QListWidget()
        self.lista.itemSelectionChanged.connect(self._mostrar_detalhes)
        col_esquerda.addWidget(self.lista)

        btn_atualizar = QPushButton("Atualizar fila")
        btn_atualizar.clicked.connect(self.atualizar_fila)
        col_esquerda.addWidget(btn_atualizar)

        layout.addLayout(col_esquerda, 1)

        col_direita = QVBoxLayout()
        col_direita.addWidget(QLabel("Detalhes da solicitação selecionada:"))
        self.detalhes = QTextEdit()
        self.detalhes.setReadOnly(True)
        col_direita.addWidget(self.detalhes)

        botoes = QHBoxLayout()
        btn_aprovar = QPushButton("✅ Aprovar")
        btn_aprovar.clicked.connect(lambda: self._decidir(True))
        btn_reprovar = QPushButton("❌ Reprovar")
        btn_reprovar.clicked.connect(lambda: self._decidir(False))
        botoes.addWidget(btn_aprovar)
        botoes.addWidget(btn_reprovar)
        col_direita.addLayout(botoes)

        layout.addLayout(col_direita, 2)

    def atualizar_fila(self):
        self.lista.clear()
        for status in STATUS_AGUARDANDO_ACAO_HUMANA:
            for sol in Solicitacao.listar(status=status):
                item = QListWidgetItem(f"#{sol.id} - {sol.tipo} ({sol.status})")
                item.setData(1000, sol.id)
                self.lista.addItem(item)
        self.detalhes.clear()

    def _solicitacao_selecionada(self):
        item = self.lista.currentItem()
        if item is None:
            return None
        return Solicitacao.carregar(item.data(1000))

    def _mostrar_detalhes(self):
        sol = self._solicitacao_selecionada()
        if sol is None:
            self.detalhes.clear()
            return

        texto = [
            f"ID: {sol.id}",
            f"Bloco: {sol.bloco}",
            f"Tipo: {sol.tipo}",
            f"Status: {sol.status}",
            f"Cliente: {sol._row.get('cliente_nome')}",
            "",
            "Dados:",
        ]
        for chave, valor in sol.dados.items():
            texto.append(f"  - {chave}: {valor}")

        self.detalhes.setPlainText("\n".join(texto))

    def _decidir(self, aprovado: bool):
        sol = self._solicitacao_selecionada()
        if sol is None:
            QMessageBox.warning(self, "Nada selecionado", "Selecione uma solicitação na lista.")
            return

        # Bloco 1 - validação obrigatória
        if sol.status == StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA:
            bloco1_recebimento.validar_humanamente(sol, aprovado, aprovado_por="analista_ui")
        else:
            # Para as demais etapas (aprovações do Bloco 2, distribuição do Bloco 1),
            # o fluxo completo de "avançar automaticamente pro próximo módulo" ainda
            # depende das integrações (Domínio/Onvio) estarem implementadas.
            sol.validar(etapa=sol.status, aprovado=aprovado, aprovado_por="analista_ui")
            if aprovado:
                QMessageBox.information(
                    self, "Aprovado",
                    "Validação registrada. O próximo passo do fluxo depende de módulos "
                    "de integração ainda não implementados (ver integracao/)."
                )

        self.atualizar_fila()
