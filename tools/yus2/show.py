import numpy as np, sys
from PIL import Image
C=np.load("work/cells.npy"); dark=np.array([(i//8+i%8)%2==1 for i in range(64)])
def members(name, ks, n=12):
    lab=np.load(f"work/lab_{name}.npy"); mask=~dark if name=="L" else dark
    X=C[:,mask].reshape(-1,40,40)
    rows=[]
    for k in ks:
        idx=np.where(lab==k)[0]; sel=idx[np.linspace(0,len(idx)-1,min(n,len(idx))).astype(int)]
        rows.append(sel)
    sheet=Image.new("L",(12*64,len(ks)*64),255)
    for r,sel in enumerate(rows):
        for t,i in enumerate(sel): sheet.paste(Image.fromarray((255-X[i]*255).astype(np.uint8)).resize((60,60)),(t*64,r*64))
    sheet.save("work/m.png")
members(sys.argv[1], [int(x) for x in sys.argv[2].split(",")])
