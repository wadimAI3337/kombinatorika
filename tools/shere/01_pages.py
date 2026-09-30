"""PDF-скан (в каждой странице одна картинка 1600x2500, 1 бит) -> work/full/pNNN.png
   (страница целиком, для поиска досок) и половины для расшифровки work/img/pNNNa.png
   (0–53% высоты) и pNNNb.png (47–100%), ширина 1400.
   Номер файла = номер страницы PDF = печатный номер.
   Запуск: python3 01_pages.py 15 49"""
import sys, os, io
import pymupdf
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "../../shere1.pdf")
os.makedirs(os.path.join(HERE, "work/img"), exist_ok=True); os.makedirs(os.path.join(HERE, "work/full"), exist_ok=True)
d = pymupdf.open(SRC)
a, b = int(sys.argv[1]), int(sys.argv[2])
for p in range(a, b + 1):
    fn = os.path.join(HERE, f"work/full/p{p:03d}.png")
    if not os.path.exists(fn):
        x = d[p].get_images()[0][0]
        im = Image.open(io.BytesIO(d.extract_image(x)["image"])).convert("L")
        im.save(fn)
    im = Image.open(fn)
    W, H = im.size
    sm = im.resize((1400, int(H * 1400 / W)), Image.LANCZOS)
    w, h = sm.size
    sm.crop((0, 0, w, int(h * .53))).save(os.path.join(HERE, f"work/img/p{p:03d}a.png"))
    sm.crop((0, int(h * .47), w, h)).save(os.path.join(HERE, f"work/img/p{p:03d}b.png"))
