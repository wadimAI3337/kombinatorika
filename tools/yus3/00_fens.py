"""FEN-файл от владельца книги (work/fen.md, 578 позиций с подписями) -> work/fens_by_label.json.
   Поправки: опечатки подписей и позиции, которых в файле нет или которые записаны неверно
   (сняты с картинок страниц вручную)."""
import re, json, chess
RENAME = {"Ex. 15-24": "Ex. 15-2", "Diagram 22-20": "Diagram 22-2", "Ex. 25-7": "Ex. 23-7"}
ADD = {   # подпись -> FEN (страница PDF)
    "Diagram 3-1": "rnq1br2/ppp2pbk/6pp/8/2B1N3/5N2/PPPQ1PPP/3RR1K1 w - - 0 1",      # стр. 31
    "Ex. 1-11": "8/2QR3p/3p1rpk/2bPp3/4P3/6P1/6BP/q5NK w - - 0 1",                   # стр. 16
    "Diagram 17-2": "r2q2k1/p2r1pb1/1p2p1p1/3bPnN1/3PB1Q1/P3B3/5PP1/3R1RK1 w - - 0 1", # стр. 185
    "Ex. 18-7": "rnb4r/pp3kpp/2p2qn1/2B1pp2/2P5/5PP1/PP1QBN1P/2KR3R w - - 0 1",      # стр. 207
    "Ex. 18-9": "r1b2rk1/1p2q1pp/pB1ppp2/Q3nn2/2P5/2N5/PP3PPP/2KR1B1R w - - 0 1",    # стр. 207
}
out = {}
for l in open("work/fen.md", encoding="utf-8"):
    m = re.match(r"\|\s*\d+\s*\|\s*([^|]*?)\s*\|\s*(\d+)\s*\|\s*[^|]*?\|\s*`([^`]+)`", l)
    if not m: continue
    lab, p, fen = m.groups()
    lab = RENAME.get(lab, lab)
    out[lab] = {"fen": fen, "p": int(p)}
for lab, fen in ADD.items(): out[lab] = {"fen": fen, "p": None}
key = lambda s: ("F" if s.startswith("F") else "EX" if s.startswith("Ex") else "D") + " " + re.search(r"(F-\d+|\d+-\d+)", s).group(1)
res = {key(k): v for k, v in out.items()}
bad = [k for k, v in res.items() if not chess.Board(v["fen"]).is_valid()]
print(len(res), "позиций; некорректных:", bad)
json.dump(res, open("work/fens_by_label.json", "w"), ensure_ascii=False, indent=0)
