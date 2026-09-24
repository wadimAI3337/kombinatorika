"""«Современный шахматный решебник · 3 хода в уме» (Я. Призант) → MIND в app.js.

Книга — PDF с текстовым слоем, 74 страницы: 500 диаграмм по 9 на странице,
под каждой ходы 1–3 обеих сторон, ответы (4-й ход и дальше) в конце.
Доски нарисованы ВЕКТОРОМ: клетки — залитые прямоугольники, фигуры —
контуры. Поэтому компьютерное зрение не нужно: у каждой фигуры свой
«отпечаток» (набор контуров с числом узлов и размером), одинаковый
на всех досках. Отпечатков 14: 12 фигур и два варианта пешки.

Какой отпечаток какая фигура — не угадываем, а подбираем: короли видны
по счёту (ровно по одному на доске), для остальных четырёх пар перебираем
24 раскладки и берём ту, где законны ходы 1–3 на всех досках: 500 из
500. №199 начинается взятием на проходе (1.gxf6) — поле f6 в FEN
дописано руками (EP), по диаграмме его не узнать. Все 500 ответов тоже
законны.

Так же устроены «4 хода в уме» (300) и «5 ходов в уме» (400), скрипт
общий. Отличия, которые он учитывает сам: страницы диаграмм и ответов
находит по рамкам досок; если задачу открывают чёрные («1...f5»),
диаграмма нарисована чёрными снизу — ориентация выбирается по
законности ходов; подпись под диаграммой бывает в три строки;
рокировка бывает разорвана переносом («O- O»). Взятия на проходе
первым ходом — в EPS по книгам.

Запуск:  pip install pymupdf python-chess
         python extract.py 3-khoda-v-ume.pdf mind.json     # → MIND
         python extract.py 4-khoda-v-ume.pdf mind4.json    # → MIND4
         python extract.py 5-khodov-v-ume.pdf mind5.json   # → MIND5
"""
import sys, re, json, itertools
from collections import Counter, defaultdict
import pymupdf, chess

PDF, OUT = sys.argv[1], sys.argv[2]
SQC = {(0.82, 0.55, 0.28), (1.0, 0.81, 0.62)}   # тёмная и светлая клетка
FIG = dict(zip("♔♕♖♗♘♚♛♜♝♞", "KQRBNKQRBN"))
# взятие на проходе первым ходом: по диаграмме не видно, что последним
# ходом соперник двинул пешку на два поля, поэтому поле вписано руками
EPS = {"3-khoda-v-ume": {199: "f6"}, "4-khoda-v-ume": {149: "f6"}, "5-khodov-v-ume": {165: "f6"}}
EP = next((v for k, v in EPS.items() if k in PDF), {})

rgb = lambda x: tuple(round(v, 2) for v in x["fill"]) if x.get("fill") else None
doc = pymupdf.open(PDF)
# страницы с диаграммами — где есть рамки досок, ответы — всё после них
def has_board(p):
    return any(x["type"] == "f" and x.get("fill") and round(x["fill"][0], 2) == 0.13
               and x["rect"].width > 100 for x in p.get_drawings())
DIAG_PAGES = [i for i in range(doc.page_count) if has_board(doc[i])]
ANS_PAGES = range(DIAG_PAGES[-1] + 1, doc.page_count)


def boards():
    out = []
    for pi in DIAG_PAGES:
        page = doc[pi]
        dr = page.get_drawings()
        words = page.get_text("words")
        frames = [x["rect"] for x in dr if x["type"] == "f" and rgb(x) == (0.13, 0.13, 0.13)
                  and x["rect"].width > 100]
        sqs = [x for x in dr if x["type"] == "f" and rgb(x) in SQC]
        for fr in frames:
            mine = [s for s in sqs if fr.contains(s["rect"])]
            assert len(mine) == 64, (pi + 1, len(mine))
            x0 = min(s["rect"].x0 for s in mine); y0 = min(s["rect"].y0 for s in mine)
            cw = (max(s["rect"].x1 for s in mine) - x0) / 8
            ch = (max(s["rect"].y1 for s in mine) - y0) / 8
            cells = defaultdict(list)
            for x in dr:
                r = x["rect"]
                if x in mine or not fr.contains(r) or r.width > cw * 1.2: continue
                cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
                # подписи a–h и 1–8 лежат на рамке, чуть за краем клеток:
                # int() округлил бы −0.3 в 0 и приклеил их к крайней клетке
                if not (x0 < cx < x0 + 8 * cw and y0 < cy < y0 + 8 * ch): continue
                c, rr = int((cx - x0) / cw), int((cy - y0) / ch)
                cells[(c, rr)].append((x["type"], rgb(x), len(x["items"]),
                                       round(r.width / cw, 2), round(r.height / ch, 2)))
            num = [w[4] for w in words if w[4].isdigit()
                   and fr.x0 < (w[0] + w[2]) / 2 < fr.x1 and fr.y0 - 20 < w[3] <= fr.y0 + 1]
            mv = sorted((w for w in words if fr.x0 - 15 < (w[0] + w[2]) / 2 < fr.x1 + 15
                         and fr.y1 < w[1] < fr.y1 + 62), key=lambda w: (round(w[1]), w[0]))
            out.append({"n": int(num[0]), "cells": {k: json.dumps(sorted(v)) for k, v in cells.items()},
                        "moves": " ".join(w[4] for w in mv)})
    return sorted(out, key=lambda b: b["n"])


