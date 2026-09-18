import numpy as np
def integral(a): return np.pad(np.cumsum(np.cumsum(a,0),1),((1,0),(1,0)))
def cells_mean(I,y0,x0,c,lo=0.30,hi=0.70):
    r=np.arange(8)
    ys=y0+r*c; xs=x0+r*c
    Y0=np.round(ys+lo*c).astype(int); Y1=np.round(ys+hi*c).astype(int)
    X0=np.round(xs+lo*c).astype(int); X1=np.round(xs+hi*c).astype(int)
    A=I[np.ix_(Y1,X1)]-I[np.ix_(Y0,X1)]-I[np.ix_(Y1,X0)]+I[np.ix_(Y0,X0)]
    area=(Y1-Y0)[:,None]*(X1-X0)[None,:]
    return A/area
PAR=np.add.outer(np.arange(8),np.arange(8))%2==0
def score(I,y0,x0,c,H,W):
    if y0<0 or x0<0 or y0+8*c>=H or x0+8*c>=W: return -1e9
    m=cells_mean(I,y0,x0,c)
    return m[PAR].mean()-m[~PAR].mean()
def fit_board(a,c_est):
    I=integral(a); H,W=a.shape
    best=(-1e9,0,0,c_est)
    for c in np.arange(c_est-1.0,c_est+1.0+1e-9,0.5):
        cy=(H-8*c)/2; cx=(W-8*c)/2
        for dy in np.arange(-10,10.1,2.0):
            for dx in np.arange(-10,10.1,2.0):
                s=score(I,cy+dy,cx+dx,c,H,W)
                if s>best[0]: best=(s,cy+dy,cx+dx,c)
    _,y0,x0,c0=best
    for c in np.arange(c0-0.6,c0+0.6+1e-9,0.15):
        for dy in np.arange(-2.5,2.6,0.5):
            for dx in np.arange(-2.5,2.6,0.5):
                s=score(I,y0+dy,x0+dx,c,H,W)
                if s>best[0]: best=(s,y0+dy,x0+dx,c)
    return best
