"""
modules/rotinas/monitor_instabilidade.py
-------------------------------------------
Gera alertas na interface sobre quedas ou oscilações em sistemas parceiros
(eSocial, Domínio, portais governamentais).

A verificação de "sistema fora do ar" pode ser feita de duas formas:
1. Ping HTTP simples nas páginas de status oficiais (quando existem).
2. Detecção indireta: se X automações falharem seguidas ao tentar
   acessar o mesmo sistema, provavelmente ele está instável (mais confiável
   que depender de página de status, que às vezes não é atualizada a tempo).

Este stub implementa a abordagem 1 de forma simples; a abordagem 2 pode ser
plugada aproveitando a tabela `log_erros` do banco (agrupando por módulo/janela de tempo).
"""

import requests

from database import db_manager

SISTEMAS_MONITORADOS = {
    # nome amigável -> URL de status/healthcheck (ajustar para URLs reais quando disponíveis)
    "esocial": "https://login.esocial.gov.br/",
    "portal_onvio": "https://onvio.com.br/",
}

TIMEOUT_SEGUNDOS = 10


def verificar_status_sistemas():
    resultados = {}
    for nome, url in SISTEMAS_MONITORADOS.items():
        try:
            resp = requests.get(url, timeout=TIMEOUT_SEGUNDOS)
            resultados[nome] = "ok" if resp.status_code < 500 else "instavel"
        except requests.RequestException as exc:
            resultados[nome] = "fora_do_ar"
            db_manager.registrar_erro("monitor_instabilidade", f"{nome} inacessível: {exc}")
    return resultados


def detectar_instabilidade_por_falhas_repetidas(modulo: str, janela_minutos=30, limite_falhas=3):
    """
    Abordagem 2: se houver `limite_falhas` ou mais erros do mesmo módulo em
    uma janela curta de tempo, provavelmente é instabilidade do sistema
    parceiro (e não um erro pontual de dados). Ainda não filtra por janela de
    tempo (precisa comparar timestamps) — próximo passo de refinamento.
    """
    erros_recentes = [e for e in db_manager.listar_erros(resolvido=False) if e["modulo"] == modulo]
    return len(erros_recentes) >= limite_falhas
