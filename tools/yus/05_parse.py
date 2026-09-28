"""Разметка страниц + FEN диаграмм -> книги Юсупова для сайта (yus.js).

Общая часть (привязка ходов к позициям, деревья вариантов) — из
dvor/06_parse.py: Tree, Linker, link_paragraph, root_fen. Здесь только
устройство этих книг: предисловие/введение, главы (введение с
диаграммами, 12 упражнений, решения с очками, оценка результата) и
финальный тест.

Запуск: python3 05_parse.py  (обе книги: yus и yus2)"""
import json, re, os, sys, importlib.util
import chess
sys.argv.append("--no-main")
spec = importlib.util.spec_from_file_location("P", os.path.join(os.path.dirname(__file__), "../dvor/06_parse.py"))
P = importlib.util.module_from_spec(spec)
cwd = os.getcwd(); os.chdir(os.path.join(os.path.dirname(__file__), "../dvor")); spec.loader.exec_module(P); os.chdir(cwd)

# в ответе на упражнение позиция диаграммы важнее любой другой той же глубины
_cand = P.Linker.candidates
def _candidates(self, ply):
    c = _cand(self, ply)
    pr = getattr(self, "prefer", None)
    if pr is not None and pr in c: c = [pr] + [x for x in c if x != pr]
    return c
P.Linker.candidates = _candidates

BOOKS = [
    {"dir": "../yus", "id": "yus1", "min": 900, "title": "Build Up Your Chess 2",
     "sub": "Beyond the Basics · оранжевая серия"},
    {"dir": "../yus2", "id": "yus2", "min": 500, "title": "Boost Your Chess 2",
     "sub": "Beyond the Basics · синяя серия"},
]

TITLES = {
 "yus1": ["Матовые комбинации", "Общие принципы эндшпиля", "Комбинации на последней горизонтали",
          "Общие принципы дебюта", "Двойной удар", "Хороший и плохой слон", "Ходы-кандидаты", "Центр",
          "Связка и вскрытое нападение", "Цугцванг", "Отвлечение", "Жертва слона на h7",
          "Оценка позиции", "Планирование", "Дебютный репертуар за белых после 1.e4 e5",
          "Разрушение рокировки", "Дебютный репертуар против 1.e4", "Размены",
          "Приоритеты при расчёте вариантов", "Пешечные окончания 1", "Завлечение",
          "Время в дебюте", "Улучшение позиции фигур", "Пешечные окончания 2"],
 "yus2": ["Атака на короля", "Открытая линия", "«Малая» тактика", "Дебютный репертуар за белых: французская защита",
          "Простые ладейные окончания", "Борьба с пешечным центром", "Ловля фигур", "Расчёт коротких вариантов",
          "Слабые пункты", "Перекрытие линий", "Дебютный репертуар за чёрных против 1.d4",
          "Простые ладейные окончания 2", "Блокирующие комбинации", "Двуслонье",
          "Типичные ошибки при расчёте вариантов", "Устранение защиты", "Хороший и плохой слон",
          "Закрытые дебюты", "Освобождение линии", "Техника эндшпиля", "Блокада",
          "Вытаскивание короля", "Дебют Рети и английское начало", "Типичные ошибки в эндшпиле"],
}
TAG = re.compile(r"\[\[(CHAPTER|CONTENTS|H|DIAG|REF|FROM|GAME|PTS|SCORE|CONT|PART|CAP)\s*([^\]]*)\]\]\s*(.*)$")

