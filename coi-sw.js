/* Многопоточному Stockfish нужна общая память (SharedArrayBuffer), а её
   браузер даёт только «изолированной» странице — с заголовками
   Cross-Origin-Opener-Policy и Cross-Origin-Embedder-Policy. GitHub Pages
   своих заголовков ставить не даёт, поэтому их дописывает этот service
   worker к каждому ответу с нашего сайта. Чужие запросы (шрифты, CDN,
   Supabase, lichess, chess.com) идут мимо него как есть: у всех них
   есть CORS или Cross-Origin-Resource-Policy, изоляция их не ломает. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", e => {
  const r = e.request;
  if (r.cache === "only-if-cached" && r.mode !== "same-origin") return;
  if (new URL(r.url).origin !== self.location.origin) return;
  e.respondWith(fetch(r).then(res => {
    if (!res || res.status === 0) return res;
    const h = new Headers(res.headers);
    h.set("Cross-Origin-Opener-Policy", "same-origin");
    h.set("Cross-Origin-Embedder-Policy", "require-corp");
    return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
  }));
});
