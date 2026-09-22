import os
"""Порт tools/books/lib_line.js + pickMove/norm из parse_konotop.js на python-chess."""
import re, chess

SAN_CORE = (r'(?:O-O-O|O-O|[KQRBN][a-h]?[1-8]?x?[a-h][1-8]|[a-h]x[a-h][1-8](?:=?[QRBN])?'
            r'|[a-h][1-8](?:=?[QRBN])?|[a-h][a-h](?:=?[QRBN])?)[+#]?')
TRIG = re.compile(r'(Например|например|случае|Ход |Вместо|вместо|Если|если|Иначе|иначе|партии|льтернатив|роигрывает|лохо|слабее|хуже|шибочн|нельзя|аслуживает|озможно|нтересн|тоже хорош|также хорош|ыбор|годится|ругой|ругая|ругие|стоило|следовало|грозит|угроз|шибка|редпочт|роще|екомендует|критик|Не |ужасно|сомнит|неточн|спасал|спасает|не дает|ничего не|обречен|попытк|Попытк|пробовал)')
GAPOK = re.compile(r'^[\s!?+\-−=±∓⩲⩱÷©ƒ‚„,;:∞]*$')


def norm(t):
    t = re.sub(r'(\d+)\s*\.\s*\.\.\.\s*', r'\1...', t)
    t = re.sub(r'(\d+)\s+\.\.\.\s*', r'\1...', t)
    t = re.sub(r'(\d+)\.\.\.\s+', r'\1...', t)
    t = re.sub(r'(\d+)\.\s+(?=[KQRBNa-h])', r'\1.', t)
    t = re.sub(r'([KQRBN][a-h1-8]?)\s*:\s*([a-h][1-8])', r'\1x\2', t)
    t = re.sub(r'([a-h][1-8])\s*:\s*([a-h][1-8])', r'\1x\2', t)
    t = re.sub(r'\b([a-h])\s*:\s*([a-h][1-8])', r'\1x\2', t)
    return t.replace('0-0-0', 'O-O-O').replace('0-0', 'O-O')


def do_move(bd, san):
    san = re.sub(r'^([a-h][18])([QRBN])([+#]?)$', r'\1=\2\3', san)
    san = re.sub(r'^([a-h]x[a-h][18])([QRBN])([+#]?)$', r'\1=\2\3', san)
    try:
        mv = bd.parse_san(san)
    except ValueError:
        mv = None
    if mv is None:
        sh = re.match(r'^([a-h])([a-h])(?:=?([QRBN]))?[+#]?$', san)
        if not sh: return None
        cand = [m for m in bd.legal_moves
                if bd.piece_type_at(m.from_square) == chess.PAWN
                and chess.square_name(m.from_square)[0] == sh.group(1)
                and chess.square_name(m.to_square)[0] == sh.group(2)
                and bd.is_capture(m)
                and ((m.promotion == chess.Piece.from_symbol(sh.group(3)).piece_type) if sh.group(3) else not m.promotion)]
        if len(cand) != 1: return None
        mv = cand[0]
    s = bd.san(mv); bd.push(mv)
    return mv.uci(), s


