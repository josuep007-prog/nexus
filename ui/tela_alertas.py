"""
ui/tela_alertas.py
----------------------
Aba "Alertas": mostra os alertas pendentes (vencimento de férias, fim de
experiência, prazos etc.) gerados por modules/rotinas/alertas.py.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox,
)

from modules.rotinas import alertas


class TelaAlertas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._montar_ui()
        self.atualizar_lista()

    def _montar_ui(self):
        layout = QVBoxLayout(self)

        barra = QHBoxLayout()
        btn_atualizar = QPushButton("Atualizar")
        btn_atualizar.clicked.connect(self.atualizar_lista)
        barra.addWidget(btn_atualizar)

        btn_resolver = QPushButton("Marcar selecionado como resolvido")
        btn_resolver.clicked.connect(self._marcar_resolvido)
        barra.addWidget(btn_resolver)

        barra.addStretch()
        layout.addLayout(barra)

        self.tabela = QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels(["ID", "Tipo", "Descrição", "Vencimento"])
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)

    def atualizar_lista(self):
        pendentes = alertas.listar_alertas_pendentes()
        self.tabela.setRowCount(len(pendentes))
        for linha, alerta in enumerate(pendentes):
            self.tabela.setItem(linha, 0, QTableWidgetItem(str(alerta["id"])))
            self.tabela.setItem(linha, 1, QTableWidgetItem(alerta["tipo"]))
            self.tabela.setItem(linha, 2, QTableWidgetItem(alerta["descricao"]))
            self.tabela.setItem(linha, 3, QTableWidgetItem(alerta.get("data_vencimento") or "-"))
        self.tabela.resizeColumnsToContents()

    def _marcar_resolvido(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            QMessageBox.warning(self, "Nada selecionado", "Selecione um alerta na lista.")
            return
        alerta_id = int(self.tabela.item(linha, 0).text())
        alertas.marcar_alerta_resolvido(alerta_id)
        self.atualizar_lista()
