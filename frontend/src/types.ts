export interface Domain {
  id: string
  name: string
  description: string
}

export interface UserMessage {
  id: string
  role: 'user'
  text: string
}

export interface BotMessage {
  id: string
  role: 'bot'
  text: string
  cache?: 'hit' | 'miss'
  done: boolean
}

export interface ErrorMessage {
  id: string
  role: 'error'
  text: string
}

export type Message = UserMessage | BotMessage | ErrorMessage

export type SSEEvent =
  | { event: 'status'; cache: 'hit' | 'miss' }
  | { event: 'text'; text: string }
  | { event: 'done' }
