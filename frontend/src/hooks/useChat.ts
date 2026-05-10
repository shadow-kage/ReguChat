import { useReducer, useCallback } from 'react'
import type { Message } from '../types'
import { streamQuery } from '../lib/sse'

type ChatState = {
  messages: Message[]
  streaming: boolean
}

type ChatAction =
  | { type: 'USER_MSG'; id: string; text: string }
  | { type: 'BOT_START'; id: string; cache: 'hit' | 'miss' }
  | { type: 'BOT_CHUNK'; id: string; chunk: string }
  | { type: 'BOT_DONE'; id: string }
  | { type: 'BOT_ERROR'; id: string; text: string }
  | { type: 'CLEAR' }

function reducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'USER_MSG':
      return {
        ...state,
        streaming: true,
        messages: [...state.messages, { id: action.id, role: 'user', text: action.text }],
      }
    case 'BOT_START':
      return {
        ...state,
        messages: [
          ...state.messages,
          { id: action.id, role: 'bot', text: '', cache: action.cache, done: false },
        ],
      }
    case 'BOT_CHUNK':
      return {
        ...state,
        messages: state.messages.map((m) =>
          m.id === action.id && m.role === 'bot' ? { ...m, text: m.text + action.chunk } : m,
        ),
      }
    case 'BOT_DONE':
      return {
        ...state,
        streaming: false,
        messages: state.messages.map((m) =>
          m.id === action.id && m.role === 'bot' ? { ...m, done: true } : m,
        ),
      }
    case 'BOT_ERROR':
      return {
        ...state,
        streaming: false,
        messages: [
          // Drop the incomplete bot bubble (if started) and replace with an error message.
          ...state.messages.filter((m) => !(m.id === action.id && m.role === 'bot')),
          { id: action.id, role: 'error', text: action.text },
        ],
      }
    case 'CLEAR':
      return { messages: [], streaming: false }
    default:
      return state
  }
}

const INITIAL: ChatState = { messages: [], streaming: false }

export function useChat() {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  const sendMessage = useCallback(
    async (domainId: string, text: string) => {
      if (!text.trim() || state.streaming) return

      const userId = crypto.randomUUID()
      const botId = crypto.randomUUID()
      dispatch({ type: 'USER_MSG', id: userId, text: text.trim() })

      try {
        let botStarted = false

        for await (const event of streamQuery(domainId, text.trim())) {
          if (event.event === 'status') {
            dispatch({ type: 'BOT_START', id: botId, cache: event.cache })
            botStarted = true
          } else if (event.event === 'text') {
            if (!botStarted) {
              // Backend skipped status event — start the bubble defensively.
              dispatch({ type: 'BOT_START', id: botId, cache: 'miss' })
              botStarted = true
            }
            dispatch({ type: 'BOT_CHUNK', id: botId, chunk: event.text })
          } else if (event.event === 'done') {
            dispatch({ type: 'BOT_DONE', id: botId })
            return
          }
        }

        // Stream closed without an explicit 'done' — mark complete anyway.
        dispatch({ type: 'BOT_DONE', id: botId })
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error'
        dispatch({ type: 'BOT_ERROR', id: botId, text: `Connection error: ${msg}` })
      }
    },
    [state.streaming],
  )

  const clearChat = useCallback(() => {
    if (!state.streaming) dispatch({ type: 'CLEAR' })
  }, [state.streaming])

  return {
    messages: state.messages,
    streaming: state.streaming,
    sendMessage,
    clearChat,
  }
}
