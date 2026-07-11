"""
ui/painel_worker.py
--------------------
O PAINEL DO ROBÔ — a versão desktop do sistema, com propósito totalmente
diferente da web. Enquanto a web recebe/valida solicitações (roda em qualquer
lugar), este painel roda NA MÁQUINA-HOST (a que tem o Domínio aberto) e serve
só para OPERAR e MONITORAR a automação:

- liga/desliga o robô que processa a fila de automação no Domínio;
- mostra a fila esperando, o log ao vivo do que está sendo feito e os erros;
- lembra os pré-requisitos (Domínio aberto, tela desbloqueada).

Não tem login nem telas de cadastro — isso é papel da web. Aqui é um "quadro
de controle" da máquina. O processamento em si NÃO é reimplementado: usa o
mesmo scripts/worker_dominio.py que o worker de console usa (uma lógica só).
"""

from datetime import datetime

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit, QSpinBox, QFrame, QHeaderView,
)

from core.solicitacao import Solicitacao
from core.workflow import NA_FILA_AUTOMACAO, EM_ATENDIMENTO_MANUAL, AGUARDANDO_ENTREGA
from database import db_manager
from scripts import worker_dominio


class RoboThread(QThread):
    """Roda o loop do robô numa thread separada, pra não travar a janela.

    Emite sinais em vez de mexer na interface direto (regra do Qt: só a thread
    principal pode tocar em widgets). O painel escuta esses sinais.
    """
    log = pyqtSignal(str)              # uma linha nova pro log ao vivo
    rodada_terminou = pyqtSignal(int)  # quantas solicitações foram processadas na rodada
    parou = pyqtSignal()

    def __init__(self, intervalo_segundos=10):
        super().__init__()
        self.intervalo = intervalo_segundos
        self._rodando = True

    def run(self):
        self.log.emit("Robô iniciado. Vigiando a fila de automação.")
        while self._rodando:
            try:
                processadas = worker_dominio.rodar_uma_rodada(log=self.log.emit)
                if processadas == 0:
                    worker_dominio.registrar_heartbeat()
            except Exception as exc:  # noqa: BLE001 - o robô não morre por um erro pontual
                self.log.emit(f"ERRO na rodada (segue rodando): {exc}")
            # Espera o intervalo, mas em passos curtos pra responder ao "Parar" na hora.
            for _ in range(self.intervalo * 2):
                if not self._rodando:
                    break
                self.msleep(500)
        self.parou.emit()

    def parar(self):
        self._rodando = False


