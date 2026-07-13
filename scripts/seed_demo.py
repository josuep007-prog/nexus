"""
scripts/seed_demo.py
---------------------
Popula um ambiente de DEMONSTRAÇÃO com contas e solicitações de exemplo, para
que quem abrir o link já veja o sistema "com vida" (não uma tela vazia).

É idempotente e SEGURO: só semeia se o banco ainda não tiver usuários — nunca
mexe num banco que já tem dados. Disparado no boot quando a variável de
ambiente DEMO_SEED=1 (ver scripts/rodar_producao.py); também pode rodar à mão:

    python scripts/seed_demo.py

Contas criadas (senha de todas: demo123):
    admin      → Administrador master
    gestor     → Gestor do departamento
    analista   → Funcionário do escritório
    cliente    → Cliente (empresa) — CNPJ 12.345.678/0001-90
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db_manager import inicializar_banco, listar_usuarios
from core.usuario import Usuario, TIPO_ADMIN, TIPO_GESTOR, TIPO_FUNCIONARIO, TIPO_CLIENTE
from core.solicitacao import Solicitacao
from modules.bloco1 import generico as bloco1_generico

SENHA_DEMO = "demo123"
CNPJ_DEMO = "12.345.678/0001-90"
NOME_CLIENTE_DEMO = "Comércio Modelo Ltda"

CONTAS = [
    ("admin", TIPO_ADMIN, "Ana Administradora", None),
    ("gestor", TIPO_GESTOR, "Gustavo Gestor", None),
    ("analista", TIPO_FUNCIONARIO, "Fernanda Analista", None),
    ("cliente", TIPO_CLIENTE, NOME_CLIENTE_DEMO, CNPJ_DEMO),
]


def semear():
    """Cria contas e solicitações de exemplo se o banco estiver vazio de usuários."""
    inicializar_banco()
    if listar_usuarios():
        return False  # já tem gente: não semeia (nunca sobrescreve dados reais)

    for login, tipo, nome, cnpj in CONTAS:
        Usuario.criar(login, SENHA_DEMO, tipo, nome, cliente_cnpj=cnpj)

    # Algumas solicitações de exemplo do cliente demo, em situações variadas,
    # pra a lista/tela inicial já mostrar o gráfico e as filas com conteúdo.
    exemplos = [
        ("ferias", {"data_inicio": "2026-08-01", "dias_solicitados": "30", "saldo_dias_direito": "30"}),
        ("declaracao", {"tipo_declaracao": "Vínculo empregatício", "funcionario": "José da Silva"}),
        ("folha_adiantamento", {"competencia": "2026-07", "percentual": "40"}),
    ]
    for tipo, dados in exemplos:
        try:
            bloco1_generico.criar_solicitacao_generica(
                tipo=tipo, cliente_cnpj=CNPJ_DEMO, cliente_nome=NOME_CLIENTE_DEMO,
                funcionario_nome=None, dados_formulario=dados, canal_origem="web",
            )
        except Exception:  # noqa: BLE001 - um exemplo que falhe não impede os demais
            pass

    print("[seed] ambiente de demonstração populado (contas: admin/gestor/analista/cliente · senha: demo123)")
    return True


if __name__ == "__main__":
    criou = semear()
    if not criou:
        print("[seed] banco já tinha usuários — nada foi alterado.")