def extract_line(fen, side, mv, text, start_at=0, max_ply=24):
    TOK = re.compile(r'([()])|(?:(\d+)\s*(\.\.\.|\.)\s*)?(' + SAN_CORE + r')([!?]{0,2})')
    bd = chess.Board(fen)
    depth = 0; exp = [mv, side]; sl = [None, None]
    prev_end = -1; prev_side = False; moves = []
    adv = lambda n, s: (n, 'b') if s == 'w' else (n + 1, 'w')
    pos = start_at
    while True:
        m = TOK.search(text, pos)
        if not m: break
        pos = m.end() if m.end() > m.start() else m.start() + 1
        if m.group(1):
            depth += 1 if m.group(1) == '(' else -1; depth = max(depth, 0); continue
        start, end = m.start(), m.end()
        before = text[start - 1] if start else ''; after = text[end] if end < len(text) else ''
        if before == '-' or after == '-' or before == '.' or re.match(r'[A-Za-z0-9]', before or ' '): continue
        if depth > 0: continue
        if len(moves) >= max_ply: break
        num = int(m.group(2)) if m.group(2) else None; dots = m.group(3); san = m.group(4)
        gap = '' if prev_end < 0 else text[prev_end:start]
        adjacent = prev_end >= 0 and bool(GAPOK.match(gap))
        tail = re.split(r'[.!?…»] ', gap)[-1]
        has_sent = bool(re.search(r'[.!?…»] ', gap))
        tside = None if num is None else ('b' if dots == '...' else 'w')

        def to_side(n, s):
            nonlocal prev_end, prev_side
            sl[0], sl[1] = adv(n, s); prev_end = end; prev_side = True

        def try_main():
            nonlocal prev_end, prev_side
            r = do_move(bd, san)
            if not r: return False
            moves.append(dict(uci=r[0], san=r[1], fen=bd.fen(), start=start, end=end, ann=m.group(5) or ''))
            exp[0], exp[1] = adv(exp[0], exp[1])
            prev_end = end; prev_side = False; sl[0] = sl[1] = None
            return True

        if num is not None:
            m_main = num == exp[0] and tside == exp[1]
            m_side = sl[0] is not None and num == sl[0] and tside == sl[1]
            if m_side and (adjacent or not has_sent): to_side(num, tside); continue
            if m_main and not (moves and TRIG.search(tail)):
                if try_main(): continue
            to_side(num, tside); continue
        if not adjacent: continue
        if prev_side:
            if sl[0] is not None: to_side(sl[0], sl[1])
            continue
        if not moves: continue
        try_main()
    return moves


BAD = re.compile(r'(Попытк|попытк|ничего не да|не спаса|обречен|неудач|нельзя|ошибочн|плохо|проигрыва|ведет к ничьей|ведёт к ничьей|половинчат|не годится|слабее|хуже|опроверга|наталкивается|в случае|В случае|Если|если|Не проходит|не проходит|напрашива|прямолинейн|жет показаться|ошибк)')
GOOD = re.compile(r'(правильн|решает|выигрывает|сильнейш|единственн|необходимо|следует играть|решение|нашли, как|могли сыграть|гораздо сильнее|значительно сильнее|намного сильнее)')
WIN = re.compile(r'(сдал|1-0|0-1|выигрыв|выигр|\+-|-\+|#|мат)')


def candidates(fen, side, text):
    rx = re.compile(r'\b1' + (r'\.(?!\.)' if side == 'w' else r'\.\.\.') + '(' + SAN_CORE + r')([!?]{0,2})')
    out = []
    for m in rx.finditer(text):
        pre = text[:m.start()]
        if pre.count('(') - pre.count(')') > 0: continue
        bd = chess.Board(fen)
        r = do_move(bd, m.group(1))
        if r: out.append(dict(san=r[1], ann=m.group(2) or '', at=m.start()))
    return out


def pick_move(fen, side, text):
    cands = candidates(fen, side, text)
    best = -1e9; pick = None; line = []
    for ci, c in enumerate(cands):
        l = extract_line(fen, side, 1, text, start_at=c['at'])
        if not l: continue
        sc = len(l) * 1.5 + ci * 2
        if '!!' in c['ann']: sc += 34
        elif '!' in c['ann']: sc += 26
        if '?' in c['ann']: sc -= 60
        if l[-1]['san'].endswith('#'): sc += 12
        seg = re.split(r'[.!?] ', text[max(0, c['at'] - 140):c['at']])[-1]
        if BAD.search(seg): sc -= 32
        if GOOD.search(seg): sc += 12
        if WIN.search(text[l[-1]['end']:l[-1]['end'] + 160]): sc += 12
        if sc > best: best, pick, line = sc, c, l
    return pick, line, cands
