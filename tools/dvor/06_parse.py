"""Расшифрованный текст + FEN диаграмм -> книга для сайта (work/dvor.json).

Книга делится на части (у Дворецкого их четыре: одна в томе 1, три в
томе 2). В каждой части: вступление (читается как книга), упражнения
(диаграмма + шапка + подпись) и ответы.

Главное здесь — привязка ходов из текста к позициям. Каждый пример —
дерево: корень = диаграмма, узел = позиция после хода. Ход из текста
вешается туда, где он легален, в таком порядке предпочтения:
  1) продолжение текущего узла (ход без номера или номер «следующий»);
  2) узел нужной глубины на пути от текущего к корню (альтернатива);
  3) любой другой узел нужной глубины, от свежих к старым.
Глубина берётся из номера хода: «23...» — после 23-го хода белых.
Скобки: «(» запоминает текущий узел, «;» и «)» к нему возвращают — так
«(66...B:f4 67.Bg8+; 66...Kc5 …) 67.Rc4+!» вешает 67.Rc4+ куда надо.
Диаграмма посреди текста ищется среди уже известных позиций примера и
становится текущим узлом; не нашлась — это новый корень.
Ходы словами («выпад ферзем на a4», «размен на d5») разрешаются в
текущей позиции, если ход такого типа на это поле ровно один.
"""
import json, re, os, sys
import chess

W = "work"
FENS = {(r["v"], r["p"], r["k"]): r["fen"] for r in json.load(open(f"{W}/fens.json"))}
BOARDS = {v: {int(p): [k for k, b in enumerate(bs) if b[2] >= 700]
              for p, bs in json.load(open(f"{W}/v{v}/boards.json")).items()} for v in (1, 2)}
FIX = json.load(open("fix_fens.json")) if os.path.exists("fix_fens.json") else {}

# ---------- 1. страницы -> поток элементов ----------
def load_volume(v):
    pages = sorted(int(f[1:4]) for f in os.listdir(f"{W}/v{v}/txt") if f.endswith(".txt"))
    items = []                 # (kind, payload)
    for p in pages:
        txt = open(f"{W}/v{v}/txt/p{p:03d}.txt", encoding="utf-8").read()
        k = 0
        paras = re.split(r"\n\s*\n", txt.strip())
        first = True
        for para in paras:
            lines = [l.strip() for l in para.split("\n") if l.strip()]
            buf = []
            def flush():
                if buf:
                    items.append(("p", " ".join(buf), p))
                    buf.clear()
            for l in lines:
                if l == "[[CONT]]":
                    if first: items.append(("cont", None, p))
                    continue
                m = re.match(r"\[\[(H|GAME|CAP|PART|DIAG)\s*([^\]]*)\]\]\s*(.*)$", l)
                if m:
                    flush()
                    tag, arg, rest = m.groups()
                    if tag == "DIAG":
                        num = re.search(r"\d+-\d+", arg)
                        turn = re.search(r"turn=([wb])", arg)
                        ks = BOARDS[v].get(p, [])
                        bk = ks[k] if k < len(ks) else -1
                        fen = FIX.get(f"{v}/{p}/{bk}") or FENS.get((v, p, bk))
                        items.append(("diag", {"n": num.group(0) if num else None,
                                               "turn": turn.group(1) if turn else None,
                                               "small": "small" in arg, "fen": fen,
                                               "src": f"{v}/{p}/{bk}"}, p))
                        k += 1
                    elif tag == "GAME":
                        items.append(("game", (arg + " " + rest).strip(), p))
                    else:
                        items.append((tag.lower(), (arg + " " + rest).strip(), p))
                else:
                    buf.append(l)
                first = False
            flush()
            first = False
    # склейка абзацев через страницу: [[CONT]] и перенос «по-»
    out = []
    for it in items:
        if it[0] == "cont":
            out.append(it); continue
        if it[0] == "p" and out and out[-1][0] == "cont":
            out.pop()
            j = len(out) - 1
            while j >= 0 and out[j][0] != "p": j -= 1
            # абзац продолжается через диаграммы/подписи — приклеиваем к последнему абзацу
            if j >= 0:
                prev = out[j][1]
                joined = prev[:-1] + it[1] if re.search(r"[а-яё]-$", prev) else prev + " " + it[1]
                out[j] = ("p", joined, out[j][2])
                continue
        out.append(it)
    return [x for x in out if x[0] != "cont"]