def load(bk):
    W = os.path.join(os.path.dirname(__file__), bk["dir"], "work")
    boards = json.load(open(f"{W}/boards.json"))
    fens = {(r["p"], r["k"]): r["fen"] for r in json.load(open(f"{W}/fens.json"))}
    fixf = os.path.join(os.path.dirname(__file__), bk["dir"], "fix_fens.json")
    fix = json.load(open(fixf)) if os.path.exists(fixf) else {}
    items, warn = [], []
    pages = sorted(int(f[1:4]) for f in os.listdir(f"{W}/txt") if re.fullmatch(r"p\d{3}\.txt", f))
    for p in pages:
        txt = open(f"{W}/txt/p{p:03d}.txt", encoding="utf-8").read().replace("†", "+")
        txt = re.sub(r"(^|[\s(.*])W(?=x?[a-h][1-8])", r"\1Q", txt, flags=re.M)   # немецкое W = ферзь
        txt = re.sub(r"[ \t]*\[\[(PTS|REF)\s+([^\]]*)\]\][ \t]*", r"\n[[\1 \2]]\n", txt)   # маркер посреди строки — на свою строку
        bl = boards.get(str(p), [])
        inside = lambda a, b: a is not b and b[0] <= a[0] and b[1] <= a[1] and a[0] + a[2] <= b[0] + b[2] + 8 and a[1] + a[3] <= b[1] + b[3] + 8
        ks = [k for k, b in enumerate(bl) if b[2] >= bk["min"] and not any(inside(b, o) for o in bl)]
        nd = 0
        # страница упражнений: доски идут по колонкам (1–3 слева, 4–6 справа), а агент мог
        # записать их по строкам — сопоставляем по номеру упражнения, а не по порядку в тексте
        labs = re.findall(r"\[\[DIAG\s+([^\]]*)\]\]", txt)
        exl = [re.search(r"(?:EX\s+)?(F-\d+|\d+-\d+)", a) for a in labs]
        bylab = {}
        if labs and all(x and ("EX" in a or x.group(1).startswith("F")) for a, x in zip(labs, exl)) and len(labs) == len(ks):
            key = lambda n: tuple(int(t) for t in re.findall(r"\d+", n))
            order = sorted((x.group(1) for x in exl), key=key)
            bylab = {n: ks[i] for i, n in enumerate(order)}
        for para in re.split(r"\n\s*\n", txt.strip()):
            buf = []
            def flush():
                if buf: items.append(("p", " ".join(buf), p)); buf.clear()
            for l in [x.strip() for x in para.split("\n") if x.strip()]:
                m = TAG.match(l)
                if not m: buf.append(l); continue
                flush()
                tag, arg, rest = m.groups()
                if tag == "CONT": items.append(("cont", None, p)); continue
                if tag == "DIAG":
                    lab = re.search(r"(EX\s+)?(F-\d+|\d+-\d+)", arg)
                    turn = re.search(r"turn=([wb])", arg); stars = re.search(r"stars=(\d)", arg)
                    bk_ = bylab.get(lab.group(2)) if (lab and bylab) else (ks[nd] if nd < len(ks) else -1)
                    fen = fix.get(f"{p}/{bk_}") or fens.get((p, bk_))
                    items.append(("diag", {"n": lab.group(2) if lab else None, "ex": bool(lab and (lab.group(1) or lab.group(2).startswith("F"))),
                                           "turn": turn.group(1) if turn else None, "stars": int(stars.group(1)) if stars else 0,
                                           "fen": fen, "small": False, "src": f"{p}/{bk_}"}, p))
                    nd += 1; continue
                items.append((tag.lower(), (arg + " " + rest).strip(), p))
            flush()
        # картинка диаграммы стоит в другой колонке после текста о ней — ставим её к ссылке [[REF]]
        pg = [i for i, it in enumerate(items) if it[2] == p]
        if pg:
            seg = items[pg[0]:]
            for d in [x for x in seg if x[0] == "diag" and x[1]["n"] and not x[1]["ex"]]:
                di = seg.index(d)
                ri = next((i for i, x in enumerate(seg) if x[0] == "ref" and re.sub(r"\D+$", "", x[1].replace("EX", "").strip()) == d[1]["n"]), None)
                if ri is not None and ri < di:
                    seg.pop(di)
                    j = ri + 1
                    while j < len(seg) and seg[j][0] == "game": j += 1
                    seg.insert(j, d)
            items[pg[0]:] = seg
        if nd != len(ks): warn.append(f"стр. {p}: диаграмм в тексте {nd}, досок {len(ks)}")
    # склейка продолжений через страницу
    out = []
    for it in items:
        if it[0] == "p" and out and out[-1][0] == "cont":
            out.pop()
            j = len(out) - 1
            while j >= 0 and out[j][0] != "p": j -= 1
            if j >= 0:
                out[j] = ("p", out[j][1] + " " + it[1], out[j][2]); continue
        if it[0] == "cont": out.append(it); continue
        out.append(it)
    return [x for x in out if x[0] != "cont"], warn

