"""Шаг 9. Сборка FEN.

Рокировки эвристикой: разрешаем, если король и ладья стоят на начальных
полях. Взятия на проходе не ставим (в задачнике они не встречаются).
Счётчики ходов 0 1.

kmanual.json — позиции, перебитые вручную (плохие сканы), они
подставляются целиком вместо распознанных.
"""
import numpy as np, json
B=np.load('kn2board.npy'); xs=np.load('kcapx.npy'); meta=json.load(open('kmeta.json'))
def fen(row, turn):
    parts=[]
    for r in range(8):
        s=''; e=0
        for f in range(8):
            c=row[r*8+f]
            if c=='.': e+=1
            else:
                if e: s+=str(e); e=0
                s+=c
        if e: s+=str(e)
        parts.append(s)
    board='/'.join(parts)
    g=lambda sq: row[sq]
    idx=lambda f,r: (8-r)*8+f
    cas=''
    if g(idx(4,1))=='K':
        if g(idx(7,1))=='R': cas+='K'
        if g(idx(0,1))=='R': cas+='Q'
    if g(idx(4,8))=='k':
        if g(idx(7,8))=='r': cas+='k'
        if g(idx(0,8))=='r': cas+='q'
    return f"{board} {turn} {cas or '-'} - 0 1"
man=json.load(open('kmanual.json'))
out=[]
for i,m in enumerate(meta):
    turn='w' if xs[i]<73 else 'b'
    f=man.get(str(i)) or fen(B[i],turn)
    out.append({'test':m['test'],'num':m['num'],'fen':f})
json.dump(out,open('kfens.json','w'),ensure_ascii=False,indent=0)
print(len(out)); print(out[0]); print(out[3])
