// Detects whether the app is running as an installed PWA (vs a browser
// tab) so the tour's install step — and its copy — can adapt. iOS Safari
// doesn't support the display-mode media query pre-install, hence the
// navigator.standalone fallback.
export function isStandalone() {
  if (typeof window === 'undefined') return false
  const mq = window.matchMedia?.('(display-mode: standalone)')?.matches
  const iosStandalone = window.navigator?.standalone === true
  return !!mq || !!iosStandalone
}

export function getMobilePlatform() {
  const ua = window.navigator?.userAgent || ''
  if (/iPad|iPhone|iPod/.test(ua)) return 'ios'
  if (/Android/.test(ua)) return 'android'
  return 'other'
}
