"""Разметка страниц + FEN диаграмм -> книга Яковлева для сайта (yak.js).

Общая часть (привязка ходов к позициям, деревья вариантов) — из
dvor/06_parse.py: Tree, Linker, link_paragraph, best_root. Здесь только
устройство этой книги и её нотация.

Книга — чтение, задач нет: предисловие и шесть глав, в главе —
пронумерованные разборы партий «№1. Пешки и слабые поля». На сайте
глава — карточка, открывается читалкой. Одно дерево вариантов на главу,
каждый разбор начинает поиск позиций заново.

Нотация полная: «19.Re3-d3», «18...Qd8:c7», «20...g4:f3», «e2-e4».
В общем разборщике длинная запись есть только для пешки, и «Re3-d3»
разбиралось бы как «Re3» — поэтому регулярка дополнена длинной записью
фигуры и взятия, стоящей первой.

Запуск: python3 06_parse.py (из tools/yak)"""
import json, re, os, sys, importlib.util
import chess
sys.argv.append("--no-main")
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("P", os.path.join(HERE, "../dvor/06_parse.py"))
P = importlib.util.module_from_spec(spec)
cwd = os.getcwd(); os.chdir(os.path.join(HERE, "../dvor")); spec.loader.exec_module(P); os.chdir(cwd)
W = os.path.join(HERE, "work")

# ---------- нотация: длинная запись ----------
P.MOVE_RX = re.compile(r"""
  (?P<num>\d{1,3})?\s*(?P<dots>\.\.\.|…|\.\s?\.\.|\.)?\s*
  (?P<mv>
     0-0-0|0-0|O-O-O|O-O|
     [KQRBN]?[a-h][1-8][-:x][a-h][1-8](?:=?[QRBN])?|
     [KQRBN][a-h]?[1-8]?[:x]?[a-h][1-8](?:=?[QRBN])?|
     [a-h][:x][a-h][1-8](?:=?[QRBN])?|
     [a-h][1-8](?:=?[QRBN])?|
     [a-h][a-h](?:[QRBN])?
  )
  (?P<suf>[+#]*[!?]*)
""", re.X)
_match = P.match_move
NUMBERED = [False]          # ход с номером или жирный (строка партии) — см. play()
def match_move(board, tok):
    m = re.fullmatch(r"([KQRBN])?([a-h][1-8])[-:x]([a-h][1-8])=?([QRBN])?", tok)
    if m and not m.group(1):
        # «a2-g8», «b6-f2» — диагональ или линия в прозе, пешка так не ходит
        a, b = m.group(2), m.group(3)
        df, dr = abs(ord(a[0]) - ord(b[0])), abs(int(a[1]) - int(b[1]))
        if df > 1 or dr > 2 or dr == 0 or (df == 1 and dr != 1): return None
    if m:
        pc, a, b, pr = m.groups()
        a, b = chess.parse_square(a), chess.parse_square(b)
        want = P.PIECE[pc] if pc else chess.PAWN
        ok = lambda x: x.to_square == b and x.promotion in (None, P.PIECE[pr] if pr else chess.QUEEN) \
                       and board.piece_type_at(x.from_square) == want
        c = [x for x in board.legal_moves if ok(x) and x.from_square == a]
        if c: return c[0]
        # опечатка в поле «откуда» («21.Nf3-g5», конь на e6): фигура этого типа
        # идёт на это поле единственным способом — это та же короткая запись
        c = [x for x in board.legal_moves if ok(x)]
        if len(c) != 1: return None
        fr = c[0].from_square
        if want == chess.PAWN:
            # та же вертикаль и направление той стороны, что в записи
            up = chess.square_rank(b) > chess.square_rank(a)
            if chess.square_file(fr) != chess.square_file(a) or up != (board.turn == chess.WHITE): return None
        elif not NUMBERED[0] and chess.square_file(fr) != chess.square_file(a) and chess.square_rank(fr) != chess.square_rank(a):
            return None          # ход в прозе: принимаем опечатку только в одном знаке поля
        return c[0]
    return _match(board, tok)
P.match_move = match_move

