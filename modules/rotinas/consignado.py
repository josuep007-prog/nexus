"""
modules/rotinas/consignado.py
--------------------------------
Disparo mensal automatizado via API do escritório (ou do banco consignatário)
para importar os lançamentos de empréstimo consignado direto na folha.
"""

from database import db_manager


def importar_lancamentos_consignado(competencia: str):
    """
    `competencia` no formato "AAAA-MM". Deve buscar na API do
    escritório/banco os lançamentos do mês e devolver algo como:
    [{"funcionario_cpf": "...", "valor_parcela": 123.45, "contrato": "..."}]
    """
    raise NotImplementedError("Integração com API de consignado ainda não implementada.")


def registrar_lancamentos_como_solicitacoes(lancamentos: list, cliente_cnpj: str, cliente_nome: str):
    """Transforma cada lançamento importado em uma solicitação do tipo 'folha_com_variaveis'."""
    from modules.bloco2.recebimento_anexo import criar_solicitacao_com_anexo

    criadas = []
    for lanc in lancamentos:
        sol = criar_solicitacao_com_anexo(
            tipo="folha_com_variaveis",
            canal_origem="integracao_consignado",
            cliente_cnpj=cliente_cnpj,
            cliente_nome=cliente_nome,
        )
        sol.atualizar_dados({"tipo_variavel": "consignado", **lanc})
        criadas.append(sol)
    return criadas
