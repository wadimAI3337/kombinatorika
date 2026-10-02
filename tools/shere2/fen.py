"""Печать FEN досок страниц: python3 fen.py 6 11"""
import json, sys
a, b = int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else int(sys.argv[1])
bj = json.load(open("work/boards.json")); F = {(r["p"], r["k"]): r["fen"] for r in json.load(open("work/fens.json"))}
for p in range(a, b + 1):
    for k, bb in enumerate(bj.get(str(p), [])):
        print(p, k, bb[2], F.get((p, k), "—"))
