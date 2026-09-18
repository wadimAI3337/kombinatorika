"""Шаг 3. Ориентация доски — она же очередь хода.

В этом сборнике доска развёрнута к тому, кто решает: если ходят
чёрные, диаграмма повёрнута на 180°, и внизу оказывается 8-я
горизонталь. Значит ориентация — это не просто порядок клеток, а
готовый ответ на вопрос «чей ход», которого в подписи нет.

По раскраске поворот НЕ виден: 180° переводит a1 в h8, а они обе
тёмные, цвета углов сохраняются. Единственный признак — подписи
координат. Берём цифру в правом верхнем углу доски: «8» — белые снизу
(ход белых), «1» — доска перевёрнута (ход чёрных).

Фон под цифрой бывает и светлый, и тёмный, и подсвеченный (шах
подсвечен красным), поэтому перед кластеризацией каждую картинку
нормируем по себе — тогда кластеры делятся по рисунку цифры, а не по
фону.
"""
import os, json, numpy as np
from PIL import Image, ImageDraw
from sklearn.cluster import KMeans

SRC = [("/Users/vadimsamalo/Desktop/Шахматная терапия/12/1 ступень (3-1 разряд)", 1, 320),
       ("/Users/vadimsamalo/Desktop/Шахматная терапия/12/2 ступень (2 разряд-КМС)", 321, 640)]
W = os.path.dirname(os.path.abspath(__file__))

# Подписи кластеров, прочитанные глазами по corner.png (k=6, random_state=0).
# k=4 оказался смешанным — три доски разнесены поимённо.
FLIP_K = {1, 2}                    # кластеры, где цифра «1»
NORM_K = {0, 3, 5}                 # кластеры, где цифра «8»
MIXED = {29: True, 582: True, 622: False}   # True = перевёрнута

def digit(path):
    im = Image.open(path).convert("L"); g = np.array(im, float)
    rp, cp = g.mean(1), g.mean(0); thr = (g.min() + g.max()) / 2
    r, c = np.where(rp > thr)[0], np.where(cp > thr)[0]
    r0, r1, c0, c1 = r[0], r[-1] + 1, c[0], c[-1] + 1
    h, w = (r1 - r0) / 8.0, (c1 - c0) / 8.0
    p = g[int(r0 + h * .02):int(r0 + h * .22),
          int(c0 + 7 * w + w * .78):int(c0 + 8 * w - w * .02)]
    return np.array(Image.fromarray(p).resize((24, 24), Image.BILINEAR), float)

P, names = [], []
for d, lo, hi in SRC:
    for n in range(lo, hi + 1):
        P.append(digit(os.path.join(d, f"{n}.jpg"))); names.append(n)
P = np.stack(P)
X = P.reshape(len(P), -1)
X = (X - X.mean(1, keepdims=True)) / (X.std(1, keepdims=True) + 1e-6)
lab = KMeans(n_clusters=6, n_init=10, random_state=0).fit(X).labels_

flipped = {}
unknown = []
for i, n in enumerate(names):
    if n in MIXED: flipped[n] = MIXED[n]
    elif lab[i] in FLIP_K: flipped[n] = True
    elif lab[i] in NORM_K: flipped[n] = False
    else: unknown.append(n)

if unknown:
    raise SystemExit(f"кластеры разъехались, подписи устарели: {unknown[:10]}")

json.dump({str(k): v for k, v in flipped.items()}, open(os.path.join(W, "flipped.json"), "w"))
print("размеры кластеров:", np.bincount(lab).tolist())
print("обычных  (внизу 1-я горизонталь, ход белых):", sum(1 for v in flipped.values() if not v))
print("перевёрнутых (внизу 8-я, ход чёрных):      ", sum(1 for v in flipped.values() if v))

sheet = Image.new("RGB", (6 * 110, 140), (20, 20, 20)); dr = ImageDraw.Draw(sheet)
for k in range(6):
    sheet.paste(Image.fromarray(P[lab == k].mean(0).astype(np.uint8)).convert("RGB")
                .resize((96, 96), Image.LANCZOS), (k * 110 + 8, 8))
    tag = "1/перев" if k in FLIP_K else "8/обычн" if k in NORM_K else "СМЕШАН"
    dr.text((k * 110 + 8, 112), f"k={k} n={(lab==k).sum()} {tag}", fill=(255, 220, 120))
sheet.save(os.path.join(W, "corner.png"))
print("контроль глазами: corner.png")
