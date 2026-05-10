import { useState, useEffect } from 'react'
import { Book } from './components/Book'
import { fetchDomains } from './lib/api'
import type { Domain } from './types'

export function App() {
  const [domains, setDomains] = useState<Domain[]>([])
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDomains()
      .then((list) => {
        setDomains(list)
        // Auto-select the only domain when there's just one.
        if (list.length === 1) setSelectedDomainId(list[0].id)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load domains'))
  }, [])

  if (error) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          color: '#f5ecd7',
          fontFamily: 'Inter, sans-serif',
          fontSize: 14,
        }}
      >
        <p>API Error: {error}</p>
      </div>
    )
  }

  return (
    <Book
      domains={domains}
      selectedDomainId={selectedDomainId}
      onSelectDomain={setSelectedDomainId}
    />
  )
}
