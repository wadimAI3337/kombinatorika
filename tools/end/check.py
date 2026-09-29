"""Проверка end.js: каждый кликабельный ход совпадает с ходом на доске (копия yak/07_check.py).
   ходом на доске — та же фигура, то же поле «куда» (и «откуда», если оно
   напечатано и не опечатка). Запуск: python3 07_check.py"""
import json, re, chess
from collections import Counter
src = open("../../end.js").read(); data = json.loads(src[src.index("=") + 1:].rstrip().rstrip(";"))
PC = {"K": chess.KING, "Q": chess.QUEEN, "R": chess.ROOK, "B": chess.BISHOP, "N": chess.KNIGHT}
bad, tot, fromfix = [], 0, 0
for ch in data[0]["chapters"]:
    roots, nodes = ch["roots"], ch["nodes"]
    fen = {}
    def f(i):
        if i < 0: return roots[-i - 1]
        if i not in fen:
            b = chess.Board(f(nodes[i][0])); b.push_uci(nodes[i][1]); fen[i] = b.fen()
        return fen[i]
    for bl in ch["intro"]:
        for s in bl.get("s") or []:
            if not isinstance(s, dict) or s.get("w"): continue
            tot += 1
            n = nodes[s["m"]]; b = chess.Board(f(n[0])); mv = chess.Move.from_uci(n[1])
            t = re.sub(r"^\d+\s*(\.\.\.|…|\.)\s*", "", s["s"]).rstrip("+#!?")
            ok = True
            if t in ("0-0", "O-O", "0-0-0", "O-O-O"):
                ok = b.is_castling(mv) and (len(t) > 3) == (chess.square_file(mv.to_square) == 2)
            else:
                m = re.fullmatch(r"([KQRBN])?([a-h][1-8])?[-:x]?([a-h][1-8])=?([QRBN])?", t)
                if m:
                    pc, fr, to, _ = m.groups()
                    ok = chess.square_name(mv.to_square) == to and b.piece_type_at(mv.from_square) == (PC[pc] if pc else chess.PAWN)
                    if ok and fr and len(fr) == 2 and chess.square_name(mv.from_square) != fr: fromfix += 1
                else:
                    m = re.fullmatch(r"([KQRBN])([a-h1-8])?[:x]?([a-h][1-8])", t) or re.fullmatch(r"([a-h])[:x]?([a-h])([1-8])?[QRBN]?", t)
                    ok = bool(m)
            if not ok: bad.append((ch["n"], s["s"], n[2]))
print("проверено", tot, "не совпало", len(bad), "опечаток «откуда» исправлено", fromfix)
for x in bad[:50]: print(x)
