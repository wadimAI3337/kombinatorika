/* ============================================================
   АДРЕСА ЭКРАНОВ И КНОПКА «НАЗАД»

   У каждого экрана свой адрес после #: #/open, #/open/<дебют>,
   #/real, #/real/pos/<позиция>, #/stats, #/review, #/g/<группа>,
   #/b/<книга>, #/b/<книга>/<глава>, #/b/<книга>/<глава>/<задача>,
   #/b/<книга>/read/<глава>. «Назад» в браузере возвращает на
   предыдущий экран сайта, а не уводит с него; ссылку можно открыть
   заново или прислать.

   Разделы после каждого переключения зовут kNavPing (app.js — через
   show, дебюты — opShow, реализация — go, статистика — openStats).
   Адрес считаем из их состояния; для «Назад» внутри вкладки помним,
   как открыть экран снова, а по прямой ссылке разбираем сам адрес.
   ============================================================ */
(function () {
  "use strict";
  const AGAIN = {};      /* ключ записи истории → как открыть экран снова */
  const trail = [];      /* адреса записей истории этой вкладки по порядку */
  let seq = 0, at = 0, queued = false, restoring = false, quietPop = false, rdAgain = null;
  const enc = encodeURIComponent;
  const vis = id => { const el = document.getElementById(id); return !!el && !el.classList.contains("gone"); };
  const home = () => { renderBooks(); show("books"); };
  /* книга вместе со своей группой — иначе в крошках пустое имя группы */
  const setBook = b => {
    book = b;
    grp = GROUPS.find(g => g.id === groupOf(b)) || grp;
    document.querySelectorAll(".gcrumb").forEach(el => el.textContent = grp.title);
  };

  /* текущий экран → [адрес, как открыть его снова] */
  function screen() {
    if (vis("vReal") && window.kombiRealNav) return window.kombiRealNav.where();
    if (vis("vStats") && window.kombiOpenStats) return ["stats", window.kombiOpenStats];
    if (view === "open" && window.kombiOp) return window.kombiOp.where();
    if (view === "review") return ["review", window.openReview];
    if (view === "group") { const g = grp; return ["g/" + enc(g.id), () => { grp = g; renderGroup(); show("group"); }]; }
    if (view === "sections") { const b = book; return ["b/" + enc(b.id), () => { setBook(b); renderSections(); show("sections"); }]; }
    if (view === "list" && sec) {
      const b = book, s = sec, pg = page, f = filter;
      return ["b/" + enc(b.id) + "/" + enc(s.id), () => { setBook(b); sec = s; page = pg; filter = f; renderList(); show("list"); }];
    }
    if (view === "solve" && st && st.p && sec) {
      const b = book, s = sec, p = st.p;
      return ["b/" + enc(b.id) + "/" + enc(s.id) + "/" + enc(p.n), () => { setBook(b); sec = s; openPuzzle(p); }];
    }
    if (view === "read" && rd) {
      const b = rd.b;
      return ["b/" + enc(b.id) + "/read" + (rd.rs ? "/" + enc(rd.rs.id) : ""),
        rdAgain || (() => { setBook(b); renderSections(); show("sections"); })];
    }
    return ["", home];
  }

  function ping() { if (queued) return; queued = true; Promise.resolve().then(flush); }
  function flush() {
    queued = false;
    const [path, again] = screen();
    const url = path ? "#/" + path : location.pathname + location.search;
    const now = trail[at];
    const key = ++seq; AGAIN[key] = again;
    /* экран, с которого сюда пришли (крошка «назад», «Выйти» из тренировки) —
       это шаг назад по истории, а не новая запись */
    if (!restoring && at > 0 && trail[at - 1] === path && now !== path) {
      quietPop = true; history.back();
      return;
    }
    /* задача за задачей в одной главе не копят историю */
    const sameList = now && path && /^b\/[^/]+\/[^/]+\/[^/]+$/.test(path) && /^b\/[^/]+\/[^/]+\/[^/]+$/.test(now) &&
      now.split("/").slice(0, 3).join("/") === path.split("/").slice(0, 3).join("/");
    if (restoring || now === path || now === undefined || sameList) {
      history.replaceState({ k: key, i: at }, "", url);
    } else {
      at++;
      history.pushState({ k: key, i: at }, "", url);
    }
    trail.length = at; trail.push(path);
  }

  /* уходя из тренировки или правки дебюта «Назадом», бросаем их без сохранения хода */
  function leave() { if (view === "open" && window.kombiOp) window.kombiOp.leave(); }

  addEventListener("popstate", e => {
    const s = e.state || {};
    if (typeof s.i === "number") at = s.i;
    if (quietPop) {
      quietPop = false;
      /* экран уже на месте — только обновим, как его открыть снова */
      const [path, again] = screen();
      trail[at] = path; AGAIN[s.k] = again;
      return;
    }
    restoring = true;
    try {
      leave();
      if (s.k && AGAIN[s.k]) AGAIN[s.k](); else fromUrl();
    } catch (err) { try { home(); } catch (e2) {} }
    Promise.resolve().then(() => { restoring = false; });
  });

  /* прямая ссылка: разбираем адрес. Книги Дворецкого, Юсупова и других
     догружаются позже — подождём их до пяти секунд */
  function fromUrl(tries) {
    tries = tries || 0;
    const [a, b2, c, d] = location.hash.replace(/^#\/?/, "").split("/").map(x => { try { return decodeURIComponent(x); } catch (e) { return x; } });
    if (!a) return home();
    if (a === "stats" && window.kombiOpenStats) return window.kombiOpenStats();
    if (a === "review" && window.openReview) return window.openReview();
    if (a === "real" && window.kombiRealNav) return window.kombiRealNav.go(b2, c);
    if (a === "open" && window.kombiOp) return window.kombiOp.go(b2);
    if (a === "g") {
      const g = GROUPS.find(x => x.id === b2);
      if (g) { grp = g; renderGroup(); show("group"); return; }
    }
    if (a === "b") {
      const bk = BOOKS.find(x => String(x.id) === b2);
      if (!bk && tries < 25) { setTimeout(() => fromUrl(tries + 1), 200); return; }
      if (bk) {
        setBook(bk);
        const s = bk.secs && bk.secs.find(x => String(x.id) === (c === "read" ? d : c));
        if (s && (s.read || c === "read")) { rdOpenRead(bk, s); return; }
        if (s && s.items) {
          sec = s; page = 0; filter = "all";
          const p = d && s.items.find(x => String(x.n) === d);
          if (p) { openPuzzle(p); return; }
          renderList(); show("list"); return;
        }
        renderSections(); show("sections"); return;
      }
    }
    home();
  }

  /* читалку открывают по-разному — запоминаем, как именно */
  ["rdOpenRead", "rdOpenChapter", "rdOpenIntro", "rdOpenAnswer", "rdOpenNotes"].forEach(n => {
    const f = window[n];
    if (typeof f !== "function") return;
    window[n] = function () {
      const args = arguments, b = book;
      rdAgain = () => { setBook(b); f.apply(null, args); };
      return f.apply(this, args);
    };
  });

  const show0 = window.show;
  window.show = function () { const r = show0.apply(this, arguments); ping(); return r; };
  window.kNavPing = ping;

  /* старт. Чужой # (ссылка восстановления пароля от Supabase) не трогаем */
  const h = location.hash;
  if (!h || h === "#" || h.indexOf("#/") === 0) {
    restoring = true;
    if (h.length > 2) fromUrl(); else ping();
    Promise.resolve().then(() => Promise.resolve()).then(() => { restoring = false; });
  }
})();
