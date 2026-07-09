"""
integracao/onvio_api.py
--------------------------
Integração com o Portal Onvio (anexar documentos na solicitação do portal do
cliente, publicar no portal de documentos, e envio de e-mail).

Você mencionou já ter scripts Batch com cURL/PowerShell para anexar arquivos
no portal do cliente — o ideal é portar essa lógica de request HTTP pra cá
(usando `requests`), assim tudo fica dentro do mesmo sistema Python em vez de
espalhado em scripts separados.

Preencha ONVIO_BASE_URL e ONVIO_TOKEN no config.py (de preferência via
variável de ambiente, não hardcoded) quando for implementar de verdade.
"""

import requests

from config import ONVIO_BASE_URL, ONVIO_TOKEN


def _headers():
    return {"Authorization": f"Bearer {ONVIO_TOKEN}", "Content-Type": "application/json"}


def anexar_na_solicitacao_portal(solicitacao_id: int, caminho_arquivo) -> dict:
    """Anexa um arquivo na solicitação correspondente dentro do Portal Onvio."""
    raise NotImplementedError("Integração de anexo no portal do cliente (Onvio) ainda não implementada.")


def publicar_documento(caminho_arquivo, cliente_cnpj: str) -> dict:
    """Publica o documento no portal de documentos do Onvio para o cliente visualizar."""
    raise NotImplementedError("Publicação de documento no portal de documentos (Onvio) ainda não implementada.")


def buscar_solicitacoes_pendentes() -> list:
    """Usado pela Automação 1 (recebimento) para puxar demandas abertas no Portal Onvio."""
    raise NotImplementedError("Busca de solicitações pendentes no Onvio ainda não implementada.")


def enviar_email(destinatario: str, assunto: str, mensagem: str, anexo=None) -> dict:
    """
    Envio de e-mail com a mensagem padrão + instruções específicas por tipo de
    documento. Pode ser via API do Onvio, ou via SMTP direto (smtplib) — o que
    for mais prático no seu ambiente.
    """
    raise NotImplementedError("Envio de e-mail ainda não implementado.")
