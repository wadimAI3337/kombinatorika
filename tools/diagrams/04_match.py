"""Шаг 4. Окончательное распознавание — сопоставление с эталонами.

k-means нужен был только чтобы дёшево получить эталоны. Решение
принимает не он: изображений клетки ровно 26 (12 фигур x 2 цвета поля
плюс два пустых поля), эталон каждого — среднее по «здоровым» членам
своих кластеров.

Дальше каждая клетка сравнивается со всеми эталонами ПОДХОДЯЩЕГО цвета
поля (цвет поля известен точно: доска раскрашена в шахматном порядке,
a1 тёмное). Перебираем сдвиги +-4 px: клетка по высоте на пиксель
меньше, чем по ширине, и к нижней горизонтали набегает сдвиг.

На выходе у каждой клетки есть ЗАПАС — насколько лучший эталон лучше
второго. Маленький запас = «посмотри глазами», и таких клеток видно
поимённо, а не «где-то в 40 тысячах».
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from labels import LAB

W = os.path.dirname(os.path.abspath(__file__))
A = np.load(os.path.join(W, "squares.npy"))
C = A.shape[2]
S = A.reshape(640 * 64, C, C, 3).astype(np.float32) / 255.
lab = np.load(os.path.join(W, "labels_km.npy"))
dist = np.load(os.path.join(W, "dist.npy"))
names = np.load(os.path.join(W, "names.npy"))
K = lab.max() + 1

# цвет поля берём из раскраски доски, а не из картинки клетки:
# a1 тёмное, дальше шахматный порядок. Строка 0 = 8-я горизонталь.
sq_light = np.array([((7 - (j // 8)) + (j % 8)) % 2 == 1 for j in range(64)])

# --- эталоны -------------------------------------------------------
tpl, tname = {}, {}
for k in range(K):
    m = lab == k
    keep = m & (dist <= np.percentile(dist[m], 90))
    piece = LAB[k]
    light = bool(sq_light[np.where(m)[0][0] % 64])
    tpl.setdefault((piece, light), []).append(S[keep].sum(0))
    tname.setdefault((piece, light), 0)
    tname[(piece, light)] += int(keep.sum())
T = {kk: (np.sum(v, 0) / tname[kk]) for kk, v in tpl.items()}
print("эталонов:", len(T), "| ожидалось 26")
for light in (False, True):
    print("  поле", "светлое" if light else "тёмное  ", ":",
          " ".join(sorted(p for (p, l) in T if l == light)))

SH = range(-4, 5)
def shifted(img, dy):
    o = np.empty_like(img)
    if dy == 0: return img
    if dy > 0: o[dy:] = img[:-dy]; o[:dy] = img[dy:dy+1]
    else:      o[:dy] = img[-dy:]; o[dy:] = img[dy-1:dy]
    return o

res = np.empty(640 * 64, "<U1")
margin = np.zeros(640 * 64)
for light in (False, True):
    keys = [kk for kk in T if kk[1] == light]
    bank = np.stack([np.stack([shifted(T[kk], d).ravel() for d in SH]) for kk in keys])  # (P, S, D)
    P_, S_, D_ = bank.shape
    flat = np.ascontiguousarray(bank.reshape(P_ * S_, D_))
    tn = (flat ** 2).sum(1)                       # ||эталон||^2
    idxs = np.where(sq_light[np.arange(640 * 64) % 64] == light)[0]
    for a in range(0, len(idxs), 4096):
        chunk = idxs[a:a + 4096]
        q = S[chunk].reshape(len(chunk), -1)
        # ||q-t||^2 = ||q||^2 - 2 q.t + ||t||^2
        qn = (q ** 2).sum(1)[:, None]
        d2 = (qn + tn[None] - 2.0 * (q @ flat.T)).reshape(len(chunk), P_, S_).min(2)
        d2 = np.maximum(d2, 0.0)
        o = np.argsort(d2, 1)
        res[chunk] = [keys[int(t)][0] for t in o[:, 0]]
        best = d2[np.arange(len(chunk)), o[:, 0]]
        second = d2[np.arange(len(chunk)), o[:, 1]]
        margin[chunk] = (second - best) / np.maximum(second, 1e-9)

np.save(os.path.join(W, "pieces.npy"), res)
np.save(os.path.join(W, "margin.npy"), margin)
agree = (res == np.array([LAB[int(k)] for k in lab])).mean()
print("совпало с разметкой k-means:", f"{agree*100:.3f}%")
print("запас: min %.3f | 1-й процентиль %.3f | медиана %.3f" %
      (margin.min(), np.percentile(margin, 1), np.median(margin)))
