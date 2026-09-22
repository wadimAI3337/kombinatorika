import os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from sklearn.cluster import KMeans
S=os.environ.get('KON1_WORK','work')
cells=np.load(f'{S}/cells.npy'); N=len(cells)
feat=np.array([np.array(Image.fromarray(c[4:60,4:60]).filter(ImageFilter.GaussianBlur(1.1)).resize((36,36),Image.BILINEAR),dtype=np.float32)/255 for c in cells])
sq=np.arange(N)%64; dark=((sq//8)+(sq%8))%2==1
# empty detection first: few dark-ink pixels after removing hatch
from scipy import ndimage
occ=np.array([ndimage.binary_opening(c[8:56,8:56]<110,iterations=1).sum() for c in cells])
lab=np.full(N,-1)
groups={}
for par in (0,1):
    m=(dark==bool(par))
    X=feat[m].reshape(m.sum(),-1)
    km=KMeans(70,n_init=3,random_state=1).fit(X)
    lab[m]=km.labels_+par*100
np.save(f'{S}/lab2.npy',lab)
keys=sorted(set(lab)); T=66
def sheet(ks,name):
    im=Image.new('L',(70+10*T,len(ks)*T),255); d=ImageDraw.Draw(im)
    for r,k in enumerate(ks):
        mem=np.where(lab==k)[0]
        d.text((2,r*T+25),f'{k}:{len(mem)}',fill=0)
        pick=mem[np.linspace(0,len(mem)-1,min(10,len(mem))).astype(int)]
        for j,i in enumerate(pick): im.paste(Image.fromarray(cells[i]).resize((T-3,T-3)),(70+j*T,r*T))
    im.save(f'{S}/{name}.png')
for i in range(0,len(keys),24): sheet(keys[i:i+24],f'cs2_{i//24}')
print(len(keys), {k:int((lab==k).sum()) for k in keys})
