from PIL import Image
import numpy as np
def maxrun(b):
    # max consecutive True run per row of 2D bool array
    out=np.zeros(b.shape[0],dtype=int)
    for i in range(b.shape[0]):
        r=b[i]; best=cur=0
        for v in r:
            cur = cur+1 if v else 0
            if cur>best: best=cur
        out[i]=best
    return out
def maxrun_fast(b):
    # vectorized-ish
    res=[]
    for i in range(b.shape[0]):
        idx=np.flatnonzero(np.diff(np.concatenate(([0],b[i].view(np.int8),[0]))))
        res.append(0 if len(idx)==0 else int((idx[1::2]-idx[0::2]).max()))
    return np.array(res)
def groups(x, gap=6):
    g=[];s=None;p=None
    for v in x:
        if s is None: s=p=v; continue
        if v<=p+gap: p=v; continue
        g.append((s,p)); s=p=v
    if s is not None: g.append((s,p))
    return g
def detect(a, minlen=350):
    dark=a<140
    hr=maxrun_fast(dark)
    vr=maxrun_fast(dark.T)
    rows=groups([i for i,v in enumerate(hr) if v>=minlen])
    cols=groups([i for i,v in enumerate(vr) if v>=minlen])
    rc=[(s+p)//2 for s,p in rows]; cc=[(s+p)//2 for s,p in cols]
    return rc, cc
