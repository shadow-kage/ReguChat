import { IconCheck, IconSearch } from '@tabler/icons-react'

interface Props {
  cache: 'hit' | 'miss'
  done: boolean
}

export function StatusBadge({ cache, done }: Props) {
  if (cache === 'hit') {
    return (
      <span className="status-badge badge-hit">
        <IconCheck size={12} stroke={2.5} />
        Cache hit
      </span>
    )
  }

  // miss + streaming: show searching indicator
  if (!done) {
    return (
      <span className="status-badge badge-searching">
        <IconSearch size={12} stroke={2} />
        Searching knowledge base…
      </span>
    )
  }

  // miss + done: badge served its purpose, hide it
  return null
}
