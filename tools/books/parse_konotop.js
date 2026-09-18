/* ============================================================
   parse_konotop.js — формат «Конотоп. Тесты по тактике»:
   в тесте 12 позиций (FEN + «Ход чёрных · 2 очка»), ответы идут
   отдельным разделом и написаны русской нотацией: взятие через
   двоеточие (R:f3), пешечные взятия сокращённо (gh, bc),
   превращение без «=» (a1Q), ход чёрных как «1. ... Nd4».

   Главная сложность: автор сначала перебирает и отбраковывает
   ходы-кандидаты, а решение даёт в конце. Поэтому «первый ход в
   тексте» не годится — кандидаты оцениваются (см. pickMove).

   Запуск: node parse_konotop.js kon.json tests1.md tests2.md ...
   ============================================================ */
const fs = require('fs');
const { Chess } = require('chess.js');
const { extractLine, doMove, SAN_CORE } = require('./lib_line');

const [, , OUT, ...FILES] = process.argv;
if (!OUT || !FILES.length) { console.error('node parse_konotop.js <выход.json> <файлы.md...>'); process.exit(1); }

/* --- 1. Нотация книги -> нотация chess.js --------------------
   Порядок замен важен: сначала «1. ...», иначе точка после
   номера склеится с русским словом («B:f4. Нападение»). */
function norm(t) {
  return t
    .replace(/(\d+)\s*\.\s*\.\.\.\s*/g, '$1...')
    .replace(/(\d+)\s+\.\.\.\s*/g, '$1...')
    .replace(/(\d+)\.\.\.\s+/g, '$1...')
    .replace(/(\d+)\.\s+(?=[KQRBNa-h])/g, '$1.')      // только перед ходом, не перед словом
    .replace(/([KQRBN][a-h1-8]?)\s*:\s*([a-h][1-8])/g, '$1x$2')   // R1:d4, Nc:d5
    .replace(/([a-h][1-8])\s*:\s*([a-h][1-8])/g, '$1x$2')
    .replace(/\b([a-h])\s*:\s*([a-h][1-8])/g, '$1x$2')
    .replace(/0-0-0/g, 'O-O-O').replace(/0-0/g, 'O-O');
}

/* --- 2. Кандидаты на первый ход ------------------------------
   Берём только токены ВНЕ скобок: то, что в скобках, — побочный
   вариант, там решения не бывает. */
function candidates(fen, side, text) {
  const re = new RegExp('\\b1' + (side === 'w' ? '\\.(?!\\.)' : '\\.\\.\\.') + '(' + SAN_CORE + ')([!?]{0,2})', 'g');
  const out = []; let m;
  while ((m = re.exec(text))) {
    const pre = text.slice(0, m.index);
    if ((pre.split('(').length - 1) - (pre.split(')').length - 1) > 0) continue;
    const ch = new Chess(); ch.load(fen);
    const r = doMove(ch, m[1]);
    if (r) out.push({ san: r.san, ann: m[2] || '', at: m.index });
  }
  return out;
}

/* --- 3. Выбор решения среди кандидатов -----------------------
   Знак автора весит больше всего: «!» — это и есть решение,
   «?» — то, что опровергают. Дальше смотрим на фразу перед
   ходом и на то, чем заканчивается вариант. */
