"""
modules/bloco2/atestados.py
------------------------------
Primeiro módulo do Bloco 2 implementado de ponta a ponta (na medida do
combinado): recebimento do atestado em PDF ou imagem, e criação da
solicitação já pronta para entrar na fila de validação humana.

De propósito, este módulo ainda NÃO faz extração de dados nem validação de
regras — ele cobre só a "Automação 1" (recebimento) do Bloco 2 no
mapeamento de processos. Extração (OCR) e lançamento no Domínio ficam para
uma próxima etapa, quando fizer sentido evoluir esse módulo.
"""

from config import BLOCO_2
from core.solicitacao import Solicitacao
from core.workflow import StatusBloco2
from database import db_manager
from utils import file_manager

EXTENSOES_PERMITIDAS = {"pdf", "png", "jpg", "jpeg"}


def extensao_permitida(nome_arquivo: str) -> bool:
    return "." in nome_arquivo and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS


def criar_solicitacao_atestado(cliente_cnpj, cliente_nome, funcionario_nome,
                                arquivo_bytes: bytes, nome_arquivo_original: str,
                                canal_origem="web", observacoes=None,
                                expectativa_conclusao=None) -> Solicitacao:
    """
    Cria a solicitação de lançamento de atestado, salva o arquivo recebido
    (PDF ou imagem) e deixa tudo pronto na fila de validação — sem tentar
    extrair dados ou processar ainda.

    Levanta ValueError se a extensão do arquivo não for permitida.
    """
    if not extensao_permitida(nome_arquivo_original):
        raise ValueError(
            f"Extensão não permitida. Envie um arquivo PDF, PNG ou JPG (recebido: {nome_arquivo_original})"
        )

    sol = Solicitacao.criar(
        bloco=BLOCO_2,
        tipo="atestado",
        canal_origem=canal_origem,
        cliente_cnpj=cliente_cnpj,
        cliente_nome=cliente_nome,
        funcionario_nome=funcionario_nome,
        dados={k: v for k, v in {"observacoes": observacoes,
                                 "expectativa_conclusao": expectativa_conclusao}.items() if v},
    )

    caminho_destino = file_manager.salvar_anexo_recebido("atestados", sol.id, arquivo_bytes, nome_arquivo_original)
    tipo_arquivo = caminho_destino.suffix.lstrip(".").lower() or None
    db_manager.adicionar_anexo(sol.id, str(caminho_destino), tipo_arquivo)

    # Avança o status até "aguardando 1ª aprovação" sem rodar extração de
    # verdade (esse passo do fluxo ainda não está implementado para atestados).
    sol.avancar(StatusBloco2.UPLOAD_VINCULADO)
    sol.avancar(StatusBloco2.EXTRACAO_IA)
    sol.avancar(StatusBloco2.AGUARDANDO_APROVACAO_1)

    return sol


def atualizar_e_reenviar_atestado(sol: Solicitacao, observacoes=None,
                                  arquivo_bytes: bytes = None, nome_arquivo_original: str = None):
    """
    Reenvio de um atestado que o analista havia REPROVADO: o cliente ajusta as
    observações e/ou anexa um novo documento e manda de volta para a fila de
    1ª aprovação. Os anexos anteriores continuam vinculados (podem ser
    removidos separadamente).
    """
    novos = {"motivo_reprovacao": None}
    if observacoes is not None:
        novos["observacoes"] = observacoes
    sol.atualizar_dados(novos)

    if arquivo_bytes and nome_arquivo_original:
        if not extensao_permitida(nome_arquivo_original):
            raise ValueError("Extensão não permitida. Envie um arquivo PDF, PNG ou JPG.")
        caminho = file_manager.salvar_anexo_recebido("atestados", sol.id, arquivo_bytes, nome_arquivo_original)
        db_manager.adicionar_anexo(sol.id, str(caminho), caminho.suffix.lstrip(".").lower() or None)

    sol.avancar(StatusBloco2.AGUARDANDO_APROVACAO_1)  # sai de 'reprovada' (transição liberada)
    return True
