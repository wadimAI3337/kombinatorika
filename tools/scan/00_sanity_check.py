"""Шаг 0 (выполняется после 08). Проверка расстановки шахматными правилами.

Это главный инструмент контроля качества: ошибки распознавания почти
всегда ломают одно из этих условий, а верная расстановка не ломает ни одного.

    ровно один белый и один чёрный король
    не больше 8 пешек у стороны
    нет пешек на 1-й и 8-й горизонтали
    не больше 16 фигур у стороны
"""
import numpy as np
B = np.load('board.npy')
cnt = {c: (B == c).sum(1) for c in 'KkQqRrBbNnPp'}
back = np.concatenate([B[:, 0:8], B[:, 56:64]], 1)
w = sum(cnt[c] for c in 'KQRBNP'); bl = sum(cnt[c] for c in 'kqrbnp')
bad = []
for i in range(len(B)):
    e = []
    if cnt['K'][i] != 1: e.append('K=%d' % cnt['K'][i])
    if cnt['k'][i] != 1: e.append('k=%d' % cnt['k'][i])
    if cnt['P'][i] > 8: e.append('P>8')
    if cnt['p'][i] > 8: e.append('p>8')
    if ((back[i] == 'P') | (back[i] == 'p')).sum(): e.append('пешка на краю')
    if w[i] > 16 or bl[i] > 16: e.append('>16 фигур')
    if e: bad.append((i, e))
print('нарушений:', len(bad))
for x in bad: print(' ', x)
print('фигур на диаграмму:', round((B != '.').sum()/len(B), 2))
