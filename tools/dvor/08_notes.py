"""Разборы остальных сборников (Конотоп, «Позиционная игра») -> кликабельные ходы.
   Тот же разборщик, что для книг (06_parse.py), но на входе поле x задачи
   из app.js и FEN задачи. На выходе notes.js: для каждой задачи отрезки
   текста, которые являются ходами, и дерево ходов:
   NOTES[книга][номер] = [[[начало, конец, узел], …], [[родитель, uci, san], …]]"""
import json, sys, importlib.util
sys.argv.append("--no-main")
spec = importlib.util.spec_from_file_location("p", "06_parse.py"); P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
src = open("../../app.js", encoding="utf-8").read().split("\n")
BOOKS = {"KON": "kon2", "KON1": "kon1", "POS1": "pos1", "POS2": "pos2", "POS3": "pos3",
         "POS4": "pos4", "POS5": "pos5", "POS6": "pos6"}
out, tot, bad = {}, 0, 0
for const, bid in BOOKS.items():
    line = next(l for l in src if l.startswith("const " + const + " = "))
    arr = json.loads(line[line.index(" = ") + 3:].rstrip(";"))
    book = out.setdefault(bid, {})
    for p in arr:
        if not p.get("x"): continue
        t = P.Tree(); L = P.Linker(t); L.set_root(p["f"])
        segs = P.link_paragraph(p["x"], L)
        spans, pos = [], 0
        for s in segs:
            if isinstance(s, str): pos += len(s); continue
            spans.append([pos, pos + len(s["s"]), s["m"]]); pos += len(s["s"])
        assert pos == len(p["x"]), (bid, p["n"])
        book[p["n"]] = [spans, [[n["parent"], n["uci"], n["san"]] for n in t.nodes]]
        tot += len(spans); bad += len(L.bad)
js = "/* Кликабельные ходы в разборах Конотопа и «Позиционной игры». Генерируется tools/dvor/08_notes.py */\n"
js += "window.NOTES = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
open("../../notes.js", "w", encoding="utf-8").write(js)
print("ходов", tot, "не связано", bad)
