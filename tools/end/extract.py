"""Дворецкий «Учебник эндшпиля» (PDF с текстовым слоем) -> end.js для блока «Эндшпиль».

Скан-пайплайн (агенты, распознавание досок) здесь не нужен: в PDF есть текст,
а диаграммы набраны шахматным шрифтом Chess-Merida — FEN читается из кодов
символов, без ошибок распознавания. Привязка ходов — общая, из
yak/06_parse.py (а тот берёт её из dvor/06_parse.py) со всеми правилами части 8/9.

Шрифты книги:
  ISChess       фигурки в ходах (K,I,G,E,C = король, ферзь, ладья, слон, конь)
                и значки оценок (Q = +−, R = −+, O = ±, …)
  Chess-Merida  доска: строка на горизонталь, код = фигура + цвет поля
  PetersburgC-Bold  жирные ходы (главная линия; в скобках — нет, см. Linker)
  NewtonC-BoldItalic  правила («Ключевыми мы называем поля…»)
  Optima-Bold 12.2 — раздел («КЛЮЧЕВЫЕ ПОЛЯ»), 11.7/13.6 — подраздел, «ТРАГИКОМЕДИИ»
  Optima-Regular 12.6 — «Упражнения»; Optima 9.7/8.7 под доской — подпись

Квадратик у номера диаграммы: белый — ход белых, чёрный — ход чёрных,
«?» — позицию предлагается решить самому (ответ в тексте скрыт),
➠ — упражнение повышенной сложности. Решения упражнений (глава 16)
ставятся сразу за диаграммой упражнения, тоже скрытыми.

Запуск: python3 extract.py [главы, по умолчанию 0,1]   (из tools/end)"""
import json, re, os, sys, importlib.util
import pymupdf, chess
import boards as BD
BD.SHIFT = True

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "../../Dvoretsky_Endshpil.pdf")

# ---------- привязка ходов: yak/06_parse.py поверх dvor/06_parse.py ----------
def load_linker():
    dsrc = open(os.path.join(HERE, "../dvor/06_parse.py"), encoding="utf-8").read()
    dsrc = re.sub(r'(?m)^FENS = .*$', "FENS = {}", dsrc)
    dsrc = re.sub(r'(?ms)^BOARDS = .*?\n(?=FIX)', "BOARDS = {}\n", dsrc)
    ysrc = open(os.path.join(HERE, "../yak/06_parse.py"), encoding="utf-8").read()
    ysrc = ysrc.replace("spec.loader.exec_module(P)", "exec(compile(DSRC, 'dvor/06_parse.py', 'exec'), P.__dict__)")
    Y = type(sys)("yak_parse"); Y.__file__ = os.path.join(HERE, "../yak/06_parse.py")
    Y.__dict__["DSRC"] = dsrc
    sys.argv.append("--no-main")
    exec(compile(ysrc, "yak/06_parse.py", "exec"), Y.__dict__)
    return Y
Y = load_linker(); P = Y.P

# оценка «+−» не шах: суффикс хода не съедает «+» перед «−»
P.MOVE_RX = re.compile(P.MOVE_RX.pattern.replace(r"(?P<suf>[+#]*[!?]*)", r"(?P<suf>(?:\+(?!−)|\#)*[!?]*)"), re.X)
# доски набраны шрифтом — позиция точная: диаграмма совпадает с узлом только целиком,
# «почти та же» позиция в эндшпиле — чаще другой пример (а не ошибка картинки)
P.diff_placement = lambda a, b: 0 if a == b else 99
P.repair_root = lambda *a, **k: None
# новая диаграмма — новый пример: ходы ищутся только в нём
_set_root = P.Linker.set_root
def set_root(self, fen):
    # «возвращаемся к партии» ([[RESUME]]) — состояние до первой новой диаграммы раздела
    if getattr(self, "hist", None) is not None: self.hist.append((self.cur, self.main, list(self.scope)))
    self.scope = []
    return _set_root(self, fen)
