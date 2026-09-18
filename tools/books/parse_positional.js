/* ============================================================
   parse_positional.js — формат «Позиционная игра»:
   заголовок задачи, строка «Ход белых · ход N», FEN в ``` и
   абзац «**Решение.** …» с ключевым ходом в начале.

   Запуск: node parse_positional.js level1.md pos1.json
   ============================================================ */
const fs = require('fs');
const { extractLine } = require('./lib_line');

const [, , SRC, OUT] = process.argv;
if (!SRC || !OUT) { console.error('node parse_positional.js <книга.md> <выход.json>'); process.exit(1); }

const raw = fs.readFileSync(SRC, 'utf8');
const blocks = raw.split(/\n(?=## \d+\. )/).slice(1);   // задачи начинаются с «## 12. Партия»
const out = [];

for (const b of blocks) {
  const head = b.match(/^## (\d+)\. (.+)/);
  const side = b.match(/\*\*Ход (белых|чёрных)\*\* · ход (\d+)/);
  const fen  = b.match(/```\n([^\n]+)\n```/);
  if (!head || !side || !fen) { console.warn('пропущен блок:', b.slice(0, 40)); continue; }

  const rec = {
    n: +head[1],
    t: head[2].trim(),
    f: fen[1].trim(),
    s: side[1] === 'белых' ? 'w' : 'b',
    v: +side[2],
  };
  /* Весь разбор в одну строку — так проще считать смещения комментариев */
  rec.x = b.slice(b.indexOf('**Решение.**') + 12).trim().replace(/\s+/g, ' ');

  const moves = extractLine(rec.f, rec.s, rec.v, rec.x);

  /* Комментарий к ходу — это текст до следующего хода. Храним не
     строкой, а парой смещений в rec.x: файл получается вдвое
     меньше, а на странице note = x.slice(a, b). */
  rec.m = moves.map((mv, i) => {
    let s = mv.end;
    const e = (i + 1 < moves.length) ? moves[i + 1].start : rec.x.length;
    const head = rec.x.slice(s, s + 10);
    const evm = head.match(/^[\s!?+#.,;:]*(\+−|−\+|\+-|-\+|[±∓⩲⩱=÷©ƒ‚„∞])/);
    let ev = '';
    if (evm) { ev = evm[1] === '+-' ? '+−' : evm[1] === '-+' ? '−+' : evm[1]; s += evm[0].length; }
    else { s += head.match(/^[\s!?+#.,;:]*/)[0].length; }
    return [mv.uci, mv.san, mv.fen, [Math.min(s, e), e], ev];
  });
  out.push(rec);
}

fs.writeFileSync(OUT, JSON.stringify(out));
const hist = {};
out.forEach(o => hist[o.m.length] = (hist[o.m.length] || 0) + 1);
console.log('задач:', out.length, '| без решения:', out.filter(o => !o.m.length).map(o => o.n).join(',') || 'нет');
console.log('длина варианта (полуходы):', JSON.stringify(hist));
console.log('файл:', OUT, (fs.statSync(OUT).size / 1024).toFixed(0) + ' KB');