def build(items):
    """Поток -> предисловие + главы. Глава: intro (поток), ex (упражнения), sol (ответы)."""
    pre, chapters, ch, mode, cur_ex, pend_game = [], [], None, "pre", None, None
    final = None
    for kind, pl, page in items:
        if kind == "chapter":
            m = re.match(r"(\d+)\s*(.*)", pl)
            ch = {"n": int(m.group(1)) if m else len(chapters) + 1, "title": (m.group(2) if m else pl).strip(),
                  "contents": "", "intro": [], "ex": {}, "order": [], "score": ""}
            chapters.append(ch); mode = "intro"; continue
        if kind == "h" and mode == "sol" and re.fullmatch(r"(ex\.?\s*)?(f-\d+|\d+-\d+)", pl.strip().lower()):
            kind = "ref"
        if kind == "h":
            t = pl.strip().lower()
            if t.startswith("exercises"): mode = "ex"; continue
            if t.startswith("solutions"): mode = "sol"; continue
            if t.startswith("scoring"): continue
            if t.startswith("final test"):
                if final is None:
                    final = {"n": 25, "title": "Final test", "contents": "", "intro": [], "ex": {}, "order": [], "score": "", "final": True}
                    chapters.append(final)
                ch = final; mode = "ex"; continue
            if t.startswith("contents") and ch is None: mode = "skip"; continue
            if ch is None:
                pre.append({"title": pl.strip(), "blocks": []}); mode = "pre"; continue
            continue
        if mode == "skip": continue
        if mode == "pre":
            if pre: pre[-1]["blocks"].append({"kind": kind, "pl": pl, "page": page})
            continue
        if ch is None: continue
        if kind == "contents": ch["contents"] = pl; continue
        if kind == "score": ch["score"] = pl; continue
        if mode == "ex":
            if kind == "diag" and pl["n"]:
                ch["ex"].setdefault(pl["n"], {"n": pl["n"], "ans": []}).update({"diag": pl})
                if pl["n"] not in ch["order"]: ch["order"].append(pl["n"])
            continue
        if mode == "sol":
            if kind == "ref":
                n = re.search(r"(F-\d+|\d+-\d+)", pl)
                n = n.group(1) if n else None
                if n:
                    cur_ex = ch["ex"].setdefault(n, {"n": n, "ans": []}); cur_ex.pop("_pts", None)
                    if n not in ch["order"]: ch["order"].append(n)
                continue
            # нет заголовка «Ex. N»: шапка партии после очков (или первая в разделе) — следующее упражнение
            if kind == "game" and (cur_ex is None or cur_ex.get("_pts")):
                nxt = next((n for n in ch["order"] if not ch["ex"][n]["ans"] and "game" not in ch["ex"][n]), None)
                if nxt: cur_ex = ch["ex"][nxt]
            if cur_ex is None: continue
            if kind == "pts": cur_ex["_pts"] = True
            if kind == "from": cur_ex["from"] = pl; continue
            if kind == "game" and "game" not in cur_ex: cur_ex["game"] = pl; continue
            if kind == "pts":
                try: cur_ex["pts"] = cur_ex.get("pts", 0) + int(re.search(r"\d+", pl).group(0))
                except Exception: pass
            if kind == "diag" and pl["n"] and pl["n"] in ch["ex"] and "adiag" not in ch["ex"][pl["n"]]:
                ch["ex"][pl["n"]]["adiag"] = pl
                continue
            cur_ex["ans"].append({"kind": kind, "pl": pl, "page": page})
            continue
        # введение главы
        if kind == "ref": continue
        ch["intro"].append({"kind": kind, "pl": pl, "page": page})
    return pre, chapters

def render(blocks, L):
    out = []
    for b in blocks:
        if b["kind"] == "pts":
            out.append({"t": "pts", "x": b["pl"]}); continue
        if b["kind"] in ("p", "game", "cap", "h", "diag"):
            out += P.render([b], L) if b["kind"] != "p" else [{"t": "p", "s": P.link_paragraph(b["pl"], L)}]
    return out

PUBLISH = [a for a in sys.argv[1:] if a.startswith("yus")] or ["yus1", "yus2"]

