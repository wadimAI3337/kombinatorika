"""Шаг 8. Кластер -> буква -> матрица 600x64 (расстановка)."""
import numpy as np, json, sys
sys.path.insert(0, '.')
from labels_example import LAB                 # 420 букв: K Q R B N P k q r b n p X

occ   = np.load('k8occ.npy')                   # индексы занятых клеток (board*64+square)
asg   = np.load('kn2asg.npy')                  # кластер для каждой занятой клетки
order = np.load('kn2order.npy')
c2l = {int(ci): LAB[p] for p, ci in enumerate(order)}

B = np.full((600, 64), '.', dtype='<U1')
for k, i in enumerate(occ):
    L = c2l[int(asg[k])]
    if L != 'X':                               # X = мусор (обрывок рамки)
        B[i//64, i % 64] = L
for b, s, v in json.load(open('override.json')):   # ручные правки единичных клеток
    B[b, s] = v
np.save('board.npy', B)
