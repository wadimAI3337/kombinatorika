"""Отладка привязки: python3 show.py ГЛАВА [с_блока] [сколько] — ходы в ⟦ ⟧, диаграммы [D корень fen]"""
import sys, json
ch, a, n = int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[3]) if len(sys.argv) > 3 else 40
src = open("../../end.js").read(); data = json.loads(src[src.index("=") + 1:].rstrip().rstrip(";"))
c = next(x for x in data[0]["chapters"] if x["n"] == ch)
for i, b in enumerate(c["intro"][a:a + n], a):
    fl = ("h" if b.get("h") else "") + ("q" if b.get("q") else "") + ("r" if b.get("r") else "")
    if b["t"] == "d":
        r = b.get("n"); print(i, fl, f"[D {r}]", c["roots"][-r - 1] if r is not None and r < 0 else ""); continue
    if b["t"] in ("s", "u", "h", "g"): print(i, fl, "##", b["t"], b.get("key", ""), b.get("x")); continue
    print(i, fl, "".join(s if isinstance(s, str) else ("⟦" + s["s"] + "⟧" if s.get("b") is False else "⟦*" + s["s"] + "⟧") for s in b.get("s") or []))
