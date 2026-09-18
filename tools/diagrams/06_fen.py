"""Шаг 6. Расстановка -> FEN.

Перевёрнутую доску разворачиваем: массив клеток идёт слева направо и
сверху вниз, поворот на 180° — это просто чтение массива задом наперёд.

Очередь хода берём из ориентации (шаг 3): доска развёрнута к тому, кто
решает. Это не догадка, а проверяемое утверждение, и оно проверяется:
сторона, которая НЕ ходит, не может стоять под шахом. Если бы правило
было неверным, на 227 перевёрнутых досках это вылезло бы сразу.

Рокировки эвристикой, как в остальных сборниках сайта: разрешаем, если
король и ладья стоят на начальных полях. Взятия на проходе не ставим.
"""
import os, json, numpy as np, chess

W = os.path.dirname(os.path.abspath(__file__))
P = np.load(os.path.join(W, "pieces.npy")).reshape(640, 64)
names = [int(x) for x in np.load(os.path.join(W, "names.npy"))]
flipped = json.load(open(os.path.join(W, "flipped.json")))

def placement(row):
    out = []
    for r in range(8):
        s, e = "", 0
        for f in range(8):
            c = row[r * 8 + f]
            if c == "X": e += 1
            else:
                if e: s += str(e); e = 0
                s += c
        if e: s += str(e)
        out.append(s)
    return "/".join(out)

def castling(row):
    at = lambda f, rk: row[(8 - rk) * 8 + f]
    c = ""
    if at(4, 1) == "K":
        if at(7, 1) == "R": c += "K"
        if at(0, 1) == "R": c += "Q"
    if at(4, 8) == "k":
        if at(7, 8) == "r": c += "k"
        if at(0, 8) == "r": c += "q"
    return c or "-"

recs, bad = [], []
for i, n in enumerate(names):
    row = list(P[i])
    if flipped[str(n)]: row = row[::-1]          # поворот на 180°
    pl, cas = placement(row), castling(row)
    side = "b" if flipped[str(n)] else "w"
    fen = f"{pl} {side} {cas} - 0 1"
    b = chess.Board(fen)
    ok = b.is_valid()
    if not ok:
        other = chess.Board(f"{pl} {'w' if side=='b' else 'b'} {cas} - 0 1")
        bad.append((n, side, "но легально с другой стороной" if other.is_valid()
                    else "нелегально при любой стороне"))
    recs.append({"n": n, "pl": pl, "cas": cas, "s": side, "fen": fen,
                 "flipped": flipped[str(n)], "valid": ok,
                 "check": b.is_check(), "mate": b.is_checkmate()})

json.dump(recs, open(os.path.join(W, "positions.json"), "w"))
print("досок:", len(recs), "| ход белых:", sum(1 for r in recs if r["s"] == "w"),
      "| ход чёрных:", sum(1 for r in recs if r["s"] == "b"))
print("позиция легальна с этой очередью хода:", sum(1 for r in recs if r["valid"]), "из", len(recs))
print("сторона на ходу уже под шахом:", sum(1 for r in recs if r["check"]),
      "| из них мат:", sum(1 for r in recs if r["mate"]))
if bad:
    print("РАСХОЖДЕНИЯ:", len(bad))
    for n, s, why in bad[:20]: print(f"  №{n}: поставили ход {s}, {why}")
else:
    print("расхождений нет: правило «перевёрнута -> ход чёрных» подтвердилось на всех досках")
