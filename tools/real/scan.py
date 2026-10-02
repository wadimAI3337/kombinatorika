#!/usr/bin/env python3
"""
Реализация перевеса: ищет в партиях «точку перевеса» — момент, когда
у будущего победителя стало +2 и выше и перевес устойчив. С этой
позиции на сайте и начинается тренировка (метод Рамеша: досмотрел
партию до выигранной позиции → доиграл сам → сверился с чемпионом).

Логика поиска точки и теги — те же, что в real.js на сайте.
Если меняешь пороги здесь, поменяй и там (константы REAL_* в real.js).

Примеры:
  # вся база Карпова, только его победы, 6 процессов
  python3 tools/real/scan.py Karpov.pgn --hero Karpov -j 6 -o out/karpov.json

  # быстрее и грубее
  python3 tools/real/scan.py games.pgn --depth1 10 --depth2 16

Нужны python-chess (pip install chess) и stockfish в PATH.
"""
import argparse, io, json, hashlib, sys, os, time
from multiprocessing import Pool

import chess, chess.pgn, chess.engine

# ---- пороги: синхронно с real.js ----
THRESH   = 200   # от какой оценки (сантипешки, глазами победителя) позиция «выиграна»
CAP      = 700   # выше — уже разгром, тренировать нечего
STABLE   = 6     # столько полуходов подряд перевес не должен падать ниже 0.75*THRESH
MIN_LEFT = 20    # после точки в партии должно остаться не меньше 10 ходов
SWING    = 80    # если потом оценка падала ниже — «победитель чуть не упустил»
TACTIC   = 2     # лучший ход выигрывает столько материала за 3 полухода — это комбинация
MATE     = 10000

PVAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


def score_cp(sc: chess.engine.PovScore) -> int:
    """Оценка глазами белых в сантипешках, мат — ±(10000 − число ходов)."""
    w = sc.white()
    if w.is_mate():
        m = w.mate()
        return (MATE - abs(m)) if m > 0 else -(MATE - abs(m))
    return max(-MATE + 100, min(MATE - 100, w.score()))


def material(board: chess.Board, color: bool) -> int:
    return sum(PVAL[p.piece_type] for p in board.piece_map().values() if p.color == color)


def gid_of(start_fen: str, ucis) -> str:
    """Идентификатор партии: те же правила, что hashGame() в real.js."""
    s = (start_fen if start_fen != chess.STARTING_FEN else "") + "|" + " ".join(ucis)
    return hashlib.sha1(s.encode()).hexdigest()[:16]


# ---------- точка перевеса ----------

def find_point(ev, stm_white0: bool, hero_white: bool, pvgain=None, thresh=THRESH):
    """ev[i] — оценка глазами белых после i полуходов. Возвращает (k, verdict, flags).
    verdict: ok | none | jump | short | tactic.
    pvgain(i) -> выигрыш материала лучшим ходом за 3 полухода (или None, если неизвестно)."""
    n = len(ev)
    sgn = 1 if hero_white else -1
    pov = [None if e is None else e * sgn for e in ev]
    hero_to_move = lambda i: ((i % 2 == 0) == stm_white0) == hero_white
    first = None
    for i in range(n):
        if not hero_to_move(i) or pov[i] is None or pov[i] < thresh:
            continue
        win = [p for p in pov[i:i + STABLE + 1] if p is not None]
        if win and min(win) >= thresh * 0.75:
            first = i
            break
    if first is None:
        return None, "none", []
    if pov[first] >= CAP:
        return first, "jump", []
    k = None
    for i in range(first, min(n, first + 12)):
        if not hero_to_move(i) or pov[i] is None or pov[i] < thresh * 0.75 or pov[i] >= CAP:
            continue
        g = pvgain(i) if pvgain else None
        if g is not None and g >= TACTIC:
            continue
        k = i
        break
    if k is None:
        return first, "tactic", []
    if n - 1 - k < MIN_LEFT:
        return k, "short", []
    flags = []
    rest = [p for p in pov[k:] if p is not None]
    if rest and min(rest) < SWING:
        flags.append("swing")
    return k, "ok", flags


# ---------- теги позиции ----------

