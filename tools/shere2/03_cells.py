"""Доска -> 64 клетки 40x40 (dvor/03_cells.py). Меньше 480 px — фотографии, не доски."""
import json, importlib.util, os
import numpy as np
spec = importlib.util.spec_from_file_location("C", os.path.join(os.path.dirname(os.path.abspath(__file__)), "../dvor/03_cells.py"))
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
MIN, MAX = 480, 580       # меньше и больше — фотографии
from PIL import Image
# страницы с фотографией (картинка 800 px) в кластеры не идут — их доски распознаёт 05_fen.py по эталонам
LOWRES = {p for p in range(0, 402) if os.path.exists(f"work/full/p{p:03d}.png") and Image.open(f"work/full/p{p:03d}.png").size[0] != 1600}
if __name__ == "__main__":
    bj = json.load(open("work/boards.json"))
    allc, meta = [], []
    for p in sorted(bj, key=int):
        for k, bb in enumerate(bj[p]):
            if not MIN <= bb[2] <= MAX or int(p) in LOWRES: continue
            fn = f"work/boards/p{int(p):03d}_{k}.png"
            try: c, g = C.cells(fn)
            except Exception as e: print("fail", fn, e); continue
            allc.append(c); meta.append([int(p), k, bb[2]])
    np.save("work/cells.npy", np.stack(allc)); json.dump(meta, open("work/cells_meta.json", "w"))
    print(len(meta))
