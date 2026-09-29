"""DjVu -> полстраницы PNG для расшифровки (0–53% и 47–100% высоты, ширина 1400)
   и страница целиком 600 dpi для поиска досок (work/full).
   Номер файла = номер страницы DjVu (печатный номер на 1 меньше).
   Текст книги — страницы 4–379, дальше оглавление."""
import subprocess, sys, os
from PIL import Image
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../Yakovlev_-_Shakhmaty_Plan_v_mittelshpile_2014.djvu")
os.makedirs("work/img", exist_ok=True); os.makedirs("work/full", exist_ok=True)
a, b = int(sys.argv[1]), int(sys.argv[2])
for p in range(a, b + 1):
    if os.path.exists(f"work/img/p{p:03d}b.png"): continue
    tmp = f"work/tmp{p}.pbm"
    subprocess.run(["ddjvu", "-format=pbm", f"-page={p}", SRC, tmp], check=True)
    im = Image.open(tmp).convert("L"); os.remove(tmp)
    im.save(f"work/full/p{p:03d}.png")
    W, H = im.size
    sm = im.resize((1400, int(H * 1400 / W)), Image.LANCZOS)
    w, h = sm.size
    sm.crop((0, 0, w, int(h * .53))).save(f"work/img/p{p:03d}a.png")
    sm.crop((0, int(h * .47), w, h)).save(f"work/img/p{p:03d}b.png")
