"""Шаг 4. Точная посадка сетки по внутренним краям рамки.

Берём профиль черноты вдоль каждой оси (доля тёмных пикселей в строке /
столбце, считая только внутри доски), ищем возле ожидаемого места сплошной
участок (доля > 0.75, расширенный до 0.35) шириной не больше 18 px — это рамка.
Внутренний край рамки и есть граница доски.

Высота и ширина клетки считаются РАЗДЕЛЬНО: сканы бывают неквадратными.
Проверка ch/cw в пределах 0.9-1.12 отсекает случаи, когда рамка не нашлась
и подцепился ряд фигур.

На выходе kc4.npy: (600, 64, 48, 48) — все клетки всех досок.
"""
import sys,os; sys.path.insert(0,'.')
import numpy as np, json
from PIL import Image
from kref import refine
meta=json.load(open('kmeta.json')); pages=sorted(os.listdir('pages'))
fits=json.load(open('kfits3.json'))['fits']
N=48; INS=0.0
out=np.empty((len(meta),64,N,N),dtype=np.uint8)
bad=[]; geo=[]
cur=None; curim=None
for i,m in enumerate(meta):
    pgf=pages[m['pg']-4]
    if pgf!=cur: cur=pgf; curim=Image.open(f'pages/{pgf}').convert('L')
    L,T,R,B=m['box']; pad=18
    crop=curim.crop((L-pad,T-pad,R+pad,B+pad))
    a=np.asarray(crop).astype(np.float32)
    s,yy,xx,cc=fits[i]
    r=refine(a,yy,xx,cc)
    if r is None:
        bad.append(i); y0,x0,ch,cw=yy,xx,cc,cc
    else:
        y0,x0,ch,cw=r
    geo.append([float(y0),float(x0),float(ch),float(cw)])
    k=0
    for rr in range(8):
        for f in range(8):
            box=(x0+f*cw, y0+rr*ch, x0+(f+1)*cw, y0+(rr+1)*ch)
            out[i,k]=np.asarray(crop.resize((N,N),Image.BILINEAR,box=box),dtype=np.uint8); k+=1
np.save('kc4.npy',out); json.dump({'geo':geo,'bad':bad},open('kgeo4.json','w'))
print(out.shape,'bad',len(bad),bad[:20])