# ---------- 2. шахматная часть ----------
PIECE = {"K": chess.KING, "Q": chess.QUEEN, "R": chess.ROOK, "B": chess.BISHOP, "N": chess.KNIGHT}
MOVE_RX = re.compile(r"""
  (?P<num>\d{1,3})?\s*(?P<dots>\.\.\.|…|\.\s?\.\.|\.)?\s*
  (?P<mv>
     0-0-0|0-0|O-O-O|O-O|
     [KQRBN][a-h]?[1-8]?[:x]?[a-h][1-8](?:=?[QRBN])?|
     [a-h][1-8]-[a-h][1-8]|
     [a-h][:x][a-h][1-8](?:=?[QRBN])?|
     [a-h][1-8](?:=?[QRBN])?|
     [a-h][a-h](?:[QRBN])?
  )
  (?P<suf>[+#]*[!?]*)
""", re.X)

def castle_fen(placement):
    """Рокировки по стоянию короля и ладей — для корней примеров."""
    b = chess.Board(placement + " w - - 0 1")
    c = ""
    if b.piece_at(chess.E1) == chess.Piece(chess.KING, True):
        if b.piece_at(chess.H1) == chess.Piece(chess.ROOK, True): c += "K"
        if b.piece_at(chess.A1) == chess.Piece(chess.ROOK, True): c += "Q"
    if b.piece_at(chess.E8) == chess.Piece(chess.KING, False):
        if b.piece_at(chess.H8) == chess.Piece(chess.ROOK, False): c += "k"
        if b.piece_at(chess.A8) == chess.Piece(chess.ROOK, False): c += "q"
    return c or "-"

def match_move(board, tok):
    """Книжная запись -> ход python-chess (или None). Взятие без двоеточия
       и двоеточие без взятия прощаем; короткое пешечное «hg» — единственное
       взятие с вертикали на вертикаль."""
    t = tok.replace("O", "0").replace("x", ":")
    legal = list(board.legal_moves)
    if t in ("0-0", "0-0-0"):
        want = "O-O" if t == "0-0" else "O-O-O"
        c = [m for m in legal if board.is_castling(m) and board.san(m).startswith(want) and
             (len(board.san(m).rstrip("+#")) == len(want))]
        return c[0] if len(c) == 1 else None
    m = re.fullmatch(r"([a-h][1-8])-([a-h][1-8])", t)
    if m:
        a, b_ = chess.parse_square(m.group(1)), chess.parse_square(m.group(2))
        c = [x for x in legal if x.from_square == a and x.to_square == b_]
        return c[0] if c else None
    m = re.fullmatch(r"([a-h])([a-h])([QRBN]?)", t)
    if m:
        f1, f2 = "abcdefgh".index(m.group(1)), "abcdefgh".index(m.group(2))
        if abs(f1 - f2) != 1: return None
        pr = PIECE.get(m.group(3)) if m.group(3) else None
        c = [x for x in legal if board.piece_type_at(x.from_square) == chess.PAWN and board.is_capture(x)
             and chess.square_file(x.from_square) == f1 and chess.square_file(x.to_square) == f2
             and (x.promotion in (None, pr or chess.QUEEN))]
        return c[0] if len(c) == 1 else None
    m = re.fullmatch(r"([KQRBN])?([a-h])?([1-8])?:?([a-h][1-8])=?([QRBN])?", t)
    if not m: return None
    pc, ff, fr, to, pr = m.groups()
    pt = PIECE[pc] if pc else chess.PAWN
    to = chess.parse_square(to)
    c = []
    for x in legal:
        if x.to_square != to or board.piece_type_at(x.from_square) != pt: continue
        if ff and chess.square_file(x.from_square) != "abcdefgh".index(ff): continue
        if fr and chess.square_rank(x.from_square) != int(fr) - 1: continue
        if x.promotion and x.promotion != (PIECE[pr] if pr else chess.QUEEN): continue
        if pt == chess.PAWN and not pc and not ff and board.is_capture(x) and len(t) <= 3 and ":" not in t:
            # «e5» — не взятие; пешка, бьющая на поле, пишется «d:e5»
            continue
        c.append(x)
    return c[0] if len(c) == 1 else None

