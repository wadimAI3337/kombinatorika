"""Шаг 9b. Чей ход — из подписи под диаграммой.

В книге под каждой диаграммой стоит «1. ?» (ход белых) или «1. ... ?»
(ход чёрных).  Различать их OCR-ом не нужно: достаточно посмотреть,
как далеко вправо уходит чернота — многоточие сдвигает «?» вправо.
Гистограмма строго бимодальна, порог попадает в пустой зазор.
"""
import numpy as np, json
from PIL import Image
from scipy import ndimage as ndi

meta = json.load(open('kmeta.json'))
xs = []
for m in meta:
    n = f"{m['test']:02d}_{m['num']:02d}.png"
    a = np.asarray(Image.open('kcap/'+n).convert('L')).astype(np.float32)[4:-4, 4:-4]
    d = a < np.median(a) - 60
    lab, k = ndi.label(d)                        # выкидываем точечный шум скана
    if k:
        sz = ndi.sum(d, lab, range(1, k+1))
        keep = np.zeros(k+1, bool); keep[1:][sz >= 10] = True
        d = keep[lab]
    cols = np.where(d.sum(0) > 0)[0]
    xs.append(int(cols.max()) if len(cols) else -1)
xs = np.array(xs)
np.save('capx.npy', xs)
print(np.histogram(xs, bins=25))                 # проверить, что зазор есть
print('белые:', (xs < 73).sum(), 'чёрные:', (xs >= 73).sum())
