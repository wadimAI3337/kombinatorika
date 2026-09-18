"""Шаг 2. Кластеризация клеток.

Доски отрисованы одним движком, значит различных изображений клетки
ровно 26: 12 фигур x 2 цвета поля + 2 пустых поля. Кластеризуем с
запасом (k=48) — лишние кластеры окажутся дублями, их подписи совпадут.

Сжимаем клетку 64->32 (ровно вдвое, без сглаживания) и гоняем PCA:
на сырых 12288 измерениях k-means считается минутами, на 48 главных
компонентах — секунды, а разделение то же: дисперсию здесь даёт
именно форма фигуры.
"""
import os, numpy as np
from PIL import Image
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

W = os.path.dirname(os.path.abspath(__file__))
A = np.load(os.path.join(W, "squares.npy"))          # (640,64,64,64,3)
N, _, C, _, _ = A.shape
S = A.reshape(N * 64, C, C, 3)

half = S[:, ::2, ::2, :].astype(np.float32) / 255.0  # 64 -> 32, без сглаживания
X = half.reshape(len(S), -1)

pc = PCA(n_components=48, random_state=0).fit(X[::7])
Z = pc.transform(X)
print("PCA: объяснено дисперсии", round(float(pc.explained_variance_ratio_.sum()), 4))

K = 48
km = KMeans(n_clusters=K, n_init=10, random_state=0).fit(Z)
lab = km.labels_
d = np.linalg.norm(Z - km.cluster_centers_[lab], axis=1)

np.save(os.path.join(W, "labels_km.npy"), lab)
np.save(os.path.join(W, "dist.npy"), d)

order = np.argsort(-np.bincount(lab, minlength=K))
np.save(os.path.join(W, "order.npy"), order)
print("кластеры в порядке контактного листа (индекс_в_листе кластер: размер, max расст.):")
for i, k in enumerate(order):
    m = lab == k
    print(f"  [{i:2d}] k={k:2d}: {m.sum():6d}  max={d[m].max():6.2f}  p99={np.percentile(d[m],99):5.2f}")

# контактный лист: усреднённая картинка кластера, 8 в ряд
rows = (K + 7) // 8
sheet = Image.new("RGB", (8 * (C + 10), rows * (C + 10)), (25, 25, 25))
for i, k in enumerate(order):
    avg = S[lab == k].mean(0).astype(np.uint8)
    sheet.paste(Image.fromarray(avg), ((i % 8) * (C + 10) + 5, (i // 8) * (C + 10) + 5))
sheet.save(os.path.join(W, "sheet.png"))
print("контактный лист: sheet.png, 8 в ряд, порядок как выше")