# Номер хода обязан совпасть с глубиной позиции. Общий разборщик при сбитом
# номере пробует позицию диаграммы — в этой книге так ход с опечаткой
# показывался на доске в чужой позиции. Разрешаем только продолжение
# текущей позиции той же стороной (сбитый номер в книге).
_play = P.Linker.play
def play(self, tok, num, dots, prev_ply, bold):
    n0, r0, cur0 = len(self.t.nodes), len(self.t.roots), self.cur
    st0 = (self.cur, self.main, list(self.scope), list(self.stack))
    # ход без номера сразу за несвязанным ходом той же цепочки («…9.Ke3 g4»):
    # цепочка оборвалась, и текущая позиция — не та, в которой он сделан
    if not num and getattr(self, "fail", False) and not getattr(self, "lone", True):
        return None, None if prev_ply is None else prev_ply + 1
    # «пункт g5(g4)» сразу после диаграммы — поле, а не первый ход от неё
    if not num and not bold and re.fullmatch(r"[a-h][1-8]", tok) and self.cur is not None and self.cur < 0:
        return None, prev_ply
    fail0 = getattr(self, "fail", False)
    NUMBERED[0] = bool(num) or bold
    nid, pp = _play(self, tok, num, dots, prev_ply, bold)
    if nid is None and num: nid, pp = renumber(self, tok, num, dots, bold)
    NUMBERED[0] = False
    self.fail = nid is None
    if nid is None or not num: return nid, pp
    want = P.tok_ply(num, dots, None)
    n = self.t.nodes[nid]
    if n["ply"] == want + 1: return nid, pp
    # сбитый номер в книге — только если цепочка до этого не рвалась
    if n["parent"] == cur0 and n["ply"] % 2 == (want + 1) % 2 and not fail0: return nid, pp
    del self.t.nodes[n0:]; del self.t.roots[r0:]
    self.cur, self.main, self.scope, self.stack = st0[0], st0[1], st0[2], st0[3]
    self.fail = True
    return None, want
P.Linker.play = play

def renumber(L, tok, num, dots, bold):
    """Диаграмма, после которой текст шёл без номеров ходов, получила 1-й ход.
       Если номерной ход ложится на такую диаграмму (у неё ещё нет ходов, та же
       очередь хода), она получает номер из текста: «Вернёмся к позиции на
       диаграмме 103 … 25.Nh5-f6+»."""
    black = bool(dots) and dots != "."
    for r in sorted((x for x in L.scope if x < 0), reverse=False):      # свежие корни первыми
        if any(n["parent"] == r for n in L.t.nodes): continue
        f = L.t.roots[-r - 1].split(" ")
        if f[5] != "1" or (f[1] == "b") != black: continue
        b = chess.Board(" ".join(f))
        mv = match_move(b, tok)
        if not mv: continue
        f[5] = str(int(num)); L.t.roots[-r - 1] = " ".join(f)
        b = chess.Board(L.t.roots[-r - 1])
        nid = L.t.child(r, mv, b, bold)
        if nid not in L.scope: L.scope.append(nid)
        L.cur = nid
        if bold and not L.stack: L.main = nid
        return nid, L.t.ply(nid)
    return None, None

TAG = re.compile(r"\[\[(CHAPTER|SEC|H|DIAG|Q|CONT)\s*([^\]]*)\]\]\s*(.*)$")
# порядок сканов: страница 7 (печатная 4) в DjVu стоит после 5–6
ORDER = {7: 4.5}

def lead_bold(line):
    """жирным — начальная цепочка ходов абзаца, до первого слова или скобки"""
    m = re.match(r"(?:\s*(?:\d{1,3}\.(?:\.\.)?)?\s*(?:[KQRBN]?[a-h]?[1-8]?[-:x]?[a-h][1-8](?:=?[QRBN])?|0-0-0|0-0|[a-h][a-h])[+#]*[!?]*\s*)+", line)
    if not m: return line
    k = m.end()
    while k > 0 and line[k - 1] in " ": k -= 1
    return "**" + line[:k] + "**" + line[k:]

def load():
    boards = json.load(open(f"{W}/boards.json"))
    fens = {(r["p"], r["k"]): r["fen"] for r in json.load(open(f"{W}/fens.json"))}
    fix = json.load(open(os.path.join(HERE, "fix_fens.json")))
    pages = sorted((int(f[1:4]) for f in os.listdir(f"{W}/txt") if re.fullmatch(r"p\d{3}\.txt", f)),
                   key=lambda p: ORDER.get(p, p))
    items, warn = [], []
    for p in pages:
        txt = open(f"{W}/txt/p{p:03d}.txt", encoding="utf-8").read()
        txt = txt.translate(str.maketrans("♔♕♖♗♘♚♛♜♝♞–—−", "KQRBNKQRBN---"))
        txt = re.sub(r"(\d)\.\s+(?=[KQRBNa-h0O])", r"\1.", txt)          # «62. f5» -> «62.f5»
        txt = re.sub(r"(\d)\s*\.\.\.\s+(?=[KQRBNa-h0O])", r"\1...", txt)
        # абзац, начатый номерным ходом, — продолжение партии (главная линия),
        # даже если агент не отметил жирное: «18.e5! Bg7 19.f4 f6 …»
        txt = re.sub(r"(?m)^(\d{1,3}\.(?:\.\.)?[KQRBNa-h0O][^\n]*)$",
                     lambda m: m.group(1) if "**" in m.group(1) else lead_bold(m.group(1)), txt)
        nb = len(boards.get(str(p), []))
        k = 0; first = True
        for para in re.split(r"\n\s*\n", txt.strip()):
            buf = []
            def flush():
                if buf: items.append(("p", " ".join(buf), p)); buf.clear()
            for l in [x.strip() for x in para.split("\n") if x.strip()]:
                m = TAG.match(l)
                if not m:
                    buf.append(l); first = False; continue
                flush()
                tag, arg, rest = m.groups()
                if tag == "CONT":
                    if first: items.append(("cont", None, p))
                elif tag == "DIAG":
                    fen = fix.get(f"{p}/{k}") or fens.get((p, k))
                    items.append(("diag", {"n": arg.strip() or None, "turn": None, "small": False,
                                           "fen": fen, "src": f"{p}/{k}"}, p))
                    k += 1
                elif tag == "CHAPTER":
                    items.append(("chapter", (arg.strip(), rest.strip()), p))
                elif tag == "SEC":
                    items.append(("sec", (arg.strip(), rest.strip()), p))
                elif tag == "Q":
                    items.append(("cap", (arg + " " + rest).strip(), p))
                else:
                    items.append(("h", (arg + " " + rest).strip(), p))
                first = False
            flush()
        if k != nb: warn.append(f"стр. {p}: [[DIAG]] {k}, досок {nb}")
    # склейка абзацев через страницу
    out = []
    for it in items:
        if it[0] == "p" and out and out[-1][0] == "cont":
            out.pop()
            j = len(out) - 1
            while j >= 0 and out[j][0] not in ("p", "chapter", "sec", "h"): j -= 1
            if j >= 0 and out[j][0] == "p" and not out[j][1].startswith("**"):
                prev = out[j][1]
                out[j] = ("p", prev[:-1] + it[1] if re.search(r"[а-яё]-$", prev) else prev + " " + it[1], out[j][2])
                continue
        out.append(it)
    return [x for x in out if x[0] != "cont"], warn

