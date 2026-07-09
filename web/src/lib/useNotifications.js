import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'

const LAST_SEEN_KEY = 'ncore_notifications_last_seen'

// Module-scoped so the list/unseen-count stay consistent across screens —
// every screen carries a bell, and switching tabs shouldn't re-flash items
// the user already saw on another screen.
let cachedItems = []

function readLastSeen() {
  return Number(localStorage.getItem(LAST_SEEN_KEY) || 0)
}

export function useNotifications() {
  const [items, setItems] = useState(cachedItems)
  const [lastSeen, setLastSeen] = useState(readLastSeen)

  useEffect(() => {
    let cancelled = false

    const poll = async () => {
      try {
        const data = await api.notifications(0)
        cachedItems = data
        if (!cancelled) setItems(data)
      } catch {
        // transient error — keep showing the last-known list
      }
    }

    poll()
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') poll()
    }, 60000)

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  const markSeen = useCallback(() => {
    const now = Math.floor(Date.now() / 1000)
    localStorage.setItem(LAST_SEEN_KEY, String(now))
    setLastSeen(now)
  }, [])

  const unseenCount = items.filter((n) => n.ts > lastSeen).length

  return { items, unseenCount, lastSeen, markSeen }
}
