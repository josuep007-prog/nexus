"""
integracao/dominio_rpa.py
----------------------------
Ponte entre o sistema e o Domínio (Sysdata), via automação de tela (PyAutoGUI).

`preencher_admissao` foi portado do projeto DominioAutoFill
(C:\\Users\\JOSUE\\Desktop\\DominioAutoFill\\dominio_auto_fill.py::fill_dominio_form) —
mesma técnica já validada lá: navegação por TAB entre campos + digitação
sequencial (`pyautogui.press("tab")` + `pyautogui.typewrite(...)`), sem
depender de coordenadas de tela fixas (que quebram com resolução/zoom
diferentes). Pré-requisito de uso é o mesmo do DominioAutoFill: o Domínio
precisa já estar aberto, logado, em primeiro plano e na tela/aba correta
antes de chamar qualquer `preencher_*` — não há automação de login aqui.

⚠️ A ordem em FIELD_ORDER_ADMISSAO foi montada a partir de
CAMPOS_MINIMOS_ADMISSAO (regras/regras_clt.py), não de um teste na tela real
de admissão do Domínio. Confirme/ajuste essa ordem (e os formatadores de
data/salário) contra a tela real antes de usar em produção.

As demais funções (`preencher_ferias`, `preencher_rescisao`,
`preencher_alteracao_cadastral`, `cadastrar_feriado`) continuam como stub —
quando for a vez delas, dá pra reaproveitar `_preencher_campos()` do mesmo
jeito, bastando definir a FIELD_ORDER de cada tela.
"""

import re
import time

# pyautogui/keyboard controlam mouse/teclado da tela real — só fazem sentido no
# PC-host com o Domínio aberto. Importamos com guarda LARGA (Exception, não só
# ImportError) de propósito: em ambiente headless (servidor/nuvem, sem DISPLAY),
# o pyautogui está até instalado, mas quebra ao abrir a tela durante o import
# (ex.: KeyError: 'DISPLAY'). Assim o app web sobe do mesmo jeito e a RPA degrada
# graciosamente — quem chama já trata `pyautogui is None`/erro sem quebrar o fluxo.
try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    import keyboard
except Exception:
    keyboard = None


class AutomacaoCancelada(Exception):
    """Levantada quando o usuário pressiona ESC durante o preenchimento."""


DELAY_ENTRE_CAMPOS = 0.5   # segundos - mesmo padrão (500ms) do DominioAutoFill
DELAY_ENTRE_TECLAS = 0.05  # segundos por caractere digitado
ATRASO_INICIAL = 3         # segundos de espera antes de começar (tempo de focar o Domínio)


def _checar_cancelamento():
    """Aborta o preenchimento se o usuário pressionar ESC (mesmo atalho do DominioAutoFill)."""
    if keyboard is None:
        return
    try:
        if keyboard.is_pressed("esc"):
            raise AutomacaoCancelada("Preenchimento cancelado pelo usuário (ESC).")
    except AutomacaoCancelada:
        raise
    except Exception:
        pass  # sem permissão para hook global de teclado - segue sem suporte a ESC


def _formatar_data_br(valor: str) -> str:
    """Converte 'AAAA-MM-DD' (<input type=date> do formulário web) para 'DD/MM/AAAA'."""
    if not valor:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(valor))
    if m:
        ano, mes, dia = m.groups()
        return f"{dia}/{mes}/{ano}"
    return str(valor)  # já deve estar em DD/MM/AAAA (ex: vindo da extração OCR)


def _formatar_salario_br(valor) -> str:
    """Converte número (1500.5) em '1.500,50'. Se já vier com vírgula (ex: extraído por OCR), mantém."""
    texto = str(valor).strip()
    if "," in texto:
        return texto
    try:
        numero = float(texto)
    except ValueError:
        return texto
    formatado_us = f"{numero:,.2f}"  # "1,500.00"
    return formatado_us.replace(",", "X").replace(".", ",").replace("X", ".")  # "1.500,00"


