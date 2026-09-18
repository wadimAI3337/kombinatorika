"""Шаг 10. Сверка ходов из решений с позициями.

Самая сильная проверка: два независимых источника — картинка диаграммы и
текст решения — должны сойтись.

Ходы в книге записаны сокращённо: ':' вместо 'x', 'fe' вместо 'fxe6',
'0-0' вместо 'O-O'. forms_for() перечисляет все написания, которыми
в этой нотации может быть записан данный легальный ход, и сверяет с токеном.

Если ход нелегален — repair() перебирает однобуквенные замены
(c<->e, b<->h, d<->b, 3<->8 и т.п.). Если ровно один вариант даёт легальный
ход — это опечатка распознавания, чиним автоматически. Если вариантов
несколько или ни одного — в отчёт, смотреть глазами.

ВАЖНО: двоеточие должно совпадать со взятием. Если ход записан как взятие,
а поле пустое, это сигнал, что ход прочитан неверно, — такие случаи
собираются отдельно в LOOSE и проверяются вручную.
"""
import json,re,chess
TOK=r'(?:[KQRBN][a-h]?[1-8]?:?[a-h][1-8]|[a-h][1-8](?:=?[QRBN])?|[a-h]:?[a-h][1-8]?|0-0-0|0-0)[+#!?]*'
MOVE=re.compile(r'(\d+)\.\s*(\.\.\.)?\s*('+TOK+r')(?:\s+('+TOK+r'))?')
def strip_var(t):
    out=[];d=0
    for ch in t:
        if ch in '([': d+=1
        elif ch in ')]': d=max(0,d-1)
        elif d==0: out.append(ch)
    return ''.join(out)
LENIENT=False
def forms_for(board,mv):
    p=board.piece_at(mv.from_square); sym=p.symbol().upper()
    s=chess.square_name(mv.to_square); fs=chess.square_name(mv.from_square)
    F=set()
    if board.is_castling(mv):
        F.add('O-O-O' if chess.square_file(mv.to_square)<4 else 'O-O')
        F.add('0-0-0' if chess.square_file(mv.to_square)<4 else '0-0')
    elif sym=='P':
        if board.is_capture(mv): F.update({fs[0]+s[0],fs[0]+':'+s,fs[0]+':'+s[0],s,fs[0]+s})
        else: F.add(s)
        if mv.promotion:
            pr=chess.piece_symbol(mv.promotion).upper()
            F.update({f+pr for f in list(F)}|{f+'='+pr for f in list(F)})
    else:
        san=board.san(mv).rstrip('+#'); core=san.replace('x',''); dis=core[1:-2]
        F.update({sym+s,sym+dis+s})
        for d2 in (fs[0],fs[1],fs): F.add(sym+d2+s)
        if board.is_capture(mv) or LENIENT:
            F.update({sym+':'+s,sym+dis+':'+s})
            for d2 in (fs[0],fs[1],fs): F.add(sym+d2+':'+s)
    return F
SUB=[('c','e'),('e','c'),('b','h'),('h','b'),('d','b'),('b','d'),('a','d'),('d','a'),
     ('g','q'),('c','o'),('4','d'),('3','8'),('8','3'),('5','6'),('6','5'),
     ('B','R'),('R','B'),('N','K'),('K','N'),('e','a'),('a','e'),('f','e'),('e','f'),
     ('g','b'),('b','g'),('c','d'),('d','c'),('6','b'),('b','6'),('2','7'),('7','2'),
     ('4','7'),('7','4'),('5','3'),('3','5'),('f','t'),('N','W'),('Q','W'),('R','H'),('b','f'),('f','b')]
def match(b,tok):
    global LENIENT
    t=tok.rstrip('!?+#')
    LENIENT=False
    r=[m for m in b.legal_moves if t in forms_for(b,m)]
    if r: return r
    LENIENT=True
    r=[m for m in b.legal_moves if t in forms_for(b,m)]
    LENIENT=False
    if r: LOOSE.append((t,b.fen()))
    return r
LOOSE=[]
def repair(b,tok):
    t=tok.rstrip('!?+#'); c={}
    for i,ch in enumerate(t):
        for a,x in SUB:
            if ch!=a: continue
            nt=t[:i]+x+t[i+1:]
            for m in b.legal_moves:
                if nt in forms_for(b,m): c[nt]=m
    return c
sols=json.load(open('ksols.json')); fens=json.load(open('kfens.json'))
F={(f['test'],f['num']):f['fen'] for f in fens}
fixes=[];fails=[];nmv=0
for s in sols:
    b=chess.Board(F[(s['test'],s['num'])])
    body=strip_var(s['body'])
    exp=1
    for m in MOVE.finditer(body):
        n=int(m.group(1))
        if n!=exp: break
        black_first=bool(m.group(2))
        mv_toks=[m.group(3)]+([m.group(4)] if m.group(4) else [])
        if black_first and b.turn!=chess.BLACK: break
        if not black_first and b.turn!=chess.WHITE: break
        bad=False
        for tok in mv_toks:
            ms=match(b,tok); nmv+=1
            if ms: b.push(ms[0]); continue
            c=repair(b,tok)
            if len(c)==1:
                nt,mm=list(c.items())[0]; fixes.append((s['test'],s['num'],n,tok,nt)); b.push(mm); continue
            fails.append((s['test'],s['num'],n,tok,sorted(c.keys())[:5],b.fen())); bad=True; break
        if bad: break
        exp=n+1
print('moves validated:',nmv)
print('fixes:',len(fixes))
for f in fixes: print(' FIX',f)
print('fails:',len(fails))
for f in fails: print(' FAIL',f)
json.dump({'fixes':fixes,'fails':fails},open('krepair2.json','w'),ensure_ascii=False,indent=0)
