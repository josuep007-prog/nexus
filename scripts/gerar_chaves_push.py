"""
scripts/gerar_chaves_push.py
-----------------------------
Gera o par de chaves VAPID usado pelas notificações push do PWA.

Uso (uma vez só, no servidor):
    pip install pywebpush
    python scripts/gerar_chaves_push.py

Depois configure as variáveis de ambiente que ele imprime e reinicie o
servidor web. As chaves NÃO devem ser commitadas nem coladas no config.py.
"""

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("Instale primeiro:  pip install pywebpush")
    print("(o pacote 'cryptography' vem junto e é usado pra gerar as chaves)")
    sys.exit(1)


def _b64url(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


def main():
    chave = ec.generate_private_key(ec.SECP256R1())

    privada = _b64url(chave.private_numbers().private_value.to_bytes(32, "big"))
    publica = _b64url(chave.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))

    print("Chaves VAPID geradas. Configure as variáveis de ambiente no servidor web:\n")
    print(f'  set VAPID_CHAVE_PRIVADA={privada}')
    print(f'  set VAPID_CHAVE_PUBLICA={publica}')
    print(f'  set VAPID_CONTATO=mailto:seu-email@escritorio.com.br')
    print("\n(no PowerShell use  $env:VAPID_CHAVE_PRIVADA=\"...\"  ; em produção,")
    print("configure nas variáveis de ambiente do sistema pra persistir)")


if __name__ == "__main__":
    main()
