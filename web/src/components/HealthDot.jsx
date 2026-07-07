import { api } from '../lib/api.js'
import { usePolling } from '../lib/usePolling.js'
import './HealthDot.css'

export default function HealthDot() {
  const { data, error } = usePolling(() => api.health(), [], 60000)
  const online = !!data && data.status === 'online' && !error

  return (
    <div className="health-dot-wrap" title={online ? 'API online' : 'API unreachable'}>
      <span className={online ? 'health-dot health-dot--online' : 'health-dot health-dot--offline'} />
      <span className="health-dot-label">{online ? 'Live' : 'Offline'}</span>
    </div>
  )
}
