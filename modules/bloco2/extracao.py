"""
modules/bloco2/extracao.py
-----------------------------
Extração de dados dos documentos que o cliente anexa (PDF nativo, PDF
escaneado ou imagem). É o que sustenta a promessa do nexus de "cliente digita
menos": o que sai daqui pré-preenche a solicitação e cai na conferência humana.

ESTRATÉGIA (importante entender antes de mexer):

1. **Por RÓTULO, não por layout.** Documentos de DP brasileiros (ficha de
   admissão, ficha de registro, formulários de RH) são quase sempre pares
   "Rótulo: valor". Procurar por rótulo (com sinônimos) funciona em qualquer
   layout — é diferente de decorar a posição de um campo num modelo específico,
   que quebra no primeiro documento diferente.
2. **Só entrega o que dá pra confiar.** Todo valor passa por normalização e,
   quando existe regra (CPF, PIS), por validação de dígito. Valor suspeito não
   é entregue como se fosse bom — vira pendência pro analista.
3. **Diz o que NÃO conseguiu.** O resultado traz `_diagnostico`, com o que foi
   achado, o que faltou e o motivo (ex.: PDF sem camada de texto). Silêncio é
   pior que "não achei": o analista precisa saber se deve conferir na mão.

CALIBRAÇÃO: a lista de rótulos (`_ROTULOS`) foi montada com os nomes usuais dos
campos. Documentos reais sempre trazem variações — use
`python scripts/testar_extracao.py <arquivo>` num documento de verdade para ver
o que foi achado e o que passou batido, e acrescente o rótulo que faltou.
"""

import re
import unicodedata
from pathlib import Path

# pdfplumber/pytesseract/Pillow são dependências PESADAS (e o OCR ainda exige o
# binário do Tesseract no sistema). Importamos SOB DEMANDA, dentro das funções,
# pra que o app web suba em ambientes enxutos (ex.: hospedagem gratuita p/ demo)
# mesmo sem elas — nesse caso a extração degrada (retorna vazio) e o analista
# revisa/preenche na mão, sem quebrar o fluxo.

# Motivos de diagnóstico (o "porquê" de não ter extraído nada)
SEM_BIBLIOTECA = "sem_biblioteca"
PDF_SEM_TEXTO = "pdf_sem_camada_de_texto"


# ---------------------------------------------------------------------------
# Leitura do arquivo -> texto
# ---------------------------------------------------------------------------

def _extrair_texto_pdf(caminho: Path):
    """-> (texto, motivo_de_falha | None)"""
    try:
        import pdfplumber
    except Exception:  # noqa: BLE001 - lib ausente ou quebrada no ambiente
        return "", SEM_BIBLIOTECA
    partes = []
    with pdfplumber.open(caminho) as pdf:
        for pagina in pdf.pages:
            partes.append(pagina.extract_text() or "")
    texto = "\n".join(partes).strip()
    # PDF escaneado (imagem dentro do PDF) não tem camada de texto: o
    # pdfplumber devolve vazio. Sinalizamos em vez de fingir que "não achou".
    return (texto, None) if texto else ("", PDF_SEM_TEXTO)


def _extrair_texto_imagem(caminho: Path):
    """-> (texto, motivo_de_falha | None)"""
    try:
        import pytesseract
        from PIL import Image
    except Exception:  # noqa: BLE001
        return "", SEM_BIBLIOTECA
    try:
        return pytesseract.image_to_string(Image.open(caminho), lang="por").strip(), None
    except Exception:  # noqa: BLE001 - Tesseract ausente/sem o idioma instalado
        return "", SEM_BIBLIOTECA


def extrair_texto_bruto(caminho_arquivo: str) -> str:
    """Texto do documento (string vazia se não foi possível ler)."""
    return _ler_documento(caminho_arquivo)[0]


def _ler_documento(caminho_arquivo: str):
    """-> (texto, motivo_de_falha | None)"""
    caminho = Path(caminho_arquivo)
    sufixo = caminho.suffix.lower()
    if sufixo == ".pdf":
        return _extrair_texto_pdf(caminho)
    if sufixo in (".jpg", ".jpeg", ".png", ".bmp", ".tiff"):
        return _extrair_texto_imagem(caminho)
    raise ValueError(f"Formato de arquivo não suportado para extração: {sufixo}")


# ---------------------------------------------------------------------------
# Normalizadores e validadores
# ---------------------------------------------------------------------------

def _so_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def _sem_acento_minusculo(texto: str) -> str:
    sem = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in sem if unicodedata.category(c) != "Mn").lower()


