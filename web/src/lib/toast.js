// Minimal global toast bus — a pub/sub so any component can raise a toast
// without prop-drilling through the screen tree. ToastHost (mounted once
// in App.jsx, outside <Routes> so it survives navigation) is the only
// subscriber that actually renders anything.
let listeners = []
let seq = 0

export function showToast(message, kind = 'default') {
  const toast = { id: ++seq, message, kind }
  listeners.forEach((fn) => fn(toast))
}

export function subscribeToast(fn) {
  listeners.push(fn)
  return () => {
    listeners = listeners.filter((l) => l !== fn)
  }
}
