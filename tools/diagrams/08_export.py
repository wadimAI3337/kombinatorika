"""Шаг 8. Выгрузка результата.

Поля те же, что у книжных сборников на сайте, кроме `m`: решения в
папках с диаграммами нет, и брать его неоткуда.
"""
import os, json, numpy as np

W = os.path.dirname(os.path.abspath(__file__))
recs = json.load(open(os.path.join(W, "positions.json")))
keep = {r["n"] for r in json.load(open(os.path.join(W, "keep.json")))}
M = np.load(os.path.join(W, "margin.npy")).reshape(640, 64)
names = [int(x) for x in np.load(os.path.join(W, "names.npy"))]

DIR = {1: "1 ступень (3-1 разряд)", 2: "2 ступень (2 разряд-КМС)"}
out = []
for r in recs:
    n = r["n"]; step = 1 if n <= 320 else 2
    out.append({
        "n": n,
        "src": f"{DIR[step]}/{n}.jpg",
        "step": step,                       # ступень: 1 = 3-1 разряд, 2 = 2 разряд-КМС
        "f": r["fen"],                      # FEN
        "s": r["s"],                        # чей ход (из разворота диаграммы)
        "cas": r["cas"],
        "flipped": r["flipped"],            # диаграмма была повёрнута на 180°
        "dup": n not in keep,               # расстановка уже есть на сайте
        "minmargin": round(float(M[names.index(n)].min()), 3),
    })

p = os.path.join(W, "..", "out", "step12_positions.json")
json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
new = [o for o in out if not o["dup"]]
print("распознано:", len(out), "| дублей с сайтом:", sum(o["dup"] for o in out), "| новых:", len(new))
print("  1 ступень:", sum(1 for o in new if o["step"] == 1),
      "| 2 ступень:", sum(1 for o in new if o["step"] == 2))
print("  ход белых:", sum(1 for o in new if o["s"] == "w"),
      "| ход чёрных:", sum(1 for o in new if o["s"] == "b"))
print("файл:", os.path.normpath(p), round(os.path.getsize(p) / 1024), "KB")
