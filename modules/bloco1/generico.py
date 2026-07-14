"""
modules/bloco1/generico.py
------------------------------
Recebimento genérico para qualquer tipo do Bloco 1 que não tenha um fluxo
próprio (férias e rescisão continuam usando modules/bloco1/recebimento.py,
que já é mais específico). Usa o schema de core/tipos_solicitacao.py pra
saber quais campos existem e qual função de regras/regras_clt.py chamar.
"""

from config import BLOCO_1
from core.solicitacao import Solicitacao
from core.tipos_solicitacao import schema_do_tipo
from core.workflow import StatusBloco1
from modules import dossie


def _aplicar_conferencia(sol: Solicitacao, tipo, dados_formulario, cliente_cnpj, ok, erros):
    """Roda a conferência automática contra o Dossiê (Cenário A/B) e grava o
    resultado na solicitação. Cenário B NUNCA bloqueia (só alerta o analista);
    Cenário A com inconsistência real (ex.: dias > saldo) volta pro cliente."""
    conf = dossie.conferir(tipo, dados_formulario, cliente_cnpj)
    if not conf:
        return ok, erros
    dados_conf = {"conferencia_cenario": conf["cenario"]}
    if conf.get("empregado_id"):
        dados_conf["conferencia_empregado_id"] = conf["empregado_id"]
    if conf.get("alerta"):
        dados_conf["conferencia_alerta"] = conf["alerta"]
        dados_conf["conferencia_pontos"] = conf.get("pontos_conferir", [])
    sol.atualizar_dados(dados_conf)
    if conf["cenario"] == "A" and conf["bloqueio_erros"]:
        return False, list(erros) + conf["bloqueio_erros"]
    return ok, erros


def criar_solicitacao_generica(tipo, cliente_cnpj, cliente_nome, funcionario_nome,
                                dados_formulario: dict, canal_origem="web"):
    """
    Cria a solicitação, roda a validação do schema (se houver) e já avança
    pro status certo — igual ao padrão de modules/bloco1/recebimento.py.
    """
    schema = schema_do_tipo(BLOCO_1, tipo)
    if schema is None:
        raise ValueError(f"Tipo '{tipo}' não está cadastrado no Bloco 1.")

    sol = Solicitacao.criar(
        bloco=BLOCO_1, tipo=tipo, canal_origem=canal_origem,
        cliente_cnpj=cliente_cnpj, cliente_nome=cliente_nome,
        funcionario_nome=funcionario_nome, dados=dados_formulario,
    )
    sol.avancar(StatusBloco1.TRIAGEM_IA)

    ok, erros = True, []
    validar = schema.get("validar")
    if validar:
        ok, erros, extra = validar(dados_formulario)
        if extra:
            sol.atualizar_dados(extra)

    ok, erros = _aplicar_conferencia(sol, tipo, dados_formulario, cliente_cnpj, ok, erros)

    sol.atualizar_dados({"triagem_erros": erros})

    if ok:
        sol.avancar(StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA)
    else:
        sol.avancar(StatusBloco1.AGUARDANDO_AJUSTE_CLIENTE)

    return sol, ok, erros


def atualizar_e_reenviar(sol: Solicitacao, dados_formulario: dict):
    """
    Reenvio de uma solicitação que o analista havia REPROVADO: o cliente corrigiu
    os campos e mandou de novo. Atualiza os dados, revalida pelo schema e devolve
    a solicitação para a fila de validação humana (mesma lógica da criação).
    """
    schema = schema_do_tipo(BLOCO_1, sol.tipo)
    if schema is None:
        raise ValueError(f"Tipo '{sol.tipo}' não está cadastrado no Bloco 1.")

    ok, erros = True, []
    validar = schema.get("validar")
    if validar:
        ok, erros, extra = validar(dados_formulario)
        if extra:
            dados_formulario = {**dados_formulario, **extra}

    # Zera o motivo da reprovação anterior e regrava os dados corrigidos.
    sol.atualizar_dados({**dados_formulario, "triagem_erros": erros, "motivo_reprovacao": None})
    ok, erros = _aplicar_conferencia(sol, sol.tipo, dados_formulario, sol.cliente_cnpj, ok, erros)
    sol.avancar(StatusBloco1.TRIAGEM_IA)  # sai de 'reprovada' (transição liberada no workflow)

    if ok:
        sol.avancar(StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA)
    else:
        sol.avancar(StatusBloco1.AGUARDANDO_AJUSTE_CLIENTE)

    return ok, erros