P.Linker.set_root = set_root
# ход с номером, совпавший с только что сыгранным («1.Kg1? Kd7 … 1...Kd7 2.Kg3») —
# автор говорит о другой ветке: ищем его и у других узлов той же глубины
_cands = P.Linker.candidates
def candidates(self, want):
    c = _cands(self, want)
    # корень угрозы («грозит 33.Bc6») — не позиция партии: номерной ход туда не ищем
    thr = {n["parent"] for n in self.t.nodes if n.get("threat")}
    c = [x for x in c if not (x < 0 and x in thr and x != self.cur)
         and not (x >= 0 and self.t.nodes[x].get("threat"))]
    # (но не когда предыдущий ход — план в прозе полной записью: «запланировал e6-e5. Однако на 31...e5»)
    if getattr(self, "_tok", None) and not getattr(self, "_prevlone", False) and self.cur is not None and self.cur >= 0 and len(c) > 1:
        par = self.t.nodes[self.cur]["parent"]
        if par in c and self._tok == self.t.nodes[self.cur]["san"].rstrip("+#").replace("x", ":").replace(":", ""):
            c = [x for x in c if x != par] + [par]
    return c
P.Linker.candidates = candidates
_pplay = P.Linker.play
def pplay(self, tok, num, dots, prev_ply, bold):
    self._tok = re.sub(r"[-:x+#!?]", "", tok) if num else None
    self._prevlone = getattr(self, "_curlone", False)
    self._curlone = getattr(self, "lone", False) and not num and "-" in tok
    try:
        if not num and getattr(self, "lone", False) and self.cur is not None:
            # ход без номера посреди прозы («угрозу хода Bb7») — только у текущей
            # позиции и на её пути к корню, а не в любой позиции раздела
            path, n = [], self.cur
            while n is not None:
                path.append(n); n = self.t.parent(n)
            old = self.scope; self.scope = path
            try: r = _pplay(self, tok, num, dots, prev_ply, bold)
            finally:
                self.scope = old + [x for x in self.scope if x not in path and x not in old]
            return r
        r = _pplay(self, tok, num, dots, prev_ply, bold)
        # «Другая попытка черных: 1...Kg7 …» — возврат к прежнему примеру раздела:
        # номерной ход, не легший в текущем, ищется во всех позициях раздела
        if r[0] is None and num and getattr(self, "sec0", None) is not None and self.cur is not None:
            n0, r0 = self.sec0
            allx = [-(k + 1) for k in range(r0, len(self.t.roots))] + \
                   [i for i in range(n0, len(self.t.nodes)) if not self.t.nodes[i].get("threat")]
            extra = [x for x in allx if x not in self.scope]
            if bold:        # жирный — продолжение главной линии: её узлы проверяются первыми
                extra = [x for x in extra if x < 0 or not self.t.nodes[x]["main"]] + \
                        [x for x in extra if x >= 0 and self.t.nodes[x]["main"]]
            if extra:
                sc = self.scope
                self.scope = extra + sc
                r = _pplay(self, tok, num, dots, prev_ply, bold)
                if r[0] is None: self.scope = sc
        return r
    finally: self._tok = None
P.Linker.play = pplay

# ---------- шрифты ----------
ISC = {"K": "K", "I": "Q", "G": "R", "E": "B", "C": "N",
       "Q": "+−", "R": "−+", "O": "±", "P": "∓", "M": "⩲", "N": "⩱", "T": "∞",
       "Z": "⇄", "[": "⊙", "c": "∆", "d": "□"}
MER = {0x10: "p", 0x09: "p", 0x0a: "P", 0x11: "P", 0x0b: "K", 0x13: "K", 0x0c: "k", 0x12: "k",
       0x14: "b", 0x17: "b", 0x16: "B", 0x15: "B", 0x18: "Q", 0x1b: "Q", 0x23: "q", 0x1f: "q",
       0x1a: "N", 0x22: "N", 0x1c: "n", 0x19: "n", 0x20: "R", 0x1d: "R", 0x1e: "r", 0x21: "r",
       0x02: ".", 0x03: "."}

def fen_of(rows):
    out = []
    for r in rows:
        s, e = "", 0
        for ch in r[1:9]:
            x = MER.get(ord(ch))
            if x is None: raise ValueError(f"код {ord(ch):#x}")
            if x == ".": e += 1; continue
            if e: s += str(e); e = 0
            s += x
        out.append(s + (str(e) if e else ""))
    return "/".join(out)

def box_kind(page, x1, y0):
    """квадратик справа над доской: 'w', 'b' или None (нет квадратика)"""
    for dr in page.get_drawings():
        r = dr["rect"]
        if 7 < r.width < 14 and 7 < r.height < 14 and x1 - 30 < r.x0 < x1 + 5 and y0 - 22 < r.y0 < y0:
            pix = page.get_pixmap(clip=pymupdf.Rect(r.x0 + 2, r.y0 + 2, r.x1 - 2, r.y1 - 2), dpi=300, colorspace=pymupdf.csGRAY)
            dark = sum(1 for v in pix.samples if v < 128) / max(1, len(pix.samples))
            return "b" if dark > .5 else "w"
    return None

