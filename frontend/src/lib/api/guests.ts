// SPDX-License-Identifier: Apache-2.0
// API: guests
import { req, authHeaders, BASE } from './client'
import { t } from '../i18n'

export const guestsApi = {
  listGuests: (hotelId: number) => req<any[]>('GET', `/guests?hotel_id=${hotelId}`),
  guestArrivalCalendar: (hotelId: number, days = 7) =>
    req<any[]>('GET', `/guests/arrival-calendar?hotel_id=${hotelId}&days=${days}`),
  guest360: (guestId: number) => req<any>('GET', `/guests/${guestId}`),
  guestWecomCareDraft: (guestId: number, material: string) =>
    req<any>('POST', `/guests/${guestId}/wecom-care-draft`, { material }),
  guestWecomCareSend: (guestId: number, content: string) =>
    req<any>('POST', `/guests/${guestId}/wecom-care-send`, { guest_id: guestId, content }),
  guestOneidAudit: (guestId: number) => req<any>('GET', `/guests/${guestId}/oneid-audit`),
  oneidBoard: () => req<any>('GET', '/oneid/board'),
  oneidDuplicatePhones: () => req<any[]>('GET', '/oneid/duplicate-phones'),
  oneidMergeCase: (conflictId?: number) =>
    req<any>('GET', `/oneid/merge-case${conflictId ? `?conflict_id=${conflictId}` : ''}`),
  oneidGuestAssets: (guestId: number) => req<any>('GET', `/oneid/guests/${guestId}/assets`),
  listTags: () => req<any[]>('GET', '/tags'),
  createTag: (body: { name: string; code?: string; category?: string; rule_expr?: string }) =>
    req<any>('POST', '/tags', body),
  mergeOneid: (primaryGuestId: number, secondaryGuestId: number) =>
    req<any>('POST', '/oneid/merge', {
      primary_guest_id: primaryGuestId,
      secondary_guest_id: secondaryGuestId,
    }),
  listOneid: () => req<any[]>('GET', '/oneid'),
  listOneidConflicts: (status = 'pending') =>
    req<any[]>('GET', `/oneid/conflicts?status=${encodeURIComponent(status)}`),
  resolveOneidConflict: (conflictId: number, guestId: number, operator = '前台运营') =>
    req<any>('POST', `/oneid/conflicts/${conflictId}/resolve`, { guest_id: guestId, operator }),
  dismissOneidConflict: (conflictId: number, note = '', operator = '前台运营') =>
    req<any>('POST', `/oneid/conflicts/${conflictId}/dismiss`, { note, operator }),
  listSegments: (hotelId: number) => req<any[]>('GET', `/segments?hotel_id=${hotelId}`),
  createSegment: (
    hotelId: number,
    payload: { name: string; filter_rule?: string; guest_ids?: number[] },
  ) => req<any>('POST', `/segments?hotel_id=${hotelId}`, payload),
  deleteSegment: (hotelId: number, segmentId: number | string) =>
    req<any>('DELETE', `/segments/${segmentId}?hotel_id=${hotelId}`),
  nlQuerySegments: (hotelId: number, query: string) =>
    req<any>('POST', `/segments/nl-query?hotel_id=${hotelId}`, { query }),
  nlQuerySegmentsStream: async (
    hotelId: number,
    query: string,
    onEvent: (evt: { type: string; content?: string; data?: any; message?: string }) => void,
    signal?: AbortSignal,
  ) => {
    const res = await fetch(`${BASE}/segments/nl-query/stream?hotel_id=${hotelId}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ query }),
      signal,
    })
    if (res.status === 401) {
      localStorage.removeItem('fml_token')
      if (!location.hash.includes('/login')) location.hash = '#/login'
      throw new Error('未登录或令牌失效')
    }
    if (!res.ok) {
      const json: any = await res.json().catch(() => ({}))
      throw new Error(json.detail || 'AI 找人请求失败')
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
  listCrmTasks: (hotelId: number, status?: string) =>
    req<any[]>('GET', `/crm/tasks?hotel_id=${hotelId}${status ? `&status=${status}` : ''}`),
  createCrmTasks: (
    hotelId: number,
    payload: {
      task_type?: string
      title?: string
      guest_ids?: number[]
      segment_id?: number
      payload?: Record<string, unknown>
    },
  ) => req<any>('POST', `/crm/tasks?hotel_id=${hotelId}`, payload),
  completeCrmTask: (taskId: number, hotelId: number) =>
    req<any>('PATCH', `/crm/tasks/${taskId}?hotel_id=${hotelId}`, {}),
  updateTag: (
    tagId: number,
    body: { name: string; category?: string; rule_expr?: string; is_active?: boolean },
  ) => req<any>('PUT', `/tags/${tagId}`, body),
  applyTag: (tagId: number, hotelId: number) =>
    req<any>('POST', `/tags/${tagId}/apply?hotel_id=${hotelId}`, {}),
  compareSegments: (hotelId: number, segmentA: string, segmentB: string) =>
    req<any>(
      'GET',
      `/segments/compare?hotel_id=${hotelId}&segment_a=${encodeURIComponent(segmentA)}&segment_b=${encodeURIComponent(segmentB)}`,
    ),
  exportSegment: (segmentId: number, hotelId: number) =>
    req<any>('GET', `/segments/${segmentId}/export?hotel_id=${hotelId}`),
  postGuestEvent: (
    hotelId: number,
    body: { guest_id: number; event_type?: string; note?: string },
  ) => req<any>('POST', `/crm/guest-events?hotel_id=${hotelId}`, body),
}
