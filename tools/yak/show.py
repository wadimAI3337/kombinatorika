import numpy as np, sys
from PIL import Image
C=np.load("work/cells.npy"); dark=np.array([(i//8+i%8)%2==1 for i in range(64)])
def members(name, k, n=24, out="work/m.png"):
    lab=np.load(f"work/lab_{name}.npy"); mask=~dark if name=="L" else dark
    X=C[:,mask].reshape(-1,40,40); idx=np.where(lab==k)[0]
    sel=idx[np.linspace(0,len(idx)-1,min(n,len(idx))).astype(int)] if len(idx) else []
    sheet=Image.new("L",(12*84,((len(sel)+11)//12)*84+1),255)
    for t,i in enumerate(sel):
        sheet.paste(Image.fromarray((255-X[i]*255).astype(np.uint8)).resize((80,80)),( (t%12)*84,(t//12)*84))
    sheet.save(out)
if __name__=="__main__":
    members(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv)>3 else 24)
