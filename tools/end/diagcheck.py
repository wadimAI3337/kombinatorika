"""Проверка диаграмм end.js (копия yak/08_diagcheck.py): после диаграммы есть номерные ходы,
   ближайших абзацах есть номерные ходы, а ни один ход на неё не лёг.
   Так выдаёт себя неверно прочитанная доска. Запуск: python3 08_diagcheck.py"""
import json, re
src = open("../../end.js").read(); data = json.loads(src[src.index("=") + 1:].rstrip().rstrip(";"))
NUM = re.compile(r"\b\d{1,3}\.(?:\.\.)?[KQRBNa-h0]")
bad = []
for ch in data[0]["chapters"]:
    kids = {}
    for i, n in enumerate(ch["nodes"]): kids.setdefault(n[0], []).append(i)
    bl = ch["intro"]; sec = ""
    for i, b in enumerate(bl):
        if b["t"] == "s": sec = b.get("n", "")
        if b["t"] != "d" or b.get("n") is None or b["n"] >= 0 or kids.get(b["n"]): continue
        txt = ""
        for x in bl[i + 1:i + 5]:
            if x["t"] in ("d", "s"): break
            txt += " ".join(s if isinstance(s, str) else s["s"] for s in (x.get("s") or [])) + " "
        if NUM.search(txt):
            bad.append((ch["n"], sec, b["n"], ch["roots"][-b["n"] - 1], txt[:150]))
print("подозрительных диаграмм:", len(bad))
for x in bad: print(x)
