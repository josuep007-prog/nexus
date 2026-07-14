"""
modules/dossie.py
------------------
Dossiê do Empregado e conferência CLT automática.

O "Dossiê" é o espelho local dos dados de cada empregado (tabelas `empregados`
e `empregado_historico` em database/db_manager.py). Ele é alimentado por:
  - massa de teste (scripts/seed_empregados.py),
  - cada solicitação processada (`registrar_solicitacao_processada`),
  - futuramente, a sincronização do Onvio (integracao/onvio_sync.py — stub).

A conferência automática cruza a solicitação com o dossiê e decide entre dois
cenários (regra de negócio):
  - **Cenário A (dados completos):** o nexus valida a conformidade CLT sozinho.
  - **Cenário B (dados insuficientes):** NÃO bloqueia; deixa seguir e gera um
    alerta em destaque para o analista, indicando o que conferir na mão.
"""

from database import db_manager
from regras import regras_clt


# ---------------------------------------------------------------------------
# Localização e montagem do dossiê
# ---------------------------------------------------------------------------

def localizar_empregado(cliente_cnpj, cpf=None, nome=None):
    """Acha o empregado no dossiê por CPF (preferencial) ou, na falta, por nome."""
    if not cliente_cnpj:
        return None
    emp = db_manager.obter_empregado(cliente_cnpj, cpf) if cpf else None
    if emp is None and nome:
        emp = db_manager.obter_empregado_por_nome(cliente_cnpj, nome)
    return emp


def montar_dossie(cliente_cnpj, cpf=None, nome=None):
    """Retorna {'empregado': {...}, 'historico': [...]} ou None se não achar."""
    emp = localizar_empregado(cliente_cnpj, cpf, nome)
    if not emp:
        return None
    return {"empregado": emp, "historico": db_manager.listar_historico_empregado(emp["id"])}


# ---------------------------------------------------------------------------
# Conferência automática (Cenário A / Cenário B)
# ---------------------------------------------------------------------------

def _resultado(cenario="B", empregado_id=None, bloqueio_erros=None, alerta=None, pontos=None):
    return {
        "cenario": cenario,
        "empregado_id": empregado_id,
        "bloqueio_erros": bloqueio_erros or [],   # inconsistências reais (Cenário A) -> ajuste do cliente
        "alerta": alerta,                          # texto em destaque p/ o analista (Cenário B)
        "pontos_conferir": pontos or [],
    }


def conferir_ferias(dados: dict, cliente_cnpj):
    """
    Cruza uma solicitação de férias com o dossiê do empregado.

    - Empregado não encontrado, ou sem saldo de férias no cadastro -> Cenário B
      (alerta pro analista, sem bloquear).
    - Empregado com saldo conhecido -> Cenário A: valida dias solicitados x saldo
      (CLT art. 134), reaproveitando regras_clt.validar_ferias.
    """
    emp = localizar_empregado(cliente_cnpj, dados.get("empregado_cpf"), dados.get("empregado_nome"))

    if not emp:
        return _resultado(
            alerta=("Não há dados suficientes para a validação automática deste empregado "
                    "(não encontrado no cadastro). Realize a conferência manual."),
            pontos=["Saldo de dias de férias (período aquisitivo)",
                    "Existência/dados cadastrais do empregado"],
        )

    saldo = emp.get("saldo_ferias_dias")
    if saldo is None:
        return _resultado(
            empregado_id=emp["id"],
            alerta=("Empregado encontrado, mas sem saldo de férias no cadastro para conferência "
                    "automática. Confira o período aquisitivo manualmente."),
            pontos=["Saldo de dias de férias (período aquisitivo)"],
        )

    # Cenário A — dados completos: valida contra o saldo do dossiê.
    try:
        dias = int(str(dados.get("dias_solicitados", "0")).strip() or 0)
    except ValueError:
        dias = 0
    _, erros = regras_clt.validar_ferias(dias, saldo_dias_direito=int(saldo))
    return _resultado(cenario="A", empregado_id=emp["id"], bloqueio_erros=erros)


# Tipos com conferência automática definida. Novos tipos entram aqui.
_CONFERENCIAS = {
    "ferias": conferir_ferias,
}


def conferir(tipo, dados: dict, cliente_cnpj):
    """Roda a conferência do tipo, se houver. Retorna o dict de resultado ou None."""
    funcao = _CONFERENCIAS.get(tipo)
    return funcao(dados, cliente_cnpj) if funcao else None


# ---------------------------------------------------------------------------
# Atualização do dossiê a partir de solicitações processadas
# ---------------------------------------------------------------------------

def registrar_solicitacao_processada(sol):
    """
    Atualiza o dossiê quando uma solicitação é processada/entregue: espelha os
    dados do empregado e grava o evento no histórico. Para férias, abate os dias
    gozados do saldo. Best-effort: nunca deixa uma falha aqui quebrar a entrega.
    """
    try:
        dados = sol.dados
        cnpj = sol.cliente_cnpj
        cpf = (dados.get("empregado_cpf") or "").strip()
        nome = (dados.get("empregado_nome") or "").strip()
        if not cnpj or not (cpf or nome):
            return  # sem como identificar o empregado — nada a fazer

        emp = localizar_empregado(cnpj, cpf or None, nome or None)
        # Se não existe e temos CPF, cria o registro mínimo (espelho).
        if emp is None:
            if not cpf:
                return  # sem CPF não dá pra criar com chave confiável
            emp_id = db_manager.sincronizar_empregado(
                cnpj, cpf, {"nome": nome} if nome else {}, origem_dados="solicitacao")
            emp = db_manager.obter_empregado(cnpj, cpf)
        else:
            emp_id = emp["id"]

        if sol.tipo == "ferias":
            try:
                dias = int(str(dados.get("dias_solicitados", "0")).strip() or 0)
            except ValueError:
                dias = 0
            saldo = emp.get("saldo_ferias_dias")
            if saldo is not None and dias > 0:
                novo_saldo = max(int(saldo) - dias, 0)
                db_manager.sincronizar_empregado(
                    cnpj, emp["cpf"], {"saldo_ferias_dias": novo_saldo}, origem_dados="solicitacao")
            db_manager.adicionar_historico_empregado(
                emp_id, "ferias",
                descricao=f"Férias: {dias} dia(s) a partir de {dados.get('data_inicio_gozo', '?')}",
                dados={"dias": dias, "inicio": dados.get("data_inicio_gozo")},
                solicitacao_id=sol.id)
    except Exception:  # noqa: BLE001 - atualizar dossiê nunca pode quebrar a entrega
        pass