def tags_of(board: chess.Board, hero_white: bool):
    hero, opp = hero_white, not hero_white
    cnt = lambda c, t: len(board.pieces(t, c))
    d = {t: cnt(hero, t) - cnt(opp, t) for t in PVAL}
    minor = d[chess.KNIGHT] + d[chess.BISHOP]
    nonpawn = lambda c: sum(PVAL[t] * cnt(c, t) for t in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))
    queens = cnt(True, chess.QUEEN) + cnt(False, chess.QUEEN)
    out = []
    if queens == 0 and nonpawn(True) <= 13 and nonpawn(False) <= 13 or nonpawn(True) + nonpawn(False) <= 16:
        out.append("эндшпиль")
    else:
        out.append("миттельшпиль")
    dp = d[chess.PAWN]
    if d[chess.QUEEN] == 0 and d[chess.ROOK] == 0 and minor == 0:
        out.append("позиционный перевес" if dp == 0 else "лишняя пешка" if dp == 1 else
                   "лишние пешки" if dp > 1 else "перевес при меньшем материале")
    elif d[chess.ROOK] == 1 and minor == -1 and d[chess.QUEEN] == 0:
        out.append("лишнее качество")
    elif minor >= 1 and d[chess.ROOK] == 0 and d[chess.QUEEN] == 0:
        out.append("лишняя фигура")
    else:
        out.append("неравный материал")
    wb, bb = board.pieces(chess.BISHOP, True), board.pieces(chess.BISHOP, False)
    if len(wb) == 1 and len(bb) == 1:
        sq = lambda s: (chess.square_file(s) + chess.square_rank(s)) % 2
        if sq(next(iter(wb))) != sq(next(iter(bb))):
            out.append("разноцветные слоны")
    for s in board.pieces(chess.PAWN, hero):
        f, r = chess.square_file(s), chess.square_rank(s)
        ahead = range(r + 1, 8) if hero else range(0, r)
        blocked = any(board.piece_at(chess.square(ff, rr)) == chess.Piece(chess.PAWN, opp)
                      for ff in (f - 1, f, f + 1) if 0 <= ff < 8 for rr in ahead)
        if not blocked:
            out.append("проходная")
            break
    return out


# ---------- разбор одной партии ----------

_engine = None


def _eng():
    global _engine
    if _engine is None:
        _engine = chess.engine.SimpleEngine.popen_uci(os.environ.get("STOCKFISH", "stockfish"))
        _engine.configure({"Threads": 1, "Hash": 64})
    return _engine


def analyse_game(job):
    """job: dict(sans, start, headers, hero ('w'|'b'|None), depth1, depth2, thresh, coach)"""
    eng = _eng()
    board = chess.Board(job["start"])
    boards, ucis = [board.copy()], []
    for san in job["sans"]:
        mv = board.parse_san(san)
        ucis.append(mv.uci())
        board.push(mv)
        boards.append(board.copy())
    res = job["headers"].get("Result", "*")
    hero = job.get("hero")
    if hero is None:
        hero = "w" if res == "1-0" else "b" if res == "0-1" else None
    if hero is None:
        return None
    hero_white = hero == "w"

    # проход 1: быстро по всем позициям
    ev = []
    for b in boards:
        if b.is_game_over():
            o = b.outcome()
            ev.append(0 if o.winner is None else (MATE if o.winner else -MATE))
            continue
        info = eng.analyse(b, chess.engine.Limit(depth=job["depth1"]))
        ev.append(score_cp(info["score"]))

    # проход 2: глубже вокруг подозрительного места
    stm0 = boards[0].turn
    k0, _, _ = find_point(ev, stm0, hero_white, thresh=job["thresh"])
    deep, pvs = {}, {}
    lo = max(0, (k0 if k0 is not None else len(ev)) - 4)
    for i in range(lo, min(len(boards), lo + 4 + STABLE + 12)):
        b = boards[i]
        if b.is_game_over():
            continue
        info = eng.analyse(b, chess.engine.Limit(depth=job["depth2"]))
        ev[i] = deep[i] = score_cp(info["score"])
        pvs[i] = [m.uci() for m in info.get("pv", [])[:6]]
    coach = job.get("coach")
    if coach is not None and coach not in pvs and coach < len(boards) and not boards[coach].is_game_over():
        info = eng.analyse(boards[coach], chess.engine.Limit(depth=job["depth2"]))
        ev[coach] = score_cp(info["score"])
        pvs[coach] = [m.uci() for m in info.get("pv", [])[:6]]

    def pvgain(i):
        pv = pvs.get(i)
        if not pv:
            return None
        b = boards[i].copy()
        side = b.turn
        m0 = material(b, side) - material(b, not side)
        for u in pv[:3]:
            b.push(chess.Move.from_uci(u))
        return (material(b, side) - material(b, not side)) - m0

    k, verdict, flags = find_point(ev, stm0, hero_white, pvgain, thresh=job["thresh"])
    h = job["headers"]
    out = {
        "gid": gid_of(job["start"], ucis),
        "white": h.get("White", "?"), "black": h.get("Black", "?"),
        "event": h.get("Event", ""), "date": h.get("Date", ""), "result": res,
        "hero": hero, "sans": " ".join(job["sans"]), "ev": ev,
        "k": k, "verdict": verdict, "flags": flags,
    }
    if job["start"] != chess.STARTING_FEN:
        out["start"] = job["start"]
    kk = coach if coach is not None else k
    if kk is not None:
        out["tags"] = tags_of(boards[kk], hero_white)
        if kk in pvs:
            out["pv"] = pvs[kk]
    if coach is not None:
        out["coach"] = coach
    return out


