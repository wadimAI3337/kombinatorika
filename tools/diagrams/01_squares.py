"""Шаг 1. Диаграмма -> 64 картинки клеток.

Доски отрисованы движком (не скан), поэтому геометрия простая:
доска лежит на тёмном фоне (яркость ~19), сама доска светлая (~175).
Границу берём по профилю яркости, дальше делим на 8x8.
Высоту и ширину клетки считаем РАЗДЕЛЬНО: кропы неквадратные.
"""
import os, sys, numpy as np
from PIL import Image

SRC = [
    ("/Users/vadimsamalo/Desktop/Шахматная терапия/12/1 ступень (3-1 разряд)", 1, 320),
    ("/Users/vadimsamalo/Desktop/Шахматная терапия/12/2 ступень (2 разряд-КМС)", 321, 640),
]
OUT = os.path.dirname(os.path.abspath(__file__))
CELL = 64          # к какому размеру приводим клетку
MARGIN = 0.12      # обрезаем края клетки: там подписи координат a-h / 1-8

def board_box(g):
    """Границы доски: строки/столбцы, где средняя яркость выше порога фона."""
    rp, cp = g.mean(1), g.mean(0)
    thr = (g.min() + g.max()) / 2
    rows = np.where(rp > thr)[0]
    cols = np.where(cp > thr)[0]
    return rows[0], rows[-1] + 1, cols[0], cols[-1] + 1

def squares(path):
    im = Image.open(path).convert("RGB")
    g = np.array(im.convert("L"), float)
    r0, r1, c0, c1 = board_box(g)
    h, w = (r1 - r0) / 8.0, (c1 - c0) / 8.0
    a = np.array(im)
    out = np.zeros((64, CELL, CELL, 3), np.uint8)
    for r in range(8):
        for c in range(8):
            y0, y1 = r0 + r * h, r0 + (r + 1) * h
            x0, x1 = c0 + c * w, c0 + (c + 1) * w
            dy, dx = (y1 - y0) * MARGIN, (x1 - x0) * MARGIN
            cell = a[int(round(y0 + dy)):int(round(y1 - dy)),
                     int(round(x0 + dx)):int(round(x1 - dx))]
            out[r * 8 + c] = np.array(Image.fromarray(cell).resize((CELL, CELL), Image.BILINEAR))
    return out, (r1 - r0, c1 - c0)

if __name__ == "__main__":
    all_sq, names, sizes = [], [], []
    for d, lo, hi in SRC:
        for n in range(lo, hi + 1):
            p = os.path.join(d, f"{n}.jpg")
            sq, sz = squares(p)
            all_sq.append(sq); names.append(n); sizes.append(sz)
    A = np.stack(all_sq)                       # (640, 64, CELL, CELL, 3)
    np.save(os.path.join(OUT, "squares.npy"), A)
    np.save(os.path.join(OUT, "names.npy"), np.array(names))
    sz = np.array(sizes)
    print("досок:", A.shape[0], "| клеток:", A.shape[0] * 64)
    print("размер доски px: высота", sz[:,0].min(), "-", sz[:,0].max(),
          "| ширина", sz[:,1].min(), "-", sz[:,1].max())
    print("несквадратность (|h-w| max):", int(np.abs(sz[:,0]-sz[:,1]).max()))
