"""Шаг 6b. k-means по картинкам клеток -> ~420 кластеров.

Зачем кластеризация, а не классификатор: размеченных данных нет.
Кластеры чистые (одна фигура одного цвета), поэтому достаточно
один раз глазами подписать 420 усреднённых картинок — это 15 листов
контактной печати, 20 минут работы, дальше всё автоматически.

k подбирается так, чтобы кластеры были заведомо ПЕРЕсегментированы:
лучше 420 чистых кластеров, чем 80 смешанных.
"""
import numpy as np
from sklearn.cluster import KMeans
from PIL import Image

F = np.load('kn2F.npy')                      # (N, 48*48) нормализованные клетки
km = KMeans(n_clusters=420, n_init=2, random_state=0).fit(F)
np.save('kn2lab.npy', km.labels_)
b = np.bincount(km.labels_, minlength=420)
order = np.argsort(-b)                       # крупные кластеры первыми
np.save('kn2order.npy', order)

# центроиды в исходном разрешении — их и разглядываем
Nc = np.load('kn2Nc.npy').astype(np.float32)
mean = np.zeros((420, 48, 48), np.float32)
for i in range(420):
    m = km.labels_ == i
    if m.sum(): mean[i] = Nc[m].mean(0)
np.save('kn2mean.npy', mean)

# контактные листы: 28 кластеров на лист, порядок = order
for p in range(0, 420, 28):
    ids = order[p:p+28]
    rows = (len(ids)+6)//7
    M = np.full((rows*50, 7*50), 255, np.uint8)
    for k, i in enumerate(ids):
        r, c = divmod(k, 7)
        M[r*50+1:r*50+49, c*50+1:c*50+49] = np.clip(mean[i], 0, 255).astype(np.uint8)
    Image.fromarray(M).resize((7*50*3, rows*50*3), Image.LANCZOS).save(f'sheet_{p//28:02d}.png')
print('готово: sheet_00.png ... подписать вручную -> labels.py')
