"""
config.py
---------
Configurações centrais do sistema. Praticamente tudo que é "caminho de pasta"
ou "constante do sistema" deve morar aqui, para não ficar espalhado nos módulos.

Quando for rodar na sua máquina de verdade, ajuste os caminhos abaixo (PASTA_SERVIDOR,
PASTA_ANEXOS etc.) para onde ficam os arquivos reais do escritório.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos base do projeto
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

DB_PATH = DATA_DIR / "dp_automacao.db"

# Pasta onde ficam os anexos recebidos dos clientes (Bloco 2) antes de processar
PASTA_ANEXOS_RECEBIDOS = DATA_DIR / "anexos_recebidos"

# Pasta "do servidor" onde os relatórios/documentos finais são salvos
# (no seu ambiente real, isso deve apontar para a pasta de rede do escritório)
PASTA_SERVIDOR = DATA_DIR / "servidor_documentos"

# Garante que as pastas essenciais existam ao importar o config
for _pasta in (DATA_DIR, LOGS_DIR, PASTA_ANEXOS_RECEBIDOS, PASTA_SERVIDOR):
    _pasta.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Blocos e tipos de solicitação (espelha o Mapeamento de Processos - DP)
# ---------------------------------------------------------------------------
BLOCO_1 = "bloco1"  # Sem anexo do cliente
BLOCO_2 = "bloco2"  # Com anexo do cliente

TIPOS_BLOCO_1 = [
    "ferias",
    "rescisao",
    "alteracao_cadastral",
    "relatorio_rotina",
    "folha_sem_variaveis",
    "advertencia",
    "suspensao",
    "alteracao_beneficio",
    "decimo_terceiro",
    "folha_adiantamento",
    "rpa",
    "transferencia_local",
    "alteracao_jornada",
    "declaracao",
    "ppp",
    "cnd",
]

TIPOS_BLOCO_2 = [
    "folha_com_variaveis",
    "admissao",
    "atestado",
    "afastamento_inss",
    "cat",
    "admissao_estagiario",
    "admissao_aprendiz",
    "inclusao_dependente",
    "exclusao_dependente",
    "licenca_maternidade",
    "licenca_paternidade",
    "exame_ocupacional",
    "outros",
]

CANAIS_ORIGEM = ["whatsapp", "email", "portal_onvio"]

# ---------------------------------------------------------------------------
# Modo de validação/extração por IA
# ---------------------------------------------------------------------------
# "regras_fixas"  -> usa funções Python fixas (regras/regras_clt.py, regras_cct.py)
# "api_claude"    -> usaria a API da Claude para validação/extração mais flexível
# Você escolheu começar com regras fixas (sem custo de API). Para trocar depois,
# basta mudar esse valor e implementar a chamada correspondente em cada módulo.
MODO_IA = "regras_fixas"

# ---------------------------------------------------------------------------
# Credenciais / endpoints de integração (preencher quando for integrar de verdade)
# ---------------------------------------------------------------------------
ONVIO_BASE_URL = ""   # ex: "https://api.onvio.com.br/..."
ONVIO_TOKEN = ""      # NUNCA deixe token real hardcoded em produção; use variável de ambiente

DOMINIO_EXECUTAVEL_PATH = ""  # caminho do executável do Domínio na máquina, se necessário

# ---------------------------------------------------------------------------
# OCR (leitura de imagens). O Tesseract é um PROGRAMA do sistema, não um
# pacote pip — e no Windows costuma ficar fora do PATH. Deixe vazio para o
# sistema procurar nos lugares usuais; ou aponte o caminho completo aqui/por
# variável de ambiente se estiver instalado em outro lugar.
# ---------------------------------------------------------------------------
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "")

# ---------------------------------------------------------------------------
# Uploads (segurança): tamanho máximo e extensões aceitas em qualquer envio
# ---------------------------------------------------------------------------
MAX_UPLOAD_MB = 10
EXTENSOES_UPLOAD_PERMITIDAS = {
    "pdf", "png", "jpg", "jpeg", "doc", "docx", "xls", "xlsx", "csv", "txt", "zip",
}

# ---------------------------------------------------------------------------
# Login: proteção contra força bruta (tentativas erradas seguidas)
# ---------------------------------------------------------------------------
LOGIN_MAX_TENTATIVAS = 5          # erros seguidos permitidos...
LOGIN_JANELA_MINUTOS = 10         # ...dentro desta janela...
LOGIN_BLOQUEIO_MINUTOS = 5        # ...bloqueiam novas tentativas por este tempo

# ---------------------------------------------------------------------------
# Notificações por e-mail (desligadas se SMTP_HOST não estiver configurado).
# Configure por variáveis de ambiente — nunca deixe senha real neste arquivo.
# ---------------------------------------------------------------------------
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORTA = int(os.environ.get("SMTP_PORTA", "587"))
SMTP_USUARIO = os.environ.get("SMTP_USUARIO", "")
SMTP_SENHA = os.environ.get("SMTP_SENHA", "")
SMTP_REMETENTE = os.environ.get("SMTP_REMETENTE", SMTP_USUARIO)
EMAIL_ESCRITORIO = os.environ.get("EMAIL_ESCRITORIO", "")  # recebe aviso de solicitação nova

# ---------------------------------------------------------------------------
# Notificações push do PWA (desligadas sem as chaves VAPID).
# Gere as chaves com: python scripts/gerar_chaves_push.py
# ---------------------------------------------------------------------------
VAPID_CHAVE_PRIVADA = os.environ.get("VAPID_CHAVE_PRIVADA", "")
VAPID_CHAVE_PUBLICA = os.environ.get("VAPID_CHAVE_PUBLICA", "")
VAPID_CONTATO = os.environ.get("VAPID_CONTATO", "mailto:contato@escritorio.com.br")

# ---------------------------------------------------------------------------
# Prazos (SLA) de atendimento por tipo de solicitação, em dias corridos a
# partir do recebimento. Tipos fora do dicionário usam o SLA padrão.
# ---------------------------------------------------------------------------
SLA_PADRAO_DIAS = 5
SLA_POR_TIPO = {
    "cat": 1,                    # CAT tem prazo legal de 1 dia útil
    "rescisao": 2,               # homologação/TRCT têm prazo de 10 dias corridos do desligamento
    "admissao": 2,               # registrar antes do 1º dia de trabalho
    "admissao_estagiario": 2,
    "admissao_aprendiz": 2,
    "atestado": 3,
    "afastamento_inss": 3,
    "ferias": 3,                 # aviso de férias exige 30 dias de antecedência
    "folha_com_variaveis": 3,
    "folha_sem_variaveis": 3,
    "folha_adiantamento": 3,
    "licenca_maternidade": 3,
    "licenca_paternidade": 3,
}
# A partir de quantos dias antes do vencimento a solicitação fica "em atenção"
SLA_ATENCAO_DIAS = 1

# ---------------------------------------------------------------------------
# Calendário mensal de obrigações do DP (dia do mês, nome, observação)
# ---------------------------------------------------------------------------
OBRIGACOES_MENSAIS = [
    {"dia": 5,  "nome": "Pagamento de salários", "obs": "Até o 5º dia útil do mês seguinte"},
    {"dia": 15, "nome": "Fechamento da folha no eSocial", "obs": "Eventos periódicos (S-1200/S-1299)"},
    {"dia": 20, "nome": "FGTS Digital", "obs": "Guia mensal — vencimento dia 20"},
    {"dia": 20, "nome": "DARF INSS/IRRF (DCTFWeb)", "obs": "Recolhimento dos tributos da folha"},
    {"dia": 25, "nome": "Entrega da DCTFWeb", "obs": "Declaração dos débitos previdenciários"},
]

# Alertas de fim do contrato de experiência (dias após a data de admissão)
EXPERIENCIA_AVISOS_DIAS = [45, 90]

# ---------------------------------------------------------------------------
# Backup automático do banco (data/) — cópias diárias com rotação
# ---------------------------------------------------------------------------
PASTA_BACKUPS = BASE_DIR / "backups"
BACKUP_MANTER_ULTIMOS = 14  # quantas cópias diárias guardar
