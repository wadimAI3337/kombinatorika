import os
import numpy as np
S=os.environ.get('KON1_WORK','work')
T="""0 P,1 E,2 P,3 R,4 K,5 P,6 Q,7 R,8 B,9 P,10 N,11 P,12 R,13 K,14 B,15 P,16 N,17 P,18 R,19 K,20 P,21 K,22 N,23 Q,
24 N,25 Q,26 P,27 K,28 Q,29 R,30 N,31 N,32 Q,33 B,34 B,35 P,36 N,37 B,38 B,39 P,40 P,41 P,42 R,43 K,44 B,45 R,46 R,47 P,48 P,49 Q,50 R,51 N,52 P,53 Q,54 P,55 B,56 R,57 R,58 P,59 P,60 K,61 B,62 B,63 R,64 R,65 R,66 Q,67 R,68 R,69 N,
100 E,101 P,102 E,103 P,104 Q,105 E,106 R,107 K,108 P,109 R,110 B,111 R,112 P,113 N,114 P,115 K,116 Q,117 P,118 P,119 E,120 P,121 P,122 N,123 E,124 P,125 R,
126 N,127 N,128 K,129 B,130 R,131 B,132 Q,133 N,134 E,135 P,136 B,137 Q,138 E,139 E,140 P,141 Q,142 Q,143 P,144 P,145 B,146 K,147 R,148 R,149 R,
150 Q,151 E,152 E,153 R,154 N,155 P,156 P,157 Q,158 P,159 K,160 E,161 R,162 K,163 E,164 E,165 N,166 E,167 P,168 P,169 B"""
TY={int(a):b for a,b in (x.split() for x in T.replace('\n','').split(','))}
lab=np.load(S+'/lab2.npy'); cells=np.load(S+'/cells.npy')
typ=np.array([TY[l] for l in lab])
# kNN relabel within same square parity
from PIL import Image, ImageFilter
feat=np.array([np.array(Image.fromarray(c[4:60,4:60]).filter(ImageFilter.GaussianBlur(1.1)).resize((24,24),Image.BILINEAR),dtype=np.float32).ravel()/255 for c in cells])
N=len(cells); sq=np.arange(N)%64; dark=((sq//8)+(sq%8))%2==1
from sklearn.neighbors import NearestNeighbors
new=typ.copy()
for par in (0,1):
    m=np.where(dark==bool(par))[0]
    nn=NearestNeighbors(n_neighbors=8).fit(feat[m]); _,ix=nn.kneighbors(feat[m])
    for a,row in zip(m,ix):
        votes=typ[m[row[1:]]]
        v,c=np.unique(votes,return_counts=True)
        if c.max()>=5 and v[c.argmax()]!=typ[a]: new[a]=v[c.argmax()]
ch=np.where(new!=typ)[0]
print('relabeled',len(ch),[(int(i),typ[i],new[i]) for i in ch[:40]])
np.save(S+'/typ.npy',new)
blk=np.load(S+'/blk.npy')
for t in 'KQRBNP':
    v=blk[new==t]; h,_=np.histogram(v,bins=20,range=(0,0.6)); print(t,len(v),h)
