"""PDF «Boost Your Chess 2» -> страница 300 dpi (для досок) и две половины 1400 px (для разметки).
   В этом PDF на странице несколько слоёв-картинок, поэтому рендерим страницу целиком."""
import pymupdf, os, sys
from PIL import Image
F = os.path.expanduser("~/Desktop/Шахматы/КНИГИ/[Artur_Yusupov]_Boost_Your_Chess_2_with_Artur_Yusu.pdf")
d = pymupdf.open(F)
os.makedirs("work/img", exist_ok=True); os.makedirs("work/full", exist_ok=True)
a, b = int(sys.argv[1]), int(sys.argv[2])
for p in range(a, min(b, d.page_count) + 1):
    pm = d[p - 1].get_pixmap(dpi=300, colorspace=pymupdf.csGRAY)
    im = Image.frombytes("L", (pm.width, pm.height), pm.samples)
    im.save(f"work/full/p{p:03d}.png")
    W, H = im.size
    sm = im.resize((1400, int(H * 1400 / W)), Image.LANCZOS); w, h = sm.size
    sm.crop((0, 0, w, int(h * .53))).save(f"work/img/p{p:03d}a.png")
    sm.crop((0, int(h * .47), w, h)).save(f"work/img/p{p:03d}b.png")