# ---------- страница -> объекты ----------
def page_objects(pn, page, two_cols):
    """строки текста и диаграммы с координатами; колонтитул выброшен"""
    lines, diags, rows = [], [], []
    d = page.get_text("dict")
    for b in d["blocks"]:
        for l in b.get("lines", []):
            sp = [s for s in l["spans"] if s["text"]]
            if not sp: continue
            if "Merida" in sp[0]["font"]:
                if sp[0]["size"] > 30: continue            # узор на титуле главы
                rows.append((sp[0]["bbox"], "".join(s["text"] for s in sp)))
                continue
            lines.append(sp)
    # доски: \x04 — верхняя рамка, 8 строк поля, \x0d — нижняя
    rows.sort(key=lambda r: (round(r[0][0] / 20), r[0][1]))
    i = 0
    while i < len(rows):
        if rows[i][1].startswith("\x04") and i + 9 < len(rows) and rows[i + 9][1].startswith("\x0d"):
            bb = [rows[i][0][0], rows[i][0][1], rows[i + 9][0][2], rows[i + 9][0][3]]
            diags.append({"bb": bb, "fen": fen_of([r[1] for r in rows[i + 1:i + 9]])})
            i += 10
        else: i += 1
    # доски, переведённые в кривые: клетки сравниваются с эталонами (boards.py)
    for vb in BD.vector_boards(page):
        cells, _ = BD.board_cells(page, vb["bb"])
        fen, worst, _ = BD.classify(cells)
        diags.append({"bb": vb["bb"], "fen": fen, "vec": round(worst, 1)})
    # подписи досок: номер «1-38» и «?» над доской, источник под ней
    rest = []
    def owner_of(s):
        x0, y0, x1, y1 = s["bbox"]
        for dg in diags:
            X0, Y0, X1, Y1 = dg["bb"]
            if X0 - 5 <= x0 and x1 <= X1 + 5 and Y0 - 22 <= y0 < Y0 + 2: return dg, "top"
            if X0 - 5 <= x0 <= X1 and Y1 - 2 <= y0 < Y1 + 26 and s["font"].startswith("Optima") and s["size"] < 10.5: return dg, "cap"
            if X0 - 2 <= x0 and x1 <= X1 + 2 and Y0 <= y0 and y1 <= Y1: return dg, "in"
        return None
    for sp in lines:
        txt = "".join(s["text"] for s in sp).strip()
        y1 = max(s["bbox"][3] for s in sp)
        if y1 < 50 and (sp[0]["font"].startswith("Optima-Regular") or re.fullmatch(r"\d+", txt)): continue   # колонтитул
        keep = []
        for s in sp:
            o = owner_of(s)
            if not o: keep.append(s); continue
            dg, where = o
            t = s["text"].strip()
            if where == "top":
                m = re.search(r"\d+-\d+", t)
                if m: dg["n"] = m.group(0)
                if "?" in t: dg["q"] = True
                if "➠" in t: dg["hard"] = True
            elif where == "cap" and t:
                if dg.get("capy") is not None and abs(s["bbox"][1] - dg["capy"]) < 3: dg["cap"][-1] += s["text"]
                else: dg.setdefault("cap", []).append(s["text"]); dg["capy"] = s["bbox"][1]
        while keep and not keep[0]["text"].strip(): keep.pop(0)
        if not keep: continue
        x0, y0, x1 = keep[0]["bbox"][0], min(s["bbox"][1] for s in keep), keep[-1]["bbox"][2]
        y1 = max(s["bbox"][3] for s in keep)
        rest.append({"x0": x0, "y0": y0, "y1": y1, "sp": keep, "txt": "".join(s["text"] for s in keep).strip()})
    for dg in diags:
        if dg.get("cap"): dg["cap"] = [c.strip() for c in dg["cap"] if c.strip()]
    for dg in diags:
        dg["turn"] = box_kind(page, dg["bb"][2], dg["bb"][1])
        # «?» бывает отдельным кусочком текста внутри квадратика
    out = [dict(kind="line", **r) for r in rest] + [dict(kind="diag", x0=dg["bb"][0], y0=dg["bb"][1] - 10, dg=dg) for dg in diags]
    mid = page.rect.width / 2
    if two_cols:
        out.sort(key=lambda o: (o["x0"] > mid - 10, o["y0"], o["x0"]))
    else:
        out.sort(key=lambda o: (round(o["y0"]), o["x0"]))
    for o in out: o["page"] = pn
    return out

