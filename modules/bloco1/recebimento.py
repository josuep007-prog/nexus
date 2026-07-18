"""
modules/bloco1/recebimento.py
------------------------------
Automação 1 do Bloco 1 (ver Mapeamento de Processos - DP):
Recebimento das solicitações sem anexo (férias, rescisões, alterações
cadastrais, relatórios de rotina, folhas sem variáveis).

Fluxo:
1. unificar_solicitacao()  -> centraliza a demanda (vinda de WhatsApp/e-mail/Onvio)
2. rodar_triagem()         -> aplica regras fixas de CLT/CCT
3. registrar_ajuste_cliente() -> se o cliente corrige algo sugerido pela triagem
4. validar_humanamente()   -> aprovação obrigatória do funcionário do escritório
"""

from config import BLOCO_1
from core.solicitacao import Solicitacao
from core.workflow import StatusBloco1
from regras import regras_clt, regras_cct


def unificar_solicitacao(tipo, canal_origem, cliente_cnpj, cliente_nome,
                          funcionario_nome=None, dados=None):
    """Centraliza uma demanda recebida por qualquer canal em uma solicitação única."""
    solicitacao = Solicitacao.criar(
        bloco=BLOCO_1,
        tipo=tipo,
        canal_origem=canal_origem,
        cliente_cnpj=cliente_cnpj,
        cliente_nome=cliente_nome,
        funcionario_nome=funcionario_nome,
        dados=dados,
    )
    solicitacao.avancar(StatusBloco1.TRIAGEM_IA)
    return solicitacao


def rodar_triagem(solicitacao: Solicitacao):
    """
    Aplica as regras fixas de CLT/CCT de acordo com o tipo da solicitação.
    Retorna (ok, erros) e já move o status conforme o resultado:
      - se ok=True  -> AGUARDANDO_VALIDACAO_HUMANA
      - se ok=False -> AGUARDANDO_AJUSTE_CLIENTE
    """
    dados = solicitacao.dados
    ok, erros = True, []

    if solicitacao.tipo == "ferias":
        ok, erros = regras_clt.validar_ferias(
            dias_solicitados=dados.get("dias_solicitados", 0),
            saldo_dias_direito=dados.get("saldo_dias_direito", 30),
            periodos=dados.get("periodos"),
        )

    elif solicitacao.tipo == "rescisao":
        from datetime import date
        try:
            data_admissao = date.fromisoformat(dados["data_admissao"])
            data_demissao = date.fromisoformat(dados["data_demissao"])
            ok, erros, extra = regras_clt.validar_rescisao(
                dados.get("tipo_rescisao"), data_admissao, data_demissao
            )
            if extra.get("dias_aviso_previo_estimado") is not None:
                solicitacao.atualizar_dados(extra)
        except (KeyError, ValueError):
            ok, erros = False, ["Datas de admissão/demissão ausentes ou em formato inválido (esperado AAAA-MM-DD)."]

    elif solicitacao.tipo == "alteracao_cadastral":
        # Regra mínima: precisa indicar o que está sendo alterado e o novo valor.
        if not dados.get("campo_alterado") or "novo_valor" not in dados:
            ok, erros = False, ["Informe 'campo_alterado' e 'novo_valor' para alterações cadastrais."]

    # Verificação de piso salarial da CCT quando aplicável (ex: alteração de salário)
    if solicitacao.tipo == "alteracao_cadastral" and dados.get("campo_alterado") == "salario":
        ok_cct, avisos_cct = regras_cct.validar_piso_salarial(
            solicitacao._row.get("cliente_cnpj"), dados.get("novo_valor", 0)
        )
        ok = ok and ok_cct
        erros += avisos_cct

    solicitacao.atualizar_dados({"triagem_erros": erros})

    if ok:
        solicitacao.avancar(StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA)
    else:
        solicitacao.avancar(StatusBloco1.AGUARDANDO_AJUSTE_CLIENTE)

    return ok, erros


def registrar_ajuste_cliente(solicitacao: Solicitacao, aceitou_sugestao: bool, dados_corrigidos=None):
    """
    Cliente responde à triagem: ou aceita a sugestão e corrige, ou envia mesmo
    assim com as inconsistências (que serão avaliadas pelo analista na validação humana).
    """
    if aceitou_sugestao and dados_corrigidos:
        solicitacao.atualizar_dados(dados_corrigidos)
        solicitacao.avancar(StatusBloco1.TRIAGEM_IA)
        return rodar_triagem(solicitacao)
    else:
        solicitacao.avancar(StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA)
        return None


def validar_humanamente(solicitacao: Solicitacao, aprovado: bool, aprovado_por: str,
                        comentario=None, modo="onvio"):
    """
    Validação humana obrigatória — TODA solicitação passa por aqui antes de
    ser processada, esteja ela 100% correta ou com inconsistências.

    Ao aprovar, a solicitação segue para o trabalho do escritório:
    - modo="onvio"  -> repasse ao Onvio (o analista lança lá, com o de-para
      pronto na tela de repasse; o Onvio pré-preenche o Domínio depois)
    - modo="manual" -> tipos sem equivalente no Onvio (CND, declaração, PPP...),
      resolvidos direto pelo escritório
    """
    from core.workflow import AGUARDANDO_REPASSE_ONVIO, EM_ATENDIMENTO_MANUAL
    solicitacao.validar("triagem", aprovado, aprovado_por=aprovado_por, comentario=comentario)
    if aprovado:
        solicitacao.atualizar_dados({"modo_processamento": modo})
        solicitacao.avancar(AGUARDANDO_REPASSE_ONVIO if modo == "onvio" else EM_ATENDIMENTO_MANUAL)
    return aprovado
