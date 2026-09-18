"""Шаг 5. Фон, чернила, занятость клетки.

Фон считается отдельно для светлых и тёмных клеток КАЖДОЙ доски
(медиана по 32 клеткам своей чётности): тёмная клетка печатается растром
и её средняя яркость ~180 против ~250 у светлой.

чернила   = V < фон - 55, компоненты меньше 18 px выбрасываются,
            узкие полоски у края клетки тоже (это обрывки рамки)
светлое   = V > фон + 40, компоненты меньше 85 px выбрасываются
            (нужно, чтобы белая фигура на тёмной клетке дала силуэт)
силуэт    = замыкание объединения + заливка дыр, берём крупнейшую компоненту

ЗАНЯТОСТЬ определяем по площади ЧЕРНИЛ, а не силуэта: у силуэта белой фигуры
заливка рвётся на разомкнутом контуре и площадь скачет. Площадь чернил даёт
чистый разрыв: 0 у пустых, >=200 у занятых.
"""
import numpy as np, json
from scipy import ndimage as ndi
C=np.load('kc4.npy').astype(np.float32)   # (600,64,48,48)
NB,NC,N,_=C.shape
V=ndi.uniform_filter(C.reshape(-1,N,N),size=(1,3,3))
V=V.reshape(NB,NC,N,N)
PAR=(np.add.outer(np.arange(8),np.arange(8))%2==0).ravel()   # True = light
bg=np.empty((NB,NC),np.float32)
for b in range(NB):
    for p in (True,False):
        m=PAR==p
        bg[b,m]=np.median(V[b,m])
V=V.reshape(-1,N,N); bg=bg.ravel()
n=len(V)
ink0=V<bg[:,None,None]-55
br0 =V>bg[:,None,None]+40
border=np.zeros((N,N),bool); border[0,:]=border[-1,:]=border[:,0]=border[:,-1]=True
ink=np.zeros((n,N,N),bool); sil=np.zeros((n,N,N),bool)
for i in range(n):
    a=np.zeros((N,N),bool)
    if ink0[i].sum()>=45:
        lab,k=ndi.label(ink0[i])
        if k:
            sz=ndi.sum(ink0[i],lab,range(1,k+1))
            objs=ndi.find_objects(lab)
            keep=np.zeros(k+1,bool)
            for j in range(k):
                sl=objs[j]; h=sl[0].stop-sl[0].start; w=sl[1].stop-sl[1].start
                if sz[j]<18: continue
                # drop thin slivers hugging the border (frame remnants)
                touch=(sl[0].start==0 or sl[0].stop==N or sl[1].start==0 or sl[1].stop==N)
                if touch and min(h,w)<=5: continue
                keep[j+1]=True
            a=keep[lab]
    ink[i]=a
    b2=np.zeros((N,N),bool)
    if br0[i].sum()>=70:
        lab,k=ndi.label(br0[i]); sz=ndi.sum(br0[i],lab,range(1,k+1))
        keep=np.zeros(k+1,bool); keep[1:][sz>=85]=True; b2=keep[lab]
    u=a|b2
    if u.sum()<70: continue
    m=ndi.binary_fill_holes(ndi.binary_closing(u,np.ones((5,5))))
    l2,k2=ndi.label(m)
    if k2>1:
        s2=ndi.sum(m,l2,range(1,k2+1)); m=(l2==int(np.argmax(s2))+1)
    sil[i]=m
area=sil.reshape(n,-1).sum(1)
np.save('k8ink.npy',ink); np.save('k8sil.npy',sil); np.save('k8area.npy',area)
np.save('k8V.npy',V.astype(np.uint8)); np.save('k8bg.npy',bg)
for t in [250,300,350,400,450]:
    print('thr',t,'per board',round((area>=t).sum()/NB,2))
