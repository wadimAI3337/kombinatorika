"""Шаг 9. Решения движком.

Решений в папках с диаграммами нет, поэтому вариант считает Stockfish.
Позиция и очередь хода уже известны точно, так что это обычный прогон,
без угадывания.

ДЛИНА ВАРИАНТА — главное здесь. Правила:

* мат — ведём до мата целиком, даже если он длинный: там всё
  форсированно, считать легко;
* не мат — обрываем там, где тактика КОНЧИЛАСЬ, то есть где материальный
  перевес перестал меняться. Тянуть выигрыш фигуры до восьми ходов
  бессмысленно: дальше идёт обычная игра, а не решение;
* потолок — 8 ходов решающей стороны (15 полуходов). Больше человеку
  считать незачем. Для форсированного мата потолок выше — 11 ходов;
* вариант всегда кончается ходом решающей стороны (нечётное число
  полуходов) — так устроены все сборники на сайте.
"""
import os, sys, json, subprocess, chess
from multiprocessing import Pool

W = os.path.dirname(os.path.abspath(__file__))
SF = os.environ.get("SF_PATH", "stockfish")
DEPTH = int(os.environ.get("SF_DEPTH", 24))
MAXPLY = 15          # 8 ходов решающей стороны
MAXPLY_MATE = 21     # 11 ходов, если форсированный мат
VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3.2, chess.ROOK: 5, chess.QUEEN: 9}

def balance(b, me):
    """Материал глазами решающей стороны."""
    s = 0
    for pt, v in VAL.items():
        s += v * (len(b.pieces(pt, me)) - len(b.pieces(pt, not me)))
    return s

class Eng:
    def __init__(self):
        self.p = subprocess.Popen([SF], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, bufsize=1)
        self.send("uci"); self.wait("uciok")
        self.send("setoption name Threads value 1")
        self.send("setoption name Hash value 128")
        self.send("isready"); self.wait("readyok")
    def send(self, c): self.p.stdin.write(c + "\n"); self.p.stdin.flush()
    def wait(self, tok):
        for line in self.p.stdout:
            if line.startswith(tok): return line
    def analyse(self, fen):
        self.send("ucinewgame"); self.send(f"position fen {fen}"); self.send(f"go depth {DEPTH}")
        pv, score = [], None
        for line in self.p.stdout:
            if line.startswith("info ") and " pv " in line:
                t = line.split()
                if "multipv" in t and t[t.index("multipv") + 1] != "1": continue
                if "score" in t:
                    k = t.index("score"); score = (t[k + 1], int(t[k + 2]))
                pv = t[t.index("pv") + 1:]
            elif line.startswith("bestmove"):
                return pv, score

def trim(fen, pv, score=None):
    """Обрезка варианта.

    Комбинация идёт ровно до тех пор, пока у соперника НЕТ свободного
    выбора: он либо уходит от шаха, либо отыгрывает взятое. Как только
    он может сыграть что угодно — комбинация кончилась, дальше обычная
    игра, и держать её в решении незачем.

    Ход самой решающей стороны при этом может быть тихим — в том и тема
    урока, поэтому по её ходам вариант не обрываем.
    """
    forced_mate = bool(score and score[0] == "mate")
    b = chess.Board(fen); me = b.turn
    rows, mate_at, run_end, loud = [], None, 0, []
    for i, u in enumerate(pv[:MAXPLY_MATE]):
        try: mv = chess.Move.from_uci(u)
        except Exception: break
        if mv not in b.legal_moves: break
        was_check = b.is_check()
        is_cap = b.is_capture(mv)
        san = b.san(mv); b.push(mv)
        rows.append([u, san, b.fen()])
        loud.append(is_cap or b.is_check())     # ход «громкий»: взятие или шах
        ply = i + 1
        if b.is_checkmate(): mate_at = ply; break
        if forced_mate:                       # мат ведём до мата, он форсирован
            run_end = ply; continue
        if ply % 2 == 0:                      # ход соперника
            if is_cap or was_check: run_end = ply
            else: break                       # свободный выбор — комбинация всё
        else:
            run_end = max(run_end, ply)   # ход решающей стороны вариант не рвёт
    if not rows: return []
    if mate_at: return rows[:mate_at]

    cut = min(run_end or 1, MAXPLY_MATE if forced_mate else MAXPLY)
    if cut % 2 == 0: cut -= 1                 # кончаем ходом решающей стороны
    cut = max(cut, 1)
    # хвостовой ТИХИЙ ход решающей стороны отбрасываем вместе с предыдущим
    # полуходом: комбинация уже кончилась, и он в решении лишний. Первый
    # ход не трогаем никогда — он и бывает тем самым тихим ходом.
    while cut >= 3 and not loud[cut - 1]:
        cut -= 2
    return rows[:cut]

def work(q):
    eng = work.eng
    pv, score = eng.analyse(q["f"])
    m = trim(q["f"], pv, score)
    ev = ""
    if score:
        if score[0] == "mate": ev = "#"
        elif score[1] >= 300: ev = "+−"
        elif score[1] <= -300: ev = "−+"
    out = dict(q); out["m"] = [[u, s, f, 0, ev if i == len(m) - 1 else ""]
                              for i, (u, s, f) in enumerate(m)]
    out["cp"] = score[1] if score and score[0] == "cp" else None
    out["mate_in"] = score[1] if score and score[0] == "mate" else None
    return out

def init(): work.eng = Eng()

if __name__ == "__main__":
    import time
    OUT = os.path.join(W, "solved.json")
    src = json.load(open(os.path.join(W, "..", "out", "step12_positions.json")))
    todo = [q for q in src if not q["dup"]]
    if len(sys.argv) > 1: todo = todo[:int(sys.argv[1])]

    # продолжаем с места обрыва: уже посчитанное не пересчитываем
    res = []
    if os.path.exists(OUT):
        try: res = json.load(open(OUT))
        except Exception: res = []
    have = {r["n"] for r in res}
    todo = [q for q in todo if q["n"] not in have]
    if have: print(f"уже посчитано: {len(have)}, осталось: {len(todo)}", flush=True)

    t0 = time.time()
    n = min(os.cpu_count() or 4, 10)
    with Pool(n, initializer=init) as pool:
        for i, r in enumerate(pool.imap_unordered(work, todo, chunksize=1)):
            res.append(r)
            if (i + 1) % 25 == 0:
                done = i + 1; el = time.time() - t0
                eta = el / done * (len(todo) - done)
                json.dump(sorted(res, key=lambda x: x["n"]), open(OUT, "w"), ensure_ascii=False)
                print(f"  {done}/{len(todo)}  прошло {el/60:.1f} мин, осталось ~{eta/60:.0f} мин", flush=True)
    res.sort(key=lambda r: r["n"])
    json.dump(res, open(OUT, "w"), ensure_ascii=False)
    import collections
    h = collections.Counter(len(r["m"]) for r in res)
    print("решено:", len(res), "| пустых:", sum(1 for r in res if not r["m"]))
    print("длина варианта (полуходы):", dict(sorted(h.items())))
    print("матов:", sum(1 for r in res if r["mate_in"]))
