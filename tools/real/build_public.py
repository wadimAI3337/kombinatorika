"""Общие подборки по FEN: public_fens.json -> real-public.js (оценку считает Stockfish).
Запуск: python3 tools/real/build_public.py"""
import json, subprocess, os
here = os.path.dirname(os.path.abspath(__file__))
src = json.load(open(os.path.join(here, "public_fens.json"), encoding="utf-8"))

def evaluate(fen):
    p = subprocess.Popen(["stockfish"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    p.stdin.write(f"uci\nposition fen {fen}\ngo depth 16\n"); p.stdin.flush()
    cp = 0
    for line in p.stdout:
        if line.startswith("info") and " score " in line and " pv " in line:
            t = line.split()
            i = t.index("score")
            cp = int(t[i + 2]) if t[i + 1] == "cp" else (30000 - abs(int(t[i + 2]))) * (1 if int(t[i + 2]) > 0 else -1)
        if line.startswith("bestmove"):
            break
    p.stdin.write("quit\n"); p.stdin.flush(); p.wait()
    return cp if fen.split()[1] == "w" else -cp

games = []
for col, lst in src.items():
    for i, x in enumerate(lst, 1):
        games.append({"pid": f"pub-{col}-{i}", "group": col, "title": x["title"], "fen": x["fen"], "ev": evaluate(x["fen"])})
open(os.path.join(here, "..", "..", "real-public.js"), "w", encoding="utf-8").write(
    "/* Общие подборки по FEN — собрано tools/real/build_public.py, руками не править. */\nwindow.REAL_PUBLIC = " + json.dumps(games, ensure_ascii=False) + ";\n")
print(games)
