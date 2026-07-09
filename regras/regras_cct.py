"""
regras/regras_cct.py
---------------------
Regras ligadas à Convenção Coletiva de Trabalho (CCT) de cada cliente/sindicato.

Diferente das regras da CLT (que são as mesmas pra todo mundo), as regras de
CCT variam por sindicato/categoria/CNPJ e mudam com frequência (reajustes
anuais, pisos salariais, adicionais). Por isso esse módulo é, propositalmente,
mais "cadastro" do que "lógica fixa" — a ideia é alimentar
CADASTRO_CCT_POR_CNPJ (ou uma tabela no banco, futuramente) com os dados reais
de cada convenção, e o `modules/rotinas/monitor_cct.py` mantém isso atualizado
consultando o site do MTE.

Por enquanto está com dados de exemplo (fictícios) só pra deixar a estrutura
funcionando ponta a ponta.
"""

# Exemplo de estrutura de cadastro. Troque pelos dados reais dos seus clientes,
# ou migre isso para uma tabela no banco quando o monitor_cct.py estiver pronto.
CADASTRO_CCT_POR_CNPJ = {
    # "00.000.000/0001-00": {
    #     "sindicato": "Sindicato dos Comerciários de XXXX",
    #     "piso_salarial": 1650.00,
    #     "data_base": "01/01",
    #     "adicional_periculosidade": 0.30,
    # },
}


def obter_cct_do_cliente(cnpj: str):
    """Retorna o cadastro de CCT do cliente, ou None se não houver cadastro."""
    return CADASTRO_CCT_POR_CNPJ.get(cnpj)


def validar_piso_salarial(cnpj: str, salario: float):
    """
    Confere se o salário informado respeita o piso da CCT do cliente.
    Se não houver CCT cadastrada pro CNPJ, retorna ok=True com aviso —
    não bloqueia a solicitação, mas sinaliza que não há verificação de CCT feita.
    """
    cct = obter_cct_do_cliente(cnpj)
    if cct is None:
        return (True, ["Nenhuma CCT cadastrada para esse CNPJ — piso salarial não verificado."])

    piso = cct.get("piso_salarial")
    if piso is not None and salario < piso:
        return (False, [f"Salário informado (R$ {salario:.2f}) é menor que o piso da CCT (R$ {piso:.2f})."])

    return (True, [])
