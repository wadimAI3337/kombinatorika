"""Доска -> 64 клетки 40x40. Границы — внутренние края рамки по профилю
   черноты (рамка ~6 px при 600 dpi), высота и ширина клетки раздельно.
   Уменьшение — усреднением площади: штриховка тёмных полей сливается в
   ровный серый, контур белой фигуры остаётся."""
import json, sys
import numpy as np
from PIL import Image
def inner(prof, rev=False):
    idx = range(len(prof) - 1, -1, -1) if rev else range(len(prof))
    seen = False
    for i in idx:
        if prof[i] > .75: seen = True
        elif seen: return i
    return None
def cells(fn, S=40):
    a = np.array(Image.open(fn)) < 128
    H, W = a.shape
    r, c = a.mean(1), a.mean(0)
    t = inner(r[:60]); b = inner(r[H - 60:], True) + H - 60
    l = inner(c[:60]); rt = inner(c[W - 60:], True) + W - 60
    ch, cw = (b + 1 - t) / 8, (rt + 1 - l) / 8
    out = np.zeros((64, S, S), np.float32)
    for i in range(8):            # i — строка сверху (8-я горизонталь)
        for j in range(8):
            y0, x0 = t + i * ch, l + j * cw
            m = .06
            sub = a[int(y0 + m * ch):int(y0 + ch - m * ch), int(x0 + m * cw):int(x0 + cw - m * cw)]
            im = Image.fromarray((sub * 255).astype(np.uint8)).resize((S, S), Image.BOX)
            out[i * 8 + j] = np.asarray(im, np.float32) / 255
    return out, (t, b, l, rt)
if __name__ == "__main__":
    allc, meta = [], []
    for v in (1, 2):
        bj = json.load(open(f"work/v{v}/boards.json"))
        for p in sorted(bj, key=int):
            for k, bb in enumerate(bj[p]):
                if bb[2] < 700: continue          # не доски (картинки обложек и т.п.)
                fn = f"work/v{v}/boards/p{int(p):03d}_{k}.png"
                try: c, g = cells(fn)
                except Exception as e: print("fail", fn, e); continue
                allc.append(c); meta.append([v, int(p), k, bb[2]])
    np.save("work/cells.npy", np.stack(allc)); json.dump(meta, open("work/cells_meta.json", "w"))
    print(len(meta))
