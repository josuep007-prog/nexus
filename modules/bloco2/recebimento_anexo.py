"""
modules/bloco2/recebimento_anexo.py
--------------------------------------
Automação 1 do Bloco 2 (solicitações COM anexo: folha com variáveis,
admissões, afastamentos).

Fluxo:
1. criar_solicitacao_com_anexo() -> cliente anexa arquivo(s) e vincula a uma solicitação
2. extrair_e_validar()           -> chama modules/bloco2/extracao.py (OCR/parsing) + regras CLT/CCT
3. aprovacao_1() / aprovacao_2() / aprovacao_3() -> tríplice validação humana
"""

from config import BLOCO_2
from core.solicitacao import Solicitacao
from core.workflow import StatusBloco2
from database import db_manager
from modules.bloco2 import extracao
from regras import regras_clt, regras_cct


def criar_solicitacao_com_anexo(tipo, canal_origem, cliente_cnpj, cliente_nome,
                                 funcionario_nome=None):
    """Cria a solicitação vazia. Os anexos são vinculados em seguida com anexar_arquivo()."""
    solicitacao = Solicitacao.criar(
        bloco=BLOCO_2,
        tipo=tipo,
        canal_origem=canal_origem,
        cliente_cnpj=cliente_cnpj,
        cliente_nome=cliente_nome,
        funcionario_nome=funcionario_nome,
    )
    return solicitacao


def anexar_arquivo(solicitacao: Solicitacao, caminho_arquivo: str, tipo_arquivo: str = None):
    anexo_id = db_manager.adicionar_anexo(solicitacao.id, caminho_arquivo, tipo_arquivo)
    if solicitacao.status == StatusBloco2.RECEBIDA:
        solicitacao.avancar(StatusBloco2.UPLOAD_VINCULADO)
    return anexo_id


def extrair_e_validar(solicitacao: Solicitacao):
    """
    Roda a extração (OCR/parsing) de cada anexo e aplica as regras fixas de
    CLT/CCT sobre os dados extraídos. Deixa tudo pronto para a 1ª aprovação
    humana revisar.
    """
    solicitacao.avancar(StatusBloco2.EXTRACAO_IA)

    dados_extraidos_total = {}
    erros_totais = []

    for anexo in solicitacao.anexos():
        try:
            dados = extracao.extrair_dados(anexo["caminho_arquivo"], solicitacao.tipo)
            db_manager.salvar_dados_extraidos(anexo["id"], dados)  # guarda com diagnóstico
            diagnostico = dados.pop("_diagnostico", {})
            # Só o que a extração conseguiu validar vira dado da solicitação;
            # o resto vira PENDÊNCIA explícita para o analista conferir na mão.
            dados_extraidos_total.update(dados)
            if diagnostico.get("falha_leitura") == extracao.PDF_SEM_TEXTO:
                erros_totais.append(
                    f"Anexo {anexo['id']}: PDF sem camada de texto (documento escaneado) — "
                    "nada pôde ser extraído automaticamente; confira na mão.")
            elif diagnostico.get("falha_leitura") == extracao.SEM_OCR:
                erros_totais.append(
                    f"Anexo {anexo['id']}: é uma imagem e o OCR (Tesseract) não está "
                    "instalado neste servidor — confira na mão.")
            elif diagnostico.get("falha_leitura") == extracao.SEM_BIBLIOTECA:
                erros_totais.append(
                    f"Anexo {anexo['id']}: leitura automática indisponível neste ambiente "
                    "(biblioteca de PDF/imagem não instalada) — confira na mão.")
            for campo, motivo in (diagnostico.get("recusados") or {}).items():
                erros_totais.append(f"'{campo}' encontrado mas não aceito: {motivo}.")
        except NotImplementedError:
            erros_totais.append(f"Extração ainda não implementada para tipo '{solicitacao.tipo}'.")
        except Exception as exc:  # noqa: BLE001
            erros_totais.append(f"Falha ao extrair anexo {anexo['id']}: {exc}")

    ok = True
    if solicitacao.tipo == "admissao":
        # Valida contra o dado completo (o que já estava salvo — ex: cargo/salário
        # preenchidos manualmente no formulário — mesclado com o que a extração
        # OCR achou agora), não só o que essa extração encontrou sozinha.
        dados_completos = {**solicitacao.dados, **dados_extraidos_total}
        ok, erros = regras_clt.validar_admissao_dados_minimos(dados_completos)
        erros_totais += erros
        if dados_completos.get("cpf") and not regras_clt.validar_cpf(dados_completos["cpf"]):
            erros_totais.append("CPF extraído não é válido (dígito verificador incorreto).")
            ok = False
        if dados_completos.get("salario"):
            ok_cct, avisos_cct = regras_cct.validar_piso_salarial(
                solicitacao._row.get("cliente_cnpj"), dados_completos["salario"]
            )
            ok = ok and ok_cct
            erros_totais += avisos_cct

    solicitacao.atualizar_dados({**dados_extraidos_total, "extracao_erros": erros_totais})
    solicitacao.avancar(StatusBloco2.AGUARDANDO_APROVACAO_1)
    return ok, erros_totais


def aprovacao_1_revisar_dados(solicitacao: Solicitacao, aprovado: bool, aprovado_por: str,
                              comentario=None, modo="onvio"):
    """1ª aprovação: funcionário revisa os dados extraídos e libera o trabalho.

    Ao aprovar, escolhe o caminho: modo="onvio" (repassar ao Onvio, que depois
    pré-preenche o Domínio) ou modo="manual" (tipos sem equivalente no Onvio,
    resolvidos direto pelo escritório).
    """
    from core.workflow import AGUARDANDO_REPASSE_ONVIO, EM_ATENDIMENTO_MANUAL
    solicitacao.validar("aprovacao_1", aprovado, aprovado_por=aprovado_por, comentario=comentario)
    if aprovado:
        solicitacao.atualizar_dados({"modo_processamento": modo})
        solicitacao.avancar(AGUARDANDO_REPASSE_ONVIO if modo == "onvio" else EM_ATENDIMENTO_MANUAL)
    return aprovado


def aprovacao_2_autorizar_processamento(solicitacao: Solicitacao, aprovado: bool, aprovado_por: str, comentario=None):
    """2ª aprovação: autoriza salvar, processar (cálculos) e gerar relatórios."""
    solicitacao.validar("aprovacao_2", aprovado, aprovado_por=aprovado_por, comentario=comentario)
    if aprovado:
        solicitacao.avancar(StatusBloco2.AGUARDANDO_APROVACAO_2)
    return aprovado


def aprovacao_3_liberar_envio(solicitacao: Solicitacao, aprovado: bool, aprovado_por: str, comentario=None):
    """3ª aprovação: revisa os relatórios gerados e dá aval final para o envio ao cliente."""
    solicitacao.validar("aprovacao_3", aprovado, aprovado_por=aprovado_por, comentario=comentario)
    if aprovado:
        solicitacao.avancar(StatusBloco2.AGUARDANDO_APROVACAO_3)
    return aprovado
