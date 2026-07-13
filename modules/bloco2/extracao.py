"""
modules/bloco2/extracao.py
-----------------------------
Extração de dados de anexos (PDF nativo, PDF escaneado ou imagem) enviados
pelo cliente. Usa pdfplumber para PDFs com texto e pytesseract (OCR) para
imagens/PDFs escaneados — mesma dupla que você já usa no seu projeto de
admissões (PyQt5 + Tesseract + pdfplumber).

Esse módulo está com uma extração básica funcional (baixar texto bruto do
arquivo) e os pontos de "mapear texto -> campos" (nome, CPF, PIS etc.) como
próximo passo a refinar com seus documentos reais — geralmente isso é feito
com expressões regulares específicas para o layout de cada tipo de
documento (RG, CTPS, comprovante de residência etc.), então vale você trazer
exemplos reais pra calibrarmos essa parte.
"""

import re
from pathlib import Path

# pdfplumber/pytesseract/Pillow são dependências PESADAS (e o OCR ainda exige o
# binário do Tesseract no sistema). Importamos SOB DEMANDA, dentro das funções,
# pra que o app web suba em ambientes enxutos (ex.: hospedagem gratuita p/ demo)
# mesmo sem elas — nesse caso a extração degrada (retorna vazio) e o analista
# revisa/preenche na mão, sem quebrar o fluxo.


def _extrair_texto_pdf(caminho: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        return ""  # sem a lib, seguimos sem extração automática
    texto = []
    with pdfplumber.open(caminho) as pdf:
        for pagina in pdf.pages:
            texto.append(pagina.extract_text() or "")
    return "\n".join(texto)


def _extrair_texto_imagem(caminho: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""  # sem OCR disponível, seguimos sem extração automática
    imagem = Image.open(caminho)
    return pytesseract.image_to_string(imagem, lang="por")


def extrair_texto_bruto(caminho_arquivo: str) -> str:
    caminho = Path(caminho_arquivo)
    sufixo = caminho.suffix.lower()

    if sufixo == ".pdf":
        texto = _extrair_texto_pdf(caminho)
        # PDF escaneado (sem texto extraível) -> cai para OCR renderizando a página como imagem
        # seria necessário pdf2image aqui; deixado como próximo passo, pois depende do poppler
        # instalado na máquina de destino.
        return texto
    elif sufixo in (".jpg", ".jpeg", ".png", ".bmp", ".tiff"):
        return _extrair_texto_imagem(caminho)
    else:
        raise ValueError(f"Formato de arquivo não suportado para extração: {sufixo}")


# ---------------------------------------------------------------------------
# Mapeamento texto -> campos, por tipo de solicitação
# ---------------------------------------------------------------------------
_REGEX_CPF = re.compile(r"\b(\d{3}\.?\d{3}\.?\d{3}-?\d{2})\b")
_REGEX_PIS = re.compile(r"\b(\d{3}\.?\d{5}\.?\d{2}-?\d{1})\b")
_REGEX_DATA = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")


def _extrair_campos_admissao(texto: str) -> dict:
    """
    Extração básica por regex. Funciona bem para achar CPF, PIS e datas soltos
    no texto. Nome, cargo e salário normalmente exigem uma regra por layout
    de documento — ajuste aqui conforme os modelos reais que você recebe.
    """
    dados = {}

    m_cpf = _REGEX_CPF.search(texto)
    if m_cpf:
        dados["cpf"] = re.sub(r"\D", "", m_cpf.group(1))

    m_pis = _REGEX_PIS.search(texto)
    if m_pis:
        dados["pis_nis"] = re.sub(r"\D", "", m_pis.group(1))

    datas = _REGEX_DATA.findall(texto)
    if datas:
        dados["datas_encontradas"] = datas  # revisão humana decide qual é nascimento/admissão

    return dados


def _extrair_campos_folha_variavel(texto: str) -> dict:
    # Placeholder: normalmente aqui você teria uma tabela com "tipo de variável -> valor"
    # (horas extras, faltas, comissões...). Ajustar conforme o padrão de planilha/documento do cliente.
    return {"texto_bruto": texto[:2000]}


def _extrair_campos_afastamento(texto: str) -> dict:
    dados = {}
    datas = _REGEX_DATA.findall(texto)
    if datas:
        dados["datas_encontradas"] = datas
    return dados


_EXTRATORES_POR_TIPO = {
    "admissao": _extrair_campos_admissao,
    "folha_com_variaveis": _extrair_campos_folha_variavel,
    "afastamento_inss": _extrair_campos_afastamento,
}


def extrair_dados(caminho_arquivo: str, tipo_solicitacao: str) -> dict:
    """Ponto de entrada usado por modules/bloco2/recebimento_anexo.py."""
    texto = extrair_texto_bruto(caminho_arquivo)

    extrator = _EXTRATORES_POR_TIPO.get(tipo_solicitacao)
    if extrator is None:
        raise NotImplementedError(f"Sem extrator definido para o tipo '{tipo_solicitacao}'.")

    return extrator(texto)