CYR = str.maketrans("асе", "ace")

def line_text(sp):
    """спаны строки -> текст: фигурки латиницей, жирное в ** **; правило/шрифт строки"""
    parts = []
    for k, s in enumerate(sp):
        f, t = s["font"], s["text"]
        if f == "ISChess":
            t = "".join(ISC.get(c, c) for c in t)
            nxt = sp[k + 1] if k + 1 < len(sp) else None
            prv = sp[k - 1] if k else None
            piece = t in ("K", "Q", "R", "B", "N")
            ref = nxt if piece and nxt is not None and re.match(r"[a-h:x]", nxt["text"]) else prv
            bold = ref is not None and "PetersburgC-Bold" in ref["font"]
        elif f in ("Wingdings-Regular", "ZapfDingbats"):
            continue
        else:
            bold = "PetersburgC-Bold" in f
        if parts and parts[-1][1] == bold: parts[-1][0] += t
        else: parts.append([t, bold])
    for a, b in zip(parts, parts[1:]):     # «2.Rh5» жирным, «+!» обычным — знаки к ходу
        m = re.match(r"[+#!?]+", b[0])
        if a[1] and not b[1] and m: a[0] += m.group(0); b[0] = b[0][m.end():]
    for p in parts:      # «Kс7», «с5» — кириллица вместо латиницы в поле хода
        p[0] = re.sub(r"(?<![А-Яа-яЁё])([асеbвh]?)([асе])([1-8])(?![А-Яа-яЁё])",
                      lambda m: m.group(1).translate(CYR) + m.group(2).translate(CYR) + m.group(3), p[0])
    s = ""
    for t, b in parts:
        if b and re.search(r"[a-h][1-8]|0-0|\b[a-h][a-h]\b", t):
            lead = len(t) - len(t.lstrip()); tail = len(t) - len(t.rstrip())
            s += t[:lead] + "**" + t.strip() + "**" + t[len(t) - tail:]
        else: s += t
    return s

def kind_of(sp):
    f, z = sp[0]["font"], sp[0]["size"]
    if f == "Optima-Italic" and z > 15: return "chapno"
    if f.startswith("Optima-Regular") and z > 20: return "chaptitle"
    if f == "Optima-Bold" and 12 < z < 13: return "sec"
    if f == "Optima-Bold" and (11 < z < 12 or z > 13): return "sub"
    if f.startswith("Optima-Regular") and 12 < z < 13: return "sub"
    if f.startswith("Optima") and z > 15: return "sec"
    if all(s["font"] == "NewtonC-BoldItalic" or not s["text"].strip() for s in sp): return "rule"
    return "text"

