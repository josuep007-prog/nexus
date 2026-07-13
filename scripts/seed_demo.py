"""
scripts/seed_demo.py
---------------------
Popula o ambiente de DEMONSTRAÇÃO (nuvem) com as MESMAS contas que existem no
PC de desenvolvimento, para que você entre no site com os mesmos logins e
senhas que já usa localmente (ex.: administrador / 123).

Como o banco de dados não viaja pelo git (a pasta data/ é ignorada), as contas
são recriadas aqui a partir de um "retrato" exportado do banco local — cada
conta traz o seu `senha_hash` (a senha embaralhada), então a senha original
continua valendo SEM precisar guardá-la em texto puro.

É idempotente e SEGURO: só semeia se o banco ainda não tiver usuários — nunca
mexe num banco que já tem dados. Disparado no boot quando DEMO_SEED=1 (ver
scripts/rodar_producao.py); também roda à mão:  python scripts/seed_demo.py

⚠️ Estes são hashes de contas de TESTE (senhas fracas, ex.: "123"). Servem para
demonstração num repositório público — NÃO reутilize num ambiente real.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db_manager
from database.db_manager import inicializar_banco, listar_usuarios
from core.solicitacao import Solicitacao
from modules.bloco1 import generico as bloco1_generico

# Retrato das contas do PC (login, senha_hash, tipo, nome, cnpj, email).
# O hash é inserido como está — a senha original de cada conta continua valendo.
CONTAS = [
    {"login": "administrador", "tipo_conta": "administrador", "nome_exibicao": "Administrador",
     "cliente_cnpj": None, "email": None,
     "senha_hash": "scrypt:32768:8:1$I2Sh5xtHKhgDjQR6$607fbe34f0ca3e4d8982f3aa71a9a02624620d5f216acc269289b7c39e603c6be672ef64c1e8691d3b66cc54834dbc66e8ba45411bfe9a971af409ba97352aab"},
    {"login": "func@teste.com", "tipo_conta": "funcionario", "nome_exibicao": "Funcionário Escritório",
     "cliente_cnpj": None, "email": None,
     "senha_hash": "scrypt:32768:8:1$ru59Sjxy2QafL73d$59ffc532a1299ef3c2404fb9e722b25487b6fd15e7fcd83f1d01f3e413ddd4ea572921b7093a90af0afd30e56856a29369488bd675efb817b6985935e0bd5a69"},
    {"login": "cliente", "tipo_conta": "cliente", "nome_exibicao": "Cliente",
     "cliente_cnpj": "00.000.000/0001-00", "email": None,
     "senha_hash": "scrypt:32768:8:1$D6S4m9L7TKG50KRL$9e77d9e637d1ec69f4cecef3feef2ac9d3b9fc344cd4dcd5e3c97b024b774b25bf346300c4bf053b61080d93835e3b74639f010f6b8590d45f27e84f9c7bea1c"},
    {"login": "clienteA@teste.com", "tipo_conta": "cliente", "nome_exibicao": "Empresa A Ltda",
     "cliente_cnpj": "11.111.111/0001-11", "email": None,
     "senha_hash": "scrypt:32768:8:1$Ye6md4k2wFop0uDZ$f2710b9454b20fcfc48b993822d014cb99d9831f66c8f6206ee993393bb03b4f3ce163c2a097c91f4a60ce4523552b6c137bb34a6bec925291315adf6fc12394"},
    {"login": "clienteB@teste.com", "tipo_conta": "cliente", "nome_exibicao": "Empresa B Ltda",
     "cliente_cnpj": "22.222.222/0001-22", "email": None,
     "senha_hash": "scrypt:32768:8:1$LDkEkm1v7MGEJfZj$bd369b5f20112c12ab2a8109b707328e866c649105a66110c46365db1102f36fc2139871f1b029ade5e46681dc28f170d7f33efd0418f96932a926d64c9063e0"},
    {"login": "grupoeco", "tipo_conta": "cliente", "nome_exibicao": "Grupo Econômico Matriz",
     "cliente_cnpj": "11.111.111/0001-11", "email": "grupo@teste.com",
     "senha_hash": "scrypt:32768:8:1$wHoAtTUmkH3eKrNN$01f70147b9b4ba02e6980c267f7fd9ace51a6a9888939ec1d628e37ac51eb655007acaf092133d09d6500f5d19c12af0a3f98707f784fff8a0f9b23cf6bf076d"},
]

# Empresas extras (grupo econômico) por login.
EMPRESAS = [
    {"login": "grupoeco", "cnpj": "11.111.111/0002-92", "nome": "Grupo Econômico Filial"},
]

# Solicitações de exemplo (para a tela inicial não abrir vazia), em nome do
# cliente "Cliente" (CNPJ 00.000.000/0001-00).
EXEMPLOS = [
    ("ferias", {"data_inicio": "2026-08-01", "dias_solicitados": "30", "saldo_dias_direito": "30"}),
    ("declaracao", {"tipo_declaracao": "Vínculo empregatício", "funcionario": "José da Silva"}),
    ("folha_adiantamento", {"competencia": "2026-07", "percentual": "40"}),
]


def semear():
    """Recria as contas do PC se o banco estiver vazio de usuários."""
    inicializar_banco()
    if listar_usuarios():
        return False  # já tem gente: não semeia (nunca sobrescreve dados reais)

    ids_por_login = {}
    for c in CONTAS:
        novo_id = db_manager.criar_usuario(
            c["login"], c["senha_hash"], c["tipo_conta"], c["nome_exibicao"], c["cliente_cnpj"])
        ids_por_login[c["login"]] = novo_id
        if c.get("email"):
            db_manager.atualizar_email_usuario(novo_id, c["email"])

    for e in EMPRESAS:
        uid = ids_por_login.get(e["login"])
        if uid:
            db_manager.adicionar_empresa_usuario(uid, e["cnpj"], e["nome"])

    for tipo, dados in EXEMPLOS:
        try:
            bloco1_generico.criar_solicitacao_generica(
                tipo=tipo, cliente_cnpj="00.000.000/0001-00", cliente_nome="Cliente",
                funcionario_nome=None, dados_formulario=dados, canal_origem="web",
            )
        except Exception:  # noqa: BLE001 - um exemplo que falhe não impede os demais
            pass

    print(f"[seed] ambiente de demonstração populado com {len(CONTAS)} contas do PC.")
    return True


if __name__ == "__main__":
    if not semear():
        print("[seed] banco já tinha usuários — nada foi alterado.")
