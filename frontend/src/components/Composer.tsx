import { useState, useRef, type KeyboardEvent } from 'react'
import { IconSend } from '@tabler/icons-react'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
}

export function Composer({ onSend, disabled }: Props) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function submit() {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
    // Reset auto-grow height after clearing
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function handleInput() {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${ta.scrollHeight}px`
  }

  return (
    <div>
      <div className="composer">
        <textarea
          ref={textareaRef}
          className="composer-textarea"
          placeholder="Ask a compliance question…"
          rows={1}
          value={text}
          disabled={disabled}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
        />
        <button
          className="send-btn"
          onClick={submit}
          disabled={disabled || !text.trim()}
          aria-label="Send message"
        >
          <IconSend size={16} stroke={2} />
        </button>
      </div>
      <p className="composer-hint">Shift + Enter for new line</p>
    </div>
  )
}