def flow(pages, two_cols=False):
    """страницы -> поток: chapter/sec/sub/p/diag. Абзац начинается с отступа."""
    doc = pymupdf.open(PDF)
    objs = []
    for pn in pages: objs += page_objects(pn, doc[pn], two_cols)
    items, para, prev = [], None, None
    def flush():
        nonlocal para
        if para and para["t"].strip():
            t = re.sub(r"(\d)\s*\.\.\.\s+(?=\**[KQRBNa-h0])", r"\1...", para["t"].strip())      # «2... Kc8» -> «2...Kc8»
            t = re.sub(r"(\d)\.\s+(?=[KQRBNa-h0]\S)", r"\1.", t)
            items.append(("p", t, para["page"], para["rule"]))
        para = None
    # левые края колонок на странице — для отступа абзаца
    lefts = {}
    for o in objs:
        if o["kind"] == "line": lefts.setdefault((o["page"], two_cols and o["x0"] > 230), []).append(o["x0"])
    def left_of(o):
        xs = sorted(lefts[(o["page"], two_cols and o["x0"] > 230)])
        cand = [x for x in xs if sum(1 for y in xs if abs(y - x) < 2) >= 2]
        # край колонки — самый левый частый край в пределах 20 pt слева
        c = [x for x in cand if o["x0"] - 20 <= x <= o["x0"] + 1]
        return min(c, default=o["x0"])
    head = None
    pend = []
    _flush = flush
    def flush():
        _flush()
        for x in pend: items.append(x)
        pend.clear()
    for o in objs:
        if o["kind"] == "diag":
            it = ("diag", o["dg"], o["page"], None)
            if head: items.append(tuple(head[:3]) + (None,)); head = None
            # доска стоит рядом с текстом: абзац начался строкой-двумя выше доски —
            # он про неё, доска перед ним; начался давно — доска после абзаца
            if para and para["page"] == o["page"] and para["y0"] >= o["y0"] - 20: items.append(it)
            elif para: pend.append(it)
            else: items.append(it)
            continue
        k = kind_of(o["sp"]); txt = line_text(o["sp"])
        if k in ("chapno", "chaptitle", "sec", "sub"):
            flush()
            if head and head[0] == k and head[2] == o["page"] and o["y0"] - head[3] < 30:
                head[1] += " " + txt.strip()
            else:
                if head: items.append(tuple(head[:3]) + (None,))
                head = [k, txt.strip(), o["page"], o["y0"]]
            head[3] = o["y0"]; prev = None; continue
        if head: items.append(tuple(head[:3]) + (None,)); head = None
        new = para is None or prev is None
        if not new:
            ind = o["x0"] - left_of(o)
            gap = o["y0"] - prev["y1"] if prev["page"] == o["page"] else 0
            new = ind > 5 or gap > 9 or (k == "rule") != para["rule"] and ind > 1
        if new:
            flush(); para = {"t": txt, "page": o["page"], "rule": k == "rule", "y0": o["y0"]}
        else:
            t = para["t"]
            if re.search(r"[а-яёa-z]-$", t) and re.match(r"\**[а-яё]", txt): para["t"] = t[:-1] + txt.lstrip()
            elif t.endswith("**") and txt.startswith("**"): para["t"] = t[:-2] + " " + txt[2:]
            else: para["t"] = t.rstrip() + " " + txt.lstrip()
        prev = o
    flush()
    if head: items.append(tuple(head[:3]) + (None,))
    return items

# ---------- главы ----------
def fix_labels(items):
    """номер диаграммы бывает набран в тексте («1-6 1.Rf4?? …» — трагикомедии
       в три колонки) или не попал в текстовый слой вовсе (1-4)"""
    items = list(items)
    i = 0
    while i < len(items):
        k, pl, page, rule = items[i]
        m = re.match(r"^(\d+-\d+)\s+(.*)$", pl) if k == "p" else None
        if m:
            lab = m.group(1)
            js = [j for j in range(max(0, i - 6), i) if items[j][0] == "diag" and items[j][2] == page
                  and items[j][1].get("n") in (None, lab)]
            js.sort(key=lambda j: items[j][1].get("n") != lab)
            if js:
                j = js[0]; d = items.pop(j); d[1]["n"] = lab
                i -= 1
                items.insert(i, d)
                items[i + 1] = ("p", m.group(2), page, rule)
        i += 1
    # подзаголовок справа от доски чуть ниже её верха («Пат» у 8-6) — он над ней
    for i in range(1, len(items)):
        if items[i][0] in ("sub", "sec") and items[i - 1][0] == "diag" and items[i][2] == items[i - 1][2]:
            items[i - 1], items[i] = items[i], items[i - 1]
    # пропуск в нумерации: между 1-3 и 1-5 — 1-4
    ds = [it[1] for it in items if it[0] == "diag"]
    for a, dg in enumerate(ds):
        if dg.get("n"): continue
        prev = next((x["n"] for x in reversed(ds[:a]) if x.get("n")), None)
        nxt = next((x["n"] for x in ds[a + 1:] if x.get("n")), None)
        if not prev and nxt and a == sum(1 for x in ds[:a] if not x.get("n")) and ds.index(dg) + 1 < int(nxt.split("-")[1]) \
           and all(not x.get("n") for x in ds[:a]):
            dg["n"] = f"{nxt.split('-')[0]}-{a + 1}"; continue
        if prev and nxt:
            c, k = prev.split("-"); c2, k2 = nxt.split("-")
            gap = [x for x in ds[ds.index(next(x for x in reversed(ds[:a]) if x.get("n") == prev)) + 1:] ]
            miss = 0
            for x in gap:
                if x.get("n"): break
                miss += 1
            if c == c2 and int(k2) - int(k) - 1 == miss:
                dg["n"] = f"{c}-{int(k) + 1}"
                # следующие безымянные подряд получат номер на своём шаге
    return items

