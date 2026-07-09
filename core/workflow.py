"""
core/workflow.py
-----------------
Define os status possíveis de uma solicitação e a ordem em que eles acontecem,
para cada bloco. Isso é o "mapa" do processo transformado em código.

A ideia é que NENHUM módulo mude o status de uma solicitação "no chute" —
sempre passando por `avancar()`, que valida se a transição faz sentido.
Isso evita, por exemplo, uma solicitação pular direto de "recebida" pra
"concluída" por um bug em algum módulo.
"""

from config import BLOCO_1, BLOCO_2

# ---------------------------------------------------------------------------
# Status - Bloco 1 (sem anexo: férias, rescisão, alteração cadastral, relatórios)
# ---------------------------------------------------------------------------
class StatusBloco1:
    RECEBIDA = "recebida"
    TRIAGEM_IA = "triagem_ia"
    AGUARDANDO_AJUSTE_CLIENTE = "aguardando_ajuste_cliente"
    AGUARDANDO_VALIDACAO_HUMANA = "aguardando_validacao_humana"
    APROVADA_PARA_PROCESSAMENTO = "aprovada_para_processamento"
    PROCESSANDO_DOMINIO = "processando_dominio"
    AGUARDANDO_ESOCIAL = "aguardando_esocial"
    ERRO_ESOCIAL = "erro_esocial"
    RELATORIO_GERADO = "relatorio_gerado"
    AGUARDANDO_APROVACAO_DISTRIBUICAO = "aguardando_aprovacao_distribuicao"
    DISTRIBUINDO = "distribuindo"
    CONCLUIDA = "concluida"


# Transições permitidas: de onde -> pra onde (lista)
FLUXO_BLOCO_1 = {
    StatusBloco1.RECEBIDA: [StatusBloco1.TRIAGEM_IA],
    StatusBloco1.TRIAGEM_IA: [
        StatusBloco1.AGUARDANDO_AJUSTE_CLIENTE,
        StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA,
    ],
    StatusBloco1.AGUARDANDO_AJUSTE_CLIENTE: [
        StatusBloco1.TRIAGEM_IA,                    # cliente corrigiu, roda triagem de novo
        StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA,    # cliente optou por enviar mesmo assim
    ],
    StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA: [StatusBloco1.APROVADA_PARA_PROCESSAMENTO],
    StatusBloco1.APROVADA_PARA_PROCESSAMENTO: [StatusBloco1.PROCESSANDO_DOMINIO],
    StatusBloco1.PROCESSANDO_DOMINIO: [StatusBloco1.AGUARDANDO_ESOCIAL],
    StatusBloco1.AGUARDANDO_ESOCIAL: [StatusBloco1.RELATORIO_GERADO, StatusBloco1.ERRO_ESOCIAL],
    StatusBloco1.ERRO_ESOCIAL: [StatusBloco1.PROCESSANDO_DOMINIO],  # após correção do analista
    StatusBloco1.RELATORIO_GERADO: [StatusBloco1.AGUARDANDO_APROVACAO_DISTRIBUICAO],
    StatusBloco1.AGUARDANDO_APROVACAO_DISTRIBUICAO: [StatusBloco1.DISTRIBUINDO],
    StatusBloco1.DISTRIBUINDO: [StatusBloco1.CONCLUIDA],
    StatusBloco1.CONCLUIDA: [],
}

# ---------------------------------------------------------------------------
# Status - Bloco 2 (com anexo: folha com variáveis, admissões, afastamentos)
# ---------------------------------------------------------------------------
class StatusBloco2:
    RECEBIDA = "recebida"
    UPLOAD_VINCULADO = "upload_vinculado"
    EXTRACAO_IA = "extracao_ia"
    AGUARDANDO_APROVACAO_1 = "aguardando_aprovacao_1"   # revisão dos dados extraídos
    PREENCHENDO_SISTEMA = "preenchendo_sistema"
    AGUARDANDO_APROVACAO_2 = "aguardando_aprovacao_2"   # autoriza salvar/processar/gerar relatório
    PROCESSANDO = "processando"
    RELATORIO_GERADO = "relatorio_gerado"
    AGUARDANDO_APROVACAO_3 = "aguardando_aprovacao_3"   # aval final pra enviar ao cliente
    DISTRIBUINDO = "distribuindo"
    CONCLUIDA = "concluida"


