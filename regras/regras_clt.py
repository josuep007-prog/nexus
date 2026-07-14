"""
regras/regras_clt.py
---------------------
Regras fixas (sem IA) para validar solicitações contra a CLT.

IMPORTANTE: as regras abaixo são um PONTO DE PARTIDA com os pontos mais
comuns da CLT (férias, aviso prévio, campos mínimos de admissão). Elas não
substituem revisão do seu setor de compliance/RH — principalmente porque
CCTs específicas podem alterar prazos e condições. Ajuste/complete conforme
a realidade do seu escritório.

Cada função `validar_*` retorna uma tupla: (ok: bool, erros: list[str])
Isso facilita mostrar pro analista exatamente o que está errado, ao invés
de só "reprovado".
"""

from datetime import date
from dateutil.relativedelta import relativedelta


# ---------------------------------------------------------------------------
# FÉRIAS
# ---------------------------------------------------------------------------
def validar_ferias(dias_solicitados, saldo_dias_direito=30, periodos=None):
    """
    Regras (CLT art. 134, alterado pela Reforma Trabalhista - Lei 13.467/2017):
    - Máximo de 30 dias de direito por período aquisitivo.
    - Pode ser fracionada em até 3 períodos, desde que um deles tenha
      pelo menos 14 dias corridos e nenhum seja inferior a 5 dias corridos.
    """
    erros = []

    if dias_solicitados <= 0:
        erros.append("Quantidade de dias de férias deve ser maior que zero.")

    if dias_solicitados > saldo_dias_direito:
        erros.append(
            f"Dias solicitados ({dias_solicitados}) excedem o saldo de direito "
            f"({saldo_dias_direito})."
        )

    if periodos:
        if len(periodos) > 3:
            erros.append("Férias não podem ser fracionadas em mais de 3 períodos.")
        if not any(p >= 14 for p in periodos):
            erros.append("Pelo menos um dos períodos fracionados deve ter no mínimo 14 dias.")
        if any(p < 5 for p in periodos):
            erros.append("Nenhum período fracionado pode ter menos de 5 dias.")
        if sum(periodos) != dias_solicitados:
            erros.append("Soma dos períodos fracionados não bate com o total de dias solicitados.")

    return (len(erros) == 0, erros)


def validar_ferias_dados(dados: dict):
    """
    Validação do formulário de Férias no caminho genérico da web (dict-in,
    retorno (ok, erros, extra)).

    Os campos seguem a solicitação "Cálculo de Férias" do Onvio Portal do
    Cliente (empregado, início do gozo, dias de gozo, abono, adiantar 13º),
    mais o campo próprio do nexus `saldo_dias_direito` — que NÃO vai pro Onvio,
    mas alimenta a conferência CLT (art. 134) antes da validação humana.
    Reaproveita `validar_ferias` para a regra dos dias/fracionamento.
    """
    erros = _campos_obrigatorios(dados, ["empregado_nome", "data_inicio_gozo", "dias_solicitados"])

    def _inteiro(chave, padrao):
        bruto = str(dados.get(chave, "")).strip()
        if not bruto:
            return padrao
        try:
            return int(bruto)
        except ValueError:
            erros.append(f"Valor inválido em '{chave}': informe um número inteiro de dias.")
            return padrao

    dias = _inteiro("dias_solicitados", 0)
    saldo = _inteiro("saldo_dias_direito", 30)

    _, erros_clt = validar_ferias(dias, saldo_dias_direito=saldo)
    erros.extend(erros_clt)

    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# AVISO PRÉVIO / RESCISÃO
# ---------------------------------------------------------------------------
def calcular_dias_aviso_previo(data_admissao: date, data_demissao: date):
    """
    Lei 12.506/2011: aviso prévio de 30 dias + 3 dias por ano completo de
    serviço, limitado a 90 dias no total.
    """
    anos_completos = relativedelta(data_demissao, data_admissao).years
    dias = 30 + (3 * anos_completos)
    return min(dias, 90)


def validar_rescisao(tipo_rescisao, data_admissao: date, data_demissao: date):
    """
    Valida dados mínimos de uma rescisão e calcula o aviso prévio esperado.
    `tipo_rescisao` esperado: 'sem_justa_causa', 'pedido_demissao',
    'justa_causa', 'acordo_comum' (Art. 484-A CLT), 'termino_contrato'.
    """
    erros = []
    tipos_validos = {
        "sem_justa_causa", "pedido_demissao", "justa_causa",
        "acordo_comum", "termino_contrato",
    }

    if tipo_rescisao not in tipos_validos:
        erros.append(f"Tipo de rescisão '{tipo_rescisao}' não reconhecido. Válidos: {tipos_validos}")

    if data_demissao < data_admissao:
        erros.append("Data de demissão não pode ser anterior à data de admissão.")

    dias_aviso = None
    if not erros:
        dias_aviso = calcular_dias_aviso_previo(data_admissao, data_demissao)

    return (len(erros) == 0, erros, {"dias_aviso_previo_estimado": dias_aviso})


