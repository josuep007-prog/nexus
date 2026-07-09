"""
modules/rotinas/feriados.py
------------------------------
Consulta feriados oficiais (nacionais/estaduais/municipais) e cadastra
diretamente no Domínio.

Ainda como stub: a consulta a uma fonte oficial de feriados (ex: API pública
de feriados nacionais, ou scraping de site da prefeitura/estado para
feriados municipais) precisa ser implementada por UF/município.
"""

from integracao import dominio_rpa


def consultar_feriados(uf: str, municipio: str, ano: int) -> list:
    """
    Deve retornar uma lista de dicts: [{"data": "2026-11-15", "descricao": "Proclamação da República"}, ...]
    Sugestão: usar uma API pública de feriados nacionais para os fixos, e manter
    uma tabela própria (banco/planilha) para os municipais, já que não têm fonte única confiável.
    """
    raise NotImplementedError("Consulta de feriados ainda não implementada.")


def cadastrar_feriados_no_dominio(feriados: list):
    resultados = []
    for feriado in feriados:
        try:
            dominio_rpa.cadastrar_feriado(feriado["data"], feriado["descricao"])
            resultados.append({**feriado, "status": "cadastrado"})
        except NotImplementedError:
            resultados.append({**feriado, "status": "pendente_integracao"})
    return resultados
