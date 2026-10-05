// SPDX-License-Identifier: Apache-2.0
// API: pricing
import { req } from './client'
import { t } from '../i18n'

export const pricingApi = {
  listPricing: (hotelId: number) => req<any[]>('GET', `/pricing?hotel_id=${hotelId}`),
  pricingDetail: (pid: number) => req<any>('GET', `/pricing/${pid}`),
  decidePricing: (pid: number, action: 'accept' | 'reject') =>
    req<any>('POST', `/pricing/${pid}/decide`, { action }),
  paConfig: (hotelId: number) => req<any>('GET', `/pricing-assistant/config?hotel_id=${hotelId}`),
  paUpdateConfig: (hotelId: number, payload: any) =>
    req<any>('PUT', `/pricing-assistant/config?hotel_id=${hotelId}`, payload),
  paOverview: (hotelId: number) =>
    req<any>('GET', `/pricing-assistant/overview?hotel_id=${hotelId}`),
  paAlerts: (hotelId: number) => req<any>('GET', `/pricing-assistant/alerts?hotel_id=${hotelId}`),
  paRecommendations: (
    hotelId: number,
    opts?: {
      status?: string
      room_type_id?: number
      channel?: string
      date_from?: string
      date_to?: string
    },
  ) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId) })
    if (opts?.status) q.set('status', opts.status)
    if (opts?.room_type_id) q.set('room_type_id', String(opts.room_type_id))
    if (opts?.channel) q.set('channel', opts.channel)
    if (opts?.date_from) q.set('date_from', opts.date_from)
    if (opts?.date_to) q.set('date_to', opts.date_to)
    return req<any[]>('GET', `/pricing-assistant/recommendations?${q}`)
  },
  paGenerate: (hotelId: number, payload: any = {}) =>
    req<any>('POST', `/pricing-assistant/recommendations/generate?hotel_id=${hotelId}`, payload),
  paRecoDetail: (recoId: string) =>
    req<any>('GET', `/pricing-assistant/recommendations/${encodeURIComponent(recoId)}`),
  paDecide: (
    recoId: string,
    payload: { action: string; staff_no?: string; staff_no2?: string; note?: string },
  ) =>
    req<any>(
      'POST',
      `/pricing-assistant/recommendations/${encodeURIComponent(recoId)}/decide`,
      payload,
    ),
  paBatchDecide: (
    hotelId: number,
    payload: {
      reco_ids: string[]
      action: string
      staff_no: string
      staff_no2?: string
      note?: string
    },
  ) =>
    req<any>(
      'POST',
      `/pricing-assistant/recommendations/batch-decide?hotel_id=${hotelId}`,
      payload,
    ),
  paCalendar: (hotelId: number, days = 30) =>
    req<any>('GET', `/pricing-assistant/calendar?hotel_id=${hotelId}&days=${days}`),
  paTrend: (hotelId: number) => req<any>('GET', `/pricing-assistant/trend?hotel_id=${hotelId}`),
  paSimulate: (hotelId: number, scenario = 'balanced') =>
    req<any>('POST', `/pricing-assistant/simulate?hotel_id=${hotelId}`, { scenario }),
  paCompetitorSets: (hotelId: number) =>
    req<any[]>('GET', `/pricing-assistant/competitor-sets?hotel_id=${hotelId}`),
  paAddCompetitor: (hotelId: number, payload: any) =>
    req<any>('POST', `/pricing-assistant/competitors?hotel_id=${hotelId}`, payload),
  paDeactivateCompetitor: (hotelId: number, compId: string) =>
    req<any>(
      'POST',
      `/pricing-assistant/competitors/${encodeURIComponent(compId)}/deactivate?hotel_id=${hotelId}`,
      {},
    ),
  paRoomMaps: (hotelId: number) =>
    req<any[]>('GET', `/pricing-assistant/room-maps?hotel_id=${hotelId}`),
  paAddRoomMap: (hotelId: number, payload: any) =>
    req<any>('POST', `/pricing-assistant/room-maps?hotel_id=${hotelId}`, payload),
  paCompetitorRate: (hotelId: number, payload: any) =>
    req<any>('POST', `/pricing-assistant/competitor-rates?hotel_id=${hotelId}`, payload),
  paListCompetitorRates: (hotelId: number, stayDate: string, channel?: string) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId), stay_date: stayDate })
    if (channel) q.set('channel', channel)
    return req<any[]>('GET', `/pricing-assistant/competitor-rates?${q}`)
  },
  paImportCompetitorRates: (hotelId: number, text: string) =>
    req<any>('POST', `/pricing-assistant/competitor-rates/import?hotel_id=${hotelId}`, { text }),
  paEvents: (hotelId: number, includeInactive = true) =>
    req<any[]>(
      'GET',
      `/pricing-assistant/events?hotel_id=${hotelId}&include_inactive=${includeInactive ? 'true' : 'false'}`,
    ),
  paCreateEvent: (hotelId: number, payload: any) =>
    req<any>('POST', `/pricing-assistant/events?hotel_id=${hotelId}`, payload),
  paUpdateEvent: (hotelId: number, eventId: string, payload: any) =>
    req<any>(
      'PUT',
      `/pricing-assistant/events/${encodeURIComponent(eventId)}?hotel_id=${hotelId}`,
      payload,
    ),
  paDeactivateEvent: (hotelId: number, eventId: string) =>
    req<any>(
      'POST',
      `/pricing-assistant/events/${encodeURIComponent(eventId)}/deactivate?hotel_id=${hotelId}`,
      {},
    ),
  paDeleteEvent: (hotelId: number, eventId: string) =>
    req<any>(
      'DELETE',
      `/pricing-assistant/events/${encodeURIComponent(eventId)}?hotel_id=${hotelId}`,
    ),
  paDataSources: (hotelId: number) =>
    req<any[]>('GET', `/pricing-assistant/data-sources?hotel_id=${hotelId}`),
  paMapCandidates: (hotelId: number) =>
    req<any[]>('GET', `/pricing-assistant/map-candidates?hotel_id=${hotelId}`),
  paAmapStatus: () => req<any>('GET', `/pricing-assistant/map/status`),
  paAmapGeocode: (hotelId: number, payload: any) =>
    req<any>('POST', `/pricing-assistant/map/geocode?hotel_id=${hotelId}`, payload),
  paAmapNearby: (hotelId: number, payload: any) =>
    req<any>('POST', `/pricing-assistant/map/nearby?hotel_id=${hotelId}`, payload),
  paNarrateExplain: (recoId: string) =>
    req<any>(
      'POST',
      `/pricing-assistant/recommendations/${encodeURIComponent(recoId)}/narrate`,
      {},
    ),
}
