import numpy as np

def runs(mask):
    idx=np.flatnonzero(np.diff(np.concatenate(([0],mask.view(np.int8),[0]))))
    return list(zip(idx[0::2], idx[1::2]))

def edge(prof, guess, want_end, win=17):
    n=len(prof)
    m=prof>0.75
    rr=[r for r in runs(m) if r[1]-r[0]<=18 and abs((r[0]+r[1])/2-guess)<=win]
    if not rr: return None
    rr.sort(key=lambda r:abs((r[0]+r[1])/2-guess))
    s,e=rr[0]
    while s>0 and prof[s-1]>0.35: s-=1
    while e<n and prof[e]>0.35: e+=1
    return e if want_end else s

def refine(a, y0, x0, c):
    dark=(a<140).astype(np.float32)
    H,W=a.shape
    xs=slice(max(0,int(x0+0.7*c)), min(W,int(x0+7.3*c)))
    ys=slice(max(0,int(y0+0.7*c)), min(H,int(y0+7.3*c)))
    rowp=dark[:,xs].mean(1); colp=dark[ys,:].mean(0)
    T=edge(rowp, y0, True)
    B=edge(rowp, y0+8*c, False)
    L=edge(colp, x0, True)
    R=edge(colp, x0+8*c, False)
    if None in (T,B,L,R): return None
    ch=(B-T)/8.0; cw=(R-L)/8.0
    if not (0.9 < ch/cw < 1.12): return None
    if abs(ch-c)>4 or abs(cw-c)>4: return None
    return T,L,ch,cw
