"""
scripts/seed_empregados.py
---------------------------
Massa de teste do Dossiê do Empregado: cria empregados fictícios vinculados aos
clientes existentes, para validar os fluxos de conferência automática (Cenário A
com dados completos e Cenário B com dados insuficientes).

Idempotente: usa upsert por (cliente_cnpj, cpf), então pode rodar quantas vezes
quiser sem duplicar. Roda sozinho no seed de demonstração e também pode ser
chamado à parte num banco já existente:

    python scripts/seed_empregados.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_manager  # noqa: E402

# (cliente_cnpj, cpf, dados). saldo_ferias_dias None de propósito em alguns,
# para exercitar o Cenário B (empregado existe, mas sem dado p/ conferência).
EMPREGADOS = [
    # Cliente "Cliente" (00.000.000/0001-00) — variados
    ("00.000.000/0001-00", "123.456.789-00", {
        "nome": "José da Silva", "data_nascimento": "1988-04-12", "pis_nis": "120.45678.90-1",
        "cargo": "Analista Contábil", "departamento": "Contabilidade", "salario": "3500.00",
        "data_admissao": "2019-03-01", "raca_cor": "parda", "banco": "001", "agencia": "1234",
        "conta": "56789-0", "saldo_ferias_dias": 30}),
    ("00.000.000/0001-00", "111.222.333-44", {
        "nome": "Maria Souza", "data_nascimento": "1992-11-30", "cargo": "Assistente de RH",
        "departamento": "Recursos Humanos", "salario": "2600.00", "data_admissao": "2021-06-15",
        "raca_cor": "branca", "saldo_ferias_dias": 20}),
    ("00.000.000/0001-00", "999.888.777-66", {
        "nome": "Carlos Pereira", "cargo": "Auxiliar", "data_admissao": "2024-02-01",
        "salario": "1800.00"}),  # sem saldo_ferias_dias -> Cenário B (existe, faltam dados)
    # Empresa A Ltda (11.111.111/0001-11)
    ("11.111.111/0001-11", "222.333.444-55", {
        "nome": "Ana Lima", "data_nascimento": "1985-07-08", "cargo": "Gerente",
        "departamento": "Administrativo", "salario": "7200.00", "data_admissao": "2018-09-01",
        "raca_cor": "preta", "saldo_ferias_dias": 30}),
    # Empresa B Ltda (22.222.222/0001-22)
    ("22.222.222/0001-22", "333.444.555-66", {
        "nome": "Pedro Alves", "cargo": "Vendedor", "salario": "2200.00",
        "data_admissao": "2022-10-20", "saldo_ferias_dias": 15}),
]


def semear_empregados():
    """Upsert dos empregados de teste + um evento de admissão no histórico. Idempotente."""
    db_manager.inicializar_banco()
    total = 0
    for cnpj, cpf, dados in EMPREGADOS:
        emp_id = db_manager.sincronizar_empregado(cnpj, cpf, dados, origem_dados="teste")
        # Registra a admissão no histórico só se ainda não houver nenhum evento.
        if not db_manager.listar_historico_empregado(emp_id):
            db_manager.adicionar_historico_empregado(
                emp_id, "admissao",
                descricao=f"Admissão (massa de teste) em {dados.get('data_admissao', '?')}",
                dados={"cargo": dados.get("cargo"), "salario": dados.get("salario")},
                data_evento=dados.get("data_admissao"))
        total += 1
    return total


if __name__ == "__main__":
    n = semear_empregados()
    print(f"[seed] {n} empregados de teste vinculados aos clientes (dossiê pronto para conferência).")