def build(items):
    chapters = [{"n": 0, "title": "Предисловие", "blocks": []}]
    for kind, pl, page in items:
        if kind == "chapter":
            chapters.append({"n": int(pl[0]), "title": pl[1], "blocks": []}); continue
        chapters[-1]["blocks"].append({"kind": kind, "pl": pl, "page": page})
    return chapters

def render(blocks, L):
    """dvor.render, но разбор «№N» начинает поиск позиций заново."""
    out, run = [], []
    def go():
        if run: out.extend(P.render(run, L)); run.clear()
    for b in blocks:
        if b["kind"] == "sec":
            go()
            L.scope = []; L.cur = None; L.main = None; L.stack = []
            out.append({"t": "s", "n": b["pl"][0], "x": b["pl"][1]}); continue
        run.append(b)
    go()
    return out

def LINE(tok):
    m = re.fullmatch(r"\s*([a-h])([1-8])-([a-h])([1-8])\s*", tok)
    if not m: return False
    df, dr = abs(ord(m[1]) - ord(m[3])), abs(int(m[2]) - int(m[4]))
    return df > 1 or dr > 2 or dr == 0 or (df == 1 and dr != 1)

def main():
    items, warn = load()
    chapters = build(items)
    res, allbad, tot, first_bad = [], [], 0, []
    for ch in chapters:
        t = P.Tree(); L = P.Linker(t)
        blocks = render(ch["blocks"], L)
        secs = [b for b in blocks if b["t"] == "s"]
        diags = [b for b in blocks if b["t"] == "d" and "n" in b]
        linked = sum(1 for b in blocks for s in (b.get("s") or []) if isinstance(s, dict))
        tot += linked
        L.bad = [x for x in L.bad if not LINE(x)]
        allbad += [f"гл.{ch['n']}: {x}" for x in L.bad]
        res.append({"n": ch["n"], "title": ch["title"], "intro": blocks, "roots": t.roots,
                    "secs": len(secs), "diags": len(diags),
                    "nodes": [[x["parent"], x["uci"], x["san"], 1 if x["main"] else 0] + ([x["base"]] if x.get("threat") else [])
                              for x in t.nodes]})
        print(f"глава {ch['n']}: {ch['title']} — разборов {len(secs)}, диаграмм {len(diags)}, "
              f"ходов связано {linked}, не связано {len(L.bad)}")
    book = {"id": "yak", "title": "Шахматы. План в миттельшпиле", "author": "Николай Яковлев", "chapters": res}
    js = "/* «Миттельшпиль»: Н. Яковлев «Шахматы. План в миттельшпиле», разобрано из скана (tools/yak). Генерируется 06_parse.py */\n"
    js += "window.YAK = " + json.dumps([book], ensure_ascii=False, separators=(",", ":")) + ";\n"
    open(os.path.join(HERE, "../../yak.js"), "w", encoding="utf-8").write(js)
    open(f"{W}/unlinked.txt", "w").write("\n".join(allbad))
    print("итого связано", tot, "не связано", len(allbad), f"({100 * len(allbad) / max(1, tot + len(allbad)):.1f}%)")
    for w in warn: print("!", w)
    if P.REPAIRS: print("починено корней:", len(P.REPAIRS))

if __name__ == "__main__":
    main()
