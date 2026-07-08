import { api } from './api.js'

const ATTEMPTED_KEY = 'ncore_push_attempted'
const MUTED_NOTE_SHOWN_KEY = 'ncore_push_muted_note_shown'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)))
}

// Call from a user gesture (e.g. the first bell tap). Returns
// { subscribed: bool, muted_note: string|null } — muted_note is set once,
// the first time the server reports push isn't configured yet.
export async function initPushIfNeeded() {
  if (localStorage.getItem(ATTEMPTED_KEY)) return { subscribed: false, mutedNote: null }
  localStorage.setItem(ATTEMPTED_KEY, '1')

  const vapidKey = import.meta.env.VITE_VAPID_PUBLIC_KEY
  if (!vapidKey) return { subscribed: false, mutedNote: null }
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    return { subscribed: false, mutedNote: null }
  }

  try {
    const permission = await Notification.requestPermission()
    if (permission !== 'granted') return { subscribed: false, mutedNote: null }

    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey),
    })

    const res = await api.pushSubscribe(subscription.toJSON())
    if (!res.push_configured && !localStorage.getItem(MUTED_NOTE_SHOWN_KEY)) {
      localStorage.setItem(MUTED_NOTE_SHOWN_KEY, '1')
      return {
        subscribed: true,
        mutedNote: 'Server push not configured — in-app alerts still active.',
      }
    }
    return { subscribed: true, mutedNote: null }
  } catch {
    return { subscribed: false, mutedNote: null }
  }
}