WORD_PIECE = [
    (re.compile(r"\b(корол[ьяюеём]\w*)", re.I), chess.KING),
    (re.compile(r"\b(ферз[ьяюеём]\w*)", re.I), chess.QUEEN),
    (re.compile(r"\b(ладь?[еёиюя]\w*|ладья)", re.I), chess.ROOK),
    (re.compile(r"\b(слон\w*)", re.I), chess.BISHOP),
    (re.compile(r"\b(кон[ьяюеём]\w*|коне\w*)", re.I), chess.KNIGHT),
    (re.compile(r"\b(пешк\w*|пешечн\w*)", re.I), chess.PAWN),
]

class Tree:
    def __init__(self):
        self.roots = []        # [fen]
        self.nodes = []        # dict(parent, root, uci, san, ply, fen, main)
    def add_root(self, fen):
        self.roots.append(fen)
        return -len(self.roots)          # корень k -> id -(k+1)
    def fen(self, nid):
        return self.roots[-nid - 1] if nid < 0 else self.nodes[nid]["fen"]
    def ply(self, nid):
        if nid < 0:
            b = chess.Board(self.fen(nid))
            return (b.fullmove_number - 1) * 2 + (0 if b.turn else 1)
        return self.nodes[nid]["ply"]
    def root_of(self, nid):
        return nid if nid < 0 else self.nodes[nid]["root"]
    def parent(self, nid):
        return None if nid < 0 else self.nodes[nid]["parent"]
    def child(self, nid, mv, board, main):
        uci = mv.uci()
        for i, n in enumerate(self.nodes):
            if n["parent"] == nid and n["uci"] == uci:
                if main: n["main"] = True
                return i
        san = board.san(mv)
        b2 = board.copy(); b2.push(mv)
        self.nodes.append({"parent": nid, "root": self.root_of(nid), "uci": uci, "san": san,
                           "ply": self.ply(nid) + 1, "fen": b2.fen(), "main": main})
        return len(self.nodes) - 1

def tok_ply(num, dots, prev):
    """абсолютный полуход ХОДА (0 = 1-й ход белых)"""
    if num:
        n = int(num)
        black = bool(dots) and dots != "."
        return (n - 1) * 2 + (1 if black else 0)
    return None if prev is None else prev + 1