# ---------------------------------------------------------------------------
# ADMISSÃO
# ---------------------------------------------------------------------------
CAMPOS_MINIMOS_ADMISSAO = [
    "nome_completo",
    "cpf",
    "pis_nis",
    "data_nascimento",
    "data_admissao",
    "cargo",
    "departamento",
    "salario",
    "horario_trabalho",
    "ctps_numero",
    "ctps_serie",
    "banco",
    "agencia",
    "conta",
]


def validar_admissao_dados_minimos(dados: dict):
    """Confere se todos os campos mínimos pra abrir uma admissão no Domínio estão presentes."""
    faltando = [c for c in CAMPOS_MINIMOS_ADMISSAO if not dados.get(c)]
    ok = len(faltando) == 0
    erros = [f"Campo obrigatório ausente: {c}" for c in faltando]
    return (ok, erros)


def validar_cpf(cpf: str):
    """Validação de dígito verificador do CPF (formato: apenas os 11 dígitos, sem pontuação)."""
    cpf = "".join(filter(str.isdigit, cpf or ""))
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    def _dv(cpf_parcial):
        soma = sum(int(d) * peso for d, peso in zip(cpf_parcial, range(len(cpf_parcial) + 1, 1, -1)))
        resto = (soma * 10) % 11
        return 0 if resto == 10 else resto

    dv1 = _dv(cpf[:9])
    dv2 = _dv(cpf[:9] + str(dv1))
    return cpf[-2:] == f"{dv1}{dv2}"


# ---------------------------------------------------------------------------
# Utilitário comum aos validadores "de formulário genérico" abaixo
# ---------------------------------------------------------------------------
def _campos_obrigatorios(dados: dict, campos: list):
    """Confere presença de campos obrigatórios num dict de formulário. Retorna lista de erros."""
    return [f"Campo obrigatório ausente: {c}" for c in campos if not dados.get(c)]


