import { useEffect, useState } from 'react'
import { subscribeToast } from '../lib/toast.js'
import './ToastHost.css'

const AUTO_DISMISS_MS = 4500

export default function ToastHost() {
  const [toasts, setToasts] = useState([])

  useEffect(() => {
    return subscribeToast((toast) => {
      setToasts((t) => [...t, toast])
      setTimeout(() => {
        setToasts((t) => t.filter((x) => x.id !== toast.id))
      }, AUTO_DISMISS_MS)
    })
  }, [])

  if (toasts.length === 0) return null

  return (
    <div className="toast-host">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast--${t.kind}`}>
          {t.message}
        </div>
      ))}
    </div>
  )
}