# ---------- отбор без движка ----------

def tc_base(h):
    tc = h.get("TimeControl", "")
    if not tc or tc in ("-", "?"):
        return None                       # партия за доской — считаем классикой
    try:
        return int(tc.split("+")[0].split("/")[-1])
    except ValueError:
        return None


def prefilter(game, hero_name, min_moves, slow_only):
    h = game.headers
    res = h.get("Result", "*")
    if res not in ("1-0", "0-1"):
        return None, "ничья или без результата"
    winner = h.get("White" if res == "1-0" else "Black", "")
    if hero_name and hero_name.lower() not in winner.lower():
        return None, "выиграл не герой"
    base = tc_base(h)
    if slow_only and base is not None and base < 600:
        return None, "блиц/пуля"
    sans = []
    b = game.board()
    for mv in game.mainline_moves():
        sans.append(b.san(mv))
        b.push(mv)
    if len(sans) < min_moves * 2:
        return None, "короткая"
    return {"sans": sans, "start": game.board().fen(), "headers": dict(h),
            "hero": "w" if res == "1-0" else "b"}, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pgn", nargs="+")
    ap.add_argument("--hero", help="только победы игрока, чьё имя содержит эту строку")
    ap.add_argument("--min-moves", type=int, default=30)
    ap.add_argument("--all-tc", action="store_true", help="не выкидывать блиц")
    ap.add_argument("--thresh", type=int, default=THRESH)
    ap.add_argument("--depth1", type=int, default=12)
    ap.add_argument("--depth2", type=int, default=18)
    ap.add_argument("-j", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("-o", default="-")
    a = ap.parse_args()

    jobs, skipped = [], {}
    for path in a.pgn:
        with open(path, encoding="utf-8", errors="replace") as f:
            while True:
                g = chess.pgn.read_game(f)
                if g is None:
                    break
                j, why = prefilter(g, a.hero, a.min_moves, not a.all_tc)
                if j is None:
                    skipped[why] = skipped.get(why, 0) + 1
                    continue
                j.update(depth1=a.depth1, depth2=a.depth2, thresh=a.thresh)
                jobs.append(j)
    print(f"к анализу: {len(jobs)}; отсеяно без движка: {skipped}", file=sys.stderr)

    out, t0 = [], time.time()
    with Pool(a.j) as pool:
        for i, r in enumerate(pool.imap_unordered(analyse_game, jobs), 1):
            if r:
                out.append(r)
            if i % 10 == 0 or i == len(jobs):
                ok = sum(1 for x in out if x["verdict"] == "ok")
                print(f"\r{i}/{len(jobs)}  найдено позиций: {ok}  {time.time() - t0:.0f} с", end="", file=sys.stderr)
    print(file=sys.stderr)
    data = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    if a.o == "-":
        print(data)
    else:
        with open(a.o, "w", encoding="utf-8") as f:
            f.write(data)


if __name__ == "__main__":
    main()
