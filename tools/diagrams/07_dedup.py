"""Шаг 7. Сверка с тем, что уже есть на сайте.

Ключ сравнения — РАССТАНОВКА плюс ОЧЕРЕДЬ ХОДА. Рокировки и счётчики у
разных сборников проставлены по-разному, по полному FEN одна и та же
позиция разошлась бы из-за служебных полей.

Совпадения здесь работают ещё и проверкой: FEN на сайте получены из
книжного текста другим пайплайном. Если наша расстановка сошлась с
тамошней, а очередь хода — с тамошней очередью, значит и распознавание
картинки, и правило «перевёрнута -> ход чёрных» верны.
"""
import os, re, json, collections

W = os.path.dirname(os.path.abspath(__file__))
APP = "/Users/vadimsamalo/Documents/kombinatorika/app.js"

src = open(APP, encoding="utf8").read()
site = collections.defaultdict(list)
for m in re.finditer(r'"n":(\d+),(?:"t":"(?:[^"\\]|\\.)*",)?"f":"([^" ]+) (\w)', src):
    site[m.group(2)].append((int(m.group(1)), m.group(3)))
print("позиций на сайте:", sum(len(v) for v in site.values()),
      "| уникальных расстановок:", len(site))

recs = json.load(open(os.path.join(W, "positions.json")))
seen, dup_site, dup_inside, keep, side_clash = {}, [], [], [], []
for r in recs:
    pl = r["pl"]
    if pl in site:
        their = site[pl][0]
        dup_site.append((r["n"], their[0], r["s"], their[1]))
        if r["s"] != their[1]: side_clash.append((r["n"], r["s"], their[1]))
    elif pl in seen:
        dup_inside.append((r["n"], seen[pl]))
    else:
        seen[pl] = r["n"]; keep.append(r)

print("\nсовпало с сайтом:", len(dup_site))
for n, sn, s, ss in dup_site:
    mark = "ход совпал" if s == ss else "!!! ХОД РАЗОШЁЛСЯ"
    print(f"  №{n} = сайт №{sn}: наш ход {s}, там {ss} — {mark}")
print("\nдублей внутри пачки:", len(dup_inside))
for n, first in dup_inside[:40]: print(f"  №{n} — повтор №{first}")
print("остаётся новых:", len(keep))
if side_clash: print("РАСХОЖДЕНИЯ ПО ОЧЕРЕДИ ХОДА:", side_clash)
json.dump(keep, open(os.path.join(W, "keep.json"), "w"))
