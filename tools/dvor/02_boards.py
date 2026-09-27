"""Поиск диаграмм на страницах (600 dpi, битональные) и нарезка досок.
   Рамка доски вместе со штрихованными тёмными полями — одна большая
   связная компонента почти квадратной формы. Сохраняем кроп доски
   (с запасом) и список: страница, номер по порядку чтения, bbox."""
import subprocess, os, sys, json
import numpy as np
from PIL import Image
from scipy import ndimage
SRC = os.path.expanduser("~/Downloads/Dvoretskiy_M_-_Pomni_o_sopernike_Tom_{}_2013.djvu")
def page(v, p):
    tmp = f"work/v{v}/full.pbm"
    subprocess.run(["ddjvu", "-format=pbm", f"-page={p}", SRC.format(v), tmp], check=True)
    return np.array(Image.open(tmp).convert("L")) < 128        # True = чернила
def find(ink):
    sm = ink[::4, ::4] | ink[1::4, 1::4][:ink[::4,::4].shape[0], :ink[::4,::4].shape[1]]
    sm = ndimage.binary_dilation(sm, iterations=1)
    lab, n = ndimage.label(sm)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        if min(h, w) < 90 or abs(h - w) > .08 * max(h, w): continue
        fill = (lab[sl] == i + 1).mean()
        out.append((sl[0].start * 4, sl[1].start * 4, h * 4, w * 4, round(float(fill), 3)))
    return out
def order(bs, W):
    # две колонки: левая целиком, потом правая
    return sorted(bs, key=lambda b: (b[1] + b[3] / 2 > W / 2, b[0]))
if __name__ == "__main__":
    v, a, b = map(int, sys.argv[1:4])
    os.makedirs(f"work/v{v}/boards", exist_ok=True)
    res = {}
    fn = f"work/v{v}/boards.json"
    if os.path.exists(fn): res = json.load(open(fn))
    for p in range(a, b + 1):
        if str(p) in res: continue
        ink = page(v, p); H, W = ink.shape
        bs = order(find(ink), W)
        res[str(p)] = []
        for k, (y, x, h, w, fill) in enumerate(bs):
            pad = 12
            crop = ink[max(0, y - pad):y + h + pad, max(0, x - pad):x + w + pad]
            Image.fromarray((~crop * 255).astype(np.uint8)).save(f"work/v{v}/boards/p{p:03d}_{k}.png")
            res[str(p)].append([y, x, h, w, fill])
        json.dump(res, open(fn, "w"))
        print(p, len(bs), [(b[2], b[3], b[4]) for b in bs], flush=True)
