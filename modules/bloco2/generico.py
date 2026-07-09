"""
modules/bloco2/generico.py
------------------------------
Recebimento genérico para qualquer tipo do Bloco 2 que não tenha um fluxo
próprio (admissão e atestado continuam com seus módulos dedicados). Usa o
schema de core/tipos_solicitacao.py pra validar os campos digitados no
formulário — os anexos aqui são opcionais (nem toda solicitação desse grupo
precisa de documento, ex: alteração de jornada não tem, mas afastamento por
INSS geralmente vem com atestado do INSS anexado).
"""

from config import BLOCO_2
from core.tipos_solicitacao import schema_do_tipo
from core.workflow import StatusBloco2
from modules.bloco2 import recebimento_anexo
from modules.bloco2.atestados import extensao_permitida
from utils import file_manager


def criar_solicitacao_generica(tipo, cliente_cnpj, cliente_nome, funcionario_nome,
                                dados_formulario: dict, arquivos=None, canal_origem="web"):
    """
    `arquivos` é uma lista opcional de tuplas (bytes, nome_original).
    Retorna (solicitacao, ok, erros).
    """
    schema = schema_do_tipo(BLOCO_2, tipo)
    if schema is None:
        raise ValueError(f"Tipo '{tipo}' não está cadastrado no Bloco 2.")

    sol = recebimento_anexo.criar_solicitacao_com_anexo(
        tipo=tipo, canal_origem=canal_origem,
        cliente_cnpj=cliente_cnpj, cliente_nome=cliente_nome, funcionario_nome=funcionario_nome,
    )
    sol.atualizar_dados(dados_formulario)

    arquivos_validos = [(b, nome) for b, nome in (arquivos or []) if nome and extensao_permitida(nome)]
    for arquivo_bytes, nome_original in arquivos_validos:
        caminho_destino = file_manager.salvar_anexo_recebido(tipo, sol.id, arquivo_bytes, nome_original)
        tipo_arquivo = caminho_destino.suffix.lstrip(".").lower() or None
        recebimento_anexo.anexar_arquivo(sol, str(caminho_destino), tipo_arquivo)

    if sol.status == StatusBloco2.RECEBIDA:
        # Não veio nenhum anexo — segue o fluxo mesmo assim (nem todo tipo do
        # Bloco 2 exige documento do cliente).
        sol.avancar(StatusBloco2.UPLOAD_VINCULADO, forcar=True)

    sol.avancar(StatusBloco2.EXTRACAO_IA)

    ok, erros = True, []
    validar = schema.get("validar")
    if validar:
        ok, erros, extra = validar(dados_formulario)
        if extra:
            sol.atualizar_dados(extra)

    sol.atualizar_dados({"extracao_erros": erros})
    sol.avancar(StatusBloco2.AGUARDANDO_APROVACAO_1)

    return sol, ok, erros


def atualizar_e_reenviar(sol, dados_formulario: dict, arquivos=None):
    """
    Reenvio de um tipo genérico do Bloco 2 que o analista havia REPROVADO: o
    cliente corrige os campos e/ou adiciona documentos e a solicitação volta
    para a 1ª aprovação. Documentos já vinculados permanecem (podem ser
    removidos separadamente).
    """
    schema = schema_do_tipo(BLOCO_2, sol.tipo)
    if schema is None:
        raise ValueError(f"Tipo '{sol.tipo}' não está cadastrado no Bloco 2.")

    sol.atualizar_dados({**dados_formulario, "motivo_reprovacao": None})

    arquivos_validos = [(b, nome) for b, nome in (arquivos or []) if nome and extensao_permitida(nome)]
    for arquivo_bytes, nome_original in arquivos_validos:
        caminho_destino = file_manager.salvar_anexo_recebido(sol.tipo, sol.id, arquivo_bytes, nome_original)
        tipo_arquivo = caminho_destino.suffix.lstrip(".").lower() or None
        recebimento_anexo.anexar_arquivo(sol, str(caminho_destino), tipo_arquivo)

    sol.avancar(StatusBloco2.EXTRACAO_IA)  # sai de 'reprovada' (transição liberada no workflow)

    ok, erros = True, []
    validar = schema.get("validar")
    if validar:
        ok, erros, extra = validar(dados_formulario)
        if extra:
            sol.atualizar_dados(extra)

    sol.atualizar_dados({"extracao_erros": erros})
    sol.avancar(StatusBloco2.AGUARDANDO_APROVACAO_1)

    return ok, erros
