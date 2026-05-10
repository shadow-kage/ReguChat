import type { SSEEvent } from '../types'

// EventSource is GET-only; we use fetch + ReadableStream to POST and receive SSE frames.
export async function* streamQuery(
  domainId: string,
  query: string,
): AsyncGenerator<SSEEvent> {
  const response = await fetch('/api/query/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain_id: domainId, query }),
  })

  if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  if (!response.body) throw new Error('Response body is null')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE frames are delimited by \n\n; keep any partial frame in buffer.
      const frames = buffer.split('\n\n')
      buffer = frames.pop() ?? ''

      for (const frame of frames) {
        for (const line of frame.split('\n')) {
          if (line.startsWith('data: ')) {
            const json = line.slice(6).trim()
            if (json) yield JSON.parse(json) as SSEEvent
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
