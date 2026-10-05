// SPDX-License-Identifier: Apache-2.0
// API: assets
import { req, authHeaders, BASE } from './client'
import { t } from '../i18n'

export const assetsApi = {
  assetsBoard: (hotelId: number) => req<any>('GET', `/assets/board?hotel_id=${hotelId}`),
  assetMaintenance: (assetId: number, hotelId: number) =>
    req<any[]>('GET', `/assets/${assetId}/maintenance?hotel_id=${hotelId}`),
  assetMaintenanceDetail: (assetId: number, maintId: number, hotelId: number) =>
    req<any>('GET', `/assets/${assetId}/maintenance/${maintId}?hotel_id=${hotelId}`),
  assetAiNextAction: (assetId: number, hotelId: number) =>
    req<any>('POST', `/assets/${assetId}/ai-next-action?hotel_id=${hotelId}`, {}),
  assetAiNextActionStream: async (
    assetId: number,
    hotelId: number,
    onEvent: (evt: { type: string; content?: string; data?: any; message?: string }) => void,
    signal?: AbortSignal,
  ) => {
    const res = await fetch(`${BASE}/assets/${assetId}/ai-next-action/stream?hotel_id=${hotelId}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: '{}',
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
        const payload = JSON.parse(line.slice(5).trim())
        onEvent(payload)
      }
    }
    if (buffer.trim().startsWith('data:')) {
      onEvent(JSON.parse(buffer.trim().slice(5).trim()))
    }
  },
  listSupplies: (hotelId: number) => req<any[]>('GET', `/supplies?hotel_id=${hotelId}`),
  suppliesBoard: (hotelId: number, line?: string) =>
    req<any>('GET', `/supplies/board?hotel_id=${hotelId}${line ? `&line=${line}` : ''}`),
  approveRestock: (oid: number) => req<any>('POST', `/supplies/restock-orders/${oid}/approve`, {}),
  resolveDamage: (tid: number) => req<any>('POST', `/supplies/damage-tickets/${tid}/resolve`, {}),
  createDamage: (payload: {
    hotel_id: number
    room_no: string
    asset_category: string
    severity?: string
    description: string
    photos?: string[]
    item_name?: string
    line?: string
    fee?: number
    ai_suggestion?: string
    ai_risk?: string
    ai_tags?: string[]
  }) => req<any>('POST', '/supplies/damage-tickets', payload),
  registerAsset: (
    hotelId: number,
    payload: {
      reason: string
      category: string
      asset_no?: string
      name: string
      spec?: string
      qty?: number
      budget?: string
      room?: string
      supplier?: string
      note?: string
      replace_asset_id?: number
    },
  ) => req<any>('POST', `/assets?hotel_id=${hotelId}`, payload),
  lossAttributionCache: (hotelId: number, period: string) =>
    req<{ hit: boolean; fingerprint: string; data: any }>(
      'GET',
      `/assets/loss-attribution/cache?hotel_id=${hotelId}&period=${period}`,
    ),
  lossAttributionAnalyze: (hotelId: number, period: string, force = false) =>
    req<any>('POST', `/assets/loss-attribution/analyze?hotel_id=${hotelId}`, { period, force }),
  lossAttributionStream: async (
    hotelId: number,
    period: string,
    onEvent: (evt: { type: string; content?: string; data?: any; message?: string }) => void,
    signal?: AbortSignal,
    force = false,
  ) => {
    const res = await fetch(`${BASE}/assets/loss-attribution/analyze/stream?hotel_id=${hotelId}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ period, force }),
      signal,
    })
    if (res.status === 401) {
      localStorage.removeItem('fml_token')
      if (!location.hash.includes('/login')) location.hash = '#/login'
      throw new Error('未登录或令牌失效')
    }
    if (!res.ok) {
      const json: any = await res.json().catch(() => ({}))
      throw new Error(json.detail || '归因分析请求失败')
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
