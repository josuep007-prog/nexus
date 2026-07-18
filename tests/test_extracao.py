"""
Testes da extração de documentos (modules/bloco2/extracao.py).

Trabalham sobre TEXTO, não sobre arquivos: o que importa aqui é a regra de
"achar campo por rótulo, normalizar e validar". A leitura do PDF/imagem em si
depende de bibliotecas pesadas e de documentos reais — é calibrada com
`python scripts/testar_extracao.py`.

Os textos abaixo imitam o padrão "Rótulo: valor" das fichas de registro/
admissão. Não são o layout de um documento específico (isso exigiria amostras
reais) — testam justamente a parte que independe de layout.
"""

from modules.bloco2 import extracao

# CPF e PIS com dígito verificador VÁLIDO (necessário: valores inválidos são recusados)
CPF_VALIDO = "111.444.777-35"
PIS_VALIDO = "120.12345.67-2"

FICHA = f"""FICHA DE REGISTRO DE EMPREGADO
Nome completo: Maria Aparecida de Souza
CPF: {CPF_VALIDO}          PIS/PASEP: {PIS_VALIDO}
Data de nascimento: 15/03/1992
Data de admissao: 01/09/2026
Cargo: Auxiliar Administrativo
Departamento: Financeiro
Salario: R$ 2.450,00
Horario de trabalho: 08:00 as 17:00
CTPS: 1234567   Serie: 0012
Banco: 341   Agencia: 4521   Conta corrente: 12345-6
"""


def test_ficha_completa_preenche_todos_os_campos_minimos():
    dados = extracao.extrair_campos(FICHA)
    diagnostico = dados.pop("_diagnostico")
    assert diagnostico["faltando"] == []
    assert diagnostico["recusados"] == {}
    assert dados["nome_completo"] == "Maria Aparecida de Souza"
    assert dados["cargo"] == "Auxiliar Administrativo"
    assert dados["departamento"] == "Financeiro"


def test_normaliza_data_para_iso_e_valor_para_decimal():
    dados = extracao.extrair_campos(FICHA)
    assert dados["data_admissao"] == "2026-09-01"      # veio como 01/09/2026
    assert dados["data_nascimento"] == "1992-03-15"
    assert dados["salario"] == "2450.00"                # veio como R$ 2.450,00


def test_dois_campos_na_mesma_linha_nao_se_misturam():
    """'CPF: X   PIS/PASEP: Y' — o valor do CPF não pode engolir o rótulo seguinte."""
    dados = extracao.extrair_campos(FICHA)
    assert dados["cpf"] == "11144477735"
    assert dados["pis_nis"] == "12012345672"


def test_cpf_invalido_e_recusado_em_vez_de_entregue():
    """Dado ruim não pode entrar como se fosse bom — vira pendência pro analista."""
    dados = extracao.extrair_campos("Nome: Fulano\nCPF: 111.111.111-11")
    diagnostico = dados.pop("_diagnostico")
    assert "cpf" not in dados
    assert "cpf" in diagnostico["recusados"]


def test_documento_sem_rotulos_ainda_acha_cpf_e_pis_validos():
    """Foto de CTPS/documento solto: sem 'Rótulo:', o fallback busca por formato."""
    dados = extracao.extrair_campos(f"documento sem rotulo {CPF_VALIDO} e {PIS_VALIDO} soltos")
    assert dados["cpf"] == "11144477735"
    assert dados["pis_nis"] == "12012345672"


def test_rotulos_alternativos_sao_reconhecidos():
    """Cada escritório escreve de um jeito — 'Função' vale por 'Cargo', etc."""
    dados = extracao.extrair_campos(
        "Nome do empregado: Joao Lima\nFuncao: Vendedor\nSetor: Comercial\nRemuneracao: 1.800,00")
    assert dados["nome_completo"] == "Joao Lima"
    assert dados["cargo"] == "Vendedor"
    assert dados["departamento"] == "Comercial"
    assert dados["salario"] == "1800.00"


def test_diagnostico_lista_o_que_faltou():
    dados = extracao.extrair_campos("Nome: Ana Souza")
    diagnostico = dados.pop("_diagnostico")
    assert "cpf" in diagnostico["faltando"]
    assert "nome_completo" in diagnostico["achados"]


def test_texto_vazio_nao_quebra():
    dados = extracao.extrair_campos("")
    assert dados["_diagnostico"]["achados"] == []
