import { IconEraser } from '@tabler/icons-react'
import { useChat } from '../hooks/useChat'
import { ChatStream } from './ChatStream'
import { Composer } from './Composer'

interface Props {
  selectedDomainId: string | null
}

export function RightPage({ selectedDomainId }: Props) {
  const { messages, streaming, sendMessage, clearChat } = useChat()

  function handleSend(text: string) {
    if (selectedDomainId) sendMessage(selectedDomainId, text)
  }

  return (
    <div className="page page-right">
      <div className="chat-header">
        <h2 className="conv-heading">Conversation</h2>
        <button
          className="clear-btn"
          onClick={clearChat}
          disabled={streaming || messages.length === 0}
          aria-label="Clear conversation"
        >
          <IconEraser size={13} stroke={2} />
          Clear
        </button>
      </div>

      {messages.length === 0 && (
        <p style={{ fontSize: '12px', color: 'var(--ink-faded)', fontStyle: 'italic', margin: '0 0 12px' }}>
          {selectedDomainId
            ? 'Ask your first compliance question below.'
            : 'Select a domain on the left to get started.'}
        </p>
      )}

      <ChatStream messages={messages} />

      <Composer onSend={handleSend} disabled={streaming || !selectedDomainId} />

      <span className="page-number">ii</span>
    </div>
  )
}
