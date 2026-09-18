"""Шаг 6a. Нормализация яркости и центрирование.

Яркость: линейно тянем [2-й перцентиль клетки; фон] -> [0; 1].
Это уравнивает клетку на светлом поле и на тёмном растровом.

Центрирование: сдвигаем картинку так, чтобы центр масс "черноты"
попал в середину. Без этого k-means разносит одну и ту же фигуру
по нескольким кластерам просто из-за сдвига на пару пикселей.

Сглаживание — гауссом sigma=0.8, НЕ сильнее: зубцы короны белого ферзя
тоньше 4 px, и при более сильном сглаживании он становится неотличим
от чёрного ферзя.
"""
import numpy as np
from scipy import ndimage as ndi
C=np.load('kc4.npy').reshape(-1,48,48).astype(np.float32)
bg=np.load('k8bg.npy'); occ=np.load('k8occ.npy')
A=C[occ]; B=bg[occ]; n=len(occ)
lo=np.percentile(A.reshape(n,-1),2,axis=1)
den=np.maximum(B-lo,30)
N=np.clip((A-lo[:,None,None])/den[:,None,None],0,1)
D=1.0-N
ys,xs=np.mgrid[0:48,0:48]
t=D.reshape(n,-1).sum(1)
cy=(D*ys).reshape(n,-1).sum(1)/t; cx=(D*xs).reshape(n,-1).sum(1)/t
Nc=np.empty_like(N)
for i in range(n):
    Nc[i]=ndi.shift(N[i],(23.5-cy[i],23.5-cx[i]),order=1,mode='constant',cval=1.0)
np.save('kn2Nc.npy',(Nc*255).astype(np.uint8))
F=ndi.gaussian_filter(Nc,(0,0.8,0.8)).reshape(n,-1)
np.save('kn2F.npy',F.astype(np.float32))
print(n,F.shape)
