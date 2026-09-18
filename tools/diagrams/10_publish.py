"""Шаг 10. Заливка сборников на сайт (app.js).

Формат записи — как у сборников комбинаций (DATA.b1700), а не как у
позиционных книг: у диаграмм нет ни названия партии, ни книжного
текста разбора, и сборник без `kind:"pos"` их и не запрашивает
(`renderPos` выходит сразу, если книга не позиционная).

Задача: {"n":1,"f":FEN,"s":"w","m":[[uci,san,FEN после], ...]}

Нумерация внутри сборника сквозная с 1: на странице стоит
«Задача №N», и номера файлов 321–640 там смотрелись бы странно.
Исходный файл сохраняем в поле `src` — оно сайту не нужно, но по нему
всегда можно вернуться к картинке.
"""
import os, json, re

W = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(W, "..", "..", "app.js")

BOOKS = [
    ("STEP1", "step1", "1 ступень (3-1 разряд)",   1, 320),
    ("STEP2", "step2", "2 ступень (2 разряд-КМС)", 321, 640),
]
MARK = "/* ===== Шахматная терапия · урок 12 ===== */"

# Разделы. Штатный SECS() делит задачи на 2/3/4+ хода, и задача из
# ОДНОГО хода не попадает ни в один раздел — а значит на сайт не
# попадает вовсе: разделы фильтруются, и пустые выкидываются.
# В книгах комбинаций одноходовок-не-матов нет, поэтому там это не
# всплывало. Здесь они есть, и их много: тихий ход, после которого у
# соперника свободный выбор, — это и есть весь ответ. Даём им раздел.
SECS_JS = """const STEPSECS = () => ([
  {id:"mate",  t:"Матовые атаки", s:"Комбинация кончается матом",        f:isMate},
  {id:"one",   t:"В один ход",    s:"Один ход — и всё; обычно тихий",    f:p => plies(p) === 1},
  {id:"two",   t:"В два хода",    s:"Два хода решающей стороны",         f:p => plies(p) === 2},
  {id:"three", t:"В три хода",    s:"Три хода решающей стороны",         f:p => plies(p) === 3},
  {id:"long",  t:"Длинные",       s:"Четыре хода и больше",              f:p => plies(p) >= 4},
  {id:"black", t:"За чёрных",     s:"Начинают чёрные",                   f:p => p.s === "b"},
]);"""

solved = json.load(open(os.path.join(W, "solved.json")))
by_n = {r["n"]: r for r in solved}

src = open(APP, encoding="utf8").read()
if MARK in src:
    raise SystemExit("сборники уже залиты — сначала откатите app.js")

consts, entries, report = [], [], []
for var, bid, title, lo, hi in BOOKS:
    items = [by_n[n] for n in sorted(by_n) if lo <= n <= hi and by_n[n]["m"]]
    recs = []
    for i, r in enumerate(items, 1):
        rec = {"n": i, "src": r["n"], "f": r["f"], "s": r["s"],
               "m": [[u, s, f] for u, s, f, _, _ in r["m"]]}
        if r.get("c"):                      # продолжение «для показа»
            rec["c"] = [[u, s, f] for u, s, f in r["c"]]
        recs.append(rec)
    if not recs:
        raise SystemExit(f"сборник «{title}» пустой — заливать нечего "
                         f"(renderBooks падает на книге без задач)")
    consts.append(f"const {var} = " + json.dumps(recs, ensure_ascii=False, separators=(",", ":")) + ";")
    entries.append(f'  {{ id:"{bid}", title:"{title}", '
                   f'meta:"Шахматная терапия · урок 12 · {len(recs)} позиций", '
                   f'puzzles:{var}, secs:STEPSECS() }}')
    report.append((title, len(recs), sum(1 for r in recs if r["s"] == "b")))

# 1) массивы задач — рядом с остальными сборниками, перед const FILES
anchor = 'const FILES = "abcdefgh";'
src = src.replace(anchor, MARK + "\n" + "\n".join(consts) + "\n" + anchor, 1)

# 2) регистрация — после того, как тесты по тактике встали на своё место
hook = '{ const i = BOOKS.findIndex(b => b.id === "kon2"); if (i > 2) BOOKS.splice(2, 0, BOOKS.splice(i, 1)[0]); }'
src = src.replace(hook, hook + "\n\n" + MARK + "\n" + SECS_JS + "\nBOOKS.push(\n" + ",\n".join(entries) + "\n);", 1)

# --- правка страницы: показать продолжение в разборе ----------------
# Решение и показ лежат в разных полях, поэтому длина задачи и разделы
# не меняются. В разборе показ идёт следом за решением, отдельным
# цветом, а открывается разбор на последнем ходе РЕШЕНИЯ — чтобы
# продолжение человек досмотрел сам стрелкой, а не увидел сразу.
old_open = ('  for (const mv of p.m){ nodes.push({ fen: mv[2], san: mv[1], uci: mv[0], book: true }); f = mv[2]; }\n'
            '  st.an = { nodes, i: nodes.length - 1 };')
new_open = ('  for (const mv of p.m){ nodes.push({ fen: mv[2], san: mv[1], uci: mv[0], book: true }); f = mv[2]; }\n'
            '  for (const mv of (p.c || [])){ nodes.push({ fen: mv[2], san: mv[1], uci: mv[0], book: true, cont: true }); f = mv[2]; }\n'
            '  st.an = { nodes, i: p.m.length };')
if old_open not in src: raise SystemExit("anOpen выглядит не так, как ожидалось — правка не применена")
src = src.replace(old_open, new_open, 1)

old_cls = '"mv" + (i === st.an.i ? " cur" : "") + (n.book ? "" : " own");'
new_cls = '"mv" + (i === st.an.i ? " cur" : "") + (n.book ? "" : " own") + (n.cont ? " cont" : "");'
if old_cls not in src: raise SystemExit("anRender выглядит не так, как ожидалось — правка не применена")
src = src.replace(old_cls, new_cls, 1)

open(APP, "w", encoding="utf8").write(src)

# --- стиль для ходов показа ----------------------------------------
IDX = os.path.join(W, "..", "..", "index.html")
html = open(IDX, encoding="utf8").read()
anchor = ".anmoves .mv.cur{background:var(--accent); color:var(--accent-ink); font-weight:700}"
if ".mv.cont{" not in html:
    if anchor not in html: raise SystemExit("не нашёл стили .anmoves — правка не применена")
    html = html.replace(anchor, anchor +
        "\n.anmoves .mv.cont{background:none; color:var(--ink-3); font-style:italic}"
        "\n.anmoves .mv.cont.cur{background:var(--accent); color:var(--accent-ink); font-style:normal}", 1)
    open(IDX, "w", encoding="utf8").write(html)
for t, n, b in report:
    print(f"  {t}: {n} задач (ход чёрных — {b})")
print("app.js:", round(os.path.getsize(APP) / 1024 / 1024, 2), "MB")
