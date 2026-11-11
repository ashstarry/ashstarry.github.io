// Retire the old blog's root-scoped service worker. Do not clear shared caches or storage.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    await self.clients.claim();
    await self.registration.unregister();
  })());
});
