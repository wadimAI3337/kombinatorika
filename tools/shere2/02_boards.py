"""Поиск диаграмм (work/full, ~300 dpi) и нарезка досок — как yak/02_boards.py:
   рамка со штриховкой тёмных полей — одна большая почти квадратная связная
   компонента. Порядок — левая колонка сверху вниз, потом правая.
   Запуск: python3 02_boards.py 3 335"""
import os, sys, json
import numpy as np
from PIL import Image
from scipy import ndimage
def find(ink):
    sm = ink[::2, ::2]
    sm = ndimage.binary_dilation(sm, iterations=1)
    lab, n = ndimage.label(sm)
    out = []
    for sl in ndimage.find_objects(lab):
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        if min(h, w) < 150 or abs(h - w) > .08 * max(h, w): continue
        out.append((sl[0].start * 2, sl[1].start * 2, h * 2, w * 2))
    return [b for b in out if not any(o != b and o[0] <= b[0] and o[1] <= b[1] and
            o[0] + o[2] >= b[0] + b[2] and o[1] + o[3] >= b[1] + b[3] for o in out)]
if __name__ == "__main__":
    a, b = int(sys.argv[1]), int(sys.argv[2])
    os.makedirs("work/boards", exist_ok=True)
    res = {}
    for p in range(a, b + 1):
        im = Image.open(f"work/full/p{p:03d}.png")
        if im.size[0] != 1600:      # страница с фотографией: картинка вдвое меньше и в оттенках серого
            im = im.resize((1600, round(im.size[1] * 1600 / im.size[0])), Image.LANCZOS)
        ink = np.array(im) < 128
        H, W = ink.shape
        bs = sorted(find(ink), key=lambda t: (t[1] + t[3] / 2 > W / 2, t[0]))
        res[p] = []
        for k, (y, x, h, w) in enumerate(bs):
            pad = 6
            crop = ink[max(0, y - pad):y + h + pad, max(0, x - pad):x + w + pad]
            Image.fromarray((~crop * 255).astype(np.uint8)).save(f"work/boards/p{p:03d}_{k}.png")
            res[p].append([y, x, h, w])
    json.dump(res, open("work/boards.json", "w"))
    import collections
    print(sum(len(v) for v in res.values()), collections.Counter(round(bb[2] / 20) * 20 for v in res.values() for bb in v).most_common(8))
