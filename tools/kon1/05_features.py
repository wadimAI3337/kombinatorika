"""Цвет фигур и очередь хода.

Тип фигуры даёт кластер (04), цвет — отдельные признаки: в кластере
белые и чёрные ферзи этого шрифта перемешаны.

* hole  — площадь самой большой замкнутой белой области внутри фигуры
  (без 4 px у краёв клетки: иначе рамка доски замыкает штриховку у
  угловых клеток и чёрная фигура на h8 выглядит белой). Белая ≥150.
* hole0 — то же по всей клетке; только для коней (у белого коня нутро
  доходит до края клетки): белый ≥700.
* qhi / qband — ферзи в полном разрешении и тёмность корпуса. Надёжно
  цвет ферзя не определяется ничем: у белого ферзя полые шарики на
  зубцах, но в скане они часто залиты. Поэтому ферзей раскрашивает
  перебор в 07 по законности авторских ходов, qband — лишь подсказка.
* side  — «1. ?» или «1. ... ?» под диаграммой: по ширине надписи.
"""
import numpy as np, json, os
from scipy import ndimage
from PIL import Image
S = os.environ.get('KON1_WORK', 'work')
cells = np.load(S + '/cells.npy'); typ = np.load(S + '/typ.npy')
B = json.load(open(S + '/boards.json')); fr = json.load(open(S + '/frames.json'))


def hole(c, margin):
    if margin: c = c[margin:-margin, margin:-margin]
    ink = ndimage.binary_closing(c < 140, iterations=1)
    if margin: ink[0, :] = ink[-1, :] = ink[:, 0] = ink[:, -1] = False
    holes = ndimage.binary_fill_holes(ink) & ~ink
    lab, n = ndimage.label(holes)
    return np.bincount(lab.ravel())[1:].max() if n else 0


np.save(S + '/hole.npy', np.array([hole(c, 4) if t != 'E' else 0 for c, t in zip(cells, typ)]))
np.save(S + '/hole0.npy', np.array([hole(c, 0) if t == 'N' else 0 for c, t in zip(cells, typ)]))

pages = {}
def page(pg):
    if pg not in pages: pages[pg] = Image.open(f'{S}/pages/p{pg:03d}.png')
    return pages[pg]

qi = np.where(typ == 'Q')[0]; Q = []
for i in qi:
    b = B[i // 64]; sq = i % 64; r, c = sq // 8, sq % 8
    x0, y0, x1, y1 = b['box']; w = (x1 - x0) / 8; h = (y1 - y0) / 8
    Q.append(np.array(page(b['pg']).crop((int(x0 + c * w), int(y0 + r * h), int(x0 + (c + 1) * w), int(y0 + (r + 1) * h))).resize((128, 128))))
Q = np.array(Q); np.save(S + '/qhi.npy', Q)
np.save(S + '/qband.npy', np.array([(q[62:92, 36:92] < 120).mean() for q in Q]))

W = []
for b in B:
    im = np.array(page(b['pg'])); x0 = b['box'][0]
    yb = fr[str(b['pg'])]['H'][2 * b['r'] + 1][1]
    cols = np.where((im[yb + 8:yb + 110, x0 - 40:x0 + 500] < 110).any(0))[0]
    W.append(int(cols.max() - cols.min()) if len(cols) else -1)
W = np.array(W)
json.dump(np.where(W > np.median(W) * 1.4, 'b', 'w').tolist(), open(S + '/side.json', 'w'))
