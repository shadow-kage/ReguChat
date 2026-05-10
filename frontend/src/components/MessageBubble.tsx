import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message } from '../types'
import { StatusBadge } from './StatusBadge'

interface Props {
  message: Message
}

export function MessageBubble({ message }: Props) {
  if (message.role === 'user') {
    return <div className="bubble-user">{message.text}</div>
  }

  if (message.role === 'error') {
    return <div className="bubble-error">{message.text}</div>
  }

  const isStreaming = !message.done
  return (
    <div className="bubble-bot-group">
      {message.cache && <StatusBadge cache={message.cache} done={message.done} />}
      <div className={`bubble-bot${isStreaming ? ' bubble-streaming' : ''}`}>
        {message.text ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
        ) : (
          <span className="bubble-note">Thinking…</span>
        )}
      </div>
    </div>
  )
}
