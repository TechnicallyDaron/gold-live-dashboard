import { precacheAndRoute } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'
import { createHandlerBoundToURL } from 'workbox-precaching'

precacheAndRoute(self.__WB_MANIFEST)

// Never let navigations fall back to a cached shell for /api/ calls —
// quotes/bias must always hit the network fresh.
registerRoute(
  new NavigationRoute(createHandlerBoundToURL('/index.html'), {
    denylist: [/^\/api\//],
  })
)

self.addEventListener('push', (event) => {
  let data = { title: 'N-CORE', body: '' }
  try {
    data = event.data.json()
  } catch {
    data.body = event.data?.text() || ''
  }
  event.waitUntil(
    self.registration.showNotification(data.title || 'N-CORE', {
      body: data.body || '',
      icon: '/pwa-192.png',
      badge: '/pwa-192.png',
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  event.waitUntil(self.clients.openWindow('/'))
})

self.skipWaiting()