def _digitos_cpf_validos(cpf: str) -> bool:
    """Dígito verificador do CPF (mesma regra de regras_clt.validar_cpf)."""
    numeros = _so_digitos(cpf)
    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(numeros[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(numeros[tamanho]):
            return False
    return True


def _digitos_pis_validos(pis: str) -> bool:
    """Dígito verificador do PIS/PASEP/NIS (módulo 11, pesos 3..2)."""
    numeros = _so_digitos(pis)
    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False
    pesos = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    resto = sum(int(numeros[i]) * pesos[i] for i in range(10)) % 11
    digito = 0 if resto < 2 else 11 - resto
    return digito == int(numeros[10])


def _data_para_iso(valor: str):
    """'01/09/2026' ou '01-09-2026' -> '2026-09-01'. None se não for data plausível."""
    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b", valor or "")
    if not m:
        return None
    dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if ano < 100:  # "26" -> 2026
        ano += 2000
    if not (1 <= dia <= 31 and 1 <= mes <= 12 and 1900 <= ano <= 2100):
        return None
    return f"{ano:04d}-{mes:02d}-{dia:02d}"


def _valor_para_decimal(valor: str):
    """'R$ 1.500,00' -> '1500.00'. None se não houver número."""
    m = re.search(r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2}|\d+)", valor or "")
    if not m:
        return None
    bruto = m.group(1)
    if "," in bruto:  # formato BR: ponto é milhar, vírgula é decimal
        bruto = bruto.replace(".", "").replace(",", ".")
    try:
        return f"{float(bruto):.2f}"
    except ValueError:
        return None


def _texto_limpo(valor: str):
    """Limpa o valor capturado depois do rótulo (corta no próximo rótulo da linha).

    Fichas colocam vários campos na mesma linha ("Banco: 341 Agência: 4521
    Conta: 12345-6"). Cortamos no PRÓXIMO RÓTULO CONHECIDO seguido de ':' —
    não em "qualquer palavra com dois-pontos", que quebraria valores legítimos
    como "Horário: 08:00 as 17:00". Exigir o ':' também protege valores que
    só contêm a palavra ("Cargo: Analista de Banco" não vira corte em "Banco").
    """
    valor = (valor or "").strip(" \t:;-–—|")
    normalizado = _sem_acento_minusculo(valor)  # mesma extensão do original
    corte = _PADRAO_PROXIMO_ROTULO.search(normalizado)
    if corte:
        valor = valor[:corte.start()]
    valor = re.sub(r"\s+", " ", valor).strip()
    return valor or None


# ---------------------------------------------------------------------------
# Extração por rótulo
# ---------------------------------------------------------------------------
# Cada campo lista os rótulos usuais (sem acento, minúsculo — a comparação é
# normalizada). Ordem importa: o primeiro que casar vence.
_ROTULOS = {
    "nome_completo": ["nome completo", "nome do empregado", "nome do colaborador",
                      "nome do funcionario", "nome do trabalhador", "empregado", "nome"],
    "cpf": ["cpf/mf", "n do cpf", "cpf"],
    "pis_nis": ["pis/pasep", "pis / pasep", "nit/pis", "pis", "pasep", "nis"],
    "data_nascimento": ["data de nascimento", "data nascimento", "nascimento", "dt nascimento",
                        "nascido em"],
    "data_admissao": ["data de admissao", "data admissao", "admissao", "data de inicio",
                      "inicio do contrato", "admitido em"],
    "cargo": ["cargo/funcao", "cargo", "funcao", "ocupacao", "cbo descricao"],
    "departamento": ["departamento", "setor", "lotacao", "area"],
    "salario": ["salario base", "salario contratual", "salario mensal", "salario",
                "remuneracao", "vencimento"],
    "horario_trabalho": ["horario de trabalho", "horario", "jornada de trabalho", "jornada",
                         "carga horaria"],
    "ctps_numero": ["ctps numero", "numero da ctps", "carteira de trabalho", "ctps"],
    "ctps_serie": ["serie da ctps", "ctps serie", "serie"],
    "banco": ["banco"],
    "agencia": ["agencia"],
    "conta": ["conta corrente", "conta salario", "conta"],
}

# Todos os rótulos conhecidos, do mais longo para o mais curto (para "conta
# corrente" vencer "conta"). Usado por _texto_limpo para saber onde termina o
# valor de um campo quando a linha tem vários campos.
_TODOS_ROTULOS = sorted({r for lista in _ROTULOS.values() for r in lista}, key=len, reverse=True)
_PADRAO_PROXIMO_ROTULO = re.compile(
    r"\s+(?:" + "|".join(re.escape(r) for r in _TODOS_ROTULOS) + r")\s*[:\-]"
)

# Como tratar o valor de cada campo depois de capturado.
_TRATAMENTO = {
    "cpf": ("digitos", _digitos_cpf_validos),
    "pis_nis": ("digitos", _digitos_pis_validos),
    "data_nascimento": ("data", None),
    "data_admissao": ("data", None),
    "salario": ("valor", None),
    "ctps_numero": ("digitos", None),
    "agencia": ("digitos", None),
}


def _buscar_por_rotulo(texto: str, rotulos):
    """Procura 'rotulo: valor' no texto (tolerante a acento/caixa). -> valor bruto | None"""
    linhas = (texto or "").splitlines()
    for rotulo in rotulos:
        for i, linha in enumerate(linhas):
            normalizada = _sem_acento_minusculo(linha)
            # o rótulo precisa vir seguido de ':' (ou espaços) — evita casar no meio de uma frase
            m = re.search(rf"\b{re.escape(rotulo)}\b\s*[:\-]\s*(.*)", normalizada)
            if not m:
                continue
            # recorta o valor da linha ORIGINAL (preserva acento/caixa do nome)
            inicio = len(linha) - len(m.group(1))
            valor = _texto_limpo(linha[inicio:])
            # valor na linha de baixo (ficha em duas linhas: rótulo em cima, valor embaixo)
            if not valor and i + 1 < len(linhas):
                valor = _texto_limpo(linhas[i + 1])
            if valor:
                return valor
    return None


def _aplicar_tratamento(campo: str, valor_bruto: str):
    """-> (valor_final | None, motivo_da_recusa | None)"""
    tipo, validador = _TRATAMENTO.get(campo, (None, None))
    if tipo == "digitos":
        if validador:
            # Se a linha trouxe mais de um número (ex.: dois campos na mesma
            # linha), testa cada candidato e fica com o que passa no dígito
            # verificador — em vez de grudar tudo e reprovar um dado bom.
            for candidato in re.findall(r"[\d][\d.\-/]{9,}[\d]", valor_bruto or ""):
                digitos = _so_digitos(candidato)
                if validador(digitos):
                    return digitos, None
            digitos = _so_digitos(valor_bruto)
            if not digitos:
                return None, "sem dígitos"
            return None, "dígito verificador inválido"
        valor = _so_digitos(valor_bruto)
        return (valor, None) if valor else (None, "sem dígitos")
    if tipo == "data":
        valor = _data_para_iso(valor_bruto)
        return (valor, None) if valor else (None, "data não reconhecida")
    if tipo == "valor":
        valor = _valor_para_decimal(valor_bruto)
        return (valor, None) if valor else (None, "valor não reconhecido")
    return valor_bruto, None


# Fallback: documentos sem rótulo (ex.: foto de CTPS) ao menos entregam
# CPF/PIS soltos, se passarem no dígito verificador.
_REGEX_CPF_SOLTO = re.compile(r"\b(\d{3}\.?\d{3}\.?\d{3}-?\d{2})\b")
_REGEX_PIS_SOLTO = re.compile(r"\b(\d{3}\.?\d{5}\.?\d{2}-?\d{1})\b")


def _buscar_documentos_soltos(texto: str, ja_achados: dict):
    achados = {}
    if not ja_achados.get("cpf"):
        for m in _REGEX_CPF_SOLTO.finditer(texto or ""):
            if _digitos_cpf_validos(m.group(1)):
                achados["cpf"] = _so_digitos(m.group(1))
                break
    if not ja_achados.get("pis_nis"):
        for m in _REGEX_PIS_SOLTO.finditer(texto or ""):
            if _digitos_pis_validos(m.group(1)):
                achados["pis_nis"] = _so_digitos(m.group(1))
                break
    return achados


def extrair_campos(texto: str, campos=None) -> dict:
    """Extrai os campos pedidos do texto. -> {campo: valor, ..., '_diagnostico': {...}}"""
    campos = campos or list(_ROTULOS)
    dados, recusados = {}, {}

    for campo in campos:
        bruto = _buscar_por_rotulo(texto, _ROTULOS.get(campo, []))
        if bruto is None:
            continue
        valor, motivo = _aplicar_tratamento(campo, bruto)
        if valor:
            dados[campo] = valor
        elif motivo:
            recusados[campo] = f"'{bruto}' — {motivo}"

    dados.update(_buscar_documentos_soltos(texto, dados))

    faltando = [c for c in campos if c not in dados]
    dados["_diagnostico"] = {
        "achados": sorted(k for k in dados if not k.startswith("_")),
        "faltando": faltando,
        "recusados": recusados,  # achou algo, mas não passou na validação
    }
    return dados


# ---------------------------------------------------------------------------
# Extratores por tipo de solicitação
# ---------------------------------------------------------------------------

def _extrair_campos_admissao(texto: str) -> dict:
    """Admissão: mira os 14 campos mínimos de regras_clt.CAMPOS_MINIMOS_ADMISSAO."""
    return extrair_campos(texto)


def _extrair_campos_afastamento(texto: str) -> dict:
    dados = extrair_campos(texto, ["nome_completo", "cpf", "data_admissao"])
    # Num atestado/afastamento a data relevante é a do afastamento; sem rótulo
    # claro, entrega as datas encontradas para o analista escolher.
    datas = [d for d in (_data_para_iso(x) for x in re.findall(r"\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}", texto or "")) if d]
    if datas:
        dados["datas_encontradas"] = sorted(set(datas))
    return dados


def _extrair_campos_folha_variavel(texto: str) -> dict:
    # Lançamento de rubricas costuma vir em planilha/tabela — o parsing por
    # tabela depende do formato real do cliente. Por ora entrega nome/CPF e o
    # texto para conferência.
    dados = extrair_campos(texto, ["nome_completo", "cpf"])
    dados["texto_bruto"] = (texto or "")[:2000]
    return dados


_EXTRATORES_POR_TIPO = {
    "admissao": _extrair_campos_admissao,
    "admissao_estagiario": _extrair_campos_admissao,
    "admissao_aprendiz": _extrair_campos_admissao,
    "folha_com_variaveis": _extrair_campos_folha_variavel,
    "afastamento_inss": _extrair_campos_afastamento,
    "atestado": _extrair_campos_afastamento,
    "cat": _extrair_campos_afastamento,
    "licenca_maternidade": _extrair_campos_afastamento,
    "licenca_paternidade": _extrair_campos_afastamento,
}


def tipos_com_extrator():
    """Tipos de solicitação que têm extrator definido (para a tela de calibração)."""
    return sorted(_EXTRATORES_POR_TIPO)


def rotulos_do_campo(campo: str):
    """Sinônimos procurados para um campo — mostrado na calibração."""
    return list(_ROTULOS.get(campo, []))


def diagnosticar(caminho_arquivo: str, tipo_solicitacao: str = "admissao") -> dict:
    """Roda a extração e devolve um relatório completo, para CALIBRAÇÃO.

    Usado pela tela `/extracao` (gestor/admin) e por scripts/testar_extracao.py —
    os dois compartilham esta função, sem reimplementar a análise.

    -> {texto, tamanho_texto, falha_leitura, achados, recusados, faltando,
        total_campos, total_achados}
    """
    texto, falha = _ler_documento(caminho_arquivo)
    relatorio = {
        "texto": texto,
        "tamanho_texto": len(texto or ""),
        "falha_leitura": falha,
        "achados": {},
        "recusados": {},
        "faltando": [],
        "total_campos": len(_ROTULOS),
        "total_achados": 0,
    }
    if not texto:
        return relatorio

    dados = extrair_dados(caminho_arquivo, tipo_solicitacao)
    diagnostico = dados.pop("_diagnostico", {})
    dados.pop("texto_bruto", None)

    relatorio["achados"] = {k: v for k, v in dados.items() if not k.startswith("_")}
    relatorio["recusados"] = diagnostico.get("recusados") or {}
    relatorio["faltando"] = [
        {"campo": campo, "rotulos": rotulos_do_campo(campo)}
        for campo in (diagnostico.get("faltando") or [])
    ]
    relatorio["total_achados"] = len([c for c in relatorio["achados"] if c in _ROTULOS])
    return relatorio


def extrair_dados(caminho_arquivo: str, tipo_solicitacao: str) -> dict:
    """Ponto de entrada usado por modules/bloco2/recebimento_anexo.py."""
    texto, motivo_falha = _ler_documento(caminho_arquivo)

    extrator = _EXTRATORES_POR_TIPO.get(tipo_solicitacao)
    if extrator is None:
        raise NotImplementedError(f"Sem extrator definido para o tipo '{tipo_solicitacao}'.")

    if not texto:
        # Não conseguimos ler: devolve o diagnóstico para o analista entender
        # por que veio vazio (em vez de parecer que o documento não tinha nada).
        return {"_diagnostico": {"achados": [], "faltando": [], "recusados": {},
                                 "falha_leitura": motivo_falha}}

    dados = extrator(texto)
    if motivo_falha:
        dados["_diagnostico"]["falha_leitura"] = motivo_falha
    return dados
