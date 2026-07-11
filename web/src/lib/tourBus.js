// Global pub/sub so "Replay tour" in settings can start TourOverlay (mounted
// once in App.jsx) without prop-drilling — same pattern as toast.js.
let listeners = []

export function startTour() {
  listeners.forEach((fn) => fn())
}

export function subscribeTourStart(fn) {
  listeners.push(fn)
  return () => {
    listeners = listeners.filter((l) => l !== fn)
  }
}
