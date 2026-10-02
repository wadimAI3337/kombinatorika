/* ============================================================
   РЕАЛИЗАЦИЯ ПЕРЕВЕСА

   Метод Рамеша (11-й урок «Терминатора»): смотришь партию чемпиона
   до момента, когда у него уже выиграно (+2 и выше), дальше не
   смотришь — доигрываешь сам против движка, а потом сверяешься,
   как реализовал чемпион.

   Позиции — стартовый набор real-seed.js (30 партий Крамника,
   Фишера и Карпова, точку выбрал тренер). Собирается
   tools/real/build_seed.py.

   Соперник — два режима:
     • упрямый защитник: Stockfish считает 5 лучших ходов и выбирает
       только среди тех, что хуже лучшего не больше чем на допуск
       уровня; когда он проигрывает, избегает разменов — так
       защищаются люди. Зевнуть фигуру он не может: такой ход
       выходит за допуск;
     • ограничение глубины: полноценный движок, но с маленьким
       лимитом позиций на ход — ошибается «горизонтно», а не случайно.
   Обратная сторона: та же позиция, но ты защищаешься против
   сильного движка.

   После партии: график (ты и чемпион), ходы, где потерял больше
   пешки, твой путь рядом с ходами чемпиона, «честная» ли победа,
   задачи из твоих ошибок с интервальным повторением, профиль
   слабостей и адаптивный уровень соперника.

   Сохранения — ключ kombi-real (синхронизируется auth.js).
   ============================================================ */
