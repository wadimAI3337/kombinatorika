"""Клетки -> фигуры -> FEN (только расстановка).
   Эталон класса = среднее по кластерам с этой подписью (отдельно для
   светлых и тёмных полей); клетка относится к ближайшему эталону, запас —
   отрыв от второго. Малый запас = «посмотри глазами»."""
import numpy as np, json
from labels import L, D
C = np.load("work/cells.npy"); meta = json.load(open("work/cells_meta.json"))
N = len(C)
dark = np.array([(i // 8 + i % 8) % 2 == 1 for i in range(64)])
out = np.full((N, 64), ".", dtype="<U1"); marg = np.zeros((N, 64))
for name, mask, lab_map in (("L", ~dark, L), ("D", dark, D)):
    X = C[:, mask].reshape(-1, 1600); lab = np.load(f"work/lab_{name}.npy")
    names = np.array([lab_map.get(k, ".") for k in lab])
    classes = sorted(set(names))
    T = np.stack([X[names == c].mean(0) for c in classes])
    # второй проход: эталоны пересчитываем по уверенно отнесённым
    for _ in range(0):
        d = ((X[:, None, :] - T[None]) ** 2).sum(-1)
        o = np.argsort(d, 1); best = o[:, 0]
        m = d[np.arange(len(X)), o[:, 1]] - d[np.arange(len(X)), best]
        T = np.stack([X[best == i].mean(0) if (best == i).any() else T[i] for i in range(len(classes))])
    d = ((X[:, None, :] - T[None]) ** 2).sum(-1); o = np.argsort(d, 1)
    m = d[np.arange(len(X)), o[:, 1]] - d[np.arange(len(X)), o[:, 0]]
    agree = np.array(classes)[o[:, 0]] == names
    m[~agree] = 0                                  # кластер и эталон спорят — смотреть глазами
    tb = np.array(classes)[o[:, 0]]
    fix = (names == "q") & (tb == "Q")             # белые ферзи, затесавшиеся в кластер чёрных
    names = names.copy(); names[fix] = "Q"; m[fix] = 1
    res = names.reshape(N, -1); mm = m.reshape(N, -1)
    out[:, mask] = res; marg[:, mask] = mm
def fen(row):
    s = ""
    for r in range(8):
        e = 0
        for c in range(8):
            x = row[r * 8 + c]
            if x == ".": e += 1
            else:
                if e: s += str(e); e = 0
                s += x
        if e: s += str(e)
        s += "/" if r < 7 else ""
    return s
res = []
for i, (v, p, k, sz) in enumerate(meta):
    res.append({"v": v, "p": p, "k": k, "size": sz, "fen": fen(out[i]), "minm": float(marg[i].min())})
json.dump(res, open("work/fens.json", "w"), ensure_ascii=False)
mm = np.array([r["minm"] for r in res])
print(len(res), "min margin percentiles", np.percentile(marg, [0.01, 0.1, 1, 50]).round(1))
bad = []
for r in res:
    f = r["fen"]
    if f.count("K") != 1 or f.count("k") != 1 or f.count("P") > 8 or f.count("p") > 8: bad.append(r)
    ranks = f.split("/")
    if any(ch in "Pp" for ch in ranks[0] + ranks[7]): bad.append(r)
print("rule violations", len(bad)); [print(b) for b in bad[:30]]
