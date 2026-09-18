"""Шаг 13. Задачи с двумя равноценными ключевыми ходами.

У части задач на спасение движок не выделяет один ход: второй по силе
отстаёт меньше чем на 0.30. Требовать там угадать конкретный ход
нечестно — он не «правильнее», просто движок выбрал его первым.

Поэтому для таких задач считаем ОБА хода и оба варианта целиком.
Сайт принимает любой из двух и ведёт тот вариант, который сыграли, а
после решения говорит, который всё-таки сильнее и на сколько.

Поля: `m` — сильнейший вариант, `a` — второй, `ab` — две подписи
(что показать, если сыграли первый / если второй).
"""
import os, json, subprocess, chess
from multiprocessing import Pool

W = os.path.dirname(os.path.abspath(__file__))
SF = os.environ.get("SF_PATH", "stockfish")
DEPTH = int(os.environ.get("SF_DEPTH", 22))
TIE = 30           # отрыв в сантипешках, ниже которого ходы считаем равными
WANT = 7           # полуходов: 4 хода решающей стороны

class Eng:
    def __init__(self):
        self.p = subprocess.Popen([SF], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, bufsize=1)
        self.send("uci"); self.wait("uciok")
        self.send("setoption name Threads value 1"); self.send("setoption name Hash value 128")
        self.send("setoption name MultiPV value 2"); self.send("isready"); self.wait("readyok")
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
            elif line.startswith("bestmove"): return best

def norm(k, v): return (100000 - abs(v)) * (1 if v > 0 else -1) if k == "mate" else v
def show(k, v): return ("мат в %d" % abs(v)) if k == "mate" else ("%+.2f" % (v / 100))

def line_of(fen, pv):
    b = chess.Board(fen); rows = []
    for u in pv[:WANT]:
        try: mv = chess.Move.from_uci(u)
        except Exception: break
        if mv not in b.legal_moves: break
        san = b.san(mv); b.push(mv); rows.append([u, san, b.fen()])
        if b.is_checkmate() or b.is_stalemate() or b.is_insufficient_material(): break
    if len(rows) % 2 == 0: rows = rows[:-1]
    return rows

def work(r):
    top = work.eng.top2(r["f"])
    if not top or 1 not in top or 2 not in top: return r
    m1 = line_of(r["f"], top[1][0]); m2 = line_of(r["f"], top[2][0])
    if not m1 or not m2 or m1[0][0] == m2[0][0]: return r
    s1, s2 = show(*top[1][1]), show(*top[2][1])
    a, bq = m1[0][1], m2[0][1]
    r["m"] = [[u, s, f, 0, ""] for u, s, f in m1]
    r["a"] = [[u, s, f, 0, ""] for u, s, f in m2]
    r["ab"] = [f"{a} ({s1}) — сильнейший. {bq} ({s2}) тоже решает.",
               f"{bq} ({s2}) решает, но {a} ({s1}) чуть сильнее."]
    return r

def init(): work.eng = Eng()

if __name__ == "__main__":
    data = json.load(open(os.path.join(W, "solved.json")))
    todo = [r for r in data if r.get("relow", {}).get("gap", 9999) < TIE]
    print("задач с двумя равноценными ходами:", len(todo), flush=True)
    with Pool(min(os.cpu_count() or 4, 10), initializer=init) as pool:
        done = {r["n"]: r for r in pool.imap_unordered(work, todo, chunksize=1)}
    out = [done.get(r["n"], r) for r in data]
    json.dump(out, open(os.path.join(W, "solved.json"), "w"), ensure_ascii=False)
    got = [n for n in done if done[n].get("a")]
    print("получили два варианта:", len(got), sorted(got))
    for n in sorted(got)[:6]: print("  №%d: %s" % (n, done[n]["ab"][0]))
