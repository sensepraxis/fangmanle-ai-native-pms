// SPDX-License-Identifier: Apache-2.0
// API: orders
import { normalizeOrdersPage } from '../orderFlow'
import { req } from './client'
import { t } from '../i18n'

export const ordersApi = {
  listOrders: (
    hotelId: number,
    status?: string,
    opts?: { channelId?: number; source?: string },
  ) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId) })
    if (status) q.set('status', status)
    if (opts?.channelId) q.set('channel_id', String(opts.channelId))
    if (opts?.source) q.set('source', opts.source)
    return req<any[]>('GET', `/orders?${q.toString()}`)
  },
  listOrdersPage: async (
    hotelId: number,
    opts: {
      view?: string
      source?: string
      onDate?: string
      page?: number
      pageSize?: number
      channelId?: number
      roomTypeId?: number
      status?: string
      paymentStatus?: string
      combo?: Partial<{
        order_no: string
        external_order_no: string
        reception_no: string
        room_no: string
        guest_name: string
        phone: string
        note: string
      }>
      q?: string
    } = {},
  ) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId) })
    q.set('page', String(opts.page ?? 1))
    q.set('page_size', String(opts.pageSize ?? 20))
    if (opts.view) q.set('view', opts.view)
    if (opts.source && opts.source !== 'all') q.set('source', opts.source)
    if (opts.onDate) q.set('on_date', opts.onDate)
    if (opts.channelId) q.set('channel_id', String(opts.channelId))
    if (opts.roomTypeId) q.set('room_type_id', String(opts.roomTypeId))
    if (opts.status) q.set('status', opts.status)
    if (opts.paymentStatus) q.set('payment_status', opts.paymentStatus)
    if (opts.combo) {
      const c = opts.combo
      if (c.order_no?.trim()) q.set('order_no', c.order_no.trim())
      if (c.external_order_no?.trim()) q.set('external_order_no', c.external_order_no.trim())
      if (c.reception_no?.trim()) q.set('reception_no', c.reception_no.trim())
      if (c.room_no?.trim()) q.set('room_no', c.room_no.trim())
      if (c.guest_name?.trim()) q.set('guest_name', c.guest_name.trim())
      if (c.phone?.trim()) q.set('phone', c.phone.trim())
      if (c.note?.trim()) q.set('note', c.note.trim())
    }
    if (opts.q?.trim()) q.set('q', opts.q.trim())
    const raw = await req<any>('GET', `/orders?${q.toString()}`)
    return normalizeOrdersPage(raw, {
      view: opts.view,
      source: opts.source,
      onDate: opts.onDate,
      page: opts.page,
      pageSize: opts.pageSize,
    })
  },
  ordersBoard: (hotelId: number) => req<any>('GET', `/orders/board?hotel_id=${hotelId}`),
  ordersSummary: (hotelId: number, onDate?: string) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId) })
    if (onDate) q.set('on_date', onDate)
    return req<any>('GET', `/orders/summary?${q.toString()}`)
  },
  ordersMonitor: (hotelId: number, range: '24h' | '7d' | '14d' = '7d') =>
    req<any>('GET', `/orders/monitor?hotel_id=${hotelId}&range=${range}`),
  ordersAiRisks: (hotelId: number) => req<any>('GET', `/orders/ai-risks?hotel_id=${hotelId}`),
  ordersChannelInsight: (hotelId: number, days = 30, roomTypeId?: number | null) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId), days: String(days) })
    if (roomTypeId) q.set('room_type_id', String(roomTypeId))
    return req<any>('GET', `/orders/channel-insight?${q.toString()}`)
  },
  ordersChannelInsightAi: (hotelId: number, days = 30, roomTypeId?: number | null) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId), days: String(days) })
    if (roomTypeId) q.set('room_type_id', String(roomTypeId))
    return req<any>('POST', `/orders/channel-insight/ai?${q.toString()}`)
  },
  ordersAttribution: (hotelId: number, days = 7) =>
    req<any>('GET', `/orders/attribution?hotel_id=${hotelId}&days=${days}`),
  ordersAttributionAi: (hotelId: number, days = 7) =>
    req<any>('POST', `/orders/attribution/ai?hotel_id=${hotelId}&days=${days}`),
  createOrder: (payload: any) => req<any>('POST', '/orders', payload),
  walkInCheckin: (payload: any) => req<any>('POST', '/orders/walk-in', payload),
  assignRoom: (orderId: number, roomId: number) =>
    req<any>('POST', `/orders/${orderId}/assign-room`, { room_id: roomId }),
  changeRoom: (orderId: number, roomId: number, reason?: string) =>
    req<any>('POST', `/orders/${orderId}/change-room`, { room_id: roomId, reason }),
  extendStay: (orderId: number, extraNights: number, dailyRate?: number) =>
    req<any>('POST', `/orders/${orderId}/extend`, {
      extra_nights: extraNights,
      daily_rate: dailyRate,
    }),
  folioCharge: (
    orderId: number,
    payload: { amount: number; description?: string; entry_type?: string },
  ) => req<any>('POST', `/orders/${orderId}/folio/charge`, payload),
  folioPay: (
    orderId: number,
    payload: {
      amount: number
      method?: string
      pos_slip_no?: string
      settle_type?: string
      note?: string
    },
  ) => req<any>('POST', `/orders/${orderId}/folio/pay`, payload),
  orderRc: (orderId: number, reveal = false) =>
    req<any>('GET', `/orders/${orderId}/rc?reveal=${reveal ? '1' : '0'}`),
  voucherLookup: (payload: { hotel_id: number; voucher_code: string }) =>
    req<any>('POST', '/orders/voucher/lookup', payload),
  voucherVerify: (payload: any) => req<any>('POST', '/orders/voucher/verify', payload),
  getOrder: (orderId: number) => req<any>('GET', `/orders/${orderId}`),
  cancelOrder: (orderId: number, reason?: string) =>
    req<any>('POST', `/orders/${orderId}/cancel`, reason ? { reason } : {}),
  revealCheckinIdDoc: (checkinId: number, payload: { reason?: string; password: string }) =>
    req<any>('POST', `/checkins/${checkinId}/reveal-id-doc`, payload),
  addRoommate: (orderId: number, payload: any) =>
    req<any>('POST', `/orders/${orderId}/roommates`, payload),
  markNoShow: (orderId: number, reason?: string) =>
    req<any>('POST', `/orders/${orderId}/no-show`, reason ? { reason } : {}),
  longstayMonthlyRent: (hotelId: number, asOf?: string) =>
    req<any>('POST', '/longstay/monthly-rent', { hotel_id: hotelId, as_of: asOf }),
  createGroupOrder: (payload: any) => req<any>('POST', '/orders/group', payload),
  assignGroupLine: (orderId: number, lineId: number, roomId: number) =>
    req<any>('POST', `/orders/${orderId}/group-lines/${lineId}/assign`, { room_id: roomId }),
  checkinGroupLine: (orderId: number, lineId: number, payload: any = {}) =>
    req<any>('POST', `/orders/${orderId}/group-lines/${lineId}/checkin`, payload),
  checkin: (orderId: number, roomId?: number) =>
    req<any>('POST', `/orders/${orderId}/checkin`, roomId ? { room_id: roomId } : {}),
  checkout: (
    orderId: number,
    opts?: { payment_mode?: string; method?: string; pos_slip_no?: string },
  ) => req<any>('POST', `/orders/${orderId}/checkout`, opts || {}),
}
