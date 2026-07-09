"""
modules/rotinas/monitor_cct.py
---------------------------------
Varredura periódica (mensal) por CNPJ no sistema do Mediador (MTE) para
buscar novos aditivos e convenções coletivas.

Fonte: https://www3.mte.gov.br/sistemas/mediador/consultarinstcoletivo

O Mediador não tem uma API pública documentada — a consulta normalmente
precisa ser feita via scraping da busca por CNPJ/sindicato, o que é frágil
(o site pode mudar de layout). Vale considerar rodar isso com Selenium/Playwright
em vez de requests puro, caso a busca dependa de JavaScript.
"""

from regras.regras_cct import CADASTRO_CCT_POR_CNPJ


def verificar_novos_aditivos(cnpj: str):
    """
    Deve retornar algo como:
    {"tem_novidade": bool, "convencoes": [...], "ultima_verificacao": "2026-07-01"}
    """
    raise NotImplementedError("Integração com o Mediador (MTE) ainda não implementada.")


def atualizar_cadastro_cct(cnpj: str, dados_convencao: dict):
    """Depois que uma nova CCT é confirmada (manualmente ou via scraping), atualiza o cadastro usado nas regras."""
    CADASTRO_CCT_POR_CNPJ[cnpj] = dados_convencao
