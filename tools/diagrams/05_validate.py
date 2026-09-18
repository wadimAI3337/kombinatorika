"""Шаг 5. Расстановка -> проверка правилами + список клеток «посмотри глазами»."""
import os, numpy as np

W = os.path.dirname(os.path.abspath(__file__))
P = np.load(os.path.join(W, "pieces.npy")).reshape(640, 64)
M = np.load(os.path.join(W, "margin.npy")).reshape(640, 64)
names = np.load(os.path.join(W, "names.npy"))
FILES = "abcdefgh"

problems = []
for i in range(640):
    b = list(P[i])
    errs = []
    if b.count("K") != 1: errs.append(f"белых королей {b.count('K')}")
    if b.count("k") != 1: errs.append(f"чёрных королей {b.count('k')}")
    if b.count("P") > 8: errs.append(f"белых пешек {b.count('P')}")
    if b.count("p") > 8: errs.append(f"чёрных пешек {b.count('p')}")
    edge = [b[j] for j in list(range(8)) + list(range(56, 64))]
    if any(c in "Pp" for c in edge): errs.append("пешка на крайней горизонтали")
    if errs: problems.append((int(names[i]), errs))

print("досок:", 640, "| нарушают шахматные правила:", len(problems))
for n, e in problems: print(f"  №{n}: {'; '.join(e)}")

low = np.argwhere(M < 0.5)
print("\nклеток с малым запасом (<0.5) — проверить глазами:", len(low))
for i, j in low:
    print(f"  №{int(names[i])} {FILES[j%8]}{8-j//8}: {P[i,j]}  запас {M[i,j]:.3f}")
