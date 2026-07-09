"""
utils/file_manager.py
-------------------------
Organização de arquivos: salvar documentos gerados na estrutura de pastas do
"servidor" (cliente / tipo de documento / competência), como no seu script
Batch de organização de documentos de admissão.

Diferente dos módulos de integração, este aqui é REAL (não stub) — é só
manipulação de arquivos locais, sem depender de nenhum sistema externo.
"""

import shutil
from datetime import date
from pathlib import Path

from werkzeug.utils import secure_filename

from config import PASTA_SERVIDOR, PASTA_ANEXOS_RECEBIDOS


def _slug(texto: str) -> str:
    """Normaliza nome de cliente/tipo pra usar como nome de pasta (sem acento, sem espaço)."""
    import unicodedata
    texto = texto or "sem_nome"
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = texto.strip().replace(" ", "_")
    return "".join(c for c in texto if c.isalnum() or c in ("_", "-")) or "sem_nome"


def criar_estrutura_pastas(cliente: str, tipo: str, competencia: str = None) -> Path:
    competencia = competencia or date.today().strftime("%Y-%m")
    pasta = PASTA_SERVIDOR / _slug(cliente) / _slug(tipo) / competencia
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def salvar_no_servidor(caminho_origem: str, cliente: str, tipo: str, competencia: str = None) -> Path:
    origem = Path(caminho_origem)
    if not origem.exists():
        raise FileNotFoundError(f"Arquivo de origem não encontrado: {origem}")

    pasta_destino = criar_estrutura_pastas(cliente, tipo, competencia)
    destino = pasta_destino / origem.name

    # Evita sobrescrever caso já exista um arquivo com o mesmo nome
    contador = 1
    destino_final = destino
    while destino_final.exists():
        destino_final = pasta_destino / f"{origem.stem}_{contador}{origem.suffix}"
        contador += 1

    shutil.copy2(origem, destino_final)
    return destino_final


def salvar_anexo_recebido(categoria: str, solicitacao_id: int, arquivo_bytes: bytes,
                           nome_arquivo_original: str) -> Path:
    """
    Salva um anexo recebido (upload web ou desktop) em
    data/anexos_recebidos/<categoria>/<id da solicitação>/<nome do arquivo>.
    Usado tanto por atestados quanto por admissões (e qualquer módulo futuro
    do Bloco 2 que receba arquivo do cliente).
    """
    pasta_destino = PASTA_ANEXOS_RECEBIDOS / categoria / str(solicitacao_id)
    pasta_destino.mkdir(parents=True, exist_ok=True)

    nome_seguro = secure_filename(nome_arquivo_original) or f"arquivo_{solicitacao_id}"
    caminho_destino = pasta_destino / nome_seguro

    # Evita sobrescrever se o mesmo nome de arquivo for enviado duas vezes
    contador = 1
    destino_final = caminho_destino
    while destino_final.exists():
        base = caminho_destino.stem
        sufixo = caminho_destino.suffix
        destino_final = pasta_destino / f"{base}_{contador}{sufixo}"
        contador += 1

    with open(destino_final, "wb") as f:
        f.write(arquivo_bytes)

    return destino_final