def split_chapters(items):
    chs = [{"n": 0, "title": "Предисловие", "items": []}]
    num = None
    for it in items:
        if it[0] == "chapno":
            num = int(re.search(r"\d+", it[1]).group(0)); continue
        if it[0] == "chaptitle":
            chs.append({"n": num, "title": it[1], "items": []}); continue
        chs[-1]["items"].append(it)
    return chs

def solutions(pages):
    """глава 16 -> {«1-14»: [items]} по заголовкам «1-14. К.Сальвиоли, 1887»"""
    out, cur = {}, None
    for it in fix_labels(flow(pages, two_cols=True)):
        if it[0] in ("chapno", "chaptitle", "sec", "sub"): continue
        if it[0] == "p":
            m = re.match(r"^\**(\d+-\d+)\.\s*(.*)$", it[1])
            if m:
                cur = out.setdefault(m.group(1), [])
                cur.append(("head", re.sub(r"\*\*", "", m.group(2)).strip(), it[2], None)); continue
        if cur is not None: cur.append(it)
    return out

REF = re.compile(r"(?:диаграмм\w*|позици\w+)\s+(\d+-\d+)")

SIDE = re.compile(r"[Пп]ри\s+(?:своем\s+)?ходе\s+(белых|черных)")

def twin(L, side):
    """та же позиция диаграммы, но ход другой стороны («При ходе белых решает …»)"""
    base = getattr(L, "diag", None)
    if base is None: return None
    f = L.t.fen(base).split(" ")
    if f[1] == side: return base
    key = (base, side)
    tw = L.__dict__.setdefault("twins", {})
    if key not in tw:
        f[1] = side; f[3] = "-"
        b = chess.Board(" ".join(f))
        tw[key] = L.t.add_root(b.fen()) if b.is_valid() else None
    return tw[key]

def link_para(text, L, labels):
    """абзац -> сегменты; после «диаграмме 1-1» ходы ищутся от той диаграммы,
       после «при ходе белых» — от диаграммы с ходом белых; после абзаца
       положение возвращается"""
    cuts = [(m, labels[m.group(1)]) for m in REF.finditer(text) if m.group(1) in labels]
    cuts += [(m, twin(L, "w" if m.group(1) == "белых" else "b")) for m in SIDE.finditer(text)]
    cuts = sorted((c for c in cuts if c[1] is not None), key=lambda c: c[0].start())
    if not cuts: return P.link_paragraph(text, L)
    st = (L.cur, L.main, list(L.scope), list(L.stack))
    segs, pos = [], 0
    for m, r in cuts:
        segs += P.link_paragraph(text[pos:m.end()], L); pos = m.end()
        L.cur, L.main, L.scope, L.stack = r, r, [r] + [i for i, n in enumerate(L.t.nodes) if P_root(L, i) == r], []
    segs += P.link_paragraph(text[pos:], L)
    L.cur, L.main, L.scope, L.stack = st[0], st[1], st[2], st[3]
    out = []
    for x in segs:
        if isinstance(x, str) and out and isinstance(out[-1], str): out[-1] += x
        else: out.append(x)
    return out

def P_root(L, i):
    return L.t.nodes[i]["root"]

def score_root(fen, text):
    """сколько ходов текста ложится на позицию; жирные (главная линия) — втрое"""
    t = P.Tree(); L = P.Linker(t); L.set_root(fen)
    for para in re.split(r"\n+", text or ""):
        P.link_paragraph(para, L)
    return sum(3 if x["main"] else 1 for x in t.nodes if x["root"] == -1)

def best_root(placement, turn, text):
    """очередь хода — с квадратика у диаграммы (закон), без квадратика — по тексту;
       номер хода — тот, при котором на позицию ложится больше ходов всего текста
       до следующей диаграммы (жирные важнее: «1.Ka2!!» после прозы с «2.Kf2»)"""
    cast = P.castle_fen(placement)
    sides = [turn] if turn else ["w", "b"]
    cands = []
    for m in P.MOVE_RX.finditer(text or ""):
        num, dots = m.group("num"), m.group("dots")
        if not num or not dots: continue
        sd = "w" if dots == "." else "b"
        c = f"{placement} {sd} {cast} - 0 {int(num)}"
        if sd in sides and c not in cands: cands.append(c)
        if len(cands) >= 10: break
    for sd in sides:
        c = f"{placement} {sd} {cast} - 0 1"
        if c not in cands: cands.append(c)
    ok = []
    for c in cands:
        try:
            if chess.Board(c).is_valid(): ok.append(c)
        except ValueError: pass
    if not ok: return cands[-1] if turn else P.root_fen(placement, turn, text)
    # при равенстве — номер из текста (он первым в списке), «1» — последним:
    # сбитый номер разборщик тоже привяжет, и счёт выйдет тот же
    return max(ok, key=lambda c: (score_root(c, text), -ok.index(c)))

