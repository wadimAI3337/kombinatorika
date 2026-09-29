"""Клетки -> FEN (только расстановка): подпись кластера. Цвет ферзя кластер
   путает (на штриховке белый и чёрный ферзь похожи) — его решает заливка тела
   короны: у чёрного > 0.525. Единичные ошибки кластеров — в FIX глазами."""
import numpy as np, json
from labels import L, D
C = np.load("work/cells.npy"); meta = json.load(open("work/cells_meta.json")); N = len(C)
dark = np.array([(i // 8 + i % 8) % 2 == 1 for i in range(64)])
out = np.full((N, 64), ".", dtype="<U1"); dis = []
for name, mask, lm in (("L", ~dark, L), ("D", dark, D)):
    X = C[:, mask].reshape(-1, 1600); lab = np.load(f"work/lab_{name}.npy")
    names = np.array([lm.get(k, ".") for k in lab])
    classes = sorted(set(names))
    T = np.stack([X[names == c].mean(0) for c in classes])
    d = ((X[:, None, :] - T[None]) ** 2).sum(-1)
    near = np.array(classes)[d.argmin(1)]
    for i in np.where(near != names)[0]: dis.append((name, int(i), names[i], near[i]))
    q = np.isin(names, ["Q", "q"])
    body = X.reshape(-1, 40, 40)[:, 22:32, 12:28].mean((1, 2))
    names[q] = np.where(body[q] > .525, "q", "Q")
    out[:, mask] = names.reshape(N, -1)
FIX = {(47, 0, "b2"): "B", (72, 1, "a1"): "r"}      # слон в «пустых», ладья в «пешках»
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
json.dump(res, open("work/fens.json", "w"))
bad = [r for r in res if r["fen"].count("K") != 1 or r["fen"].count("k") != 1 or
       any(ch in "Pp" for ch in r["fen"].split("/")[0] + r["fen"].split("/")[7])]
print(len(res), "нарушений", len(bad)); [print(b) for b in bad]
