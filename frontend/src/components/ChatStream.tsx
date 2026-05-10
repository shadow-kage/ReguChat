import { useEffect, useRef } from 'react'
import type { Message } from '../types'
import { MessageBubble } from './MessageBubble'

interface Props {
  messages: Message[]
}

export function ChatStream({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="chat-stream">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} aria-hidden="true" />
    </div>
  )
}
