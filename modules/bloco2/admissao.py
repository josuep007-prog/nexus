"""
modules/bloco2/admissao.py
------------------------------
Segundo módulo do Bloco 2 implementado de ponta a ponta: recebimento de
admissão com MÚLTIPLOS documentos (RG, CTPS, comprovante de residência,
dados bancários etc.) numa mesma solicitação, seguido de extração
automática dos dados e validação das regras CLT.

Diferente do módulo de atestados (que só recebe o arquivo), aqui o fluxo
completo da "Automação 1" do Bloco 2 já roda: recebimento -> extração -> 1ª
aprovação. A extração e as regras já existiam (modules/bloco2/extracao.py e
regras/regras_clt.py) — este módulo é a "cola" que junta várias anexos numa
solicitação só e aciona esse pipeline.
"""

from modules.bloco2.atestados import extensao_permitida
from modules.bloco2 import recebimento_anexo
from utils import file_manager


def criar_solicitacao_admissao(cliente_cnpj, cliente_nome, funcionario_nome,
                                arquivos, canal_origem="web", observacoes=None,
                                cargo=None, departamento=None, data_admissao=None,
                                salario=None, horario_trabalho=None,
                                expectativa_conclusao=None):
    """
    Cria a solicitação de admissão, salva todos os documentos enviados,
    roda a extração automática e a validação das regras CLT.

    `arquivos` é uma lista de tuplas (bytes_do_arquivo, nome_original).

    `cargo`, `departamento`, `data_admissao`, `salario` e `horario_trabalho`
    são dados cadastrais/contratuais que dependem do cliente (não do
    documento do funcionário) — por isso são preenchidos manualmente no
    formulário, em vez de esperar a extração OCR dos anexos (que cobre só os
    dados pessoais do funcionário: nome, CPF, PIS, data de nascimento etc.).

    Levanta ValueError se nenhum arquivo válido for enviado.
    Retorna (solicitacao, ok, erros) — `ok` indica se passou pela extração/
    validação sem pendências, `erros` é a lista de pendências encontradas
    (campos faltando, CPF inválido etc.) para o analista revisar na 1ª aprovação.
    """
    arquivos_validos = [(b, nome) for b, nome in arquivos if nome and extensao_permitida(nome)]
    if not arquivos_validos:
        raise ValueError("Envie ao menos um arquivo válido (PDF, PNG ou JPG).")

    sol = recebimento_anexo.criar_solicitacao_com_anexo(
        tipo="admissao",
        canal_origem=canal_origem,
        cliente_cnpj=cliente_cnpj,
        cliente_nome=cliente_nome,
        funcionario_nome=funcionario_nome,
    )
    if observacoes:
        sol.atualizar_dados({"observacoes": observacoes})

    dados_cadastrais = {
        "cargo": cargo,
        "departamento": departamento,
        "data_admissao": data_admissao,
        "salario": salario,
        "horario_trabalho": horario_trabalho,
        "expectativa_conclusao": expectativa_conclusao,
    }
    sol.atualizar_dados({k: v for k, v in dados_cadastrais.items() if v})

    for arquivo_bytes, nome_original in arquivos_validos:
        caminho_destino = file_manager.salvar_anexo_recebido("admissoes", sol.id, arquivo_bytes, nome_original)
        tipo_arquivo = caminho_destino.suffix.lstrip(".").lower() or None
        recebimento_anexo.anexar_arquivo(sol, str(caminho_destino), tipo_arquivo)

    ok, erros = recebimento_anexo.extrair_e_validar(sol)
    return sol, ok, erros


def atualizar_e_reenviar_admissao(sol, arquivos=None, cargo=None, departamento=None,
                                  data_admissao=None, salario=None, horario_trabalho=None,
                                  observacoes=None):
    """
    Reenvio de uma admissão que o analista havia REPROVADO: o cliente corrige os
    dados cadastrais/contratuais e/ou anexa novos documentos, e a solicitação
    roda de novo a extração + validação, voltando para a 1ª aprovação.

    `arquivos` é uma lista de tuplas (bytes, nome_original) — os documentos que
    já estavam vinculados permanecem (podem ser removidos separadamente).
    """
    campos = {
        "cargo": cargo, "departamento": departamento, "data_admissao": data_admissao,
        "salario": salario, "horario_trabalho": horario_trabalho,
    }
    dados = {k: v for k, v in campos.items() if v}
    dados["motivo_reprovacao"] = None
    if observacoes is not None:
        dados["observacoes"] = observacoes
    sol.atualizar_dados(dados)

    for arquivo_bytes, nome_original in (arquivos or []):
        if nome_original and extensao_permitida(nome_original):
            caminho = file_manager.salvar_anexo_recebido("admissoes", sol.id, arquivo_bytes, nome_original)
            tipo_arquivo = caminho.suffix.lstrip(".").lower() or None
            recebimento_anexo.anexar_arquivo(sol, str(caminho), tipo_arquivo)

    # Reprocessa extração + validação sobre TODOS os anexos (antigos + novos).
    ok, erros = recebimento_anexo.extrair_e_validar(sol)
    return ok, erros
