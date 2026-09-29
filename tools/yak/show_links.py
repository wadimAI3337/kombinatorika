"""Отладка привязки: абзацы главы, связанные ходы в ⟦ ⟧, диаграммы — [D корень].
   python3 show_links.py ГЛАВА [с_абзаца] [сколько]"""
import sys, json, re
ch, a, n = int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[3]) if len(sys.argv) > 3 else 40
src = open("../../yak.js").read(); data = json.loads(src[src.index("=") + 1:].rstrip().rstrip(";"))
c = next(x for x in data[0]["chapters"] if x["n"] == ch)
for i, b in enumerate(c["intro"][a:a + n], a):
    if b["t"] == "d": print(i, f"[D {b.get('n')}]"); continue
    if b["t"] in ("s", "h", "g"): print(i, "##", b.get("n", ""), b.get("x")); continue
    print(i, "".join(s if isinstance(s, str) else f"⟦{s['s']}⟧" for s in b.get("s") or []))
