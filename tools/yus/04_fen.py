"""Клетки -> FEN. Чистые кластеры берут свою подпись; клетки смешанных
   кластеров ('?') относятся к ближайшему эталону чистых классов своего цвета поля."""
import numpy as np, json
from labels import L, D
C = np.load("work/cells.npy"); meta = json.load(open("work/cells_meta.json")); N = len(C)
dark = np.array([(i // 8 + i % 8) % 2 == 1 for i in range(64)])
out = np.full((N, 64), ".", dtype="<U1")
for name, mask, lm in (("L", ~dark, L), ("D", dark, D)):
    X = C[:, mask].reshape(-1, 1600); lab = np.load(f"work/lab_{name}.npy")
    names = np.array([lm.get(k, ".") for k in lab])
    classes = sorted(set(names) - {"?"})
    T = np.stack([X[names == c].mean(0) for c in classes])
    for k in sorted(set(lab[names == "?"])):
        idx = np.where((lab == k) & (names == "?"))[0]
        if (name, k) == ("L", 45):
            # только ферзи: чёрный залит, белый — контур
            ink = X[idx].mean(1)
            names[idx] = np.where(ink > (ink.min() + ink.max()) / 2, "q", "Q")
            continue
        cl, TT = list(classes), T
        if (name, k) == ("D", 16):
            # бледная печать: своё «пусто»
            cl = cl + ["."]; TT = np.vstack([T, X[idx].mean(0, keepdims=True)])
        d = ((X[idx, None, :] - TT[None]) ** 2).sum(-1)
        names[idx] = np.array(cl)[d.argmin(1)]
    out[:, mask] = names.reshape(N, -1)
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