def _parse_data(valor):
    """Converte string 'AAAA-MM-DD' (padrão de <input type=date>) em date. Retorna None se inválido."""
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# BLOCO 1 — Advertência
# ---------------------------------------------------------------------------
def validar_advertencia(dados: dict):
    erros = _campos_obrigatorios(dados, ["motivo", "tipo_advertencia"])
    if dados.get("tipo_advertencia") not in (None, "", "verbal", "escrita"):
        erros.append("Tipo de advertência deve ser 'verbal' ou 'escrita'.")
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 1 — Suspensão disciplinar
# ---------------------------------------------------------------------------
def validar_suspensao(dados: dict):
    erros = _campos_obrigatorios(dados, ["motivo", "dias_suspensao"])
    try:
        dias = int(dados.get("dias_suspensao") or 0)
        if dias <= 0:
            erros.append("Dias de suspensão deve ser maior que zero.")
        elif dias > 30:
            erros.append("Suspensão maior que 30 dias é incomum — confira se não configura rescisão indireta (CLT art. 474).")
    except (TypeError, ValueError):
        erros.append("Dias de suspensão inválido.")
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 1 — Alteração de benefício (VT/VR/plano etc.)
# ---------------------------------------------------------------------------
def validar_alteracao_beneficio(dados: dict):
    erros = _campos_obrigatorios(dados, ["tipo_beneficio", "acao"])
    if dados.get("acao") not in (None, "", "incluir", "alterar", "excluir"):
        erros.append("Ação deve ser 'incluir', 'alterar' ou 'excluir'.")
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 1 — 13º salário
# ---------------------------------------------------------------------------
def validar_decimo_terceiro(dados: dict):
    erros = _campos_obrigatorios(dados, ["parcela", "competencia"])
    if dados.get("parcela") not in (None, "", "1", "2", 1, 2):
        erros.append("Parcela deve ser '1' ou '2'.")
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 1 — Transferência de local de trabalho
# ---------------------------------------------------------------------------
def validar_transferencia_local(dados: dict):
    erros = _campos_obrigatorios(dados, ["novo_local", "data_transferencia"])
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 1 — Alteração de jornada
# ---------------------------------------------------------------------------
def validar_alteracao_jornada(dados: dict):
    erros = _campos_obrigatorios(dados, ["nova_jornada_semanal"])
    try:
        horas = float(dados.get("nova_jornada_semanal") or 0)
        if horas > 44:
            erros.append("Jornada semanal não pode ultrapassar 44 horas (CLT art. 58), salvo acordo/convenção específico.")
        elif horas <= 0:
            erros.append("Jornada semanal deve ser maior que zero.")
    except (TypeError, ValueError):
        erros.append("Jornada semanal inválida.")
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 1 — Solicitação de declaração
# ---------------------------------------------------------------------------
def validar_declaracao(dados: dict):
    erros = _campos_obrigatorios(dados, ["tipo_declaracao"])
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 1 — PPP (Perfil Profissiográfico Previdenciário)
# ---------------------------------------------------------------------------
def validar_ppp(dados: dict):
    erros = _campos_obrigatorios(dados, ["motivo_solicitacao"])
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 1 — CND (certidões negativas de débitos ligadas ao DP)
# ---------------------------------------------------------------------------
def validar_cnd(dados: dict):
    erros = _campos_obrigatorios(dados, ["tipo_certidao", "finalidade"])
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 2 — Outros (solicitação livre, fora da lista)
# ---------------------------------------------------------------------------
def validar_outros(dados: dict):
    erros = _campos_obrigatorios(dados, ["assunto", "descricao"])
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 1 — Folha de adiantamento
# ---------------------------------------------------------------------------
def validar_folha_adiantamento(dados: dict):
    erros = _campos_obrigatorios(dados, ["competencia"])
    percentual = dados.get("percentual")
    if percentual not in (None, ""):
        try:
            p = float(percentual)
            if not (0 < p <= 100):
                erros.append("Percentual do adiantamento deve estar entre 1 e 100.")
        except (TypeError, ValueError):
            erros.append("Percentual inválido.")
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 1 — RPA (Recibo de Pagamento a Autônomo)
# ---------------------------------------------------------------------------
def validar_rpa(dados: dict):
    erros = _campos_obrigatorios(
        dados, ["prestador_nome", "prestador_cpf", "valor_servico", "descricao_servico", "competencia"]
    )
    if dados.get("prestador_cpf") and not validar_cpf(dados["prestador_cpf"]):
        erros.append("CPF do prestador inválido (dígito verificador incorreto).")
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 2 — Afastamento por INSS (auxílio-doença)
# ---------------------------------------------------------------------------
def validar_afastamento_inss(dados: dict):
    erros = _campos_obrigatorios(dados, ["data_inicio", "motivo_afastamento"])
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 2 — CAT (Comunicação de Acidente de Trabalho)
# ---------------------------------------------------------------------------
def validar_cat(dados: dict):
    """
    Lei 8.213/1991, art. 22: a CAT deve ser comunicada até o 1º dia útil
    seguinte ao acidente (imediatamente em caso de óbito).
    """
    erros = _campos_obrigatorios(dados, ["data_acidente", "data_comunicacao"])
    extra = {}
    data_acidente = _parse_data(dados.get("data_acidente"))
    data_comunicacao = _parse_data(dados.get("data_comunicacao"))
    if data_acidente and data_comunicacao:
        dias_para_comunicar = (data_comunicacao - data_acidente).days
        extra["dias_para_comunicar"] = dias_para_comunicar
        if dias_para_comunicar > 1:
            erros.append(
                f"CAT comunicada {dias_para_comunicar} dia(s) após o acidente — "
                "prazo legal é até o 1º dia útil seguinte (Lei 8.213/91, art. 22)."
            )
        if dias_para_comunicar < 0:
            erros.append("Data de comunicação não pode ser anterior à data do acidente.")
    return (len(erros) == 0, erros, extra)


