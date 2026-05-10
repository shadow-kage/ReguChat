import type { Domain } from '../types'

const BASE = '/api'

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json() as Promise<T>
}

export function fetchDomains(): Promise<Domain[]> {
  return apiFetch<Domain[]>('/domains')
}

export function fetchHealth(): Promise<{ status: string; domains: string[] }> {
  return apiFetch<{ status: string; domains: string[] }>('/health')
}