class Linker:
    def __init__(self, tree):
        self.t = tree
        self.cur = None          # текущий узел
        self.scope = []          # узлы, доступные этому примеру (для поиска по глубине)
        self.stack = []
        self.bad = []
        self.main = None         # последний ход главной (жирной) линии
    def path(self, n, ply):
        out = []
        while n is not None:
            if self.t.ply(n) == ply: out.append(n)
            n = self.t.parent(n)
        return out
    def set_root(self, fen):
        r = self.t.add_root(fen)
        self.cur = r; self.main = r; self.scope.append(r); self.stack = []
        return r
    def candidates(self, want_parent_ply):
        seen = []
        n = self.cur
        # 1-2: путь от текущего к корню
        while n is not None:
            if self.t.ply(n) == want_parent_ply: seen.append(n)
            n = self.t.parent(n)
        # 3: остальные узлы примера нужной глубины, свежие первыми
        for nid in reversed(self.scope):
            if nid not in seen and self.t.ply(nid) == want_parent_ply: seen.append(nid)
        return seen
    def merge(self, nid):
        f = " ".join(self.t.fen(nid).split(" ")[:2])
        for r in self.scope:
            if r < 0 and r != self.t.root_of(nid) and " ".join(self.t.fen(r).split(" ")[:2]) == f:
                return r
        return nid
    def play(self, tok, num, dots, prev_ply, bold):
        ply = tok_ply(num, dots, prev_ply)
        if self.cur is None and not (ply == 0 and num): return None, prev_ply   # до первой диаграммы — только партия с 1-го хода
        tries = []
        if ply is not None: tries += self.candidates(ply)
        if bold and ply is not None and self.main is not None:
            # жирный ход — продолжение главной линии, а не варианта, упомянутого в тексте
            mp = self.path(self.main, ply)
            tries = mp + [x for x in tries if x not in mp]
        if not num and self.cur is not None:
            tries = [self.cur] + [x for x in tries if x != self.cur]
            # альтернатива последнему ходу: «1.Qg6? Nf8!» уже взято, а «Nf8 Qg7» без номеров
        for parent in tries:
            b = chess.Board(self.t.fen(parent))
            mv = match_move(b, tok)
            if mv:
                nid = self.t.child(parent, mv, b, bold)
                if nid not in self.scope: self.scope.append(nid)
                self.cur = self.merge(nid)
                if bold: self.main = self.cur
                return nid, self.t.ply(self.cur)
        # опечатки распознавания/книги: одна буква или цифра, фигура.
        # Выключено по умолчанию: на вычитанном тексте эта «починка» чаще цепляла ход
        # не к той позиции (10% ходов показывали на доске другой ход), чем чинила опечатку.
        if not getattr(self, "allow_fix", False): tries = []
        SUB = {"c": "e", "e": "c", "b": "h", "h": "b", "3": "8", "8": "3", "5": "6", "6": "5",
               "1": "7", "7": "1", "f": "t", "g": "q", "B": "R", "R": "B", "Q": "K", "K": "Q", "N": "B"}
        hits = []
        for parent in tries[:4]:
            b = chess.Board(self.t.fen(parent))
            for k, ch in enumerate(tok):
                if ch in SUB:
                    t2 = tok[:k] + SUB[ch] + tok[k + 1:]
                    mv = match_move(b, t2)
                    if mv: hits.append((parent, mv, b))
            if hits: break
        if len({(h[0], h[1].uci()) for h in hits}) == 1:
            parent, mv, b = hits[0]
            nid = self.t.child(parent, mv, b, bold)
            if nid not in self.scope: self.scope.append(nid)
            self.t.nodes[nid]["fixed"] = tok
            self.cur = self.merge(nid)
            return nid, self.t.ply(self.cur)
        # партия с самого начала («1.e4 c5 2.Nf3…») без диаграммы
        if ply == 0 and num:
            b = chess.Board()
            mv = match_move(b, tok)
            if mv:
                r = self.t.add_root(b.fen()); self.scope.append(r)
                nid = self.t.child(r, mv, b, bold); self.scope.append(nid)
                self.cur = nid; self.main = nid
                return nid, 0
        # опечатки в номерах книги: пробуем продолжить текущий
        if num and self.cur is not None:
            b = chess.Board(self.t.fen(self.cur))
            mv = match_move(b, tok)
            if mv:
                nid = self.t.child(self.cur, mv, b, bold)
                if nid not in self.scope: self.scope.append(nid)
                self.cur = nid
                return nid, self.t.ply(nid)
        # номер хода в книге сбит («нумерация как в книге»): пробуем позицию диаграммы
        if num and self.scope:
            r = min((x for x in self.scope if x < 0), default=None)   # последний корень
            if r is not None and r != self.cur:
                b = chess.Board(self.t.fen(r))
                mv = match_move(b, tok)
                if mv and (b.turn == chess.WHITE) == (not dots or dots == "."):
                    nid = self.t.child(r, mv, b, bold)
                    if nid not in self.scope: self.scope.append(nid)
                    self.cur = nid
                    if bold: self.main = nid
                    return nid, self.t.ply(nid)
        # угроза: «грозит 20.Rc7», «грозит матом Qxf7#» — ход той же стороны,
        # будто соперник пропустил ход (от последней настоящей позиции)
        base = self.cur
        if base is not None and base >= 0 and self.t.nodes[base].get("threat"): base = self.t.nodes[base]["base"]
        if base is not None and base >= 0 and (not self.stack or getattr(self, "lone", False)):
            b = chess.Board(self.t.fen(base))
            black = (bool(dots) and dots != ".") if num else b.turn
            if (num or getattr(self, "lone", False)) and b.turn == black and not b.is_check():
                b.turn = not b.turn; b.ep_square = None
                if b.is_valid():
                    if num: b.fullmove_number = int(num)
                    mv = match_move(b, tok)
                    if mv:
                        r = self.t.add_root(b.fen()); self.scope.append(r)
                        nid = self.t.child(r, mv, b, False); self.scope.append(nid)
                        self.t.nodes[nid]["threat"] = True
                        self.t.nodes[nid]["base"] = base
                        self.cur = nid
                        return nid, self.t.ply(nid)
        return None, ply
    def word_move(self, pt, sq, capture):
        """ход словами: единственный ход фигуры pt на поле sq в текущей позиции"""
        if self.cur is None: return None
        for parent in [self.cur] + ([self.t.parent(self.cur)] if self.t.parent(self.cur) is not None else []):
            b = chess.Board(self.t.fen(parent))
            to = chess.parse_square(sq)
            c = [m for m in b.legal_moves if m.to_square == to and (pt is None or b.piece_type_at(m.from_square) == pt)
                 and (not capture or b.is_capture(m)) and m.promotion in (None, chess.QUEEN)]
            if len(c) == 1:
                nid = self.t.child(parent, c[0], b, False)
                self.t.nodes[nid]["word"] = True
                return nid
        return None

