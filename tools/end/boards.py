"""Доски книги двух видов:
  1) шрифт Chess-Merida — FEN прямо из кодов символов (fen_of в extract.py);
  2) те же доски, переведённые в кривые: на горизонталь один залитый контур
     (штриховка + фигуры). Их клетки рисуем в картинку и сравниваем с
     эталонами, снятыми с досок первого вида (фигура там известна точно).
Эталоны: tmpl.npz (build_templates)."""
import numpy as np, pymupdf, os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
OFF = 0.0
S = 14                      # клетка -> S x S

def cell_img(page, r, dpi=200):
    pix = page.get_pixmap(clip=r, dpi=dpi, colorspace=pymupdf.csGRAY)
    im = Image.frombytes("L", (pix.width, pix.height), pix.samples).resize((S, S), Image.BOX)
    return 1 - np.asarray(im, dtype=np.float32) / 255

def vector_boards(page):
    """рамки досок-кривых: 10 залитых контуров подряд одной ширины —
       верхняя линия, 8 горизонталей, нижняя линия"""
    dr = [x for x in page.get_drawings() if x["type"] == "f" and x["rect"].width > 90]
    dr.sort(key=lambda x: (round(x["rect"].x0 / 10), x["rect"].y0))     # бывает нарисована снизу вверх
    out, i = [], 0
    while i + 9 < len(dr):
        g = dr[i:i + 10]
        r0 = g[0]["rect"]
        if r0.height < 2 and g[9]["rect"].height < 2 and all(abs(x["rect"].x0 - r0.x0) < 1.5 and abs(x["rect"].x1 - r0.x1) < 1.5 for x in g) \
           and all(8 < x["rect"].height < 25 for x in g[1:9]) \
           and all(g[k]["rect"].y0 < g[k + 1]["rect"].y0 for k in range(9)):
            ranks = [x["rect"] for x in g[1:9]]
            out.append({"bb": [r0.x0, r0.y0, r0.x1, g[9]["rect"].y1], "ranks": ranks})
            i += 10
        else: i += 1
    return out

def vector_cells(page, vb):
    x0, x1 = vb["bb"][0], vb["bb"][2]
    # боковые линии рамки: по 1/10 ширины клетки у краёв
    w = (x1 - x0)
    cw = w / 8.1
    xl = x0 + (w - 8 * cw) / 2
    cells = []
    for r in vb["ranks"]:
        for f in range(8):
            cells.append(cell_img(page, pymupdf.Rect(xl + f * cw, r.y0, xl + (f + 1) * cw, r.y1)))
    return np.stack(cells)

def font_cells(page, rows):
    """rows: 8 спанов rawdict горизонталей (с символами) -> 64 клетки"""
    cells = []
    for sp in rows:
        ch = sp["chars"]
        for f in range(1, 9):
            b = ch[f]["bbox"]; oy = ch[f]["origin"][1]
            # клетка — квадрат ширины символа, стоит на базовой линии
            h = b[2] - b[0]
            cells.append(cell_img(page, pymupdf.Rect(b[0], oy - h + OFF * h, b[2], oy + OFF * h)))
    return np.stack(cells)

DPI = 400
SHIFT = False          # подбирать сдвиг сетки (для досок-кривых)
def board_cells(page, bb):
    """единый способ для обоих видов досок: рисуем доску, находим рамку по
       тёмным строкам/столбцам, делим внутренность на 8x8"""
    pad = 6
    r = pymupdf.Rect(bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad)
    pix = page.get_pixmap(clip=r, dpi=DPI, colorspace=pymupdf.csGRAY)
    a = 1 - np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).astype(np.float32) / 255
    ink = a > .5
    H, W = ink.shape
    rows = ink.mean(1); cols = ink.mean(0)
    def edges(prof, n):
        idx = np.where(prof > .7)[0]
        lo = idx[idx < n * .2]; hi = idx[idx > n * .8]
        return (lo.max() + 1 if len(lo) else 0), (hi.min() if len(hi) else n)
    y0, y1 = edges(rows, H); x0, x1 = edges(cols, W)
    ch, cw = (y1 - y0) / 8, (x1 - x0) / 8
    def grid(dx, dy):
        out = []
        for i in range(8):
            for j in range(8):
                c = a[int(y0 + dy + i * ch + ch * .06):int(y0 + dy + (i + 1) * ch - ch * .06),
                      int(x0 + dx + j * cw + cw * .06):int(x0 + dx + (j + 1) * cw - cw * .06)]
                im = Image.fromarray((c * 255).astype(np.uint8)).resize((S, S), Image.BOX)
                out.append(np.asarray(im, dtype=np.float32) / 255)
        return np.stack(out)
    if not SHIFT: return grid(0, 0), (x1 - x0) / (y1 - y0)
    best = min(((classify(grid(dx, dy))[2], dx, dy) for dx in range(-4, 5, 2) for dy in range(-4, 5, 2)))
    return grid(best[1], best[2]), (x1 - x0) / (y1 - y0)

