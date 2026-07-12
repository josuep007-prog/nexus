"""
web/app.py
-----------
Versão web do sistema, pra testar em qualquer navegador sem precisar do
PyQt5 instalado. Reaproveita 100% da lógica de negócio já existente
(core/, database/, modules/, regras/) — só troca a "casca" (interface).

Rodar com:
    cd dp_automacao
    python web/app.py

Abre em http://localhost:5000
"""

import csv
import io
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

# Garante que a raiz do projeto (dp_automacao/) está no sys.path,
# já que este arquivo mora em dp_automacao/web/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_file, abort, Response,
    session, g, jsonify
)

import config
from config import BLOCO_1, BLOCO_2, TIPOS_BLOCO_2
from database.db_manager import inicializar_banco
from database import db_manager
from core.solicitacao import Solicitacao
from core.usuario import (
    Usuario, TIPO_FUNCIONARIO, TIPO_CLIENTE, TIPO_GESTOR, TIPO_ADMIN,
    TIPOS_ESCRITORIO, NIVEL_FUNCIONARIO, NIVEL_GESTOR, NIVEL_ADMIN, ROTULO_PAPEL,
)
from core.workflow import StatusBloco1, StatusBloco2, REPROVADA
from core.tipos_solicitacao import schema_do_tipo, catalogo_completo, catalogo_por_categoria
from modules.bloco1 import recebimento as bloco1_recebimento
from modules.bloco1 import distribuicao as bloco1_distribuicao
from modules.bloco1 import generico as bloco1_generico
from modules.bloco2 import recebimento_anexo as bloco2_recebimento
from modules.bloco2 import atestados as bloco2_atestados
from modules.bloco2 import admissao as bloco2_admissao
from modules.bloco2 import generico as bloco2_generico
from modules import fila_processamento
from modules.rotinas import alertas as rotina_alertas
from core.workflow import NA_FILA_AUTOMACAO, EM_ATENDIMENTO_MANUAL, AGUARDANDO_ENTREGA
from utils import notificacoes, prazos
from utils import backup as backup_util

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-troque-em-producao")
# Limite global de upload (payload inteiro da requisição)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024

inicializar_banco()
backup_util.fazer_backup_diario()  # cópia diária do banco (com rotação) ao subir o app


# ---------------------------------------------------------------------------
# Autenticação: gate de login + controle de acesso por tipo de conta.
# Endpoints públicos não exigem login. Rotas só-funcionário ficam invisíveis
# (404) para contas do tipo cliente.
# ---------------------------------------------------------------------------
ROTAS_PUBLICAS = {"login", "manifest", "service_worker", "static"}

# Nível mínimo de acesso por rota (escada do escritório). Cliente (nível 0) não
# entra em nenhuma destas. Rotas fora do mapa exigem só estar logado.
#   1 = funcionário+  ·  2 = gestor+  ·  3 = admin
ROTAS_NIVEL_MINIMO = {
    # Operacional — qualquer um da equipe do escritório
    "validacoes": NIVEL_FUNCIONARIO, "decidir_validacao": NIVEL_FUNCIONARIO,
    "processamento": NIVEL_FUNCIONARIO, "concluir_manual": NIVEL_FUNCIONARIO,
    "alertas": NIVEL_FUNCIONARIO, "resolver_alerta": NIVEL_FUNCIONARIO,
    "obrigacoes": NIVEL_FUNCIONARIO, "marcar_obrigacao_web": NIVEL_FUNCIONARIO,
    # Gerencial — gestor e admin
    "relatorios": NIVEL_GESTOR,
    "usuarios": NIVEL_GESTOR, "criar_usuario_web": NIVEL_GESTOR,
    "alternar_usuario_ativo": NIVEL_GESTOR, "resetar_senha_usuario": NIVEL_GESTOR,
    "salvar_email_usuario": NIVEL_GESTOR, "adicionar_empresa": NIVEL_GESTOR,
    "remover_empresa": NIVEL_GESTOR,
}


# ---------------------------------------------------------------------------
# CSRF: token por sessão, exigido em todo POST (formulários têm um campo
# oculto _csrf; requisições fetch mandam o header X-CSRF).
# ---------------------------------------------------------------------------
def _token_csrf():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


@app.before_request
def proteger_csrf():
    if request.method != "POST":
        return
    token_sessao = session.get("_csrf")
    token_enviado = request.form.get("_csrf") or request.headers.get("X-CSRF")
    if not token_sessao or token_enviado != token_sessao:
        abort(400, "Token CSRF ausente ou inválido. Recarregue a página e tente de novo.")


@app.before_request
def exigir_login():
    if request.endpoint in ROTAS_PUBLICAS or request.endpoint is None:
        return
    if "usuario_id" not in session:
        return redirect(url_for("login", proximo=request.path))
    try:
        g.usuario = Usuario.carregar(session["usuario_id"])
    except ValueError:
        # Conta apagada/ID inválido na sessão: força novo login.
        session.clear()
        return redirect(url_for("login"))
    # Gate por nível: cada rota interna exige um nível mínimo. Quem não alcança
    # (cliente numa rota do escritório, funcionário numa rota gerencial) recebe
    # 404 — não revela a existência da rota.
    nivel_min = ROTAS_NIVEL_MINIMO.get(request.endpoint)
    if nivel_min and g.usuario.nivel < nivel_min:
        abort(404)


@app.context_processor
def injetar_usuario():
    return dict(usuario_logado=getattr(g, "usuario", None), csrf_token=_token_csrf)


@app.errorhandler(413)
def upload_grande_demais(_erro):
    flash(f"Arquivo grande demais — o limite é {config.MAX_UPLOAD_MB} MB por envio.", "erro")
    return redirect(request.referrer or url_for("solicitacoes"))


def _extensao_permitida_global(nome_arquivo):
    """Whitelist global de extensões (config.EXTENSOES_UPLOAD_PERMITIDAS)."""
    return ("." in nome_arquivo and
            nome_arquivo.rsplit(".", 1)[1].lower() in config.EXTENSOES_UPLOAD_PERMITIDAS)


def _filtrar_uploads(arquivos):
    """Separa uploads válidos dos rejeitados pela whitelist. -> (validos, nomes_rejeitados)"""
    validos, rejeitados = [], []
    for a in arquivos:
        (validos if _extensao_permitida_global(a.filename) else rejeitados).append(a)
    return validos, [a.filename for a in rejeitados]


# ---------------------------------------------------------------------------
# Proteção contra força bruta no login: N erros seguidos na janela bloqueiam
# novas tentativas por alguns minutos (por IP+login; em memória, por processo).
# ---------------------------------------------------------------------------
_tentativas_login = {}  # chave "ip|login" -> {"erros": [datetimes], "bloqueado_ate": datetime|None}


def _chave_login(login_informado):
    return f"{request.remote_addr}|{login_informado.lower()}"


