import os
import numpy as np, json, itertools, chess, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from lineparse import norm, pick_move, do_move, SAN_CORE
import re
S=os.environ.get('KON1_WORK','work')
typ=np.load(S+'/typ.npy'); hole=np.load(S+'/hole.npy'); hole0=np.load(S+'/hole0.npy'); band=np.load(S+'/qband.npy')
qi=list(np.where(typ=='Q')[0]); qband={int(i):float(b) for i,b in zip(qi,band)}
side=json.load(open(S+'/side.json')); side[53]='w'; side[10]='b'
# ручные поправки распознавания: доска -> {клетка: фигура}; клетка как в FEN (0 = a8)
FIX={133:{61:'B'}, 130:{7:'K'}, 228:{1:'b'}, 53:{21:'B'},
     # цвет ферзей, который решает текст решения (см. разбор в README)
     124:{12:'q',37:'Q'}, 159:{3:'Q',27:'Q',14:'q',53:'q'}, 199:{19:'q',29:'Q'}, 235:{58:'q',59:'Q'}}
# правки вычитки: край скана обрезан, ход восстановлен по дальнейшему тексту
TXTFIX={235:[('1.Qd7!! Qc1+','1.Qd7!! Q:e1+')]}
A=json.load(open(S+'/answers.json'))
THR={'P':150,'N':150,'B':150,'K':150,'R':150}
def fen_of(grid,s):
    rows=[]
    for r in range(8):
        row='';e=0
        for c in range(8):
            p=grid[r][c]
            if p: row+=(str(e) if e else '')+p; e=0
            else: e+=1
        rows.append(row+(str(e) if e else ''))
    pl='/'.join(rows); bd=chess.Board(pl+' w - - 0 1'); cr=''
    P=chess.Piece.from_symbol
    if bd.piece_at(chess.E1)==P('K'):
        if bd.piece_at(chess.H1)==P('R'): cr+='K'
        if bd.piece_at(chess.A1)==P('R'): cr+='Q'
    if bd.piece_at(chess.E8)==P('k'):
        if bd.piece_at(chess.H8)==P('r'): cr+='k'
        if bd.piece_at(chess.A8)==P('r'): cr+='q'
    return f'{pl} {s} {cr or "-"} - 0 1'
out=[]; report=[]
for b in range(240):
    grid=[[None]*8 for _ in range(8)]; qs=[]
    for sq in range(64):
        i=b*64+sq; t=typ[i]
        if t=='E': continue
        if t=='Q': qs.append((i,sq)); continue
        white=(hole0[i]>=700) if t=='N' else (hole[i]>=THR[t])
        grid[sq//8][sq%8]=t if white else t.lower()
    for sq,pc in FIX.get(b,{}).items(): grid[sq//8][sq%8]=pc; qs=[q for q in qs if q[1]!=sq]
    a=A[b]
    for o,n in TXTFIX.get(b,[]): assert o in a['text']; a['text']=a['text'].replace(o,n)
    txt=norm(a['text']); s=side[b]
    best=None; scores=[]
    for combo in itertools.product('Qq',repeat=len(qs)):
        for (i,sq),c in zip(qs,combo): grid[sq//8][sq%8]=c
        f=fen_of(grid,s); bd=chess.Board(f)
        st=bd.status(); valid=st==chess.STATUS_VALID
        pick,line,cands=pick_move(f,s,txt)
        prior=sum((qband[i]-0.87)*(1 if c=='q' else -1) for (i,sq),c in zip(qs,combo))
        nq=[combo.count('Q'),combo.count('q')]
        rx=re.compile(r'(?<![\d.])1' + (r'\.(?!\.)' if s=='w' else r'\.\.\.') + '(' + SAN_CORE + ')')
        ment=[bool(do_move(chess.Board(f),mm.group(1))) for mm in rx.finditer(txt)] if valid else []
        sc=(valid*100)+len(line)*10+len(cands)*3+prior*20-10*sum(max(0,x-1) for x in nq)-40*ment.count(False)
        scores.append(sc)
        if best is None or sc>best[0]: best=(sc,f,valid,len(line),len(cands),str(st))
    ss=sorted(scores,reverse=True); margin=ss[0]-ss[1] if len(ss)>1 else 999
    out.append(dict(b=b,fen=best[1],valid=best[2],plies=best[3],cands=best[4],margin=round(margin,1),nq=len(qs)))
    if not best[2] or best[3]==0: report.append((b,best[1],best[5],best[3]))
json.dump(out,open(S+'/fens.json','w')); json.dump(A,open(S+'/answers_fixed.json','w'),ensure_ascii=False)
print('invalid or no line:',len(report))
for r in report: print(r)