def main():
    allbooks, stats = [], []
    for bk in [b for b in BOOKS if b["id"] in PUBLISH]:
        items, warn = load(bk)
        pre, chapters = build(items)
        chs = []
        tot, bad = 0, 0
        for ch in chapters:
            tree = P.Tree(); L = P.Linker(tree)
            intro = P.render(ch["intro"], L)
            exs = []
            for n in ch["order"]:
                e = ch["ex"][n]
                d = e.get("diag") or e.get("adiag")
                if not d or not (d.get("fen") or (e.get("adiag") or {}).get("fen")): continue
                placement = d.get("fen") or e["adiag"]["fen"]
                L.scope = []
                ans = e["ans"]
                text = " ".join(b["pl"] for b in ans if b["kind"] == "p")
                mk = re.search(r"позици\w* диаграммы[^)]*\)?", text)
                if mk: text = text[mk.end():] + " " + text      # номер хода — сразу после пометки
                else: text = " ".join(re.findall(r"\*\*(.+?)\*\*", text)) + " " + text   # или по жирной главной линии
                root = L.set_root(P.best_root(placement, d.get("turn") or (e.get("adiag") or {}).get("turn"), text))
                L.prefer = root
                blocks = render(ans, L)
                L.prefer = None
                if not any(x["parent"] == root for x in tree.nodes):
                    # партия из решения дошла до позиции диаграммы: берём её, если отличие 0–3 поля
                    # (распознавание иногда теряет тонкого слона)
                    def diff(a, b):
                        A, B = chess.Board(a + " w - - 0 1"), chess.Board(b + " w - - 0 1")
                        return sum(A.piece_at(q) != B.piece_at(q) for q in chess.SQUARES)
                    cand = sorted((diff(tree.fen(i).split(" ")[0], placement), i) for i in L.scope if i >= 0
                                  and any(x["parent"] == i for x in tree.nodes))
                    if cand and cand[0][0] > 3: print(bk["id"], "упр.", n, "ближайшая позиция партии отличается на", cand[0][0])
                    if cand and cand[0][0] <= 3:
                        if cand[0][0]: print(bk["id"], "упр.", n, "позиция взята из партии, отличий", cand[0][0])
                        root = cand[0][1]
                main, cur = [], root
                while True:
                    kids = [i for i, x in enumerate(tree.nodes) if x["parent"] == cur and x["main"]]
                    if not kids: break
                    cur = kids[0]; main.append(cur)
                if not main:          # жирного нет — первый ход ответа
                    kids = [i for i, x in enumerate(tree.nodes) if x["parent"] == root]
                    if kids: main = [kids[0]]
                if not any(x["parent"] == root for x in tree.nodes):
                    print(bk["id"], "упр.", n, "ни один ход решения не лёг на позицию", d.get("src"), placement)
                exs.append({"n": n, "g": e.get("game"), "from": e.get("from"), "pts": e.get("pts", 0),
                            "stars": d.get("stars", 0), "root": root, "main": main, "a": blocks})
            tot += len(tree.nodes); bad += len(L.bad)
            ru = "Итоговый тест" if ch.get("final") else (TITLES[bk["id"]][ch["n"] - 1] if 0 < ch["n"] <= 24 else ch["title"])
            chs.append({"n": ch["n"], "title": ru, "en": ch["title"], "contents": ch["contents"], "score": ch["score"],
                        "final": ch.get("final", False), "intro": intro, "ex": exs,
                        "roots": tree.roots, "nodes": [[x["parent"], x["uci"], x["san"], 1 if x["main"] else 0] + ([x["base"]] if x.get("threat") else []) for x in tree.nodes]})
        pre_out = [{"title": s["title"], "blocks": [{"t": "p", "x": b["pl"]} for b in s["blocks"] if b["kind"] == "p"]} for s in pre]
        allbooks.append({"id": bk["id"], "title": bk["title"], "sub": bk["sub"], "pre": pre_out, "chapters": chs})
        stats.append((bk["id"], len(chs), sum(len(c["ex"]) for c in chs), tot, bad, len(warn)))
        for w in warn[:15]: print(bk["id"], w)
    js = "/* Книги А. Юсупова: ходы и позиции из книг, комментарии — собственные (tools/yus/05_parse.py) */\n"
    js += "window.YUS = " + json.dumps(allbooks, ensure_ascii=False, separators=(",", ":")) + ";\n"
    open(os.path.join(os.path.dirname(__file__), "../../yus.js"), "w", encoding="utf-8").write(js)
    for s in stats: print("книга %s: глав %d, упражнений %d, ходов %d, не связано %d, страниц с несовпадением диаграмм %d" % s)

if __name__ == "__main__":
    main()
