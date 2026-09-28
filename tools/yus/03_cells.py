"""Доски -> клетки 40x40 (та же нарезка, что в dvor/03_cells.py) -> k-means и листы для подписи."""
import json, sys, importlib.util
import numpy as np
from PIL import Image, ImageDraw
from sklearn.cluster import MiniBatchKMeans
spec = importlib.util.spec_from_file_location("c", "../dvor/03_cells.py"); C3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(C3)
bj = json.load(open("work/boards.json"))
allc, meta = [], []
for p in sorted(bj, key=int):
    for k, b in enumerate(bj[p]):
        if b[2] < 900: continue
        try: c, g = C3.cells(f"work/boards/p{int(p):03d}_{k}.png")
        except Exception as e: print("fail", p, k, e); continue
        allc.append(c); meta.append([int(p), k, b[2]])
C = np.stack(allc); np.save("work/cells.npy", C); json.dump(meta, open("work/cells_meta.json", "w"))
dark = np.array([(i // 8 + i % 8) % 2 == 1 for i in range(64)])
for name, mask in (("L", ~dark), ("D", dark)):
    X = C[:, mask].reshape(-1, 1600)
    km = MiniBatchKMeans(n_clusters=64, random_state=0, batch_size=4096, n_init=3).fit(X)
    np.save(f"work/lab_{name}.npy", km.labels_)
    cnt = np.bincount(km.labels_, minlength=64)
    sheet = Image.new("L", (8 * 110, 8 * 125), 255); dr = ImageDraw.Draw(sheet)
    for k in range(64):
        im = Image.fromarray((255 - km.cluster_centers_[k].reshape(40, 40) * 255).clip(0, 255).astype(np.uint8)).resize((96, 96))
        x, y = (k % 8) * 110, (k // 8) * 125
        sheet.paste(im, (x + 7, y + 20)); dr.text((x + 7, y + 4), f"{k}  n={cnt[k]}", fill=0)
    sheet.save(f"work/sheet_{name}.png")
print(len(meta))