def _login_bloqueado(login_informado):
    """Minutos restantes de bloqueio, ou 0 se pode tentar."""
    info = _tentativas_login.get(_chave_login(login_informado))
    if not info or not info.get("bloqueado_ate"):
        return 0
    restante = (info["bloqueado_ate"] - datetime.now()).total_seconds()
    if restante <= 0:
        _tentativas_login.pop(_chave_login(login_informado), None)
        return 0
    return max(1, int(restante // 60) + 1)


def _registrar_falha_login(login_informado):
    chave = _chave_login(login_informado)
    agora = datetime.now()
    info = _tentativas_login.setdefault(chave, {"erros": [], "bloqueado_ate": None})
    janela = agora - timedelta(minutes=config.LOGIN_JANELA_MINUTOS)
    info["erros"] = [t for t in info["erros"] if t > janela] + [agora]
    if len(info["erros"]) >= config.LOGIN_MAX_TENTATIVAS:
        info["bloqueado_ate"] = agora + timedelta(minutes=config.LOGIN_BLOQUEIO_MINUTOS)
        info["erros"] = []


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_informado = request.form.get("login", "").strip()
        senha = request.form.get("senha", "")
        minutos = _login_bloqueado(login_informado)
        if minutos:
            flash(f"Muitas tentativas erradas. Aguarde {minutos} min e tente novamente.", "erro")
            return render_template("login.html", form=request.form)
        usuario = Usuario.autenticar(login_informado, senha)
        if usuario is None:
            _registrar_falha_login(login_informado)
            flash("Login ou senha inválidos.", "erro")
            return render_template("login.html", form=request.form)
        _tentativas_login.pop(_chave_login(login_informado), None)
        session["usuario_id"] = usuario.id
        return redirect(request.args.get("proximo") or url_for("solicitacoes"))
    return render_template("login.html", form={})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# PWA: manifest e service worker precisam ser servidos na raiz (não em
# /static/) pra o service worker ter escopo sobre o site inteiro.
# ---------------------------------------------------------------------------
@app.route("/manifest.json")
def manifest():
    return send_file(
        Path(__file__).resolve().parent / "static" / "manifest.json",
        mimetype="application/manifest+json",
    )


@app.route("/sw.js")
def service_worker():
    resposta = send_file(
        Path(__file__).resolve().parent / "static" / "sw.js",
        mimetype="application/javascript",
    )
    resposta.headers["Service-Worker-Allowed"] = "/"
    resposta.headers["Cache-Control"] = "no-cache"
    return resposta

STATUS_AGUARDANDO_ACAO_HUMANA = [
    StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA,
    StatusBloco1.AGUARDANDO_APROVACAO_DISTRIBUICAO,
    StatusBloco2.AGUARDANDO_APROVACAO_1,
    StatusBloco2.AGUARDANDO_APROVACAO_2,
    StatusBloco2.AGUARDANDO_APROVACAO_3,
]

RÓTULOS_STATUS = {
    "recebida": "Recebida",
    "triagem_ia": "Em triagem",
    "aguardando_ajuste_cliente": "Aguardando ajuste do cliente",
    "aguardando_validacao_humana": "Aguardando validação",
    "aprovada_para_processamento": "Aprovada",
    "processando_dominio": "Processando no Domínio",
    "aguardando_esocial": "Aguardando eSocial",
    "erro_esocial": "Erro no eSocial",
    "relatorio_gerado": "Relatório gerado",
    "aguardando_aprovacao_distribuicao": "Aguardando aprovação p/ distribuição",
    "distribuindo": "Distribuindo",
    "concluida": "Concluída",
    "upload_vinculado": "Anexo recebido",
    "extracao_ia": "Extraindo dados",
    "aguardando_aprovacao_1": "Aguardando 1ª aprovação",
    "preenchendo_sistema": "Preenchendo sistema",
    "aguardando_aprovacao_2": "Aguardando 2ª aprovação",
    "processando": "Processando",
    "aguardando_aprovacao_3": "Aguardando 3ª aprovação (envio)",
    "erro": "Erro",
    "reprovada": "Reprovada — corrigir",
    "na_fila_automacao": "Na fila de automação",
    "em_atendimento_manual": "Em atendimento manual",
    "aguardando_entrega": "Processado — revisar e entregar",
}

RÓTULOS_TIPO = {tipo: schema["titulo"] for _, tipo, schema in catalogo_completo()}

# Rótulos amigáveis para as etapas registradas no histórico (tabela validacoes).
RÓTULOS_ETAPA = {
    "recebimento": "Solicitação criada",
    "reenvio": "Corrigida e reenviada",
    "triagem": "Validação",
    "aprovacao_1": "1ª aprovação",
    "aprovacao_2": "2ª aprovação",
    "aprovacao_3": "3ª aprovação",
    "distribuicao": "Distribuição",
    "correcao_esocial": "Correção (eSocial)",
    "processamento_automatico": "Processado pela automação",
    "processamento_manual": "Processado / entregue",
}
# Etapas que representam uma DECISÃO (aprovar/reprovar) — só nessas mostramos o
# selo Aprovado/Reprovado no histórico.
ETAPAS_DE_DECISAO = {"triagem", "aprovacao_1", "aprovacao_2", "aprovacao_3", "distribuicao", "correcao_esocial"}


def _ator(usuario):
    """String que identifica quem executou uma etapa, associada ao username (login)."""
    return f"{usuario.nome_exibicao} ({usuario.login})"


def _registrar_etapa(sol, etapa, comentario=None):
    """Registra no histórico quem (usuário logado) executou uma etapa do processo."""
    sol.validar(etapa, True, aprovado_por=_ator(g.usuario), comentario=comentario)


def _automatizavel(sol):
    """Se o tipo permite a opção 'Aprovar e automatizar' (ex.: 'outros' é só manual)."""
    schema = schema_do_tipo(sol.bloco, sol.tipo)
    return bool(schema) and schema.get("automatizavel", True)


# Agrupamento por SITUAÇÃO para o gráfico de rosca do painel (cores didáticas).
BUCKETS_GRAFICO = [
    {"key": "aguardando", "label": "Aguardando validação/aprovação", "cor": "var(--accent-amber)",
     "status": {"aguardando_validacao_humana", "aguardando_aprovacao_1", "aguardando_aprovacao_2",
                "aguardando_aprovacao_3", "aguardando_ajuste_cliente", "aguardando_aprovacao_distribuicao"}},
    {"key": "processamento", "label": "Em processamento / entrega", "cor": "var(--accent-blue)",
     "status": {"aprovada_para_processamento", "processando_dominio", "aguardando_esocial", "relatorio_gerado",
                "distribuindo", "preenchendo_sistema", "processando", "na_fila_automacao",
                "aguardando_entrega", "em_atendimento_manual"}},
    {"key": "reprovadas", "label": "Reprovadas / erro", "cor": "var(--accent-red)",
     "status": {"reprovada", "erro", "erro_esocial"}},
    {"key": "concluidas", "label": "Concluídas", "cor": "var(--accent-green)",
     "status": {"concluida"}},
    {"key": "recebidas", "label": "Recebidas / triagem", "cor": "var(--text-muted)",
     "status": {"recebida", "triagem_ia", "upload_vinculado", "extracao_ia"}},
]


def _bucket_status(status):
    for b in BUCKETS_GRAFICO:
        if status in b["status"]:
            return b["key"]
    return "recebidas"


@app.context_processor
def injetar_helpers():
    return dict(rotulo_status=lambda s: RÓTULOS_STATUS.get(s, s),
                rotulo_tipo=lambda t: RÓTULOS_TIPO.get(t, t),
                rotulo_etapa=lambda e: RÓTULOS_ETAPA.get(e, e),
                etapas_de_decisao=ETAPAS_DE_DECISAO,
                automatizavel=_automatizavel,
                bucket_status=_bucket_status,
                situacao_prazo=prazos.situacao_prazo,
                rotulo_prazo=prazos.rotulo_prazo)


def _cnpjs_do_usuario():
    """Filtro de posse: None p/ funcionário (vê tudo); lista de CNPJs p/ cliente."""
    return None if g.usuario.eh_funcionario else g.usuario.cnpjs


# ---------------------------------------------------------------------------
# Dashboard / Solicitações
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return redirect(url_for("solicitacoes"))


@app.route("/solicitacoes")
def solicitacoes():
    # Cliente só enxerga as próprias solicitações; funcionário vê todas.
    lista = Solicitacao.listar(cliente_cnpj=_cnpjs_do_usuario())

    # Ordem do painel: 1º as não finalizadas, 2º as concluídas que o cliente
    # ainda não abriu, 3º as concluídas já vistas. sorted() é estável, então
    # dentro de cada grupo a ordem por data (mais recentes primeiro) se mantém.
    def _ordem_painel(s):
        if s.status != "concluida":
            return 0
        return 2 if s.dados.get("visto_pelo_cliente") else 1
    lista = sorted(lista, key=_ordem_painel)

    total = len(lista)
    pendentes = len([s for s in lista if s.status in STATUS_AGUARDANDO_ACAO_HUMANA])
    concluidas = len([s for s in lista if s.status == "concluida"])
    # Alertas são visão interna do escritório — só fazem sentido para funcionário.
    alertas_pendentes = len(rotina_alertas.listar_alertas_pendentes()) if g.usuario.eh_funcionario else 0

    # Resumo por situação para o gráfico de rosca (só grupos com pelo menos 1).
    contagem = {}
    for s in lista:
        k = _bucket_status(s.status)
        contagem[k] = contagem.get(k, 0) + 1
    resumo_grafico = [
        {"key": b["key"], "label": b["label"], "cor": b["cor"], "count": contagem[b["key"]]}
        for b in BUCKETS_GRAFICO if contagem.get(b["key"], 0) > 0
    ]

    return render_template(
        "solicitacoes.html",
        solicitacoes=lista,
        resumo_grafico=resumo_grafico,
        stats=dict(total=total, pendentes=pendentes, concluidas=concluidas, alertas=alertas_pendentes),
    )


@app.route("/acompanhamento")
def acompanhamento():
    """Painel do cliente para acompanhar o status de cada solicitação, com
    prioridade: devolvidas p/ correção > novas entregas > em andamento > concluídas vistas."""
    todas = Solicitacao.listar(cliente_cnpj=_cnpjs_do_usuario())  # já vem por data (mais recentes 1º)

    devolvidas = [s for s in todas if s.status == "reprovada"]
    novas = [s for s in todas if s.status == "concluida" and not s.dados.get("visto_pelo_cliente")]
    andamento = [s for s in todas if s.status not in ("reprovada", "concluida")]
    concluidas = [s for s in todas if s.status == "concluida" and s.dados.get("visto_pelo_cliente")]

    return render_template("acompanhamento.html", devolvidas=devolvidas, novas=novas,
                           andamento=andamento, concluidas=concluidas, total=len(todas))


def _verificar_posse_ou_abortar(sol):
    """Aborta com 404 se o usuário logado for cliente e a solicitação não for dele.

    404 (não 403) de propósito: não confirma para o cliente que aquele ID existe.
    """
    if g.usuario.eh_cliente and not sol.pertence_a(g.usuario.cnpjs):
        abort(404)


def _dados_cliente_do_formulario():
    """Decide o par (cliente_cnpj, cliente_nome) de uma nova solicitação.

    Para contas cliente, o servidor IGNORA o que veio no formulário e usa os
    dados da própria conta logada — impede um cliente de abrir solicitação em
    nome de outra empresa (CNPJ de terceiros). Se a conta tem várias empresas
    (grupo econômico), aceita só um CNPJ que esteja na lista da conta.
    Funcionário digita livremente.
    """
    if g.usuario.eh_cliente:
        empresas = g.usuario.empresas()
        if len(empresas) > 1:
            escolhido = request.form.get("empresa_cnpj", "").strip()
            for e in empresas:
                if e["cnpj"] == escolhido:
                    return e["cnpj"], e["nome"]
        return g.usuario.cliente_cnpj, g.usuario.nome_exibicao
    return (request.form.get("cliente_cnpj", "").strip(),
            request.form.get("cliente_nome", "").strip())


@app.route("/solicitacoes/<int:solicitacao_id>")
def solicitacao_detalhe(solicitacao_id):
    try:
        sol = Solicitacao.carregar(solicitacao_id)
    except ValueError:
        abort(404)
    _verificar_posse_ou_abortar(sol)
    # Quando o CLIENTE dono abre uma solicitação já concluída, marca como vista
    # (para sair do destaque "concluída não visualizada" no painel).
    if g.usuario.eh_cliente and sol.status == "concluida" and not sol.dados.get("visto_pelo_cliente"):
        sol.atualizar_dados({"visto_pelo_cliente": True})
    return render_template(
        "solicitacao_detalhe.html",
        sol=sol,
        anexos=sol.anexos(),
        historico=sol.historico_validacoes(),
        comentarios=db_manager.listar_comentarios(sol.id),
        pode_editar=_pode_editar(sol),
    )


@app.route("/anexos/<int:anexo_id>/arquivo")
def anexo_arquivo(anexo_id):
    with db_manager.get_conn() as conn:
        row = conn.execute("SELECT * FROM anexos WHERE id = ?", (anexo_id,)).fetchone()
    if row is None:
        abort(404)
    # Checa posse pela solicitação-pai antes de servir o arquivo.
    try:
        sol = Solicitacao.carregar(row["solicitacao_id"])
    except ValueError:
        abort(404)
    _verificar_posse_ou_abortar(sol)
    caminho = Path(row["caminho_arquivo"])
    if not caminho.exists():
        abort(404)
    return send_file(caminho)


def _pode_editar(sol):
    """Quando reprovada, toda solicitação pode ser corrigida pelo cliente: os
    fluxos dedicados com anexos (admissão, atestado) e qualquer tipo de
    formulário (Bloco 1 ou Bloco 2 genérico)."""
    schema = schema_do_tipo(sol.bloco, sol.tipo)
    if schema is None:
        return False
    if schema.get("rota_especial") in ("nova_admissao", "novo_atestado"):
        return True
    return bool(schema.get("campos"))


@app.route("/solicitacoes/<int:solicitacao_id>/excluir", methods=["POST"])
def excluir_solicitacao(solicitacao_id):
    try:
        sol = Solicitacao.carregar(solicitacao_id)
    except ValueError:
        abort(404)
    _verificar_posse_ou_abortar(sol)
    if sol.status != REPROVADA:
        flash("Só é possível excluir uma solicitação que foi reprovada.", "erro")
        return redirect(url_for("solicitacao_detalhe", solicitacao_id=solicitacao_id))

    caminhos = db_manager.excluir_solicitacao(solicitacao_id)
    for caminho in caminhos:
        try:
            arq = Path(caminho)
            if arq.exists():
                arq.unlink()
        except OSError:
            pass  # arquivo já sumiu / sem permissão — o registro já foi removido do banco
    flash(f"Solicitação #{solicitacao_id} excluída.", "sucesso")
    return redirect(url_for("solicitacoes"))


@app.route("/anexos/<int:anexo_id>/excluir", methods=["POST"])
def excluir_anexo(anexo_id):
    row = db_manager.buscar_anexo(anexo_id)
    if row is None:
        abort(404)
    try:
        sol = Solicitacao.carregar(row["solicitacao_id"])
    except ValueError:
        abort(404)
    _verificar_posse_ou_abortar(sol)
    if sol.status != REPROVADA:
        flash("Só é possível remover documentos de uma solicitação reprovada.", "erro")
        return redirect(url_for("solicitacao_detalhe", solicitacao_id=sol.id))

    caminho = db_manager.excluir_anexo(anexo_id)
    if caminho:
        try:
            arq = Path(caminho)
            if arq.exists():
                arq.unlink()
        except OSError:
            pass
    flash("Documento removido.", "sucesso")
    return redirect(url_for("editar_solicitacao", solicitacao_id=sol.id))


def _editar_atestado(sol):
    """Edição de um atestado reprovado: ajusta observações e/ou anexa novo documento."""
    if request.method == "POST":
        observacoes = request.form.get("observacoes", "").strip()
        arquivo = request.files.get("arquivo")
        arquivo_bytes, nome = None, None
        if arquivo and arquivo.filename:
            if not bloco2_atestados.extensao_permitida(arquivo.filename):
                flash("Formato não suportado. Envie PDF, PNG ou JPG.", "erro")
                return _render_edicao_atestado(sol)
            arquivo_bytes, nome = arquivo.read(), arquivo.filename
        bloco2_atestados.atualizar_e_reenviar_atestado(
            sol, observacoes=observacoes or None,
            arquivo_bytes=arquivo_bytes, nome_arquivo_original=nome,
        )
        _registrar_etapa(sol, "reenvio")
        flash(f"Atestado #{sol.id} corrigido e reenviado para validação.", "sucesso")
        return redirect(url_for("solicitacao_detalhe", solicitacao_id=sol.id))
    return _render_edicao_atestado(sol)


def _render_edicao_atestado(sol):
    form = {**sol.dados, "funcionario_nome": sol._row.get("funcionario_nome") or ""}
    return render_template("novo_atestado.html", form=form, edicao_id=sol.id, anexos=sol.anexos())


def _editar_admissao(sol):
    """Edição de uma admissão reprovada: corrige os dados cadastrais e/ou os documentos."""
    if request.method == "POST":
        campos = {c: request.form.get(c, "").strip() for c in
                  ("cargo", "departamento", "data_admissao", "salario", "horario_trabalho")}
        observacoes = request.form.get("observacoes", "").strip()

        erros = [f"Informe {rot}." for c, rot in
                 [("cargo", "o cargo"), ("departamento", "o departamento"), ("data_admissao", "a data de admissão"),
                  ("salario", "o salário"), ("horario_trabalho", "o horário de trabalho")] if not campos[c]]
        arquivos_enviados = [a for a in request.files.getlist("arquivos") if a and a.filename]
        invalidos = [a.filename for a in arquivos_enviados if not bloco2_admissao.extensao_permitida(a.filename)]
        if invalidos:
            erros.append(f"Formato não suportado: {', '.join(invalidos)}. Envie PDF, PNG ou JPG.")
        if erros:
            for e in erros:
                flash(e, "erro")
            return _render_edicao_admissao(sol)

        arquivos = [(a.read(), a.filename) for a in arquivos_enviados]
        ok, erros_val = bloco2_admissao.atualizar_e_reenviar_admissao(
            sol, arquivos=arquivos, observacoes=observacoes or None, **campos)
        _registrar_etapa(sol, "reenvio")
        if ok:
            flash(f"Admissão #{sol.id} corrigida e reenviada — sem pendências.", "sucesso")
        else:
            flash(f"Admissão #{sol.id} reenviada, mas ainda com {len(erros_val)} pendência(s) — revise na 1ª aprovação.", "aviso")
        return redirect(url_for("solicitacao_detalhe", solicitacao_id=sol.id))
    return _render_edicao_admissao(sol)


def _render_edicao_admissao(sol):
    form = {**sol.dados, "funcionario_nome": sol._row.get("funcionario_nome") or ""}
    return render_template("novo_admissao.html", form=form, edicao_id=sol.id, anexos=sol.anexos())


@app.route("/solicitacoes/<int:solicitacao_id>/editar", methods=["GET", "POST"])
def editar_solicitacao(solicitacao_id):
    try:
        sol = Solicitacao.carregar(solicitacao_id)
    except ValueError:
        abort(404)
    _verificar_posse_ou_abortar(sol)
    if sol.status != REPROVADA or not _pode_editar(sol):
        abort(404)
    schema = schema_do_tipo(sol.bloco, sol.tipo)

    # Tipos com fluxo dedicado (anexos) têm formulário próprio de edição.
    rota = schema.get("rota_especial")
    if rota == "nova_admissao":
        return _editar_admissao(sol)
    if rota == "novo_atestado":
        return _editar_atestado(sol)

    if request.method == "POST":
        dados_formulario, erros = {}, []
        for campo in schema["campos"]:
            valor = request.form.get(campo["nome"], "").strip()
            if campo.get("obrigatorio") and not valor:
                erros.append(f"Campo obrigatório: {campo['rotulo']}")
            if valor:
                dados_formulario[campo["nome"]] = valor

        arquivos_enviados = [a for a in request.files.getlist("arquivos") if a and a.filename] if sol.bloco == BLOCO_2 else []
        arquivos_enviados, rejeitados = _filtrar_uploads(arquivos_enviados)
        if rejeitados:
            erros.append(f"Formato não permitido: {', '.join(rejeitados)}.")

        if erros:
            for e in erros:
                flash(e, "erro")
            return render_template("solicitacao_generica.html", bloco=sol.bloco, tipo=sol.tipo,
                                   schema=schema, form=request.form, edicao_id=solicitacao_id, anexos=sol.anexos())

        if sol.bloco == BLOCO_1:
            ok, erros_val = bloco1_generico.atualizar_e_reenviar(sol, dados_formulario)
        else:
            arquivos = [(a.read(), a.filename) for a in arquivos_enviados]
            ok, erros_val = bloco2_generico.atualizar_e_reenviar(sol, dados_formulario, arquivos=arquivos)

        _registrar_etapa(sol, "reenvio")

        if ok:
            flash(f"Solicitação #{sol.id} corrigida e reenviada para validação.", "sucesso")
        else:
            flash(f"Solicitação #{sol.id} reenviada, mas ainda com {len(erros_val)} pendência(s) — revise na validação.", "aviso")
        return redirect(url_for("solicitacao_detalhe", solicitacao_id=sol.id))

    # GET: formulário pré-preenchido com os dados atuais da solicitação.
    return render_template("solicitacao_generica.html", bloco=sol.bloco, tipo=sol.tipo,
                           schema=schema, form=sol.dados, edicao_id=solicitacao_id, anexos=sol.anexos())


# ---------------------------------------------------------------------------
# Novo Atestado (o módulo implementado nesta etapa)
# ---------------------------------------------------------------------------
@app.route("/atestados/novo", methods=["GET", "POST"])
def novo_atestado():
    if request.method == "POST":
        cliente_cnpj, cliente_nome = _dados_cliente_do_formulario()
        funcionario_nome = request.form.get("funcionario_nome", "").strip()
        observacoes = request.form.get("observacoes", "").strip()
        arquivo = request.files.get("arquivo")

        erros = []
        if not cliente_nome:
            erros.append("Informe o nome do cliente.")
        if not funcionario_nome:
            erros.append("Informe o nome do funcionário.")
        if not arquivo or arquivo.filename == "":
            erros.append("Selecione um arquivo (PDF, PNG ou JPG).")
        elif not bloco2_atestados.extensao_permitida(arquivo.filename):
            erros.append("Formato não suportado. Envie PDF, PNG ou JPG.")

        if erros:
            for e in erros:
                flash(e, "erro")
            return render_template("novo_atestado.html", form=request.form)

        sol = bloco2_atestados.criar_solicitacao_atestado(
            cliente_cnpj=cliente_cnpj or None,
            cliente_nome=cliente_nome,
            funcionario_nome=funcionario_nome,
            arquivo_bytes=arquivo.read(),
            nome_arquivo_original=arquivo.filename,
            canal_origem="web",
            observacoes=observacoes or None,
        )
        _registrar_etapa(sol, "recebimento")
        notificacoes.notificar_nova_solicitacao(sol, RÓTULOS_TIPO.get(sol.tipo))
        flash(f"Atestado recebido! Solicitação #{sol.id} criada e enviada para validação.", "sucesso")
        return redirect(url_for("solicitacao_detalhe", solicitacao_id=sol.id))

    return render_template("novo_atestado.html", form={})


# ---------------------------------------------------------------------------
# Nova Admissão (recebimento com múltiplos anexos + extração + validação CLT)
# ---------------------------------------------------------------------------
@app.route("/admissoes/novo", methods=["GET", "POST"])
def nova_admissao():
    if request.method == "POST":
        cliente_cnpj, cliente_nome = _dados_cliente_do_formulario()
        funcionario_nome = request.form.get("funcionario_nome", "").strip()
        observacoes = request.form.get("observacoes", "").strip()
        cargo = request.form.get("cargo", "").strip()
        departamento = request.form.get("departamento", "").strip()
        data_admissao = request.form.get("data_admissao", "").strip()
        salario = request.form.get("salario", "").strip()
        horario_trabalho = request.form.get("horario_trabalho", "").strip()
        arquivos_enviados = request.files.getlist("arquivos")

        erros = []
        if not cliente_nome:
            erros.append("Informe o nome do cliente.")
        if not funcionario_nome:
            erros.append("Informe o nome do funcionário.")
        if not cargo:
            erros.append("Informe o cargo.")
        if not departamento:
            erros.append("Informe o departamento/setor.")
        if not data_admissao:
            erros.append("Informe a data de admissão.")
        if not salario:
            erros.append("Informe o salário.")
        if not horario_trabalho:
            erros.append("Informe o horário de trabalho.")
        arquivos_enviados = [a for a in arquivos_enviados if a and a.filename]
        if not arquivos_enviados:
            erros.append("Selecione ao menos um documento (PDF, PNG ou JPG).")
        else:
            invalidos = [a.filename for a in arquivos_enviados if not bloco2_admissao.extensao_permitida(a.filename)]
            if invalidos:
                erros.append(f"Formato não suportado: {', '.join(invalidos)}. Envie PDF, PNG ou JPG.")

        if erros:
            for e in erros:
                flash(e, "erro")
            return render_template("novo_admissao.html", form=request.form)

        arquivos = [(a.read(), a.filename) for a in arquivos_enviados]
        sol, ok, erros_validacao = bloco2_admissao.criar_solicitacao_admissao(
            cliente_cnpj=cliente_cnpj or None,
            cliente_nome=cliente_nome,
            funcionario_nome=funcionario_nome,
            arquivos=arquivos,
            canal_origem="web",
            observacoes=observacoes or None,
            cargo=cargo,
            departamento=departamento,
            data_admissao=data_admissao,
            salario=salario,
            horario_trabalho=horario_trabalho,
        )
        _registrar_etapa(sol, "recebimento")
        notificacoes.notificar_nova_solicitacao(sol, RÓTULOS_TIPO.get(sol.tipo))

        if ok:
            flash(f"Admissão #{sol.id} recebida e validada automaticamente — sem pendências. Pronta para 1ª aprovação.", "sucesso")
        else:
            flash(f"Admissão #{sol.id} recebida, mas a extração encontrou {len(erros_validacao)} pendência(s) "
                  f"— revise na 1ª aprovação.", "aviso")
        return redirect(url_for("solicitacao_detalhe", solicitacao_id=sol.id))

    return render_template("novo_admissao.html", form={})


# ---------------------------------------------------------------------------
# Catálogo de solicitações + formulário genérico (demais tipos)
# ---------------------------------------------------------------------------
@app.route("/solicitacoes/nova")
def catalogo_solicitacoes():
    grupos = catalogo_por_categoria()
    return render_template("catalogo.html", grupos=grupos)


@app.route("/solicitacoes/nova/<bloco>/<tipo>", methods=["GET", "POST"])
def nova_solicitacao_generica(bloco, tipo):
    schema = schema_do_tipo(bloco, tipo)
    if schema is None:
        abort(404)

    # Tipos com fluxo próprio (admissão, atestado) redirecionam pra tela dedicada
    if schema.get("rota_especial"):
        return redirect(url_for(schema["rota_especial"]))

    if request.method == "POST":
        cliente_cnpj, cliente_nome = _dados_cliente_do_formulario()
        funcionario_nome = request.form.get("funcionario_nome", "").strip()

        erros = []
        if not cliente_nome:
            erros.append("Informe o nome do cliente.")

        dados_formulario = {}
        for campo in schema["campos"]:
            valor = request.form.get(campo["nome"], "").strip()
            if campo.get("obrigatorio") and not valor:
                erros.append(f"Campo obrigatório: {campo['rotulo']}")
            if valor:
                dados_formulario[campo["nome"]] = valor

        arquivos_enviados = [a for a in request.files.getlist("arquivos") if a and a.filename] if bloco == "bloco2" else []
        arquivos_enviados, rejeitados = _filtrar_uploads(arquivos_enviados)
        if rejeitados:
            erros.append(f"Formato não permitido: {', '.join(rejeitados)}.")

        if erros:
            for e in erros:
                flash(e, "erro")
            return render_template("solicitacao_generica.html", bloco=bloco, tipo=tipo, schema=schema, form=request.form)

        if bloco == BLOCO_1:
            sol, ok, erros_validacao = bloco1_generico.criar_solicitacao_generica(
                tipo=tipo, cliente_cnpj=cliente_cnpj or None, cliente_nome=cliente_nome,
                funcionario_nome=funcionario_nome or None, dados_formulario=dados_formulario, canal_origem="web",
            )
        else:
            arquivos = [(a.read(), a.filename) for a in arquivos_enviados]
            sol, ok, erros_validacao = bloco2_generico.criar_solicitacao_generica(
                tipo=tipo, cliente_cnpj=cliente_cnpj or None, cliente_nome=cliente_nome,
                funcionario_nome=funcionario_nome or None, dados_formulario=dados_formulario,
                arquivos=arquivos, canal_origem="web",
            )

        _registrar_etapa(sol, "recebimento")
        notificacoes.notificar_nova_solicitacao(sol, RÓTULOS_TIPO.get(sol.tipo))

        if ok:
            flash(f"Solicitação #{sol.id} ({schema['titulo']}) criada e enviada para validação.", "sucesso")
        else:
            flash(f"Solicitação #{sol.id} criada, mas com {len(erros_validacao)} pendência(s) — revise na validação.", "aviso")
        return redirect(url_for("solicitacao_detalhe", solicitacao_id=sol.id))

    return render_template("solicitacao_generica.html", bloco=bloco, tipo=tipo, schema=schema, form={})


# ---------------------------------------------------------------------------
# Validações (fila de aprovação humana)
# ---------------------------------------------------------------------------
@app.route("/validacoes")
def validacoes():
    fila = []
    for status in STATUS_AGUARDANDO_ACAO_HUMANA:
        fila.extend(Solicitacao.listar(status=status))
    fila.sort(key=lambda s: s.id)
    return render_template("validacoes.html", fila=fila)


@app.route("/validacoes/<int:solicitacao_id>/decidir", methods=["POST"])
def decidir_validacao(solicitacao_id):
    sol = Solicitacao.carregar(solicitacao_id)
    # decisao: "aprovar" | "aprovar_auto" | "aprovar_manual" | "reprovar"
    decisao = request.form.get("decisao")
    aprovado = decisao in ("aprovar", "aprovar_auto", "aprovar_manual")
    modo = "manual" if decisao == "aprovar_manual" else "automatico"
    # Tipos não-automatizáveis (ex.: 'outros') sempre vão para atendimento manual.
    if modo == "automatico" and not _automatizavel(sol):
        modo = "manual"
    # Quem aprovou/reprovou é o funcionário logado (não mais um campo livre).
    aprovado_por = _ator(g.usuario)
    comentario = request.form.get("comentario", "").strip() or None

    try:
        if sol.status == StatusBloco1.AGUARDANDO_VALIDACAO_HUMANA:
            bloco1_recebimento.validar_humanamente(sol, aprovado, aprovado_por, comentario, modo=modo)
        elif sol.status == StatusBloco1.AGUARDANDO_APROVACAO_DISTRIBUICAO:
            bloco1_distribuicao.aprovar_relatorio_para_distribuicao(sol, aprovado, aprovado_por, comentario)
        elif sol.status == StatusBloco2.AGUARDANDO_APROVACAO_1:
            bloco2_recebimento.aprovacao_1_revisar_dados(sol, aprovado, aprovado_por, comentario, modo=modo)
        elif sol.status == StatusBloco2.AGUARDANDO_APROVACAO_2:
            bloco2_recebimento.aprovacao_2_autorizar_processamento(sol, aprovado, aprovado_por, comentario)
        elif sol.status == StatusBloco2.AGUARDANDO_APROVACAO_3:
            bloco2_recebimento.aprovacao_3_liberar_envio(sol, aprovado, aprovado_por, comentario)
        else:
            sol.validar(sol.status, aprovado, aprovado_por, comentario)

        # Reprovado: volta pro cliente corrigir ou excluir (as funções acima só
        # avançam quando aprovado; na reprovação o status ainda é o de espera).
        if not aprovado and sol.status != REPROVADA:
            motivo = comentario or "Sem comentário do analista."
            sol.atualizar_dados({"motivo_reprovacao": motivo})
            sol.avancar(REPROVADA)
            notificacoes.notificar_reprovacao(sol, motivo, RÓTULOS_TIPO.get(sol.tipo))

        flash(f"Solicitação #{sol.id} {'aprovada' if aprovado else 'reprovada — devolvida ao cliente'}.", "sucesso")
    except NotImplementedError as exc:
        flash(f"Decisão registrada, mas o próximo passo depende de integração ainda não implementada: {exc}", "aviso")
    except Exception as exc:  # noqa: BLE001
        flash(f"Decisão registrada, mas houve um erro ao avançar o fluxo: {exc}", "aviso")

    return redirect(url_for("validacoes"))


# ---------------------------------------------------------------------------
# Processamento no Domínio (fila da automação + atendimento manual)
# ---------------------------------------------------------------------------
def _status_worker():
    """'online' | 'offline' | None (nunca rodou) — pelo heartbeat gravado pelo worker."""
    batida = db_manager.obter_valor_sistema("worker_heartbeat")
    if not batida:
        return None
    try:
        ultima = datetime.fromisoformat(batida)
    except ValueError:
        return None
    # Tolerância: 3 intervalos padrão do worker (10s) + folga → 60s.
    return "online" if datetime.now() - ultima < timedelta(seconds=60) else "offline"


@app.route("/processamento")
def processamento():
    fila_auto = sorted(Solicitacao.listar(status=NA_FILA_AUTOMACAO), key=lambda s: s.id)
    fila_entrega = sorted(Solicitacao.listar(status=AGUARDANDO_ENTREGA), key=lambda s: s.id)
    fila_manual = sorted(Solicitacao.listar(status=EM_ATENDIMENTO_MANUAL), key=lambda s: s.id)
    return render_template("processamento.html", fila_auto=fila_auto,
                           fila_entrega=fila_entrega, fila_manual=fila_manual,
                           worker_status=_status_worker())


@app.route("/solicitacoes/<int:solicitacao_id>/concluir-manual", methods=["POST"])
def concluir_manual(solicitacao_id):
    sol = Solicitacao.carregar(solicitacao_id)
    if sol.status not in (EM_ATENDIMENTO_MANUAL, AGUARDANDO_ENTREGA):
        flash("Esta solicitação não está pronta para entrega.", "erro")
        return redirect(url_for("processamento"))
    por = _ator(g.usuario)  # quem entregou é o funcionário logado
    resumo = request.form.get("resumo", "").strip() or None
    arquivos_enviados = [a for a in request.files.getlist("arquivos_resultado") if a and a.filename]
    arquivos_enviados, rejeitados = _filtrar_uploads(arquivos_enviados)
    if rejeitados:
        flash(f"Formato não permitido: {', '.join(rejeitados)}.", "erro")
        return redirect(url_for("processamento"))
    arquivos = [(a.read(), a.filename) for a in arquivos_enviados]
    try:
        fila_processamento.concluir_atendimento_manual(sol, por=por, resumo=resumo, arquivos=arquivos)
        notificacoes.notificar_entrega(sol, RÓTULOS_TIPO.get(sol.tipo))
        flash(f"Solicitação #{sol.id} concluída e entregue ao cliente.", "sucesso")
    except Exception as exc:  # noqa: BLE001
        flash(f"Não foi possível concluir: {exc}", "erro")
    return redirect(url_for("processamento"))


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------
@app.route("/alertas")
def alertas():
    # Gera (idempotente) os alertas de fim de experiência das admissões concluídas.
    prazos.gerar_alertas_experiencia()
    lista = rotina_alertas.listar_alertas_pendentes()
    return render_template("alertas.html", alertas=lista)


@app.route("/alertas/<int:alerta_id>/resolver", methods=["POST"])
def resolver_alerta(alerta_id):
    rotina_alertas.marcar_alerta_resolvido(alerta_id)
    flash("Alerta marcado como resolvido.", "sucesso")
    return redirect(url_for("alertas"))


# ---------------------------------------------------------------------------
# Comentários: conversa cliente <-> escritório dentro da solicitação
# ---------------------------------------------------------------------------
@app.route("/solicitacoes/<int:solicitacao_id>/comentar", methods=["POST"])
def comentar_solicitacao(solicitacao_id):
    try:
        sol = Solicitacao.carregar(solicitacao_id)
    except ValueError:
        abort(404)
    _verificar_posse_ou_abortar(sol)
    texto = request.form.get("texto", "").strip()
    if not texto:
        flash("Escreva a mensagem antes de enviar.", "erro")
    else:
        db_manager.adicionar_comentario(sol.id, _ator(g.usuario), g.usuario.tipo_conta, texto)
        notificacoes.notificar_comentario(sol, g.usuario.tipo_conta, texto, RÓTULOS_TIPO.get(sol.tipo))
        flash("Mensagem enviada.", "sucesso")
    return redirect(url_for("solicitacao_detalhe", solicitacao_id=sol.id) + "#comentarios")


# ---------------------------------------------------------------------------
# Minha conta: trocar senha, e-mail de notificação e ativar push
# ---------------------------------------------------------------------------
@app.route("/conta", methods=["GET", "POST"])
def conta():
    if request.method == "POST":
        acao = request.form.get("acao")
        if acao == "senha":
            try:
                g.usuario.alterar_senha(request.form.get("senha_atual", ""),
                                        request.form.get("senha_nova", ""))
                flash("Senha alterada com sucesso.", "sucesso")
            except ValueError as exc:
                flash(str(exc), "erro")
        elif acao == "email":
            email = request.form.get("email", "").strip()
            db_manager.atualizar_email_usuario(g.usuario.id, email)
            flash("E-mail de notificação atualizado.", "sucesso")
        return redirect(url_for("conta"))
    return render_template("conta.html",
                           push_configurado=notificacoes.push_configurado(),
                           email_configurado=notificacoes.email_configurado())


# ---------------------------------------------------------------------------
# Gestão de usuários pela web (só escritório) — substitui o uso diário do CLI
# ---------------------------------------------------------------------------
@app.route("/usuarios")
def usuarios():
    lista = [Usuario(u) for u in db_manager.listar_usuarios()]
    # Só o admin pode criar/gerir contas do ESCRITÓRIO; o gestor gere só clientes.
    return render_template("usuarios.html", usuarios=lista, pode_gerir_equipe=g.usuario.eh_admin)


def _gerir_conta_ou_abortar(alvo_row):
    """Bloqueia (404) se o usuário logado não pode gerir a conta-alvo.

    Gestor gere contas de cliente; contas do escritório só o admin mexe.
    """
    if alvo_row is None:
        abort(404)
    if not g.usuario.pode_gerir(alvo_row["tipo_conta"]):
        abort(404)


@app.route("/usuarios/criar", methods=["POST"])
def criar_usuario_web():
    login_novo = request.form.get("login", "").strip()
    senha = request.form.get("senha", "")
    tipo = request.form.get("tipo_conta", TIPO_CLIENTE)
    nome = request.form.get("nome_exibicao", "").strip()
    cnpj = request.form.get("cliente_cnpj", "").strip() or None
    email = request.form.get("email", "").strip()
    try:
        if not login_novo or not senha or not nome:
            raise ValueError("Preencha login, senha e nome.")
        # Gestor só cria cliente; conta do escritório (funcionário/gestor/admin) exige admin.
        if not g.usuario.pode_gerir(tipo):
            raise ValueError("Você não tem permissão para criar esse tipo de conta.")
        novo = Usuario.criar(login_novo, senha, tipo, nome,
                             cliente_cnpj=cnpj if tipo == TIPO_CLIENTE else None)
        if email:
            db_manager.atualizar_email_usuario(novo.id, email)
        flash(f"Conta '{login_novo}' criada.", "sucesso")
    except ValueError as exc:
        flash(str(exc), "erro")
    except Exception:  # login duplicado (UNIQUE)
        flash(f"Não foi possível criar: o login '{login_novo}' já existe?", "erro")
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:usuario_id>/ativo", methods=["POST"])
def alternar_usuario_ativo(usuario_id):
    alvo = db_manager.buscar_usuario_por_id(usuario_id)
    _gerir_conta_ou_abortar(alvo)
    if usuario_id == g.usuario.id:
        flash("Você não pode desativar a própria conta.", "erro")
        return redirect(url_for("usuarios"))
    db_manager.definir_usuario_ativo(usuario_id, not alvo["ativo"])
    flash(f"Conta '{alvo['login']}' {'reativada' if not alvo['ativo'] else 'desativada'}.", "sucesso")
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:usuario_id>/resetar-senha", methods=["POST"])
def resetar_senha_usuario(usuario_id):
    alvo_row = db_manager.buscar_usuario_por_id(usuario_id)
    _gerir_conta_ou_abortar(alvo_row)
    try:
        alvo = Usuario.carregar(usuario_id)
        alvo.redefinir_senha(request.form.get("senha_nova", ""))
        flash(f"Senha de '{alvo.login}' redefinida.", "sucesso")
    except ValueError as exc:
        flash(str(exc), "erro")
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:usuario_id>/email", methods=["POST"])
def salvar_email_usuario(usuario_id):
    _gerir_conta_ou_abortar(db_manager.buscar_usuario_por_id(usuario_id))
    db_manager.atualizar_email_usuario(usuario_id, request.form.get("email", "").strip())
    flash("E-mail atualizado.", "sucesso")
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:usuario_id>/empresas/adicionar", methods=["POST"])
def adicionar_empresa(usuario_id):
    alvo = db_manager.buscar_usuario_por_id(usuario_id)
    if alvo is None or alvo["tipo_conta"] != TIPO_CLIENTE:
        abort(404)
    cnpj = request.form.get("cnpj", "").strip()
    nome = request.form.get("nome", "").strip()
    if not cnpj:
        flash("Informe o CNPJ da empresa.", "erro")
    else:
        db_manager.adicionar_empresa_usuario(usuario_id, cnpj, nome or None)
        flash(f"Empresa {cnpj} vinculada à conta '{alvo['login']}'.", "sucesso")
    return redirect(url_for("usuarios"))


@app.route("/empresas/<int:empresa_id>/remover", methods=["POST"])
def remover_empresa(empresa_id):
    db_manager.remover_empresa_usuario(empresa_id)
    flash("Empresa desvinculada.", "sucesso")
    return redirect(url_for("usuarios"))


# ---------------------------------------------------------------------------
# Relatórios (CSV + produtividade) — só escritório
# ---------------------------------------------------------------------------
@app.route("/relatorios")
def relatorios():
    hoje = date.today()
    data_inicio = request.args.get("data_inicio") or (hoje - timedelta(days=30)).isoformat()
    data_fim = request.args.get("data_fim") or hoje.isoformat()
    tipo = request.args.get("tipo") or None
    lista = Solicitacao.listar(cliente_cnpj=None, tipo=tipo,
                               data_inicio=data_inicio, data_fim=data_fim)

    # Export CSV (mesmos filtros da tela)
    if request.args.get("formato") == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(["id", "tipo", "cliente", "cnpj", "funcionario", "status", "criado_em", "atualizado_em"])
        for s in lista:
            w.writerow([s.id, RÓTULOS_TIPO.get(s.tipo, s.tipo), s._row.get("cliente_nome") or "",
                        s.cliente_cnpj or "", s._row.get("funcionario_nome") or "",
                        RÓTULOS_STATUS.get(s.status, s.status), s._row["criado_em"], s._row["atualizado_em"]])
        return Response(
            "﻿" + buf.getvalue(),  # BOM p/ Excel abrir acentuação certa
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition":
                     f"attachment; filename=solicitacoes_{data_inicio}_a_{data_fim}.csv"},
        )

    # Resumos da tela
    por_tipo, por_status, por_cliente = {}, {}, {}
    tempos_conclusao = []
    for s in lista:
        por_tipo[s.tipo] = por_tipo.get(s.tipo, 0) + 1
        por_status[_bucket_status(s.status)] = por_status.get(_bucket_status(s.status), 0) + 1
        nome_cli = s._row.get("cliente_nome") or "(sem nome)"
        por_cliente[nome_cli] = por_cliente.get(nome_cli, 0) + 1
        if s.status == "concluida":
            try:
                dur = (datetime.fromisoformat(s._row["atualizado_em"]) -
                       datetime.fromisoformat(s._row["criado_em"]))
                tempos_conclusao.append(dur.total_seconds())
            except ValueError:
                pass
    tempo_medio_horas = round(sum(tempos_conclusao) / len(tempos_conclusao) / 3600, 1) if tempos_conclusao else None

    # Produtividade por analista (etapas registradas no período)
    validacoes_periodo = db_manager.listar_validacoes_periodo(data_inicio, data_fim)
    por_analista = {}
    for v in validacoes_periodo:
        quem = v.get("aprovado_por") or "(não informado)"
        if quem.startswith("Automação"):
            continue
        info = por_analista.setdefault(quem, {"total": 0, "aprovacoes": 0, "entregas": 0})
        info["total"] += 1
        if v["etapa"] in ETAPAS_DE_DECISAO:
            info["aprovacoes"] += 1
        if v["etapa"] == "processamento_manual":
            info["entregas"] += 1

    return render_template("relatorios.html", lista=lista,
                           data_inicio=data_inicio, data_fim=data_fim, tipo=tipo,
                           tipos_disponiveis=sorted(RÓTULOS_TIPO.items(), key=lambda kv: kv[1]),
                           por_tipo=sorted(por_tipo.items(), key=lambda kv: -kv[1]),
                           por_cliente=sorted(por_cliente.items(), key=lambda kv: -kv[1]),
                           por_status=por_status,
                           tempo_medio_horas=tempo_medio_horas,
                           por_analista=sorted(por_analista.items(), key=lambda kv: -kv[1]["total"]))


# ---------------------------------------------------------------------------
# Calendário de obrigações do DP (checklist mensal) — só escritório
# ---------------------------------------------------------------------------
@app.route("/obrigacoes")
def obrigacoes():
    competencia = request.args.get("competencia") or date.today().strftime("%Y-%m")
    marcadas = db_manager.listar_obrigacoes_marcadas(competencia)
    ano, mes = map(int, competencia.split("-"))
    hoje = date.today()
    itens = []
    for ob in config.OBRIGACOES_MENSAIS:
        vencimento = date(ano, mes, min(ob["dia"], 28))
        registro = marcadas.get(ob["nome"])
        feito = bool(registro and registro["feito"])
        itens.append({**ob, "vencimento": vencimento, "feito": feito,
                      "marcado_por": registro["marcado_por"] if registro else None,
                      "atrasada": (not feito) and hoje > vencimento})
    anterior = (date(ano, mes, 1) - timedelta(days=1)).strftime("%Y-%m")
    proxima = (date(ano, mes, 28) + timedelta(days=5)).strftime("%Y-%m")
    return render_template("obrigacoes.html", itens=itens, competencia=competencia,
                           anterior=anterior, proxima=proxima)


@app.route("/obrigacoes/marcar", methods=["POST"])
def marcar_obrigacao_web():
    competencia = request.form.get("competencia", date.today().strftime("%Y-%m"))
    obrigacao = request.form.get("obrigacao", "")
    feito = request.form.get("feito") == "1"
    db_manager.marcar_obrigacao(competencia, obrigacao, feito, marcado_por=_ator(g.usuario))
    return redirect(url_for("obrigacoes", competencia=competencia))


# ---------------------------------------------------------------------------
# Push (PWA): chave pública + inscrição do dispositivo do usuário logado
# ---------------------------------------------------------------------------
@app.route("/push/chave-publica")
def push_chave_publica():
    return jsonify({"ativo": notificacoes.push_configurado(),
                    "chave": config.VAPID_CHAVE_PUBLICA})


@app.route("/push/inscrever", methods=["POST"])
def push_inscrever():
    dados = request.get_json(silent=True) or {}
    endpoint = (dados.get("endpoint") or "").strip()
    if not endpoint:
        return jsonify({"ok": False, "erro": "Inscrição inválida."}), 400
    db_manager.salvar_assinatura_push(g.usuario.id, endpoint, json.dumps(dados, ensure_ascii=False))
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("Automação DP - versão web rodando em http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
