"""
modules/bloco1/distribuicao.py
--------------------------------
Automação 3 do Bloco 1: depois que o Domínio gera os PDFs, eles aguardam
validação humana. Assim que aprovados, a automação executa os 4 passos:
1. Salva o documento na pasta correta do servidor.
2. Anexa o arquivo na própria solicitação do portal do cliente.
3. Publica o documento no portal de documentos do Onvio.
4. Envia por e-mail com mensagem padrão (com instruções específicas por tipo de documento).
"""

from core.solicitacao import Solicitacao
from core.workflow import StatusBloco1
from integracao import onvio_api
from utils import file_manager

MENSAGENS_PADRAO = {
    "admissao": (
        "Segue documentação de admissão. O funcionário deve preencher os "
        "papéis antes de iniciar e a empresa deve arquivá-los."
    ),
    "ferias": "Segue o aviso/recibo de férias referente à solicitação.",
    "rescisao": "Segue o TRCT e demais documentos da rescisão.",
}
MENSAGEM_PADRAO_GENERICA = "Segue documento referente à sua solicitação."


def aprovar_relatorio_para_distribuicao(solicitacao: Solicitacao, aprovado: bool,
                                         aprovado_por: str, comentario=None):
    solicitacao.validar("aprovacao_distribuicao", aprovado, aprovado_por=aprovado_por, comentario=comentario)
    if aprovado:
        solicitacao.avancar(StatusBloco1.DISTRIBUINDO)
        return distribuir(solicitacao)
    return False


def distribuir(solicitacao: Solicitacao):
    """Executa os 4 passos pós-validação humana."""
    dados = solicitacao.dados
    caminho_pdf = dados.get("caminho_relatorio_gerado")

    if not caminho_pdf:
        solicitacao.registrar_erro("distribuicao", "Nenhum caminho de relatório gerado encontrado nos dados.")
        return False

    # 1. Salva na pasta do servidor
    destino = file_manager.salvar_no_servidor(
        caminho_pdf, cliente=solicitacao._row.get("cliente_nome"), tipo=solicitacao.tipo
    )

    # 2. Anexa na solicitação do portal do cliente
    onvio_api.anexar_na_solicitacao_portal(solicitacao.id, destino)

    # 3. Publica no portal de documentos do Onvio
    onvio_api.publicar_documento(destino, cliente_cnpj=solicitacao._row.get("cliente_cnpj"))

    # 4. Envia por e-mail com mensagem padrão
    mensagem = MENSAGENS_PADRAO.get(solicitacao.tipo, MENSAGEM_PADRAO_GENERICA)
    onvio_api.enviar_email(
        destinatario=dados.get("email_cliente"),
        assunto=f"Documento referente à sua solicitação - {solicitacao.tipo}",
        mensagem=mensagem,
        anexo=destino,
    )

    solicitacao.atualizar_dados({"caminho_final": str(destino)})
    solicitacao.avancar(StatusBloco1.CONCLUIDA)
    return True
