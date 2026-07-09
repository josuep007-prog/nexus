"""Testes do SLA de atendimento (utils/prazos.py) — parte pura, sem banco."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from utils import prazos


class _SolFake:
    """Só o que situacao_prazo/rotulo_prazo usam: _row.criado_em, status, tipo."""
    def __init__(self, criado_em, status="recebida", tipo="declaracao"):
        self._row = {"criado_em": criado_em}
        self.status = status
        self.tipo = tipo


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def test_sla_por_tipo_e_padrao():
    assert prazos.sla_dias("cat") == config.SLA_POR_TIPO["cat"]
    assert prazos.sla_dias("tipo_que_nao_existe") == config.SLA_PADRAO_DIAS


def test_recem_criada_esta_ok():
    sol = _SolFake(_iso(datetime.now()))
    assert prazos.situacao_prazo(sol) == "ok"


def test_prazo_estourado():
    sol = _SolFake(_iso(datetime.now() - timedelta(days=config.SLA_PADRAO_DIAS + 2)))
    assert prazos.situacao_prazo(sol) == "estourado"
    assert "vencida" in prazos.rotulo_prazo(sol)


def test_perto_do_vencimento_fica_em_atencao():
    dias = prazos.sla_dias("declaracao")
    sol = _SolFake(_iso(datetime.now() - timedelta(days=dias, hours=-2)))  # vence em ~2h
    assert prazos.situacao_prazo(sol) == "atencao"


def test_finalizadas_nao_tem_prazo():
    for status in ("concluida", "reprovada"):
        sol = _SolFake(_iso(datetime.now() - timedelta(days=99)), status=status)
        assert prazos.situacao_prazo(sol) is None
        assert prazos.rotulo_prazo(sol) is None
