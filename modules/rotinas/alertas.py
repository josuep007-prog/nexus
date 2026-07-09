"""
modules/rotinas/alertas.py
------------------------------
Painel de alertas e vencimentos: férias vencendo, fim de contrato de
experiência, conversão para tempo indeterminado, prazos de impostos.

Diferente de outras rotinas, este módulo já tem uma implementação funcional
básica (não é só stub), porque a lógica de "gerar alerta X dias antes de uma
data" não depende de nenhuma integração externa — só dos dados que já estão
no banco. Conforme você for alimentando o sistema com dados reais de
funcionários (datas de admissão, férias etc.), os alertas passam a fazer sentido.
"""

from datetime import date, timedelta

from database import db_manager

DIAS_AVISO_FERIAS_VENCENDO = 30
DIAS_AVISO_FIM_EXPERIENCIA = 10


def gerar_alerta_ferias_vencendo(funcionario_nome, cliente_cnpj, data_limite_ferias: date,
                                  solicitacao_id=None):
    dias_restantes = (data_limite_ferias - date.today()).days
    if dias_restantes <= DIAS_AVISO_FERIAS_VENCENDO:
        return db_manager.criar_alerta(
            tipo="vencimento_ferias",
            descricao=f"Férias de {funcionario_nome} ({cliente_cnpj}) vencem em {dias_restantes} dia(s).",
            data_vencimento=data_limite_ferias.isoformat(),
            referencia_id=solicitacao_id,
        )
    return None


def gerar_alerta_fim_experiencia(funcionario_nome, cliente_cnpj, data_fim_experiencia: date,
                                  solicitacao_id=None):
    dias_restantes = (data_fim_experiencia - date.today()).days
    if dias_restantes <= DIAS_AVISO_FIM_EXPERIENCIA:
        return db_manager.criar_alerta(
            tipo="fim_experiencia",
            descricao=f"Contrato de experiência de {funcionario_nome} ({cliente_cnpj}) termina em {dias_restantes} dia(s).",
            data_vencimento=data_fim_experiencia.isoformat(),
            referencia_id=solicitacao_id,
        )
    return None


def gerar_alerta_prazo_imposto(descricao, data_vencimento: date):
    return db_manager.criar_alerta(
        tipo="prazo_imposto",
        descricao=descricao,
        data_vencimento=data_vencimento.isoformat(),
    )


def listar_alertas_pendentes():
    return db_manager.listar_alertas(status="pendente")


def marcar_alerta_resolvido(alerta_id):
    db_manager.atualizar_status_alerta(alerta_id, "resolvido")
