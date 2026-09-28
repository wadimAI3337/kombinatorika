# Промпт для разметки «Build Up Your Chess 2» (А. Юсупов)

Книга изданная, поэтому авторский текст НЕ переписывается и не переводится.
Переносятся факты — ходы, варианты, оценки, очки, шапки партий, метки
диаграмм — и собственный тренерский комментарий по-русски к тем же ходам и идеям (не перевод). Параллельные
под-агенты, по 7 страниц; страница порезана на половины (`01_pages.py`).

---

You are extracting the CHESS DATA from scanned pages of the English book "Build Up Your
Chess 2" by Artur Yusupov (a copyrighted book, used privately by its owner). Each chapter:
an introduction with diagrams ("Diagram 3-1" …) and commented games, a page "Exercises"
(12 diagrams "Ex. 3-1" …), "Solutions" (answers with points) and a "Scoring" box. At the
end — "Final test" (F-1 …) with solutions.

COPYRIGHT RULE — STRICT: do NOT copy the author's prose, do NOT quote it and do NOT
translate it sentence by sentence. Moves, variations, evaluation symbols, points, player
names, events and diagram labels are facts — copy those exactly.
Instead of the author's prose write YOUR OWN TEACHING COMMENTARY IN RUSSIAN, as a chess coach
explaining the position to a club player (about 1800–2000): for every move and variation the
book gives, explain what it does and why — the threat, the defence it refutes, why the
alternative fails, the plan, the typical pattern to remember. Cover every chess idea the book
covers; you may add your own clarifications (e.g. spell out a short line the book only hints
at, if you are sure of it). Detail level: similar to the book or more — this is for learning,
not a summary. Use your own structure and wording — never follow the author's sentences one by
one, never reuse his phrases or anecdotes. For pure-prose pages (preface, introduction, chapter
openings) write your own Russian explanation of the chess principles the page is about.

WORK FOLDER: /Users/vadimsamalo/Documents/kombinatorika/tools/yus/work
YOUR PAGES: {PAGES}

For every page NNN:
1. Read with the Read tool `img/pNNNa.png` (top) and `img/pNNNb.png` (bottom). The halves
   OVERLAP by ~6% of the height — do not duplicate lines visible in both.
2. Write the result with the Write tool to `txt/pNNN.txt` (skip the page if the file exists).

READING ORDER. Two columns: the whole left column top to bottom, then the right column.
Diagrams go into the flow where they stand.

MARKUP (each marker on its own line):
- Running heads and page numbers — DROP.
- Chapter title page: `[[CHAPTER 3]] <English chapter title as printed>` and
  `[[CONTENTS]] <the small contents list items, in Russian, separated by ;>`.
- Section headings — `[[H]] Exercises` / `Solutions` / `Scoring` / `Final test` / `Preface` / `Introduction` / `Key to symbols used`.
- A diagram drawing — `[[DIAG 3-1 turn=w]]`: label "Diagram 3-1" → `3-1`; "Ex. 3-5" →
  `EX 3-5`; "F-12" → `F-12`. `turn=w` if the triangle at the top right is WHITE (△),
  `turn=b` if BLACK (▼). Exercises add `stars=N` (number of ★). No label → `[[DIAG]]`.
  Do NOT transcribe the pieces.
- The heading "Diagram 3-1" in the text column above a game name — `[[REF 3-1]]`; in Solutions
  "Ex. 3-5" → `[[REF EX 3-5]]`; "F-16" → `[[REF F-16]]`; a line like "Tactics /Chapter 16" → `[[FROM]] Tactics /Chapter 16`.
- Game header (white on black bar + event line) — `[[GAME]] J.Aitken – Keffler | Edinburgh 1954`.
- Points: "(1 point)" → a separate line `[[PTS 1]]`.
- Scoring box: `[[SCORE]] 16; 14; 12; 9` (maximum, excellent, good, pass mark).
- Paragraphs are separated by an empty line. A paragraph = moves exactly as printed +
  your Russian commentary, e.g. `**1.Rc6!! Bxc6** 2.Bh6 g6 3.Qxe5+- — жертва качества вскрывает короля, ферзь и слоны атакуют g7, защиты нет.`
  Keep the moves in the order printed, keep brackets of variations.
- If the page starts in the middle of a move sequence from the previous page — first line `[[CONT]]`.
- BOLD moves (main line) wrap in `**…**`.

CHESS NOTATION — THE MOST IMPORTANT PART:
- Figurines → letters: K Q R B N (outline and solid are the same). Pawns have no letter.
- Squares a1–h8; check every letter and digit against the picture (c/e, b/h, 1/l, 3/8, 5/6).
- Keep: `x` captures, `...` black moves (`2...Qg6`), `0-0` / `0-0-0`, promotion as printed,
  `! ? !! ?? !? ?!`, check (the book prints †) → `+`, `#`, evaluations `+- -+ = ± ∓ ⩲ ⩱ ∞`.
- Every move that appears in the author's text must appear in your file, in the same order.

When done, reply in one line: the files written.
