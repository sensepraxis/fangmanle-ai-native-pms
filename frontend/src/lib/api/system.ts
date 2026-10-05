// SPDX-License-Identifier: Apache-2.0
// API: system
import { req } from './client'

export const systemApi = {
  branding: () => req<any>('GET', '/system/branding'),
  privateChannelGet: () => req<any>('GET', '/system/private-channel'),
  privateChannelSave: (payload: Record<string, unknown>) =>
    req<any>('PUT', '/system/private-channel', payload),
  listHotels: () => req<any[]>('GET', '/hotel'),
  listChannels: () => req<any[]>('GET', '/channels'),
  otaCommissionGet: (hotelId: number) =>
    req<any>('GET', `/system/ota-commission?hotel_id=${hotelId}`),
  otaCommissionSave: (hotelId: number, payload: any) =>
    req<any>('PUT', `/system/ota-commission?hotel_id=${hotelId}`, payload),
  otaCommissionChannelUpsert: (hotelId: number, payload: any) =>
    req<any>('POST', `/system/ota-commission/channels?hotel_id=${hotelId}`, payload),
  otaCommissionChannelEnabled: (hotelId: number, code: string, enabled: boolean) =>
    req<any>(
      'PATCH',
      `/system/ota-commission/channels/${encodeURIComponent(code)}/enabled?hotel_id=${hotelId}`,
      {
        is_enabled: enabled,
      },
    ),
  otaCommissionReset: (hotelId: number) =>
    req<any>('POST', `/system/ota-commission/reset?hotel_id=${hotelId}`, {}),
  otaCommissionOverrides: (hotelId: number) =>
    req<any[]>('GET', `/system/ota-commission/overrides?hotel_id=${hotelId}`),
  otaCommissionOverrideSave: (hotelId: number, payload: any) =>
    req<any>('POST', `/system/ota-commission/overrides?hotel_id=${hotelId}`, payload),
  otaCommissionOverrideDelete: (hotelId: number, id: number) =>
    req<any>('DELETE', `/system/ota-commission/overrides/${id}?hotel_id=${hotelId}`),
  otaCommissionPreview: (payload: any) =>
    req<any>('POST', `/system/ota-commission/preview`, payload),
  complianceStatus: (hotelId: number) => req<any>('GET', `/compliance/status?hotel_id=${hotelId}`),
  complianceAudits: (hotelId: number, limit = 50) =>
    req<any>('GET', `/compliance/id-doc-audits?hotel_id=${hotelId}&limit=${limit}`),
  compliancePurgeIdDocs: (retainYears?: number) =>
    req<any>('POST', '/compliance/purge-expired-id-docs', {
      retain_years: retainYears,
    }),
  otaSyncOrder: (payload: any) => req<any>('POST', '/orders/ota/sync', payload),
  llmProviders: () => req<any[]>('GET', '/llm/providers'),
  llmConfig: () => req<any>('GET', '/llm/config'),
  mapConfig: () => req<any>('GET', '/system/map-config'),
  mapConfigSave: (payload: Record<string, unknown>) =>
    req<any>('PUT', '/system/map-config', payload),
  mapConfigTest: (payload: Record<string, unknown>) =>
    req<any>('POST', '/system/map-config/test', payload),
  llmChat: (messages: { role: string; content: string }[], systemHint?: string) =>
    req<any>('POST', '/llm/chat', { messages, system_hint: systemHint }),
  login: (payload: { username: string; password: string }) =>
    req<any>('POST', '/auth/login', payload),
  me: () => req<any>('GET', '/auth/me'),
  rbacRoles: () => req<any[]>('GET', '/rbac/roles'),
  rbacCreateRole: (payload: Record<string, unknown>) => req<any>('POST', '/rbac/roles', payload),
  rbacUpdateRole: (roleCode: string, payload: Record<string, unknown>) =>
    req<any>('PUT', `/rbac/roles/${encodeURIComponent(roleCode)}`, payload),
  rbacDeleteRole: (roleCode: string) =>
    req<any>('DELETE', `/rbac/roles/${encodeURIComponent(roleCode)}`),
  rbacPermissions: () => req<any[]>('GET', '/rbac/permissions'),
  rbacRolePermissions: (roleCode: string) =>
    req<any>('GET', `/rbac/roles/${encodeURIComponent(roleCode)}/permissions`),
  rbacSaveRolePermissions: (roleCode: string, codes: string[]) =>
    req<any>('PUT', `/rbac/roles/${encodeURIComponent(roleCode)}/permissions`, { codes }),
  rbacResetRoleDefaults: (roleCode: string) =>
    req<any>('POST', `/rbac/roles/${encodeURIComponent(roleCode)}/reset-defaults`, {}),
  rbacUsers: () => req<any[]>('GET', '/rbac/users'),
  rbacCreateUser: (payload: Record<string, unknown>) => req<any>('POST', '/rbac/users', payload),
  rbacUpdateUser: (userId: number, payload: Record<string, unknown>) =>
    req<any>('PUT', `/rbac/users/${userId}`, payload),
  wecomSidebarCareSent: (externalUserid: string, content: string, senderUserid?: string) =>
    req<any>('POST', '/wecom/sidebar/care-sent', {
      external_userid: externalUserid,
      content,
      sender_userid: senderUserid,
    }),
  listAudits: (hotelId: number) => req<any[]>('GET', `/night-audit/list?hotel_id=${hotelId}`),
  auditDetail: (hotelId: number, bizDate: string) =>
    req<any>('GET', `/night-audit/${hotelId}/${bizDate}`),
  runAudit: (payload: { hotel_id: number; biz_date: string }) =>
    req<any>('POST', '/night-audit', payload),
  listAuditExceptions: (hotelId: number, bizDate?: string) =>
    req<any[]>(
      'GET',
      `/finance/audit-exceptions?hotel_id=${hotelId}${bizDate ? `&biz_date=${bizDate}` : ''}`,
    ),
  fixAuditException: (id: number) => req<any>('POST', `/finance/audit-exceptions/${id}/fix`, {}),
  listRiskAlerts: (hotelId: number) => req<any[]>('GET', `/risk-alerts?hotel_id=${hotelId}`),
  riskBoard: (hotelId: number) => req<any>('GET', `/risk/board?hotel_id=${hotelId}`),
  listAiCommands: (hotelId: number) => req<any[]>('GET', `/ai-commands?hotel_id=${hotelId}`),
  saveLlmConfig: (payload: Record<string, unknown>) => req<any>('PUT', '/llm/config', payload),
  testLlmConfig: () => req<any>('POST', '/llm/config/test', {}),
  wecomConfig: () => req<any>('GET', '/wecom/config'),
  saveWecomConfig: (payload: Record<string, unknown>) => req<any>('PUT', '/wecom/config', payload),
  testWecomConfig: () => req<any>('POST', '/wecom/config/test', {}),
  syncWecomContacts: (hotelId: number) =>
    req<any>('POST', `/wecom/sync-contacts?hotel_id=${hotelId}`, {}),
  simulateWecomScan: (hotelId: number, externalUserid?: string) =>
    req<any>('POST', `/wecom/simulate-scan?hotel_id=${hotelId}`, {
      external_userid: externalUserid || null,
    }),
  listWecomBindTickets: (hotelId: number) =>
    req<any[]>('GET', `/wecom/bind-tickets?hotel_id=${hotelId}`),
  wecomMsgResult: (hotelId: number, msgid?: string) =>
    req<any>(
      'GET',
      `/wecom/msg-result?hotel_id=${hotelId}${msgid ? `&msgid=${encodeURIComponent(msgid)}` : ''}`,
    ),
  sendWecomMessage: (hotelId: number, guestId: number, content: string) =>
    req<any>('POST', `/wecom/send?hotel_id=${hotelId}`, { guest_id: guestId, content }),
  listWecomTasks: (hotelId: number, guestId?: number) =>
    req<any[]>('GET', `/wecom/tasks?hotel_id=${hotelId}${guestId ? `&guest_id=${guestId}` : ''}`),
  demo: (entity: string) => req<any[]>('GET', `/demo/${entity}`),
}
