"""k-means отдельно по светлым и тёмным полям -> контактные листы центроидов."""
import numpy as np, json
from sklearn.cluster import MiniBatchKMeans
from PIL import Image, ImageDraw
C = np.load("work/cells.npy")                  # N x 64 x 40 x 40
N = len(C)
dark = np.array([(i // 8 + i % 8) % 2 == 1 for i in range(64)])
res = {}
for name, mask in (("L", ~dark), ("D", dark)):
    X = C[:, mask].reshape(-1, 1600)
    km = MiniBatchKMeans(n_clusters=64, random_state=0, batch_size=4096, n_init=3).fit(X)
    lab = km.labels_; d = km.transform(X).min(1)
    res[name] = (lab, d)
    cnt = np.bincount(lab, minlength=64)
    sheet = Image.new("L", (8 * 110, 8 * 125), 255); dr = ImageDraw.Draw(sheet)
    for k in range(64):
        im = Image.fromarray((255 - km.cluster_centers_[k].reshape(40, 40) * 255).clip(0, 255).astype(np.uint8)).resize((96, 96), Image.NEAREST)
        x, y = (k % 8) * 110, (k // 8) * 125
        sheet.paste(im, (x + 7, y + 20)); dr.text((x + 7, y + 4), f"{k}  n={cnt[k]}", fill=0)
    sheet.save(f"work/sheet_{name}.png")
    np.save(f"work/lab_{name}.npy", lab); np.save(f"work/dist_{name}.npy", d)
    np.save(f"work/cent_{name}.npy", km.cluster_centers_)
print("ok")
