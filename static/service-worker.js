self.addEventListener("install", event => {
  event.waitUntil(
    caches.open("receipt-cache").then(cache =>
      cache.addAll([
        "/",
        "/static/style.css",
        "/static/script.js"
      ])
    )
  );
});

self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request).then(resp => resp || fetch(event.request))
  );
});