(function () {
"use strict";
const CH = window.__chess;
if (!CH || typeof makeMove !== "function" || typeof SF_SOURCES === "undefined") return;

const $ = id => document.getElementById(id);
const KEY = "kombi-real";
const START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
const MATE = 10000, DAY = 864e5, IVL = [1, 3, 7, 16, 35, 70, 140];
const MISTAKE = 100;          /* потеря больше пешки — ошибка */
const GIFT = 200;             /* соперник отдал две пешки и больше — подарок */
const AN_DEPTH = 12;          /* разбор после партии */
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const C = cp => clamp(cp, -1000, 1000);
const Wcp = cp => 50 + 50 * (2 / (1 + Math.exp(-0.00368208 * clamp(cp, -1600, 1600))) - 1);
const sideOf = fen => fen.split(" ")[1];
const other = s => s === "w" ? "b" : "w";
const posKey = fen => fen.split(" ").slice(0, 4).join(" ");
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
const h = t => esc(String(t == null ? "" : t));
function plural(n, one, few, many) {
  const a = Math.abs(n) % 100, b = a % 10;
  if (a > 10 && a < 20) return many;
  if (b > 1 && b < 5) return few;
  return b === 1 ? one : many;
}
const FIGS = { w: { K: "♔", Q: "♕", R: "♖", B: "♗", N: "♘" }, b: { K: "♚", Q: "♛", R: "♜", B: "♝", N: "♞" } };
const fig = (san, side) => { const m = /^([KQRBN])/.exec(san || ""); return m ? FIGS[side][m[1]] + san.slice(1) : (san || ""); };
const evTxt = cp => Math.abs(cp) >= MATE - 300 ? (cp > 0 ? "мат" : "−мат") :
  (cp > 0 ? "+" : cp < 0 ? "−" : "") + (Math.abs(cp) / 100).toFixed(2);
const moveLab = (fen) => { const p = fen.split(" "); return p[5] + (p[1] === "w" ? "." : "…"); };

/* ---------- сохранения ---------- */
function norm(o) {
  o = o && typeof o === "object" ? o : {};
  o.cfg = Object.assign({ opp: "stub", adapt: true, clock: "0" }, o.cfg || {});
  o.cfg.lvl = Object.assign({ stub: 3, nodes: 3 }, o.cfg.lvl || {});
  o.res = Array.isArray(o.res) ? o.res : [];
  o.puz = o.puz && typeof o.puz === "object" ? o.puz : {};
  o.lib = o.lib && typeof o.lib === "object" ? o.lib : {};
  o.imp = Object.assign({ th: 200, min: 30, slow: true, n: 100 }, o.imp || {});
  return o;
}
let S = norm((() => { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; } })());
function save() {
  if (S.res.length > 400) S.res = S.res.slice(-400);
  try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {}
}
function reload() { try { S = norm(JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {} }

/* ---------- стартовый набор ---------- */
let SEED = null;
const scriptVer = () => { const t = document.querySelector('script[src*="auth.js"]'), m = t && /[?&]v=([^&]+)/.exec(t.src); return m ? "?v=" + m[1] : ""; };
function loadSeed() {
  if (SEED) return Promise.resolve(true);
  return new Promise(res => {
    const done = () => {
      const s = window.REAL_SEED;
      if (!s || !s.games) { res(false); return; }
      s.games.forEach(g => { g.sansArr = g.sans.split(" "); });
      SEED = s; res(true);
    };
    if (window.REAL_SEED) { done(); return; }
    const el = document.createElement("script");
    el.src = "real-seed.js" + scriptVer();
    el.onload = done; el.onerror = () => res(false);
    document.body.appendChild(el);
  });
}
const items = () => (SEED ? SEED.games : []).concat(IMP);
const itemById = pid => items().find(g => g.pid === pid);
function nodesOf(g) {
  if (g._nodes) return g._nodes;
  const out = [{ fen: g.start || START, san: "", uci: "" }];
  let f = out[0].fen;
  for (const s of g.sansArr) {
    const mv = CH.sanToMove(f, s);
    if (!mv) break;
    out.push({ fen: mv.fen, san: mv.san, uci: mv.uci, from: mv.from, to: mv.to });
    f = mv.fen;
  }
  return (g._nodes = out);
}
const heroName = g => g.heroName || g.group || (g.hero === "w" ? g.white : g.black);
const sgn = side => side === "w" ? 1 : -1;
const evAt = (g, i) => (g.ev[i] == null ? 0 : g.ev[i]) * sgn(g.hero);
const champMoves = g => Math.ceil((g.sansArr.length - g.k) / 2);

/* ---------- Stockfish: свой воркер ---------- */
const E = {
  w: null, state: "off", job: null, queue: [], opt: {}, _p: null,
  load() {
    if (this.w) return Promise.resolve(true);
    if (this._p) return this._p;
    this.state = "loading";
    return (this._p = new Promise(resolve => {
      const tryLoad = i => {
        if (i >= SF_SOURCES.length) { this.state = "fail"; this._p = null; resolve(false); return; }
        const js = SF_SOURCES[i];
        let w;
        try { w = sfWorker(js); } catch (e) { tryLoad(i + 1); return; }
        let alive = false, settled = false, timer = null;
        const fail = () => {
          if (alive || settled) return;
          settled = true; clearTimeout(timer);
          try { w.terminate(); } catch (e) {}
          tryLoad(i + 1);
        };
        w.onerror = fail;
        timer = setTimeout(fail, /^https?:/i.test(js) ? 45000 : 20000);
        w.onmessage = e => {
          const s = typeof e.data === "string" ? e.data : (e.data && e.data.data) || "";
          if (!alive && /abort|RuntimeError|Failed to fetch|failed to load/i.test(s)) { fail(); return; }
          if (!alive && (s.indexOf("uciok") >= 0 || s.indexOf("Stockfish") >= 0)) {
            if (settled) { try { w.terminate(); } catch (e2) {} return; }
            alive = true; settled = true; clearTimeout(timer);
            this.w = w; this.state = "on"; this.opt = {};
            sfSetup(w, js);
            w.postMessage("setoption name Hash value 32");
            w.postMessage("ucinewgame");
            resolve(true);
          }
          if (w === this.w) this.line(s);
        };
        w.postMessage("uci");
      };
      tryLoad(0);
    }));
  },
  set(name, v) {
    if (this.opt[name] === v) return;
    this.opt[name] = v;
    this.w.postMessage("setoption name " + name + " value " + v);
  },
  go(o) {
    return new Promise(resolve => {
      const j = Object.assign({ pvs: [], depth: 0, resolve }, o);
      if (!this.w) { resolve({ pvs: [], best: "" }); return; }
      if (this.job) this.queue.push(j); else this.start(j);
    });
  },
  start(j) {
    this.job = j;
    this.set("MultiPV", j.multipv || 1);
    this.w.postMessage("position fen " + j.fen);
    let cmd = "go";
    if (j.depth) cmd += " depth " + j.depth;
    if (j.nodes) cmd += " nodes " + j.nodes;
    if (j.movetime) cmd += " movetime " + j.movetime;
    if (cmd === "go") cmd += " depth 12";
    this.w.postMessage(cmd);
    j.timer = setTimeout(() => { if (this.job === j) this.w.postMessage("stop"); }, j.cap || 15000);
  },
  line(s) {
    const j = this.job;
    if (!j || typeof s !== "string") return;
    if (s.indexOf("bestmove") === 0) {
      clearTimeout(j.timer); this.job = null;
      const bm = s.split(/\s+/)[1] || "";
      if (!j.pvs[0] && bm && bm !== "(none)") j.pvs[0] = { kind: "cp", val: 0, pv: [bm], depth: 0 };
      j.resolve({ pvs: j.pvs.filter(Boolean), best: bm === "(none)" ? "" : bm, depth: j.depth });
      const n = this.queue.shift();
      if (n) this.start(n);
      return;
    }
    if (s.indexOf("info") !== 0 || s.indexOf(" pv ") < 0) return;
    if (s.indexOf(" upperbound") >= 0 || s.indexOf(" lowerbound") >= 0) return;
    const d = +(s.match(/ depth (\d+)/) || [])[1] || 0;
    const mp = +(s.match(/ multipv (\d+)/) || [])[1] || 1;
    const sc = s.match(/ score (cp|mate) (-?\d+)/);
    const pv = (s.split(" pv ")[1] || "").trim().split(/\s+/);
    if (!sc || !pv[0]) return;
    const had = j.pvs[mp - 1];
    if (had && had.depth > d) return;
    j.depth = Math.max(j.depth, d);
    j.pvs[mp - 1] = { kind: sc[1], val: +sc[2], pv, depth: d };
  },
  stopAll() {
    this.queue.forEach(j => j.resolve({ pvs: [], best: "", cancelled: true }));
    this.queue = [];
    if (this.job && this.w) this.w.postMessage("stop");
  }
};
/* оценка глазами того, чей ход; мат — ±(10000 − ходов) */
const cpOf = p => !p ? 0 : p.kind === "mate" ? (p.val > 0 ? MATE - p.val : -MATE - p.val) : p.val;

/* ---------- соперник ---------- */
const LVL = 8;
/* уровни 1…8: допуск (сантипешки), глубина, «температура» выбора */
const STUB = { tol: [0, 80, 70, 60, 50, 42, 35, 26, 15], depth: [0, 4, 5, 6, 8, 9, 11, 13, 15],
               temp: [0, 40, 34, 28, 23, 18, 14, 10, 5] };
const NODES = [0, 1000, 4000, 12000, 35000, 90000, 220000, 550000, 1400000];
const OPP_NAME = { stub: "Упрямый защитник", nodes: "Ограничение глубины" };

function tradePenalty(fen, pv) {
  const pos = parseFen(fen), m = pv[0], to = m.slice(2, 4), cap = pos[to];
  if (!cap || !pv[1] || pv[1].slice(2, 4) !== to) return 0;   /* взял — и сразу забирают обратно */
  return cap.toLowerCase() === "q" ? 45 : 22;
}
async function engineMove(fen, rev) {
  if (rev) {
    const r = await E.go({ fen, movetime: 1500, depth: 22, multipv: 1, cap: 4000 });
    return { uci: r.best, cp: cpOf(r.pvs[0]), cancelled: r.cancelled };
  }
  const mode = S.cfg.opp, lv = clamp(S.cfg.lvl[mode] || 3, 1, LVL);
  if (mode === "nodes") {
    const r = await E.go({ fen, nodes: NODES[lv], multipv: 1 });
    return { uci: r.best, cp: cpOf(r.pvs[0]), cancelled: r.cancelled };
  }
  const r = await E.go({ fen, depth: STUB.depth[lv], multipv: 5 });
  if (r.cancelled) return { cancelled: true };
  const c = r.pvs.filter(p => p && p.pv && p.pv[0]).map(p => ({ uci: p.pv[0], cp: cpOf(p), pv: p.pv }));
  if (!c.length) return { uci: r.best, cp: 0 };
  c.sort((a, b) => b.cp - a.cp);
  const best = c[0].cp;
  if (best >= MATE - 300) return c[0];
  const losing = best < -50, tol = STUB.tol[lv], tmp = STUB.temp[lv];
  const ok = c.filter(x => best - x.cp <= tol)
    .map(x => Object.assign({ adj: best - x.cp + (losing ? tradePenalty(fen, x.pv) : 0) }, x));
  const ws = ok.map(x => Math.exp(-x.adj / tmp));
  let roll = Math.random() * ws.reduce((a, b) => a + b, 0);
  for (let i = 0; i < ok.length; i++) { roll -= ws[i]; if (roll <= 0) return ok[i]; }
  return ok[0];
}

/* ---------- доска ---------- */
const ARROW = { green: "#3F8F2E", red: "#B53A2A", blue: "#2E6FB5", gray: "rgba(90,80,70,.75)" };
function drawBoard(host, fen, o) {
  o = o || {};
  const pos = parseFen(fen), dests = o.sel ? legalTargets(fen, o.sel) : [];
  let html = "";
  for (let r = 0; r < 8; r++) for (let f = 0; f < 8; f++) {
    const rank = o.flip ? r + 1 : 8 - r, file = o.flip ? FILES[7 - f] : FILES[f], name = file + rank;
    let cls = "sq" + ((r + f) % 2 ? " dk" : "");
    if (o.sel === name) cls += " sel";
    if (dests.indexOf(name) >= 0) cls += " dest" + (pos[name] ? " cap" : "");
    if (o.last && (o.last[0] === name || o.last[1] === name)) cls += " last";
    if (o.check === name) cls += " err";
    html += `<div class="${cls}" data-sq="${name}"><span class="mark"></span>` +
      (pos[name] ? `<svg class="pc" viewBox="0 0 100 100"><use href="#pc-${pos[name]}"/></svg>` : "") +
      (r === 7 ? `<span class="coord f">${file}</span>` : "") + (f === 0 ? `<span class="coord r">${rank}</span>` : "") + "</div>";
  }
  host.innerHTML = html;
  (o.arrows || []).forEach(a => arrowOn(host, a[0], a[1], o.flip, a[2]));
}
function arrowOn(host, from, to, flip, color) {
  if (!from || !to) return;
  const ctr = sq => { const f = FILES.indexOf(sq[0]), r = +sq[1] - 1; return flip ? [7 - f + .5, r + .5] : [f + .5, 7 - r + .5]; };
  const [ax, ay] = ctr(from), [bx, by] = ctr(to);
  const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy) || 1, ux = dx / len, uy = dy / len, head = .26, hw = .115;
  const sx = ax + ux * .22, sy = ay + uy * .22, ex = bx - ux * head, ey = by - uy * head, col = ARROW[color] || color || ARROW.green;
  host.insertAdjacentHTML("beforeend",
    `<svg class="opar" viewBox="0 0 8 8" preserveAspectRatio="none">` +
    `<line x1="${sx}" y1="${sy}" x2="${ex}" y2="${ey}" stroke="${col}" stroke-width=".095" opacity=".9"/>` +
    `<polygon points="${bx - ux * .04},${by - uy * .04} ${ex - uy * hw},${ey + ux * hw} ${ex + uy * hw},${ey - ux * hw}" fill="${col}" opacity=".9"/></svg>`);
}
function bindBoard(host, handler) {
  let down = null;
  host.addEventListener("pointerdown", e => {
    const el = e.target.closest(".sq"); if (!el) return;
    e.preventDefault(); down = el.dataset.sq; handler("down", down);
  });
  host.addEventListener("pointerup", e => {
    const el = document.elementFromPoint(e.clientX, e.clientY);
    const sq = el && el.closest && el.closest(".sq");
    if (sq && down && sq.dataset.sq !== down) handler("up", sq.dataset.sq);
    down = null;
  });
  host.addEventListener("contextmenu", e => e.preventDefault());
}
const checkSq = fen => {
  if (!inCheckNow(fen)) return "";
  const pos = parseFen(fen), k = sideOf(fen) === "w" ? "K" : "k";
  return Object.keys(pos).find(s => pos[s] === k) || "";
};
function ebar(el, cpWhite, fen, flip) {
  if (!el || !CH.evalBar) return;
  const stm = sideOf(fen) === "w" ? cpWhite : -cpWhite;
  const e = Math.abs(stm) >= MATE - 300
    ? { kind: "mate", val: stm > 0 ? Math.max(1, MATE - stm) : -Math.max(1, MATE + stm) }
    : { kind: "cp", val: stm };
  CH.evalBar(el, e, fen, flip);
}

/* ---------- статистика по позиции ---------- */
const resOf = pid => S.res.filter(r => r.pid === pid && !r.rev);
function statusOf(pid) {
  const rs = resOf(pid);
  if (!rs.length) return { k: "new", t: "новая" };
  if (rs.some(r => r.result === "win" && r.fair && r.mist.length <= 1)) return { k: "clean", t: "реализовано чисто" };
  if (rs.some(r => r.result === "win")) return { k: "won", t: "реализовано" };
  return { k: "fail", t: "не дожал" };
}
const duePuz = () => Object.values(S.puz).filter(p => p.due <= Date.now()).sort((a, b) => a.due - b.due);

/* ============================================================
   СВОИ ПАРТИИ: загрузка, отсев, поиск точки перевеса

   Источники: PGN (вставить или файлом), ссылка на партию или study
   lichess, ник на lichess, ник на chess.com.
   1) отсев без движка — по заголовкам и длине партии;
   2) готовые оценки lichess (%eval), если партию там уже разбирали;
   3) два прохода Stockfish: быстро по всем позициям, глубже — вокруг
      места, где оценка перевалила порог;
   4) точка перевеса — та же логика, что в tools/real/scan.py.
   Очередь живёт в IndexedDB: закрыл вкладку — продолжится с того же
   места. Разобранные партии кладутся в общий кэш Supabase (таблица
   real_cache), чтобы одну и ту же партию не считать дважды.
   ============================================================ */
const PT = { CAP: 700, STABLE: 6, MIN_LEFT: 20, SWING: 80, TACTIC: 2 };
const D1 = 10, D2 = 16;
const PVAL = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
let IMP = [];                 /* загруженные позиции — как элементы стартового набора */

/* --- точка перевеса (синхронно с scan.py: find_point) --- */
function findPoint(ev, stmWhite0, heroWhite, gain, th) {
  const n = ev.length, s = heroWhite ? 1 : -1;
  const pov = ev.map(e => e == null ? null : e * s);
  const heroMoves = i => ((i % 2 === 0) === stmWhite0) === heroWhite;
  let first = null;
  for (let i = 0; i < n; i++) {
    if (!heroMoves(i) || pov[i] == null || pov[i] < th) continue;
    const win = pov.slice(i, i + PT.STABLE + 1).filter(p => p != null);
    if (win.length && Math.min(...win) >= th * 0.75) { first = i; break; }
  }
  if (first == null) return { k: null, v: "none", flags: [] };
  if (pov[first] >= PT.CAP) return { k: first, v: "jump", flags: [] };
  let k = null;
  for (let i = first; i < Math.min(n, first + 12); i++) {
    if (!heroMoves(i) || pov[i] == null || pov[i] < th * 0.75 || pov[i] >= PT.CAP) continue;
    const g = gain ? gain(i) : null;
    if (g != null && g >= PT.TACTIC) continue;
    k = i; break;
  }
  if (k == null) return { k: first, v: "tactic", flags: [] };
  if (n - 1 - k < PT.MIN_LEFT) return { k, v: "short", flags: [] };
  const rest = pov.slice(k).filter(p => p != null);
  return { k, v: "ok", flags: rest.length && Math.min(...rest) < PT.SWING ? ["swing"] : [] };
}
function matBal(fen, side) {
  const pos = parseFen(fen); let m = 0;
  for (const q in pos) { const pc = pos[q], v = PVAL[pc.toLowerCase()] || 0; m += (isW(pc) === (side === "w")) ? v : -v; }
  return m;
}
function pvGain(fen, pv) {
  if (!pv || !pv.length) return null;
  const side = sideOf(fen), m0 = matBal(fen, side);
  let f = fen;
  for (const u of pv.slice(0, 3)) { const mv = makeMove(f, u.slice(0, 2), u.slice(2, 4), u[4]); if (!mv) break; f = mv.fen; }
  return matBal(f, side) - m0;
}
/* --- теги (синхронно с scan.py: tags_of) --- */
function tagsOf(fen, heroWhite) {
  const pos = parseFen(fen), cnt = {};
  for (const q in pos) { const pc = pos[q]; cnt[pc] = (cnt[pc] || 0) + 1; }
  const c = (side, t) => cnt[side === "w" ? t.toUpperCase() : t] || 0;
  const H = heroWhite ? "w" : "b", O = heroWhite ? "b" : "w";
  const d = t => c(H, t) - c(O, t);
  const minor = d("n") + d("b");
  const np = side => 3 * c(side, "n") + 3 * c(side, "b") + 5 * c(side, "r") + 9 * c(side, "q");
  const queens = c("w", "q") + c("b", "q");
  const out = [];
  out.push((queens === 0 && np("w") <= 13 && np("b") <= 13) || np("w") + np("b") <= 16 ? "эндшпиль" : "миттельшпиль");
  const dp = d("p");
  if (d("q") === 0 && d("r") === 0 && minor === 0)
    out.push(dp === 0 ? "позиционный перевес" : dp === 1 ? "лишняя пешка" : dp > 1 ? "лишние пешки" : "перевес при меньшем материале");
  else if (d("r") === 1 && minor === -1 && d("q") === 0) out.push("лишнее качество");
  else if (minor >= 1 && d("r") === 0 && d("q") === 0) out.push("лишняя фигура");
  else out.push("неравный материал");
  const bsq = side => Object.keys(pos).filter(q => pos[q] === (side === "w" ? "B" : "b"));
  const wb = bsq("w"), bb = bsq("b"), col = q => (FILES.indexOf(q[0]) + +q[1] - 1) % 2;
  if (wb.length === 1 && bb.length === 1 && col(wb[0]) !== col(bb[0])) out.push("разноцветные слоны");
  const hp = H === "w" ? "P" : "p", op = H === "w" ? "p" : "P";
  for (const q in pos) {
    if (pos[q] !== hp) continue;
    const f = FILES.indexOf(q[0]), r = +q[1];
    let blocked = false;
    for (let ff = f - 1; ff <= f + 1 && !blocked; ff++) {
      if (ff < 0 || ff > 7) continue;
      for (let rr = 1; rr <= 8; rr++) {
        if (H === "w" ? rr <= r : rr >= r) continue;
        if (pos[FILES[ff] + rr] === op) { blocked = true; break; }
      }
    }
    if (!blocked) { out.push("проходная"); break; }
  }
  return out;
}

/* --- PGN: заголовки, ходы и оценки lichess --- */
function splitPgn(text) {
  return String(text || "").replace(/\r/g, "").split(/\n(?=\s*\[Event\s)/).map(t => t.trim()).filter(t => /\d\.|\[/.test(t));
}
function headersOf(pgn) {
  const hd = {}, re = /^\s*\[\s*([A-Za-z0-9_]+)\s+"([^"]*)"\s*\]\s*$/gm; let m;
  while ((m = re.exec(pgn))) hd[m[1]] = m[2];
  return hd;
}
function movesOf(pgn) {
  let body = pgn.replace(/^\s*\[[^\]]*\]\s*$/gm, " ");
  let prev;
  do { prev = body; body = body.replace(/\([^()]*\)/g, " "); } while (body !== prev);
  body = body.replace(/\$\d+/g, " ").replace(/;[^\n]*/g, " ");
  const toks = body.match(/\{[^}]*\}|[^\s{}]+/g) || [];
  const SAN = /^(?:O-O-O|O-O|0-0-0|0-0|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?)[+#]?[!?]{0,2}$/;
  const sans = [], evals = [];
  for (const t of toks) {
    if (t[0] === "{") {
      const e = /\[%eval\s+(#?-?[\d.]+)/.exec(t);
      if (e && sans.length) {
        const v = e[1];
        evals[sans.length] = v[0] === "#" ? (+v.slice(1) > 0 ? MATE - Math.abs(+v.slice(1)) : -MATE + Math.abs(+v.slice(1))) : Math.round(+v * 100);
      }
      continue;
    }
    if (/^\d+\.*$/.test(t) || /^(1-0|0-1|1\/2-1\/2|\*)$/.test(t)) continue;
    const c = t.replace(/^\d+\.+/, "");
    if (SAN.test(c)) sans.push(c.replace(/[!?]+$/, ""));
  }
  return { sans, evals };
}
const tcBase = hd => { const tc = hd.TimeControl || ""; if (!tc || tc === "-" || tc === "?") return null; const b = parseInt(tc.split("+")[0].split("/").pop(), 10); return isNaN(b) ? null : b; };
const lc = s => String(s || "").toLowerCase();
/* отсев без движка; возвращает причину отказа или null */
function prefilter(pgn, o) {
  const hd = headersOf(pgn), res = hd.Result || "*";
  if (o.me) {
    if (lc(hd.White) !== lc(o.me) && lc(hd.Black) !== lc(o.me)) return "не твоя партия";
  } else {
    if (res !== "1-0" && res !== "0-1") return "ничья или без результата";
    const winner = res === "1-0" ? hd.White : hd.Black;
    if (o.hero && lc(winner).indexOf(lc(o.hero)) < 0) return "выиграл не тот игрок";
  }
  if (hd.Variant && !/standard/i.test(hd.Variant)) return "не классические шахматы";
  const b = tcBase(hd);
  if (o.slow && b != null && b < 600) return "блиц и пуля";
  const plies = (pgn.replace(/\{[^}]*\}/g, " ").replace(/\([^()]*\)/g, " ").match(/(?:^|\s)(?:\d+\.+\s*)?(?:O-O|[KQRBNa-h])[^\s]*/g) || []).length;
  if (plies < o.min * 2) return "короткая";
  return null;
}

/* --- IndexedDB: разобранные партии и очередь --- */
const DB = {
  db: null, bad: false,
  open() {
    if (this.db) return Promise.resolve(this.db);
    if (this.bad || !window.indexedDB) return Promise.resolve(null);
    return new Promise(res => {
      let r;
      try { r = indexedDB.open("kombi-real", 1); } catch (e) { this.bad = true; res(null); return; }
      r.onupgradeneeded = () => {
        const d = r.result;
        ["games", "job", "jobdata"].forEach(n => { if (!d.objectStoreNames.contains(n)) d.createObjectStore(n, { keyPath: "id" }); });
      };
      r.onsuccess = () => { this.db = r.result; res(this.db); };
      r.onerror = () => { this.bad = true; res(null); };
    });
  },
  async req(store, mode, fn) {
    const d = await this.open();
    if (!d) return undefined;
    return new Promise(res => {
      try {
        const q = fn(d.transaction(store, mode).objectStore(store));
        q.onsuccess = () => res(q.result); q.onerror = () => res(undefined);
      } catch (e) { res(undefined); }
    });
  },
  get(store, id) { return this.req(store, "readonly", o => o.get(id)); },
  put(store, v) { return this.req(store, "readwrite", o => o.put(v)); },
  del(store, id) { return this.req(store, "readwrite", o => o.delete(id)); }
};

/* --- общий кэш в Supabase --- */
let cloudOff = false;
const sbc = () => { try { return window.kombiSync && window.kombiSync.client ? window.kombiSync.client() : null; } catch (e) { return null; } };
const cloudErr = e => { if (e && /real_cache|does not exist|schema cache|PGRST205|42P01/i.test((e.message || "") + (e.code || ""))) cloudOff = true; };
async function cloudGet(ids) {
  const c = sbc(); if (!c || cloudOff || !ids.length) return {};
  try {
    const r = await c.from("real_cache").select("gid,data").in("gid", ids);
    if (r.error) { cloudErr(r.error); return {}; }
    const out = {}; (r.data || []).forEach(x => { out[x.gid] = x.data; }); return out;
  } catch (e) { return {}; }
}
async function cloudPut(rec) {
  const c = sbc(); if (!c || cloudOff) return;
  const u = window.kombiSync.user && window.kombiSync.user(); if (!u) return;
  try {
    const r = await c.from("real_cache").upsert({ gid: rec.id, data: rec }, { onConflict: "gid", ignoreDuplicates: true });
    if (r.error) cloudErr(r.error);
  } catch (e) {}
}
async function sha(s) {
  try {
    const b = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(s));
    return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("").slice(0, 16);
  } catch (e) { let h1 = 5381; for (let i = 0; i < s.length; i++) h1 = ((h1 << 5) + h1 + s.charCodeAt(i)) | 0; return "h" + (h1 >>> 0).toString(16); }
}

/* --- элементы библиотеки из разобранных партий --- */
function itemOf(meta, rec) {
  return {
    pid: meta.pid, gid: meta.gid, imported: true, mine: !!meta.mine, group: meta.col,
    heroName: meta.heroName, title: meta.title, year: meta.year, white: rec.h.White || "?", black: rec.h.Black || "?",
    result: rec.h.Result || "*", hero: meta.hero, sans: rec.sans, sansArr: rec.sans.split(" "),
    start: rec.start || START, k: meta.k, ev: rec.ev, tags: meta.tags || [], flags: meta.flags || [], missed: !!meta.missed
  };
}
async function loadImported() {
  const metas = Object.values(S.lib), out = [], miss = [];
  for (const m of metas) {
    const rec = await DB.get("games", m.gid);
    if (rec) out.push(itemOf(m, rec)); else miss.push(m);
  }
  if (miss.length) {
    for (let i = 0; i < miss.length; i += 100) {
      const got = await cloudGet(miss.slice(i, i + 100).map(m => m.gid));
      for (const m of miss.slice(i, i + 100)) {
        const rec = got[m.gid];
        if (rec) { await DB.put("games", rec); out.push(itemOf(m, rec)); }
      }
    }
  }
  IMP = out.concat(IMP.filter(g => !out.some(x => x.pid === g.pid)));
  IMP.missing = metas.length - out.length;
}

/* --- источники --- */
async function fetchText(url, accept) {
  const r = await fetch(url, { headers: accept ? { Accept: accept } : {} });
  if (r.status === 404) throw new Error("не найдено (404)");
  if (r.status === 403) throw new Error("доступ закрыт (403) — например, автор study запретил скачивание");
  if (r.status === 429) throw new Error("lichess просит подождать минуту (429)");
  if (!r.ok) throw new Error("ответ " + r.status);
  return r.text();
}
async function collect(src, o, say) {
  const t = String(src || "").trim();
  if (o.kind === "li") {
    say("Скачиваю партии " + o.nick + " с lichess…");
    const perf = o.slow ? "&perfType=rapid,classical,correspondence" : "";
    return splitPgn(await fetchText(`https://lichess.org/api/games/user/${encodeURIComponent(o.nick)}?max=${o.n}${perf}&evals=true&clocks=false&opening=false`, "application/x-chess-pgn"));
  }
  if (o.kind === "cc") {
    say("Читаю архивы chess.com…");
    const a = JSON.parse(await fetchText(`https://api.chess.com/pub/player/${encodeURIComponent(lc(o.nick))}/games/archives`));
    const months = (a.archives || []).slice().reverse(), out = [];
    for (const m of months) {
      if (out.length >= o.n) break;
      say(`Читаю архивы chess.com… ${out.length} партий`);
      const j = JSON.parse(await fetchText(m));
      (j.games || []).slice().reverse().forEach(g => {
        if (out.length >= o.n || !g.pgn || g.rules !== "chess") return;
        if (o.slow && (g.time_class === "blitz" || g.time_class === "bullet")) return;
        out.push(g.pgn);
      });
    }
    return out;
  }
  const out = [];
  const lines = t.split(/\s+/).filter(x => /^https?:\/\//.test(x));
  if (lines.length && !/\[Event|1\.\s*\S/.test(t.replace(/https?:\/\/\S+/g, ""))) {
    for (const u of lines) {
      const st = /lichess\.org\/study\/([A-Za-z0-9]{8})(?:\/([A-Za-z0-9]{8}))?/.exec(u);
      const gm = /lichess\.org\/([A-Za-z0-9]{8})(?:[A-Za-z0-9]{4})?(?:$|[\/?#])/.exec(u);
      say("Скачиваю " + u);
      if (st) out.push(...splitPgn(await fetchText(st[2] ? `https://lichess.org/api/study/${st[1]}/${st[2]}.pgn` : `https://lichess.org/api/study/${st[1]}.pgn`)));
      else if (gm) out.push(await fetchText(`https://lichess.org/game/export/${gm[1]}?evals=true&clocks=false`));
      else throw new Error("не понял ссылку: " + u + ". Поддерживаются партии и study с lichess; для chess.com — укажи ник.");
    }
    return out;
  }
  return splitPgn(t);
}

/* --- очередь --- */
let JOB = null, jobRun = false;
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function startJob(list, o, col) {
  const pass = [], skip = {};
  list.forEach(p => { const why = prefilter(p, o); if (why) skip[why] = (skip[why] || 0) + 1; else pass.push(p); });
  JOB = { id: "cur", col, o, total: pass.length, all: list.length, i: 0, found: 0, cached: 0, skip, pre: Object.assign({}, skip), state: "run", t: Date.now() };
  await DB.put("jobdata", { id: "cur", list: pass });
  await DB.put("job", JOB);
  runJob();
}
async function resumeJob() {
  const j = await DB.get("job", "cur");
  if (j && j.state === "run" && j.i < j.total) { JOB = j; runJob(); }
  else if (j && j.state !== "done") JOB = j;
}
async function runJob() {
  if (jobRun || !JOB) return;
  jobRun = true;
  const data = await DB.get("jobdata", "cur");
  const list = data ? data.list : [];
  if (!list.length) JOB.total = 0;
  await E.load();
  while (JOB && JOB.state === "run" && JOB.i < JOB.total) {
    while (G && !G.over) await sleep(1500);            /* пока ты играешь — не отбираем движок */
    if (!JOB || JOB.state !== "run") break;
    try { await processOne(list[JOB.i], JOB); } catch (e) { JOB.skip["ошибка разбора"] = (JOB.skip["ошибка разбора"] || 0) + 1; }
    JOB.i++;
    await DB.put("job", JOB);
    paintJob();
  }
  if (JOB && JOB.i >= JOB.total) { JOB.state = "done"; await DB.put("job", JOB); await DB.del("jobdata", "cur"); }
  jobRun = false;
  paintJob();
  if (view === "lib" && root && !root.classList.contains("gone")) renderLib();
}
async function processOne(pgn, job) {
  const o = job.o, hd = headersOf(pgn), mv = movesOf(pgn);
  let f = hd.FEN && hd.SetUp !== "0" ? hd.FEN : START;
  const start = f, fens = [f], ucis = [], sans = [];
  for (const s of mv.sans) {
    const m = CH.sanToMove(f, s);
    if (!m) break;
    fens.push(m.fen); ucis.push(m.uci); sans.push(m.san); f = m.fen;
  }
  if (sans.length < o.min * 2) { job.skip["короткая"] = (job.skip["короткая"] || 0) + 1; return; }
  const res = hd.Result || "*";
  const hero = o.me ? (lc(hd.White) === lc(o.me) ? "w" : "b") : (res === "1-0" ? "w" : "b");
  const gid = await sha((start === START ? "" : start) + "|" + ucis.join(" "));
  const pid = "i" + gid;
  if (S.lib[pid]) { job.skip["уже в библиотеке"] = (job.skip["уже в библиотеке"] || 0) + 1; return; }

  let rec = await DB.get("games", gid), fromCache = !!rec;
  if (!rec) { const c = await cloudGet([gid]); rec = c[gid] || null; fromCache = !!rec; if (rec) await DB.put("games", rec); }
  if (!rec) {
    rec = { id: gid, sans: sans.join(" "), h: { White: hd.White, Black: hd.Black, Result: res, Date: hd.Date || hd.UTCDate || "", Event: hd.Event || "" },
            ev: [], pv: {}, d: [D1, D2] };
    if (start !== START) rec.start = start;
    const hasEv = mv.evals.filter(x => x != null).length >= sans.length - 1;
    for (let i = 0; i < fens.length; i++) {
      const fi = fens[i];
      if (!anyLegal(fi)) { rec.ev[i] = inCheckNow(fi) ? (sideOf(fi) === "w" ? -MATE : MATE) : 0; continue; }
      if (hasEv && i > 0 && mv.evals[i] != null) { rec.ev[i] = mv.evals[i]; continue; }
      if (hasEv && i === 0) { rec.ev[i] = 20; continue; }
      const r = await E.go({ fen: fi, depth: D1, multipv: 1 });
      const cp = cpOf(r.pvs[0]); rec.ev[i] = sideOf(fi) === "w" ? cp : -cp;
    }
    if (hasEv) rec.lichess = 1;
  }
  /* второй проход: глубже вокруг места, где перевес перевалил порог */
  const stm0 = sideOf(start) === "w";
  const p0 = findPoint(rec.ev, stm0, hero === "w", null, o.th);
  if (p0.k != null) {
    const lo = Math.max(0, p0.k - 2), hi = Math.min(fens.length, p0.k + PT.STABLE + 10);
    let touched = false;
    for (let i = lo; i < hi; i++) {
      if (rec.pv[i] || !anyLegal(fens[i])) continue;
      const r = await E.go({ fen: fens[i], depth: D2, multipv: 1 });
      const cp = cpOf(r.pvs[0]); rec.ev[i] = sideOf(fens[i]) === "w" ? cp : -cp;
      rec.pv[i] = (r.pvs[0] && r.pvs[0].pv || []).slice(0, 6); touched = true;
    }
    if (touched || !fromCache) { await DB.put("games", rec); cloudPut(rec); }
  } else if (!fromCache) { await DB.put("games", rec); cloudPut(rec); }
  if (fromCache) job.cached++;

  const pt = findPoint(rec.ev, stm0, hero === "w", i => pvGain(fens[i], rec.pv[i]), o.th);
  if (pt.v !== "ok") {
    const why = { none: "перевес не появился", jump: "сразу разгром", tactic: "решает комбинация", short: "мало ходов после точки" }[pt.v];
    job.skip[why] = (job.skip[why] || 0) + 1;
    return;
  }
  const won = (res === "1-0") === (hero === "w") && res !== "1/2-1/2" && res !== "*";
  const W = hd.White || "?", B = hd.Black || "?";
  const year = (/(\d{4})/.exec(hd.Date || hd.UTCDate || "") || [])[1] || "";
  S.lib[pid] = {
    pid, gid, k: pt.k, hero, col: job.col, mine: !!o.me, missed: !!o.me && !won,
    heroName: hero === "w" ? W : B, title: W + " – " + B, year,
    tags: tagsOf(fens[pt.k], hero === "w").concat(o.me && !won ? ["упущено"] : []), flags: pt.flags, added: Date.now()
  };
  save();
  IMP.push(itemOf(S.lib[pid], rec));
  job.found++;
}
function paintJob() {
  const el = $("rlJob");
  if (!el) return;
  if (!JOB || JOB.state === "gone") { el.innerHTML = ""; el.classList.add("gone"); return; }
  el.classList.remove("gone");
  const pct = JOB.total ? Math.round(100 * JOB.i / JOB.total) : 100;
  const sk = Object.entries(JOB.skip).filter(x => x[1]).map(([k, v]) => `${k} — ${v}`).join(", ");
  const st = JOB.state === "run" ? (G && !G.over ? "пауза, пока идёт твоя партия" : "считаю") : JOB.state === "pause" ? "на паузе" : "готово";
  el.innerHTML = `<div class="rl-jobh"><b>${h(JOB.col)}</b><span>${st}</span></div>
    <div class="rvbar"><i style="width:${pct}%"></i></div>
    <p class="rl-p">Обработано ${JOB.i} из ${JOB.total} · найдено позиций: <b>${JOB.found}</b>${JOB.cached ? ` · из кэша: ${JOB.cached}` : ""}
      ${JOB.all > JOB.total ? ` · отсеяно без движка: ${JOB.all - JOB.total}` : ""}</p>
    ${sk ? `<p class="rvhint">Не подошли: ${h(sk)}.</p>` : ""}
    <div class="rvacts">${JOB.state === "run" ? '<button id="rlJobP">Пауза</button>' : JOB.state === "pause" ? '<button class="go" id="rlJobR">Продолжить</button>' : ""}
      <button id="rlJobX">${JOB.state === "done" ? "Скрыть" : "Отменить"}</button></div>`;
  const p = $("rlJobP"), r = $("rlJobR");
  if (p) p.onclick = async () => { JOB.state = "pause"; await DB.put("job", JOB); paintJob(); };
  if (r) r.onclick = async () => { JOB.state = "run"; await DB.put("job", JOB); runJob(); paintJob(); };
  $("rlJobX").onclick = async () => {
    if (JOB.state !== "done" && !confirm("Остановить обработку? Найденные позиции останутся.")) return;
    JOB.state = "gone"; await DB.put("job", JOB); await DB.del("jobdata", "cur"); JOB = null; paintJob();
  };
}
function importCard() {
  const o = S.imp;
  return `<details class="rvcard rl-imp" id="rlImp"${IMP.length || (JOB && JOB.state !== "gone") ? "" : " open"}>
    <summary>＋ Добавить свои партии</summary>
    <div class="rvseg rl-seg" id="rlKind">
      <button data-k="pgn" aria-pressed="${(o.kind || "pgn") === "pgn"}">PGN или ссылки</button>
      <button data-k="li" aria-pressed="${o.kind === "li"}">ник lichess</button>
      <button data-k="cc" aria-pressed="${o.kind === "cc"}">ник chess.com</button></div>
    <div id="rlSrcBox"></div>
    <div class="rl-row">
      <label class="opcheck"><input type="checkbox" id="rlMe" ${o.meOn ? "checked" : ""}> это мои партии — искать перевесы, которые я упустил</label></div>
    <div class="rl-row rl-me ${o.meOn ? "" : "gone"}"><input class="opinput" id="rlMeNick" placeholder="твой ник в этих партиях" value="${h(o.me || "")}" spellcheck="false"></div>
    <div class="rl-row rl-hero ${o.meOn ? "gone" : ""}"><input class="opinput" id="rlHero" placeholder="Чьи победы брать — например Karpov (пусто — любые)" value="${h(o.hero || "")}" spellcheck="false"></div>
    <div class="rl-row"><span class="rvhint" style="margin:0">Порог</span>
      <div class="rvseg" id="rlTh">${[[150, "+1.5"], [200, "+2"], [300, "+3"]].map(([v, t]) => `<button data-v="${v}" aria-pressed="${o.th === v}">${t}</button>`).join("")}</div>
      <span class="rvhint" style="margin:0">от</span>
      <select class="opsel" id="rlMin">${[20, 30, 40].map(v => `<option value="${v}"${o.min === v ? " selected" : ""}>${v} ходов</option>`).join("")}</select>
      <label class="opcheck"><input type="checkbox" id="rlSlow" ${o.slow ? "checked" : ""}> без блица</label></div>
    <div class="rl-row"><input class="opinput" id="rlCol" placeholder="Название подборки — например «Карпов» или «Мои партии»" spellcheck="false"></div>
    <div class="rl-row"><button class="rvgo" id="rlImpGo">Найти позиции</button><span class="rvhint" id="rlImpSay" style="margin:0"></span></div>
    <p class="rvhint">Сначала сайт без движка выкидывает ничьи, блиц и короткие партии, потом Stockfish ищет момент, когда у
      победителя стало ${(o.th / 100).toFixed(1).replace(".0", "")} и выше и перевес устойчив. Партии, которые уже разбирали на lichess, идут без движка.
      Всё считается в фоне: закроешь вкладку — продолжится при следующем заходе.</p>
  </details>`;
}
function bindImport() {
  const o = S.imp;
  const box = () => {
    const k = o.kind || "pgn";
    $("rlSrcBox").innerHTML = k === "pgn"
      ? `<textarea class="rl-ta" id="rlSrc" spellcheck="false" placeholder="Вставь PGN (можно сразу много партий) или ссылки на партии / study с lichess"></textarea>
         <div class="rl-row"><button class="ghost" id="rlFile">Взять из .pgn-файла</button><input type="file" id="rlFileIn" accept=".pgn,text/plain" multiple hidden><span class="rvhint" id="rlFileSay" style="margin:0"></span></div>`
      : `<div class="rl-row"><input class="opinput" id="rlNick" placeholder="ник на ${k === "li" ? "lichess" : "chess.com"}" value="${h(o["nick_" + k] || "")}" spellcheck="false">
         <select class="opsel" id="rlN">${[50, 100, 300, 1000].map(v => `<option value="${v}"${o.n === v ? " selected" : ""}>последние ${v}</option>`).join("")}</select></div>`;
    if (k === "pgn") {
      $("rlFile").onclick = () => $("rlFileIn").click();
      $("rlFileIn").onchange = async e => {
        const fs = [...e.target.files]; let all = "";
        for (const f of fs) all += "\n\n" + await f.text();
        $("rlSrc").value = all.trim();
        $("rlFileSay").textContent = fs.map(f => f.name).join(", ") + " · " + splitPgn(all).length + " партий";
        if (!$("rlCol").value && fs[0]) $("rlCol").value = fs[0].name.replace(/\.pgn$/i, "");
      };
    }
  };
  box();
  root.querySelectorAll("#rlKind button").forEach(b => b.onclick = () => {
    o.kind = b.dataset.k; save();
    root.querySelectorAll("#rlKind button").forEach(x => x.setAttribute("aria-pressed", x === b));
    if (o.kind !== "pgn") { o.meOn = true; $("rlMe").checked = true; syncMe(); }
    box();
  });
  const syncMe = () => { root.querySelector(".rl-me").classList.toggle("gone", !$("rlMe").checked); root.querySelector(".rl-hero").classList.toggle("gone", $("rlMe").checked); };
  $("rlMe").onchange = () => { o.meOn = $("rlMe").checked; save(); syncMe(); };
  root.querySelectorAll("#rlTh button").forEach(b => b.onclick = () => { o.th = +b.dataset.v; save(); root.querySelectorAll("#rlTh button").forEach(x => x.setAttribute("aria-pressed", x === b)); });
  $("rlMin").onchange = e => { o.min = +e.target.value; save(); };
  $("rlSlow").onchange = e => { o.slow = e.target.checked; save(); };
  $("rlImpGo").onclick = async () => {
    const say = t => { $("rlImpSay").innerHTML = t; };
    if (jobRun && JOB && JOB.state === "run") { say("Уже идёт обработка — дождись или отмени её."); return; }
    const kind = o.kind || "pgn", me = $("rlMe").checked;
    const nick = kind === "pgn" ? "" : ($("rlNick").value || "").trim();
    if (kind !== "pgn") { if (!nick) { say("Нужен ник."); return; } o["nick_" + kind] = nick; o.n = +$("rlN").value; }
    const meNick = me ? (($("rlMeNick").value || "").trim() || nick) : "";
    if (me && !meNick) { say("Впиши свой ник — по нему сайт поймёт, за кого ты играл."); return; }
    o.me = meNick; o.hero = me ? "" : ($("rlHero").value || "").trim(); save();
    const col = ($("rlCol").value || "").trim() || (me ? "Мои партии" : o.hero || "Подборка");
    const opts = { kind, nick, n: o.n, me: meNick, hero: o.hero, th: o.th, min: o.min, slow: o.slow };
    $("rlImpGo").disabled = true;
    try {
      const list = await collect(kind === "pgn" ? $("rlSrc").value : "", opts, t => say('<span class="rvspin"></span> ' + h(t)));
      if (!list.length) { say("Не нашёл ни одной партии."); $("rlImpGo").disabled = false; return; }
      say(`Партий: ${list.length}. Запускаю…`);
      await startJob(list, opts, col);
      filt.g = "all";
      renderLib();
    } catch (e) {
      say("Не получилось: " + h(e.message || e));
      $("rlImpGo").disabled = false;
    }
  };
}
async function dropCol(col) {
  if (!confirm(`Убрать подборку «${col}» из библиотеки? Твои сыгранные партии и задачи останутся.`)) return;
  Object.keys(S.lib).forEach(k => { if (S.lib[k].col === col) delete S.lib[k]; });
  save();
  IMP = IMP.filter(g => g.group !== col);
  filt.g = "all";
  renderLib();
}

/* ============================================================
   разметка раздела
   ============================================================ */
let root, view = "lib", cur = null, filt = { g: "all", s: "all" }, ORIG = null;
function mount() {
  root = document.createElement("section");
  root.id = "vReal";
  root.className = "gone";
  (document.querySelector(".wrap") || document.body).appendChild(root);

  const top = document.querySelector("header.top"), anchor = $("navReview");
  if (top) {
    const b = document.createElement("button");
    b.className = "navbtn"; b.id = "navReal"; b.textContent = "♔ Реализация";
    b.addEventListener("click", () => open("lib"));
    if (anchor) top.insertBefore(b, anchor); else top.appendChild(b);
  }
  const books = $("books");
  if (books && books.parentElement) {
    const p = document.createElement("div");
    p.className = "promo";
    p.innerHTML = '<div class="pi">♔</div><div class="pb"><h3>Реализация перевеса</h3>' +
      "<p>Партия чемпиона доходит до выигранной позиции — дальше доигрываешь сам против движка " +
      "и сверяешься, как реализовал Крамник, Фишер или Карпов. После партии — разбор твоих ошибок.</p></div>" +
      '<button class="go">Тренировать →</button>';
    p.querySelector(".go").onclick = () => open("lib");
    books.parentElement.insertBefore(p, books);
  }
  const orig = window.show;
  if (typeof orig === "function") {
    window.show = function () {
      hide();
      return orig.apply(this, arguments);
    };
    ORIG = orig;
  }
  document.addEventListener("keydown", onKey);
}
function hide() {
  if (!root || root.classList.contains("gone")) return;
  root.classList.add("gone");
  const b = $("navReal"); if (b) b.classList.remove("on");
}
async function open(v, arg) {
  const orig = ORIG;
  /* приложение переключаем на нейтральный экран — оно глушит свои движки — и прячем всё */
  if (typeof orig === "function" && root.classList.contains("gone")) { try { orig("books"); } catch (e) {} }
  document.querySelectorAll(".wrap > section").forEach(s => { if (s !== root) s.classList.add("gone"); });
  const ns = $("navStats"); if (ns) ns.classList.remove("on");
  root.classList.remove("gone");
  const b = $("navReal"); if (b) b.classList.add("on");
  document.body.classList.remove("zen", "wide");
  if (!SEED) {
    root.innerHTML = '<div class="rl-load"><span class="rvspin"></span> Загружаю позиции…</div>';
    const ok = await loadSeed();
    if (!ok) { root.innerHTML = '<div class="rl-load">Не получилось загрузить real-seed.js. Обнови страницу.</div>'; return; }
  }
  reload();
  if (!open.loaded) { open.loaded = true; await loadImported(); }
  go(v, arg);
}
function go(v, arg) {
  view = v;
  window.scrollTo(0, 0);
  if (v === "lib") renderLib();
  else if (v === "pos") renderPos(arg);
  else if (v === "play") renderPlay();
  else if (v === "rep") renderRep();
  else if (v === "puz") { PZ = null; renderPuz(); }
  else if (v === "prof") renderProf();
  else if (v === "champ") renderChamp(arg);
}
const crumb = (here, mid) =>
  `<div class="crumb"><button data-rl="books">Мои сборники</button><span class="sep">/</span>` +
  (here ? `<button data-rl="lib">Реализация перевеса</button>` : `<span>Реализация перевеса</span>`) +
  (mid ? `<span class="sep">/</span>${mid}` : "") +
  (here ? `<span class="sep">/</span><span>${here}</span>` : "") + "</div>";
function bindCrumbs() {
  root.querySelectorAll("[data-rl]").forEach(b => b.onclick = () => {
    const t = b.dataset.rl;
    if (t === "books") { stopGame(); window.show("books"); }
    else if (t === "lib") { leavePlay(); go("lib"); }
    else if (t === "pos") { leavePlay(); go("pos", cur); }
  });
}
function leavePlay() { /* партия остаётся в памяти — её можно продолжить из библиотеки */ }

/* ---------- библиотека ---------- */
function renderLib() {
  const list = items();
  const st = list.map(g => statusOf(g.pid).k);
  const won = st.filter(k => k === "clean" || k === "won").length, clean = st.filter(k => k === "clean").length;
  const due = duePuz().length, lv = S.cfg.lvl[S.cfg.opp];
  const groups = ["all"].concat([...new Set(list.map(g => g.group))]);
  const vis = list.filter(g => (filt.g === "all" || g.group === filt.g) &&
    (filt.s === "all" || (filt.s === "new" ? statusOf(g.pid).k === "new" :
      filt.s === "fail" ? statusOf(g.pid).k === "fail" : ["clean", "won"].indexOf(statusOf(g.pid).k) >= 0)));
  const live = G && !G.over;
  root.innerHTML = crumb() +
    `<div class="hero"><h1>Реализация перевеса</h1>
      <p>Метод Рамеша, тренера Гукеша и Прагнанандхи: партия чемпиона идёт до момента, когда у него уже выиграно —
      дальше не смотришь, а доигрываешь сам против Stockfish. Потом сверяешься, как реализовал чемпион.
      Стартовые позиции отобрал тренер из партий Крамника, Фишера и Карпова; ниже можно добавить свои базы и свои партии.</p></div>` +
    (live ? `<div class="rl-banner"><span>Партия не закончена: <b>${h(G.item.title)}</b></span>
      <button class="rvgo" id="rlResume">Продолжить партию</button></div>` : "") +
    `<div class="rl-tiles">
      <div class="rl-tile"><b>${list.length}</b><span>позиций</span></div>
      <div class="rl-tile"><b>${won}</b><span>реализовано</span></div>
      <div class="rl-tile"><b>${clean}</b><span>чисто, без подарков</span></div>
      <button class="rl-tile act" id="rlPuzGo" ${due ? "" : "disabled"}><b>${due}</b><span>${due ? "задач из ошибок — решать →" : "задач из ошибок к повтору"}</span></button>
      <button class="rl-tile act" id="rlProfGo"><b>${OPP_NAME[S.cfg.opp].split(" ")[0]} · ${lv}</b><span>соперник · профиль →</span></button>
    </div>
    <div class="rl-filters">
      <div class="rvseg" id="rlG">${groups.map(g => `<button data-g="${h(g)}" aria-pressed="${filt.g === g}">${g === "all" ? "Все" : h(g)}</button>`).join("")}</div>
      <div class="rvseg" id="rlS">${[["all", "Все"], ["new", "Новые"], ["fail", "Не дожал"], ["won", "Реализовал"]]
        .map(([k, t]) => `<button data-s="${k}" aria-pressed="${filt.s === k}">${t}</button>`).join("")}</div>
    </div>
    ${filt.g !== "all" && list.some(g => g.imported && g.group === filt.g) ? `<div class="rl-row" style="margin:-6px 0 14px"><button class="ghost" id="rlDrop">Убрать подборку «${h(filt.g)}»</button></div>` : ""}
    ${IMP.missing ? `<p class="rvhint">${IMP.missing} ${plural(IMP.missing, "позиция", "позиции", "позиций")} с другого устройства не подтянулись: их разбор не найден ни здесь, ни в общем кэше.</p>` : ""}
    <div class="rl-grid" id="rlGrid"></div>` +
    (vis.length ? "" : '<p class="rvhint">Под этот фильтр позиций нет.</p>') +
    (vis.length > LIB_PAGE * libPage ? `<div class="rl-row"><button class="ghost" id="rlMore">Показать ещё (${vis.length - LIB_PAGE * libPage})</button></div>` : "") +
    `<div class="rvcard rl-job gone" id="rlJob"></div>` + importCard();
  const grid = $("rlGrid");
  vis.slice(0, LIB_PAGE * libPage).forEach(g => {
    const n = nodesOf(g), fen = (n[g.k] || n[n.length - 1]).fen, s = statusOf(g.pid);
    const el = document.createElement("button");
    el.className = "rl-card";
    el.innerHTML = `<div class="th">${mini(fen, g.hero === "b")}</div><div class="bd">
      <div class="tt">${h(g.title)}${g.year ? ` <i>${h(g.year)}</i>` : ""}</div>
      <div class="mt">Играешь за ${h(heroName(g))} (${g.hero === "w" ? "белые" : "чёрные"}) · <b>${evTxt(evAt(g, g.k))}</b></div>
      <div class="tg">${(g.tags || []).map(t => `<span>${h(t)}</span>`).join("")}</div>
      <span class="pill rl-st ${s.k}">${s.t}</span></div>`;
    el.onclick = () => go("pos", g.pid);
    grid.appendChild(el);
  });
  root.querySelectorAll("#rlG button").forEach(b => b.onclick = () => { filt.g = b.dataset.g; libPage = 1; renderLib(); });
  root.querySelectorAll("#rlS button").forEach(b => b.onclick = () => { filt.s = b.dataset.s; libPage = 1; renderLib(); });
  $("rlPuzGo").onclick = () => due && go("puz");
  $("rlProfGo").onclick = () => go("prof");
  if (live) $("rlResume").onclick = () => go("play");
  if ($("rlMore")) $("rlMore").onclick = () => { libPage++; renderLib(); };
  if ($("rlDrop")) $("rlDrop").onclick = () => dropCol(filt.g);
  bindImport();
  paintJob();
  bindCrumbs();
}
const LIB_PAGE = 48;
let libPage = 1;

/* ---------- позиция: просмотр до точки и настройки ---------- */
let PV = { i: 0 };
function renderPos(pid) {
  const g = itemById(pid);
  if (!g) { go("lib"); return; }
  cur = pid;
  const nodes = nodesOf(g);
  if (PV.pid !== pid) PV = { pid, i: g.k };
  const flip = g.hero === "b", n = nodes[PV.i];
  const rs = S.res.filter(r => r.pid === pid).slice(-8).reverse();
  const opp = S.cfg.opp, lv = S.cfg.lvl[opp];
  const oppSide = g.hero === "w" ? g.black : g.white;
  root.innerHTML = crumb(h(g.title)) +
    `<div class="rvgrid"><div class="rvboardbox">
      <div class="rvtools"><span class="who">${PV.i === g.k ? "Тренировочная позиция" : "Ход партии " + Math.ceil(PV.i / 2)}</span>
        <div class="sp"></div><span class="who">${h(g.white)} — ${h(g.black)}</span></div>
      <div class="rvbwrap"><div class="rvebar" id="rlBar"><i></i><b></b></div><div class="boardgrid" id="rlBoard"></div></div>
      <div class="rvnav"><button id="rlF">⏮</button><button id="rlP">◀</button><button id="rlN">▶</button><button id="rlL" title="К тренировочной позиции">⏭</button></div>
      <p class="rvhint">Партию можно пролистать до тренировочной позиции. Что было дальше — откроется после твоей попытки.</p>
    </div>
    <div class="rvpanel">
      <div class="rvcard"><h4>Тренировочная позиция</h4>
        <div class="rl-big">${h(g.title)}${g.year ? " · " + h(g.year) : ""}</div>
        <p class="rl-p">Ход ${g.hero === "w" ? "белых" : "чёрных"}. Играешь за <b>${h(heroName(g))}</b> —
          оценка Stockfish <b>${evTxt(evAt(g, g.k))}</b>. Задача — довести до победы.</p>
        <div class="tg rl-tags">${(g.tags || []).map(t => `<span>${h(t)}</span>`).join("")}</div>
        ${g.ka != null && g.ka !== g.k ? `<p class="rvhint">Алгоритм поставил бы точку на ${Math.floor(g.ka / 2) + 1}-м ходу, тренер — на ${Math.floor(g.k / 2) + 1}-м.</p>` : ""}
      </div>
      <div class="rvcard"><h4>Соперник</h4>
        <div class="rvseg rl-seg" id="rlOpp">
          <button data-o="stub" aria-pressed="${opp === "stub"}">Упрямый защитник</button>
          <button data-o="nodes" aria-pressed="${opp === "nodes"}">Ограничение глубины</button></div>
        <p class="rvhint" style="margin-top:8px">${opp === "stub"
          ? "Выбирает среди лучших ходов с небольшим допуском, не зевает, избегает разменов — как защищается человек."
          : "Полноценный движок с маленьким лимитом расчёта: ошибается, потому что не видит далеко."}</p>
        <div class="rl-row"><span class="rvhint" style="margin:0">Уровень</span>
          <div class="rvseg rl-lv" id="rlLv">${Array.from({ length: LVL }, (_, i) => `<button data-l="${i + 1}" aria-pressed="${lv === i + 1}">${i + 1}</button>`).join("")}</div></div>
        <label class="opcheck" style="margin-top:10px"><input type="checkbox" id="rlAd" ${S.cfg.adapt ? "checked" : ""}>
          адаптивно: чистая победа — уровень выше, не дожал — ниже</label>
        <div class="rl-row"><span class="rvhint" style="margin:0">Часы</span>
          <div class="rvseg" id="rlClk">${[["0", "без часов"], ["600+5", "10+5"], ["900+10", "15+10"]]
            .map(([k, t]) => `<button data-c="${k}" aria-pressed="${S.cfg.clock === k}">${t}</button>`).join("")}</div></div>
      </div>
      <div class="rvcard"><div class="rvacts" style="margin-top:0">
        <button class="go" id="rlPlay">Играть за ${h(heroName(g))} →</button>
        <button id="rlRev" title="Ты за проигрывающую сторону против сильного движка">Обратная сторона: защищаться за ${h(oppSide)}</button>
        <button id="rlChamp">${g.mine ? "Как ты сыграл тогда" : "Как реализовал чемпион"}</button></div>
        <p class="rvhint">Полную партию лучше смотреть после своей попытки.</p></div>
      ${rs.length ? `<div class="rvcard"><h4>Попытки</h4><div class="rl-hist">${rs.map(histRow).join("")}</div></div>` : ""}
    </div></div>`;
  drawBoard($("rlBoard"), n.fen, { flip, last: n.from ? [n.from, n.to] : null, check: checkSq(n.fen) });
  ebar($("rlBar"), g.ev[PV.i] || 0, n.fen, flip);
  const step = i => { PV.i = clamp(i, 0, g.k); renderPos(pid); };
  $("rlF").onclick = () => step(0); $("rlP").onclick = () => step(PV.i - 1);
  $("rlN").onclick = () => step(PV.i + 1); $("rlL").onclick = () => step(g.k);
  root.querySelectorAll("#rlOpp button").forEach(b => b.onclick = () => { S.cfg.opp = b.dataset.o; save(); renderPos(pid); });
  root.querySelectorAll("#rlLv button").forEach(b => b.onclick = () => { S.cfg.lvl[S.cfg.opp] = +b.dataset.l; save(); renderPos(pid); });
  root.querySelectorAll("#rlClk button").forEach(b => b.onclick = () => { S.cfg.clock = b.dataset.c; save(); renderPos(pid); });
  $("rlAd").onchange = e => { S.cfg.adapt = e.target.checked; save(); };
  $("rlPlay").onclick = () => newGame(g, false);
  $("rlRev").onclick = () => newGame(g, true);
  $("rlChamp").onclick = () => {
    if (!resOf(pid).length && !confirm("Ты ещё не играл эту позицию. Всё равно открыть, как сыграл чемпион?")) return;
    go("champ", { pid, back: "pos" });
  };
  bindCrumbs();
}
const RES_T = { win: "победа", draw: "ничья", loss: "поражение" };
function histRow(r) {
  const d = new Date(r.t);
  const tx = r.rev ? (r.result === "loss" ? "не удержал" : "удержал") : RES_T[r.result];
  return `<div class="rl-hr"><span>${d.getDate()}.${String(d.getMonth() + 1).padStart(2, "0")}</span>
    <b class="${r.result}">${tx}</b><span>${r.rev ? "защита" : OPP_NAME[r.opp].split(" ")[0].toLowerCase() + " " + r.lvl}</span>
    <span>${r.mist.length} ${plural(r.mist.length, "ошибка", "ошибки", "ошибок")}${r.rev ? "" : r.fair ? "" : " · подарок"}</span></div>`;
}

/* ============================================================
   партия
   ============================================================ */
let G = null, clockT = null;
function newGame(g, rev) {
  stopGame();
  const nodes = nodesOf(g), start = nodes[g.k].fen;
  const user = rev ? other(g.hero) : g.hero;
  const cl = S.cfg.clock !== "0" ? S.cfg.clock.split("+").map(Number) : null;
  G = {
    id: uid(), item: g, rev, user, start, fens: [start], ucis: [], sans: [], last: null, sel: null,
    over: null, keys: { [posKey(start)]: 1 }, hopeless: 0, thinking: false, flip: user === "b",
    opp: S.cfg.opp, lvl: S.cfg.lvl[S.cfg.opp], promo: null, view: -1,
    clock: cl ? { t: { w: cl[0] * 1000, b: cl[0] * 1000 }, inc: cl[1] * 1000, started: false, ts: 0 } : null
  };
  cur = g.pid;
  go("play");
  E.load().then(ok => {
    if (!ok) { setStatus("Stockfish не загрузился — нужен интернет для первого запуска.", "bad"); return; }
    if (sideOf(start) !== user) oppTurn();
    else setStatus();
  });
}
function stopGame() {
  if (clockT) { clearInterval(clockT); clockT = null; }
  if (G && !G.over) E.stopAll();
}
const gFen = () => G.fens[G.fens.length - 1];
function renderPlay() {
  if (!G) { go("lib"); return; }
  const g = G.item, oppName = G.user === g.hero ? (g.hero === "w" ? g.black : g.white) : heroName(g);
  root.innerHTML = crumb(G.rev ? "Защита" : "Партия", `<button data-rl="pos">${h(g.title)}</button>`) +
    `<div class="rvgrid"><div class="rvboardbox">
      <div class="rvtools"><button class="ghost" id="rlFlip">⇅ Перевернуть</button><div class="sp"></div>
        <span class="who">${G.rev ? "Защищаешься" : "Реализуешь"} · соперник: ${G.rev ? "Stockfish в полную силу" : OPP_NAME[G.opp].toLowerCase() + ", уровень " + G.lvl}</span></div>
      <div class="rl-pl" id="rlTop"></div>
      <div class="rl-bwrap"><div class="boardgrid" id="rlBoard"></div><div class="rl-promo gone" id="rlPromo"></div></div>
      <div class="rl-pl" id="rlBot"></div>
    </div>
    <div class="rvpanel">
      <div class="rvcard"><div class="rl-status" id="rlStatus"></div>
        <div class="rl-moves" id="rlMoves"></div>
        <div class="rvacts"><button id="rlResign">Сдаться</button><button id="rlStop">Закончить и разобрать</button></div>
        <p class="rvhint">Оценки во время партии не видно — как за доской. ← → листают ходы, клик по ходу — тоже.</p></div>
    </div></div>`;
  G.oppName = oppName;
  bindBoard($("rlBoard"), onSq);
  $("rlFlip").onclick = () => { G.flip = !G.flip; paint(); };
  $("rlResign").onclick = () => { if (!G.over && confirm("Сдаться?")) endGame("loss", "resignU"); };
  $("rlStop").onclick = () => { if (!G.over && confirm("Закончить партию сейчас и разобрать?")) endGame(G.rev ? "draw" : "draw", "stopped"); };
  bindCrumbs();
  paint();
  if (G.clock && !clockT) clockT = setInterval(tick, 200);
}
function paint() {
  if (!G || view !== "play") return;
  const i = G.view < 0 ? G.fens.length - 1 : G.view, fen = G.fens[i];
  const last = i > 0 ? [G.ucis[i - 1].slice(0, 2), G.ucis[i - 1].slice(2, 4)] : null;
  drawBoard($("rlBoard"), fen, { flip: G.flip, sel: G.view < 0 ? G.sel : null, last, check: checkSq(fen) });
  const top = G.flip ? "w" : "b", bot = other(top);
  $("rlTop").innerHTML = plHtml(top); $("rlBot").innerHTML = plHtml(bot);
  let mv = "", f0 = G.start;
  G.sans.forEach((s, k) => {
    const fen0 = G.fens[k], white = sideOf(fen0) === "w";
    if (white || k === 0) mv += `<span class="no">${moveLab(fen0)}</span>`;
    mv += `<button class="rl-m${k + 1 === i ? " cur" : ""}" data-k="${k + 1}">${fig(s, sideOf(fen0))}</button>`;
  });
  $("rlMoves").innerHTML = mv || '<span class="rvhint" style="margin:0">Ходов пока нет.</span>';
  $("rlMoves").querySelectorAll(".rl-m").forEach(b => b.onclick = () => { G.view = +b.dataset.k === G.fens.length - 1 ? -1 : +b.dataset.k; paint(); });
  $("rlMoves").scrollTop = 1e6;
  setStatus();
  void f0;
}
function plHtml(side) {
  const me = side === G.user, name = me ? "Ты" : G.oppName;
  let clk = "";
  if (G.clock) {
    let t = G.clock.t[side];
    if (G.clock.started && !G.over && sideOf(gFen()) === side) t -= Date.now() - G.clock.ts;
    t = Math.max(0, t);
    const m = Math.floor(t / 60000), s = Math.floor(t / 1000) % 60;
    clk = `<span class="rl-clk${sideOf(gFen()) === side && !G.over ? " on" : ""}${t < 30000 ? " low" : ""}">${m}:${String(s).padStart(2, "0")}</span>`;
  }
  return `<span class="dot ${side}"></span><b>${h(name)}</b>${clk}`;
}
function tick() {
  if (!G || !G.clock || G.over) { clearInterval(clockT); clockT = null; return; }
  if (!G.clock.started) return;
  const side = sideOf(gFen()), left = G.clock.t[side] - (Date.now() - G.clock.ts);
  if (view === "play") { $("rlTop").innerHTML = plHtml(G.flip ? "w" : "b"); $("rlBot").innerHTML = plHtml(G.flip ? "b" : "w"); }
  if (left <= 0) { G.clock.t[side] = 0; endGame(side === G.user ? "loss" : "win", "time"); }
}
function setStatus(txt, kind) {
  const el = $("rlStatus");
  if (!el || !G) return;
  if (!txt) {
    if (G.over) { txt = "Партия окончена"; kind = ""; }
    else if (G.thinking) { txt = '<span class="rvspin"></span> Соперник думает…'; kind = ""; }
    else if (sideOf(gFen()) === G.user) { txt = "Твой ход"; kind = "go"; }
    else { txt = "Ход соперника"; kind = ""; }
  }
  el.className = "rl-status " + (kind || "");
  el.innerHTML = txt;
}
function onSq(kind, sq) {
  if (!G || G.over || G.view >= 0 || view !== "play") { if (G && G.view >= 0) { G.view = -1; paint(); } return; }
  const fen = gFen(), pos = parseFen(fen);
  const can = (from, to) => from && to !== from && legalTargets(fen, from).indexOf(to) >= 0;
  if (kind === "down") {
    if (can(G.sel, sq)) { userMove(G.sel, sq); return; }
    const pc = pos[sq];
    G.sel = pc && (isW(pc) ? "w" : "b") === G.user ? sq : null;
    paint();
  } else if (can(G.sel, sq)) userMove(G.sel, sq);
}
function userMove(from, to, promo) {
  if (!G || G.over || G.thinking) return;
  const fen = gFen();
  if (sideOf(fen) !== G.user || legalTargets(fen, from).indexOf(to) < 0) return;
  const pc = parseFen(fen)[from];
  if (pc && pc.toLowerCase() === "p" && (to[1] === "8" || to[1] === "1") && !promo) { askPromo(from, to); return; }
  const mv = makeMove(fen, from, to, promo);
  if (!mv) return;
  push(mv);
  if (!checkEnd()) oppTurn();
}
function askPromo(from, to) {
  const el = $("rlPromo"), c = G.user;
  el.innerHTML = ["q", "r", "b", "n"].map(p => {
    const code = c === "w" ? p.toUpperCase() : p;
    return `<button data-p="${p}"><svg viewBox="0 0 100 100"><use href="#pc-${code}"/></svg></button>`;
  }).join("") + '<button data-p="" class="x">✕</button>';
  el.classList.remove("gone");
  el.querySelectorAll("button").forEach(b => b.onclick = () => {
    el.classList.add("gone");
    if (b.dataset.p) userMove(from, to, b.dataset.p); else { G.sel = null; paint(); }
  });
}
function push(mv) {
  const mover = sideOf(gFen());
  if (G.clock) {
    const now = Date.now();
    if (G.clock.started) G.clock.t[mover] += G.clock.inc - (now - G.clock.ts);
    else if (mover === G.user) G.clock.started = true;   /* на первом ходу время не идёт */
    G.clock.ts = now;
  }
  G.fens.push(mv.fen); G.ucis.push(mv.uci); G.sans.push(mv.san);
  G.sel = null; G.view = -1;
  const k = posKey(mv.fen); G.keys[k] = (G.keys[k] || 0) + 1;
  paint();
}
async function oppTurn() {
  if (!G || G.over) return;
  G.thinking = true; setStatus();
  const gid = G.id, fen = gFen();
  const ok = await E.load();
  if (!ok || !G || G.id !== gid || G.over) { if (G) G.thinking = false; return; }
  const t0 = Date.now();
  const r = await engineMove(fen, G.rev);
  if (!G || G.id !== gid || G.over || r.cancelled) return;
  /* ход не мгновенный — так легче следить за доской */
  const wait = Math.max(0, 350 - (Date.now() - t0));
  if (wait) await new Promise(res => setTimeout(res, wait));
  if (!G || G.id !== gid || G.over) return;
  G.thinking = false;
  if (!G.rev) {
    G.hopeless = r.cp <= -900 ? G.hopeless + 1 : 0;
    if (G.hopeless >= 3) { endGame("win", "resign"); return; }
  }
  if (!r.uci) { setStatus("Движок не ответил", "bad"); return; }
  const mv = makeMove(fen, r.uci.slice(0, 2), r.uci.slice(2, 4), r.uci[4]);
  if (!mv) { setStatus("Движок не ответил", "bad"); return; }
  push(mv);
  checkEnd();
}
function insufficient(fen) {
  const p = Object.values(parseFen(fen)).map(x => x.toLowerCase()).filter(x => x !== "k");
  return !p.length || (p.length === 1 && (p[0] === "n" || p[0] === "b"));
}
function checkEnd() {
  const fen = gFen();
  if (!anyLegal(fen)) {
    if (inCheckNow(fen)) endGame(sideOf(fen) === G.user ? "loss" : "win", "mate");
    else endGame("draw", "stalemate");
    return true;
  }
  if (G.keys[posKey(fen)] >= 3) { endGame("draw", "rep"); return true; }
  if (+fen.split(" ")[4] >= 100) { endGame("draw", "50"); return true; }
  if (insufficient(fen)) { endGame("draw", "material"); return true; }
  return false;
}
const WHY = {
  mate: "мат", stalemate: "пат", rep: "троекратное повторение", "50": "правило 50 ходов",
  material: "недостаточно материала", resign: "соперник сдался", resignU: "ты сдался",
  time: "время", stopped: "партия остановлена"
};

/* ---------- конец партии и разбор ---------- */
let REP = null;
async function endGame(result, why) {
  if (!G || G.over) return;
  G.over = { result, why };
  G.thinking = false;
  if (clockT) { clearInterval(clockT); clockT = null; }
  E.stopAll();
  REP = { g: G, busy: true, done: 0, i: G.fens.length - 1, src: "me" };
  go("rep");
  const an = await analyse(G);
  if (!REP || REP.g !== G) return;
  Object.assign(REP, build(G, an));
  REP.busy = false;
  record(G, REP);
  if (view === "rep") renderRep();
}
async function analyse(game) {
  await E.load();
  const ev = [], best = [];
  for (let i = 0; i < game.fens.length; i++) {
    const f = game.fens[i];
    if (!anyLegal(f)) { ev[i] = inCheckNow(f) ? (sideOf(f) === "w" ? -MATE : MATE) : 0; best[i] = ""; }
    else {
      const r = await E.go({ fen: f, depth: AN_DEPTH, multipv: 1 });
      const cp = cpOf(r.pvs[0]);
      ev[i] = sideOf(f) === "w" ? cp : -cp; best[i] = r.best;
    }
    if (REP && REP.g === game) { REP.done = i + 1; const b = $("rlAnBar"); if (b) { b.style.width = (100 * REP.done / game.fens.length) + "%"; $("rlAnTx").textContent = REP.done + " / " + game.fens.length; } }
  }
  return { ev, best };
}
function build(game, an) {
  const s = sgn(game.user), pov = an.ev.map(e => e * s);
  const mist = [], gifts = [];
  let loss = 0, n = 0;
  for (let i = 0; i < game.fens.length - 1; i++) {
    const mover = sideOf(game.fens[i]);
    if (mover === game.user) {
      const l = Math.max(0, C(pov[i]) - C(pov[i + 1]));
      loss += l; n++;
      if (l >= MISTAKE && pov[i + 1] < 500) mist.push({ i, loss: l, before: pov[i], after: pov[i + 1], san: game.sans[i], uci: game.ucis[i], best: an.best[i] });
    } else {
      const gain = C(pov[i + 1]) - C(pov[i]);
      if (gain >= GIFT && pov[i] < 800) gifts.push({ i, gain, san: game.sans[i] });
    }
  }
  return { pov, best: an.best, mist, gifts, fair: !gifts.length, avg: n ? Math.round(loss / n) : 0, myMoves: n };
}
function record(game, rep) {
  const r = game.over.result;
  let lvlChange = 0;
  if (!game.rev && S.cfg.adapt && game.over.why !== "stopped") {
    const clean = r === "win" && rep.fair && rep.mist.length <= 1;
    const lv = S.cfg.lvl[game.opp];
    if (clean && lv < LVL) lvlChange = 1;
    else if (r !== "win" && lv > 1) lvlChange = -1;
    S.cfg.lvl[game.opp] = lv + lvlChange;
  }
  rep.lvlChange = lvlChange;
  S.res.push({
    id: game.id, pid: game.item.pid, t: Date.now(), rev: game.rev, opp: game.opp, lvl: game.lvl,
    clock: S.cfg.clock, result: r, why: game.over.why, plies: game.ucis.length, my: rep.myMoves,
    mist: rep.mist.map(m => ({ i: m.i, l: m.loss })), gifts: rep.gifts.length, fair: rep.fair, avg: rep.avg,
    ucis: game.ucis.join(" "), lvlChange
  });
  /* три худшие ошибки — в задачи с интервальным повторением */
  rep.mist.slice().sort((a, b) => b.loss - a.loss).slice(0, 3).forEach(m => {
    if (!m.best) return;
    const id = game.id + "-" + m.i;
    S.puz[id] = { id, pid: game.item.pid, fen: game.fens[m.i], played: m.uci, playedSan: m.san, best: m.best,
      bestCp: m.before, side: game.user, made: Date.now(), due: Date.now(), step: 0, reps: 0, fails: 0 };
  });
  rep.puzAdded = Math.min(3, rep.mist.filter(m => m.best).length);
  save();
}

function renderRep() {
  if (!REP) { go("lib"); return; }
  const game = REP.g, g = game.item;
  if (REP.busy) {
    root.innerHTML = crumb("Разбор", `<button data-rl="pos">${h(g.title)}</button>`) +
      `<div class="rvprog"><h2>${verdictTitle(game)}</h2><p>Stockfish разбирает твою партию</p>
       <div class="rvbar"><i id="rlAnBar" style="width:${100 * REP.done / game.fens.length}%"></i></div>
       <div class="rvpct" id="rlAnTx">${REP.done} / ${game.fens.length}</div></div>`;
    bindCrumbs();
    return;
  }
  const champ = nodesOf(g).slice(g.k), myN = REP.myMoves, chN = champMoves(g);
  const r = game.over.result, rev = game.rev;
  const giftTx = REP.gifts.length ? REP.gifts.slice(0, 2).map(x => `${moveLab(game.fens[x.i])}${fig(x.san, sideOf(game.fens[x.i]))} (${evTxt(-x.gain)})`).join(", ") : "";
  root.innerHTML = crumb("Разбор", `<button data-rl="pos">${h(g.title)}</button>`) +
    `<div class="rvgrid"><div class="rvboardbox">
      <div class="rvtools"><div class="rvseg" id="rlSrc">
        <button data-s="me" aria-pressed="${REP.src === "me"}">Твоя партия</button>
        <button data-s="ch" aria-pressed="${REP.src === "ch"}">Как сыграл ${h(heroName(g))}</button></div>
        <div class="sp"></div><span class="who" id="rlWhere"></span></div>
      <div class="rvbwrap"><div class="rvebar" id="rlBar"><i></i><b></b></div><div class="boardgrid" id="rlBoard"></div></div>
      <div class="rvnav"><button id="rlF">⏮</button><button id="rlP">◀</button><button id="rlN">▶</button><button id="rlL">⏭</button></div>
      <div class="rl-moves rl-moves2" id="rlMoves"></div>
    </div>
    <div class="rvpanel">
      <div class="rvcard rl-verd ${rev ? (r === "loss" ? "bad" : "good") : (r === "win" ? "good" : "bad")}">
        <div class="rl-big">${verdictTitle(game)}</div>
        <p class="rl-p">${h(WHY[game.over.why] || "")}${rev ? ` · продержался ${myN} ${plural(myN, "ход", "хода", "ходов")}` : ""}</p>
        ${!rev ? `<div class="rl-cmp"><div><b>${myN}</b><span>${plural(myN, "ход", "хода", "ходов")} у тебя</span></div>
          <div><b>${chN}</b><span>у ${h(heroName(g))}</span></div>
          <div><b>${REP.mist.length}</b><span>${plural(REP.mist.length, "ошибка", "ошибки", "ошибок")}</span></div>
          <div><b>${(REP.avg / 100).toFixed(2)}</b><span>теряешь за ход</span></div></div>` : ""}
        ${!rev && r === "win" ? (REP.fair ? '<p class="rl-fair good">✓ Честная реализация — соперник не дарил.</p>'
          : `<p class="rl-fair bad">Победа с подарком: соперник ошибся — ${giftTx}. В «чистые» не идёт.</p>`) : ""}
        ${REP.lvlChange ? `<p class="rl-p">Адаптивный уровень: ${REP.lvlChange > 0 ? "соперник стал сильнее" : "соперник стал слабее"} — теперь ${S.cfg.lvl[game.opp]}.</p>` : ""}
      </div>
      <div class="rvcard"><h4>График оценки</h4><div class="rl-graph" id="rlGraph"></div>
        <div class="rl-leg"><span class="me">ты</span>${rev ? "" : `<span class="ch">${h(heroName(g))}</span>`}<span class="er">ошибка</span></div></div>
      <div class="rvcard"><h4>Где терял больше пешки</h4>${REP.mist.length ? `<div class="rvkey">${REP.mist.map((m, x) =>
        `<button class="rvkeyb" data-m="${x}"><span class="mv">${moveLab(game.fens[m.i])}${fig(m.san, game.user)}</span>
         <span class="tx">${evTxt(m.before)} → ${evTxt(m.after)} · лучше ${fig(sanOf(game.fens[m.i], m.best), game.user)}</span></button>`).join("")}</div>`
        : '<p class="rl-p" style="margin:0">Ни одного хода с потерей больше пешки.</p>'}
        ${REP.puzAdded ? `<p class="rvhint">${REP.puzAdded} ${plural(REP.puzAdded, "позиция ушла", "позиции ушли", "позиций ушло")} в задачи из ошибок — вернутся на повтор.</p>` : ""}</div>
      <div class="rvcard"><h4>Твой путь и ходы чемпиона</h4><div class="rl-path" id="rlPath"></div></div>
      <div class="rvcard"><div class="rvacts" style="margin-top:0">
        <button class="go" id="rlAgain">${rev ? "Защищаться ещё раз" : "Сыграть ещё раз"}</button>
        <button id="rlOther">${rev ? "Играть за чемпиона" : "Обратная сторона"}</button>
        ${duePuz().length ? `<button id="rlPz">Задачи из ошибок · ${duePuz().length}</button>` : ""}
        <button id="rlBack">К позициям</button></div></div>
    </div></div>`;
  paintRep();
  renderGraph();
  renderPath(champ);
  root.querySelectorAll("#rlSrc button").forEach(b => b.onclick = () => {
    REP.src = b.dataset.s; REP.i = 0; REP.mark = null;
    root.querySelectorAll("#rlSrc button").forEach(x => x.setAttribute("aria-pressed", x === b));
    paintRep();
  });
  const len = () => (REP.src === "me" ? game.fens.length : champ.length) - 1;
  const step = i => { REP.i = clamp(i, 0, len()); REP.mark = null; paintRep(); };
  $("rlF").onclick = () => step(0); $("rlP").onclick = () => step(REP.i - 1);
  $("rlN").onclick = () => step(REP.i + 1); $("rlL").onclick = () => step(len());
  REP.step = step;
  root.querySelectorAll("[data-m]").forEach(b => b.onclick = () => {
    const m = REP.mist[+b.dataset.m];
    REP.src = "me"; REP.i = m.i; REP.mark = m;
    root.querySelectorAll("#rlSrc button").forEach(x => x.setAttribute("aria-pressed", x.dataset.s === "me"));
    paintRep();
  });
  $("rlAgain").onclick = () => newGame(g, rev);
  $("rlOther").onclick = () => newGame(g, !rev);
  if ($("rlPz")) $("rlPz").onclick = () => go("puz");
  $("rlBack").onclick = () => go("lib");
  bindCrumbs();
}
function verdictTitle(game) {
  const r = game.over.result;
  if (game.over.why === "stopped") return "Партия остановлена";
  if (game.rev) return r === "loss" ? "Не удержал" : r === "win" ? "Отыгрался и выиграл!" : "Удержал!";
  return r === "win" ? "Реализовал!" : r === "draw" ? "Ничья — перевес упущен" : "Поражение";
}
function sanOf(fen, uci) {
  if (!uci) return "";
  const mv = makeMove(fen, uci.slice(0, 2), uci.slice(2, 4), uci[4]);
  return mv ? mv.san : uci;
}
function paintRep() {
  const game = REP.g, g = game.item, champ = nodesOf(g).slice(g.k);
  let fen, last = null, cpw = null, arrows = [];
  if (REP.src === "me") {
    fen = game.fens[REP.i];
    if (REP.i > 0) { const u = game.ucis[REP.i - 1]; last = [u.slice(0, 2), u.slice(2, 4)]; }
    cpw = REP.pov[REP.i] * sgn(game.user);
    if (REP.mark) {
      arrows.push([REP.mark.uci.slice(0, 2), REP.mark.uci.slice(2, 4), "red"]);
      if (REP.mark.best) arrows.push([REP.mark.best.slice(0, 2), REP.mark.best.slice(2, 4), "green"]);
    }
  } else {
    const n = champ[REP.i];
    fen = n.fen; if (n.from) last = [n.from, n.to];
    cpw = g.ev[g.k + REP.i];
  }
  drawBoard($("rlBoard"), fen, { flip: game.user === "b", last, check: checkSq(fen), arrows });
  ebar($("rlBar"), cpw || 0, fen, game.user === "b");
  $("rlWhere").textContent = REP.mark ? "красная — твой ход, зелёная — лучше" : (REP.i ? "после " + REP.i + "-го полухода" : "тренировочная позиция");
  /* список ходов текущей партии */
  const list = REP.src === "me" ? game.sans.map((s, k) => ({ san: s, fen: game.fens[k] }))
    : champ.slice(1).map((n, k) => ({ san: n.san, fen: champ[k].fen }));
  const misK = REP.src === "me" ? new Set(REP.mist.map(m => m.i)) : new Set();
  let mv = "";
  list.forEach((x, k) => {
    if (sideOf(x.fen) === "w" || k === 0) mv += `<span class="no">${moveLab(x.fen)}</span>`;
    mv += `<button class="rl-m${k + 1 === REP.i ? " cur" : ""}${misK.has(k) ? " bad" : ""}" data-k="${k + 1}">${fig(x.san, sideOf(x.fen))}</button>`;
  });
  const host = $("rlMoves");
  host.innerHTML = mv;
  host.querySelectorAll(".rl-m").forEach(b => b.onclick = () => REP.step(+b.dataset.k));
  const c = host.querySelector(".cur"); if (c) c.scrollIntoView({ block: "nearest" });
}
function renderGraph() {
  const game = REP.g, g = game.item, s = sgn(game.user);
  const me = REP.pov, ch = game.rev ? [] : g.ev.slice(g.k).map(e => e * s);
  const n = Math.max(me.length, ch.length, 2) - 1;
  const xy = (i, cp) => [(100 * i / n).toFixed(2), (100 - Wcp(cp)).toFixed(2)];
  const line = arr => arr.map((cp, i) => (i ? "L" : "M") + xy(i, cp).join(" ")).join(" ");
  const dots = REP.mist.map(m => { const p = xy(m.i + 1, me[m.i + 1]); return `<circle cx="${p[0]}" cy="${p[1]}" r="2.2"/>`; }).join("");
  $("rlGraph").innerHTML = `<svg viewBox="0 0 100 100" preserveAspectRatio="none">
    <line class="mid" x1="0" y1="50" x2="100" y2="50"/>
    ${ch.length ? `<path class="ch" d="${line(ch)}"/>` : ""}<path class="me" d="${line(me)}"/>
    <g class="er">${dots}</g></svg>`;
  $("rlGraph").querySelector("svg").onclick = e => {
    const r = e.currentTarget.getBoundingClientRect();
    REP.src = "me"; REP.mark = null;
    REP.step(Math.round(clamp((e.clientX - r.left) / r.width, 0, 1) * n));
  };
}
function renderPath(champ) {
  const game = REP.g;
  const rows = Math.max(game.sans.length, champ.length - 1);
  let same = true, html = '<div class="rl-pr hd"><span></span><span>ты</span><span>чемпион</span></div>';
  for (let k = 0; k < rows; k++) {
    const mine = game.ucis[k], his = champ[k + 1] && champ[k + 1].uci;
    const eq = same && mine && mine === his;
    if (!eq) same = false;
    const fen = game.fens[k] || champ[k].fen;
    const mineS = game.sans[k] ? fig(game.sans[k], sideOf(game.fens[k])) : "";
    const hisS = champ[k + 1] ? fig(champ[k + 1].san, sideOf(champ[k].fen)) : "";
    const mt = REP.mist.some(m => m.i === k);
    html += `<div class="rl-pr${eq ? " eq" : ""}${sideOf(fen) === game.user ? " mine" : ""}"><span>${moveLab(fen)}</span>` +
      `<span class="${mt ? "bad" : ""}">${mineS}</span><span>${hisS}</span></div>`;
  }
  const eqN = (() => { let c = 0; for (let k = 0; k < game.ucis.length; k++) { if (champ[k + 1] && game.ucis[k] === champ[k + 1].uci) c++; else break; } return c; })();
  $("rlPath").innerHTML = `<p class="rl-p" style="margin-top:0">${eqN ? `Первые ${eqN} ${plural(eqN, "полуход совпал", "полухода совпали", "полуходов совпали")} с партией.` : "С первого хода ты пошёл своим путём."}</p>` +
    `<div class="rl-pathw">${html}</div>`;
}

/* ---------- партия чемпиона целиком ---------- */
let CV = null;
function renderChamp(arg) {
  const g = itemById(arg.pid); if (!g) { go("lib"); return; }
  const nodes = nodesOf(g);
  if (!CV || CV.pid !== g.pid) CV = { pid: g.pid, i: g.k };
  const n = nodes[CV.i], flip = g.hero === "b";
  root.innerHTML = crumb("Партия чемпиона", `<button data-rl="pos">${h(g.title)}</button>`) +
    `<div class="rvgrid"><div class="rvboardbox">
      <div class="rvtools"><span class="who">${h(g.white)} — ${h(g.black)} · ${h(g.result)}</span></div>
      <div class="rvbwrap"><div class="rvebar" id="rlBar"><i></i><b></b></div><div class="boardgrid" id="rlBoard"></div></div>
      <div class="rvnav"><button id="rlF">⏮</button><button id="rlP">◀</button><button id="rlN">▶</button><button id="rlL">⏭</button></div></div>
    <div class="rvpanel"><div class="rvcard"><h4>Ходы</h4><div class="rl-moves rl-moves2" id="rlMoves"></div>
      <p class="rvhint">Подсвечен ход, с которого начиналась тренировка.</p></div>
      <div class="rvcard"><div class="rvacts" style="margin-top:0"><button class="go" id="rlPlay">Играть эту позицию</button>
      <button id="rlBack">К позиции</button></div></div></div></div>`;
  drawBoard($("rlBoard"), n.fen, { flip, last: n.from ? [n.from, n.to] : null, check: checkSq(n.fen) });
  ebar($("rlBar"), g.ev[CV.i] || 0, n.fen, flip);
  let mv = "";
  nodes.slice(1).forEach((x, k) => {
    const f = nodes[k].fen;
    if (sideOf(f) === "w" || k === 0) mv += `<span class="no">${moveLab(f)}</span>`;
    mv += `<button class="rl-m${k + 1 === CV.i ? " cur" : ""}${k === g.k ? " start" : ""}" data-k="${k + 1}">${fig(x.san, sideOf(f))}</button>`;
  });
  $("rlMoves").innerHTML = mv;
  const step = i => { CV.i = clamp(i, 0, nodes.length - 1); renderChamp(arg); };
  CV.step = step;
  $("rlMoves").querySelectorAll(".rl-m").forEach(b => b.onclick = () => step(+b.dataset.k));
  const c = $("rlMoves").querySelector(".cur"); if (c) c.scrollIntoView({ block: "nearest" });
  $("rlF").onclick = () => step(0); $("rlP").onclick = () => step(CV.i - 1);
  $("rlN").onclick = () => step(CV.i + 1); $("rlL").onclick = () => step(nodes.length - 1);
  $("rlPlay").onclick = () => newGame(g, false);
  $("rlBack").onclick = () => go("pos", g.pid);
  bindCrumbs();
}

/* ---------- задачи из ошибок ---------- */
let PZ = null;
function renderPuz() {
  const list = duePuz();
  if (!PZ || !PZ.p || !S.puz[PZ.p.id]) PZ = { p: list[0] || null, state: "ask", sel: null, solved: 0, total: PZ ? PZ.total : 0 };
  const p = PZ.p;
  if (!p) {
    root.innerHTML = crumb("Задачи из ошибок") +
      `<div class="rvcard rl-empty"><div class="rl-big">Все задачи из ошибок решены</div>
       <p class="rl-p">Новые появятся после партий — сюда уходят три самых дорогих твоих хода. Решённые вернутся на повтор через день, три, неделю…</p>
       <div class="rvacts"><button class="go" id="rlBack">К позициям</button></div></div>`;
    $("rlBack").onclick = () => go("lib");
    bindCrumbs();
    return;
  }
  const g = itemById(p.pid), flip = p.side === "b";
  const arrows = PZ.state !== "ask" ? [[p.best.slice(0, 2), p.best.slice(2, 4), "green"], [p.played.slice(0, 2), p.played.slice(2, 4), "red"]] : [];
  const fen = PZ.fen || p.fen;
  root.innerHTML = crumb("Задачи из ошибок") +
    `<div class="rvgrid"><div class="rvboardbox">
      <div class="rvtools"><span class="who">${g ? h(g.title) : ""}</span><div class="sp"></div><span class="who">осталось ${list.length}</span></div>
      <div class="rl-bwrap"><div class="boardgrid" id="rlBoard"></div><div class="rl-promo gone" id="rlPromo"></div></div></div>
    <div class="rvpanel"><div class="rvcard">
      <h4>Найди ход сильнее</h4>
      <p class="rl-p">В своей партии здесь ты сыграл <b>${fig(p.playedSan, p.side)}</b> и потерял больше пешки.
        Ход ${p.side === "w" ? "белых" : "чёрных"} — найди лучше. Засчитывается любой ход не хуже лучшего больше чем на полпешки.</p>
      <div class="rl-status ${PZ.state === "ok" ? "go" : PZ.state === "bad" ? "bad" : ""}" id="rlPzSay">${PZ.say || "Твой ход"}</div>
      <div class="rvacts">${PZ.state === "ask" ? '<button id="rlShow">Показать ответ</button>' : '<button class="go" id="rlNext">Дальше →</button>'}
        <button id="rlBack">К позициям</button></div>
      <p class="rvhint">Решил — задача вернётся через ${IVL[Math.min(p.step, IVL.length - 1)]} ${plural(IVL[Math.min(p.step, IVL.length - 1)], "день", "дня", "дней")}. Не решил — завтра.</p>
    </div></div></div>`;
  drawBoard($("rlBoard"), fen, { flip, sel: PZ.state === "ask" ? PZ.sel : null, arrows, last: PZ.last, check: checkSq(fen) });
  bindBoard($("rlBoard"), (kind, sq) => {
    if (PZ.state !== "ask" || PZ.busy) return;
    const pos = parseFen(p.fen), can = (a, b) => a && a !== b && legalTargets(p.fen, a).indexOf(b) >= 0;
    if (kind === "down") {
      if (can(PZ.sel, sq)) { puzTry(PZ.sel, sq); return; }
      const pc = pos[sq];
      PZ.sel = pc && (isW(pc) ? "w" : "b") === p.side ? sq : null;
      renderPuz();
    } else if (can(PZ.sel, sq)) puzTry(PZ.sel, sq);
  });
  if ($("rlShow")) $("rlShow").onclick = () => puzDone(false, "Лучший ход — " + fig(sanOf(p.fen, p.best), p.side) + ". Вернётся завтра.");
  if ($("rlNext")) $("rlNext").onclick = () => { PZ = { p: null, total: PZ.total }; renderPuz(); };
  $("rlBack").onclick = () => go("lib");
  bindCrumbs();
}
async function puzTry(from, to, promo) {
  const p = PZ.p, pc = parseFen(p.fen)[from];
  if (pc && pc.toLowerCase() === "p" && (to[1] === "8" || to[1] === "1") && !promo) {
    const el = $("rlPromo");
    el.innerHTML = ["q", "r", "b", "n"].map(x => `<button data-p="${x}"><svg viewBox="0 0 100 100"><use href="#pc-${p.side === "w" ? x.toUpperCase() : x}"/></svg></button>`).join("");
    el.classList.remove("gone");
    el.querySelectorAll("button").forEach(b => b.onclick = () => { el.classList.add("gone"); puzTry(from, to, b.dataset.p); });
    return;
  }
  const mv = makeMove(p.fen, from, to, promo);
  if (!mv) return;
  PZ.sel = null; PZ.fen = mv.fen; PZ.last = [from, to];
  if (mv.uci === p.played) { puzDone(false, "Это и есть ход из партии. Лучше — " + fig(sanOf(p.fen, p.best), p.side) + "."); return; }
  if (mv.uci === p.best) { puzDone(true, "Да! Это лучший ход."); return; }
  PZ.busy = true; PZ.say = '<span class="rvspin"></span> Проверяю…'; renderPuz();
  await E.load();
  let cp;
  if (!anyLegal(mv.fen)) cp = inCheckNow(mv.fen) ? MATE : 0;
  else { const r = await E.go({ fen: mv.fen, depth: 13, multipv: 1 }); cp = -cpOf(r.pvs[0]); }
  PZ.busy = false;
  const loss = C(p.bestCp) - C(cp);
  if (loss <= 50) puzDone(true, `Годится: ${evTxt(cp)} — почти как лучший ${fig(sanOf(p.fen, p.best), p.side)}.`);
  else puzDone(false, `После ${fig(mv.san, p.side)} оценка ${evTxt(cp)}, а было ${evTxt(p.bestCp)}. Лучше — ${fig(sanOf(p.fen, p.best), p.side)}.`);
}
function puzDone(ok, say) {
  const p = S.puz[PZ.p.id];
  if (p) {
    p.reps++;
    if (ok) { p.step = Math.min(p.step + 1, IVL.length); p.due = Date.now() + IVL[p.step - 1] * DAY; }
    else { p.step = 0; p.fails++; p.due = Date.now() + DAY; }
    p.last = Date.now();
    save();
  }
  PZ.state = ok ? "ok" : "bad"; PZ.say = say;
  if (!ok) { PZ.fen = PZ.p.fen; PZ.last = null; }
  renderPuz();
}

/* ---------- профиль слабостей ---------- */
function renderProf() {
  const all = S.res.filter(r => !r.rev && r.why !== "stopped"), rv = S.res.filter(r => r.rev);
  const pct = (a, b) => b ? Math.round(100 * a / b) + "%" : "—";
  const wins = all.filter(r => r.result === "win"), clean = wins.filter(r => r.fair && r.mist.length <= 1);
  const avg = all.length ? (all.reduce((a, r) => a + r.avg, 0) / all.length / 100).toFixed(2) : "—";
  const mpg = all.length ? (all.reduce((a, r) => a + r.mist.length, 0) / all.length).toFixed(1) : "—";
  const by = keyFn => {
    const m = {};
    all.forEach(r => { const g = itemById(r.pid); if (!g) return; [].concat(keyFn(g)).forEach(k => { if (!k) return; const x = m[k] || (m[k] = { n: 0, w: 0, c: 0 }); x.n++; if (r.result === "win") x.w++; if (r.result === "win" && r.fair && r.mist.length <= 1) x.c++; }); });
    return Object.entries(m).sort((a, b) => b[1].n - a[1].n);
  };
  const tbl = rows => rows.length ? `<table class="rvtab rl-tab"><tr class="hd"><td></td><td class="n">партий</td><td class="n">реализовал</td><td class="n">чисто</td></tr>` +
    rows.map(([k, x]) => `<tr><td>${h(k)}</td><td class="n">${x.n}</td><td class="n">${pct(x.w, x.n)}</td><td class="n">${pct(x.c, x.n)}</td></tr>`).join("") + "</table>"
    : '<p class="rl-p" style="margin:0">Пока нет сыгранных партий.</p>';
  /* где теряешь: номер твоего хода от начала тренировки */
  const bins = [["1–5", 1, 5], ["6–10", 6, 10], ["11–20", 11, 20], ["21+", 21, 999]].map(([t, a, b]) => {
    let c = 0; all.forEach(r => r.mist.forEach(m => { const mv = Math.floor(m.i / 2) + 1; if (mv >= a && mv <= b) c++; }));
    return [t, c];
  });
  const bmax = Math.max(1, ...bins.map(b => b[1]));
  const held = rv.filter(r => r.result !== "loss").length;
  root.innerHTML = crumb("Профиль") +
    `<div class="pagehead"><h1>Профиль реализации</h1><span class="sub">по ${all.length} ${plural(all.length, "партии", "партиям", "партиям")}</span></div>
    <div class="rl-tiles">
      <div class="rl-tile"><b>${pct(wins.length, all.length)}</b><span>реализовано</span></div>
      <div class="rl-tile"><b>${pct(clean.length, all.length)}</b><span>чисто, без подарков</span></div>
      <div class="rl-tile"><b>${avg}</b><span>теряешь за ход, пешек</span></div>
      <div class="rl-tile"><b>${mpg}</b><span>ошибок за партию</span></div>
      <div class="rl-tile"><b>${rv.length ? held + " / " + rv.length : "—"}</b><span>удержал в защите</span></div>
    </div>
    <div class="rl-two">
      <div class="rvcard"><h4>По типу позиции</h4>${tbl(by(g => g.tags || []))}</div>
      <div class="rvcard"><h4>По чемпиону</h4>${tbl(by(g => g.group))}</div>
      <div class="rvcard"><h4>Где теряешь перевес</h4>
        <p class="rl-p" style="margin-top:0">На каком твоём ходу после начала тренировки случаются ошибки.</p>
        <div class="rl-bins">${bins.map(([t, c]) => `<div><span>${t}</span><i style="width:${100 * c / bmax}%"></i><b>${c}</b></div>`).join("")}</div></div>
      <div class="rvcard"><h4>Соперник</h4>
        <p class="rl-p" style="margin-top:0">Упрямый защитник — уровень <b>${S.cfg.lvl.stub}</b>, ограничение глубины — <b>${S.cfg.lvl.nodes}</b>.
          ${S.cfg.adapt ? "Уровень меняется сам: чистая победа — выше, не дожал — ниже." : "Адаптивный уровень выключен."}</p>
        ${S.res.length ? `<div class="rl-hist">${S.res.slice(-10).reverse().map(r => { const g = itemById(r.pid); return `<div class="rl-hr"><span>${g ? h(g.title) : ""}</span>` + histRow(r).replace('<div class="rl-hr">', "").replace(/<\/div>$/, "") + "</div>"; }).join("")}</div>` : ""}</div>
    </div>
    <div class="rvacts"><button id="rlBack">К позициям</button></div>`;
  $("rlBack").onclick = () => go("lib");
  bindCrumbs();
}

/* ---------- клавиатура ---------- */
function onKey(e) {
  if (!root || root.classList.contains("gone")) return;
  if (e.target && /input|textarea|select/i.test(e.target.tagName)) return;
  const d = e.key === "ArrowLeft" ? -1 : e.key === "ArrowRight" ? 1 : 0;
  if (!d) return;
  if (view === "rep" && REP && REP.step && !REP.busy) { REP.step(REP.i + d); e.preventDefault(); }
  else if (view === "champ" && CV && CV.step) { CV.step(CV.i + d); e.preventDefault(); }
  else if (view === "play" && G) {
    const n = G.fens.length - 1, i = G.view < 0 ? n : G.view, j = clamp(i + d, 0, n);
    G.view = j === n ? -1 : j; paint(); e.preventDefault();
  }
}

mount();
setTimeout(() => { resumeJob().then(() => { if (JOB && JOB.state === "run") loadSeed().then(() => { if (!open.loaded) { open.loaded = true; loadImported(); } }); }); }, 3000);
window.kombiReal = { open, state: () => S };
})();