def render_run(blocks, L, labels):
    """dvor.render: диаграмма — известная позиция примера (точно та же) или новый
       корень (очередь хода и номер — best_root по тексту после неё)"""
    out = []
    for i, b in enumerate(blocks):
        k, pl = b["kind"], b["pl"]
        if k == "game": out.append({"t": "g", "x": pl}); continue
        if k == "resume":
            h = [x for x in (getattr(L, "hist", None) or []) if x[1] is not None]
            if h:
                L.cur, L.main, L.scope = h[0][0], h[0][1], list(h[0][2]); L.stack = []; L.hist = []
            elif L.main is not None:        # без доски-отступления: к последнему ходу главной линии
                L.cur = L.main; L.stack = []
            continue
        if k == "diag":
            placement = pl["fen"]
            found = None
            for nid in reversed(L.scope):
                f = L.t.fen(nid).split(" ")
                if f[0] == placement and (pl["turn"] is None or f[1] == pl["turn"]): found = nid; break
            if pl.get("q"): L.sec0 = (len(L.t.nodes), len(L.t.roots))     # позиция «?» — отдельный пример
            if found is None:
                nxt, far = [], False
                for x in blocks[i + 1:]:
                    if x["kind"] == "game": break
                    if x["kind"] == "diag":
                        # до следующей доски номерных ходов нет — номер берём дальше по тексту
                        # (только для первой доски партии — после шапки)
                        if not (i == 0 or blocks[i - 1]["kind"] == "game") or \
                           any(m.group("num") and m.group("dots") for m in P.MOVE_RX.finditer("\n".join(nxt))): break
                        far = True; continue
                    if x["kind"] == "p": nxt.append(x["pl"])
                if pl.get("num") and pl.get("turn"):     # номер хода указан в разметке
                    found = L.set_root(f"{placement} {pl['turn']} {P.castle_fen(placement)} - 0 {pl['num']}")
                else:
                    found = L.set_root(best_root(placement, pl["turn"], "\n".join(nxt)))
            else:
                # диаграмма в конце побочного варианта главную линию не сдвигает:
                # жирный ход после неё («Партия продолжалась: 14...Nd6») — к главной
                if found < 0 or L.t.nodes[found]["main"] or L.main is None: L.main = found
                L.cur = found; L.stack = []
            if pl.get("n"): labels.setdefault(pl["n"], found)
            L.diag = found
            out.append({"t": "d", "n": found, "small": pl["small"]}); continue
        if k == "p": out.append({"t": "p", "s": link_para(pl, L, labels)})
    return out

def title_case(t):
    return t[:1] + t[1:].lower() if t.isupper() else t

