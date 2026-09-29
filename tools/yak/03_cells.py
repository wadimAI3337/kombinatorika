"""Доска -> 64 клетки 40x40 (как dvor/03_cells.py): границы — внутренние края
   рамки по профилю черноты, уменьшение усреднением площади."""
import json, sys, importlib.util, os
import numpy as np
spec = importlib.util.spec_from_file_location("C", os.path.join(os.path.dirname(os.path.abspath(__file__)), "../dvor/03_cells.py"))
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
if __name__ == "__main__":
    bj = json.load(open("work/boards.json"))
    allc, meta = [], []
    for p in sorted(bj, key=int):
        for k, bb in enumerate(bj[p]):
            fn = f"work/boards/p{int(p):03d}_{k}.png"
            try: c, g = C.cells(fn)
            except Exception as e: print("fail", fn, e); continue     # повёрнутый скан — FEN руками в fix_fens.json

            allc.append(c); meta.append([int(p), k, bb[2]])
    np.save("work/cells.npy", np.stack(allc)); json.dump(meta, open("work/cells_meta.json", "w"))
    print(len(meta))
