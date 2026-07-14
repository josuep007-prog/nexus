"""
integracao/onvio_sync.py
-------------------------
Sincronização do Dossiê do Empregado a partir do Onvio — STUB proposital.

O nexus deve consumir os dados de empregados do Onvio para alimentar/atualizar
o dossiê local (modules/dossie.py + tabelas `empregados`/`empregado_historico`).
Porém, como levantado em docs/onvio_referencia.md, o Onvio NÃO expõe uma API
pública para os dados de DP — a única entrada é a interface web. Então esta
sincronização depende de acesso real ao Onvio (automação de navegador com o
usuário do escritório) e por isso ainda não está implementada.

O contrato já está definido: quando plugado, cada empregado lido do Onvio deve
ser gravado via `database.db_manager.sincronizar_empregado(cliente_cnpj, cpf,
dados, origem_dados="onvio")`, com o mesmo dicionário de campos que o dossiê
entende. Assim, o resto do sistema (conferência A/B) funciona igual, venha o
dado da massa de teste, de uma solicitação processada ou do Onvio.
"""

from database import db_manager


def sincronizar_empregados(cliente_cnpj=None):
    """Puxa empregados do Onvio e atualiza o dossiê. Ainda não implementado."""
    raise NotImplementedError(
        "Sincronização do Onvio ainda não implementada: depende de acesso ao "
        "Onvio (automação de navegador com o usuário do escritório). Quando "
        "disponível, gravar cada empregado com db_manager.sincronizar_empregado(..., origem_dados='onvio')."
    )


def aplicar_empregado_do_onvio(cliente_cnpj, cpf, dados: dict):
    """
    Ponto de entrada único para persistir UM empregado vindo do Onvio no dossiê.
    Já funciona: recebe o dicionário de dados normalizado e grava. É isso que a
    automação de navegador deve chamar por empregado, quando existir.
    """
    return db_manager.sincronizar_empregado(cliente_cnpj, cpf, dados, origem_dados="onvio")
