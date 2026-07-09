"""
utils/prazos.py
----------------
Prazo (SLA) de atendimento por solicitação e alertas de fim de experiência.

O SLA é contado em dias corridos a partir do recebimento (criado_em), com o
prazo de cada tipo em config.SLA_POR_TIPO (padrão config.SLA_PADRAO_DIAS).
Solicitações finalizadas (concluída/reprovada) não têm situação de prazo.
"""

from datetime import datetime, timedelta, date

import config
from database import db_manager

STATUS_SEM_PRAZO = {"concluida", "reprovada"}


def sla_dias(tipo):
    return config.SLA_POR_TIPO.get(tipo, config.SLA_PADRAO_DIAS)


def prazo_limite(sol):
    """Data-limite de atendimento (datetime) da solicitação."""
    criado = datetime.fromisoformat(sol._row["criado_em"])
    return criado + timedelta(days=sla_dias(sol.tipo))


def situacao_prazo(sol):
    """'ok' | 'atencao' (vence em <= SLA_ATENCAO_DIAS) | 'estourado' | None (finalizada)."""
    if sol.status in STATUS_SEM_PRAZO:
        return None
    limite = prazo_limite(sol)
    agora = datetime.now()
    if agora > limite:
        return "estourado"
    if agora >= limite - timedelta(days=config.SLA_ATENCAO_DIAS):
        return "atencao"
    return "ok"


def rotulo_prazo(sol):
    """Texto curto para exibir nas filas: 'vence hoje', 'vencida há 2d', 'até 12/07'."""
    situacao = situacao_prazo(sol)
    if situacao is None:
        return None
    limite = prazo_limite(sol)
    hoje = date.today()
    dias = (limite.date() - hoje).days
    if dias < 0:
        return f"vencida há {-dias}d"
    if dias == 0:
        return "vence hoje"
    if dias == 1:
        return "vence amanhã"
    return f"até {limite.strftime('%d/%m')}"


# ---------------------------------------------------------------------------
# Alertas de fim do contrato de experiência (45/90 dias após a admissão)
# ---------------------------------------------------------------------------

def gerar_alertas_experiencia():
    """Cria alertas de vencimento de experiência para admissões concluídas.

    Idempotente: usa a descrição como chave — não duplica alerta já criado.
    Chamada ao abrir a página de alertas (barata: só varre admissões concluídas).
    """
    criados = 0
    existentes = {(a["tipo"], a["referencia_id"], a["descricao"])
                  for a in db_manager.listar_alertas(status=None)}
    admissoes = [s for s in db_manager.listar_solicitacoes(tipo="admissao", status="concluida")]
    admissoes += db_manager.listar_solicitacoes(tipo="admissao_estagiario", status="concluida")
    admissoes += db_manager.listar_solicitacoes(tipo="admissao_aprendiz", status="concluida")

    import json
    for row in admissoes:
        dados = json.loads(row.get("dados_json") or "{}")
        data_admissao = dados.get("data_admissao")
        if not data_admissao:
            continue
        try:
            inicio = datetime.fromisoformat(data_admissao).date()
        except ValueError:
            continue  # data em formato livre — não dá pra calcular
        for dias in config.EXPERIENCIA_AVISOS_DIAS:
            vencimento = inicio + timedelta(days=dias)
            if vencimento < date.today():
                continue  # já passou — não adianta alertar
            descricao = (f"Fim do período de experiência ({dias} dias) de "
                         f"{row.get('funcionario_nome') or 'funcionário'} — "
                         f"{row.get('cliente_nome') or ''} (admissão #{row['id']})")
            chave = ("fim_experiencia", row["id"], descricao)
            if chave in existentes:
                continue
            db_manager.criar_alerta("fim_experiencia", descricao,
                                    data_vencimento=vencimento.isoformat(),
                                    referencia_id=row["id"])
            existentes.add(chave)
            criados += 1
    return criados
