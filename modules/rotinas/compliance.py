"""
modules/rotinas/compliance.py
--------------------------------
Lembretes automáticos baseados em prazos da Receita Federal e mudanças na
legislação. Sugere a aplicação automática por CNPJ das medidas necessárias
(reajustes de pisos salariais, adicionais de CCT etc.).

Esse módulo naturalmente se conecta com monitor_cct.py (fonte dos reajustes)
e alertas.py (para notificar o time).
"""

from modules.rotinas import alertas
from regras.regras_cct import CADASTRO_CCT_POR_CNPJ


def verificar_prazos_receita_federal():
    """
    Deve consultar o calendário de obrigações da Receita Federal (ex: DCTFWeb,
    eSocial, FGTS Digital) e gerar alertas para os prazos que se aproximam.
    """
    raise NotImplementedError("Consulta ao calendário de obrigações da Receita Federal ainda não implementada.")


def sugerir_aplicacao_reajuste_cct(cnpj: str):
    """
    Quando monitor_cct.py detecta uma nova convenção/aditivo para um CNPJ,
    esta função organiza a sugestão de reajuste (piso salarial, adicionais)
    para revisão humana antes de aplicar em massa.
    """
    cct = CADASTRO_CCT_POR_CNPJ.get(cnpj)
    if cct is None:
        return None

    descricao = (
        f"Nova CCT detectada para {cnpj}: piso salarial R$ {cct.get('piso_salarial', 'N/D')}. "
        "Revisar e aplicar reajustes necessários."
    )
    return alertas.db_manager.criar_alerta(tipo="reajuste_cct", descricao=descricao)
