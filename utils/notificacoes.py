"""
utils/notificacoes.py
----------------------
Notificações por E-MAIL (SMTP) e PUSH (PWA) — as duas desligam sozinhas
quando não estão configuradas, sem quebrar nenhum fluxo:

- E-mail : configure SMTP_HOST/SMTP_USUARIO/SMTP_SENHA por variável de
  ambiente (ver config.py). Sem SMTP_HOST, os envios são só registrados no log.
- Push   : exige as chaves VAPID (python scripts/gerar_chaves_push.py) e o
  pacote `pywebpush` instalado. Sem um dos dois, o push fica inativo.

NUNCA deixe senha/chave real hardcoded — sempre variável de ambiente.
Todos os envios são "melhor esforço": falha de rede/credencial é registrada
em log_erros e o fluxo da solicitação segue normalmente.
"""

import json
import smtplib
from email.message import EmailMessage

import config
from database import db_manager

try:  # pywebpush é opcional — só necessário se for usar push
    from pywebpush import webpush, WebPushException
    _PUSH_DISPONIVEL = True
except ImportError:
    _PUSH_DISPONIVEL = False


# ---------------------------------------------------------------------------
# E-mail
# ---------------------------------------------------------------------------

def email_configurado():
    return bool(config.SMTP_HOST)


def enviar_email(destinatarios, assunto, corpo):
    """Envia um e-mail simples (texto). Retorna True se enviou de verdade.

    `destinatarios` pode ser um e-mail ou lista. Sem SMTP configurado ou sem
    destinatário, não faz nada (retorna False) — o fluxo de negócio não depende
    do e-mail para funcionar.
    """
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]
    destinatarios = [d for d in (destinatarios or []) if d]
    if not destinatarios or not email_configurado():
        return False

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = config.SMTP_REMETENTE or config.SMTP_USUARIO
    msg["To"] = ", ".join(destinatarios)
    msg.set_content(corpo)

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORTA, timeout=15) as smtp:
            smtp.starttls()
            if config.SMTP_USUARIO:
                smtp.login(config.SMTP_USUARIO, config.SMTP_SENHA)
            smtp.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001 - notificação nunca derruba o fluxo
        db_manager.registrar_erro("notificacoes.email", f"Falha ao enviar '{assunto}': {exc}")
        return False


# ---------------------------------------------------------------------------
# Push (PWA)
# ---------------------------------------------------------------------------

def push_configurado():
    return _PUSH_DISPONIVEL and bool(config.VAPID_CHAVE_PRIVADA) and bool(config.VAPID_CHAVE_PUBLICA)


def enviar_push(usuario_ids, titulo, corpo, url="/"):
    """Envia push a todos os dispositivos inscritos dos usuários informados.

    Assinaturas mortas (dispositivo desinscrito) são removidas do banco.
    Retorna quantos pushes foram enviados.
    """
    if not push_configurado() or not usuario_ids:
        return 0
    enviados = 0
    payload = json.dumps({"titulo": titulo, "corpo": corpo, "url": url}, ensure_ascii=False)
    for assinatura in db_manager.listar_assinaturas_push(list(usuario_ids)):
        try:
            webpush(
                subscription_info=json.loads(assinatura["assinatura_json"]),
                data=payload,
                vapid_private_key=config.VAPID_CHAVE_PRIVADA,
                vapid_claims={"sub": config.VAPID_CONTATO},
            )
            enviados += 1
        except WebPushException as exc:
            # 404/410 = inscrição expirada: limpa do banco. Outros erros: log.
            codigo = getattr(getattr(exc, "response", None), "status_code", None)
            if codigo in (404, 410):
                db_manager.remover_assinatura_push(assinatura["endpoint"])
            else:
                db_manager.registrar_erro("notificacoes.push", f"Falha no push '{titulo}': {exc}")
        except Exception as exc:  # noqa: BLE001
            db_manager.registrar_erro("notificacoes.push", f"Falha no push '{titulo}': {exc}")
    return enviados


# ---------------------------------------------------------------------------
# Eventos de negócio (chamados pelas rotas/módulos)
# ---------------------------------------------------------------------------

