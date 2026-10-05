// SPDX-License-Identifier: Apache-2.0
// API: finance
import { req, authHeaders, BASE } from './client'
import { t } from '../i18n'

export const financeApi = {
  depositsBoard: (
    hotelId: number,
    opts?: { status?: string; form?: string; q?: string; bucket?: string },
  ) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId) })
    if (opts?.status) q.set('status', opts.status)
    if (opts?.form) q.set('form', opts.form)
    if (opts?.q) q.set('q', opts.q)
    if (opts?.bucket) q.set('bucket', opts.bucket)
    return req<any>('GET', `/deposits/board?${q.toString()}`)
  },
  depositsOrders: (hotelId: number) => req<any>('GET', `/deposits/orders?hotel_id=${hotelId}`),
  depositsLookupByPhone: (hotelId: number, phone: string) =>
    req<any>(
      'GET',
      `/deposits/lookup-by-phone?hotel_id=${hotelId}&phone=${encodeURIComponent(phone)}`,
    ),
  depositsLookupByRoom: (hotelId: number, roomNo: string) =>
    req<any>(
      'GET',
      `/deposits/lookup-by-room?hotel_id=${hotelId}&room_no=${encodeURIComponent(roomNo)}`,
    ),
  depositsLookupByGuest: (hotelId: number, guestId: number) =>
    req<any>('GET', `/deposits/lookup-by-guest?hotel_id=${hotelId}&guest_id=${guestId}`),
  depositDetail: (depositId: string, hotelId: number) =>
    req<any>('GET', `/deposits/${encodeURIComponent(depositId)}?hotel_id=${hotelId}`),
  depositPreview: (payload: { customer_id?: string; guest_id?: number; nights?: number }) =>
    req<any>('POST', '/deposits/preview-amount', payload),
  depositCollect: (payload: Record<string, unknown>) => req<any>('POST', '/deposits', payload),
  depositCapture: (depositId: string, payload: Record<string, unknown>) =>
    req<any>('POST', `/deposits/${encodeURIComponent(depositId)}/capture`, payload),
  depositRelease: (depositId: string, payload: Record<string, unknown>) =>
    req<any>('POST', `/deposits/${encodeURIComponent(depositId)}/release`, payload),
  depositReauthorize: (depositId: string, payload?: Record<string, unknown>) =>
    req<any>('POST', `/deposits/${encodeURIComponent(depositId)}/reauthorize`, payload || {}),
  depositDispute: (depositId: string, payload?: Record<string, unknown>) =>
    req<any>('POST', `/deposits/${encodeURIComponent(depositId)}/dispute`, payload || {}),
  refundAdjustBoard: (hotelId: number) =>
    req<any>('GET', `/refund-adjust/board?hotel_id=${hotelId}`),
  refundAdjustThreshold: (payload: { refund_threshold_yuan: number }) =>
    req<any>('PUT', '/refund-adjust/threshold', payload),
  refundAdjustLookupOrder: (hotelId: number, q: string) =>
    req<any>('GET', `/refund-adjust/lookup-order?hotel_id=${hotelId}&q=${encodeURIComponent(q)}`),
  refundAdjustLookupByPhone: (hotelId: number, phone: string) =>
    req<any>(
      'GET',
      `/refund-adjust/lookup-by-phone?hotel_id=${hotelId}&phone=${encodeURIComponent(phone)}`,
    ),
  refundAdjustOrderDetail: (hotelId: number, orderId: number) =>
    req<any>('GET', `/refund-adjust/order-detail?hotel_id=${hotelId}&order_id=${orderId}`),
  refundAdjustEntries: (hotelId: number) =>
    req<any>('GET', `/refund-adjust/adjust-entries?hotel_id=${hotelId}`),
  refundAdjustReverseTargets: (hotelId: number) =>
    req<any>('GET', `/refund-adjust/reverse-targets?hotel_id=${hotelId}`),
  refundAdjustSubmitRefund: (payload: Record<string, unknown>) =>
    req<any>('POST', '/refund-adjust/refund', payload),
  refundAdjustSubmitAdjust: (payload: Record<string, unknown>) =>
    req<any>('POST', '/refund-adjust/adjust', payload),
  refundAdjustSubmitReverse: (payload: Record<string, unknown>) =>
    req<any>('POST', '/refund-adjust/reverse', payload),
  refundAdjustDualAuth: (ticketId: number, role: 'mgr' | 'fin') =>
    req<any>('POST', `/refund-adjust/tickets/${ticketId}/dual-auth`, { role }),
  financeFlowSummary: (hotelId: number) =>
    req<any>('GET', `/finance/flow-summary?hotel_id=${hotelId}`),
  reconBatchDetail: (batchId: number) => req<any>('GET', `/finance/recon-batches/${batchId}`),
  reconBatchAiExplain: (batchId: number) =>
    req<any>('POST', `/finance/recon-batches/${batchId}/ai-explain`, {}),
  arApWorkspace: (hotelId: number) =>
    req<any>('GET', `/finance/ar-ap/workspace?hotel_id=${hotelId}`),
  arApCheckCredit: (hotelId: number, corpId: number, amount: number) =>
    req<any>('POST', `/finance/ar-ap/check-credit?hotel_id=${hotelId}`, {
      corp_id: corpId,
      amount,
    }),
  arApCharge: (hotelId: number, payload: { corp_id: number; amount: number; note?: string }) =>
    req<any>('POST', `/finance/ar-ap/charge?hotel_id=${hotelId}`, payload),
  arApReceipt: (
    hotelId: number,
    arId: number,
    payload: { amount: number; channel?: string; ref_no?: string },
  ) => req<any>('POST', `/finance/ar-ap/ar/${arId}/receipt?hotel_id=${hotelId}`, payload),
  arApPayment: (
    hotelId: number,
    apId: number,
    payload: { amount: number; channel?: string; ref_no?: string },
  ) => req<any>('POST', `/finance/ar-ap/ap/${apId}/payment?hotel_id=${hotelId}`, payload),
  arApWriteOff: (hotelId: number, arId: number, payload: { reason: string; approver: string }) =>
    req<any>('POST', `/finance/ar-ap/ar/${arId}/write-off?hotel_id=${hotelId}`, payload),
  arApDismissTodo: (hotelId: number, todoId: string, note?: string) =>
    req<any>(
      'POST',
      `/finance/ar-ap/todos/${encodeURIComponent(todoId)}/dismiss?hotel_id=${hotelId}`,
      {
        note: note || '',
      },
    ),
  financeReportsCenter: (
    hotelId: number,
    opts?: { period?: string; start?: string; end?: string; compare?: string },
  ) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId) })
    if (opts?.period) q.set('period', opts.period)
    if (opts?.start) q.set('start', opts.start)
    if (opts?.end) q.set('end', opts.end)
    if (opts?.compare) q.set('compare', opts.compare)
    return req<any>('GET', `/finance/reports/center?${q.toString()}`)
  },
  financeReportDetail: (
    hotelId: number,
    code: string,
    opts?: { period?: string; start?: string; end?: string; compare?: string },
  ) => {
    const q = new URLSearchParams({ hotel_id: String(hotelId) })
    if (opts?.period) q.set('period', opts.period)
    if (opts?.start) q.set('start', opts.start)
    if (opts?.end) q.set('end', opts.end)
    if (opts?.compare) q.set('compare', opts.compare)
    return req<any>('GET', `/finance/reports/${encodeURIComponent(code)}?${q.toString()}`)
  },
  financeReportExports: (hotelId: number, code: string) =>
    req<any[]>('GET', `/finance/reports/${encodeURIComponent(code)}/exports?hotel_id=${hotelId}`),
  financeReportExport: (
    hotelId: number,
    code: string,
    payload: { format: string; period?: string; start?: string; end?: string; compare?: string },
  ) =>
    req<any>(
      'POST',
      `/finance/reports/${encodeURIComponent(code)}/export?hotel_id=${hotelId}`,
      payload,
    ),
  financeReportExportDownloadUrl: (hotelId: number, exportId: number) =>
    `${BASE}/finance/reports/exports/${exportId}/download?hotel_id=${hotelId}`,
  financeReportAiInterpret: (
    hotelId: number,
    code: string,
    payload: { period?: string; start?: string; end?: string; compare?: string },
  ) =>
    req<any>(
      'POST',
      `/finance/reports/${encodeURIComponent(code)}/ai-interpret?hotel_id=${hotelId}`,
      payload,
    ),
  financeReportAiInterpretGet: (hotelId: number, interpretationId: number) =>
    req<any>('GET', `/finance/reports/ai-interpret/${interpretationId}?hotel_id=${hotelId}`),
  financeReportAiActionDecide: (
    hotelId: number,
    interpretationId: number,
    actionIndex: number,
    payload: { decision: 'confirmed' | 'dismissed'; remark?: string },
  ) =>
    req<any>(
      'POST',
      `/finance/reports/ai-interpret/${interpretationId}/actions/${actionIndex}/decide?hotel_id=${hotelId}`,
      payload,
    ),
  financeBoard: (hotelId: number) => req<any>('GET', `/finance/board?hotel_id=${hotelId}`),
  revenueForecast: (hotelId: number, growthFactor = 1) =>
    req<any>('GET', `/overview/revenue-forecast?hotel_id=${hotelId}&growth_factor=${growthFactor}`),
  revenueForecastAiAdvice: (hotelId: number, growthFactor = 1) =>
    req<any>('POST', `/overview/revenue-forecast/ai-advice?hotel_id=${hotelId}`, {
      growth_factor: growthFactor,
    }),
  revenueForecastAiAdviceStream: async (
    hotelId: number,
    onEvent: (evt: { type: string; content?: string; data?: any; message?: string }) => void,
    growthFactor = 1,
    signal?: AbortSignal,
  ) => {
    const res = await fetch(
      `${BASE}/overview/revenue-forecast/ai-advice/stream?hotel_id=${hotelId}`,
      {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ growth_factor: growthFactor }),
        signal,
      },
    )
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
  shiftHandoverWorkspace: (hotelId: number) =>
    req<any>('GET', `/finance/shift-handover/workspace?hotel_id=${hotelId}`),
  shiftHandoverFloatCount: (
    hotelId: number,
    handoverId: number,
    payload: Record<string, unknown>,
  ) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/float-count?hotel_id=${hotelId}`,
      payload,
    ),
  shiftHandoverAssetCount: (
    hotelId: number,
    handoverId: number,
    payload: Record<string, unknown>,
  ) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/asset-count?hotel_id=${hotelId}`,
      payload,
    ),
  shiftHandoverSign: (hotelId: number, handoverId: number, payload: Record<string, unknown>) =>
    req<any>('POST', `/finance/shift-handover/${handoverId}/sign?hotel_id=${hotelId}`, payload),
  shiftHandoverComplete: (hotelId: number, handoverId: number) =>
    req<any>('POST', `/finance/shift-handover/${handoverId}/complete?hotel_id=${hotelId}`, {}),
  shiftHandoverEscalate: (hotelId: number, handoverId: number, taskIndex: number) =>
    req<any>('POST', `/finance/shift-handover/${handoverId}/escalate?hotel_id=${hotelId}`, {
      task_index: taskIndex,
    }),
  shiftTakeoverWorkspace: (hotelId: number) =>
    req<any>('GET', `/finance/shift-handover/takeover/workspace?hotel_id=${hotelId}`),
  shiftTakeoverRevenueAck: (
    hotelId: number,
    handoverId: number,
    payload: Record<string, unknown>,
  ) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/takeover/revenue-ack?hotel_id=${hotelId}`,
      payload,
    ),
  shiftTakeoverDepositAck: (
    hotelId: number,
    handoverId: number,
    payload: Record<string, unknown>,
  ) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/takeover/deposit-ack?hotel_id=${hotelId}`,
      payload,
    ),
  shiftTakeoverFloatRecount: (
    hotelId: number,
    handoverId: number,
    payload: Record<string, unknown>,
  ) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/takeover/float-recount?hotel_id=${hotelId}`,
      payload,
    ),
  shiftTakeoverAssetRecount: (
    hotelId: number,
    handoverId: number,
    payload: Record<string, unknown>,
  ) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/takeover/asset-recount?hotel_id=${hotelId}`,
      payload,
    ),
  shiftTakeoverGuestAck: (hotelId: number, handoverId: number, payload: Record<string, unknown>) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/takeover/guest-ack?hotel_id=${hotelId}`,
      payload,
    ),
  shiftTakeoverTaskClaim: (hotelId: number, handoverId: number, payload: Record<string, unknown>) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/takeover/task-claim?hotel_id=${hotelId}`,
      payload,
    ),
  shiftTakeoverCarryoverAck: (
    hotelId: number,
    handoverId: number,
    payload: Record<string, unknown>,
  ) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/takeover/carryover-ack?hotel_id=${hotelId}`,
      payload,
    ),
  shiftTakeoverMattersConfirm: (hotelId: number, handoverId: number) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/takeover/matters-confirm?hotel_id=${hotelId}`,
      {},
    ),
  shiftTakeoverReportDiff: (
    hotelId: number,
    handoverId: number,
    payload: Record<string, unknown>,
  ) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/takeover/report-diff?hotel_id=${hotelId}`,
      payload,
    ),
  shiftTakeoverSign: (hotelId: number, handoverId: number, payload: Record<string, unknown>) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/takeover/sign?hotel_id=${hotelId}`,
      payload,
    ),
  shiftTakeoverComplete: (hotelId: number, handoverId: number) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/takeover/complete?hotel_id=${hotelId}`,
      {},
    ),
  shiftAiDraftGenerate: (hotelId: number, handoverId: number, scene: 'handover' | 'takeover') =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/ai-draft/generate?hotel_id=${hotelId}`,
      { scene },
    ),
  shiftAiDraftConfirm: (hotelId: number, handoverId: number, payload: Record<string, unknown>) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/ai-draft/confirm?hotel_id=${hotelId}`,
      payload,
    ),
  shiftAiDraftReject: (hotelId: number, handoverId: number, payload: Record<string, unknown>) =>
    req<any>(
      'POST',
      `/finance/shift-handover/${handoverId}/ai-draft/reject?hotel_id=${hotelId}`,
      payload,
    ),
  financeParamsFloatCarry: (hotelId: number) =>
    req<any>('GET', `/system/finance-params/float-carry?hotel_id=${hotelId}`),
  financeParamsFloatCarryRequest: (hotelId: number, payload: Record<string, unknown>) =>
    req<any>('POST', `/system/finance-params/float-carry/request?hotel_id=${hotelId}`, payload),
  financeParamsFloatCarryApproveFinance: (
    hotelId: number,
    requestId: number,
    payload: Record<string, unknown> = {},
  ) =>
    req<any>(
      'POST',
      `/system/finance-params/float-carry/${requestId}/approve-finance?hotel_id=${hotelId}`,
      payload,
    ),
  financeParamsFloatCarryApproveManager: (
    hotelId: number,
    requestId: number,
    payload: Record<string, unknown> = {},
  ) =>
    req<any>(
      'POST',
      `/system/finance-params/float-carry/${requestId}/approve-manager?hotel_id=${hotelId}`,
      payload,
    ),
  financeParamsFloatCarryReject: (
    hotelId: number,
    requestId: number,
    payload: Record<string, unknown>,
  ) =>
    req<any>(
      'POST',
      `/system/finance-params/float-carry/${requestId}/reject?hotel_id=${hotelId}`,
      payload,
    ),
  financeParamsTax: (hotelId: number) =>
    req<any>('GET', `/system/finance-params/tax?hotel_id=${hotelId}`),
  financeParamsTaxUpdate: (hotelId: number, payload: Record<string, unknown>) =>
    req<any>('POST', `/system/finance-params/tax?hotel_id=${hotelId}`, payload),
  financeParamsTermUpdate: (hotelId: number, termId: number, payload: Record<string, unknown>) =>
    req<any>('POST', `/system/finance-params/tax/terms/${termId}?hotel_id=${hotelId}`, payload),
  financeParamsAcquiring: (hotelId: number) =>
    req<any>('GET', `/system/finance-params/acquiring?hotel_id=${hotelId}`),
  financeParamsAcquiringRate: (
    hotelId: number,
    channelId: number,
    payload: Record<string, unknown>,
  ) =>
    req<any>(
      'POST',
      `/system/finance-params/acquiring/${channelId}/rate?hotel_id=${hotelId}`,
      payload,
    ),
  financeParamsAcquiringToggle: (hotelId: number, channelId: number, enabled: boolean) =>
    req<any>('POST', `/system/finance-params/acquiring/${channelId}/toggle?hotel_id=${hotelId}`, {
      enabled,
    }),
  financeParamsCredit: (hotelId: number) =>
    req<any>('GET', `/system/finance-params/credit?hotel_id=${hotelId}`),
  financeParamsCreditCreate: (hotelId: number, payload: Record<string, unknown>) =>
    req<any>('POST', `/system/finance-params/credit?hotel_id=${hotelId}`, payload),
  financeParamsCreditLimit: (
    hotelId: number,
    customerId: number,
    payload: Record<string, unknown>,
  ) =>
    req<any>(
      'POST',
      `/system/finance-params/credit/${customerId}/limit?hotel_id=${hotelId}`,
      payload,
    ),
  financeParamsBadDebt: (hotelId: number, rateId: number, payload: Record<string, unknown>) =>
    req<any>(
      'POST',
      `/system/finance-params/credit/bad-debt/${rateId}?hotel_id=${hotelId}`,
      payload,
    ),
  financeAiPlanGenerate: (
    hotelId: number,
    scene: 'deposit' | 'refund' | 'night_audit' | 'recon' | 'invoice',
  ) => req<any>('POST', `/finance/ai-plan/generate?hotel_id=${hotelId}`, { scene }),
  financeAiPlanConfirm: (hotelId: number, plan: Record<string, unknown>) =>
    req<any>('POST', `/finance/ai-plan/confirm?hotel_id=${hotelId}`, { plan }),
  paymentsShift: (hotelId: number) =>
    req<any>('GET', `/finance/payments-shift?hotel_id=${hotelId}`),
  agreementsBoard: (hotelId: number) => req<any>('GET', `/agreements/board?hotel_id=${hotelId}`),
  arBoard: (hotelId: number) => req<any>('GET', `/ar/board?hotel_id=${hotelId}`),
  arSettle: (ledgerId: number, payload: { amount: number; ref_no?: string; note?: string }) =>
    req<any>('POST', `/ar/${ledgerId}/settle`, payload),
  listReconBatches: (hotelId: number) =>
    req<any[]>('GET', `/finance/recon-batches?hotel_id=${hotelId}`),
  syncReconBatches: (hotelId: number, days = 14) =>
    req<any>('POST', `/finance/recon-batches/sync?hotel_id=${hotelId}&days=${days}`, {}),
  listTaxFilings: (hotelId: number) =>
    req<any[]>('GET', `/finance/tax-filings?hotel_id=${hotelId}`),
  invoiceWorkspace: (hotelId: number) =>
    req<any>('GET', `/finance/invoices/workspace?hotel_id=${hotelId}`),
  issueInvoice: (hotelId: number, orderId: number) =>
    req<any>('POST', `/finance/invoices/issue?hotel_id=${hotelId}`, { order_id: orderId }),
  redFlushInvoice: (hotelId: number, invoiceId: number, reason: string) =>
    req<any>('POST', `/finance/invoices/${invoiceId}/red-flush?hotel_id=${hotelId}`, { reason }),
  listProfitInsights: (hotelId: number) =>
    req<any[]>('GET', `/finance/profit-insights?hotel_id=${hotelId}`),
  listFinanceReports: (hotelId: number) =>
    req<any[]>('GET', `/finance/reports?hotel_id=${hotelId}`),
  listLedger: (hotelId: number, limit = 40) =>
    req<any>('GET', `/finance/ledger?hotel_id=${hotelId}&limit=${limit}`),
  listRevenueAnomalies: (hotelId: number) =>
    req<any[]>('GET', `/finance/revenue-anomalies?hotel_id=${hotelId}`),
}
