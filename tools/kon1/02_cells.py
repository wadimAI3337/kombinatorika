import os
import numpy as np, json
from PIL import Image
S=os.environ.get('KON1_WORK','work')
fr=json.load(open(f'{S}/frames.json'))
C=64  # cell size after resample
boards=[]; cells=[]
for pg in range(12,52):
    im=Image.open(f'{S}/pages/p{pg:03d}.png')
    H=fr[str(pg)]['H']; V=fr[str(pg)]['V']
    for r in range(3):
        for c in range(2):
            y0=H[2*r][1]+1; y1=H[2*r+1][0]; x0=V[2*c][1]+1; x1=V[2*c+1][0]
            b=im.crop((x0,y0,x1,y1)).resize((8*C,8*C),Image.BILINEAR)
            a=np.array(b)
            boards.append(dict(pg=pg,r=r,c=c,box=[x0,y0,x1,y1]))
            for i in range(8):
                for j in range(8):
                    cells.append(a[i*C:(i+1)*C, j*C:(j+1)*C])
np.save(f'{S}/cells.npy',np.array(cells,dtype=np.uint8))
json.dump(boards,open(f'{S}/boards.json','w'))
print(len(boards),len(cells))
# preview first board
b0=np.array(cells[:64]).reshape(8,8,C,C).transpose(0,2,1,3).reshape(8*C,8*C)
Image.fromarray(b0).save(f'{S}/b0.png')
