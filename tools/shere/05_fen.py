"""Клетки -> FEN (только расстановка) по подписям кластеров (labels.py) с досплитом.
   Потом проверка: каждая клетка — к ближайшему среднему своего класса; расхождения печатаются."""
import numpy as np, json
from labels import L, D, SUB
C = np.load("work/cells.npy"); meta = json.load(open("work/cells_meta.json")); N = len(C)
dark = np.array([(i // 8 + i % 8) % 2 == 1 for i in range(64)])
out = np.full((N, 64), ".", dtype="<U1"); dis = []
for name, mask, lm in (("L", ~dark, L), ("D", dark, D)):
    X = C[:, mask].reshape(-1, 1600); lab = np.load(f"work/lab_{name}.npy")
    names = np.array([lm.get(k, ".") for k in lab])
    for (nm, k0, n), s in SUB.items():
        if nm != name: continue
        idx, sl = np.load(f"work/sub_{nm}{k0}.npy")
        names[idx] = np.array(list(s))[sl]
    classes = sorted(set(names))
    T = np.stack([X[names == c].mean(0) for c in classes])
    d = ((X[:, None, :] - T[None]) ** 2).sum(-1)
    near = np.array(classes)[d.argmin(1)]
    for i in np.where(near != names)[0]: dis.append((name, int(i) // mask.sum(), names[i], near[i]))
    # цвет ферзя: 2-means по клеткам с ферзями, признак — 200 пикселей, где центры
    # групп сильнее всего различаются (у чёрного залито тело короны); как yak/05_fen.py.
    # Спорные доски глав проверяются глазами и вписываются в FIX.
    q = np.where(np.isin(names, ["Q", "q"]))[0]
    if len(q) > 1:
        from sklearn.cluster import KMeans
        km = KMeans(2, n_init=10, random_state=0).fit(X[q])
        blk = int(np.argmax(km.cluster_centers_.mean(1)))
        top = np.argsort(km.cluster_centers_[blk] - km.cluster_centers_[1 - blk])[-200:]
        names[q] = np.where(X[q][:, top].mean(1) > .6, "q", "Q")
    out[:, mask] = names.reshape(N, -1)
FIX = {(26, 0, "g5"): "q", (65, 1, "b8"): "q", (65, 1, "c6"): "Q", (68, 0, "d4"): "Q", (75, 0, "f6"): "q", (120, 1, "e5"): "q"}      # цвет ферзя, проверено глазами
where = {(p, k): i for i, (p, k, sz) in enumerate(meta)}
for (p, k, sq), pc in FIX.items():
    out[where[(p, k)], (8 - int(sq[1])) * 8 + "abcdefgh".index(sq[0])] = pc
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
        if r < 7: s += "/"
    return s
res = [{"p": p, "k": k, "fen": fen(out[i])} for i, (p, k, sz) in enumerate(meta)]
# доски страниц с фотографией (в кластеры не шли): клетка -> ближайшее среднее класса
import importlib.util, os
spec = importlib.util.spec_from_file_location("CC", "03_cells.py"); CC = importlib.util.module_from_spec(spec); spec.loader.exec_module(CC)
TT = {}
for name, mask in (("L", ~dark), ("D", dark)):
    X = C[:, mask].reshape(-1, 1600); nm = out[:, mask].reshape(-1)
    TT[name] = (nm, X)
bj = json.load(open("work/boards.json"))
for p in sorted(CC.LOWRES):
    for k, bb in enumerate(bj.get(str(p), [])):
        if not CC.MIN <= bb[2] <= CC.MAX: continue
        c, _ = CC.C.cells(f"work/boards/p{p:03d}_{k}.png")
        row = np.full(64, ".", dtype="<U1")
        for name, mask in (("L", ~dark), ("D", dark)):
            nm, XT = TT[name]; X = c[mask].reshape(-1, 1600)
            # ближайшая подписанная клетка (1-NN): штриховка увеличенной картинки
            # другая, средние классов тут путают пустое тёмное поле со слоном
            d = (X ** 2).sum(1)[:, None] - 2 * X @ XT.T + (XT ** 2).sum(1)[None]
            row[mask] = nm[d.argmin(1)]
        res.append({"p": p, "k": k, "fen": fen(row), "tmpl": 1})
json.dump(res, open("work/fens.json", "w"))
bad = [r for r in res if r["fen"].count("K") != 1 or r["fen"].count("k") != 1 or
       any(ch in "Pp" for ch in r["fen"].split("/")[0] + r["fen"].split("/")[7])]
print(len(res), "нарушений", len(bad)); [print(b) for b in bad]
print("расхождений с ближайшим классом", len(dis)); [print(x, meta[x[1]][:2]) for x in dis[:30]]
