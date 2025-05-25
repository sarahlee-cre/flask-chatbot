const CACHE_NAME = "hubi-cache-v4";
const STATIC_ASSETS = [
  "/install",
  "/static/manifest.json",
  "/static/sw.js",
  "/static/icons/icon3.png",
  "/static/icons/icon512.png",
  "/static/icons/hufs.png"
];

self.addEventListener("install", (event) => {
  console.log("📦 Installing service worker and caching static assets...");
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  console.log("✅ Activating new service worker and clearing old caches...");
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request);
    })
  );
});