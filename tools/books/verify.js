/* ============================================================
   verify.js — приёмка данных. Два уровня:

   1) без движка: каждый ход варианта проигрывается на доске из
      своего FEN. Ловит битые FEN, сбитую нумерацию, ход не той
      стороны. Это обязательный прогон после любой правки.

   2) с движком (--sf, нужен stockfish в PATH): первый ход
      сверяется с лучшим ходом Stockfish. Это НЕ источник истины
      (в тактике часто выигрывает несколько ходов, а книга даёт
      поучительный), а сито: расхождения показывают, где парсер
      мог зацепить не тот вариант.

   Запуск: node verify.js pos1.json [--sf] [--depth 16]
   ============================================================ */
const fs = require('fs');
const { Chess } = require('chess.js');

const args = process.argv.slice(2);
const FILE = args[0];
const USE_SF = args.includes('--sf');
const DEPTH = +((args[args.indexOf('--depth') + 1]) || 16);
const data = JSON.parse(fs.readFileSync(FILE, 'utf8'));

let plies = 0; const bad = [];
for (const q of data) {
  if (!q.m || !q.m.length) { bad.push(q.n + ': пустой вариант'); continue; }
  const ch = new Chess();
  try { ch.load(q.f); } catch (e) { bad.push(q.n + ': битый FEN'); continue; }
  if (ch.fen().split(' ')[1] !== q.s) bad.push(q.n + ': сторона хода не совпала с FEN');
  for (const mv of q.m) {
    plies++;
    let r = null;
    try { r = ch.move({ from: mv[0].slice(0, 2), to: mv[0].slice(2, 4), promotion: mv[0][4] || undefined }); } catch (e) {}
    if (!r) { bad.push(q.n + ': нелегальный ход ' + mv[1]); break; }
    if (r.san !== mv[1]) bad.push(q.n + ': запись ' + mv[1] + ' вместо ' + r.san);
    if (ch.fen() !== mv[2]) bad.push(q.n + ': FEN после ' + mv[1] + ' не совпал');
  }
}
console.log('задач:', data.length, '| ходов проверено:', plies, '| замечаний:', bad.length);
if (bad.length) console.log(bad.slice(0, 20).join('\n'));

if (!USE_SF) process.exit(bad.length ? 1 : 0);

/* --- сверка первого хода с движком --- */
const { spawn } = require('child_process');
function engine() {
  const p = spawn(process.env.SF_PATH || 'stockfish');
  let buf = '', waiter = null;
  p.stdout.on('data', d => {
    buf += d.toString(); let i;
    while ((i = buf.indexOf('\n')) >= 0) { const l = buf.slice(0, i).trim(); buf = buf.slice(i + 1); if (waiter) waiter(l); }
  });
  const send = s => p.stdin.write(s + '\n');
  const until = pred => new Promise(res => { const all = []; waiter = l => { all.push(l); const r = pred(l, all); if (r !== undefined && r !== false) { waiter = null; res(r); } }; });
  return {
    async init() { send('uci'); await until(l => l === 'uciok' || undefined); send('setoption name Threads value 2'); send('isready'); await until(l => l === 'readyok' || undefined); },
    async best(fen) { send('position fen ' + fen); send('go depth ' + DEPTH); return until(l => l.startsWith('bestmove') ? l.split(' ')[1] : undefined); },
    quit() { send('quit'); p.kill(); }
  };
}
(async () => {
  const N = 4, eng = [];
  for (let i = 0; i < N; i++) { const e = engine(); await e.init(); eng.push(e); }
  let next = 0, agree = 0; const dis = [];
  await Promise.all(eng.map(async e => {
    while (true) {
      const i = next++; if (i >= data.length) break;
      const q = data[i]; if (!q.m || !q.m.length) continue;
      const b = await e.best(q.f);
      if (b && b.slice(0, 4) === q.m[0][0].slice(0, 4)) agree++;
      else dis.push('№' + q.n + ' книга ' + q.m[0][1] + ' / движок ' + b);
    }
  }));
  eng.forEach(e => e.quit());
  console.log('\nсовпало с движком:', agree, 'из', data.length, '(' + (100 * agree / data.length).toFixed(1) + '%)');
  console.log('расхождения (просмотреть глазами):');
  console.log(dis.slice(0, 40).join('\n'));
})();