SQ_WORD = re.compile(r"\b(?:на|в|с)\s+([a-h][1-8])\b")
CAPWORD = re.compile(r"(размен|взяти|бить|побить|забрать|снять|взять|бьет|берет)", re.I)

def link_paragraph(text, L):
    """Абзац -> список сегментов: строка или {"m": id, "s": текст, "b": жирный}."""
    segs = []
    pos = 0
    bold = False
    prev_ply = None
    # разбиваем по ** (жирное)
    parts = re.split(r"(\*\*)", text)
    buf = ""
    out = []
    for part in parts:
        if part == "**":
            bold = not bold; continue
        out.append((part, bold))
    for part, bold in out:
        i = 0
        last_end = None
        while i < len(part):
            ch = part[i]
            if ch == "(":
                L.stack.append((L.cur, prev_ply)); buf += ch; i += 1; continue
            if ch == ";" and L.stack:
                L.cur, prev_ply = L.stack[-1]; buf += ch; i += 1; continue
            if ch == ")" and L.stack:
                L.cur, prev_ply = L.stack.pop(); buf += ch; i += 1; continue
            m = MOVE_RX.match(part, i) if not ch.isspace() else None
            okstart = i == 0 or not re.match(r"[A-Za-zА-Яа-яЁё0-9]", part[i - 1])
            if m and okstart and m.group("mv") and m.end() > i:
                end = m.end()
                after = part[end:end + 1]
                if not re.match(r"[A-Za-zА-Яа-яЁё0-9]", after or " "):
                    mv = m.group("mv"); num = m.group("num"); dots = m.group("dots")
                    if num and not dots: num = None     # «в 1997 году» — не ход
                    shortpawn = re.fullmatch(r"[a-h][a-h][QRBN]?", mv)
                    if shortpawn and not num and prev_ply is None:
                        pass                               # «ab» вне варианта — не трогаем
                    else:
                        # ход сам по себе в прозе (перед ним слова, а не ходы) — может быть угрозой
                        L.lone = last_end is None or bool(re.search(r"[А-Яа-яЁё]", part[last_end:i]))
                        last_end = end
                        if L.lone and not num and re.fullmatch(r"[a-h][1-8]", mv):
                            buf += part[i:end]; i = end; continue     # «пункт f7», «на d5» — поле, не ход
                        nid, prev_ply2 = L.play(mv, num, dots, prev_ply, bold)
                        if nid is not None:
                            if buf: segs.append(buf); buf = ""
                            segs.append({"m": nid, "s": part[i:end].strip(), "b": bold})
                            prev_ply = prev_ply2
                            i = end; continue
                        elif re.fullmatch(r"[a-h][1-8]", mv) and not num:
                            pass                           # просто поле
                        else:
                            L.bad.append(part[i:end]); prev_ply = prev_ply2
                        buf += part[i:end]; i = end; continue
            # ход словами: «ферзем на a4», «размен на d5»
            if ch.isalpha() and (i == 0 or not part[i - 1].isalpha()):
                handled = False
                for rx, pt in WORD_PIECE + [(CAPWORD, None)]:
                    wm = rx.match(part, i)
                    if not wm: continue
                    rest = part[wm.end():wm.end() + 25]
                    sm = SQ_WORD.search(rest)
                    if sm and not re.search(r"[.;!?]", rest[:sm.start()]):
                        cap = pt is None
                        nid = L.word_move(pt, sm.group(1), cap)
                        if nid is not None:
                            j = wm.end() + sm.end()
                            if buf: segs.append(buf); buf = ""
                            segs.append({"m": nid, "s": part[i:j], "w": 1})
                            i = j; handled = True
                    break
                if handled: continue
            buf += ch; i += 1
    if buf: segs.append(buf)
    # склеиваем соседние строки
    res = []
    for s in segs:
        if isinstance(s, str) and res and isinstance(res[-1], str): res[-1] += s
        else: res.append(s)
    return res

