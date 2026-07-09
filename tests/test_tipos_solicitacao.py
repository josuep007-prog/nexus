"""Consistência do registro central de tipos (core/tipos_solicitacao.py).

Garante que a regra do CLAUDE.md ("adicione o tipo em 3 lugares") foi seguida:
cada tipo de config.py tem schema registrado, título, e (quando é formulário)
campos + função de validação.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from core import tipos_solicitacao as ts


def test_todo_tipo_do_config_tem_schema():
    for tipo in config.TIPOS_BLOCO_1:
        assert ts.schema_do_tipo(config.BLOCO_1, tipo) is not None, f"bloco1/{tipo} sem schema"
    for tipo in config.TIPOS_BLOCO_2:
        assert ts.schema_do_tipo(config.BLOCO_2, tipo) is not None, f"bloco2/{tipo} sem schema"


def test_todo_schema_tem_titulo():
    for _bloco, tipo, schema in ts.catalogo_completo():
        assert schema.get("titulo"), f"{tipo} sem título"


def test_validar_quando_definido_eh_chamavel_e_retorna_tripla():
    """`validar` pode ser None (só campos obrigatórios), mas quando existe tem
    que ser chamável e devolver (ok, erros, extra) — o contrato do projeto."""
    for bloco, tipo, schema in ts.catalogo_completo():
        validar = schema.get("validar")
        if validar is None:
            continue
        assert callable(validar), f"{bloco}/{tipo}: validar não é chamável"
        resultado = validar({})  # dict vazio nunca deve estourar exceção
        assert isinstance(resultado, tuple) and len(resultado) == 3, \
            f"{bloco}/{tipo}: validar deve retornar (ok, erros, extra)"


def test_categorias_cobrem_so_tipos_existentes():
    conhecidos = {tipo for _b, tipo, _s in ts.catalogo_completo()}
    for categoria, tipos in ts.CATEGORIAS.items():
        for tipo in tipos:
            assert tipo in conhecidos, f"categoria '{categoria}' referencia tipo inexistente '{tipo}'"


def test_outros_nao_eh_automatizavel():
    schema = ts.schema_do_tipo(config.BLOCO_2, "outros")
    assert schema.get("automatizavel") is False
