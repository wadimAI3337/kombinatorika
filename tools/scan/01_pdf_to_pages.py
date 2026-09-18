"""Шаг 1. PDF (скан) -> PNG страниц.

pdfimages вытаскивает встроенные картинки без пересжатия — это лучше,
чем pdftoppm, потому что не теряется резкость штриха (важно для мелких
значков фигур).  Один вызов на весь диапазон: по одной странице за раз
получается на порядок медленнее.

    python 01_pdf_to_pages.py book.pdf 4 103 pages
"""
import subprocess, sys, os
pdf, first, last, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
os.makedirs(out, exist_ok=True)
subprocess.run(['pdfimages','-f',first,'-l',last,'-png',pdf,os.path.join(out,'p')],check=True)
print(sorted(os.listdir(out))[:3], len(os.listdir(out)))
