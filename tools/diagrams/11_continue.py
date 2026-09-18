"""Шаг 11. Продолжение «для показа».

Решение часто состоит из одного тихого хода: нашёл — и всё, у соперника
дальше свободный выбор. Считать там больше нечего, но и обрывать доску
сразу после находки жалко: не видно, ради чего ход делался.

Поэтому к каждой задаче добавляем 2 полухода (ответ соперника и наш
ход), которые в решение НЕ входят. Длина задачи и разделы от этого не
меняются: показ лежит отдельным полем и виден только в разборе, уже
после того, как задача решена.

Матовые варианты не трогаем: там и так всё сказано.
"""
import os, json, subprocess, chess
from multiprocessing import Pool

W = os.path.dirname(os.path.abspath(__file__))
SF = os.environ.get("SF_PATH", "stockfish")
DEPTH = int(os.environ.get("SF_DEPTH", 18))
EXTRA = 2          # полуходов показа: ответ соперника + наш ход

class Eng:
    def __init__(self):
        self.p = subprocess.Popen([SF], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, bufsize=1)
        self.send("uci"); self.wait("uciok")
        self.send("setoption name Threads value 1"); self.send("setoption name Hash value 128")
        self.send("isready"); self.wait("readyok")
    def send(self, c): self.p.stdin.write(c + "\n"); self.p.stdin.flush()
    def wait(self, tok):
        for line in self.p.stdout:
            if line.startswith(tok): return line
    def pv(self, fen):
        self.send("ucinewgame"); self.send(f"position fen {fen}"); self.send(f"go depth {DEPTH}")
        out = []
        for line in self.p.stdout:
            if line.startswith("info ") and " pv " in line:
                t = line.split(); out = t[t.index("pv") + 1:]
            elif line.startswith("bestmove"): return out

def work(r):
    if not r["m"] or r["m"][-1][1].endswith("#"):
        r["c"] = []; return r
    fen = r["m"][-1][2]
    b = chess.Board(fen)
    if b.is_game_over(): r["c"] = []; return r
    rows = []
    for u in work.eng.pv(fen)[:EXTRA]:
        try: mv = chess.Move.from_uci(u)
        except Exception: break
        if mv not in b.legal_moves: break
        san = b.san(mv); b.push(mv)
        rows.append([u, san, b.fen()])
        if b.is_checkmate(): break
    if len(rows) % 2: rows = rows[:-1]      # показ кончаем ходом решающей стороны
    r["c"] = rows
    return r

def init(): work.eng = Eng()

if __name__ == "__main__":
    data = json.load(open(os.path.join(W, "solved.json")))
    n = min(os.cpu_count() or 4, 10)
    with Pool(n, initializer=init) as pool:
        res = list(pool.imap_unordered(work, data, chunksize=4))
    res.sort(key=lambda r: r["n"])
    json.dump(res, open(os.path.join(W, "solved.json"), "w"), ensure_ascii=False)
    got = sum(1 for r in res if r["c"])
    print("задач:", len(res), "| с продолжением:", got,
          "| без (мат или конец партии):", len(res) - got)
