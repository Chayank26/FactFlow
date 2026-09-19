import { useEffect, useState } from 'react'
import type { ChangeEvent } from 'react'
import { ArrowRight, ArrowUpRight, Check, ChevronRight, FileText, Files, GitCompareArrows, Layers3, Link2, RefreshCw, Search, Sparkles, Trash2, Upload, Waypoints, X } from 'lucide-react'
import BackendStatus from './BackendStatus'

type View = 'documents' | 'facts' | 'comparisons'
type DocumentRecord = {
  id: string
  filename: string
  size_bytes: number
  content_type: string | null
  stored_path: string
  created_at: string
  status: string
}
type ComparisonRecord = {
  id: string
  relationship: 'agreement' | 'difference'
  summary: string
  left_document_id: string
  left_document_name: string
  left_claim: string
  left_page: number
  left_source_text: string
  right_document_id: string
  right_document_name: string
  right_claim: string
  right_page: number
  right_source_text: string
}
type RelationshipFilter = '' | 'agreement' | 'difference'
type FactRecord = {
  id: string
  document_id: string
  claim: string
  source_page: number
  source_text: string
  created_at: string
}

const sections = {
  documents: { title: 'Documents', subtitle: 'The starting point for everything you know.', icon: Files, emptyTitle: 'Good knowledge starts with a source.', emptyText: 'Your documents will live here. Soon, you’ll be able to upload PDFs and turn scattered information into traceable facts.' },
  facts: { title: 'Facts', subtitle: 'Every claim, connected to its evidence.', icon: Search, emptyTitle: 'A place for the details that matter.', emptyText: 'Extracted facts will appear here with their values, context, and source passages. Add and process documents once PDF upload is available.' },
  comparisons: { title: 'Comparisons', subtitle: 'See where your sources agree — and why they differ.', icon: GitCompareArrows, emptyTitle: 'Find the context between the claims.', emptyText: 'Compare facts side by side to explore agreement, possible contradictions, and differences explained by context.' },
}

const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8019').replace(/\/$/, '')

function readView(): View {
  const value = window.location.hash.slice(1)
  return value === 'facts' || value === 'comparisons' ? value : 'documents'
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unknown date'
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(date)
}

