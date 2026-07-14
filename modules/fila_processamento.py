"""
modules/fila_processamento.py
------------------------------
Ponte entre a decisão do analista ("automatizar" ou "atender manual") e o
trabalho de fato no Domínio.

- `processar_automatico(sol)` é o que o WORKER do PC-host chama para cada
  solicitação que está `na_fila_automacao`: coloca em "processando", aciona o
  RPA (integracao/dominio_rpa.py) e, se der certo, segue o fluxo normal; se
  falhar, registra o erro e joga a solicitação para atendimento MANUAL (pra um
  humano resolver) — nunca finge que deu certo.

- `concluir_atendimento_manual(sol)` é o que a WEB chama quando o analista
  termina de fazer manualmente no Domínio e clica "Concluir".

Depois do trabalho no Domínio (auto ou manual), a solicitação vai para o
próximo passo que já existia no fluxo:
  - Bloco 1: aguardando eSocial
  - Bloco 2: aguardando a 2ª aprovação
"""

from config import BLOCO_1
from core.solicitacao import Solicitacao
from core.workflow import StatusBloco1, StatusBloco2, EM_ATENDIMENTO_MANUAL, AGUARDANDO_ENTREGA
from database import db_manager
from integracao import dominio_rpa
from modules import dossie
from modules.bloco2.atestados import extensao_permitida
from utils import file_manager


def _status_processando(sol: Solicitacao):
    """Status exibido enquanto o Domínio está sendo preenchido."""
    if sol.bloco == BLOCO_1:
        return StatusBloco1.PROCESSANDO_DOMINIO
    return StatusBloco2.PREENCHENDO_SISTEMA


def processar_automatico(sol: Solicitacao):
    """
    Processa UMA solicitação no Domínio via RPA. Chamado pelo worker do PC-host.
    Retorna (ok, info). Em caso de falha (incluindo integração ainda não
    implementada), devolve a solicitação para atendimento manual.
    """
    sol.avancar(_status_processando(sol))
    try:
        resultado = dominio_rpa.executar_processo(sol.tipo, sol.dados)
        sol.atualizar_dados({"resultado_dominio": resultado, "erro_automacao": None})
        # Registra no histórico que quem executou foi a automação.
        sol.validar("processamento_automatico", True, aprovado_por="Automação (worker)",
                    comentario="Preenchido no Domínio pela automação")
        # Automação fez o trabalho no Domínio; agora o escritório revisa,
        # anexa o resultado (comprovante/documento) e entrega ao cliente.
        dossie.registrar_solicitacao_processada(sol)
        sol.avancar(AGUARDANDO_ENTREGA)
        return True, resultado
    except NotImplementedError as exc:
        # Automação ainda não pronta para esse tipo — cai pro humano fazer.
        sol.registrar_erro("processamento_dominio", f"Automação indisponível: {exc}")
        sol.atualizar_dados({"erro_automacao": f"Automação indisponível: {exc}"})
        sol.avancar(EM_ATENDIMENTO_MANUAL)
        return False, str(exc)
    except Exception as exc:  # noqa: BLE001 - qualquer falha de RPA cai pro humano
        sol.registrar_erro("processamento_dominio", str(exc))
        sol.atualizar_dados({"erro_automacao": str(exc)})
        sol.avancar(EM_ATENDIMENTO_MANUAL)
        return False, str(exc)


def anexar_resultados(sol: Solicitacao, arquivos):
    """Anexa à solicitação os documentos gerados pelo escritório (origem='escritorio').

    `arquivos` é uma lista de tuplas (bytes, nome_original). Ignora extensões
    não permitidas. Devolve quantos anexos foram salvos.
    """
    salvos = 0
    for arquivo_bytes, nome_original in (arquivos or []):
        if nome_original and extensao_permitida(nome_original):
            caminho = file_manager.salvar_anexo_recebido(sol.tipo, sol.id, arquivo_bytes, nome_original)
            tipo_arquivo = caminho.suffix.lstrip(".").lower() or None
            db_manager.adicionar_anexo(sol.id, str(caminho), tipo_arquivo, origem="escritorio")
            salvos += 1
    return salvos


def concluir_atendimento_manual(sol: Solicitacao, por: str = None, resumo: str = None, arquivos=None):
    """
    O analista terminou o trabalho no Domínio e ENTREGA ao cliente: anexa os
    documentos gerados (origem='escritorio'), grava um resumo do que foi feito
    e finaliza a solicitação (concluída). O cliente passa a ver tudo no detalhe.
    """
    anexar_resultados(sol, arquivos)
    dados = {"erro_automacao": None}
    if resumo:
        dados["resumo_entrega"] = resumo
    sol.atualizar_dados(dados)
    sol.validar("processamento_manual", True, aprovado_por=por,
                comentario=resumo or "Atendido manualmente no Domínio")
    dossie.registrar_solicitacao_processada(sol)
    # Entrega direta ao cliente. (As etapas internas seguintes ainda são stubs;
    # quando existirem, é aqui que se insere aprovação 2/3 antes de concluir.)
    sol.avancar(StatusBloco1.CONCLUIDA if sol.bloco == BLOCO_1 else StatusBloco2.CONCLUIDA)
    return True
