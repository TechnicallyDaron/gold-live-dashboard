import { NavLink } from 'react-router-dom'
import './TabBar.css'

const TABS = [
  { to: '/hub', label: 'HUB', icon: HubIcon, end: true },
  { to: '/bias', label: 'Bias', icon: BiasIcon },
  { to: '/chart', label: 'Chart', icon: ChartIcon },
  { to: '/news', label: 'News', icon: NewsIcon },
  { to: '/positions', label: 'Positions', icon: PositionsIcon },
]

function HubIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M4 5.5A1.5 1.5 0 0 1 5.5 4h13A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5v-13Z"
        stroke={active ? 'var(--bullion)' : 'var(--muted)'} strokeWidth="1.6" />
      <path d="M8 9h8M8 13h8M8 17h5" stroke={active ? 'var(--bullion)' : 'var(--muted)'} strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

function BiasIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M4 17l5-6 4 3 7-9" stroke={active ? 'var(--bullion)' : 'var(--muted)'} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 20h16" stroke={active ? 'var(--bullion)' : 'var(--muted)'} strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

function ChartIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M5 19V10M12 19V5M19 19v-6" stroke={active ? 'var(--bullion)' : 'var(--muted)'} strokeWidth="1.8" strokeLinecap="round" />
      <path d="M4 20h16" stroke={active ? 'var(--bullion)' : 'var(--muted)'} strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

function NewsIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H15l4 4v12.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 19.5v-15Z"
        stroke={active ? 'var(--bullion)' : 'var(--muted)'} strokeWidth="1.6" />
      <path d="M9 12h6M9 16h6" stroke={active ? 'var(--bullion)' : 'var(--muted)'} strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

function PositionsIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <rect x="4" y="4" width="16" height="16" rx="3" stroke={active ? 'var(--bullion)' : 'var(--muted)'} strokeWidth="1.6" />
      <path d="M4 10h16" stroke={active ? 'var(--bullion)' : 'var(--muted)'} strokeWidth="1.6" />
      <path d="M9 14h6" stroke={active ? 'var(--bullion)' : 'var(--muted)'} strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

export default function TabBar() {
  return (
    <nav className="tab-bar" role="navigation" aria-label="Primary">
      {TABS.map(({ to, label, icon: Icon, end }) => (
        <NavLink key={to} to={to} end={end} className="tab-item">
          {({ isActive }) => (
            <>
              <Icon active={isActive} />
              <span className={isActive ? 'tab-label tab-label--active' : 'tab-label'}>
                {label}
              </span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}