_T = None
def classify(cells):
    """64 клетки -> (расстановка FEN, худшее расстояние, сумма); цвет поля известен.
       Эталоны — tmpl.npz (build_templates ниже)"""
    global _T
    if _T is None:
        z = np.load(os.path.join(HERE, "tmpl.npz")); _T = (list(z["cls"]), z["T"])
    cls, T = _T
    v = cells.reshape(64, -1)
    dd = ((v[:, None, :] - T[None]) ** 2).sum(-1)
    out, worst, tot = [], 0, 0
    for i in range(64):
        col = "LD"[(i // 8 + i % 8) % 2]
        k = min((j for j, c in enumerate(cls) if c[1] == col), key=lambda j: dd[i, j])
        out.append(cls[k][0]); worst = max(worst, dd[i, k]); tot += dd[i, k]
    rows = []
    for r in range(8):
        s, e = "", 0
        for x in out[r * 8:r * 8 + 8]:
            if x == ".": e += 1; continue
            if e: s += str(e); e = 0
            s += x
        rows.append(s + (str(e) if e else ""))
    return "/".join(rows), float(worst), float(tot)


def build_templates():
    """tmpl.npz: средняя клетка каждого класса «фигура + цвет поля» с шрифтовых досок
       (фигура там известна точно), плюс то, чего у шрифтовых нет: чёрная ладья на
       тёмном поле (в шрифте другой рисунок; кластеры клеток досок-кривых, подписаны
       глазами) и точка-пометка на пустом поле (диаграмма 1-2, стр. 16).
       Так и собирались — запуск: python3 -c "import boards; boards.build_templates()" """
    import extract as E
    d = pymupdf.open(E.PDF)
    X, Y = [], []
    for pn in range(15, 441):
        pg = d[pn]
        for o in E.page_objects(pn, pg, False):
            if o["kind"] != "diag" or "vec" in o["dg"]: continue
            c, _ = board_cells(pg, o["dg"]["bb"]); sq = []
            for row in o["dg"]["fen"].split("/"):
                for ch in row: sq += ["."] * int(ch) if ch.isdigit() else [ch]
            for i in range(64): X.append(c[i].ravel()); Y.append(sq[i] + "LD"[(i // 8 + i % 8) % 2])
    X, Y = np.stack(X), np.array(Y)
    cls = sorted(set(Y)); T = [X[Y == c].mean(0) for c in cls]
    # чёрная ладья на тёмном поле: клетки досок-кривых, далёкие от всех эталонов
    odd = []
    for pn in range(15, 441):
        pg = d[pn]
        for vb in vector_boards(pg):
            c, _ = board_cells(pg, vb["bb"]); v = c.reshape(64, -1)
            dd = ((v[:, None, :] - np.stack(T)[None]) ** 2).sum(-1)
            for i in range(64):
                if (i // 8 + i % 8) % 2 and min(dd[i, j] for j, cc in enumerate(cls) if cc[1] == "D") > 2: odd.append(v[i])
    from sklearn.cluster import KMeans
    km = KMeans(16, n_init=10, random_state=0).fit(np.stack(odd))
    for k in (1, 4, 10):               # подписано глазами по листу центров кластеров
        cls.append("rD"); T.append(km.cluster_centers_[k])
    pg = d[16]; c, _ = board_cells(pg, vector_boards(pg)[0]["bb"]); v = c.reshape(64, -1)
    cls += [".L", ".D"]; T += [v[[9, 16, 18]].mean(0), v[[8, 10]].mean(0)]
    np.savez_compressed(os.path.join(HERE, "tmpl.npz"), cls=np.array(cls), T=np.stack(T).astype(np.float32))
