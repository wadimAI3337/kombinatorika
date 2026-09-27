"""DjVu -> полстраницы PNG для расшифровки (0–53% и 47–100% высоты).
   ddjvu рендерит в pnm; ширина 1400 px — мелкий шрифт читается уверенно."""
import subprocess, sys, os
from PIL import Image
SRC = os.path.expanduser("~/Downloads/Dvoretskiy_M_-_Pomni_o_sopernike_Tom_{}_2013.djvu")
def run(v, a, b):
    out = f"work/v{v}/img"; os.makedirs(out, exist_ok=True)
    for p in range(a, b + 1):
        fa = f"{out}/p{p:03d}a.png"
        if os.path.exists(fa): continue
        tmp = f"work/v{v}/tmp.pnm"
        subprocess.run(["ddjvu", "-format=pnm", f"-page={p}", "-size=1400x2200", SRC.format(v), tmp], check=True)
        im = Image.open(tmp).convert("L"); W, H = im.size
        im.crop((0, 0, W, int(H * .53))).save(fa)
        im.crop((0, int(H * .47), W, H)).save(f"{out}/p{p:03d}b.png")
if __name__ == "__main__":
    run(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
