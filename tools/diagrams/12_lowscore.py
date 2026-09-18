"""Шаг 12. Удлинить вариант там, где перевес маленький.

Обычное правило обрывает вариант, как только у соперника появляется
свободный выбор. В разгромных позициях этого хватает: ход найден —
всё понятно. Но там, где оценка около нуля (задача на спасение) или
перевес маленький, после одного хода не видно вообще ничего.

Для таких задач ведём вариант до 4 ходов решающей стороны.

Считаем ОДИН раз на позицию, с MultiPV 2: главный вариант даёт сами
ходы, а отрыв от второго показывает, единственный ли ключевой ход.
Пересчитывать на каждом полуходе — верный способ ждать полчаса ради
52 задач, проверено.
"""
import os, json, subprocess, chess
from multiprocessing import Pool

W = os.path.dirname(os.path.abspath(__file__))
SF = os.environ.get("SF_PATH", "stockfish")
DEPTH = int(os.environ.get("SF_DEPTH", 20))
LOW = 150          # «маленький перевес» — сантипешки
WANT = 7           # полуходов: 4 хода решающей стороны

class Eng:
    def __init__(self):
        self.p = subprocess.Popen([SF], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, bufsize=1)
        self.send("uci"); self.wait("uciok")
        self.send("setoption name Threads value 1"); self.send("setoption name Hash value 128")
        self.send("setoption name MultiPV value 2")
        self.send("isready"); self.wait("readyok")
    def send(self, c): self.p.stdin.write(c + "\n"); self.p.stdin.flush()
    def wait(self, tok):
        for line in self.p.stdout:
            if line.startswith(tok): return line
    def top2(self, fen):
        self.send("ucinewgame"); self.send(f"position fen {fen}"); self.send(f"go depth {DEPTH}")
        best = {}
        for line in self.p.stdout:
            if line.startswith("info ") and " pv " in line and " multipv " in line:
                t = line.split()
                best[int(t[t.index("multipv") + 1])] = (
                    t[t.index("pv") + 1:],
                    (t[t.index("score") + 1], int(t[t.index("score") + 2])))
            elif line.startswith("bestmove"):
                return best

def norm(k, v): return (100000 - abs(v)) * (1 if v > 0 else -1) if k == "mate" else v

def work(r):
    top = work.eng.top2(r["f"])
    if 1 not in top or not top[1][0]: return r
    pv, sc = top[1]
    b = chess.Board(r["f"]); rows = []
    for u in pv[:WANT]:
        try: mv = chess.Move.from_uci(u)
        except Exception: break
        if mv not in b.legal_moves: break
        san = b.san(mv); b.push(mv)
        rows.append([u, san, b.fen()])
        if b.is_checkmate() or b.is_stalemate() or b.is_insufficient_material(): break
    if len(rows) % 2 == 0: rows = rows[:-1]      # кончаем ходом решающей стороны
    if rows:
        r["m"] = [[u, s, f, 0, ""] for u, s, f in rows]
        gap = norm(*sc) - norm(*top[2][1]) if 2 in top else 9999
        r["relow"] = {"gap": gap}                # отрыв ключевого хода от второго
    return r

def init(): work.eng = Eng()

if __name__ == "__main__":
    data = json.load(open(os.path.join(W, "solved.json")))
    todo = [r for r in data if r["mate_in"] is None and r["cp"] is not None and r["cp"] < LOW]
    print("задач с маленьким перевесом:", len(todo), flush=True)
    with Pool(min(os.cpu_count() or 4, 10), initializer=init) as pool:
        done = {r["n"]: r for r in pool.imap_unordered(work, todo, chunksize=2)}
    out = [done.get(r["n"], r) for r in data]
    json.dump(out, open(os.path.join(W, "solved.json"), "w"), ensure_ascii=False)
    import collections
    h = collections.Counter(len(done[n]["m"]) for n in done)
    ties = [n for n in done if done[n].get("relow", {}).get("gap", 9999) < 30]
    print("длина после удлинения (полуходы):", dict(sorted(h.items())))
    print("где ключевой ход не единственный (отрыв <0.30):", len(ties), sorted(ties))
