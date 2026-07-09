"""Testes das regras CLT (regras/regras_clt.py) — as validações puras por tipo."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from regras import regras_clt as r


# -- CPF -------------------------------------------------------------------

def test_cpf_valido():
    assert r.validar_cpf("529.982.247-25")  # CPF válido conhecido (dígitos conferem)


def test_cpf_invalido():
    assert not r.validar_cpf("111.111.111-11")  # dígitos repetidos
    assert not r.validar_cpf("123.456.789-00")
    assert not r.validar_cpf("12345")


# -- Férias ------------------------------------------------------------------

def test_ferias_dentro_do_saldo():
    ok, erros = r.validar_ferias(30)
    assert ok and not erros


def test_ferias_acima_do_saldo():
    ok, erros = r.validar_ferias(40, saldo_dias_direito=30)
    assert not ok and erros


def test_ferias_fracionadas_regras_da_reforma():
    # 3 períodos, um com >= 14 dias, nenhum < 5: ok
    ok, _ = r.validar_ferias(30, periodos=[14, 11, 5])
    assert ok
    # nenhum período com 14 dias: reprova
    ok, erros = r.validar_ferias(30, periodos=[10, 10, 10])
    assert not ok and erros


# -- Rescisão ----------------------------------------------------------------

def test_rescisao_data_demissao_antes_da_admissao():
    ok, erros, _ = r.validar_rescisao("sem_justa_causa",
                                      data_admissao=date(2026, 5, 1),
                                      data_demissao=date(2026, 1, 1))
    assert not ok and erros


# -- Tipos novos (CND, Outros, Adiantamento, RPA) -----------------------------

def test_cnd_exige_tipo_de_certidao():
    ok, erros, _ = r.validar_cnd({})
    assert not ok
    ok, _, _ = r.validar_cnd({"tipo_certidao": "crf_fgts", "finalidade": "licitação"})
    assert ok


def test_outros_exige_assunto_e_descricao():
    ok, _, _ = r.validar_outros({})
    assert not ok
    ok, _, _ = r.validar_outros({"assunto": "Relatório de horas",
                                 "descricao": "Preciso de um relatório específico de horas."})
    assert ok


def test_rpa_valida_cpf_do_prestador():
    dados = {"prestador_nome": "João", "prestador_cpf": "111.111.111-11",
             "descricao_servico": "Frete", "valor_servico": "1000", "competencia": "2026-07"}
    ok, erros, _ = r.validar_rpa(dados)
    assert not ok  # CPF inválido tem que reprovar
    dados["prestador_cpf"] = "529.982.247-25"
    ok, _, _ = r.validar_rpa(dados)
    assert ok
