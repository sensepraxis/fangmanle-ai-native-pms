// SPDX-License-Identifier: Apache-2.0
// API: analytics
import { req, authHeaders, BASE } from './client'
import { t } from '../i18n'

export const analyticsApi = {
  dashboard: (hotelId: number, period = '今日') =>
    req<any>('GET', `/dashboard?hotel_id=${hotelId}&period=${encodeURIComponent(period)}`),
  analyticsAiActions: (hotelId: number) =>
    req<any>('GET', `/analytics/ai-actions?hotel_id=${hotelId}`),
  analyticsAiExecute: (hotelId: number, action: Record<string, unknown>) =>
    req<any>('POST', `/analytics/ai-actions/execute?hotel_id=${hotelId}`, { action }),
  boardAiNarrate: (
    hotelId: number,
    kind: 'order_risks' | 'profit_insights' | 'pricing_compare',
    payload?: Record<string, any>,
  ) => req<any>('POST', `/board-ai/${kind}?hotel_id=${hotelId}`, payload || {}),
  boardAiExecute: (hotelId: number, action: Record<string, any>) =>
    req<any>('POST', `/board-ai/execute?hotel_id=${hotelId}`, { action }),
  insightsWorkspace: (
    hotelId: number,
    opts?: { period?: string; compare?: string; start?: string; end?: string; olap_dim?: string },
  ) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId) })
    if (opts?.period) q.set('period', opts.period)
    if (opts?.compare) q.set('compare', opts.compare)
    if (opts?.start) q.set('start', opts.start)
    if (opts?.end) q.set('end', opts.end)
    if (opts?.olap_dim) q.set('olap_dim', opts.olap_dim)
    return req<any>('GET', `/insights/workspace?${q.toString()}`)
  },
  insightsOlap: (
    hotelId: number,
    opts?: { period?: string; start?: string; end?: string; dim?: string },
  ) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId) })
    if (opts?.period) q.set('period', opts.period)
    if (opts?.start) q.set('start', opts.start)
    if (opts?.end) q.set('end', opts.end)
    if (opts?.dim) q.set('dim', opts.dim)
    return req<any>('GET', `/insights/olap?${q.toString()}`)
  },
  insightsAsk: (
    hotelId: number,
    payload: {
      question?: string
      period?: string
      compare?: string
      start?: string
      end?: string
      growth_factor?: number
    },
  ) => req<any>('POST', `/insights/ask?hotel_id=${hotelId}`, payload),
  insightsAskStream: async (
    hotelId: number,
    onEvent: (evt: { type: string; content?: string; data?: any; message?: string }) => void,
    payload: {
      question?: string
      growth_factor?: number
      period?: string
      compare?: string
      start?: string
      end?: string
    } = {},
    signal?: AbortSignal,
  ) => {
    const res = await fetch(`${BASE}/insights/ask/stream?hotel_id=${hotelId}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
      signal,
    })
    if (res.status === 401) {
      localStorage.removeItem('fml_token')
      if (!location.hash.includes('/login')) location.hash = '#/login'
      throw new Error('未登录或令牌失效')
    }
    if (!res.ok) {
      const json: any = await res.json().catch(() => ({}))
      throw new Error(json.detail || '流式请求失败')
    }
    const reader = res.body?.getReader()
    if (!reader) throw new Error('无响应流')
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data:')) continue
        onEvent(JSON.parse(line.slice(5).trim()))
      }
    }
    if (buffer.trim().startsWith('data:')) {
      onEvent(JSON.parse(buffer.trim().slice(5).trim()))
    }
  },
  insightsChat: (
    hotelId: number,
    payload: { message: string; history?: { role: string; content: string }[] },
  ) => req<any>('POST', `/insights/chat?hotel_id=${hotelId}`, payload),
  insightsAiAskCatalog: (hotelId: number) =>
    req<any>('GET', `/insights/ai-ask/catalog?hotel_id=${hotelId}`),
  insightsAiAskRoute: (
    hotelId: number,
    payload: {
      question: string
      period?: string
      baseline?: string
      session_id?: string
      clarify_round?: number
    },
  ) => req<any>('POST', `/insights/ai-ask/route?hotel_id=${hotelId}`, payload),
  insightsAiAskClarify: (
    hotelId: number,
    payload: {
      query_id: number
      question?: string
      intent_id?: string
      slot?: string
      slot_value?: string | number
      period?: string
      baseline?: string
      clarify_round?: number
    },
  ) => req<any>('POST', `/insights/ai-ask/clarify?hotel_id=${hotelId}`, payload),
  insightsAiAskConfirm: (
    hotelId: number,
    payload: {
      query_id: number
      confirmed?: boolean
      intent_id?: string
      slots?: Record<string, unknown>
      period?: string
      baseline?: string
      start?: string
      end?: string
    },
  ) => req<any>('POST', `/insights/ai-ask/confirm?hotel_id=${hotelId}`, payload),
  insightsAiAskPiiAck: (
    hotelId: number,
    payload: {
      query_id: number
      ack_by: string
      period?: string
      baseline?: string
      start?: string
      end?: string
    },
  ) => req<any>('POST', `/insights/ai-ask/pii-ack?hotel_id=${hotelId}`, payload),
  insightsAiAskConfirmStream: async (
    hotelId: number,
    onEvent: (evt: {
      type: string
      content?: string
      message?: string
      stage?: string
      model?: string
      result?: any
      intent_label?: string
      data?: any
    }) => void,
    payload: {
      query_id: number
      confirmed?: boolean
      intent_id?: string
      slots?: Record<string, unknown>
      period?: string
      baseline?: string
      start?: string
      end?: string
    },
    signal?: AbortSignal,
  ) => {
    const res = await fetch(`${BASE}/insights/ai-ask/confirm/stream?hotel_id=${hotelId}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
      signal,
    })
    if (res.status === 401) {
      localStorage.removeItem('fml_token')
      if (!location.hash.includes('/login')) location.hash = '#/login'
      throw new Error('未登录或令牌失效')
    }
    if (!res.ok) {
      const json: any = await res.json().catch(() => ({}))
      throw new Error(json.detail || '流式请求失败')
    }
    const reader = res.body?.getReader()
    if (!reader) throw new Error('无响应流')
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data:')) continue
        onEvent(JSON.parse(line.slice(5).trim()))
      }
    }
    if (buffer.trim().startsWith('data:')) {
      onEvent(JSON.parse(buffer.trim().slice(5).trim()))
    }
  },
}
