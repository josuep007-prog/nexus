"""
ui/dialogo_login.py
--------------------
Diálogo de login exibido antes da janela principal do app desktop. Autentica
chamando core.usuario.Usuario.autenticar() — a mesma função usada pela versão
web, sem reimplementar checagem de senha aqui.

Uso (em main.py):
    dialogo = DialogoLogin()
    if dialogo.exec_() != DialogoLogin.Accepted:
        sys.exit(0)
    janela = MainWindow(usuario=dialogo.usuario_autenticado)
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel,
)

from core.usuario import Usuario


class DialogoLogin(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Automação DP - Login")
        self.setMinimumWidth(320)
        self.usuario_autenticado = None
        self._montar_ui()

    def _montar_ui(self):
        layout = QVBoxLayout(self)

        titulo = QLabel("Automação DP")
        titulo.setStyleSheet("font-size: 18px; font-weight: 600; color: #16324A;")
        layout.addWidget(titulo)

        subtitulo = QLabel("Departamento Pessoal")
        subtitulo.setStyleSheet("color: #5B6B76; margin-bottom: 8px;")
        layout.addWidget(subtitulo)

        form = QFormLayout()
        self.campo_login = QLineEdit()
        self.campo_login.setPlaceholderText("e-mail ou usuário")
        self.campo_senha = QLineEdit()
        self.campo_senha.setPlaceholderText("sua senha")
        self.campo_senha.setEchoMode(QLineEdit.Password)
        form.addRow("Login:", self.campo_login)
        form.addRow("Senha:", self.campo_senha)
        layout.addLayout(form)

        self.rotulo_erro = QLabel("")
        self.rotulo_erro.setStyleSheet("color: #B3402E;")
        self.rotulo_erro.setVisible(False)
        layout.addWidget(self.rotulo_erro)

        btn_entrar = QPushButton("Entrar")
        btn_entrar.clicked.connect(self._tentar_login)
        btn_entrar.setDefault(True)
        layout.addWidget(btn_entrar)

        # Enter em qualquer campo tenta logar.
        self.campo_login.returnPressed.connect(self._tentar_login)
        self.campo_senha.returnPressed.connect(self._tentar_login)

    def _tentar_login(self):
        login = self.campo_login.text().strip()
        senha = self.campo_senha.text()
        usuario = Usuario.autenticar(login, senha)
        if usuario is None:
            self.rotulo_erro.setText("Login ou senha inválidos.")
            self.rotulo_erro.setVisible(True)
            return
        self.usuario_autenticado = usuario
        self.accept()