const BAD  = /(Попытк|попытк|ничего не да|не спаса|обречен|неудач|нельзя|ошибочн|плохо|проигрыва|ведет к ничьей|ведёт к ничьей|половинчат|не годится|слабее|хуже|опроверга|наталкивается|в случае|В случае|Если|если|Не проходит|не проходит|напрашива|прямолинейн|жет показаться|ошибк)/;
const GOOD = /(правильн|решает|выигрывает|сильнейш|единственн|необходимо|следует играть|решение|нашли, как|могли сыграть|гораздо сильнее|значительно сильнее|намного сильнее)/;
const WIN  = /(сдал|1-0|0-1|выигрыв|выигр|\+-|-\+|#|мат)/;

function pickMove(fen, side, text) {
  const cands = candidates(fen, side, text);
  let best = -1e9, pick = null, line = [];
  cands.forEach((c, ci) => {
    const l = extractLine(fen, side, 1, text, { startAt: c.at });
    if (!l.length) return;
    let sc = l.length * 1.5 + ci * 2;                 // длиннее и позже — чуть лучше
    if (c.ann.includes('!!')) sc += 34; else if (c.ann.includes('!')) sc += 26;
    if (c.ann.includes('?')) sc -= 60;
    if (l[l.length - 1].san.endsWith('#')) sc += 12;  // вариант кончается матом
    const seg = text.slice(Math.max(0, c.at - 140), c.at).split(/[.!?] /).pop();
    if (BAD.test(seg)) sc -= 32;
    if (GOOD.test(seg)) sc += 12;
    const after = text.slice(l[l.length - 1].end, l[l.length - 1].end + 160);
    if (WIN.test(after)) sc += 12;                    // после варианта сдались
    if (sc > best) { best = sc; pick = c; line = l; }
  });
  return { pick, line, cands };
}

/* --- 4. Разбор файлов --------------------------------------- */
const out = [];
for (const f of FILES) {
  const raw = fs.readFileSync(f, 'utf8');
  for (const t of raw.split(/\n(?=## ТЕСТ №\d+)/).slice(1)) {
    const tn = +t.match(/## ТЕСТ №(\d+)/)[1];
    const posPart = t.slice(t.indexOf('### Позиции'), t.indexOf('### Ответы'));
    const ansPart = t.slice(t.indexOf('### Ответы'));
    const positions = [...posPart.matchAll(/\*\*№(\d+)\. Ход (белых|чёрных)\*\* · (\d) очк[а-я]*\s*\n+```\n([^\n]+)\n```/g)]
      .map(m => ({ i: +m[1], s: m[2] === 'белых' ? 'w' : 'b', pts: +m[3], fen: m[4].trim() }));
    const answers = [...ansPart.matchAll(/\*\*№(\d+)\.\s*([^*]*?)\*\*\s*—\s*(\d) очк[а-я]*\s*\n+([\s\S]*?)(?=\n\*\*№\d+\.|\n## |$)/g)]
      .map(m => ({ i: +m[1], title: m[2].trim(), text: m[4].trim().replace(/\s+/g, ' ') }));

    for (const p of positions) {
      const a = answers.find(x => x.i === p.i) || { title: '', text: '' };
      const x = norm(a.text);
      const { line, cands } = pickMove(p.fen, p.s, x);
      const rec = { n: (tn - 1) * 12 + p.i, t: a.title, f: p.fen, s: p.s, v: 1, pts: p.pts, tt: tn, x, m: [] };
      rec.m = line.map((mv, i) => {
        let s = mv.end;
        const e = (i + 1 < line.length) ? line[i + 1].start : x.length;
        const head = x.slice(s, s + 10);
        const evm = head.match(/^[\s!?+#.,;:]*(\+-|-\+|[±∓∞=])/);
        let ev = '';
        if (evm) { ev = evm[1] === '+-' ? '+−' : evm[1] === '-+' ? '−+' : evm[1]; s += evm[0].length; }
        else { s += head.match(/^[\s!?+#.,;:]*/)[0].length; }
        return [mv.uci, mv.san, mv.fen, [Math.min(s, e), e], ev];
      });
      rec._cands = cands.map(c => c.san + c.ann);
      out.push(rec);
    }
  }
}
out.sort((a, b) => a.n - b.n);

/* Диагностика: где выбор мог уехать. Эти задачи стоит глазами
   сверить с книгой — их обычно единицы. */
const susp = out.filter(o => {
  const bang = o._cands.filter(c => c.includes('!')).map(c => c.replace(/[!?]+$/, ''));
  return o.m.length && bang.length && !bang.includes(o.m[0][1].replace(/[!?]+$/, ''));
});
console.log('позиций:', out.length, '| без решения:', out.filter(o => !o.m.length).map(o => o.n).join(',') || 'нет');
console.log('многокандидатных:', out.filter(o => o._cands.length > 1).length,
            '| выбран не ход с «!»:', susp.map(o => o.n).join(',') || 'нет');
out.forEach(o => delete o._cands);
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('файл:', OUT, (fs.statSync(OUT).size / 1024).toFixed(0) + ' KB');
