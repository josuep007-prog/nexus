"""
core/usuario.py
----------------
Camada de autenticação: representa uma conta de acesso (funcionário do
escritório ou cliente) como objeto Python, no mesmo estilo de
core/solicitacao.py (classe fina em cima de database/db_manager.py).

A autenticação (usada pela web em web/app.py) chama `Usuario.autenticar(login,
senha)` — a lógica de senha mora só aqui, nunca é reimplementada em cada
interface. (O desktop hoje é o Painel do Robô e não faz login: é um quadro de
operação local da máquina-host; contas são papel da web.)

Dois tipos de conta:
- 'funcionario' : pessoal do escritório, acesso total (todas as solicitações,
                  validações e alertas). Não tem cliente_cnpj.
- 'cliente'     : empresa cliente, só vê/cria as próprias solicitações
                  (filtradas por cliente_cnpj). cliente_cnpj é obrigatório.
"""

from werkzeug.security import generate_password_hash, check_password_hash

from database import db_manager


TIPO_FUNCIONARIO = "funcionario"
TIPO_CLIENTE = "cliente"


class Usuario:
    def __init__(self, row: dict):
        self._row = row

    # -- construtores -------------------------------------------------
    @classmethod
    def autenticar(cls, login, senha):
        """Retorna o Usuario se login+senha conferem e a conta está ativa; senão None."""
        row = db_manager.buscar_usuario_por_login(login)
        if row is None or not row["ativo"]:
            return None
        if not check_password_hash(row["senha_hash"], senha):
            return None
        return cls(row)

    @classmethod
    def carregar(cls, usuario_id):
        row = db_manager.buscar_usuario_por_id(usuario_id)
        if row is None:
            raise ValueError(f"Usuário {usuario_id} não encontrado")
        return cls(row)

    @classmethod
    def criar(cls, login, senha, tipo_conta, nome_exibicao, cliente_cnpj=None):
        """Cria uma nova conta. É a única porta de criação de usuário do sistema.

        Usado pelo script de provisionamento (scripts/criar_usuario.py), já que
        não há autocadastro — as contas são criadas manualmente pelo escritório.
        """
        if tipo_conta not in (TIPO_FUNCIONARIO, TIPO_CLIENTE):
            raise ValueError(f"Tipo de conta inválido: '{tipo_conta}'. Use '{TIPO_FUNCIONARIO}' ou '{TIPO_CLIENTE}'.")
        if tipo_conta == TIPO_CLIENTE and not cliente_cnpj:
            raise ValueError("Contas do tipo 'cliente' exigem cliente_cnpj.")
        if tipo_conta == TIPO_FUNCIONARIO and cliente_cnpj:
            raise ValueError("Contas do tipo 'funcionario' não devem ter cliente_cnpj.")
        senha_hash = generate_password_hash(senha)
        novo_id = db_manager.criar_usuario(login, senha_hash, tipo_conta, nome_exibicao, cliente_cnpj)
        return cls.carregar(novo_id)

    # -- propriedades ---------------------------------------------------
    @property
    def id(self):
        return self._row["id"]

    @property
    def login(self):
        return self._row["login"]

    @property
    def tipo_conta(self):
        return self._row["tipo_conta"]

    @property
    def nome_exibicao(self):
        return self._row["nome_exibicao"]

    @property
    def cliente_cnpj(self):
        return self._row.get("cliente_cnpj")

    @property
    def email(self):
        return self._row.get("email")

    @property
    def eh_funcionario(self):
        return self.tipo_conta == TIPO_FUNCIONARIO

    @property
    def eh_cliente(self):
        return self.tipo_conta == TIPO_CLIENTE

    # -- várias empresas por conta cliente (grupo econômico / filiais) ----
    def empresas_extras(self):
        """Empresas ADICIONAIS vinculadas à conta (além do CNPJ principal)."""
        return db_manager.listar_empresas_usuario(self.id)

    @property
    def cnpjs(self):
        """Todos os CNPJs que esta conta cliente pode ver/usar (principal + extras)."""
        if not self.eh_cliente:
            return []
        extras = [e["cnpj"] for e in self.empresas_extras()]
        return [self.cliente_cnpj] + [c for c in extras if c != self.cliente_cnpj]

    def empresas(self):
        """Lista (cnpj, nome) de todas as empresas da conta — p/ seletor no formulário."""
        principais = [{"cnpj": self.cliente_cnpj, "nome": self.nome_exibicao}]
        return principais + [{"cnpj": e["cnpj"], "nome": e["nome"] or e["cnpj"]}
                             for e in self.empresas_extras() if e["cnpj"] != self.cliente_cnpj]

    # -- senha -------------------------------------------------------------
    def verificar_senha(self, senha):
        return check_password_hash(self._row["senha_hash"], senha)

    def alterar_senha(self, senha_atual, senha_nova):
        """Troca a própria senha (exige a senha atual correta)."""
        if not self.verificar_senha(senha_atual):
            raise ValueError("Senha atual incorreta.")
        if len(senha_nova) < 4:
            raise ValueError("A nova senha precisa ter pelo menos 4 caracteres.")
        db_manager.atualizar_senha_usuario(self.id, generate_password_hash(senha_nova))

    def redefinir_senha(self, senha_nova):
        """Redefine a senha SEM pedir a atual — só o escritório usa (reset)."""
        if len(senha_nova) < 4:
            raise ValueError("A nova senha precisa ter pelo menos 4 caracteres.")
        db_manager.atualizar_senha_usuario(self.id, generate_password_hash(senha_nova))

    def __repr__(self):
        return f"<Usuario #{self.id} {self.login} ({self.tipo_conta})>"
