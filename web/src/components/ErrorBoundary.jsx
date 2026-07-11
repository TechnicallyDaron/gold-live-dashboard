import { Component } from 'react'

// Without this, any uncaught render-time exception anywhere in the tree
// unmounts the whole app, leaving a genuinely blank page with zero signal
// to the user or to us. Error boundaries must be class components — there
// is no hook equivalent.
export default class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('N-CORE crashed:', error, info?.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div
        style={{
          minHeight: '100svh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
          padding: 24,
          textAlign: 'center',
          background: '#0B0E14',
          color: '#e8ecf3',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        <span style={{ fontSize: 32 }}>⚠️</span>
        <p style={{ margin: 0, fontSize: 15, maxWidth: 320, lineHeight: 1.5 }}>
          Something went wrong loading N-CORE⚡️. Reloading usually fixes it.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          style={{
            padding: '12px 20px',
            borderRadius: 12,
            border: '1px solid #00e5ff',
            background: 'rgba(0, 229, 255, 0.12)',
            color: '#00e5ff',
            fontSize: 14,
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          Reload
        </button>
      </div>
    )
  }
}
