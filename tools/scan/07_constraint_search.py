"""Шаг 7. Чиним подписи кластеров шахматными правилами.

Ручная разметка ошибается в первую очередь в цвете: на усреднённой картинке
чёрный король и белый король отличаются только заливкой "ушей" короны.

Локальный поиск: перебираем кластеры (от крупных к мелким), пробуем
перекрасить кластер в противоположный цвет, оставляем замену, если
суммарная стоимость нарушений по всем 600 доскам падает.

Стоимость: |число K - 1|*10 + |число k - 1|*10 + лишние пешки*3
+ пешки на крайних горизонталях*4 + перебор фигур*2.

Замена на 'X' (выбросить кластер) разрешена только мелким кластерам:
иначе поиск начинает "стирать" фигуры, чтобы уложиться в лимит 16.

У нас: стоимость 2714 -> 46, найдено 5 ошибок разметки.
"""
import numpy as np, sys, json; sys.path.insert(0,'.')
from kn2labels import LAB
lab=np.load('kn2lab.npy'); order=np.load('kn2order.npy'); occ=np.load('k8occ.npy')
K=420
cur=[None]*K
for p,ci in enumerate(order): cur[int(ci)]=LAB[p]
bidx=occ//64; sidx=occ%64
cells=[np.where(lab==c)[0] for c in range(K)]

def build(labels):
    B=np.full((600,64),'.',dtype='<U1')
    for c in range(K):
        L=labels[c]
        if L=='X': continue
        idx=cells[c]
        B[bidx[idx],sidx[idx]]=L
    return B

def cost(B):
    tot=0.0
    cnt={ch:(B==ch).sum(1) for ch in 'KkQqRrBbNnPp'}
    tot+=10*np.abs(cnt['K']-1).sum()+10*np.abs(cnt['k']-1).sum()
    tot+=3*np.maximum(cnt['P']-8,0).sum()+3*np.maximum(cnt['p']-8,0).sum()
    back=np.concatenate([B[:,0:8],B[:,56:64]],1)
    tot+=4*((back=='P')|(back=='p')).sum()
    w=sum(cnt[c] for c in 'KQRBNP'); b=sum(cnt[c] for c in 'kqrbnp')
    tot+=2*np.maximum(w-16,0).sum()+2*np.maximum(b-16,0).sum()
    tot+=2*np.maximum(cnt['Q']-1-np.maximum(8-cnt['P'],0),0).sum()
    tot+=2*np.maximum(cnt['q']-1-np.maximum(8-cnt['p'],0),0).sum()
    return tot

FLIP={'K':'k','k':'K','Q':'q','q':'Q','R':'r','r':'R','B':'b','b':'B','N':'n','n':'N','P':'p','p':'P'}
B=build(cur); c0=cost(B); print('seed',c0)
for it in range(12):
    improved=False
    orderc=sorted(range(K), key=lambda c:-len(cells[c]))
    for c in orderc:
        L=cur[c]
        if L=='X' or len(cells[c])==0: continue
        for alt in ([FLIP[L]] if len(cells[c])>=8 else [FLIP[L],'X']):
            cur[c]=alt
            B2=build(cur); c2=cost(B2)
            if c2<c0-1e-9:
                c0=c2; improved=True; L=alt; break
            cur[c]=L
    print('iter',it,c0)
    if not improved: break
B=build(cur)
np.save('kn2board2.npy',B)
diff=[(p,LAB[p],cur[int(order[p])],int(len(cells[int(order[p])]))) for p in range(K) if cur[int(order[p])]!=LAB[p]]
print(len(diff)); print(diff)
import collections
print(collections.Counter(B.ravel()))
for ch in 'KkQq': print(ch,np.bincount((B==ch).sum(1),minlength=4)[:4])
