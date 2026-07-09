"""
integracao/esocial_monitor.py
--------------------------------
Consulta o status de processamento de um evento enviado ao eSocial
(aceito / recusado / em processamento), a partir do número de recibo.

Na prática o Domínio geralmente já expõe essa informação na própria tela
(ou em relatório); então essa integração pode acabar sendo, na verdade, uma
leitura de tela via `integracao/dominio_rpa.py` em vez de uma chamada de API
direta ao eSocial — decida conforme o que for mais estável no seu fluxo.
"""


def consultar_status_evento(recibo_esocial: str) -> str:
    """
    Retorna uma das strings: "aceito", "recusado", "processando", "desconhecido".
    """
    if not recibo_esocial:
        return "desconhecido"
    raise NotImplementedError("Consulta de status de evento no eSocial ainda não implementada.")


def ultimo_motivo_recusa(recibo_esocial: str) -> str:
    raise NotImplementedError("Consulta de motivo de recusa do eSocial ainda não implementada.")