FLUXO_BLOCO_2 = {
    StatusBloco2.RECEBIDA: [StatusBloco2.UPLOAD_VINCULADO],
    StatusBloco2.UPLOAD_VINCULADO: [StatusBloco2.EXTRACAO_IA],
    StatusBloco2.EXTRACAO_IA: [StatusBloco2.AGUARDANDO_APROVACAO_1],
    StatusBloco2.AGUARDANDO_APROVACAO_1: [StatusBloco2.PREENCHENDO_SISTEMA],
    StatusBloco2.PREENCHENDO_SISTEMA: [StatusBloco2.AGUARDANDO_APROVACAO_2],
    StatusBloco2.AGUARDANDO_APROVACAO_2: [StatusBloco2.PROCESSANDO],
    StatusBloco2.PROCESSANDO: [StatusBloco2.RELATORIO_GERADO],
    StatusBloco2.RELATORIO_GERADO: [StatusBloco2.AGUARDANDO_APROVACAO_3],
    StatusBloco2.AGUARDANDO_APROVACAO_3: [StatusBloco2.DISTRIBUINDO],
    StatusBloco2.DISTRIBUINDO: [StatusBloco2.CONCLUIDA],
    StatusBloco2.CONCLUIDA: [],
}

ERRO = "erro"  # status genérico de erro, pode ser aplicado em qualquer bloco
REPROVADA = "reprovada"  # genérico: analista reprovou; volta pro cliente editar/excluir

# Após aprovar, o analista decide COMO o trabalho no Domínio vai ser feito:
NA_FILA_AUTOMACAO = "na_fila_automacao"        # o worker do PC-host vai processar sozinho
EM_ATENDIMENTO_MANUAL = "em_atendimento_manual"  # o analista vai fazer na mão no Domínio
AGUARDANDO_ENTREGA = "aguardando_entrega"      # automação processou; escritório revisa, anexa resultado e entrega

# Estados "genéricos" que podem ser alcançados/deixados de qualquer ponto do
# fluxo (o código que chama controla o destino certo).
_ESTADOS_GENERICOS = {ERRO, REPROVADA, NA_FILA_AUTOMACAO, EM_ATENDIMENTO_MANUAL, AGUARDANDO_ENTREGA}


def fluxo_para_bloco(bloco):
    if bloco == BLOCO_1:
        return FLUXO_BLOCO_1
    elif bloco == BLOCO_2:
        return FLUXO_BLOCO_2
    raise ValueError(f"Bloco desconhecido: {bloco}")


def status_inicial(bloco):
    if bloco == BLOCO_1:
        return StatusBloco1.RECEBIDA
    elif bloco == BLOCO_2:
        return StatusBloco2.RECEBIDA
    raise ValueError(f"Bloco desconhecido: {bloco}")


def transicao_valida(bloco, status_atual, novo_status):
    """Verifica se ir de status_atual -> novo_status é uma transição permitida."""
    # Estados genéricos (erro, reprovada, fila de automação, atendimento manual)
    # podem ser alcançados ou deixados de qualquer ponto — o código que chama
    # controla o destino correto (worker, conclusão manual, reenvio do cliente).
    if novo_status in _ESTADOS_GENERICOS or status_atual in _ESTADOS_GENERICOS:
        return True
    fluxo = fluxo_para_bloco(bloco)
    return novo_status in fluxo.get(status_atual, [])


def proximos_status_possiveis(bloco, status_atual):
    fluxo = fluxo_para_bloco(bloco)
    return fluxo.get(status_atual, [])
