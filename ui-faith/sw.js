const CACHE = "xynasoft-faith-v4";

/*
Core static assets
*/
const STATIC_ASSETS = [

  "/faith/",
  "/faith/index.html",

  "/faith/styles.css",
  "/faith/app.js",

  "/faith/manifest.webmanifest",

  "/faith/assets/xynasoft-logo.png"

];


/* -----------------------
   INSTALL
----------------------- */

self.addEventListener("install", (event) => {

  event.waitUntil(

    caches.open(CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })

  );

  self.skipWaiting();

});


/* -----------------------
   ACTIVATE
----------------------- */

self.addEventListener("activate", (event) => {

  event.waitUntil(

    caches.keys().then((keys) =>

      Promise.all(
        keys.map((key) => {
          if (key !== CACHE) {
            return caches.delete(key);
          }
        })
      )

    )

  );

  self.clients.claim();

});


/* -----------------------
   FETCH
----------------------- */

self.addEventListener("fetch", (event) => {

  const request = event.request;
  const url = new URL(request.url);


  /*
  NEVER CACHE API
  */

  if (url.pathname.startsWith("/api/")) {

    event.respondWith(fetch(request));
    return;

  }


  /*
  NETWORK FIRST FOR HTML
  */

  if (request.mode === "navigate") {

    event.respondWith(

      fetch(request)

        .then((response) => {

          const copy = response.clone();

          caches.open(CACHE).then((cache) => {
            cache.put(request, copy);
          });

          return response;

        })

        .catch(() => {

          return caches.match(request)
            || caches.match("/faith/index.html");

        })

    );

    return;

  }


  /*
  CACHE FIRST FOR STATIC FILES
  */

  event.respondWith(

    caches.match(request).then((cached) => {

      if (cached) return cached;

      return fetch(request).then((response) => {

        if (!response || response.status !== 200) {
          return response;
        }

        const clone = response.clone();

        caches.open(CACHE).then((cache) => {
          cache.put(request, clone);
        });

        return response;

      });

    })

  );

});