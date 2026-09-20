const CACHE = 'kawsay-shell-v2';
const SHELL = ['/', '/offline', '/favicon.svg', '/icon-192.png', '/icon-512.png'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))),
      ),
  );
  self.clients.claim();
});

function isStaticAsset(url) {
  return url.pathname.startsWith('/_next/static/');
}

function isDocument(request) {
  return request.mode === 'navigate' || request.destination === 'document';
}

async function put(request, response) {
  if (!response.ok) return response;
  const cache = await caches.open(CACHE);
  await cache.put(request, response.clone());
  return response;
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  return put(request, response);
}

async function networkFirstDocument(request) {
  try {
    return await put(request, await fetch(request));
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return (await caches.match('/offline')) || (await caches.match('/'));
  }
}

async function networkFirst(request) {
  try {
    return await put(request, await fetch(request));
  } catch {
    return (await caches.match(request)) || Response.error();
  }
}

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  if (!event.request.url.startsWith(self.location.origin)) return;

  const url = new URL(event.request.url);
  if (url.pathname === '/sw.js') return;

  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  if (isDocument(event.request)) {
    event.respondWith(networkFirstDocument(event.request));
    return;
  }

  event.respondWith(networkFirst(event.request));
});
