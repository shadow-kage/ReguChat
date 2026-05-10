import type { Domain } from '../types'

interface Props {
  domains: Domain[]
  selectedDomainId: string | null
  onSelectDomain: (id: string) => void
}

export function LeftPage({ domains, selectedDomainId, onSelectDomain }: Props) {
  return (
    <div className="page page-left">
      <div className="page-masthead">
        <div className="logo-mark">R</div>
        <span className="version-tag">v0.1 · Pilot</span>
      </div>

      <h1 className="h-display">ReguChat</h1>
      <p className="lede">
        Compliance-aware, domain-specific conversational AI — grounded in your regulatory
        documents.
      </p>

      <p className="h-section" style={{ marginTop: '20px' }}>Available domains</p>
      <ul className="source-list">
        {domains.length === 0 ? (
          <li>
            <span className="source-pill">Loading…</span>
          </li>
        ) : (
          domains.map((d) => (
            <li key={d.id}>
              <button
                className="source-pill"
                style={
                  selectedDomainId === d.id
                    ? {
                        background: 'rgba(139, 115, 75, 0.18)',
                        borderColor: 'rgba(139, 115, 75, 0.6)',
                        cursor: 'default',
                      }
                    : { cursor: 'pointer' }
                }
                onClick={() => onSelectDomain(d.id)}
                title={d.description}
                aria-pressed={selectedDomainId === d.id}
              >
                {d.name}
              </button>
            </li>
          ))
        )}
      </ul>

      <span className="page-number">i</span>
    </div>
  )
}
