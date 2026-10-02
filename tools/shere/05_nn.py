"""FEN без подписей кластеров: клетка -> ближайшая (1-NN) клетка эталонных досок.
   Эталон — work/gt.json (gt.py: FEN уже расшифрованных досок из shere.js по порядку [[DIAG]]).
   Нужен, когда кластеры 04_cluster.py вышли другими (другая версия sklearn) и labels.py не подходит.
   Эталонные доски берут FEN из эталона, остальные — 1-NN. Проверка: каждая эталонная страница
   распознаётся без своих клеток. Пишет work/fens.json. Запуск: python3 05_nn.py"""
import numpy as np, json
C = np.load("work/cells.npy").reshape(-1, 64, 1600); meta = json.load(open("work/cells_meta.json"))
where = {(p, k): i for i, (p, k, sz) in enumerate(meta)}
gt = {(p, k): f for p, k, f in json.load(open("work/gt.json")) if f and (p, k) in where}
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
ti = [where[k] for k in gt]; tp = np.array([k[0] for k in gt])
TL = np.array([rows(gt[k]) for k in gt])           # n x 64
def predict(idx, excl_page=None):
    keep = tp != excl_page if excl_page else np.ones(len(ti), bool)
    out = np.full((len(idx), 64), ".", dtype="<U1")
    for mask in (~dark, dark):
        XT = C[np.array(ti)[keep]][:, mask].reshape(-1, 1600); YT = TL[keep][:, mask].reshape(-1)
        X = C[idx][:, mask].reshape(-1, 1600)
        d = (X ** 2).sum(1)[:, None] - 2 * X @ XT.T + (XT ** 2).sum(1)[None]
        out[:, mask] = YT[d.argmin(1)].reshape(len(idx), -1)
    return out
err = 0
for p in sorted(set(tp)):
    ks = [k for k in gt if k[0] == p]
    pr = predict([where[k] for k in ks], p)
    for k, r in zip(ks, pr):
        bad = [(i, a, b) for i, (a, b) in enumerate(zip(rows(gt[k]), r)) if a != b]
        if bad: err += 1; print("эталон", k, ["abcdefgh"[i % 8] + str(8 - i // 8) + f" {a}->{b}" for i, a, b in bad])
print("эталонных досок", len(gt), "с ошибками", err)
rest = [i for i, (p, k, sz) in enumerate(meta) if (p, k) not in gt]
pr = predict(rest)
res = [{"p": p, "k": k, "fen": f} for (p, k), f in gt.items()] + [{"p": meta[i][0], "k": meta[i][1], "fen": fen(r)} for i, r in zip(rest, pr)]
# доски страниц с фотографией (в cells.npy не попали)
import importlib.util
spec = importlib.util.spec_from_file_location("CC", "03_cells.py"); CC = importlib.util.module_from_spec(spec); spec.loader.exec_module(CC)
bj = json.load(open("work/boards.json"))
for p in sorted(CC.LOWRES):
    for k, bb in enumerate(bj.get(str(p), [])):
        if not CC.MIN <= bb[2] <= CC.MAX: continue
        c, _ = CC.C.cells(f"work/boards/p{p:03d}_{k}.png")
        C = np.concatenate([C, c.reshape(1, 64, 1600)])
        res.append({"p": p, "k": k, "fen": fen(predict([len(C) - 1])[0]), "tmpl": 1})
FIX = {(142, 0, "a8"): "Q", (149, 1, "f8"): "r", (157, 0, "f8"): "r", (177, 1, "d7"): "Q", (181, 0, "h8"): "r", (183, 0, "b4"): "r", (195, 1, "e3"): "Q", (195, 2, "e3"): "Q", (199, 0, "g4"): ".", (199, 0, "f4"): "P", (199, 1, "g4"): ".", (199, 1, "f4"): "P", (200, 0, "g4"): ".", (200, 0, "f4"): "P", (200, 0, "b1"): "q", (213, 0, "f8"): "Q", (214, 0, "f8"): "Q", (214, 1, "f8"): "Q", (216, 0, "e1"): "Q", (225, 0, "h8"): "r", (270, 1, "d8"): "q", (270, 1, "c6"): "Q", (271, 1, "e6"): "Q", (290, 1, "a8"): "Q", (290, 1, "b6"): "q", (290, 2, "b7"): "Q"}      # цвет ферзя и ошибки 1-NN, проверено глазами
for r in res:
    for (p, k, sq), pc in FIX.items():
        if (r["p"], r["k"]) == (p, k):
            row = rows(r["fen"]); row[(8 - int(sq[1])) * 8 + "abcdefgh".index(sq[0])] = pc; r["fen"] = fen(row)
json.dump(res, open("work/fens.json", "w"))
bad = [r for r in res if r["fen"].count("K") != 1 or r["fen"].count("k") != 1 or
       any(ch in "Pp" for ch in r["fen"].split("/")[0] + r["fen"].split("/")[7])]
print(len(res), "нарушений", len(bad)); [print(b) for b in bad]
