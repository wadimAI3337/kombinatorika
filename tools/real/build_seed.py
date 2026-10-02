#!/usr/bin/env python3
"""
Стартовый набор «Реализации перевеса» — 30 партий из 11-го урока
«Терминатора» (Крамник, Фишер, Карпов). Позиция для тренировки —
та, что выбрал тренер (длина тренировочной главы в студии), рядом
сохраняется точка, которую нашёл бы алгоритм, — для сверки.

  python3 tools/real/build_seed.py            # → real-seed.js в корне сайта
  python3 tools/real/build_seed.py --depth1 12 --depth2 16   # быстрее

Ходы студии лежат в tools/real/data/terminator11.json (лист студии
lichess.org/study/CLxLSsob: автор закрыл скачивание PGN, поэтому ходы
сняты со страницы по главам).
"""
import argparse, json, os, re, sys
from multiprocessing import Pool

import chess

sys.path.insert(0, os.path.dirname(__file__))
from scan import analyse_game, find_point  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GROUP = {"Крамник": "Крамник", "Фишер": "Фишер", "Карпов": "Карпов"}


def clean(name):
    return re.sub(r"\s*\(\d+\)\s*$", "", name.strip())


def job_of(g, a):
    sans = g["m"].split()
    w, b = [clean(x) for x in g["full"].split(" - ", 1)]
    hero = "w" if g["res"] == "1-0" else "b"
    k = g["k"]
    # если у тренера в позиции ход соперника — даём ему сделать ход из партии
    stm_white = k % 2 == 0
    if stm_white != (hero == "w"):
        k += 1
    return {"sans": sans, "start": chess.STARTING_FEN,
            "headers": {"White": w, "Black": b, "Result": g["res"], "Event": "", "Date": g["t"][-4:]},
            "hero": hero, "depth1": a.depth1, "depth2": a.depth2, "thresh": 200, "coach": k,
            "_n": g["n"], "_t": g["t"]}


def run(job):
    r = analyse_game(job)
    r["n"], r["title"] = job["_n"], job["_t"]
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth1", type=int, default=14)
    ap.add_argument("--depth2", type=int, default=18)
    ap.add_argument("-j", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    a = ap.parse_args()
    src = json.load(open(os.path.join(os.path.dirname(__file__), "data", "terminator11.json"), encoding="utf-8"))
    jobs = [job_of(g, a) for g in src]
    with Pool(a.j) as p:
        res = sorted(p.map(run, jobs), key=lambda r: r["n"])

    out = []
    print(f"{'№':>3} {'партия':28} {'тренер':>6} {'алгоритм':>9} {'оценка':>7}  вердикт")
    for r in res:
        sgn = 1 if r["hero"] == "w" else -1
        kc = r["coach"]
        title = r["title"]
        hero_name = next((v for kk, v in GROUP.items() if kk in title), "")
        print(f"{r['n']:>3} {title[:28]:28} {kc//2+1:>6} {(r['k']//2+1) if r['k'] is not None else '—':>9} "
              f"{r['ev'][kc]*sgn/100:>+7.2f}  {r['verdict']} {' '.join(r['flags'])}")
        year = (re.search(r"(\d{4})$", title) or [None, ""])[1]
        out.append({
            "pid": "t%02d" % r["n"], "n": r["n"], "group": hero_name,
            "title": re.sub(r"\s*\d{4}$", "", title).replace(" - ", " – "), "year": year,
            "white": r["white"], "black": r["black"], "result": r["result"], "hero": r["hero"],
            "sans": r["sans"], "k": kc, "ka": r["k"], "verdict": r["verdict"], "flags": r["flags"],
            "ev": r["ev"], "tags": r.get("tags", []), "pv": r.get("pv", []),
        })
    js = ("/* Стартовый набор «Реализации перевеса»: 30 партий 11-го урока «Терминатора».\n"
          "   Собрано tools/real/build_seed.py — руками не править. */\n"
          "window.REAL_SEED = " + json.dumps({"v": 1, "col": "Терминатор · урок 11", "games": out},
                                              ensure_ascii=False, separators=(",", ":")) + ";\n")
    with open(os.path.join(ROOT, "real-seed.js"), "w", encoding="utf-8") as f:
        f.write(js)
    print(f"\nreal-seed.js: {len(out)} партий, {len(js)//1024} КБ")


if __name__ == "__main__":
    main()
