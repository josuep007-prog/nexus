"""
utils/backup.py
----------------
Backup automático do banco SQLite com rotação. Uma cópia por dia, guardando
as últimas `config.BACKUP_MANTER_ULTIMOS` (14 por padrão).

É chamado no início do web/app.py e a cada rodada do worker — como só copia
uma vez por dia (controle na tabela `sistema`), pode ser chamado à vontade.
Usa a API de backup do próprio sqlite3 (segura mesmo com o banco em uso).
"""

import sqlite3
from datetime import date

import config
from database import db_manager

CHAVE_ULTIMO_BACKUP = "ultimo_backup_em"


def fazer_backup_diario():
    """Copia o banco pra backups/ se ainda não houve backup hoje. Retorna o Path ou None."""
    hoje = date.today().isoformat()
    if db_manager.obter_valor_sistema(CHAVE_ULTIMO_BACKUP) == hoje:
        return None  # já tem backup de hoje
    if not config.DB_PATH.exists():
        return None

    config.PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
    destino = config.PASTA_BACKUPS / f"dp_automacao_{hoje}.db"

    try:
        origem = sqlite3.connect(config.DB_PATH)
        try:
            copia = sqlite3.connect(destino)
            try:
                origem.backup(copia)  # cópia consistente, mesmo com o app rodando
            finally:
                copia.close()
        finally:
            origem.close()
    except sqlite3.Error as exc:
        db_manager.registrar_erro("backup", f"Falha no backup diário: {exc}")
        return None

    db_manager.definir_valor_sistema(CHAVE_ULTIMO_BACKUP, hoje)
    _rotacionar()
    return destino


def _rotacionar():
    """Apaga os backups mais antigos, mantendo só os últimos N."""
    arquivos = sorted(config.PASTA_BACKUPS.glob("dp_automacao_*.db"))
    excedentes = arquivos[:-config.BACKUP_MANTER_ULTIMOS] if len(arquivos) > config.BACKUP_MANTER_ULTIMOS else []
    for arq in excedentes:
        try:
            arq.unlink()
        except OSError:
            pass  # arquivo em uso/sem permissão — tenta de novo na próxima rotação
