"""Досплит смешанного кластера: python3 sub.py L 50 6 -> work/sub_L50.png, work/sub_L50.npy"""
import numpy as np, sys
from sklearn.cluster import KMeans
from PIL import Image, ImageDraw
name, k0, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
C = np.load("work/cells.npy"); dark = np.array([(i // 8 + i % 8) % 2 == 1 for i in range(64)])
mask = ~dark if name == "L" else dark
X = C[:, mask].reshape(-1, 1600); lab = np.load(f"work/lab_{name}.npy")
idx = np.where(lab == k0)[0]
km = KMeans(n, n_init=10, random_state=0).fit(X[idx])
np.save(f"work/sub_{name}{k0}.npy", np.stack([idx, km.labels_]))
sheet = Image.new("L", (n * 110, 125), 255); dr = ImageDraw.Draw(sheet)
for j in range(n):
    im = Image.fromarray((255 - km.cluster_centers_[j].reshape(40, 40) * 255).clip(0, 255).astype(np.uint8)).resize((96, 96), Image.NEAREST)
    sheet.paste(im, (j * 110 + 7, 20)); dr.text((j * 110 + 7, 4), f"{j} n={(km.labels_ == j).sum()}", fill=0)
sheet.save(f"work/sub_{name}{k0}.png")