def root_fen(placement, turn, first_text):
    """Корень: расстановка + очередь хода + номер. Берём первый ход текста с
       номером, легальный в этой позиции («1.e4 …» партии с начала
       пропускается сам — он здесь невозможен). Не нашли — квадратик."""
    cast = castle_fen(placement)
    ms = list(MOVE_RX.finditer(first_text or ""))
    if turn:        # сначала ходы той стороны, что указана квадратиком
        ms = [m for m in ms if m.group("dots") and (m.group("dots") == ".") == (turn == "w")] + ms
    for m in ms:
        num, dots, mv = m.group("num"), m.group("dots"), m.group("mv")
        if not num or not dots: continue
        side = "w" if dots == "." else "b"
        fen = f"{placement} {side} {cast} - 0 {int(num)}"
        try: b = chess.Board(fen)
        except ValueError: continue
        if b.is_valid() and match_move(b, mv): return fen
    side = turn or "w"
    fen = f"{placement} {side} {cast} - 0 1"
    if not chess.Board(fen).is_valid():
        other = "w" if side == "b" else "b"
        fen2 = f"{placement} {other} {cast} - 0 1"
        if chess.Board(fen2).is_valid(): fen = fen2
    return fen

def best_root(placement, turn, text, repair=True):
    """Очередь хода и номер корня выбираем проверкой: пробуем все варианты,
       которые дают номерные ходы текста (и квадратик), и берём тот, при котором
       к позиции привязывается больше ходов. При равенстве — как root_fen."""
    cast = castle_fen(placement)
    cands = [root_fen(placement, turn, text)]
    for m in MOVE_RX.finditer(text or ""):
        num, dots = m.group("num"), m.group("dots")
        if not num or not dots: continue
        f = f"{placement} {'w' if dots == '.' else 'b'} {cast} - 0 {int(num)}"
        if f not in cands: cands.append(f)
        if len(cands) >= 8: break
    for side in "wb":
        f = f"{placement} {side} {cast} - 0 1"
        if f not in cands: cands.append(f)
    best, score = cands[0], -1
    for k, f in enumerate(cands):
        try:
            if not chess.Board(f).is_valid(): continue
        except ValueError: continue
        t = Tree(); L = Linker(t); L.set_root(f)
        for para in re.split(r"\n+", text or "")[:6]:
            link_paragraph(para, L)
        # ходы, легшие на эту позицию (не партия с начала)
        n = sum(1 for x in t.nodes if x["root"] == -1)
        sc = n * 2 + (1 if k == 0 else 0)
        if sc > score: best, score = f, sc
    if repair:
        fx = repair_root(placement, turn, text, best, score // 2)
        if fx: return fx
    return best

def links_from(fen, text):
    t = Tree(); L = Linker(t); L.set_root(fen)
    for para in re.split(r"\n+", text or "")[:6]:
        link_paragraph(para, L)
    return sum(1 for x in t.nodes if x["root"] == -1)

REPAIRS = []
def repair_root(placement, turn, text, best, have):
    """Распознавание картинки иногда ошибается в одной клетке (пешка вместо
       слона, чёрный ферзь вместо белого). Если первый номерной ход текста
       не ложится на позицию, пробуем заменить одну клетку и берём замену,
       при которой ложится заметно больше ходов текста."""
    ms = [m for m in MOVE_RX.finditer(text or "") if m.group("mv")]
    first = next((k for k, m in enumerate(ms) if m.group("num") and m.group("dots")), None)
    if first is None: return None
    m0 = ms[first]
    try:
        if match_move(chess.Board(best), m0.group("mv")): return None
    except ValueError: pass
    seq = [m.group("mv") for m in ms[first:first + 4]]
    side = "w" if m0.group("dots") == "." else "b"
    base = chess.Board(placement + " w - - 0 1")
    pieces = [None] + [chess.Piece(pt, c) for pt in range(1, 7) for c in (True, False)]
    good = []
    for sq in chess.SQUARES:
        old = base.piece_at(sq)
        for pc in pieces:
            if pc == old or (pc and pc.piece_type == chess.KING) or (old and old.piece_type == chess.KING): continue
            if pc is None and old is None: continue
            b = base.copy(); b.set_piece_at(sq, pc) if pc else b.remove_piece_at(sq)
            pl = b.board_fen()
            f = f"{pl} {side} {castle_fen(pl)} - 0 {int(m0.group('num'))}"
            try: bb = chess.Board(f)
            except ValueError: continue
            if not bb.is_valid(): continue
            k = 0
            for tok in seq:
                mv = match_move(bb, tok)
                if not mv: break
                bb.push(mv); k += 1
            if k: good.append((-k, f))
    good.sort()
    if not good: return None
    top = [f for kk, f in good if kk == good[0][0]][:12]
    sc = sorted(((links_from(f, text), f) for f in top), reverse=True)
    if sc and sc[0][0] >= have + 3 and (len(sc) == 1 or sc[0][0] > sc[1][0]):
        REPAIRS.append((placement, sc[0][1].split(" ")[0]))
        return sc[0][1]
    return None

# ---------- 3. сборка частей ----------
def build(v, items):
    parts = []
    part = None
    mode = None
    def new_part(title):
        nonlocal part
        part = {"title": title, "intro": [], "ex": {}, "order": []}
        parts.append(part)
    pending_game = None
    ans = None                 # текущий ответ (блоки)
    for idx, (kind, pl, page) in enumerate(items):
        if kind == "part": continue
        if kind == "h":
            t = pl.strip()
            tl = t.lower()
            if tl in ("упражнения",): mode = "ex"; continue
            if tl in ("ответы",): mode = "ans"; continue
            if tl in ("предисловие", "условные обозначения"):
                if not parts: new_part("Предисловие")
                mode = "pre"; parts[0].setdefault("pre", []).append({"t": "h", "x": t})
                continue
            if parts and parts[-1]["title"] == "Предисловие" and not parts[-1]["ex"]:
                pre = parts.pop()
                new_part(t); part["pre"] = pre.get("pre", [])
            else:
                new_part(t)
            mode = "intro"
            continue
        if part is None: new_part("Предисловие"); mode = "pre"
        if mode == "pre":
            if kind == "p": part.setdefault("pre", []).append({"t": "p", "x": pl})
            continue
        if mode == "ex":
            if kind == "game": pending_game = pl
            elif kind == "diag" and pl["n"]:
                part["ex"].setdefault(pl["n"], {})
                e = part["ex"][pl["n"]]
                e.update({"n": pl["n"], "game": pending_game, "diag": pl})
                part["order"].append(pl["n"]); pending_game = None
            elif kind == "cap" and part["order"]:
                part["ex"][part["order"][-1]]["cap"] = pl
            continue
        # вступление и ответы — поток блоков
        blk = {"kind": kind, "pl": pl, "page": page}
        if mode == "intro":
            part["intro"].append(blk)
        elif mode == "ans":
            if kind == "diag" and pl["n"] and pl["n"] in part["ex"]:
                ans = part["ex"][pl["n"]].setdefault("ans", [])
                part["ex"][pl["n"]]["adiag"] = pl
                continue
            if kind == "game":
                # шапка перед диаграммой ответа — её уже знаем из упражнений
                nxt = next((it for it in items[idx + 1: idx + 3] if it[0] == "diag"), None)
                if nxt and nxt[1]["n"]: continue
            if ans is not None: ans.append(blk)
    return parts

def diff_placement(a, b):
    A, B = chess.Board(a + " w - - 0 1"), chess.Board(b + " w - - 0 1")
    return sum(A.piece_at(q) != B.piece_at(q) for q in chess.SQUARES)

def first_text(blocks):
    return " ".join(b["pl"] for b in blocks if b["kind"] in ("p", "cap"))

def render(blocks, L, start_fen=None, start_turn=None):
    """Поток блоков -> блоки для сайта, с привязкой ходов."""
    out = []
    pending_game = None
    for i, b in enumerate(blocks):
        k, pl = b["kind"], b["pl"]
        if k == "game":
            pending_game = pl; out.append({"t": "g", "x": pl}); continue
        if k == "cap":
            out.append({"t": "c", "s": link_paragraph(pl, L)}); continue
        if k == "h":
            out.append({"t": "h", "x": pl}); continue
        if k == "diag":
            placement = pl["fen"]
            if not placement:
                out.append({"t": "d", "miss": pl["src"]}); continue
            # диаграмма посреди примера: ищем среди известных позиций
            # диаграмма посреди примера/партии: ищем среди известных позиций.
            # Позиция, до которой дошли ходы текста, надёжнее распознанной картинки:
            # берём её и при отличии в 1–3 поля (фигура не того цвета, потерянный слон)
            found = None
            best = None
            for nid in reversed(L.scope):
                d = diff_placement(L.t.fen(nid).split(" ")[0], placement)
                if d == 0: found = nid; break
                if d <= 3 and nid >= 0 and (best is None or d < best[0]): best = (d, nid)
            if found is None and best: found = best[1]
            if found is None:
                nxt = []
                for x in blocks[i + 1:]:
                    if x["kind"] in ("diag", "game"): break
                    if x["kind"] in ("p", "cap"): nxt.append(x["pl"])
                nxt = "\n".join(nxt)
                if pending_game: L.scope = []
                fen = best_root(placement, pl["turn"], nxt)
                found = L.set_root(fen)
            else:
                L.cur = found; L.main = found; L.stack = []
            pending_game = None
            out.append({"t": "d", "n": found, "small": pl["small"]})
            continue
        if k == "p":
            out.append({"t": "p", "s": link_paragraph(pl, L)})
    return out

def main():
    book = []
    stats = {"moves": 0, "bad": 0}
    allbad = []
    for v in (1, 2):
        items = load_volume(v)
        parts = build(v, items)
        for part in parts:
            if part["title"] == "Предисловие": continue
            tree = Tree(); L = Linker(tree)
            intro = render(part["intro"], L)
            exs = []
            for n in part["order"]:
                e = part["ex"][n]
                d = e["diag"]; ad = e.get("adiag") or d
                placement = d["fen"] or ad["fen"]
                if d["fen"] and ad["fen"] and d["fen"] != ad["fen"]:
                    import copy
                    score = {}
                    for cand in (d["fen"], ad["fen"]):
                        t2 = copy.deepcopy(tree); L2 = Linker(t2)
                        cap = [{"kind": "cap", "pl": e["cap"], "page": 0}] if e.get("cap") else []
                        L2.set_root(root_fen(cand, d["turn"] or ad["turn"], first_text(cap + e.get("ans", []))))
                        render(cap + e.get("ans", []), L2)
                        score[cand] = len(t2.nodes) - len(tree.nodes) - 3 * len(L2.bad)
                    placement = max(score, key=score.get)
                    allbad.append(f"{n}: диаграммы упражнения и ответа расходятся, взята {'ответа' if placement == ad['fen'] else 'упражнения'} {score}")
                L.scope = []
                ans = e.get("ans", [])
                if e.get("cap"): ans = [{"kind": "cap", "pl": e["cap"], "page": 0}] + ans
                root = None
                if placement:
                    root = L.set_root(root_fen(placement, d["turn"] or ad["turn"], first_text(ans)))
                blocks = render(ans, L) if root is not None else []
                # партия с начала дошла до позиции диаграммы — упражнение стартует оттуда
                if root is not None and not any(x["parent"] == root for x in tree.nodes):
                    pl0 = tree.fen(root).split(" ")[0]
                    hit = [i for i in L.scope if i >= 0 and tree.fen(i).split(" ")[0] == pl0]
                    if hit: root = hit[0]
                # главная линия — жирные ходы от корня
                main = []
                cur = root
                while cur is not None:
                    kids = [i for i, x in enumerate(tree.nodes) if x["parent"] == cur and x["main"]]
                    if not kids: break
                    cur = kids[0]; main.append(cur)
                exs.append({"n": n, "g": e.get("game"), "cap": e.get("cap"), "root": root,
                            "turn": d["turn"], "main": main, "a": blocks, "src": d["src"]})
            stats["moves"] += len(tree.nodes); stats["bad"] += len(L.bad)
            allbad += [f"{part['title']}: {x}" for x in L.bad]
            book.append({"v": v, "title": part["title"], "pre": part.get("pre", []),
                         "intro": intro, "ex": exs,
                         "roots": tree.roots,
                         "nodes": [[x["parent"], x["uci"], x["san"], 1 if x["main"] else 0] + ([x["base"]] if x.get("threat") else []) for x in tree.nodes]})
    json.dump(book, open(f"{W}/dvor.json", "w"), ensure_ascii=False)
    # для сайта: тома -> части; ходы без FEN (FEN считает страница)
    vols = []
    for v in (1, 2):
        ps = [p for p in book if p["v"] == v]
        pre = next((p["pre"] for p in ps if p["pre"]), [])
        vols.append({"id": f"dvor{v}", "title": f"Том {v}", "pre": pre,
                     "parts": [{k: p[k] for k in ("title", "intro", "ex", "roots", "nodes")} for p in ps]})
    js = "/* «Профилактика»: две книги, разобранные из сканов (tools/dvor). Генерируется 06_parse.py */\n"
    js += "window.DVOR = " + json.dumps(vols, ensure_ascii=False, separators=(",", ":")) + ";\n"
    open("../../dvor.js", "w", encoding="utf-8").write(js)
    open(f"{W}/unlinked.txt", "w").write("\n".join(allbad))
    print(stats, [(p["title"], len(p["ex"]), len(p["nodes"])) for p in book])

if __name__ == "__main__" and "--no-main" not in sys.argv:
    main()
