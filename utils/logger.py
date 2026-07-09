"""
utils/logger.py
-------------------
Logging padronizado do sistema, gravando em arquivo (logs/dp_automacao.log)
além de mostrar no console. Use `obter_logger(__name__)` em qualquer módulo.
"""

import logging
from logging.handlers import RotatingFileHandler

from config import LOGS_DIR

_LOG_PATH = LOGS_DIR / "dp_automacao.log"
_FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

_configurado = False


def _configurar_root():
    global _configurado
    if _configurado:
        return
    logging.basicConfig(
        level=logging.INFO,
        format=_FORMATO,
        handlers=[
            RotatingFileHandler(_LOG_PATH, maxBytes=2_000_000, backupCount=5, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    _configurado = True


def obter_logger(nome: str) -> logging.Logger:
    _configurar_root()
    return logging.getLogger(nome)
