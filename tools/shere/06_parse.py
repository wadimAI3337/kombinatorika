"""Расшифровка страниц (work/txt) + FEN досок (work/fens.json) -> shere.js.

Привязка ходов — та же, что у Дворецкого (tools/end/extract.py: render_chapter,
best_root, «при ходе белых», «вернёмся к диаграмме»), а та — общая из
yak/06_parse.py и dvor/06_parse.py. Здесь только разметка этой книги:
  [[CHAPTER N]] Название      начало главы
  [[GAME]] Игроки | Турнир     шапка партии — единица «прочитано»
  [[H]] Заголовок              заголовок без партии
  [[DIAG]]                     доска (число на странице = число найденных досок);
                               [[DIAG ? b]] — упражнение (ответ скрыт), ход чёрных;
                               [[DIAG w 45]] — номер хода, когда по тексту его не угадать
  [[CONT]]                     страница начинается с продолжения абзаца
  [[RESUME]]                   «Возвращаемся к партии»: ходы снова от позиции партии
                               (до первой диаграммы-отступления в разделе)
  **…**                        жирные ходы (главная линия)
Запуск: python3 06_parse.py [главы, по умолчанию 1]"""
import json, re, os, sys, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, "work")
spec = importlib.util.spec_from_file_location("E", os.path.join(HERE, "../end/extract.py"))
E = importlib.util.module_from_spec(spec); sys.modules["E"] = E
cwd = os.getcwd(); os.chdir(os.path.join(HERE, "../end")); sys.path.insert(0, os.path.join(HERE, "../end"))
spec.loader.exec_module(E); os.chdir(cwd)
FIX = json.load(open(os.path.join(HERE, "fix_fens.json"))) if os.path.exists(os.path.join(HERE, "fix_fens.json")) else {}
TAG = re.compile(r"\[\[(CHAPTER|GAME|H|DIAG|CONT|RESUME)\s*([^\]]*)\]\]\s*(.*)$")
MIN, MAX = 480, 580

def load():
    boards = json.load(open(f"{W}/boards.json"))
    fens = {(r["p"], r["k"]): r["fen"] for r in json.load(open(f"{W}/fens.json"))}
    pages = sorted(int(f[1:4]) for f in os.listdir(os.path.join(HERE, "txt")) if re.fullmatch(r"p\d{3}\.txt", f))
    items, warn = [], []
    for p in pages:
        txt = open(os.path.join(HERE, f"txt/p{p:03d}.txt"), encoding="utf-8").read()
        txt = txt.translate(str.maketrans("♔♕♖♗♘♚♛♜♝♞", "KQRBNKQRBN"))
        txt = re.sub(r"\+[-–]", "+−", txt); txt = re.sub(r"[-–]\+", "−+", txt)
        real = [k for k, b in enumerate(boards.get(str(p), [])) if MIN <= b[2] <= MAX]
        k = 0; first = True
        for para in re.split(r"\n\s*\n", txt.strip()):
            buf = []
            def flush():
                if buf: items.append(("p", " ".join(buf), p, None)); buf.clear()
            for l in [x.strip() for x in para.split("\n") if x.strip()]:
                m = TAG.match(l)
                if not m:
                    buf.append(l); first = False; continue
                flush()
                tag, arg, rest = m.groups()
                if tag == "RESUME":
                    items.append(("resume", None, p, None)); first = False; continue
                if tag == "CONT":
                    if first: items.append(("cont", None, p, None))
                elif tag == "DIAG":
                    src = f"{p}/{real[k]}" if k < len(real) else None
                    fen = FIX.get(src) or (fens.get((p, real[k])) if k < len(real) else None)
                    a = arg.split() + rest.split()
                    items.append(("diag", {"n": None, "turn": next((x for x in a if x in ("w", "b")), None), "q": "?" in a,
                                           "num": next((int(x) for x in a if x.isdigit()), None),
                                           "fen": fen, "src": src}, p, None)); k += 1
                elif tag == "CHAPTER":
                    items.append(("chapno", arg.strip(), p, None)); items.append(("chaptitle", rest.strip(), p, None))
                elif tag == "GAME":
                    items.append(("sec", (arg + " " + rest).strip().replace(" | ", ", "), p, None))
                else:
                    items.append(("sub", (arg + " " + rest).strip(), p, None))
                first = False
            flush()
        if k != len(real): warn.append(f"стр. {p}: [[DIAG]] {k}, досок {len(real)}")
    out = []
    for it in items:            # склейка абзаца через страницу
        if it[0] == "p" and out and out[-1][0] == "cont":
            out.pop()
            j = len(out) - 1
            while j >= 0 and out[j][0] not in ("p", "sec", "sub", "chaptitle"): j -= 1
            if j >= 0 and out[j][0] == "p":
                prev = out[j][1]
                out[j] = ("p", prev[:-1] + it[1] if re.search(r"[а-яё]-$", prev) else prev + " " + it[1], out[j][2], None)
                continue
        out.append(it)
    out = [x for x in out if x[0] != "cont"]
    # «Вернемся к партии Рибли – Карпов»: шапка с тем же именем партии и пометкой
    # «(продолжение)» — повторяем первую доску той партии, чтобы ходы легли на неё
    first, res, last, need = {}, [], None, None
    for it in out:
        res.append(it)
        if it[0] == "sec":
            key = re.sub(r"\s*\(продолжение\)", "", it[1]); last = key
            if "(продолжение)" in it[1] and key in first:
                res.append(first[key]); need = None
            else: need = key
        elif it[0] == "diag" and last and need == last:
            first[last] = it; need = None
    return res, warn

def main():
    want = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "--no-main" else "0,1,2,3,4,5,6,7,8,9").split(",")]
    items, warn = load()
    chs = [c for c in E.split_chapters(items) if c["n"] in want]
    res, allbad, tot = [], [], 0
    for ch in chs:
        blocks, t, bad = E.render_chapter(ch, {})
        allbad += [f"гл.{ch['n']}: {x}" for x in bad]
        linked = sum(1 for b in blocks for s in (b.get("s") or []) if isinstance(s, dict))
        tot += linked
        diags = [b for b in blocks if b["t"] == "d"]
        secs = [b for b in blocks if b["t"] == "s"]
        res.append({"n": ch["n"], "title": "Введение" if ch["n"] == 0 else ch["title"], "intro": blocks, "roots": t.roots, "secs": len(secs), "diags": len(diags),
                    "nodes": [[x["parent"], x["uci"], x["san"], 1 if x["main"] else 0] + ([x["base"]] if x.get("threat") else []) for x in t.nodes]})
        print(f"глава {ch['n']}: {ch['title']} — партий {len(secs)}, диаграмм {len(diags)}, ходов связано {linked}, не связано {len(bad)}")
    book = {"id": "shere1", "title": "С молодежью – в эндшпиль. Книга первая", "author": "Михаил Шерешевский", "chapters": res}
    js = "/* «Эндшпиль»: М. Шерешевский «С молодежью – в эндшпиль», книга 1, разобрано из скана (tools/shere). Генерируется 06_parse.py */\n"
    js += "window.SHERE = " + json.dumps([book], ensure_ascii=False, separators=(",", ":")) + ";\n"
    open(os.path.join(HERE, "../../shere.js"), "w", encoding="utf-8").write(js)
    open(f"{W}/unlinked.txt", "w").write("\n".join(allbad))
    print("итого связано", tot, "не связано", len(allbad), f"({100 * len(allbad) / max(1, tot + len(allbad)):.1f}%)")
    for w in warn: print("!", w)

if __name__ == "__main__":
    main()