export default function App() {
  const [view, setView] = useState<View>(readView)
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [loadingDocuments, setLoadingDocuments] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [comparisons, setComparisons] = useState<ComparisonRecord[]>([])
  const [loadingComparisons, setLoadingComparisons] = useState(false)
  const [comparisonDocumentId, setComparisonDocumentId] = useState('')
  const [comparisonRelationship, setComparisonRelationship] = useState<RelationshipFilter>('')
  const [selectedDocument, setSelectedDocument] = useState<DocumentRecord | null>(null)
  const [selectedFacts, setSelectedFacts] = useState<FactRecord[]>([])
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [managementError, setManagementError] = useState<string | null>(null)

  useEffect(() => {
    const onHashChange = () => setView(readView())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    if (view !== 'documents' && view !== 'comparisons') return

    const controller = new AbortController()
    setLoadingDocuments(true)
    void fetch(`${apiBase}/documents`, { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('Could not load documents')
        const data = await response.json() as DocumentRecord[]
        setDocuments(Array.isArray(data) ? data : [])
      })
      .catch(() => {
        setDocuments([])
      })
      .finally(() => {
        setLoadingDocuments(false)
      })

    return () => controller.abort()
  }, [view])

  useEffect(() => {
    if (view !== 'comparisons') return

    const controller = new AbortController()
    setLoadingComparisons(true)
    const params = new URLSearchParams()
    if (comparisonDocumentId) params.set('document_id', comparisonDocumentId)
    if (comparisonRelationship) params.set('relationship', comparisonRelationship)
    const query = params.toString()
    void fetch(`${apiBase}/comparisons${query ? `?${query}` : ''}`, { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('Could not load comparisons')
        const data = await response.json() as ComparisonRecord[]
        setComparisons(Array.isArray(data) ? data : [])
      })
      .catch(() => {
        setComparisons([])
      })
      .finally(() => {
        setLoadingComparisons(false)
      })

    return () => controller.abort()
  }, [view, comparisonDocumentId, comparisonRelationship])

  useEffect(() => { document.title = `${sections[view].title} · Fact Layer` }, [view])

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploading(true)
    setUploadError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch(`${apiBase}/documents`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      const created = await response.json() as DocumentRecord
      setDocuments(current => [created, ...current])
      setView('documents')
    } catch {
      setUploadError('The upload could not be saved. Please try again.')
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  const openDocument = async (document: DocumentRecord) => {
    setSelectedDocument(document)
    setSelectedFacts([])
    setManagementError(null)
    setLoadingDetails(true)
    try {
      const [detailResponse, factsResponse] = await Promise.all([
        fetch(`${apiBase}/documents/${document.id}`),
        fetch(`${apiBase}/facts?document_id=${encodeURIComponent(document.id)}`),
      ])
      if (!detailResponse.ok || !factsResponse.ok) throw new Error('Could not load document details')
      setSelectedDocument(await detailResponse.json() as DocumentRecord)
      setSelectedFacts(await factsResponse.json() as FactRecord[])
    } catch {
      setManagementError('Document details could not be loaded.')
    } finally {
      setLoadingDetails(false)
    }
  }

  const reprocessDocument = async (document: DocumentRecord) => {
    setManagementError(null)
    try {
      const response = await fetch(`${apiBase}/documents/${document.id}/process`, { method: 'POST' })
      if (!response.ok) throw new Error('Could not reprocess document')
      const updated = await response.json() as DocumentRecord
      setDocuments(current => current.map(item => item.id === updated.id ? updated : item))
      if (selectedDocument?.id === updated.id) await openDocument(updated)
    } catch {
      setManagementError('The document could not be reprocessed.')
    }
  }

  const deleteDocument = async (document: DocumentRecord) => {
    if (!window.confirm(`Delete ${document.filename}? Its extracted facts will also be removed.`)) return
    setManagementError(null)
    try {
      const response = await fetch(`${apiBase}/documents/${document.id}`, { method: 'DELETE' })
      if (!response.ok) throw new Error('Could not delete document')
      setDocuments(current => current.filter(item => item.id !== document.id))
      if (selectedDocument?.id === document.id) setSelectedDocument(null)
    } catch {
      setManagementError('The document could not be deleted.')
    }
  }

  const section = sections[view]
  const EmptyIcon = section.icon

  return <div className="app-layout">
    <a href="#main-content" className="skip-link">Skip to content</a>
    <aside className="sidebar">
      <a className="brand" href="#documents" aria-label="Fact Layer home"><span className="brand-mark"><Layers3 size={22} /></span>Fact Layer<span className="brand-dot">.</span></a>
      <div className="workspace-label">PERSONAL WORKSPACE</div>
      <nav aria-label="Workspace">
        {(Object.keys(sections) as View[]).map(key => {
          const Icon = sections[key].icon
          return <a key={key} href={`#${key}`} className={`nav-item ${view === key ? 'active' : ''}`} aria-current={view === key ? 'page' : undefined}><Icon size={19} strokeWidth={1.7} /><span>{sections[key].title}</span>{view === key && <span className="active-dot" />}</a>
        })}
      </nav>
      <div className="sidebar-note"><span className="note-icon"><Link2 size={18} /></span><strong>Evidence comes first.</strong><p>Follow every fact back to where it began.</p></div>
      <div className="sidebar-footer"><div className="avatar">P</div><div><strong>Personal workspace</strong><span>Local development</span></div></div>
    </aside>

    <div className="main-column">
      <header className="topbar"><div className="breadcrumb"><span>Workspace</span><ChevronRight size={14} /><span>{section.title}</span></div><BackendStatus /></header>
      <main id="main-content" tabIndex={-1}>
        <div className="page-heading"><div><div className="eyebrow">YOUR KNOWLEDGE WORKSPACE</div><h1>{section.title}</h1><p>{section.subtitle}</p></div><span className="workspace-badge"><span /> Getting started</span></div>

        <section className="intro-card" aria-labelledby="intro-title"><div className="intro-copy"><span className="intro-label"><Sparkles size={14} /> CONNECT THE DOTS</span><h2 id="intro-title">From scattered pages<br />to a clearer picture.</h2><p>Bring your sources together. Discover the facts.<br className="desktop-break" /> Understand the story between them.</p><a href="#comparisons" className="intro-link">Explore comparisons <ArrowRight size={16} /></a></div><div className="source-art" aria-hidden="true"><div className="art-orbit" /><div className="art-line line-one" /><div className="art-line line-two" /><div className="art-paper paper-one"><FileText size={24} /><i /><i /><i /></div><div className="art-center"><Waypoints size={32} /></div><div className="art-paper paper-two"><span className="art-check"><Check size={17} /></span><i /><i /><i /></div><span className="art-spark spark-one" /><span className="art-spark spark-two" /></div></section>

        <div className="stats-grid">
          {([{key:'documents',label:'Documents',description:'Your source collection',icon:Files},{key:'facts',label:'Facts',description:'Grounded in evidence',icon:Search},{key:'comparisons',label:'Comparisons',description:'Connections across sources',icon:GitCompareArrows}] as const).map(item => <a href={`#${item.key}`} key={item.key} className="stat-card"><div className="stat-top"><span>{item.label}</span><item.icon size={18} /></div><div className="stat-number">{item.key === 'documents' ? documents.length : '—'}</div><div className="stat-bottom"><span>{item.description}</span><ArrowUpRight size={15} /></div></a>)}
        </div>

        <section className="collection" aria-labelledby="collection-title"><div className="collection-heading"><div><h2 id="collection-title">{view === 'documents' ? 'Your documents' : view === 'facts' ? 'Your facts' : 'Your comparisons'}</h2><span>{view === 'documents' ? 'A home for your source material' : 'Your knowledge will take shape here'}</span></div><span className="coming-label">{view === 'documents' ? 'Live data' : 'Coming soon'}</span></div>

          {view === 'documents' ? (
            <div className="documents-panel">
              <div className="documents-actions">
                <label className="upload-button upload-button-live" aria-label="Upload a document">
                  <Upload size={16} /> Upload PDF
                  <input type="file" onChange={handleUpload} hidden />
                </label>
                {uploading && <span className="empty-hint">Uploading…</span>}
                {uploadError && <span className="error-text">{uploadError}</span>}
              </div>

              {loadingDocuments ? (
                <div className="document-loading">Loading documents…</div>
              ) : documents.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon"><EmptyIcon size={27} strokeWidth={1.4} /></div>
                  <h3>{section.emptyTitle}</h3>
                  <p>{section.emptyText}</p>
                  <label className="upload-button upload-button-live" aria-label="Upload your first document">
                    <Upload size={16} /> Upload PDF
                    <input type="file" onChange={handleUpload} hidden />
                  </label>
                </div>
              ) : (
                <div className="document-list">
                  {documents.map(document => (
                    <article key={document.id} className="document-card">
                      <div className="document-icon"><Files size={18} /></div>
                      <div className="document-copy">
                        <div className="document-header">
                          <h3>{document.filename}</h3>
                          <span className="document-status">{document.status}</span>
                        </div>
                        <div className="document-meta">
                          <span>{formatBytes(document.size_bytes)}</span>
                          <span>{document.content_type || 'unknown type'}</span>
                          <span>{formatDate(document.created_at)}</span>
                        </div>
                      </div>
                      <div className="document-actions">
                        <button className="icon-action" onClick={() => void openDocument(document)} title={`View ${document.filename}`} aria-label={`View ${document.filename}`}><Search size={15} /></button>
                        <button className="icon-action" onClick={() => void reprocessDocument(document)} title={`Reprocess ${document.filename}`} aria-label={`Reprocess ${document.filename}`}><RefreshCw size={15} /></button>
                        <button className="icon-action danger" onClick={() => void deleteDocument(document)} title={`Delete ${document.filename}`} aria-label={`Delete ${document.filename}`}><Trash2 size={15} /></button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
              {managementError && <div className="error-text management-error">{managementError}</div>}
              {selectedDocument && <section className="document-detail" aria-labelledby="document-detail-title">
                <div className="detail-heading">
                  <div><span className="eyebrow">DOCUMENT DETAIL</span><h3 id="document-detail-title">{selectedDocument.filename}</h3></div>
                  <button className="icon-action" onClick={() => setSelectedDocument(null)} title="Close document detail" aria-label="Close document detail"><X size={16} /></button>
                </div>
                {loadingDetails ? <div className="document-loading">Loading evidence…</div> : <>
                  <div className="detail-meta"><span>{formatBytes(selectedDocument.size_bytes)}</span><span>{selectedDocument.status}</span><span>{formatDate(selectedDocument.created_at)}</span></div>
                  {selectedFacts.length === 0 ? <p className="detail-empty">No extracted facts are stored for this document.</p> : <div className="fact-list">
                    {selectedFacts.map(fact => <article className="fact-row" key={fact.id}><strong>{fact.claim}</strong><span>Page {fact.source_page} · {fact.source_text}</span></article>)}
                  </div>}
                </>}
              </section>}
            </div>
          ) : view === 'comparisons' ? (
            <div className="comparison-panel">
              <div className="comparison-filters" aria-label="Comparison filters">
                <label>Source
                  <select value={comparisonDocumentId} onChange={event => setComparisonDocumentId(event.target.value)}>
                    <option value="">All documents</option>
                    {documents.map(document => <option key={document.id} value={document.id}>{document.filename}</option>)}
                  </select>
                </label>
                <label>Relationship
                  <select value={comparisonRelationship} onChange={event => setComparisonRelationship(event.target.value as RelationshipFilter)}>
                    <option value="">All relationships</option>
                    <option value="agreement">Agreement</option>
                    <option value="difference">Difference</option>
                  </select>
                </label>
              </div>
              {loadingComparisons ? (
                <div className="document-loading">Finding connections…</div>
              ) : comparisons.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon"><EmptyIcon size={27} strokeWidth={1.4} /></div>
                  <h3>{section.emptyTitle}</h3>
                  <p>{section.emptyText}</p>
                  <a className="back-link" href="#documents">Go to documents <ArrowRight size={16} /></a>
                </div>
              ) : (
                <div className="comparison-list">
                  {comparisons.map(comparison => (
                    <article key={comparison.id} className="comparison-card">
                      <div className="comparison-card-header">
                        <span className={`relationship-label ${comparison.relationship}`}>{comparison.relationship}</span>
                        <span className="comparison-summary">{comparison.summary}</span>
                      </div>
                      <div className="comparison-sources">
                        <div className="comparison-source">
                          <strong>{comparison.left_document_name}</strong>
                          <p>{comparison.left_claim}</p>
                          <span>Page {comparison.left_page} · {comparison.left_source_text}</span>
                        </div>
                        <div className="comparison-divider" aria-hidden="true"><GitCompareArrows size={16} /></div>
                        <div className="comparison-source">
                          <strong>{comparison.right_document_name}</strong>
                          <p>{comparison.right_claim}</p>
                          <span>Page {comparison.right_page} · {comparison.right_source_text}</span>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon"><EmptyIcon size={27} strokeWidth={1.4} /></div>
              <h3>{section.emptyTitle}</h3>
              <p>{section.emptyText}</p>
              <a className="back-link" href="#documents">Go to documents <ArrowRight size={16} /></a>
            </div>
          )}
        </section>

        <div className="workflow-strip"><span className="workflow-title">HOW IT WILL WORK</span><span><span className="step-number">1</span> Add documents</span><ChevronRight size={14} /><span><span className="step-number">2</span> Discover facts</span><ChevronRight size={14} /><span><span className="step-number">3</span> Compare evidence</span></div>
        <footer className="page-footer"><span>Built for curiosity. Grounded in evidence.</span><span>Fact Layer · Practice workspace</span></footer>
      </main>
    </div>
  </div>
}
