/* ============================================================
   Экран «Статистика».

   Ничего не знает про внутренности приложения, кроме моста
   window.KOMBI_APP (сборники и прогресс) и window.kombiStats
   (дневник активности и хранилище внешних аккаунтов).

   Данные берёт из трёх мест:
     • дневник решённых задач — считает auth.js по записям прогресса;
     • lichess  — /api/user/{ник} и экспорт партий;
     • chess.com — /pub/player/{ник}/stats и месячные архивы партий.

   Рейтинг по дням восстанавливается из архивов партий, поэтому
   график показывает историю и за те дни, когда сайт не открывался.
   Рейтинг задач lichess так не достать — его снимаем раз в день.
   ============================================================ */

(function () {
  "use strict";

  var APP = window.KOMBI_APP;
  var S = window.kombiStats;
  if (!APP || !S) return;

  /* ---------- палитра ----------
     Слоты 1 и 2 проверенной палитры. Обе пары проходят контроль на
     различимость при дальтонизме и контраст к фону в обеих темах. */
  var SERIES = {
    li: { name: "lichess",   light: "#2a78d6", dark: "#3987e5" },
    cc: { name: "chess.com", light: "#eb6834", dark: "#d95926" }
  };

  function dark() {
    var t = document.documentElement.getAttribute("data-theme");
    if (t === "dark") return true;
    if (t === "light") return false;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function col(k) { return dark() ? SERIES[k].dark : SERIES[k].light; }
  function ink(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }

  /* ---------- даты ---------- */

  function key(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") +
           "-" + String(d.getDate()).padStart(2, "0");
  }
  function daysBack(n) {
    var out = [], d = new Date();
    d.setHours(12, 0, 0, 0);
    for (var i = n - 1; i >= 0; i--) {
      var x = new Date(d); x.setDate(d.getDate() - i);
      out.push(key(x));
    }
    return out;
  }
  var MON = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
  function human(k) {
    var p = k.split("-");
    return parseInt(p[2], 10) + " " + MON[parseInt(p[1], 10) - 1];
  }
  function plural(n, one, few, many) {
    var a = Math.abs(n) % 100, b = a % 10;
    if (a > 10 && a < 20) return many;
    if (b > 1 && b < 5) return few;
    if (b === 1) return one;
    return many;
  }

  /* ---------- сводка по сборникам ---------- */

  function totals() {
    var prog = APP.prog || {}, solved = 0, all = 0, stars = 0, maxStars = 0;
    APP.BOOKS.forEach(function (b) {
      var p = prog[b.id] || {};
      all += b.puzzles.length;
      maxStars += b.puzzles.length * 3;
      b.puzzles.forEach(function (z) {
        if ((p[z.n] || {}).solved) solved++;
        stars += APP.starsOf(b.id, z.n);
      });
    });
    return { solved: solved, all: all, stars: stars, maxStars: maxStars };
  }

  function sections() {
    var prog = APP.prog || {}, out = [];
    APP.BOOKS.forEach(function (b) {
      var p = prog[b.id] || {};
      (b.secs || []).forEach(function (s) {
        var items = s.items || [];
        if (!items.length) return;
        var done = items.filter(function (z) { return (p[z.n] || {}).solved; }).length;
        if (!done) return;                       /* нетронутые разделы не показываем */
        out.push({ book: b.title, name: s.t || s.title || "Раздел",
                   done: done, all: items.length, pct: done / items.length });
      });
    });
    out.sort(function (a, b) { return b.pct - a.pct; });
    return out;
  }

  /* серия: сколько дней подряд решались задачи */
  function streak() {
    var st = S.stats(), d = new Date(), n = 0;
    d.setHours(12, 0, 0, 0);
    if (!(st[key(d)] || {}).solved) d.setDate(d.getDate() - 1);   /* сегодня ещё можно успеть */
    while ((st[key(d)] || {}).solved) { n++; d.setDate(d.getDate() - 1); }
    return n;
  }

  /* ---------- внешние сайты ---------- */

  function jget(url, accept) {
    return fetch(url, accept ? { headers: { Accept: accept } } : undefined)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return accept === "application/x-ndjson" ? r.text() : r.json();
      });
  }

  var CC_CLASS = { rapid: "rapid", blitz: "blitz", bullet: "bullet" };

  function fetchChesscom(user, days) {
    var u = encodeURIComponent(String(user).toLowerCase());
    var now = new Date(), months = [];
    for (var i = 0; i < 2; i++) {
      var m = new Date(now.getFullYear(), now.getMonth() - i, 1);
      months.push(m.getFullYear() + "/" + String(m.getMonth() + 1).padStart(2, "0"));
    }

    return jget("https://api.chess.com/pub/player/" + u + "/stats").then(function (st) {
      var cur = {};
      Object.keys(CC_CLASS).forEach(function (c) {
        var box = st["chess_" + c];
        if (box && box.last) cur[c] = box.last.rating;
      });
      if (st.puzzle_rush && st.puzzle_rush.best) cur.rush = st.puzzle_rush.best.score;

      return Promise.all(months.map(function (m) {
        return jget("https://api.chess.com/pub/player/" + u + "/games/" + m)
          .catch(function () { return { games: [] }; });
      })).then(function (chunks) {
        var today = S.today(), fromGames = {}, counted = {};
        chunks.forEach(function (ch) {
          (ch.games || []).forEach(function (g) {
            var me = (g.white && g.white.username || "").toLowerCase() === String(user).toLowerCase()
              ? g.white : g.black;
            if (!me) return;
            var k = key(new Date(g.end_time * 1000));
            if (!days[k]) days[k] = {};
            var slot = days[k].cc || (days[k].cc = {});
            if (!counted[k]) { slot.games = 0; counted[k] = true; }   /* пересчитываем с нуля */
            var cls = CC_CLASS[g.time_class];
            if (cls) slot[cls] = me.rating;                 /* последняя партия дня и есть итог */
            slot.games = (slot.games || 0) + 1;
            if (k === today && cls) fromGames[cls] = true;
          });
        });

        /* За сегодня профиль авторитетнее того, что лежит в хранилище:
           иначе однажды попавшее туда чужое значение не перезапишется никогда.
           Уступаем только сегодняшним партиям — они точнее. */
        if (!days[today]) days[today] = {};
        var slot = days[today].cc || (days[today].cc = {});
        Object.keys(cur).forEach(function (c) {
          if (!fromGames[c]) slot[c] = cur[c];
        });
        return cur;
      });
    });
  }

  /* deep — тянуть ли архив партий. Он у lichess жёстко ограничен
     («не больше одного запроса за раз»), поэтому за историей ходим
     раз в шесть часов, а текущий рейтинг снимаем с профиля всегда. */
  function fetchLichess(user, days, deep) {
    var u = encodeURIComponent(user);
    return jget("https://lichess.org/api/user/" + u).then(function (p) {
      var perfs = p.perfs || {}, cur = {};
      ["bullet", "blitz", "rapid"].forEach(function (c) {
        if (perfs[c] && perfs[c].games) cur[c] = perfs[c].rating;
      });
      if (perfs.puzzle && perfs.puzzle.games) {
        cur.puzzle = perfs.puzzle.rating;
        cur.puzzleN = perfs.puzzle.games;
      }

      var fromGames = {};
      var finish = function () {
        var today = S.today();
        if (!days[today]) days[today] = {};
        var slot = days[today].li || (days[today].li = {});
        Object.keys(cur).forEach(function (c) {
          if (!fromGames[c]) slot[c] = cur[c];   /* профиль главнее старого снимка */
        });
        return cur;
      };
      if (!deep) return finish();

      var since = Date.now() - 45 * 86400000;
      return jget("https://lichess.org/api/games/user/" + u +
                  "?since=" + since + "&max=300&moves=false&pgnInJson=false",
                  "application/x-ndjson")
        .then(function (txt) {
          var counted = {};
          txt.split("\n").forEach(function (line) {
            if (!line.trim()) return;
            var g; try { g = JSON.parse(line); } catch (e) { return; }
            var pl = g.players || {};
            var side = (pl.white && pl.white.user && pl.white.user.name || "").toLowerCase()
              === String(user).toLowerCase() ? pl.white : pl.black;
            if (!side) return;
            var k = key(new Date(g.lastMoveAt || g.createdAt));
            if (!days[k]) days[k] = {};
            var slot = days[k].li || (days[k].li = {});
            if (!counted[k]) { slot.games = 0; counted[k] = true; }   /* пересчитываем с нуля */
            var after = (side.rating || 0) + (side.ratingDiff || 0);
            if (g.perf && after) slot[g.perf] = after;
            slot.games = (slot.games || 0) + 1;
            if (k === S.today() && g.perf) fromGames[g.perf] = true;
          });
        })
        /* экспорт партий может не отдаться (частые запросы) — текущий рейтинг
           из профиля всё равно запишем, историю доберём в следующий раз */
        .then(function () { deepDone = true; })
        .catch(noteErr("lichess"))
        .then(finish);
    });
  }

  var refreshing = false, deepDone = false;

  function refresh(force) {
    if (refreshing) return Promise.resolve();
    var e = S.ext(), acc = e.accounts || {};
    if (!acc.lichess && !acc.chesscom) return Promise.resolve();
    if (!force && e.fetchedAt && Date.now() - e.fetchedAt < 3600000) return Promise.resolve();

    refreshing = true;
    paintRefresh();
    if (!root.classList.contains("gone")) render();
    var days = Object.assign({}, e.days || {});
    var jobs = [];
    var deep = !e.liExportAt || Date.now() - e.liExportAt > 6 * 3600000;
    deepDone = false;
    if (acc.lichess)  jobs.push(fetchLichess(acc.lichess, days, deep).catch(noteErr("lichess")));
    if (acc.chesscom) jobs.push(fetchChesscom(acc.chesscom, days).catch(noteErr("chess.com")));

    return Promise.all(jobs).then(function () {
      e.days = days;
      e.fetchedAt = Date.now();
      if (deepDone) e.liExportAt = Date.now();
      S.saveExt(e);
    }).then(function () {
      refreshing = false;
      render();
    }, function () {
      refreshing = false;
      render();
    });
  }

  var errors = [];
  function noteErr(who) {
    return function (e) {
      var m = String(e && e.message || "");
      var text = m.indexOf("404") >= 0 ? "такого ника нет"
        : m.indexOf("429") >= 0 ? "сайт просит подождать — попробуй через минуту"
        : m.indexOf("403") >= 0 ? "профиль закрыт"
        : m ? m : "не ответил";
      errors.push(who + ": " + text);
    };
  }

  /* ============================================================
     Графики. Рисуем инлайновый SVG: подписи остаются текстом,
     а цвета берутся из темы на момент отрисовки.
     ============================================================ */

  var PADL = 38, PADR = 14, PADT = 12;

  /* Ширину системы координат берём по фактической ширине карточки: тогда
     10 px подписи в SVG остаются 10 px на экране и на телефоне читаются,
     а не сжимаются вместе с графиком. */
  function widthOf(host) {
    return Math.max(320, Math.min(760, Math.round(host.clientWidth || 720)));
  }

  function svgEl(n, attrs) {
    var el = document.createElementNS("http://www.w3.org/2000/svg", n);
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    return el;
  }

  /* И задачи, и рейтинг — величины целые, дробных делений на шкале быть
     не должно. `span` задаёт минимальный размах: без него одна-единственная
     точка растягивает ось в «1819.5 · 1820 · 1820.5». */
  function niceTicks(min, max, n, span) {
    span = span || 1;
    if (max - min < span) {
      var mid = (min + max) / 2;
      min = mid - span / 2; max = mid + span / 2;
    }
    var raw = (max - min) / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var step = [1, 2, 2.5, 5, 10].map(function (s) { return s * mag; })
      .find(function (s) { return s >= raw; }) || 10 * mag;
    step = Math.max(1, Math.round(step));                 /* только целые деления */
    var lo = Math.floor(min / step) * step, out = [];
    for (var v = lo; v <= max + step / 2; v += step) out.push(Math.round(v));
    return out;
  }

  /* столбики: решённые задачи по дням */
  function barChart(host, rows) {
    host.innerHTML = "";
    var W = widthOf(host);
    var H = 172, plotH = H - PADT - 26, max = Math.max(1, Math.max.apply(null, rows.map(function (r) { return r.v; })));
    var ticks = niceTicks(0, max, 3, 3);
    var top = ticks[ticks.length - 1];
    var innerW = W - PADL - PADR;
    var step = innerW / rows.length;
    var bw = Math.max(3, Math.min(18, step - 2));           /* 2px просвет между столбиками */

    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img",
      "aria-label": "Решённые задачи по дням" });

    ticks.forEach(function (t) {
      var y = PADT + plotH - (t / top) * plotH;
      svg.appendChild(svgEl("line", { x1: PADL, x2: W - PADR, y1: y, y2: y, class: "st-grid" }));
      var lab = svgEl("text", { x: PADL - 8, y: y + 3.5, class: "st-axis", "text-anchor": "end" });
      lab.textContent = t;
      svg.appendChild(lab);
    });

    rows.forEach(function (r, i) {
      var x = PADL + i * step + (step - bw) / 2;
      var h = r.v ? Math.max(3, (r.v / top) * plotH) : 0;
      var y = PADT + plotH - h;
      if (h) {
        var rad = Math.min(4, bw / 2, h);
        var p = "M" + x + " " + (y + h) + " V" + (y + rad) +
                " a" + rad + " " + rad + " 0 0 1 " + rad + " " + -rad +
                " h" + (bw - 2 * rad) +
                " a" + rad + " " + rad + " 0 0 1 " + rad + " " + rad +
                " V" + (y + h) + " Z";
        svg.appendChild(svgEl("path", { d: p, class: "st-barmark" }));
      }
      var hit = svgEl("rect", { x: PADL + i * step, y: PADT, width: step, height: plotH, class: "st-hit" });
      hit.addEventListener("mouseenter", function () {
        tip(host, PADL + i * step + step / 2, y, W, [
          { color: ink("--accent"), name: "решено", value: r.v }
        ], human(r.d));
      });
      hit.addEventListener("mouseleave", function () { hideTip(host); });
      svg.appendChild(hit);
    });

    axisLabels(svg, rows.map(function (r) { return r.d; }), H,
      function (i) { return PADL + i * step + step / 2; }, W);

    host.appendChild(svg);
  }

  /* линии: рейтинг по дням, одна серия на площадку */
  function lineChart(host, series, dates) {
    host.innerHTML = "";
    var live = series.filter(function (s) { return s.points.some(function (p) { return p.v != null; }); });
    if (!live.length) { host.appendChild(emptyBox("Нет данных за этот период.")); return; }

    var W = widthOf(host);
    var H = 210, plotH = H - PADT - 26;
    var vals = [];
    live.forEach(function (s) { s.points.forEach(function (p) { if (p.v != null) vals.push(p.v); }); });
    /* размах меньше 40 очков смотреть неинтересно — разворачиваем шкалу шире */
    var ticks = niceTicks(Math.min.apply(null, vals), Math.max.apply(null, vals), 4, 40);
    var lo = ticks[0], hi = ticks[ticks.length - 1];
    var innerW = W - PADL - PADR - 34;                       /* место под подпись у конца линии */
    var x = function (i) { return PADL + (dates.length < 2 ? innerW / 2 : (i / (dates.length - 1)) * innerW); };
    var y = function (v) { return PADT + plotH - ((v - lo) / (hi - lo || 1)) * plotH; };

    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img",
      "aria-label": "Рейтинг по дням" });

    ticks.forEach(function (t) {
      svg.appendChild(svgEl("line", { x1: PADL, x2: W - PADR, y1: y(t), y2: y(t), class: "st-grid" }));
      var lab = svgEl("text", { x: PADL - 8, y: y(t) + 3.5, class: "st-axis", "text-anchor": "end" });
      lab.textContent = t;
      svg.appendChild(lab);
    });

    live.forEach(function (s) {
      var d = "", open = false, last = null, played = [];
      s.points.forEach(function (p, i) {
        if (p.v == null) return;                             /* разрывы не соединяем сквозь пустоту */
        d += (open ? " L" : "M") + x(i) + " " + y(p.v);
        open = true; last = { i: i, v: p.v };
        if (p.real) played.push({ i: i, v: p.v });
      });
      if (!d) return;
      svg.appendChild(svgEl("path", { d: d, class: "st-line", stroke: col(s.key) }));

      /* кружок только там, где в этот день действительно играли */
      played.forEach(function (p) {
        svg.appendChild(svgEl("circle", { cx: x(p.i), cy: y(p.v), r: 3.5,
          fill: col(s.key), class: "st-dot" }));
      });

      if (last) {
        var lab = svgEl("text", { x: x(last.i) + 9, y: y(last.v) + 4, class: "st-dlabel" });
        lab.textContent = last.v;
        svg.appendChild(lab);
      }
    });

    /* перекрестие прячем display'ем, а не уводом за край: у svg включён
       overflow:visible, и уехавшая линия торчала бы слева от графика */
    var cross = svgEl("line", { class: "st-cross", y1: PADT, y2: PADT + plotH, x1: 0, x2: 0 });
    cross.style.display = "none";
    svg.appendChild(cross);

    var band = svgEl("rect", { x: PADL, y: PADT, width: W - PADL - PADR, height: plotH, class: "st-hit" });
    band.addEventListener("mousemove", function (ev) {
      var box = svg.getBoundingClientRect();
      var px = (ev.clientX - box.left) / box.width * W;
      var i = Math.max(0, Math.min(dates.length - 1,
        Math.round((px - PADL) / (innerW / Math.max(1, dates.length - 1)))));
      cross.style.display = "";
      cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i));
      var rows = live.map(function (s) {
        var p = s.points[i];
        return { color: col(s.key),
                 name: s.name + (p.v != null && !p.real ? " · не играл" : ""),
                 value: p.v == null ? "—" : p.v };
      });
      tip(host, x(i), PADT, W, rows, human(dates[i]));
    });
    band.addEventListener("mouseleave", function () {
      cross.style.display = "none";
      hideTip(host);
    });
    svg.appendChild(band);

    axisLabels(svg, dates, H, x, W);

    host.appendChild(svg);
  }

  /* Подписи дат: берём каждую n-ю и обязательно последнюю, но если последняя
     налезает на предыдущую — предыдущую убираем, иначе даты сливаются. */
  function axisLabels(svg, dates, H, xOf, W) {
    var room = Math.max(2, Math.floor((W - PADL - PADR) / 62));   /* подписи по ~62 px */
    var every = Math.max(1, Math.ceil(dates.length / room));
    var pick = [];
    dates.forEach(function (d, i) { if (!(i % every)) pick.push(i); });
    var last = dates.length - 1;
    if (pick[pick.length - 1] !== last) {
      if (xOf(last) - xOf(pick[pick.length - 1]) < 52) pick.pop();
      pick.push(last);
    }
    pick.forEach(function (i) {
      var lab = svgEl("text", { x: xOf(i), y: H - 8, class: "st-axis", "text-anchor": "middle" });
      lab.textContent = human(dates[i]);
      svg.appendChild(lab);
    });
  }

  function tip(host, sx, sy, vw, rows, title) {
    var el = host.querySelector(".st-tip");
    if (!el) { el = document.createElement("div"); el.className = "st-tip"; host.appendChild(el); }
    el.innerHTML = '<div class="st-d"></div>';
    el.querySelector(".st-d").textContent = title;
    rows.forEach(function (r) {
      var line = document.createElement("div");
      line.className = "st-r";
      var dot = document.createElement("i"); dot.style.background = r.color;
      var nm = document.createElement("span"); nm.textContent = r.name;
      var v = document.createElement("b"); v.textContent = r.value;
      line.appendChild(dot); line.appendChild(nm); line.appendChild(v);
      el.appendChild(line);
    });
    el.style.left = (sx / vw * 100) + "%";
    el.style.top = Math.max(0, sy - 6) + "px";
    el.hidden = false;
  }
  function hideTip(host) {
    var el = host.querySelector(".st-tip");
    if (el) el.hidden = true;
  }

  function emptyBox(text, title) {
    var d = document.createElement("div");
    d.className = "st-empty";
    if (title) { var b = document.createElement("b"); b.textContent = title; d.appendChild(b); }
    d.appendChild(document.createTextNode(text));
    return d;
  }

  /* ---------- разметка экрана ---------- */

  var root, state = { control: "rapid", range: 30, table: false };

  function build() {
    root = document.createElement("section");
    root.id = "vStats";
    root.className = "gone";
    root.innerHTML =
      '<div class="st-head">' +
        '<h1>Статистика</h1><span class="st-sub" id="stWho"></span>' +
        '<div class="st-sp"></div>' +
        '<button class="st-refresh" id="stRefresh">Обновить</button>' +
      '</div>' +
      '<div class="st-tiles" id="stTiles"></div>' +
      '<div class="st-card">' +
        '<h3>Задачи на сайте</h3><p class="st-cap">Сколько решено по дням — считается автоматически.</p>' +
        '<div class="st-bar"><div class="st-seg" id="stRange">' +
          '<button data-r="14" aria-pressed="false">2 недели</button>' +
          '<button data-r="30" aria-pressed="true">Месяц</button>' +
          '<button data-r="90" aria-pressed="false">3 месяца</button>' +
        '</div></div>' +
        '<div class="st-plot" id="stBars"></div>' +
      '</div>' +
      '<div class="st-card">' +
        '<h3>Рейтинг</h3><p class="st-cap">История собрана из архива партий, поэтому видно и те дни, когда сюда не заходил.</p>' +
        '<div class="st-bar"><div class="st-seg" id="stCtrl">' +
          '<button data-c="rapid" aria-pressed="true">Рапид</button>' +
          '<button data-c="blitz" aria-pressed="false">Блиц</button>' +
          '<button data-c="bullet" aria-pressed="false">Пуля</button>' +
          '<button data-c="puzzle" aria-pressed="false">Задачи</button>' +
        '</div><div class="st-sp"></div>' +
        '<button class="st-tbtn" id="stToggleTable">Показать таблицей</button></div>' +
        '<div class="st-leg" id="stLeg"></div>' +
        '<div class="st-plot" id="stLine"></div>' +
      '</div>' +
      '<div class="st-card">' +
        '<h3>Активность</h3><p class="st-cap" id="stMapCap">Задачи здесь и партии на обоих сайтах — день за днём.</p>' +
        '<div class="st-map" id="stMap"></div>' +
        '<div class="st-maplg"><span>реже</span><i data-l="0"></i><i data-l="1"></i>' +
          '<i data-l="2"></i><i data-l="3"></i><i data-l="4"></i><span>чаще</span></div>' +
      '</div>' +
      '<div class="st-card">' +
        '<h3>Разделы</h3><p class="st-cap">Где уже уверенно, а где стоит вернуться.</p>' +
        '<div class="st-themes" id="stThemes"></div>' +
      '</div>' +
      '<div class="st-card">' +
        '<h3>Аккаунты</h3><p class="st-cap">Ники нужны, чтобы подтягивать рейтинг и партии. Читаем только открытые данные, пароли не нужны.</p>' +
        '<div class="st-accs">' +
          '<div class="st-acc"><label for="stLi">lichess.org</label>' +
            '<div class="st-row"><input id="stLi" placeholder="ник на lichess" autocomplete="off" spellcheck="false"></div>' +
            '<div class="st-hint" id="stLiHint"></div></div>' +
          '<div class="st-acc"><label for="stCc">chess.com</label>' +
            '<div class="st-row"><input id="stCc" placeholder="ник на chess.com" autocomplete="off" spellcheck="false"></div>' +
            '<div class="st-hint" id="stCcHint"></div></div>' +
        '</div>' +
        '<div class="st-bar" style="margin-top:14px">' +
          '<button class="st-save" id="stSave">Сохранить и обновить</button>' +
          '<div class="st-sp"></div>' +
          '<button class="st-tbtn" id="stWipe">Очистить и собрать заново</button>' +
        '</div>' +
      '</div>';

    (document.querySelector(".wrap") || document.body).appendChild(root);

    root.querySelector("#stRange").addEventListener("click", function (e) {
      var b = e.target.closest("button[data-r]"); if (!b) return;
      state.range = +b.dataset.r; render();
    });
    root.querySelector("#stCtrl").addEventListener("click", function (e) {
      var b = e.target.closest("button[data-c]"); if (!b) return;
      state.control = b.dataset.c; render();
    });
    root.querySelector("#stToggleTable").addEventListener("click", function () {
      state.table = !state.table; render();
    });
    root.querySelector("#stRefresh").addEventListener("click", function () {
      errors = []; refresh(true);
    });
    root.querySelector("#stSave").addEventListener("click", saveAccounts);
    root.querySelector("#stWipe").addEventListener("click", wipeExternal);
  }

  /* Ник поменялся — собранная по нему история больше не наша. Если её не
     выбросить, в графике останутся цифры от прежнего аккаунта: новые дни
     допишутся, а старые так и будут висеть. */
  function saveAccounts() {
    var e = S.ext();
    e.accounts = e.accounts || {};
    var was = { lichess: e.accounts.lichess || "", chesscom: e.accounts.chesscom || "" };
    var now = {
      lichess:  root.querySelector("#stLi").value.trim(),
      chesscom: root.querySelector("#stCc").value.trim()
    };

    var drop = [];
    if (now.lichess.toLowerCase()  !== was.lichess.toLowerCase())  drop.push("li");
    if (now.chesscom.toLowerCase() !== was.chesscom.toLowerCase()) drop.push("cc");
    if (drop.length) {
      Object.keys(e.days || {}).forEach(function (d) {
        drop.forEach(function (k) { delete e.days[d][k]; });
        if (!Object.keys(e.days[d]).length) delete e.days[d];
      });
      if (drop.indexOf("li") >= 0) e.liExportAt = 0;
    }

    e.accounts = now;
    e.fetchedAt = 0;
    S.saveExt(e);
    errors = [];
    refresh(true);
  }

  /* выбрасывает всё, что натянуто с lichess и chess.com, и собирает заново —
     на случай, если в истории осели данные от прежнего ника */
  function wipeExternal() {
    if (!confirm("Удалить всё, что подтянуто с lichess и chess.com, и собрать заново?\n\n" +
                 "Решённые здесь задачи и дневник активности не тронутся.")) return;
    var e = S.ext();
    e.days = {};
    e.fetchedAt = 0;
    e.liExportAt = 0;
    S.saveExt(e);
    errors = [];
    refresh(true);
  }

  function paintRefresh() {
    var b = root && root.querySelector("#stRefresh");
    if (b) { b.disabled = refreshing; b.textContent = refreshing ? "Обновляю…" : "Обновить"; }
  }

  /* ---------- отрисовка ---------- */

  function render() {
    if (!root) return;
    paintRefresh();

    var st = S.stats(), e = S.ext(), acc = e.accounts || {}, t = totals();
    var u = S.user();
    root.querySelector("#stWho").textContent = u
      ? u.email
      : "без входа статистика считается только в этом браузере";

    /* --- плитки --- */
    var today = S.today(), tod = st[today] || {};
    var sk = streak();
    var extToday = (e.days || {})[today] || {};
    var games = ((extToday.li || {}).games || 0) + ((extToday.cc || {}).games || 0);
    var delta = bestDelta(e.days || {});

    var tiles = [
      { lab: "Решено сегодня", num: tod.solved || 0,
        note: (tod.stars || 0) + " " + plural(tod.stars || 0, "звезда", "звезды", "звёзд") },
      { lab: "Серия", num: sk, cls: sk ? "flame" : "",
        note: sk ? plural(sk, "день подряд", "дня подряд", "дней подряд") : "сегодня ещё не решал" },
      { lab: "Партий сегодня", num: games,
        note: acc.lichess || acc.chesscom ? "lichess и chess.com" : "аккаунты не привязаны" },
      delta
        ? { lab: "Рейтинг за день", num: (delta.v > 0 ? "+" : "") + delta.v,
            cls: delta.v > 0 ? "up" : delta.v < 0 ? "down" : "",
            note: delta.label }
        : { lab: "Всего решено", num: t.solved, note: "из " + t.all + " задач" }
    ];
    var host = root.querySelector("#stTiles");
    host.innerHTML = "";
    tiles.forEach(function (x) {
      var d = document.createElement("div");
      d.className = "st-tile";
      d.innerHTML = '<div class="st-k"></div><div class="st-v ' + (x.cls || "") + '"></div><div class="st-n"></div>';
      d.querySelector(".st-k").textContent = x.lab;
      d.querySelector(".st-v").textContent = x.num;
      d.querySelector(".st-n").textContent = x.note;
      host.appendChild(d);
    });

    /* --- столбики --- */
    root.querySelectorAll("#stRange button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(+b.dataset.r === state.range));
    });
    var dates = daysBack(state.range);
    barChart(root.querySelector("#stBars"),
      dates.map(function (d) { return { d: d, v: (st[d] || {}).solved || 0 }; }));

    /* --- рейтинг --- */
    root.querySelectorAll("#stCtrl button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.c === state.control));
    });
    var series = ["li", "cc"].map(function (k) {
      return {
        key: k, name: SERIES[k].name,
        points: dates.map(function (d) {
          var box = ((e.days || {})[d] || {})[k] || {};
          return { d: d, v: box[state.control] == null ? null : box[state.control] };
        })
      };
    });
    carryForward(series);

    var leg = root.querySelector("#stLeg");
    leg.innerHTML = "";
    series.forEach(function (s) {
      if (!s.points.some(function (p) { return p.v != null; })) return;
      var sp = document.createElement("span");
      var i = document.createElement("i"); i.style.background = col(s.key);
      sp.appendChild(i);
      sp.appendChild(document.createTextNode(s.name));
      leg.appendChild(sp);
    });

    var plot = root.querySelector("#stLine");
    root.querySelector("#stToggleTable").textContent = state.table ? "Показать графиком" : "Показать таблицей";

    if (refreshing) {
      var busy = document.createElement("span");
      busy.className = "st-busy";
      busy.textContent = "обновляю…";
      leg.appendChild(busy);
    }

    if (!acc.lichess && !acc.chesscom) {
      plot.innerHTML = "";
      plot.appendChild(emptyBox(
        "Впиши ники ниже — подтянем рейтинг и партии с обоих сайтов.",
        "Аккаунты не привязаны"));
    } else if (state.table) {
      plot.innerHTML = "";
      plot.appendChild(ratingTable(series, dates));
    } else {
      lineChart(plot, series, dates);
    }

    /* --- карта активности --- */
    heatmap(root.querySelector("#stMap"), st, e.days || {});

    /* --- разделы --- */
    var th = root.querySelector("#stThemes");
    th.innerHTML = "";
    var secs = sections();
    if (!secs.length) {
      th.appendChild(emptyBox("Реши хотя бы одну задачу — и здесь появится разбор по разделам."));
    } else {
      secs.slice(0, 10).forEach(function (s) {
        var d = document.createElement("div");
        d.className = "st-theme";
        d.innerHTML = '<div class="st-nm"><b></b><span></span></div><div class="pct"></div>' +
                      '<div class="track"><div class="fill"></div></div>';
        d.querySelector("b").textContent = s.name;
        d.querySelector(".st-nm span").textContent = s.book + " · " + s.done + " из " + s.all;
        d.querySelector(".pct").textContent = Math.round(s.pct * 100) + "%";
        d.querySelector(".fill").style.width = (s.pct * 100) + "%";
        th.appendChild(d);
      });
    }

    /* --- аккаунты --- */
    var li = root.querySelector("#stLi"), cc = root.querySelector("#stCc");
    if (document.activeElement !== li) li.value = acc.lichess || "";
    if (document.activeElement !== cc) cc.value = acc.chesscom || "";
    var liH = root.querySelector("#stLiHint"), ccH = root.querySelector("#stCcHint");
    liH.className = "st-hint"; ccH.className = "st-hint";
    liH.textContent = acc.lichess ? "" : "например wadim9993";
    ccH.textContent = acc.chesscom ? "" : "как в адресе профиля";
    errors.forEach(function (m) {
      if (m.indexOf("lichess") === 0) { liH.className = "st-hint bad"; liH.textContent = m; }
      else { ccH.className = "st-hint bad"; ccH.textContent = m; }
    });
    if (e.fetchedAt && !errors.length) {
      var ago = Math.round((Date.now() - e.fetchedAt) / 60000);
      var txt = ago < 2 ? "обновлено только что" : "обновлено " + ago + " мин назад";
      if (acc.lichess)  { liH.className = "st-hint ok"; liH.textContent = txt; }
      if (acc.chesscom) { ccH.className = "st-hint ok"; ccH.textContent = txt; }
    }
  }

  /* Играть можно урывками: неделю тишины, потом десять партий за вечер.
     В дни без партий рейтинг не меняется — тянем последнее известное значение
     вперёд, но помечаем такие точки как «не игровые»: график рисует их ровной
     линией без кружка, и сразу видно, где были простои, а где всплески. */
  function carryForward(series) {
    series.forEach(function (s) {
      var last = null;
      s.points.forEach(function (p) {
        if (p.v != null) { p.real = true; last = p.v; }
        else if (last != null) { p.v = last; p.real = false; }
      });
    });
  }

  /* Карта активности за 18 недель. Одна клетка — день, насыщенность растёт
     вместе с нагрузкой. Пустые клетки тоже говорящие: по ним сразу видно,
     где был перерыв, а где ты вернулся и разобрал всё за вечер. */
  var WD = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

  function heatmap(host, st, days) {
    host.innerHTML = "";

    var end = new Date(); end.setHours(12, 0, 0, 0);
    var shift = (end.getDay() + 6) % 7;                  /* к воскресенью текущей недели */
    end.setDate(end.getDate() + (6 - shift));
    var start = new Date(end); start.setDate(end.getDate() - 18 * 7 + 1);

    var cells = [], peak = { n: 0 };
    for (var d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      var k = key(d);
      var mine = (st[k] || {}).solved || 0;
      var ext = (days[k] || {});
      var gm = ((ext.li || {}).games || 0) + ((ext.cc || {}).games || 0);
      var future = d > new Date();
      var total = mine + gm;
      if (total > peak.n) peak = { n: total, k: k, mine: mine, gm: gm };
      cells.push({ k: k, wd: (d.getDay() + 6) % 7, mine: mine, gm: gm, total: total, future: future });
    }

    /* пороги от собственного максимума, иначе один ударный день съест всю шкалу */
    var top = Math.max(4, peak.n);
    function level(v) {
      if (!v) return 0;
      var r = v / top;
      return r > 0.66 ? 4 : r > 0.38 ? 3 : r > 0.15 ? 2 : 1;
    }

    var grid = document.createElement("div");
    grid.className = "st-mapgrid";

    var labs = document.createElement("div");
    labs.className = "st-mapwd";
    [0, 2, 4].forEach(function (i) {
      var s = document.createElement("span");
      s.textContent = WD[i];
      s.style.gridRow = String(i + 1);
      labs.appendChild(s);
    });

    cells.forEach(function (c) {
      var el = document.createElement("i");
      el.className = "st-cell";
      el.dataset.l = c.future ? "x" : String(level(c.total));
      el.style.gridRow = String(c.wd + 1);
      if (!c.future) {
        el.addEventListener("mouseenter", function () {
          var parts = [];
          if (c.mine) parts.push(c.mine + " " + plural(c.mine, "задача", "задачи", "задач") + " здесь");
          if (c.gm) parts.push(c.gm + " " + plural(c.gm, "партия", "партии", "партий"));
          tipAt(host, el, human(c.k), parts.length ? parts.join(" · ") : "ничего");
        });
        el.addEventListener("mouseleave", function () { hideTip(host); });
      }
      grid.appendChild(el);
    });

    host.appendChild(labs);
    host.appendChild(grid);

    var cap = root.querySelector("#stMapCap");
    cap.textContent = peak.n
      ? "Задачи здесь и партии на обоих сайтах. Самый плотный день — " + human(peak.k) +
        ": " + (peak.mine ? peak.mine + " " + plural(peak.mine, "задача", "задачи", "задач") : "") +
        (peak.mine && peak.gm ? " и " : "") +
        (peak.gm ? peak.gm + " " + plural(peak.gm, "партия", "партии", "партий") : "") + "."
      : "Здесь будут видны дни занятий — и те, что пропущены.";
  }

  function tipAt(host, el, title, text) {
    var t = host.querySelector(".st-tip");
    if (!t) { t = document.createElement("div"); t.className = "st-tip"; host.appendChild(t); }
    t.innerHTML = '<div class="st-d"></div><div class="st-r"><span></span></div>';
    t.querySelector(".st-d").textContent = title;
    t.querySelector(".st-r span").textContent = text;
    var hb = host.getBoundingClientRect(), eb = el.getBoundingClientRect();
    t.style.left = (eb.left - hb.left + eb.width / 2) + "px";
    t.style.top = (eb.top - hb.top - 6) + "px";
    t.hidden = false;
  }

  function bestDelta(days) {
    var today = S.today(), d = new Date(); d.setHours(12, 0, 0, 0);
    d.setDate(d.getDate() - 1);
    var prev = days[key(d)] || {}, cur = days[today] || {};
    var best = null;
    var names = { rapid: "рапид", blitz: "блиц", bullet: "пуля", puzzle: "задачи" };
    ["li", "cc"].forEach(function (k) {
      var a = prev[k] || {}, b = cur[k] || {};
      Object.keys(names).forEach(function (c) {
        if (a[c] == null || b[c] == null) return;
        var v = b[c] - a[c];
        if (!best || Math.abs(v) > Math.abs(best.v)) {
          best = { v: v, label: names[c] + " · " + SERIES[k].name };
        }
      });
    });
    return best;
  }

  function ratingTable(series, dates) {
    var live = series.filter(function (s) { return s.points.some(function (p) { return p.v != null; }); });
    var box = document.createElement("div");
    box.className = "st-scroll";
    var t = document.createElement("table");
    t.className = "st-table";
    var head = "<tr><th>День</th>" + live.map(function (s) { return "<th>" + s.name + "</th>"; }).join("") + "</tr>";
    var rows = dates.map(function (d, i) {
      return "<tr><td>" + human(d) + "</td>" + live.map(function (s) {
        return "<td>" + (s.points[i].v == null ? "—" : s.points[i].v) + "</td>";
      }).join("") + "</tr>";
    }).reverse().join("");
    t.innerHTML = "<thead>" + head + "</thead><tbody>" + rows + "</tbody>";
    box.appendChild(t);
    return box;
  }

  /* ---------- встраивание в навигацию ---------- */

  var SECTIONS = ["vBooks", "vSections", "vList", "vSolve", "vReview", "vOpen"];

  function openStats() {
    SECTIONS.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.classList.add("gone");
    });
    root.classList.remove("gone");
    document.body.classList.remove("zen");
    window.scrollTo(0, 0);
    paintNav(true);
    render();
    refresh(false);
  }

  function paintNav(on) {
    var b = document.getElementById("navStats");
    if (b) b.classList.toggle("on", !!on);
  }

  function mountNav() {
    var host = document.querySelector("header.top");
    var anchor = document.getElementById("navReview");
    if (!host) return;
    var b = document.createElement("button");
    b.className = "navbtn";
    b.id = "navStats";
    b.textContent = "◱ Статистика";
    b.addEventListener("click", openStats);
    if (anchor) host.insertBefore(b, anchor); else host.appendChild(b);
  }

  /* когда приложение само переключает экран — прячемся */
  function hookShow() {
    var orig = window.show;
    if (typeof orig !== "function") return;
    window.show = function () {
      if (root) root.classList.add("gone");
      paintNav(false);
      return orig.apply(this, arguments);
    };
  }

  /* перерисовываем графики при смене темы: цвета линий заданы атрибутами */
  function watchTheme() {
    new MutationObserver(function () {
      if (root && !root.classList.contains("gone")) render();
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      var fn = function () { if (root && !root.classList.contains("gone")) render(); };
      if (mq.addEventListener) mq.addEventListener("change", fn);
    }
  }

  /* система координат зависит от ширины карточки — при повороте экрана
     или смене размера окна графики надо пересобрать */
  function watchResize() {
    var t = null;
    window.addEventListener("resize", function () {
      if (!root || root.classList.contains("gone")) return;
      clearTimeout(t);
      t = setTimeout(render, 180);
    });
  }

  build();
  mountNav();
  hookShow();
  watchTheme();
  watchResize();

  /* тихо подтягиваем внешние данные при заходе на сайт, не чаще раза в час */
  setTimeout(function () { refresh(false); }, 2500);

  window.kombiStatsUI = { open: openStats, render: render, refresh: refresh };
})();
