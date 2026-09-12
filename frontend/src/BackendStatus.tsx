import { useEffect, useState } from 'react'

const apiUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
type Status = 'checking' | 'connected' | 'offline'

export default function BackendStatus() {
  const [status, setStatus] = useState<Status>('checking')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    const timeout = window.setTimeout(() => controller.abort(), 5000)
    setStatus('checking')
    async function check() {
      try {
        const response = await fetch(`${apiUrl}/health`, { signal: controller.signal })
        if (!response.ok) throw new Error('Health request failed')
        const data: unknown = await response.json()
        if (!data || typeof data !== 'object' || !('status' in data) || data.status !== 'ok'
          || !('service' in data) || data.service !== 'fact-layer-api') {
          throw new Error('Unexpected health response')
        }
        if (active) setStatus('connected')
      } catch {
        if (active) setStatus('offline')
      } finally {
        window.clearTimeout(timeout)
      }
    }
    void check()
    return () => { active = false; controller.abort(); window.clearTimeout(timeout) }
  }, [attempt])

  return <div className={`backend-status ${status}`}>
    <span className="status-dot" aria-hidden="true" />
    <span role="status">{status === 'checking' ? 'Checking connection…' : status === 'connected' ? 'Backend connected' : 'Backend unavailable'}</span>
    {status === 'offline' && <button onClick={() => setAttempt(value => value + 1)}>Retry connection</button>}
  </div>
}
