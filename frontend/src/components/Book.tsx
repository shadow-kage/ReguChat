import type { Domain } from '../types'
import { LeftPage } from './LeftPage'
import { RightPage } from './RightPage'

interface Props {
  domains: Domain[]
  selectedDomainId: string | null
  onSelectDomain: (id: string) => void
}

export function Book({ domains, selectedDomainId, onSelectDomain }: Props) {
  return (
    <div className="book-stage">
      <div className="book">
        <LeftPage
          domains={domains}
          selectedDomainId={selectedDomainId}
          onSelectDomain={onSelectDomain}
        />
        <RightPage selectedDomainId={selectedDomainId} />
        {/* Absolutely positioned — does not occupy a grid cell */}
        <div className="spine-shadow" aria-hidden="true" />
      </div>
    </div>
  )
}
