import os
import numpy as np, json
from PIL import Image
S=os.environ.get('KON1_WORK','work')
def runs(a):  # longest run of True per row
    out=np.zeros(a.shape[0],int)
    for i,row in enumerate(a):
        d=np.diff(np.concatenate([[0],row.astype(int),[0]]))
        s=np.where(d==1)[0]; e=np.where(d==-1)[0]
        out[i]=(e-s).max() if len(s) else 0
    return out
def groups(idx,tol=25):
    g=[]
    for v in idx:
        if g and v-g[-1][-1]<=tol: g[-1].append(v)
        else: g.append([v])
    return [(int(min(x)),int(max(x))) for x in g]
res={}
for pg in range(12,52):
    im=np.array(Image.open(f'{S}/pages/p{pg:03d}.png'))
    ink=im<110
    hr=runs(ink); vr=runs(ink.T)
    H=groups(np.where(hr>800)[0]); V=groups(np.where(vr>800)[0])
    res[pg]=dict(H=H,V=V)
    if len(H)!=6 or len(V)!=4: print(pg,len(H),len(V),H,V)
json.dump(res,open(f'{S}/frames.json','w'))
print('done', res[12])
