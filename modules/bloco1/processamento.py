"""
modules/bloco1/processamento.py
---------------------------------
Automação 2 do Bloco 1: processamento da solicitação no sistema Domínio e
acompanhamento do evento correspondente no eSocial.

Esse módulo é o ponto de integração com `integracao/dominio_rpa.py` (PyAutoGUI)
e `integracao/esocial_monitor.py`. Por enquanto ambos são stubs — a lógica de
automação de tela em si deve reaproveitar o padrão que você já usa no seu
pacote `dominio_banco_agencia`.
"""

from core.solicitacao import Solicitacao
from core.workflow import StatusBloco1
from integracao import dominio_rpa, esocial_monitor


def processar_no_dominio(solicitacao: Solicitacao):
    """Envia a solicitação aprovada para o Domínio processar."""
    solicitacao.avancar(StatusBloco1.PROCESSANDO_DOMINIO)

    try:
        resultado = dominio_rpa.executar_processo(solicitacao.tipo, solicitacao.dados)
        solicitacao.atualizar_dados({"resultado_dominio": resultado})
        solicitacao.avancar(StatusBloco1.AGUARDANDO_ESOCIAL)
        return True
    except NotImplementedError:
        # Esperado enquanto integracao/dominio_rpa.py ainda for um stub.
        solicitacao.registrar_erro("processamento_dominio", "Integração com Domínio ainda não implementada.")
        return False
    except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha de RPA aqui
        solicitacao.registrar_erro("processamento_dominio", str(exc))
        solicitacao.avancar(StatusBloco1.ERRO_ESOCIAL, forcar=True)
        return False


def monitorar_esocial(solicitacao: Solicitacao):
    """
    Consulta o status do evento no eSocial. Se aceito, segue o fluxo normal.
    Se recusado, marca erro para o analista corrigir e reprocessar.
    """
    status_evento = esocial_monitor.consultar_status_evento(
        solicitacao.dados.get("recibo_esocial")
    )

    if status_evento == "aceito":
        solicitacao.avancar(StatusBloco1.RELATORIO_GERADO)
        return True
    elif status_evento == "recusado":
        solicitacao.registrar_erro(
            "monitor_esocial",
            f"Evento recusado pelo eSocial: {esocial_monitor.ultimo_motivo_recusa(solicitacao.dados.get('recibo_esocial'))}",
        )
        solicitacao.avancar(StatusBloco1.ERRO_ESOCIAL)
        return False
    else:
        # ainda processando no eSocial, nada a fazer por enquanto
        return None


def registrar_correcao_e_reprocessar(solicitacao: Solicitacao, correcoes: dict, analista: str):
    """
    Quando o eSocial recusa um evento, o analista corrige e o sistema tenta
    reprocessar. Idealmente aqui também entraria uma regra "aprendida" pra
    evitar repetir o mesmo erro no futuro (ex: gravar em regras_cct.py /
    numa tabela de erros conhecidos).
    """
    solicitacao.atualizar_dados(correcoes)
    solicitacao.validar("correcao_esocial", True, aprovado_por=analista,
                         comentario="Correção aplicada após recusa do eSocial")
    return processar_no_dominio(solicitacao)
