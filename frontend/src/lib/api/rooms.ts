// SPDX-License-Identifier: Apache-2.0
// API: rooms
import { req } from './client'
import { t } from '../i18n'

export const roomsApi = {
  listRooms: (hotelId: number, onDate?: string) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId) })
    if (onDate) q.set('on_date', onDate)
    return req<any[]>('GET', `/rooms?${q.toString()}`)
  },
  roomsAiRecommend: (payload: { hotel_id: number; need: string; limit?: number }) =>
    req<any>('POST', `/rooms/ai-recommend?hotel_id=${payload.hotel_id}`, payload),
  setRoomStatus: (roomId: number, status: string, reason?: string, extra?: { eta?: string }) =>
    req<any>('POST', `/rooms/${roomId}/status`, { status, reason, ...(extra || {}) }),
  markDueOut: (roomId: number, reason?: string) =>
    req<any>('POST', `/rooms/${roomId}/mark-due-out`, { reason }),
  roomsOversell: (hotelId: number, days = 7) =>
    req<any>('GET', `/rooms/oversell?hotel_id=${hotelId}&days=${days}`),
  roomsStatusHistory: (
    hotelId: number,
    opts?: { from?: string; to?: string; room_no?: string; limit?: number },
  ) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId) })
    if (opts?.from) q.set('from', opts.from)
    if (opts?.to) q.set('to', opts.to)
    if (opts?.room_no) q.set('room_no', opts.room_no)
    if (opts?.limit) q.set('limit', String(opts.limit))
    return req<any>('GET', `/rooms/status-history?${q.toString()}`)
  },
  roomMasterMaintenance: (roomId: number) => req<any>('GET', `/rooms/master/${roomId}/maintenance`),
  roomAiMaintainAdvice: (roomId: number) =>
    req<any>('POST', `/rooms/master/${roomId}/ai-maintain-advice`, {}),
  getRoom: (roomId: number) => req<any>('GET', `/rooms/${roomId}`),
  listRoomTypes: (hotelId: number) => req<any[]>('GET', `/room-types?hotel_id=${hotelId}`),
  createRoomType: (payload: any) => req<any>('POST', '/room-types', payload),
  updateRoomType: (typeId: number, payload: any) =>
    req<any>('PUT', `/room-types/${typeId}`, payload),
  deleteRoomType: (typeId: number) => req<any>('DELETE', `/room-types/${typeId}`),
  listRoomMaster: (hotelId: number, roomTypeId?: number, q?: string) => {
    const params = new URLSearchParams({ hotel_id: String(hotelId) })
    if (roomTypeId) params.set('room_type_id', String(roomTypeId))
    if (q?.trim()) params.set('q', q.trim())
    return req<any[]>('GET', `/rooms/master?${params}`)
  },
  createRoomMaster: (payload: any) => req<any>('POST', '/rooms/master', payload),
  updateRoomMaster: (roomId: number, payload: any) =>
    req<any>('PUT', `/rooms/master/${roomId}`, payload),
  deleteRoomMaster: (roomId: number) => req<any>('DELETE', `/rooms/master/${roomId}`),
  inventoryForecast: (hotelId: number, days = 30, startDate?: string) =>
    req<any>(
      'GET',
      `/inventory/forecast?hotel_id=${hotelId}&days=${days}${startDate ? `&start_date=${encodeURIComponent(startDate)}` : ''}`,
    ),
  inventoryForecastDayDetail: (hotelId: number, bizDate: string) =>
    req<any>(
      'GET',
      `/inventory/forecast/day-detail?hotel_id=${hotelId}&biz_date=${encodeURIComponent(bizDate)}`,
    ),
  inventoryCalendar: (hotelId: number, days = 14) =>
    req<any>('GET', `/inventory/calendar?hotel_id=${hotelId}&days=${days}`),
}
