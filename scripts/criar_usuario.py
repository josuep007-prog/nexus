"""
scripts/criar_usuario.py
-------------------------
Ferramenta de linha de comando para o próprio escritório criar contas de
acesso manualmente (cliente, funcionário, gestor ou administrador). Não há
autocadastro no sistema; a criação de contas também pode ser feita pela web
(página /usuarios, por gestor/admin) — este script é útil para criar o
PRIMEIRO administrador, quando ainda não há ninguém que possa fazê-lo pela web.

Uso (a partir da raiz do projeto):
    python scripts/criar_usuario.py

Roda interativo, pedindo os dados pelo terminal. Reaproveita
core.usuario.Usuario.criar (nenhuma lógica de senha é duplicada aqui).
"""

import sys
from pathlib import Path

# Garante que a raiz do projeto (dp_automacao/) está no sys.path,
# já que este arquivo mora em dp_automacao/scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from getpass import getpass

from database.db_manager import inicializar_banco
from core.usuario import Usuario, TIPOS_VALIDOS, TIPO_CLIENTE, ROTULO_PAPEL


def main():
    inicializar_banco()
    print("=== Criar novo usuário — Automação DP ===\n")

    login = input("Login (e-mail ou usuário): ").strip()
    nome_exibicao = input("Nome de exibição (pessoa ou razão social): ").strip()

    print("\nTipos de conta:")
    for t in TIPOS_VALIDOS:
        print(f"  - {t}: {ROTULO_PAPEL[t]}")
    tipo_conta = ""
    while tipo_conta not in TIPOS_VALIDOS:
        tipo_conta = input(f"Tipo de conta ({'/'.join(TIPOS_VALIDOS)}): ").strip().lower()
        if tipo_conta not in TIPOS_VALIDOS:
            print(f"  Valor inválido. Escolha um de: {', '.join(TIPOS_VALIDOS)}.")

    cliente_cnpj = None
    if tipo_conta == TIPO_CLIENTE:
        cliente_cnpj = input("CNPJ do cliente: ").strip()

    senha = getpass("Senha: ")
    senha2 = getpass("Repita a senha: ")
    if senha != senha2:
        print("\nAs senhas não conferem. Nenhuma conta foi criada.")
        sys.exit(1)
    if not senha:
        print("\nSenha vazia. Nenhuma conta foi criada.")
        sys.exit(1)

    try:
        usuario = Usuario.criar(login, senha, tipo_conta, nome_exibicao, cliente_cnpj)
    except ValueError as exc:
        print(f"\nErro: {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001 - login duplicado (UNIQUE) cai aqui
        print(f"\nNão foi possível criar o usuário: {exc}")
        print("(Verifique se o login já não está em uso.)")
        sys.exit(1)

    print(f"\nUsuário '{usuario.login}' ({usuario.tipo_conta}) criado com sucesso. ID={usuario.id}")


if __name__ == "__main__":
    main()
