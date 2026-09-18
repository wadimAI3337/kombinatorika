import numpy as np
def runs(mask):
    idx=np.flatnonzero(np.diff(np.concatenate(([0],mask.view(np.int8),[0]))))
    return list(zip(idx[0::2], idx[1::2]))  # [start,end)
def inner_box(a, frac=0.6, thr=140):
    H,W=a.shape
    dark=a<thr
    colcnt=dark[int(H*0.15):int(H*0.85)].sum(0); rowcnt=dark[:,int(W*0.15):int(W*0.85)].sum(1)
    ch=int((int(H*0.85)-int(H*0.15))*frac); rh=int((int(W*0.85)-int(W*0.15))*frac)
    cm=colcnt>=ch; rm=rowcnt>=rh
    cr=[r for r in runs(cm) if r[1]-r[0]<=14]
    rr=[r for r in runs(rm) if r[1]-r[0]<=14]
    if len(cr)<2 or len(rr)<2: return None
    L=cr[0][1]; R=cr[-1][0]; T=rr[0][1]; B=rr[-1][0]
    return L,T,R,B
