/* ============================================================
   lib_line.js — извлечение основного варианта из книжной прозы.
   Ядро всей обработки. Не зависит от формата книги: на вход
   даётся FEN, чей ход, номер хода и текст разбора; на выходе —
   список ходов [{uci, san, fen, start, end, ann}].
   Зависимость: chess.js (npm i chess.js)
   ============================================================ */
const { Chess } = require('chess.js');

/* Латинские токены, похожие на ход. [+#] в конце обязателен в
   регулярке, иначе «+» и «#» останутся мусором в комментарии. */
const SAN_CORE =
  '(?:O-O-O|O-O|[KQRBN][a-h]?[1-8]?x?[a-h][1-8]|[a-h]x[a-h][1-8](?:=?[QRBN])?' +
  '|[a-h][1-8](?:=?[QRBN])?|[a-h][a-h](?:=?[QRBN])?)[+#]?';

/* Слова, после которых идёт НЕ основной вариант, а разбор
   альтернативы. Список набран по двум книгам; при новой книге
   его стоит проверить на 20–30 примерах. */
const TRIG = /(Например|например|случае|Ход |Вместо|вместо|Если|если|Иначе|иначе|партии|льтернатив|роигрывает|лохо|слабее|хуже|шибочн|нельзя|аслуживает|озможно|нтересн|тоже хорош|также хорош|ыбор|годится|ругой|ругая|ругие|стоило|следовало|грозит|угроз|шибка|редпочт|роще|екомендует|критик|Не |ужасно|сомнит|неточн|спасал|спасает|не дает|ничего не|обречен|попытк|Попытк|пробовал)/;

/* «Пустой» промежуток: только пробелы, знаки оценки и пунктуация
   оценок. Нужен, чтобы отличить продолжение записи ходов
   («17.h4 c6») от хода, к которому ведёт русский текст. */
const GAPOK = /^[\s!?+\-−=±∓⩲⩱÷©ƒ‚„,;:∞]*$/;

/* Ход из книжных сокращений: «gh» (пешка g бьёт на h),
   «a1Q» (превращение без «=»), «R1:d4» уже нормализован в Rxd4. */
function doMove(ch, san) {
  san = san.replace(/^([a-h][18])([QRBN])$/, '$1=$2');
  let m = null;
  try { m = ch.move(san); } catch (e) { m = null; }
  if (m) return m;
  const sh = san.match(/^([a-h])([a-h])(?:=?([QRBN]))?$/);
  if (sh) {
    const cand = ch.moves({ verbose: true }).filter(x =>
      x.piece === 'p' && x.from[0] === sh[1] && x.to[0] === sh[2] &&
      (sh[3] ? x.promotion === sh[3].toLowerCase() : !x.promotion));
    if (cand.length === 1) { try { return ch.move(cand[0].san); } catch (e) { return null; } }
  }
  return null;
}

/**
 * Главная функция.
 * @param fen     позиция задачи
 * @param side    'w' | 'b' — чей ход
 * @param mv      номер хода в партии (у Конотопа всегда 1)
 * @param text    текст разбора, уже нормализованный под chess.js
 * @param opts    {startAt, maxPly, softTrig}
 *
 * Как это работает. Идём по тексту токен за токеном и ведём ДВЕ
 * нумерации: основную (какой ход ждём в решении) и нумерацию
 * побочного варианта. Токен принимается в основную ветку, только
 * если его номер и сторона совпадают с ожиданием И он легален в
 * текущей позиции. Всё остальное уходит в побочный вариант со
 * своей нумерацией — и продолжается, пока его собственная
 * нумерация сходится. Именно это разделение и отсеивает
 * «В партии было 16.0-0» или «Ход 15...d5?? невозможен».
 */
function extractLine(fen, side, mv, text, opts = {}) {
  const TOK = new RegExp('([()])|(?:(\\d+)\\s*(\\.\\.\\.|\\.)\\s*)?(' + SAN_CORE + ')([!?]{0,2})', 'g');
  const maxPly = opts.maxPly || 24;
  const ch = new Chess(); ch.load(fen);
  let depth = 0, expNum = mv, expSide = side;
  let slNum = null, slSide = null;          // нумерация побочного варианта
  let prevEnd = -1, prevWasSide = false;
  const moves = [];
  const adv = (n, s) => s === 'w' ? [n, 'b'] : [n + 1, 'w'];

  TOK.lastIndex = opts.startAt || 0;
  let m;
  while ((m = TOK.exec(text))) {
    if (m[1]) { depth += m[1] === '(' ? 1 : -1; if (depth < 0) depth = 0; continue; }
    const start = m.index, end = start + m[0].length;
    const before = text[start - 1] || '', after = text[end] || '';
    /* «g5-g6», «...e6-e5» — это планы словами, а не ходы */
    if (before === '-' || after === '-' || before === '.' || /[A-Za-z0-9]/.test(before)) continue;
    if (depth > 0) continue;                 // всё в скобках — побочное
    if (moves.length >= maxPly) break;

    const num = m[2] ? +m[2] : null, dots = m[3], san = m[4];
    const gap = prevEnd < 0 ? '' : text.slice(prevEnd, start);
    const adjacent = prevEnd >= 0 && GAPOK.test(gap);
    const tail = gap.split(/[.!?…»][ ]/).pop();      // хвост последней фразы
    const hasSent = /[.!?…»][ ]/.test(gap);          // была ли точка
    const tside = num === null ? null : (dots === '...' ? 'b' : 'w');
    const toSide = (n, s) => { [slNum, slSide] = adv(n, s); prevEnd = end; prevWasSide = true; };
    const tryMain = () => {
      const r = doMove(ch, san);
      if (!r) return false;
      moves.push({ uci: r.from + r.to + (r.promotion || ''), san: r.san, fen: ch.fen(), start, end, ann: m[5] || '' });
      [expNum, expSide] = adv(expNum, expSide);
      prevEnd = end; prevWasSide = false; slNum = null; slSide = null;
      return true;
    };

    if (num !== null) {
      const mMain = num === expNum && tside === expSide;
      const mSide = slNum !== null && num === slNum && tside === slSide;
      /* Внутри фразы побочный вариант продолжается: пока не было
         точки, мы всё ещё разбираем альтернативу. */
      if (mSide && (adjacent || !hasSent)) { toSide(num, tside); continue; }
      if (mMain && !(moves.length && TRIG.test(tail))) { if (tryMain()) continue; }
      if (mSide) { toSide(num, tside); continue; }
      toSide(num, tside); continue;
    }
    /* Ход без номера («17.h4 c6») берём только если он стоит
       сразу за предыдущим — иначе это Nd5 из пояснения. */
    if (!adjacent) continue;
    if (prevWasSide) { if (slNum !== null) toSide(slNum, slSide); continue; }
    if (moves.length === 0) continue;
    tryMain();
  }
  return moves;
}

module.exports = { extractLine, doMove, SAN_CORE, TRIG };
