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


def test_outros_mapeia_para_solicitacao_geral_do_onvio():
    """'Outros' é a solicitação livre — no Onvio equivale à Solicitação Geral."""
    assert ts.onvio_destino(config.BLOCO_2, "outros") == "Solicitação Geral"


def test_tipos_sem_equivalente_no_onvio_nao_tem_destino():
    """Tipos que o escritório resolve direto (CND, declaração, PPP) não repassam."""
    for tipo in ("cnd", "declaracao", "ppp"):
        assert ts.onvio_destino(config.BLOCO_1, tipo) is None


def test_campos_para_onvio_usa_rotulos_do_onvio_e_valores_da_solicitacao():
    linhas = ts.campos_para_onvio(config.BLOCO_1, "ferias",
                                  {"empregado_nome": "José da Silva", "dias_solicitados": "30"})
    de_para = {l["rotulo_onvio"]: l["valor"] for l in linhas}
    assert de_para["Empregado"] == "José da Silva"
    assert de_para["Dias de gozo"] == "30"
    # campos só do nexus (sem chave "onvio") não vazam para o repasse
    assert all("saldo" not in l["rotulo_onvio"].lower() for l in linhas)


def test_campos_para_onvio_inclui_valores_fixos_do_tipo():
    """Tipos de afastamento já determinam o 'Tipo do Afastamento' exigido no Onvio."""
    linhas = ts.campos_para_onvio(config.BLOCO_2, "cat", {"empregado_nome": "Maria"})
    de_para = {l["rotulo_onvio"]: l["valor"] for l in linhas}
    assert de_para["Tipo do Afastamento"] == "Acidente de trabalho"


def test_tipos_com_formulario_dedicado_tambem_mapeiam_para_onvio():
    """Admissão/atestado têm campos na tela dedicada — o de-para vem de onvio_campos."""
    linhas = ts.campos_para_onvio(config.BLOCO_2, "admissao",
                                  {"funcionario_nome": "Ana", "cargo": "Vendedora"})
    de_para = {l["rotulo_onvio"]: l["valor"] for l in linhas}
    assert de_para["Nome do colaborador"] == "Ana"
    assert de_para["Cargo"] == "Vendedora"
    assert de_para["Tipo de colaborador"] == "Empregado"