def _contas_cliente(sol):
    """Contas cliente donas da solicitação (pelo CNPJ)."""
    if not sol.cliente_cnpj:
        return []
    return db_manager.buscar_clientes_por_cnpj(sol.cliente_cnpj)


def notificar_nova_solicitacao(sol, rotulo_tipo=None):
    """Avisa o ESCRITÓRIO que chegou solicitação nova (e-mail EMAIL_ESCRITORIO)."""
    titulo = rotulo_tipo or sol.tipo
    enviar_email(
        config.EMAIL_ESCRITORIO,
        f"[Automação DP] Nova solicitação #{sol.id} — {titulo}",
        f"Chegou uma nova solicitação de {sol._row.get('cliente_nome') or 'cliente sem nome'}:\n\n"
        f"  Nº:      #{sol.id}\n"
        f"  Tipo:    {titulo}\n"
        f"  Criada:  {sol._row.get('criado_em')}\n\n"
        f"Acesse a fila de validações para dar andamento.",
    )


def notificar_reprovacao(sol, motivo, rotulo_tipo=None):
    """Avisa o CLIENTE que a solicitação foi devolvida para correção."""
    contas = _contas_cliente(sol)
    titulo = rotulo_tipo or sol.tipo
    enviar_email(
        [c.get("email") for c in contas],
        f"[Automação DP] Solicitação #{sol.id} devolvida para correção",
        f"Sua solicitação #{sol.id} ({titulo}) foi analisada e precisa de ajustes.\n\n"
        f"Motivo informado pelo escritório:\n  {motivo}\n\n"
        f"Entre no sistema, corrija os dados e reenvie.",
    )
    enviar_push([c["id"] for c in contas],
                f"Solicitação #{sol.id} devolvida",
                "O escritório pediu correções. Toque para ver o motivo.",
                url=f"/solicitacoes/{sol.id}")


def notificar_entrega(sol, rotulo_tipo=None):
    """Avisa o CLIENTE que a solicitação foi concluída e os documentos entregues."""
    contas = _contas_cliente(sol)
    titulo = rotulo_tipo or sol.tipo
    enviar_email(
        [c.get("email") for c in contas],
        f"[Automação DP] Solicitação #{sol.id} concluída — documentos disponíveis",
        f"Sua solicitação #{sol.id} ({titulo}) foi concluída pelo escritório.\n\n"
        f"Os documentos e o resumo do atendimento já estão disponíveis no sistema.",
    )
    enviar_push([c["id"] for c in contas],
                f"Solicitação #{sol.id} concluída ✓",
                "Nova entrega do escritório disponível. Toque para abrir.",
                url=f"/solicitacoes/{sol.id}")


def notificar_comentario(sol, autor_tipo_conta, texto, rotulo_tipo=None):
    """Comentário novo: avisa o OUTRO lado da conversa (cliente <-> escritório)."""
    titulo = rotulo_tipo or sol.tipo
    resumo = texto if len(texto) <= 140 else texto[:137] + "..."
    if autor_tipo_conta == "cliente":
        # cliente escreveu -> avisa o escritório
        enviar_email(
            config.EMAIL_ESCRITORIO,
            f"[Automação DP] Comentário do cliente na solicitação #{sol.id}",
            f"O cliente comentou na solicitação #{sol.id} ({titulo}):\n\n  \"{resumo}\"",
        )
    else:
        # escritório escreveu -> avisa o(s) dono(s) da solicitação
        contas = _contas_cliente(sol)
        enviar_email(
            [c.get("email") for c in contas],
            f"[Automação DP] Nova mensagem do escritório na solicitação #{sol.id}",
            f"O escritório comentou na sua solicitação #{sol.id} ({titulo}):\n\n  \"{resumo}\"\n\n"
            f"Responda pelo próprio sistema, na página da solicitação.",
        )
        enviar_push([c["id"] for c in contas],
                    f"Mensagem na solicitação #{sol.id}",
                    resumo, url=f"/solicitacoes/{sol.id}")
