import { useEffect, useState } from 'react'
import { ArrowRight, ArrowUpRight, Check, ChevronRight, FileText, Files, GitCompareArrows, Layers3, Link2, Search, Sparkles, Upload, Waypoints } from 'lucide-react'
import BackendStatus from './BackendStatus'

type View = 'documents' | 'facts' | 'comparisons'
const sections = {
  documents: { title: 'Documents', subtitle: 'The starting point for everything you know.', icon: Files, emptyTitle: 'Good knowledge starts with a source.', emptyText: 'Your documents will live here. Soon, you’ll be able to upload PDFs and turn scattered information into traceable facts.' },
  facts: { title: 'Facts', subtitle: 'Every claim, connected to its evidence.', icon: Search, emptyTitle: 'A place for the details that matter.', emptyText: 'Extracted facts will appear here with their values, context, and source passages. Add and process documents once PDF upload is available.' },
  comparisons: { title: 'Comparisons', subtitle: 'See where your sources agree — and why they differ.', icon: GitCompareArrows, emptyTitle: 'Find the context between the claims.', emptyText: 'Compare facts side by side to explore agreement, possible contradictions, and differences explained by context.' },
}
function readView(): View { //return type will be a View
  const value = window.location.hash.slice(1) //if the url is {{URL}}/#facts, this will return 'facts' only
  return value === 'facts' || value === 'comparisons' ? value : 'documents'
}

export default function App() {
  const [view, setView] = useState<View>(readView)
  useEffect(() => {
    const onHashChange = () => setView(readView())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])
  useEffect(() => { document.title = `${sections[view].title} · Fact Layer` }, [view])
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
          {([{key:'documents',label:'Documents',description:'Your source collection',icon:Files},{key:'facts',label:'Facts',description:'Grounded in evidence',icon:Search},{key:'comparisons',label:'Comparisons',description:'Connections across sources',icon:GitCompareArrows}] as const).map(item => <a href={`#${item.key}`} key={item.key} className="stat-card"><div className="stat-top"><span>{item.label}</span><item.icon size={18} /></div><div className="stat-number">—</div><div className="stat-bottom"><span>{item.description}</span><ArrowUpRight size={15} /></div></a>)}
        </div>

        <section className="collection" aria-labelledby="collection-title"><div className="collection-heading"><div><h2 id="collection-title">{view === 'documents' ? 'Your documents' : view === 'facts' ? 'Your facts' : 'Your comparisons'}</h2><span>{view === 'documents' ? 'A home for your source material' : 'Your knowledge will take shape here'}</span></div><span className="coming-label">Coming soon</span></div><div className="empty-state"><div className="empty-icon"><EmptyIcon size={27} strokeWidth={1.4} /></div><h3>{section.emptyTitle}</h3><p>{section.emptyText}</p>{view === 'documents' ? <><button className="upload-button" disabled aria-describedby="upload-note"><Upload size={16} /> Upload PDF</button><span id="upload-note" className="empty-hint">PDF upload is the next step.</span></> : <a className="back-link" href="#documents">Go to documents <ArrowRight size={16} /></a>}</div></section>

        <div className="workflow-strip"><span className="workflow-title">HOW IT WILL WORK</span><span><span className="step-number">1</span> Add documents</span><ChevronRight size={14} /><span><span className="step-number">2</span> Discover facts</span><ChevronRight size={14} /><span><span className="step-number">3</span> Compare evidence</span></div>
        <footer className="page-footer"><span>Built for curiosity. Grounded in evidence.</span><span>Fact Layer · Practice workspace</span></footer>
      </main>
    </div>
  </div>
}
