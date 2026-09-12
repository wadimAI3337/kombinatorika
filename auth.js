/* ============================================================
   Вход, регистрация и облачные сохранения.

   Что делает этот файл:
     1. до запуска app.js подтягивает сохранения из облака в localStorage,
        поэтому приложению ничего не нужно знать про аккаунты;
     2. перехватывает запись в localStorage и отправляет её в облако;
     3. рисует кнопку в шапке и модалку входа/регистрации.

   Если config.js не заполнен — сайт просто работает как раньше,
   локально, и никакой кнопки не появляется.
   ============================================================ */

(function () {
  "use strict";

  /* ---------- что синхронизируем ---------- */
  /* kombi         — прогресс по задачам (звёзды, решено, подсказки)
     kombi-op      — дебютный репертуар и интервальное повторение
     kombi-theme   — тема оформления
     kombi-autoan  — автоматический разбор после решения
     kombi-rv-*    — НЕ синхронизируем: это локальный кэш работы движка */
  /* kombi-stats    — сколько решено и заработано звёзд по дням
     kombi-ext      — ники на lichess/chess.com и ежедневные снимки рейтинга */
  var KEYS = ["kombi", "kombi-op", "kombi-theme", "kombi-autoan", "kombi-stats", "kombi-ext"];
  var JSON_KEYS = { "kombi": true, "kombi-op": true, "kombi-stats": true, "kombi-ext": true };
  var SYNCED = {}; KEYS.forEach(function (k) { SYNCED[k] = true; });

  var SB_CDN = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.js";
  var PUSH_DELAY = 1500;

  /* версия из своего же тега <script src="auth.js?v=N"> — тот же номер
     вешаем на app.js, иначе GitHub Pages будет отдавать его из кэша
     ещё десять минут после публикации */
  var VER = (function () {
    var el = document.currentScript;
    var m = el && /[?&]v=([^&]+)/.exec(el.src || "");
    return m ? m[1] : "";
  })();

  var cfg = window.KOMBI_CONFIG || {};
  var URL_OK = /^https:\/\/[a-z0-9-]+\.supabase\.(co|in)\/?$/i.test(String(cfg.SUPABASE_URL || "").trim());
  var KEY_OK = String(cfg.SUPABASE_ANON_KEY || "").trim().length > 30;
  var ENABLED = URL_OK && KEY_OK;

  var sb = null;          /* клиент supabase */
  var user = null;        /* текущий пользователь */
  var recovery = false;   /* переход по ссылке «сменить пароль» */
  var appStarted = false;
  var muted = false;      /* когда мы сами пишем в localStorage */
  var pushTimer = null;
  var pushing = false;
  var dirty = false;
  var lastError = "";

  /* ---------- мелкие помощники ---------- */

  function $(id) { return document.getElementById(id); }

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function lsDel(k) { try { localStorage.removeItem(k); } catch (e) {} }

  function safeParse(s) { try { return JSON.parse(s); } catch (e) { return undefined; } }

  /* тема — применяем сразу, чтобы заставка не мигала светлым */
  (function () {
    var t = lsGet("kombi-theme");
    if (t) document.documentElement.setAttribute("data-theme", t);
  })();

  /* ---------- снимок сохранений ---------- */

  function readLocal() {
    var o = {};
    KEYS.forEach(function (k) {
      var v = lsGet(k);
      if (v == null) return;
      if (JSON_KEYS[k]) { var p = safeParse(v); if (p !== undefined) o[k] = p; }
      else o[k] = v;
    });
    return o;
  }

  function writeLocal(snap) {
    muted = true;
    try {
      KEYS.forEach(function (k) {
        var v = snap ? snap[k] : undefined;
        if (v === undefined || v === null) lsDel(k);
        else lsSet(k, JSON_KEYS[k] ? JSON.stringify(v) : String(v));
      });
    } finally { muted = false; }
  }

  function isEmptySnap(s) {
    if (!s || typeof s !== "object") return true;
    return !KEYS.some(function (k) { return s[k] !== undefined && s[k] !== null; });
  }

  /* ---------- слияние (только при первом входе на устройстве) ---------- */

  /* прогресс: { bookId: { номер: {solved, hinted, stars, errs} } } — берём лучшее из двух */
  function mergeProgress(a, b) {
    a = (a && typeof a === "object") ? a : {};
    b = (b && typeof b === "object") ? b : {};
    var out = {}, books = {};
    Object.keys(a).forEach(function (k) { books[k] = 1; });
    Object.keys(b).forEach(function (k) { books[k] = 1; });

    Object.keys(books).forEach(function (bid) {
      var x = a[bid] || {}, y = b[bid] || {}, res = {}, nums = {};
      Object.keys(x).forEach(function (n) { nums[n] = 1; });
      Object.keys(y).forEach(function (n) { nums[n] = 1; });

      Object.keys(nums).forEach(function (n) {
        var p = x[n] || {}, q = y[n] || {}, r = {};
        if (p.solved || q.solved) r.solved = true;
        if (p.hinted || q.hinted) r.hinted = true;
        var st = Math.max(p.stars || 0, q.stars || 0);
        if (st) r.stars = st;
        var er = Math.max(p.errs || 0, q.errs || 0);
        if (er) r.errs = er;
        if (Object.keys(r).length) res[n] = r;
      });
      if (Object.keys(res).length) out[bid] = res;
    });
    return out;
  }

  /* репертуар: массив [{id, lines:[{id, st:{last,...}}], ...}] — объединяем по id */
  function lastTouch(rep) {
    var t = 0;
    (rep && rep.lines || []).forEach(function (l) {
      var v = l && l.st && l.st.last; if (v > t) t = v;
    });
    return t;
  }

  function mergeReps(a, b) {
    a = Array.isArray(a) ? a : [];
    b = Array.isArray(b) ? b : [];
    var byId = {}, order = [];

    function take(rep) {
      if (!rep || !rep.id) return;
      var cur = byId[rep.id];
      if (!cur) { byId[rep.id] = rep; order.push(rep.id); return; }

      /* за основу берём тот, где занимались позже */
      var base = lastTouch(rep) > lastTouch(cur) ? rep : cur;
      var other = base === rep ? cur : rep;

      var lines = (base.lines || []).slice();
      var seen = {};
      lines.forEach(function (l) { if (l && l.id) seen[l.id] = l; });

      (other.lines || []).forEach(function (l) {
        if (!l || !l.id) return;
        var mine = seen[l.id];
        if (!mine) { lines.push(l); return; }
        /* один и тот же вариант — оставляем более свежее состояние повторения */
        var ml = (mine.st && mine.st.last) || 0, ol = (l.st && l.st.last) || 0;
        if (ol > ml) lines[lines.indexOf(mine)] = l;
      });

      var merged = Object.assign({}, other, base);
      merged.lines = lines;
      byId[rep.id] = merged;
    }

    a.forEach(take);
    b.forEach(take);
    return order.map(function (id) { return byId[id]; });
  }

  /* дневник активности: { "2026-09-12": {solved, stars, errs, hints} } —
     за общий день берём большее значение, счётчики только растут */
  function mergeStats(a, b) {
    a = (a && typeof a === "object") ? a : {};
    b = (b && typeof b === "object") ? b : {};
    var out = {}, days = {};
    Object.keys(a).forEach(function (d) { days[d] = 1; });
    Object.keys(b).forEach(function (d) { days[d] = 1; });

    Object.keys(days).forEach(function (d) {
      var x = a[d] || {}, y = b[d] || {}, r = {};
      ["solved", "stars", "errs", "hints"].forEach(function (f) {
        var v = Math.max(x[f] || 0, y[f] || 0);
        if (v) r[f] = v;
      });
      if (Object.keys(r).length) out[d] = r;
    });
    return out;
  }

  /* снимки с lichess/chess.com: дни объединяем, при совпадении оставляем локальный */
  function mergeExt(a, b) {
    a = (a && typeof a === "object") ? a : {};
    b = (b && typeof b === "object") ? b : {};
    return {
      accounts: Object.assign({}, b.accounts || {}, a.accounts || {}),
      days: Object.assign({}, b.days || {}, a.days || {}),
      fetchedAt: Math.max(a.fetchedAt || 0, b.fetchedAt || 0)
    };
  }

  function mergeSnap(local, cloud) {
    var out = {};
    var prog = mergeProgress(local["kombi"], cloud["kombi"]);
    if (Object.keys(prog).length) out["kombi"] = prog;

    var reps = mergeReps(local["kombi-op"], cloud["kombi-op"]);
    if (reps.length) out["kombi-op"] = reps;

    var stats = mergeStats(local["kombi-stats"], cloud["kombi-stats"]);
    if (Object.keys(stats).length) out["kombi-stats"] = stats;

    var ext = mergeExt(local["kombi-ext"], cloud["kombi-ext"]);
    if (Object.keys(ext.accounts).length || Object.keys(ext.days).length) out["kombi-ext"] = ext;

    /* настройки — приоритет у устройства, с которого входим */
    ["kombi-theme", "kombi-autoan"].forEach(function (k) {
      var v = local[k] !== undefined ? local[k] : cloud[k];
      if (v !== undefined) out[k] = v;
    });
    return out;
  }

  /* ---------- обмен с облаком ---------- */

  function loadSupabase() {
    if (window.supabase && window.supabase.createClient) return Promise.resolve(window.supabase);
    return new Promise(function (res, rej) {
      var s = document.createElement("script");
      s.src = SB_CDN;
      s.onload = function () {
        if (window.supabase && window.supabase.createClient) res(window.supabase);
        else rej(new Error("supabase не загрузился"));
      };
      s.onerror = function () { rej(new Error("не удалось загрузить библиотеку supabase")); };
      document.head.appendChild(s);
    });
  }

  function fetchCloud(uid) {
    return sb.from("saves").select("data").eq("user_id", uid).maybeSingle()
      .then(function (r) {
        if (r.error) throw r.error;
        return (r.data && r.data.data) || null;
      });
  }

  function pushCloud(uid, snap) {
    return sb.from("saves").upsert({
      user_id: uid,
      data: snap,
      updated_at: new Date().toISOString()
    }, { onConflict: "user_id" }).then(function (r) {
      if (r.error) throw r.error;
    });
  }

  /* сохранения уже в облаке — они и есть истина: заменяем локальные */
  function pullAndApply(uid) {
    return fetchCloud(uid).then(function (cloud) {
      if (isEmptySnap(cloud)) return pushCloud(uid, readLocal());
      writeLocal(cloud);
    });
  }

  /* первый вход с этого устройства — не теряем то, что уже нарешано локально */
  function linkAndMerge(uid) {
    return fetchCloud(uid).then(function (cloud) {
      var local = readLocal();
      var snap = isEmptySnap(cloud) ? local : mergeSnap(local, cloud);
      writeLocal(snap);
      return pushCloud(uid, snap);
    });
  }

  /* ---------- дневник: что решено за сегодня ----------
     Приложение не помечает задачи датой, поэтому активность считаем сами:
     на каждую запись прогресса сравниваем новое состояние с предыдущим
     и прибавляем разницу к сегодняшнему дню. app.js при этом не меняется. */

  var lastProg = null;

  function today() {
    var d = new Date();
    return d.getFullYear() + "-" +
           String(d.getMonth() + 1).padStart(2, "0") + "-" +
           String(d.getDate()).padStart(2, "0");
  }

  function diffProgress(before, after) {
    var d = { solved: 0, stars: 0, errs: 0, hints: 0 };
    Object.keys(after || {}).forEach(function (bid) {
      var x = (before && before[bid]) || {}, y = after[bid] || {};
      Object.keys(y).forEach(function (n) {
        var p = x[n] || {}, q = y[n] || {};
        if (q.solved && !p.solved) d.solved++;
        if (q.hinted && !p.hinted) d.hints++;
        var ds = (q.stars || 0) - (p.stars || 0); if (ds > 0) d.stars += ds;
        var de = (q.errs || 0) - (p.errs || 0);   if (de > 0) d.errs += de;
      });
    });
    return d;
  }

  function bumpStats(d) {
    var all = safeParse(lsGet("kombi-stats")) || {};
    var key = today(), day = all[key] || (all[key] = {});
    ["solved", "stars", "errs", "hints"].forEach(function (f) {
      if (d[f]) day[f] = (day[f] || 0) + d[f];
    });
    lsSet("kombi-stats", JSON.stringify(all));   /* не muted — пусть уедет в облако */
  }

  function trackProgress() {
    var now = safeParse(lsGet("kombi")) || {};
    if (lastProg) {
      var d = diffProgress(lastProg, now);
      if (d.solved || d.stars || d.errs || d.hints) bumpStats(d);
    }
    lastProg = now;
  }

  /* ---------- отложенная отправка ---------- */

  function markDirty() {
    if (!user) return;
    dirty = true;
    paintButton();
    clearTimeout(pushTimer);
    pushTimer = setTimeout(flush, PUSH_DELAY);
  }

  function flush() {
    clearTimeout(pushTimer);
    if (!user || !dirty || pushing) return Promise.resolve();
    pushing = true;
    var snap = readLocal();
    dirty = false;
    paintButton();
    return pushCloud(user.id, snap)
      .then(function () { lastError = ""; })
      .catch(function (e) {
        dirty = true;
        lastError = humanError(e);
        console.warn("[sync] не сохранилось:", e);
      })
      .then(function () { pushing = false; paintButton(); });
  }

  function installInterceptor() {
    var proto = window.Storage && window.Storage.prototype;
    if (!proto) return;
    var set = proto.setItem, del = proto.removeItem, clr = proto.clear;

    proto.setItem = function (k, v) {
      set.apply(this, arguments);
      if (muted || this !== window.localStorage) return;
      if (k === "kombi") trackProgress();
      if (SYNCED[k]) markDirty();
    };
    proto.removeItem = function (k) {
      del.apply(this, arguments);
      if (!muted && this === window.localStorage && SYNCED[k]) markDirty();
    };
    proto.clear = function () {
      clr.apply(this, arguments);
      if (!muted && this === window.localStorage) markDirty();
    };

    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") flush();
    });
    window.addEventListener("pagehide", flush);
  }

  /* ---------- запуск приложения ---------- */

  function startApp() {
    if (appStarted) return;
    appStarted = true;
    var boot = $("authBoot");
    if (boot) boot.hidden = true;

    /* точка отсчёта для дневника: всё, что было решено до этого момента,
       новой активностью не считается */
    lastProg = safeParse(lsGet("kombi")) || {};

    var s = document.createElement("script");
    s.src = "app.js" + (VER ? "?v=" + VER : "");
    s.onload = function () {
      var t = document.createElement("script");
      t.src = "stats.js" + (VER ? "?v=" + VER : "");
      document.body.appendChild(t);
    };
    document.body.appendChild(s);
  }

  /* ---------- кнопка и меню в шапке ---------- */

  var btn = null, menu = null;

  function mountButton() {
    var top = document.querySelector("header.top");
    if (!top) return;
    var box = document.createElement("div");
    box.style.position = "relative";
    box.style.display = "flex";

    btn = document.createElement("button");
    btn.className = "navbtn";
    btn.id = "authBtn";
    box.appendChild(btn);

    var theme = $("themeBtn");
    if (theme) top.insertBefore(box, theme); else top.appendChild(box);

    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      if (user) toggleMenu(box); else openDialog("in");
    });
    document.addEventListener("click", function () { closeMenu(); });
    paintButton();
  }

  function paintButton() {
    if (!btn) return;
    if (!user) { btn.innerHTML = "Войти"; btn.title = "Войти, чтобы прогресс хранился в облаке"; return; }
    var cls = lastError ? "off" : (dirty || pushing ? "sync" : "");
    var name = user.email || "аккаунт";
    btn.innerHTML = '<span class="dot ' + cls + '"></span><span class="who"></span>';
    btn.querySelector(".who").textContent = name.split("@")[0];
    btn.title = lastError ? ("Не сохранилось: " + lastError)
      : (dirty || pushing ? "Сохраняю…" : "Сохранено в облаке · " + name);
  }

  function closeMenu() { if (menu) { menu.remove(); menu = null; } }

  function toggleMenu(box) {
    if (menu) { closeMenu(); return; }
    menu = document.createElement("div");
    menu.className = "auth-menu";
    menu.addEventListener("click", function (e) { e.stopPropagation(); });

    var mail = document.createElement("div");
    mail.className = "mail";
    mail.textContent = user.email || "";
    menu.appendChild(mail);

    if (lastError) {
      var warn = document.createElement("div");
      warn.className = "mail";
      warn.style.color = "var(--bad)";
      warn.textContent = "Не сохранилось: " + lastError;
      menu.appendChild(warn);
    }

    menu.appendChild(item("Сохранить сейчас", function () {
      dirty = true; flush().then(function () { closeMenu(); });
    }));
    menu.appendChild(item("Загрузить из облака", function () {
      closeMenu();
      pullAndApply(user.id).then(function () { location.reload(); })
        .catch(function (e) { alert("Не получилось: " + humanError(e)); });
    }));
    menu.appendChild(item("Выйти", function () {
      closeMenu();
      if (!confirm("Выйти из аккаунта?\n\nПрогресс останется в облаке и вернётся при следующем входе.")) return;
      flush().then(function () { return sb.auth.signOut(); }).then(function () {
        writeLocal({});          /* чистим устройство: данные уже в облаке */
        location.reload();
      });
    }));

    box.appendChild(menu);
  }

  function item(label, fn) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.addEventListener("click", fn);
    return b;
  }

  /* ---------- модалка ---------- */

  var mode = "in";   /* in | up | forgot | reset */

  var TITLES = {
    in:     ["Вход", "Прогресс, звёзды и дебютный репертуар подтянутся на любом устройстве.", "Войти"],
    up:     ["Регистрация", "Заведи аккаунт — и весь прогресс, что уже накопился в этом браузере, переедет в облако.", "Создать аккаунт"],
    forgot: ["Восстановление", "Пришлём письмо со ссылкой для смены пароля.", "Отправить письмо"],
    reset:  ["Новый пароль", "Придумай новый пароль для входа.", "Сохранить пароль"]
  };

  function openDialog(m) {
    setMode(m || "in");
    $("authBack").hidden = false;
    setTimeout(function () { var f = $("authEmail"); if (f && !f.hidden) f.focus(); }, 30);
  }

  function closeDialog() {
    if (mode === "reset") return;    /* пароль нужно довести до конца */
    $("authBack").hidden = true;
    showMsg("");
  }

  function setMode(m) {
    mode = m;
    var t = TITLES[m];
    $("authTitle").textContent = t[0];
    $("authLead").textContent = t[1];
    $("authGo").textContent = t[2];
    $("authTabs").hidden = (m === "forgot" || m === "reset");
    $("authPassWrap").hidden = (m === "forgot");
    $("authEmail").parentNode.hidden = (m === "reset");
    $("authClose").hidden = (m === "reset");
    $("authForgot").textContent = (m === "in" || m === "up") ? "Забыли пароль?" : "← Назад";
    $("authForgot").parentNode.hidden = (m === "reset");
    $("authPass").autocomplete = (m === "up" || m === "reset") ? "new-password" : "current-password";

    var tabs = $("authTabs").querySelectorAll("button");
    tabs.forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.mode === m)); });
    showMsg("");
  }

  function showMsg(text, ok) {
    var el = $("authMsg");
    el.textContent = text || "";
    el.hidden = !text;
    el.className = "auth-msg" + (ok ? " ok" : "");
  }

  function busy(on) {
    var g = $("authGo");
    g.disabled = !!on;
    if (on) { g.dataset.label = g.textContent; g.textContent = "Минутку…"; }
    else if (g.dataset.label) g.textContent = g.dataset.label;
  }

  function humanError(e) {
    var m = String((e && (e.message || e.error_description)) || e || "");
    var low = m.toLowerCase();
    if (low.indexOf("invalid login credentials") >= 0) return "Неверная почта или пароль.";
    if (low.indexOf("already registered") >= 0 || low.indexOf("already been registered") >= 0)
      return "Такая почта уже зарегистрирована — попробуй войти.";
    if (low.indexOf("password should be at least") >= 0) return "Пароль должен быть не короче 6 символов.";
    if (low.indexOf("email not confirmed") >= 0) return "Почта не подтверждена — проверь письмо.";
    if (low.indexOf("unable to validate email") >= 0 || low.indexOf("invalid email") >= 0)
      return "Проверь адрес почты.";
    if (low.indexOf("rate limit") >= 0 || low.indexOf("too many") >= 0 || low.indexOf("429") >= 0)
      return "Слишком много попыток — подожди минуту.";
    if (low.indexOf("failed to fetch") >= 0 || low.indexOf("networkerror") >= 0)
      return "Нет связи с сервером.";
    if (low.indexOf("relation") >= 0 && low.indexOf("saves") >= 0)
      return "В базе нет таблицы saves — выполни schema.sql в Supabase.";
    return m || "Что-то пошло не так.";
  }

  function bindDialog() {
    $("authClose").addEventListener("click", closeDialog);
    $("authBack").addEventListener("click", function (e) { if (e.target === $("authBack")) closeDialog(); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !$("authBack").hidden) closeDialog();
    });

    $("authTabs").addEventListener("click", function (e) {
      var b = e.target.closest("button[data-mode]");
      if (b) setMode(b.dataset.mode);
    });

    $("authForgot").addEventListener("click", function () {
      setMode(mode === "forgot" ? "in" : "forgot");
    });

    $("authForm").addEventListener("submit", function (e) {
      e.preventDefault();
      submit();
    });
  }

  function submit() {
    var email = $("authEmail").value.trim();
    var pass = $("authPass").value;

    if (mode !== "reset" && !/.+@.+\..+/.test(email)) { showMsg("Проверь адрес почты."); return; }
    if (mode !== "forgot" && pass.length < 6) { showMsg("Пароль должен быть не короче 6 символов."); return; }

    busy(true); showMsg("");

    var job;
    if (mode === "in") {
      job = sb.auth.signInWithPassword({ email: email, password: pass })
        .then(check)
        .then(function (d) { return afterAuth(d.user, true); });

    } else if (mode === "up") {
      job = sb.auth.signUp({ email: email, password: pass })
        .then(check)
        .then(function (d) {
          if (!d.session) {
            busy(false);
            showMsg("Готово! Мы отправили письмо на " + email +
                    ". Подтверди адрес по ссылке из письма и возвращайся сюда — вход заработает.", true);
            return null;
          }
          return afterAuth(d.user, true);
        });

    } else if (mode === "forgot") {
      var back = location.origin + location.pathname;
      job = sb.auth.resetPasswordForEmail(email, { redirectTo: back })
        .then(check)
        .then(function () {
          busy(false);
          showMsg("Письмо со ссылкой ушло на " + email + ".", true);
          return null;
        });

    } else {  /* reset */
      job = sb.auth.updateUser({ password: pass })
        .then(check)
        .then(function () {
          showMsg("Пароль обновлён.", true);
          setTimeout(function () { location.replace(location.origin + location.pathname); }, 900);
          return null;
        });
    }

    job.catch(function (e) {
      busy(false);
      showMsg(humanError(e));
    });
  }

  function check(r) {
    if (r && r.error) throw r.error;
    return (r && r.data) || {};
  }

  /* после успешного входа: сливаем локальное с облачным и перезапускаем страницу,
     чтобы приложение перечитало сохранения с нуля */
  function afterAuth(u, merge) {
    user = u;
    $("authGo").textContent = "Переношу сохранения…";
    var job = merge ? linkAndMerge(u.id) : pullAndApply(u.id);
    return job.then(function () { location.reload(); })
      .catch(function (e) {
        busy(false);
        showMsg("Вход выполнен, но сохранения не перенеслись: " + humanError(e));
      });
  }

  /* ---------- старт ---------- */

  function boot() {
    bindDialog();

    if (!ENABLED) {
      console.info("[kombi] Облачные сохранения выключены: заполни config.js " +
                   "(SUPABASE_URL и SUPABASE_ANON_KEY). Пока прогресс хранится только в этом браузере.");
      startApp();
      return;
    }

    recovery = /(^|[#&?])type=recovery/.test(location.hash) || /(^|[#&?])type=recovery/.test(location.search);

    /* если сессия уже есть — покажем заставку, чтобы не мелькнул чужой прогресс */
    var maybeSession = false;
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && k.indexOf("sb-") === 0 && k.indexOf("-auth-token") > 0) { maybeSession = true; break; }
      }
    } catch (e) {}
    if (maybeSession || recovery) $("authBoot").hidden = false;

    /* если сеть подвиснет — не держим приложение заложником */
    var guard = setTimeout(startApp, 8000);

    loadSupabase().then(function (lib) {
      sb = lib.createClient(cfg.SUPABASE_URL.replace(/\/$/, ""), cfg.SUPABASE_ANON_KEY, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
      });

      sb.auth.onAuthStateChange(function (event) {
        if (event === "PASSWORD_RECOVERY") { recovery = true; openDialog("reset"); }
      });

      return sb.auth.getSession().then(function (r) {
        var session = r && r.data && r.data.session;
        if (!session) return null;
        user = session.user;
        if (recovery) return null;              /* смена пароля — данные не трогаем */
        return pullAndApply(user.id).catch(function (e) {
          lastError = humanError(e);
          console.warn("[sync] не удалось загрузить сохранения:", e);
        });
      });
    }).catch(function (e) {
      lastError = humanError(e);
      console.warn("[sync]", e);
    }).then(function () {
      clearTimeout(guard);
      installInterceptor();
      startApp();
      mountButton();
      if (recovery) openDialog("reset");
    });
  }

  /* доступ из консоли — удобно при отладке синхронизации */
  window.kombiSync = {
    snapshot: readLocal,
    flush: function () { dirty = true; return flush(); },
    merge: mergeSnap,
    user: function () { return user; }
  };

  /* то, чем пользуется stats.js */
  window.kombiStats = {
    today: today,
    user: function () { return user; },
    stats: function () { return safeParse(lsGet("kombi-stats")) || {}; },
    ext: function () {
      var e = safeParse(lsGet("kombi-ext")) || {};
      e.accounts = e.accounts || {};
      e.days = e.days || {};
      return e;
    },
    saveExt: function (e) { lsSet("kombi-ext", JSON.stringify(e)); },
    openLogin: function () { openDialog("in"); }
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
