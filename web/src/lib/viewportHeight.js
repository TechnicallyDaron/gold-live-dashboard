// In an installed iOS standalone PWA, 100svh can overshoot the real visible
// viewport (status-bar/home-indicator handling differs from any simulator),
// stretching #root taller than the screen and leaving dead space above the
// fixed tab bar on short-content screens. Mirror the JS-measured viewport
// height into a CSS var so #root tracks the real device, not the CSS unit.
function setAppVh() {
  const h = window.visualViewport?.height ?? window.innerHeight
  document.documentElement.style.setProperty('--app-vh', `${h}px`)
}

setAppVh()
window.addEventListener('resize', setAppVh)
window.addEventListener('orientationchange', setAppVh)
window.visualViewport?.addEventListener('resize', setAppVh)
