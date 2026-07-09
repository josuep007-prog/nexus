"""Testes da máquina de estados (core/workflow.py).

Rodar:  pip install pytest  ;  pytest
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import BLOCO_1, BLOCO_2
from core import workflow
from core.workflow import (StatusBloco1, StatusBloco2, REPROVADA, ERRO,
                           NA_FILA_AUTOMACAO, EM_ATENDIMENTO_MANUAL, AGUARDANDO_ENTREGA)


def test_status_inicial_por_bloco():
    assert workflow.status_inicial(BLOCO_1) == StatusBloco1.RECEBIDA
    assert workflow.status_inicial(BLOCO_2) == StatusBloco2.RECEBIDA


def test_transicoes_normais_do_bloco1():
    assert workflow.transicao_valida(BLOCO_1, StatusBloco1.RECEBIDA, StatusBloco1.TRIAGEM_IA)
    assert workflow.transicao_valida(BLOCO_1, StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA,
                                     StatusBloco1.APROVADA_PARA_PROCESSAMENTO)


def test_nao_pode_pular_validacao_humana():
    """Regra de ouro do projeto: nada pula a validação humana obrigatória."""
    assert not workflow.transicao_valida(BLOCO_1, StatusBloco1.RECEBIDA, StatusBloco1.CONCLUIDA)
    assert not workflow.transicao_valida(BLOCO_1, StatusBloco1.TRIAGEM_IA,
                                         StatusBloco1.APROVADA_PARA_PROCESSAMENTO)
    assert not workflow.transicao_valida(BLOCO_2, StatusBloco2.EXTRACAO_IA, StatusBloco2.CONCLUIDA)


def test_estados_genericos_entram_e_saem_de_qualquer_lugar():
    for generico in (REPROVADA, ERRO, NA_FILA_AUTOMACAO, EM_ATENDIMENTO_MANUAL, AGUARDANDO_ENTREGA):
        assert workflow.transicao_valida(BLOCO_1, StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA, generico)
        assert workflow.transicao_valida(BLOCO_1, generico, StatusBloco1.TRIAGEM_IA)
        assert workflow.transicao_valida(BLOCO_2, StatusBloco2.AGUARDANDO_APROVACAO_1, generico)


def test_concluida_eh_terminal_no_fluxo_normal():
    assert workflow.proximos_status_possiveis(BLOCO_1, StatusBloco1.CONCLUIDA) == []
    assert workflow.proximos_status_possiveis(BLOCO_2, StatusBloco2.CONCLUIDA) == []


def test_bloco_desconhecido_da_erro():
    import pytest
    with pytest.raises(ValueError):
        workflow.status_inicial("bloco3")
