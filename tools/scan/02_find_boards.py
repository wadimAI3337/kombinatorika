"""Шаг 2. Найти диаграммы на странице и вырезать их.

Рамка диаграммы — длинная сплошная тёмная линия. Ищем строки и столбцы,
где максимальная непрерывная серия тёмных пикселей длиннее minlen, и
группируем соседние. На развороте книги 6 диаграмм: 3 ряда x 2 колонки,
значит должно найтись ровно 6 горизонтальных и 4 вертикальных линии.

Если не нашлось — понижаем minlen (350 -> 320 -> 300 -> 280): на бледных
сканах рамка местами светлее порога. Отдельный случай: нашлись 3 колонки
вместо 4 (крайняя правая обрезана при сканировании) — четвёртую достраиваем
по шагу между первыми двумя.

Заодно режем подпись под диаграммой (полоска 190x40 под левым нижним углом) —
из неё потом определяется, чей ход.
"""
import sys, os, json, glob
sys.path.insert(0,'/tmp/claude-0/-home-claude/92163164-9364-555b-a43c-5bbbf44cb2a2/scratchpad')
from kdet import detect
from PIL import Image
import numpy as np
os.makedirs('kboards',exist_ok=True); os.makedirs('kcap',exist_ok=True)
def merge(x, tol=30):
    out=[]
    for v in x:
        if out and v-out[-1][-1]<=tol: out[-1].append(v)
        else: out.append([v])
    return [int(np.mean(g)) for g in out]
files=sorted(glob.glob('pages/p-*.png'))
assert len(files)==100, len(files)
meta=[]; bad=[]
for i,f in enumerate(files):
    pg=4+i
    im=Image.open(f).convert('L'); a=np.asarray(im).astype(float)
    ok=False
    for ml in [350,320,300,280]:
        rc,cc=detect(a,ml); rc=merge(rc); cc=merge(cc)
        if len(rc)==6 and len(cc)==4: ok=True; break
    if not ok:
        rc,cc=detect(a,320); rc=merge(rc); cc=merge(cc)
        if len(rc)==6 and len(cc)==3:
            cc=cc+[cc[2]+(cc[1]-cc[0])]; ok=True
    if not ok:
        bad.append((pg,rc,cc)); continue
    test=(pg-4)//2+1; half=(pg-4)%2; k=0
    for r in range(3):
        for c in range(2):
            k+=1; num=half*6+k
            top,bot=rc[2*r],rc[2*r+1]; lef,rig=cc[2*c],cc[2*c+1]
            im.crop((lef,top,rig,bot)).save(f'kboards/{test:02d}_{num:02d}.png')
            im.crop((lef-12, bot+4, lef+190, bot+44)).save(f'kcap/{test:02d}_{num:02d}.png')
            meta.append({'test':test,'num':num,'pg':pg,'box':[lef,top,rig,bot]})
json.dump(meta,open('kmeta.json','w'))
print('boards',len(meta),'bad pages',bad)