class PainelWorker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread_robo = None
        self.setWindowTitle("Automação DP — Robô do Domínio (PC-host)")
        self.resize(880, 680)
        self._montar_ui()
        self.atualizar_paineis()

    # -- construção da tela ------------------------------------------------
    def _montar_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        raiz = QVBoxLayout(central)
        raiz.setContentsMargins(26, 24, 26, 20)
        raiz.setSpacing(14)

        # Cabeçalho: título à esquerda, pílula de status à direita
        topo = QHBoxLayout()
        bloco_titulo = QVBoxLayout()
        bloco_titulo.setSpacing(2)
        titulo = QLabel("ROBÔ DO DOMÍNIO")
        titulo.setObjectName("titulo")
        sub = QLabel("Painel de operação da automação  ·  esta máquina (PC-host)")
        sub.setObjectName("subtitulo")
        bloco_titulo.addWidget(titulo)
        bloco_titulo.addWidget(sub)
        topo.addLayout(bloco_titulo)
        topo.addStretch()

        self.pill_status = QLabel("●  PARADO")
        self.pill_status.setObjectName("statusPill")
        self.pill_status.setProperty("estado", "off")
        topo.addWidget(self.pill_status, alignment=Qt.AlignTop)
        raiz.addLayout(topo)

        # Barra de controles
        barra = QFrame()
        barra.setObjectName("cartao")
        lin = QHBoxLayout(barra)
        lin.setContentsMargins(18, 14, 18, 14)
        lin.setSpacing(10)

        self.btn_iniciar = QPushButton("▶   Ligar robô")
        self.btn_iniciar.setObjectName("btnIniciar")
        self.btn_iniciar.setMinimumWidth(150)
        self.btn_iniciar.clicked.connect(self.iniciar_robo)
        self.btn_parar = QPushButton("■   Parar")
        self.btn_parar.setObjectName("btnParar")
        self.btn_parar.setMinimumWidth(110)
        self.btn_parar.clicked.connect(self.parar_robo)
        self.btn_parar.setEnabled(False)
        lin.addWidget(self.btn_iniciar)
        lin.addWidget(self.btn_parar)
        lin.addStretch()

        rotulo_intervalo = QLabel("Verificar a fila a cada")
        rotulo_intervalo.setObjectName("subtitulo")
        lin.addWidget(rotulo_intervalo)
        self.intervalo = QSpinBox()
        self.intervalo.setRange(3, 300)
        self.intervalo.setValue(10)
        self.intervalo.setSuffix(" s")
        lin.addWidget(self.intervalo)
        raiz.addWidget(barra)

        # Aviso de pré-requisitos (o robô controla a tela real do Domínio)
        aviso = QLabel(
            "⚠  Enquanto o robô estiver ligado, mantenha o Domínio ABERTO e logado, "
            "a máquina DESBLOQUEADA e não mexa no mouse/teclado — ele digita na tela real."
        )
        aviso.setObjectName("aviso")
        aviso.setWordWrap(True)
        raiz.addWidget(aviso)

        # Contadores rápidos (fila / entrega / manual), com filete de cor
        self.linha_contadores = QHBoxLayout()
        self.linha_contadores.setSpacing(12)
        self.card_fila = self._card_contador("Na fila de automação", "0", accent="azul")
        self.card_entrega = self._card_contador("Processadas (aguard. entrega)", "0", accent="verde")
        self.card_manual = self._card_contador("Em atendimento manual", "0", accent="ambar")
        for c in (self.card_fila, self.card_entrega, self.card_manual):
            self.linha_contadores.addWidget(c)
        raiz.addLayout(self.linha_contadores)

        # Fila detalhada
        raiz.addWidget(self._rotulo_secao("FILA DE AUTOMAÇÃO — ESPERANDO O ROBÔ"))
        self.tabela_fila = QTableWidget(0, 3)
        self.tabela_fila.setHorizontalHeaderLabels(["Nº", "Tipo", "Cliente"])
        self.tabela_fila.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela_fila.setAlternatingRowColors(True)
        self.tabela_fila.setShowGrid(False)
        self.tabela_fila.setFocusPolicy(Qt.NoFocus)
        self.tabela_fila.verticalHeader().setVisible(False)
        self.tabela_fila.verticalHeader().setDefaultSectionSize(34)
        self.tabela_fila.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela_fila.setMaximumHeight(180)
        raiz.addWidget(self.tabela_fila)

        # Log ao vivo
        raiz.addWidget(self._rotulo_secao("LOG AO VIVO"))
        self.log = QTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        raiz.addWidget(self.log, stretch=1)

        # Rodapé com atualização manual
        rodape = QHBoxLayout()
        self.rotulo_atualizado = QLabel("")
        self.rotulo_atualizado.setObjectName("subtitulo")
        rodape.addWidget(self.rotulo_atualizado)
        rodape.addStretch()
        btn_atualizar = QPushButton("Atualizar")
        btn_atualizar.setObjectName("btnFantasma")
        btn_atualizar.clicked.connect(self.atualizar_paineis)
        rodape.addWidget(btn_atualizar)
        raiz.addLayout(rodape)

    def _card_contador(self, rotulo, valor, accent="azul"):
        card = QFrame()
        card.setObjectName("cartao")
        card.setProperty("accent", accent)  # filete de cor via QSS
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(2)
        lbl_valor = QLabel(valor)
        lbl_valor.setObjectName("contadorValor")
        lbl_rot = QLabel(rotulo)
        lbl_rot.setObjectName("contadorRotulo")
        lbl_rot.setWordWrap(True)
        v.addWidget(lbl_valor)
        v.addWidget(lbl_rot)
        card.valor = lbl_valor  # atalho pra atualizar depois
        return card

    def _rotulo_secao(self, texto):
        lbl = QLabel(texto)
        lbl.setObjectName("secao")
        return lbl

    # -- ações -------------------------------------------------------------
    def iniciar_robo(self):
        if self.thread_robo and self.thread_robo.isRunning():
            return
        self.thread_robo = RoboThread(self.intervalo.value())
        self.thread_robo.log.connect(self._anexar_log)
        self.thread_robo.rodada_terminou.connect(lambda _n: self.atualizar_paineis())
        self.thread_robo.parou.connect(self._ao_parar)
        self.thread_robo.start()
        self._marcar_rodando(True)

    def parar_robo(self):
        if self.thread_robo:
            self._anexar_log("Parando o robô… (termina a solicitação atual antes de encerrar)")
            self.thread_robo.parar()
            self.btn_parar.setEnabled(False)

    def _ao_parar(self):
        self._marcar_rodando(False)
        self._anexar_log("Robô parado.")

    def _marcar_rodando(self, rodando):
        self.pill_status.setText("●  RODANDO" if rodando else "●  PARADO")
        self.pill_status.setProperty("estado", "on" if rodando else "off")
        # força reaplicar o QSS (as cores da pílula mudam pelo 'estado')
        self.pill_status.style().unpolish(self.pill_status)
        self.pill_status.style().polish(self.pill_status)
        self.btn_iniciar.setEnabled(not rodando)
        self.btn_parar.setEnabled(rodando)
        self.intervalo.setEnabled(not rodando)

    def _anexar_log(self, linha):
        agora = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{agora}] {linha}")
        # se o robô processou algo, os contadores mudaram
        if "OK" in linha or "FALHOU" in linha:
            self.atualizar_paineis()

    def atualizar_paineis(self):
        fila = sorted(Solicitacao.listar(status=NA_FILA_AUTOMACAO), key=lambda s: s.id)
        entrega = Solicitacao.listar(status=AGUARDANDO_ENTREGA)
        manual = Solicitacao.listar(status=EM_ATENDIMENTO_MANUAL)

        self.card_fila.valor.setText(str(len(fila)))
        self.card_entrega.valor.setText(str(len(entrega)))
        self.card_manual.valor.setText(str(len(manual)))

        self.tabela_fila.setRowCount(len(fila))
        for i, sol in enumerate(fila):
            self.tabela_fila.setItem(i, 0, QTableWidgetItem(f"#{sol.id}"))
            self.tabela_fila.setItem(i, 1, QTableWidgetItem(sol.tipo))
            self.tabela_fila.setItem(i, 2, QTableWidgetItem(sol._row.get("cliente_nome") or "—"))

        self.rotulo_atualizado.setText("Atualizado às " + datetime.now().strftime("%H:%M:%S"))

    # -- ciclo de vida -----------------------------------------------------
    def closeEvent(self, evento):
        """Ao fechar a janela, para o robô com elegância (não deixa thread solta)."""
        if self.thread_robo and self.thread_robo.isRunning():
            self.thread_robo.parar()
            self.thread_robo.wait(3000)
        super().closeEvent(evento)