def render_chapter(ch, sols):
    t = P.Tree(); L = P.Linker(t)
    L.sec0 = (0, 0)
    labels = {}
    out, run, meta = [], [], []
    nsec = [0]
    def go():
        if not run: return
        res = render_run(run, L, labels)
        for b, m in zip(res, [m for m in meta if m is not None]):
            b.update(m)
        out.extend(res); run.clear(); meta.clear()
    def reset():
        L.scope = []; L.cur = None; L.main = None; L.stack = []
        L.sec0 = (len(t.nodes), len(t.roots)); L.diag = None; L.hist = []
    hide = False
    def add(kind, pl, m):
        run.append({"kind": kind, "pl": pl}); meta.append(m)
    for kind, pl, page, rule in ch["items"]:
        if kind == "sec":
            go(); reset(); hide = False; nsec[0] += 1
            out.append({"t": "s", "n": None, "key": f"{ch['n']}.{nsec[0]}", "x": title_case(pl)}); continue
        if kind == "sub":
            go(); reset(); hide = False
            out.append({"t": "u", "x": title_case(pl)}); continue
        if kind == "diag":
            dg = pl
            cap = " · ".join(dg.get("cap", []))
            head = (dg.get("n") or "") + (" | " + cap if cap else "")
            if dg.get("hard"): head += (" · " if cap else " | ") + "повышенной сложности"
            if head: add("game", head, {})
            add("diag", {"n": dg.get("n"), "turn": dg.get("turn"), "small": False, "fen": dg["fen"], "src": f"{page}", "q": dg.get("q"), "num": dg.get("num")},
                {"q": 1} if dg.get("q") else {})
            hide = bool(dg.get("q"))
            sol = sols.get(dg.get("n")) if dg.get("q") else None
            if sol:
                for sk, spl, spage, srule in sol:
                    if sk == "head": continue
                    if sk == "diag":
                        add("diag", {"n": spl.get("n"), "turn": spl.get("turn"), "small": True, "fen": spl["fen"], "src": f"{spage}"}, {"h": 1})
                    elif sk == "p":
                        add("p", spl, {"h": 1, "sol": 1})
                hide = False
            continue
        if kind == "resume":
            add("resume", None, None); continue
        if kind == "p" and pl.strip("* ").upper() == ch["title"].upper(): continue   # «ПРЕДИСЛОВИЕ» текстом
        if kind == "p":
            # ответ к позиции «?» — всё до следующей диаграммы или заголовка
            m = {"h": 1} if hide else {}
            if rule: m["r"] = 1
            add("p", pl, m)
    go()
    # диаграмма посреди варианта, до которого текст дошёл позже (ходы легли в
    # дерево прежнего примера): у её корня нет ходов — ставим её на тот узел
    kids = {n["parent"] for n in t.nodes}
    for b in out:
        if b["t"] == "d" and b.get("n") is not None and b["n"] < 0 and b["n"] not in kids:
            f = " ".join(t.fen(b["n"]).split(" ")[:2])
            same = [i for i, n in enumerate(t.nodes) if " ".join(n["fen"].split(" ")[:2]) == f]
            if not same:        # квадратик у диаграммы бывает о другой стороне
                same = [i for i, n in enumerate(t.nodes) if n["fen"].split(" ")[0] == f.split(" ")[0]]
            if same: b["n"] = same[0]
    L.bad = [x for x in L.bad if not Y.LINE(x)]
    return out, t, L.bad

def main():
    want = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "--no-main" else "0,1").split(",")]
    doc = pymupdf.open(PDF)
    last = 441
    items = flow(range(8, last + 1)) if max(want) > 1 else flow(range(8, 87))
    chs = [c for c in split_chapters(fix_labels(items)) if c["n"] in want]
    sol_pages = range(442, 513)
    sols = solutions(sol_pages)
    res, allbad, tot = [], [], 0
    for ch in chs:
        blocks, t, bad = render_chapter(ch, sols)
        allbad += [f"гл.{ch['n']}: {x}" for x in bad]
        linked = sum(1 for b in blocks for s in (b.get("s") or []) if isinstance(s, dict))
        tot += linked
        diags = [b for b in blocks if b["t"] == "d" and "n" in b and not b.get("h")]
        secs = [b for b in blocks if b["t"] == "s"]
        res.append({"n": ch["n"], "title": title_case(ch["title"]), "intro": blocks, "roots": t.roots,
                    "secs": len(secs), "diags": len(diags),
                    "nodes": [[x["parent"], x["uci"], x["san"], 1 if x["main"] else 0] + ([x["base"]] if x.get("threat") else [])
                              for x in t.nodes]})
        print(f"глава {ch['n']}: {ch['title']} — разделов {len(secs)}, диаграмм {len(diags)}, ходов связано {linked}, не связано {len(bad)}")
    book = {"id": "end", "title": "Учебник эндшпиля", "author": "Марк Дворецкий", "unit": "sec", "chapters": res}
    js = "/* «Эндшпиль»: М. Дворецкий «Учебник эндшпиля», разобрано из PDF (tools/end). Генерируется extract.py */\n"
    js += "window.END = " + json.dumps([book], ensure_ascii=False, separators=(",", ":")) + ";\n"
    open(os.path.join(HERE, "../../end.js"), "w", encoding="utf-8").write(js)
    os.makedirs(os.path.join(HERE, "work"), exist_ok=True)
    open(os.path.join(HERE, "work/unlinked.txt"), "w").write("\n".join(allbad))
    print("итого связано", tot, "не связано", len(allbad), f"({100 * len(allbad) / max(1, tot + len(allbad)):.1f}%)")

if __name__ == "__main__":
    main()
