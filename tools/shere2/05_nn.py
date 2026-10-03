"""FEN досок второй книги: клетка -> ближайшая (1-NN) клетка эталонных досок.
   Эталон — доски первой книги (gt1.py: FEN из shere.js по порядку [[DIAG]], клетки — ../shere/work/cells.npy)
   плюс уже проверенные доски этой книги (work/gt2.json, пишет gt2.py после расшифровки глав).
   Доски страниц с фото (LOWRES) — тем же 1-NN. Правки глазами — FIX. Пишет work/fens.json.
   Запуск: python3 05_nn.py"""
import numpy as np, json, os, importlib.util
S1 = "../shere/work"
dark = np.array([(i // 8 + i % 8) % 2 == 1 for i in range(64)])
def rows(f):
    r = []
    for row in f.split("/"):
        for ch in row: r += ["."] * int(ch) if ch.isdigit() else [ch]
    return r
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
# эталон: первая книга
C1 = np.load(f"{S1}/cells.npy").reshape(-1, 64, 1600); m1 = json.load(open(f"{S1}/cells_meta.json"))
w1 = {(p, k): i for i, (p, k, sz) in enumerate(m1)}
gt1 = [(w1[(p, k)], f) for p, k, f in json.load(open("work/gt1.json")) if f and (p, k) in w1]
# вторая книга
C = np.load("work/cells.npy").reshape(-1, 64, 1600); meta = json.load(open("work/cells_meta.json"))
where = {(p, k): i for i, (p, k, sz) in enumerate(meta)}
gt2 = {(p, k): f for p, k, f in json.load(open("work/gt2.json"))} if os.path.exists("work/gt2.json") else {}
gt2 = {k: f for k, f in gt2.items() if f and k in where}
XT = np.concatenate([C1[[i for i, f in gt1]], C[[where[k] for k in gt2]]]) if gt2 else C1[[i for i, f in gt1]]
TL = np.array([rows(f) for i, f in gt1] + [rows(f) for f in gt2.values()])
def predict(X):
    out = np.full((len(X), 64), ".", dtype="<U1")
    for mask in (~dark, dark):
        xt = XT[:, mask].reshape(-1, 1600); yt = TL[:, mask].reshape(-1)
        x = X[:, mask].reshape(-1, 1600)
        d = (x ** 2).sum(1)[:, None] - 2 * x @ xt.T + (xt ** 2).sum(1)[None]
        out[:, mask] = yt[d.argmin(1)].reshape(len(X), -1)
    return out
res = [{"p": p, "k": k, "fen": f} for (p, k), f in gt2.items()]
rest = [i for i, (p, k, sz) in enumerate(meta) if (p, k) not in gt2]
for a in range(0, len(rest), 100):
    ch = rest[a:a + 100]
    for i, r in zip(ch, predict(C[ch])): res.append({"p": meta[i][0], "k": meta[i][1], "fen": fen(r)})
spec = importlib.util.spec_from_file_location("CC", "03_cells.py"); CC = importlib.util.module_from_spec(spec); spec.loader.exec_module(CC)
bj = json.load(open("work/boards.json"))
for p in sorted(CC.LOWRES):
    for k, bb in enumerate(bj.get(str(p), [])):
        if not CC.MIN <= bb[2] <= CC.MAX or (p, k) in gt2: continue
        c, _ = CC.C.cells(f"work/boards/p{p:03d}_{k}.png")
        res.append({"p": p, "k": k, "fen": fen(predict(c.reshape(1, 64, 1600))[0]), "tmpl": 1})
FIX = {(118, 1, "e7"): "q"}      # (стр, № доски, поле): фигура; «.» — пусто. Проверено глазами
for r in res:
    for (p, k, sq), pc in FIX.items():
        if (r["p"], r["k"]) == (p, k):
            row = rows(r["fen"]); row[(8 - int(sq[1])) * 8 + "abcdefgh".index(sq[0])] = pc; r["fen"] = fen(row)
res.sort(key=lambda r: (r["p"], r["k"]))
json.dump(res, open("work/fens.json", "w"))
bad = [r for r in res if r["fen"].count("K") != 1 or r["fen"].count("k") != 1 or
       any(ch in "Pp" for ch in r["fen"].split("/")[0] + r["fen"].split("/")[7])]
print(len(res), "нарушений", len(bad)); [print(b) for b in bad]
