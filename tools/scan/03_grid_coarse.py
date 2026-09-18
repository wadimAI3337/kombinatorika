"""Шаг 3. Грубая посадка сетки 8x8.

Сначала inner_box() даёт первое приближение по рамке, затем перебором
(шаг клетки +-0.5, сдвиги +-3 px) максимизируем контраст чётности:
средняя яркость клеток одного цвета минус средняя яркость клеток другого.
Мера считается по центральным 30-70% клетки, чтобы фигуры не мешали.

Важно: эта мера почти не чувствительна к сдвигу на 1-2 px (центры клеток
при таком сдвиге остаются центрами). Поэтому после неё ОБЯЗАТЕЛЕН шаг 4.
Здесь она нужна только чтобы попасть в правильную фазу шахматного узора.
"""
import sys,os; sys.path.insert(0,'.')
from kframe import inner_box
from kfit3 import integral, score
import numpy as np, json
from PIL import Image
meta=json.load(open('kmeta.json')); pages=sorted(os.listdir('pages'))
N=44; INS=0.07
out=np.empty((len(meta),64,N,N),dtype=np.uint8)
names=[]; fits=[]; fails=[]
cur=None; curim=None
for i,m in enumerate(meta):
    pgf=pages[m['pg']-4]
    if pgf!=cur: cur=pgf; curim=Image.open(f'pages/{pgf}').convert('L')
    im=curim
    L,T,R,B=m['box']; pad=18
    crop=im.crop((L-pad,T-pad,R+pad,B+pad))
    a=np.asarray(crop).astype(np.float32)
    bx=inner_box(a)
    if bx is None:
        fails.append((m['test'],m['num'])); bx=(pad,pad,a.shape[1]-pad,a.shape[0]-pad)
    x0,y0,x1,y1=bx
    cx=(x1-x0)/8.0; cy=(y1-y0)/8.0; c=(cx+cy)/2
    I=integral(a); H,W=a.shape
    best=(score(I,y0,x0,c,H,W),y0,x0,c)
    for dc in np.arange(-0.5,0.51,0.1):
        for dy in np.arange(-3,3.1,0.5):
            for dx in np.arange(-3,3.1,0.5):
                s=score(I,y0+dy,x0+dx,c+dc,H,W)
                if s>best[0]: best=(s,y0+dy,x0+dx,c+dc)
    s,yy,xx,cc=best
    fits.append([float(s),float(yy),float(xx),float(cc)])
    k=0
    for r in range(8):
        for f in range(8):
            box=(xx+f*cc+INS*cc, yy+r*cc+INS*cc, xx+(f+1)*cc-INS*cc, yy+(r+1)*cc-INS*cc)
            out[i,k]=np.asarray(crop.resize((N,N),Image.BILINEAR,box=box),dtype=np.uint8); k+=1
    names.append(f"{m['test']:02d}_{m['num']:02d}")
np.save('kc3.npy',out); json.dump({'names':names,'fits':fits,'fails':fails},open('kfits3.json','w'))
print(out.shape,'fails',fails,'min score',min(f[0] for f in fits))
