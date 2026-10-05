// SPDX-License-Identifier: Apache-2.0
// API: hk
import { req } from './client'

export const hkApi = {
  housekeepingBoard: (hotelId: number, opts?: { range?: string }) => {
    const r = opts?.range ? `&perf_range=${encodeURIComponent(opts.range)}` : ''
    return req<any>('GET', `/housekeeping/board?hotel_id=${hotelId}${r}`)
  },
  housekeepingStaffing: (hotelId: number, opts?: { view?: string; start?: string }) => {
    const view = opts?.view || 'week'
    const start = opts?.start ? `&start=${encodeURIComponent(opts.start)}` : ''
    return req<any>(
      'GET',
      `/housekeeping/staffing?hotel_id=${hotelId}&view=${encodeURIComponent(view)}${start}`,
    )
  },
  hkStaffingAiApply: (
    hotelId: number,
    payload?: {
      proposed?: any[]
      day?: string
      date?: string
      date_from?: string
      date_to?: string
      from?: string
      to?: string
    },
  ) => req<any>('POST', `/housekeeping/staffing/ai-apply?hotel_id=${hotelId}`, payload || {}),
  hkStaffingAiRefresh: (hotelId: number, payload?: { days?: number }) =>
    req<any>('POST', `/housekeeping/staffing/ai-refresh?hotel_id=${hotelId}`, payload || {}),
  hkStaffingAiNarrate: (hotelId: number, payload?: { days?: number }) =>
    req<any>('POST', `/housekeeping/staffing/ai-narrate?hotel_id=${hotelId}`, payload || {}),
  hkAiPlanGenerate: (
    hotelId: number,
    scene: 'cleaning_plan' | 'dispatch_assign' | 'floor_rebalance' | 'staffing_gap',
  ) => req<any>('POST', `/housekeeping/ai-plan/generate?hotel_id=${hotelId}`, { scene }),
  hkAiPlanConfirm: (hotelId: number, plan: Record<string, unknown>) =>
    req<any>('POST', `/housekeeping/ai-plan/confirm?hotel_id=${hotelId}`, { plan }),
  hkStaffingUpsertShift: (
    hotelId: number,
    payload: { user_id: number; date: string; shift: string; view?: string; start?: string },
  ) => req<any>('POST', `/housekeeping/staffing/shift?hotel_id=${hotelId}`, payload),
  hkStaffingCopyWeek: (hotelId: number, payload: { start?: string; view?: string }) =>
    req<any>('POST', `/housekeeping/staffing/copy-week?hotel_id=${hotelId}`, payload),
  hkStaffingSaveTemplate: (hotelId: number, payload: { start?: string; name?: string }) =>
    req<any>('POST', `/housekeeping/staffing/save-template?hotel_id=${hotelId}`, payload),
  hkStaffingAddStaff: (
    hotelId: number,
    payload: { user_id: number; start?: string; view?: string },
  ) => req<any>('POST', `/housekeeping/staffing/add-staff?hotel_id=${hotelId}`, payload),
  hkStaffingDecideRequest: (
    hotelId: number,
    rid: number,
    payload: { approved: boolean; view?: string; start?: string },
  ) =>
    req<any>('POST', `/housekeeping/staffing/requests/${rid}/decide?hotel_id=${hotelId}`, payload),
  housekeepingAiAssistant: (hotelId: number) =>
    req<any>('GET', `/housekeeping/ai-assistant?hotel_id=${hotelId}`),
  hkStart: (
    tid: number,
    payload?: { assignee_id?: number; assignee_name?: string; assignee?: string },
  ) => req<any>('POST', `/housekeeping/${tid}/start`, payload || {}),
  hkAssign: (
    tid: number,
    payload: { assignee_id?: number; assignee_name?: string; assignee?: string },
  ) => req<any>('POST', `/housekeeping/${tid}/assign`, payload),
  hkIgnore: (tid: number, payload?: { reason?: string }) =>
    req<any>('POST', `/housekeeping/${tid}/ignore`, payload || {}),
  hkUrge: (tid: number) => req<any>('POST', `/housekeeping/${tid}/urge`, {}),
  hkBatchDispatch: (payload: {
    task_ids: number[]
    mode: 'single' | 'by_floor' | 'smart'
    assignee_id?: number
    preview?: boolean
    notify?: boolean
  }) => req<any>('POST', '/housekeeping/batch-dispatch', payload),
  hkAiSuggest: (
    hotelId: number,
    payload?: { apply?: boolean; notify?: boolean; snapshot?: Record<string, unknown> },
  ) => req<any>('POST', `/housekeeping/ai-suggest?hotel_id=${hotelId}`, payload || { apply: true }),
  hkCreateTasks: (
    hotelId: number,
    payload: {
      room_id?: number
      task_type?: string
      assignee_id?: number | null
      assignee_name?: string
      priority?: number
      tasks?: Array<{
        room_id: number
        task_type?: string
        assignee_id?: number | null
        assignee_name?: string
        priority?: number
      }>
    },
  ) => req<any>('POST', `/housekeeping/tasks?hotel_id=${hotelId}`, payload),
  hkDispatchStaff: (hotelId: number) =>
    req<any[]>('GET', `/housekeeping/dispatch-staff?hotel_id=${hotelId}`),
  hkInspect: (
    tid: number,
    payload?: { passed?: boolean; fail_reason?: string; fail_items?: string[] },
  ) => req<any>('POST', `/housekeeping/${tid}/inspect`, payload || { passed: true }),
  listHousekeeping: (hotelId: number) => req<any[]>('GET', `/housekeeping?hotel_id=${hotelId}`),
  createServiceRequest: (
    hotelId: number,
    payload: { room_id: number; content: string; assignee_id?: number; priority?: number },
  ) => req<any>('POST', `/service-requests?hotel_id=${hotelId}`, payload),
  listServiceRequests: (hotelId: number) =>
    req<any[]>('GET', `/service-requests?hotel_id=${hotelId}`),
  finishHousekeeping: (tid: number, payload?: { to_status?: string }) =>
    req<any>('POST', `/housekeeping/${tid}/done`, payload || {}),
}