def _preencher_campos(dados: dict, ordem: list, delay: float = DELAY_ENTRE_CAMPOS) -> dict:
    """
    Motor genérico de preenchimento: navega com TAB e digita cada valor, na
    ordem informada. Mesmo mecanismo do DominioAutoFill.

    `ordem` é uma lista de tuplas (chave_em_dados, rotulo_pro_log, formatador_ou_None).
    """
    if pyautogui is None:
        raise RuntimeError("pyautogui não está instalado (pip install pyautogui).")

    pyautogui.FAILSAFE = False
    time.sleep(ATRASO_INICIAL)

    preenchidos, pulados = [], []
    for data_key, rotulo, formatador in ordem:
        _checar_cancelamento()

        valor = dados.get(data_key)
        if not valor:
            pulados.append(rotulo)
            pyautogui.press("tab")
            time.sleep(delay)
            continue

        valor_formatado = formatador(valor) if formatador else str(valor)

        pyautogui.press("tab")
        time.sleep(delay)
        pyautogui.typewrite(valor_formatado, interval=DELAY_ENTRE_TECLAS)
        time.sleep(delay)
        preenchidos.append(rotulo)

    return {"sucesso": True, "campos_preenchidos": preenchidos, "campos_pulados": pulados}


FIELD_ORDER_ADMISSAO = [
    # (chave em `dados`, rótulo pro log, formatador ou None para texto puro)
    ("nome_completo", "Nome", None),
    ("cpf", "CPF", None),
    ("pis_nis", "PIS/PASEP", None),
    ("data_nascimento", "Data de Nascimento", _formatar_data_br),
    ("data_admissao", "Data de Admissão", _formatar_data_br),
    ("cargo", "Cargo", None),
    ("salario", "Salário", _formatar_salario_br),
    ("ctps_numero", "Número CTPS", None),
    ("ctps_serie", "Série CTPS", None),
    ("banco", "Banco", None),
    ("agencia", "Agência", None),
    ("conta", "Conta", None),
]


def executar_processo(tipo_solicitacao: str, dados: dict) -> dict:
    """
    Roteador principal: decide qual automação de tela chamar de acordo com o
    tipo da solicitação (ferias, rescisao, alteracao_cadastral, admissao...).
    """
    roteador = {
        "ferias": preencher_ferias,
        "rescisao": preencher_rescisao,
        "alteracao_cadastral": preencher_alteracao_cadastral,
        "admissao": preencher_admissao,
    }
    funcao = roteador.get(tipo_solicitacao)
    if funcao is None:
        raise NotImplementedError(f"Nenhuma automação de tela definida para '{tipo_solicitacao}'.")
    return funcao(dados)


def abrir_dominio():
    raise NotImplementedError("Abertura/login automático do Domínio ainda não implementado.")


def preencher_ferias(dados: dict) -> dict:
    raise NotImplementedError("Automação de tela de férias ainda não implementada.")


def preencher_rescisao(dados: dict) -> dict:
    raise NotImplementedError("Automação de tela de rescisão ainda não implementada.")


def preencher_alteracao_cadastral(dados: dict) -> dict:
    raise NotImplementedError("Automação de tela de alteração cadastral ainda não implementada.")


def preencher_admissao(dados: dict) -> dict:
    """
    Preenche a tela de admissão do Domínio via TAB + digitação, na ordem de
    FIELD_ORDER_ADMISSAO. Assume que o Domínio já está aberto, em primeiro
    plano e na tela de admissão (mesmo pré-requisito do DominioAutoFill).
    """
    return _preencher_campos(dados, FIELD_ORDER_ADMISSAO)


def cadastrar_feriado(data: str, descricao: str) -> dict:
    raise NotImplementedError("Automação de cadastro de feriado no Domínio ainda não implementada.")
