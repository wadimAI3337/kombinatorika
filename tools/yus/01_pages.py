"""PDF (скан, JBIG2) -> полстраницы PNG для расшифровки и страница 600 dpi для досок.
   Номер файла = номер страницы PDF (1-based)."""
import pymupdf, os, sys
from PIL import Image
F = os.path.expanduser("~/Desktop/Шахматы/КНИГИ/[Artur_Yusupov]_Build_Up_Your_Chess_With_Artur_Yus.pdf")
d = pymupdf.open(F)
os.makedirs("work/img", exist_ok=True); os.makedirs("work/full", exist_ok=True)
a, b = int(sys.argv[1]), int(sys.argv[2])
for p in range(a, b + 1):
    page = d[p - 1]
    xref = page.get_images()[0][0]
    pix = pymupdf.Pixmap(d, xref)
    im = Image.frombytes("L", (pix.width, pix.height), pix.samples) if pix.n == 1 else \
         Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
    im.save(f"work/full/p{p:03d}.png")
    W, H = im.size
    sm = im.resize((1400, int(H * 1400 / W)), Image.LANCZOS)
    w, h = sm.size
    sm.crop((0, 0, w, int(h * .53))).save(f"work/img/p{p:03d}a.png")
    sm.crop((0, int(h * .47), w, h)).save(f"work/img/p{p:03d}b.png")
