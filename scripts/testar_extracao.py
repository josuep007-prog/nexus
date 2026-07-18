"""
scripts/testar_extracao.py
---------------------------
Ferramenta de CALIBRAÇÃO da extração de documentos.

Aponte para um documento real (pode ser com dados fictícios) e veja exatamente
o que o sistema conseguiu extrair, o que ficou faltando e por quê. É assim que
se descobre qual RÓTULO o documento usa e que ainda não está na lista de
`modules/bloco2/extracao.py::_ROTULOS`.

Uso:
    python scripts/testar_extracao.py caminho/do/documento.pdf
    python scripts/testar_extracao.py ficha.jpg --tipo admissao
    python scripts/testar_extracao.py ficha.pdf --texto     # mostra o texto lido

Fluxo de calibração:
1. Rode num documento real do escritório.
2. Veja em "NÃO ENCONTRADOS" o que faltou.
3. Procure no texto (--texto) como aquele campo aparece no documento.
4. Acrescente o rótulo em _ROTULOS e rode de novo até achar tudo.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.bloco2 import extracao


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)

    caminho = Path(args[0])
    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}")
        sys.exit(1)

    tipo = "admissao"
    if "--tipo" in sys.argv:
        tipo = sys.argv[sys.argv.index("--tipo") + 1]

    print(f"\n=== {caminho.name} (tipo: {tipo}) ===\n")

    # Mesma análise que a tela /extracao (gestor/admin) usa — uma lógica só.
    relatorio = extracao.diagnosticar(str(caminho), tipo)
    texto, motivo = relatorio["texto"], relatorio["falha_leitura"]
    if motivo == extracao.PDF_SEM_TEXTO:
        print("⚠  PDF SEM CAMADA DE TEXTO (escaneado).")
        print("   O pdfplumber não lê imagem. Para esses casos é preciso OCR na")
        print("   página inteira (pdf2image + poppler) — hoje não instalado.")
        print("   Alternativa imediata: peça o documento em foto/JPG, que passa por OCR.\n")
        sys.exit(0)
    if motivo == extracao.SEM_BIBLIOTECA:
        print("⚠  Bibliotecas de leitura indisponíveis neste ambiente.")
        print("   Instale:  pip install pdfplumber pytesseract Pillow")
        print("   Para imagens, é preciso também o binário do Tesseract (idioma 'por').\n")
        sys.exit(0)

    print(f"Texto lido: {len(texto)} caracteres\n")
    if "--texto" in sys.argv:
        print("-" * 60)
        print(texto)
        print("-" * 60 + "\n")

    print("ENCONTRADOS:")
    if relatorio["achados"]:
        for campo, valor in sorted(relatorio["achados"].items()):
            print(f"   ✓ {campo:20} = {valor}")
    else:
        print("   (nenhum)")

    if relatorio["recusados"]:
        print("\nRECUSADOS (achou, mas não passou na validação):")
        for campo, motivo_recusa in relatorio["recusados"].items():
            print(f"   ✕ {campo:20} {motivo_recusa}")

    if relatorio["faltando"]:
        print("\nNÃO ENCONTRADOS:")
        for item in relatorio["faltando"]:
            rotulos = ", ".join(item["rotulos"][:4])
            print(f"   – {item['campo']:20} (procurei por: {rotulos}...)")
        print("\n   Se algum destes EXISTE no documento, veja com --texto qual rótulo")
        print("   ele usa e acrescente em _ROTULOS (modules/bloco2/extracao.py).")

    print(f"\nResumo: {relatorio['total_achados']}/{relatorio['total_campos']} "
          "campos preenchidos automaticamente.\n")


if __name__ == "__main__":
    main()
