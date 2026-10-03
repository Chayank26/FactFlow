import { useEffect, useState } from 'react'

const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8019').replace(/\/$/, '')
type Source = { id: string; filename: string }

export default function SourceSelect({ value, onChange, revision }: { value: string; onChange: (value: string) => void; revision: number }) {
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [items, setItems] = useState<Source[]>([])
  const [selected, setSelected] = useState<Source | null>(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(false)
    const params = new URLSearchParams({ search, limit: '20', offset: String(offset) })
    void fetch(`${apiBase}/documents?${params}`, { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('Sources unavailable')
        const data = await response.json() as { items: Source[]; total: number }
        if (controller.signal.aborted) return
        if (offset > 0 && offset >= data.total) { setOffset(0); return }
        setItems(data.items)
        setTotal(data.total)
      })
      .catch(() => { if (!controller.signal.aborted) setError(true) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [search, offset, revision, retry])
  return <div>
    <label>Find source by filename<input value={search} onChange={event => { setSearch(event.target.value); setOffset(0) }} /></label>
    <label>Source<select value={value} onChange={event => { setSelected(items.find(item => item.id === event.target.value) || null); onChange(event.target.value) }}>
      <option value="">All documents</option>
      {value && !items.some(item => item.id === value) && <option value={value}>{selected?.id === value ? selected.filename : 'Selected source'}</option>}
      {items.map(item => <option key={item.id} value={item.id}>{item.filename}</option>)}
    </select></label>
    {error ? <p>Sources could not be loaded. <button onClick={() => setRetry(attempt => attempt + 1)}>Retry sources</button></p> : <span>{loading ? 'Loading sources…' : `${total} matching sources`}</span>}
    <div><button disabled={loading || offset === 0} onClick={() => setOffset(page => Math.max(0, page - 20))}>Previous sources</button><button disabled={loading || error || offset + 20 >= total} onClick={() => setOffset(page => page + 20)}>Next sources</button></div>
  </div>
}