def sans(s):
    s = re.sub(r"O-\s+O", "O-O", s)            # рокировка, разорванная переносом строки
    out = []
    for t in s.split():
        if re.fullmatch(r"\d+\.*", t): continue
        t = re.sub(r"^\d+\.+", "", t)
        for a, b in FIG.items(): t = t.replace(a, b)
        out.append(t.replace("0-0", "O-O"))
    return out


def fen_of(b, lab, flip=None):
    # если начинают чёрные, диаграмма нарисована чёрными снизу
    if flip is None: flip = b.get("flip", False)
    rows = []
    for r in range(8):
        row, e = "", 0
        for c in range(8):
            fp = b["cells"].get((7 - c, 7 - r) if flip else (c, r))
            if fp:
                row += (str(e) if e else "") + lab[fp]; e = 0
            else: e += 1
        rows.append(row + (str(e) if e else ""))
    side = "b" if re.match(r"\s*1\.\.\.", b["moves"]) else "w"
    bd = chess.Board("/".join(rows) + " " + side + " - - 0 1")
    cr = ""
    P = chess.Piece.from_symbol
    if bd.piece_at(chess.E1) == P("K"):
        cr += "K" if bd.piece_at(chess.H1) == P("R") else ""
        cr += "Q" if bd.piece_at(chess.A1) == P("R") else ""
    if bd.piece_at(chess.E8) == P("k"):
        cr += "k" if bd.piece_at(chess.H8) == P("r") else ""
        cr += "q" if bd.piece_at(chess.A8) == P("r") else ""
    return "/".join(rows) + " " + side + " " + (cr or "-") + " " + EP.get(b["n"], "-") + " 0 1"


def legal(fen, moves):
    bd = chess.Board(fen)
    try:
        for m in moves: bd.push_san(m)
        return True
    except ValueError:
        return False


B = boards()
NB = len(B)
assert [b["n"] for b in B] == list(range(1, NB + 1))

# отпечатки → фигуры: цвет по заливке, короли по счёту, остальное перебором
fps = Counter(fp for b in B for fp in b["cells"].values())
white = lambda fp: any(x[0] == "f" and x[1] == [1.0, 1.0, 1.0] and x[3] > 0.3 for x in json.loads(fp))
kings = [fp for fp, n in fps.items() if n == len(B)]
pawns = sorted(fps, key=fps.get, reverse=True)[:2]
pawns += [fp for fp in fps if fp not in pawns + kings and json.loads(fp)[0][2] == 12
          and abs(json.loads(fp)[0][4] - 0.68) < 0.01]
rest = [fp for fp in fps if fp not in kings + pawns]
# белую и чёрную версию одной фигуры сводим по частоте: ладей на досках
# больше всего, дальше по убыванию; ошибку в паре покажет перебор ниже
byn = lambda side: sorted((fp for fp in rest if white(fp) == side), key=fps.get, reverse=True)
pairs = list(zip(byn(True), byn(False)))
base = {fp: ("K" if white(fp) else "k") for fp in kings}
base.update({fp: ("P" if white(fp) else "p") for fp in pawns})
best = (-1, None)
for perm in itertools.permutations("RQBN"):
    lab = dict(base)
    for (w, b), t in zip(pairs, perm): lab[w], lab[b] = t, t.lower()
    n = sum(legal(fen_of(b, lab, False), sans(b["moves"])) or legal(fen_of(b, lab, True), sans(b["moves"])) for b in B)
    if n > best[0]: best = (n, lab)
lab = best[1]
for b in B:     # ориентация: та, где ходы до решения законны
    b["flip"] = not legal(fen_of(b, lab, False), sans(b["moves"])) and legal(fen_of(b, lab, True), sans(b["moves"]))
print("перевёрнутых диаграмм:", sum(b["flip"] for b in B), "— все с ходом чёрных:",
      all(re.match(r"\s*1\.\.\.", b["moves"]) for b in B if b["flip"]))
print("ходы до решения законны:", best[0], "из", len(B))
print("не сошлись:", [b["n"] for b in B if not legal(fen_of(b, lab, False), sans(b["moves"])) and not legal(fen_of(b, lab, True), sans(b["moves"]))])
assert best[0] >= len(B) - len(EP)

txt = "\n".join(doc[i].get_text() for i in ANS_PAGES)
# запись ответа: «N.» отдельной строкой (или «N. 4.…» в строку), дальше ходы
ans = {int(m.group(1)): " ".join(m.group(2).split()) for m in re.finditer(
    r"(?m)^\s*(\d+)\.[ \t]*\n?\s*(\d+\..*?)(?=^\s*\d+\.[ \t]*(?:\n|\d+\.)|\Z)", txt, re.S)}
assert sorted(ans) == list(range(1, NB + 1)), sorted(set(range(1, NB + 1)) - set(ans))

out = []
for b in B:
    bd = chess.Board(fen_of(b, lab))
    f0 = bd.fen()

    def run(lst):
        r = []
        for s in lst:
            mv = bd.parse_san(s); san = bd.san(mv); bd.push(mv)
            r.append([mv.uci(), san, bd.fen()])
        return r

    pre = run(sans(b["moves"]))
    # s — сторона, которая решает: ходит после разыгранных в уме ходов
    out.append({"n": b["n"], "f": f0, "s": "w" if bd.turn else "b", "pre": pre, "m": run(sans(ans[b["n"]]))})
json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
print("записано", len(out), "задач →", OUT)