# ---------------------------------------------------------------------------
# BLOCO 2 — Admissão de estagiário
# ---------------------------------------------------------------------------
def validar_admissao_estagiario(dados: dict):
    """Lei 11.788/2008 (Lei do Estágio)."""
    erros = _campos_obrigatorios(dados, ["instituicao_ensino", "carga_horaria_diaria"])
    try:
        carga = float(dados.get("carga_horaria_diaria") or 0)
        if carga > 6:
            erros.append("Carga horária de estágio não pode exceder 6h/dia, salvo cursos que alternam teoria/prática (Lei 11.788/2008, art. 10).")
        elif carga <= 0:
            erros.append("Carga horária diária deve ser maior que zero.")
    except (TypeError, ValueError):
        erros.append("Carga horária diária inválida.")
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 2 — Admissão de aprendiz
# ---------------------------------------------------------------------------
def validar_admissao_aprendiz(dados: dict):
    """CLT art. 428 / Lei 10.097/2000: aprendiz entre 14 e 24 anos (sem limite superior para PCD)."""
    erros = _campos_obrigatorios(dados, ["idade", "eh_pcd"])
    try:
        idade = int(dados.get("idade") or 0)
        eh_pcd = str(dados.get("eh_pcd")).lower() in ("true", "1", "sim", "on")
        if idade < 14:
            erros.append("Aprendiz deve ter no mínimo 14 anos (CLT art. 428).")
        elif idade > 24 and not eh_pcd:
            erros.append("Aprendiz deve ter no máximo 24 anos, exceto quando pessoa com deficiência (CLT art. 428, §5º).")
    except (TypeError, ValueError):
        erros.append("Idade inválida.")
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 2 — Inclusão / exclusão de dependente
# ---------------------------------------------------------------------------
def validar_dependente(dados: dict):
    erros = _campos_obrigatorios(dados, ["nome_dependente", "parentesco", "data_nascimento"])
    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 2 — Lançamento de valores na folha (horas extras, faltas, comissões etc.)
# ---------------------------------------------------------------------------
def validar_lancamento_valores_folha(dados: dict):
    """
    Cobre de forma genérica qualquer variável de folha: horas extras, faltas,
    comissões, adicional noturno, DSR etc. Quando o tipo for 'horas_extras',
    aplica o limite do CLT art. 59 (máx. 2h extras por dia).
    """
    erros = _campos_obrigatorios(dados, ["tipo_valor", "valor", "competencia"])

    if dados.get("tipo_valor") == "horas_extras":
        try:
            horas_por_dia = float(dados.get("horas_por_dia") or 0)
            if horas_por_dia > 2:
                erros.append("Horas extras não podem ultrapassar 2h/dia, salvo acordo de compensação específico (CLT art. 59).")
        except (TypeError, ValueError):
            pass  # campo opcional; só valida se foi preenchido

    try:
        valor = float(dados.get("valor") or 0)
        if valor < 0:
            erros.append("Valor não pode ser negativo.")
    except (TypeError, ValueError):
        erros.append("Valor inválido.")

    return (len(erros) == 0, erros, {})


# ---------------------------------------------------------------------------
# BLOCO 2 — Licença maternidade / paternidade
# ---------------------------------------------------------------------------
def validar_licenca_maternidade(dados: dict):
    """CLT art. 392: 120 dias corridos, ou 180 dias se a empresa aderir ao Programa Empresa Cidadã."""
    erros = _campos_obrigatorios(dados, ["data_inicio"])
    extra = {}
    data_inicio = _parse_data(dados.get("data_inicio"))
    empresa_cidada = str(dados.get("empresa_cidada")).lower() in ("true", "1", "sim", "on")
    if data_inicio:
        dias = 180 if empresa_cidada else 120
        extra["dias_licenca"] = dias
        extra["data_fim_estimada"] = (data_inicio + relativedelta(days=dias)).isoformat()
    return (len(erros) == 0, erros, extra)


def validar_licenca_paternidade(dados: dict):
    """CLT art. 473 / Lei 13.257/2016: 5 dias corridos, ou 20 dias se Empresa Cidadã."""
    erros = _campos_obrigatorios(dados, ["data_inicio"])
    extra = {}
    data_inicio = _parse_data(dados.get("data_inicio"))
    empresa_cidada = str(dados.get("empresa_cidada")).lower() in ("true", "1", "sim", "on")
    if data_inicio:
        dias = 20 if empresa_cidada else 5
        extra["dias_licenca"] = dias
        extra["data_fim_estimada"] = (data_inicio + relativedelta(days=dias)).isoformat()
    return (len(erros) == 0, erros, extra)


# ---------------------------------------------------------------------------
# BLOCO 2 — Exame ocupacional (ASO)
# ---------------------------------------------------------------------------
def validar_exame_ocupacional(dados: dict):
    tipos_validos = {"admissional", "periodico", "demissional", "mudanca_funcao", "retorno"}
    erros = _campos_obrigatorios(dados, ["tipo_exame"])
    if dados.get("tipo_exame") and dados["tipo_exame"] not in tipos_validos:
        erros.append(f"Tipo de exame deve ser um de: {tipos_validos}")
    return (len(erros) == 0, erros, {})
