"""Поиск диаграмм на страницах (work/full, 600 dpi) и нарезка досок —
   так же, как в dvor/02_boards.py: рамка со штриховкой тёмных полей —
   одна большая почти квадратная связная компонента.
   Порядок — левая колонка сверху вниз, потом правая."""
import os, sys, json
import numpy as np
from PIL import Image
from scipy import ndimage
def find(ink):
    sm = ink[::4, ::4]
    sm = ndimage.binary_dilation(sm, iterations=1)
    lab, n = ndimage.label(sm)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        if min(h, w) < 150 or abs(h - w) > .08 * max(h, w): continue
        out.append((sl[0].start * 4, sl[1].start * 4, h * 4, w * 4))
    # доска внутри доски (кусок штриховки) — не доска
    return [b for b in out if not any(o != b and o[0] <= b[0] and o[1] <= b[1] and
            o[0] + o[2] >= b[0] + b[2] and o[1] + o[3] >= b[1] + b[3] for o in out)]
if __name__ == "__main__":
    a, b = int(sys.argv[1]), int(sys.argv[2])
    os.makedirs("work/boards", exist_ok=True)
    fn = f"work/boards_{a}.json"; res = {}
    for p in range(a, b + 1):
        ink = np.array(Image.open(f"work/full/p{p:03d}.png")) < 128
        H, W = ink.shape
        bs = sorted(find(ink), key=lambda t: (t[1] + t[3] / 2 > W / 2, t[0]))
        res[p] = []
        for k, (y, x, h, w) in enumerate(bs):
            pad = 12
            crop = ink[max(0, y - pad):y + h + pad, max(0, x - pad):x + w + pad]
            Image.fromarray((~crop * 255).astype(np.uint8)).save(f"work/boards/p{p:03d}_{k}.png")
            res[p].append([y, x, h, w])
    json.dump(res, open(fn, "w"))
