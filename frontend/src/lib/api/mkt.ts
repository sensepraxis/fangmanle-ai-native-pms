// SPDX-License-Identifier: Apache-2.0
// API: mkt
import { req } from './client'

export const mktApi = {
  mktDashboard: (hotelId: number) => req<any>('GET', `/mkt/dashboard?hotel_id=${hotelId}`),
  mktAiNarrate: (hotelId: number, kind: 'diagnosis' | 'week_plan' | 'radar') =>
    req<any>('POST', `/mkt/ai-ops/${kind}?hotel_id=${hotelId}`, {}),
  mktAiDiagnosis: (hotelId: number) =>
    req<any>('POST', `/mkt/ai-ops/diagnosis?hotel_id=${hotelId}`, {}),
  mktAiExecute: (hotelId: number, action: Record<string, any>) =>
    req<any>('POST', `/mkt/ai-ops/execute?hotel_id=${hotelId}`, { action }),
  mktCouponAiNarrate: (
    hotelId: number,
    kind: 'smart_create' | 'audience' | 'rule_recommend' | 'budget' | 'redeem_insight',
    payload?: Record<string, any>,
  ) => req<any>('POST', `/mkt/coupon-ai/${kind}?hotel_id=${hotelId}`, payload || {}),
  mktCouponAiExecute: (hotelId: number, action: Record<string, any>) =>
    req<any>('POST', `/mkt/coupon-ai/execute?hotel_id=${hotelId}`, { action }),
  mktPrivateOverview: (hotelId: number) =>
    req<any>('GET', `/wecom/private/overview?hotel_id=${hotelId}`),
  mktCoupons: (hotelId: number, status?: string) =>
    req<any[]>(
      'GET',
      `/mkt/coupons?hotel_id=${hotelId}${status ? `&status=${encodeURIComponent(status)}` : ''}`,
    ),
  mktCouponTemplates: () => req<any[]>('GET', `/mkt/coupons/templates`),
  mktCreateCoupon: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/coupons?hotel_id=${hotelId}`, payload),
  mktCouponStatus: (hotelId: number, couponId: number, status: string) =>
    req<any>('PATCH', `/mkt/coupons/${couponId}/status?hotel_id=${hotelId}`, { status }),
  mktGrantCoupon: (hotelId: number, couponId: number, payload: any) =>
    req<any>('POST', `/mkt/coupons/${couponId}/grant?hotel_id=${hotelId}`, payload),
  mktCouponOwnership: (hotelId: number, couponId: number, guestIds?: number[]) => {
    const q =
      guestIds && guestIds.length
        ? `&guest_ids=${guestIds.map((x) => encodeURIComponent(String(x))).join(',')}`
        : ''
    return req<any>('GET', `/mkt/coupons/${couponId}/ownership?hotel_id=${hotelId}${q}`)
  },
  mktGrantSegments: (hotelId: number) =>
    req<any[]>('GET', `/mkt/grant-segments?hotel_id=${hotelId}`),
  mktGrantPreview: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/grant-preview?hotel_id=${hotelId}`, payload),
  mktCouponClaimEntries: (hotelId: number, couponId: number) =>
    req<any[]>('GET', `/mkt/coupons/${couponId}/claim-entries?hotel_id=${hotelId}`),
  mktBindClaimLanding: (hotelId: number, couponId: number, pageId: number) =>
    req<any>('POST', `/mkt/coupons/${couponId}/bind-claim-landing?hotel_id=${hotelId}`, {
      page_id: pageId,
    }),
  mktGrants: (hotelId: number) => req<any[]>('GET', `/mkt/grants?hotel_id=${hotelId}`),
  mktVerifyCoupon: (hotelId: number, payload: { code: string; order_id?: number }) =>
    req<any>('POST', `/mkt/coupons/verify?hotel_id=${hotelId}`, payload),
  mktCouponBatchList: (hotelId: number, status?: string) =>
    req<any[]>(
      'GET',
      `/mkt/coupon/batch?hotel_id=${hotelId}${status ? `&status=${encodeURIComponent(status)}` : ''}`,
    ),
  mktCouponBatchCreate: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/coupon/batch?hotel_id=${hotelId}`, payload),
  mktCouponBatchUpdate: (hotelId: number, batchId: number, payload: any) =>
    req<any>('PUT', `/mkt/coupon/batch/${batchId}?hotel_id=${hotelId}`, payload),
  mktCouponInstanceGrant: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/coupon/instance/grant?hotel_id=${hotelId}`, payload),
  mktCouponWallet: (hotelId: number, oneid: number) =>
    req<any>('GET', `/mkt/coupon/wallet?hotel_id=${hotelId}&oneid=${oneid}`),
  mktCouponClaim: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/coupon/claim?hotel_id=${hotelId}`, payload),
  mktCouponRedeem: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/coupon/redeem?hotel_id=${hotelId}`, payload),
  mktCouponVerifyPreview: (hotelId: number, code: string) =>
    req<any>('GET', `/mkt/coupon/verify?hotel_id=${hotelId}&code=${encodeURIComponent(code)}`),
  mktCouponTriggerCreate: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/coupon/trigger?hotel_id=${hotelId}`, payload),
  mktCouponTriggerList: (hotelId: number) =>
    req<any[]>('GET', `/mkt/coupon/trigger?hotel_id=${hotelId}`),
  mktCouponRedeemLog: (hotelId: number) =>
    req<any[]>('GET', `/mkt/coupon/redeem/log?hotel_id=${hotelId}`),
  mktCampaignTemplates: () => req<any[]>('GET', `/mkt/campaigns/templates`),
  mktCampaigns: (hotelId: number, status?: string) =>
    req<any[]>(
      'GET',
      `/mkt/campaigns?hotel_id=${hotelId}${status ? `&status=${encodeURIComponent(status)}` : ''}`,
    ),
  mktCreateCampaign: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/campaigns?hotel_id=${hotelId}`, payload),
  mktCampaignStatus: (hotelId: number, campaignId: number, status: string) =>
    req<any>('PATCH', `/mkt/campaigns/${campaignId}/status?hotel_id=${hotelId}`, { status }),
  mktApproveCampaign: (hotelId: number, campaignId: number, payload: any = {}) =>
    req<any>('POST', `/mkt/campaigns/${campaignId}/approve?hotel_id=${hotelId}`, payload),
  mktRejectCampaign: (hotelId: number, campaignId: number) =>
    req<any>('POST', `/mkt/campaigns/${campaignId}/reject?hotel_id=${hotelId}`, {}),
  mktLandingTemplates: () => req<any[]>('GET', `/mkt/landing-templates`),
  mktLandingPages: (hotelId: number) => req<any[]>('GET', `/mkt/landing-pages?hotel_id=${hotelId}`),
  mktCreateLanding: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/landing-pages?hotel_id=${hotelId}`, payload),
  mktUpdateLanding: (hotelId: number, pageId: number, payload: any) =>
    req<any>('PUT', `/mkt/landing-pages/${pageId}?hotel_id=${hotelId}`, payload),
  mktPublishLanding: (hotelId: number, pageId: number) =>
    req<any>('POST', `/mkt/landing-pages/${pageId}/publish?hotel_id=${hotelId}`, {}),
  mktUnpublishLanding: (hotelId: number, pageId: number) =>
    req<any>('POST', `/mkt/landing-pages/${pageId}/unpublish?hotel_id=${hotelId}`, {}),
  mktCustomers: (hotelId: number, tag?: string, h5Only?: boolean) =>
    req<any[]>(
      'GET',
      `/mkt/customers?hotel_id=${hotelId}${tag ? `&tag=${encodeURIComponent(tag)}` : ''}${
        h5Only ? '&h5_only=1' : ''
      }`,
    ),
  mktCustomer: (hotelId: number, guestId: number) =>
    req<any>('GET', `/mkt/customers/${guestId}?hotel_id=${hotelId}`),
  mktCustomerNote: (hotelId: number, guestId: number, payload: any) =>
    req<any>('PATCH', `/mkt/customers/${guestId}/note?hotel_id=${hotelId}`, payload),
  mktSettings: (hotelId: number) => req<any>('GET', `/mkt/settings?hotel_id=${hotelId}`),
  mktSaveSettings: (hotelId: number, payload: any) =>
    req<any>('PUT', `/mkt/settings?hotel_id=${hotelId}`, payload),
  mktMembers: (hotelId: number) => req<any>('GET', `/mkt/members?hotel_id=${hotelId}`),
  mktMemberAiNarrate: (
    hotelId: number,
    kind: 'threshold_calibrate' | 'benefit_pack',
    payload?: Record<string, any>,
  ) => req<any>('POST', `/mkt/member-ai/${kind}?hotel_id=${hotelId}`, payload || {}),
  mktMemberAiExecute: (hotelId: number, action: Record<string, any>) =>
    req<any>('POST', `/mkt/member-ai/execute?hotel_id=${hotelId}`, { action }),
  mktUpsertLevel: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/members/levels?hotel_id=${hotelId}`, payload),
  mktDeleteLevel: (hotelId: number, levelId: number) =>
    req<any>('DELETE', `/mkt/members/levels/${levelId}?hotel_id=${hotelId}`),
  mktMemberBenefitsPut: (hotelId: number, payload: any) =>
    req<any>('PUT', `/mkt/member/benefits?hotel_id=${hotelId}`, payload),
  mktMemberLevelRule: (hotelId: number) =>
    req<any>('GET', `/mkt/member/level-rule?hotel_id=${hotelId}`),
  mktMemberLevelRuleSave: (hotelId: number, payload: any) =>
    req<any>('PUT', `/mkt/member/level-rule?hotel_id=${hotelId}`, payload),
  mktMemberPointRule: (hotelId: number) =>
    req<any>('GET', `/mkt/member/point-rule?hotel_id=${hotelId}`),
  mktPointsAiNarrate: (
    hotelId: number,
    kind: 'rate_suggest' | 'expire_wakeup' | 'scenario_nl',
    payload?: Record<string, any>,
  ) => req<any>('POST', `/mkt/points-ai/${kind}?hotel_id=${hotelId}`, payload || {}),
  mktPointsAiExecute: (hotelId: number, action: Record<string, any>) =>
    req<any>('POST', `/mkt/points-ai/execute?hotel_id=${hotelId}`, { action }),
  mktMemberPointRuleSave: (hotelId: number, payload: any) =>
    req<any>('PUT', `/mkt/member/point-rule?hotel_id=${hotelId}`, payload),
  mktMemberPointPreview: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/member/point/preview?hotel_id=${hotelId}`, payload),
  mktAutomations: (hotelId: number) => req<any[]>('GET', `/mkt/automations?hotel_id=${hotelId}`),
  mktUpsertAutomation: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/automations?hotel_id=${hotelId}`, payload),
  mktAutomationEnabled: (hotelId: number, autoId: number, is_enabled: boolean) =>
    req<any>('PATCH', `/mkt/automations/${autoId}/enabled?hotel_id=${hotelId}`, { is_enabled }),
  mktAutomationPreview: (hotelId: number, autoId: number) =>
    req<any>('POST', `/mkt/automations/${autoId}/preview?hotel_id=${hotelId}`, {}),
  mktDeleteAutomation: (hotelId: number, autoId: number) =>
    req<any>('DELETE', `/mkt/automations/${autoId}?hotel_id=${hotelId}`),
  mktAutoRulesKpi: (hotelId: number) => req<any>('GET', `/mkt/auto-rules/kpi?hotel_id=${hotelId}`),
  mktAutoRulesFields: () => req<any[]>('GET', `/mkt/auto-rules/fields`),
  mktAutoRulesEvents: () => req<any[]>('GET', `/mkt/auto-rules/events`),
  mktAutoRulesList: (hotelId: number, status?: string) =>
    req<any[]>(
      'GET',
      `/mkt/auto-rules?hotel_id=${hotelId}${status && status !== 'all' ? `&status=${status}` : ''}`,
    ),
  mktAutoRulesGet: (hotelId: number, ruleId: number) =>
    req<any>('GET', `/mkt/auto-rules/${ruleId}?hotel_id=${hotelId}`),
  mktAutoRulesCreate: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/auto-rules?hotel_id=${hotelId}`, payload),
  mktAutoRulesUpdate: (hotelId: number, ruleId: number, payload: any) =>
    req<any>('PUT', `/mkt/auto-rules/${ruleId}?hotel_id=${hotelId}`, payload),
  mktAutoRulesEnable: (hotelId: number, ruleId: number) =>
    req<any>('POST', `/mkt/auto-rules/${ruleId}/enable?hotel_id=${hotelId}`, {}),
  mktAutoRulesPause: (hotelId: number, ruleId: number) =>
    req<any>('POST', `/mkt/auto-rules/${ruleId}/pause?hotel_id=${hotelId}`, {}),
  mktAutoRulesDelete: (hotelId: number, ruleId: number) =>
    req<any>('DELETE', `/mkt/auto-rules/${ruleId}?hotel_id=${hotelId}`),
  mktAutoRulesPreview: (hotelId: number, payload: any) =>
    req<any>(
      'POST',
      payload?.rule_id || payload?.id
        ? `/mkt/auto-rules/${payload.rule_id || payload.id}/preview?hotel_id=${hotelId}`
        : `/mkt/auto-rules/preview?hotel_id=${hotelId}`,
      payload,
    ),
  mktAutoRulesDryRun: (hotelId: number, ruleId: number, customerIds: number[]) =>
    req<any>('POST', `/mkt/auto-rules/${ruleId}/dry-run?hotel_id=${hotelId}`, {
      customer_ids: customerIds,
    }),
  mktAutoRulesTriggers: (hotelId: number, ruleId: number) =>
    req<any>('GET', `/mkt/auto-rules/${ruleId}/triggers?hotel_id=${hotelId}`),
  mktAutoRulesScan: (hotelId: number, payload: any = {}) =>
    req<any>('POST', `/mkt/auto-rules/scan?hotel_id=${hotelId}`, payload),
  mktAutoGrantTemplates: () => req<any[]>('GET', `/mkt/auto-grant/templates`),
  mktAutoGrantFields: () => req<any[]>('GET', `/mkt/auto-grant/fields`),
  mktAutoGrantPreview: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/auto-grant/preview?hotel_id=${hotelId}`, payload),
  mktAutoGrantRules: (hotelId: number) =>
    req<any[]>('GET', `/mkt/auto-grant/rules?hotel_id=${hotelId}`),
  mktAutoGrantUpsert: (hotelId: number, payload: any) =>
    req<any>('POST', `/mkt/auto-grant/rules?hotel_id=${hotelId}`, payload),
  mktAutoGrantEnabled: (hotelId: number, ruleId: number, is_enabled: boolean) =>
    req<any>('PATCH', `/mkt/auto-grant/rules/${ruleId}/enabled?hotel_id=${hotelId}`, {
      is_enabled,
    }),
  mktAutoGrantDelete: (hotelId: number, ruleId: number) =>
    req<any>('DELETE', `/mkt/auto-grant/rules/${ruleId}?hotel_id=${hotelId}`),
  mktAutoGrantScan: (hotelId: number, payload: any = {}) =>
    req<any>('POST', `/mkt/auto-grant/rules/scan?hotel_id=${hotelId}`, payload),
  mktAutoGrantTry: (hotelId: number, ruleId: number, guestId: number) =>
    req<any>('POST', `/mkt/auto-grant/rules/${ruleId}/try?hotel_id=${hotelId}`, {
      guest_id: guestId,
    }),
  couponLookup: (code: string) =>
    req<any>('GET', `/coupons/lookup?code=${encodeURIComponent(code)}`),
  couponRedeem: (payload: {
    coupon_id?: number
    code?: string
    order_id?: number
    remark?: string
  }) => req<any>('POST', '/coupons/redeem', payload),
  listCampaigns: (hotelId: number) => req<any[]>('GET', `/campaigns?hotel_id=${hotelId}`),
  createCampaign: (payload: any) => req<any>('POST', '/campaigns', payload),
  acquisitionBoard: (hotelId: number, channel?: string) =>
    req<any>(
      'GET',
      `/acquisition/board?hotel_id=${hotelId}${channel ? `&channel=${encodeURIComponent(channel)}` : ''}`,
    ),
  acquisitionLeads: (hotelId: number, stage?: string) =>
    req<any[]>(
      'GET',
      `/acquisition/leads?hotel_id=${hotelId}${stage ? `&stage=${encodeURIComponent(stage)}` : ''}`,
    ),
  acquisitionMockIngest: (payload: { hotel_id: number; count?: number }) =>
    req<any[]>('POST', '/acquisition/leads/mock-ingest', payload),
  acquisitionManualLead: (payload: Record<string, unknown>) =>
    req<any>('POST', '/acquisition/leads/manual', payload),
  acquisitionRoiAttribution: (hotelId: number, channel = 'xiaohongshu') =>
    req<any>(
      'GET',
      `/acquisition/roi-attribution?hotel_id=${hotelId}&channel=${encodeURIComponent(channel)}`,
    ),
  acquisitionDouyinTradeBoard: (hotelId: number) =>
    req<any>('GET', `/acquisition/douyin/trade-board?hotel_id=${hotelId}`),
  acquisitionClaimLead: (leadId: number, payload: Record<string, unknown> = {}) =>
    req<any>('POST', `/acquisition/leads/${leadId}/claim`, payload),
  acquisitionToPrivate: (leadId: number, payload: Record<string, unknown> = {}) =>
    req<any>('POST', `/acquisition/leads/${leadId}/to-private`, payload),
  acquisitionCreateOrder: (leadId: number, payload: Record<string, unknown>) =>
    req<any>('POST', `/acquisition/leads/${leadId}/convert-booking`, payload),
  acquisitionConvertBooking: (leadId: number, payload: Record<string, unknown>) =>
    req<any>('POST', `/acquisition/leads/${leadId}/convert-booking`, payload),
  acquisitionMarkArrived: (leadId: number, payload: Record<string, unknown> = {}) =>
    req<any>('POST', `/acquisition/leads/${leadId}/mark-arrived`, payload),
  acquisitionChannelBindings: (hotelId: number, channel = 'xiaohongshu') =>
    req<any>(
      'GET',
      `/acquisition/channel-bindings?hotel_id=${hotelId}&channel=${encodeURIComponent(channel)}`,
    ),
  acquisitionCreateChannelBinding: (payload: Record<string, unknown>) =>
    req<any>('POST', '/acquisition/channel-bindings', payload),
  acquisitionUpdateChannelBinding: (bindingId: number, payload: Record<string, unknown>) =>
    req<any>('PATCH', `/acquisition/channel-bindings/${bindingId}`, payload),
  acquisitionWebhookEvents: (hotelId: number, limit = 20) =>
    req<any[]>('GET', `/acquisition/webhook-events?hotel_id=${hotelId}&limit=${limit}`),
  acquisitionWebhookSimulate: (payload: Record<string, unknown> = {}) =>
    req<any>('POST', '/acquisition/webhook/simulate', payload),
  listReviews: (hotelId: number) => req<any[]>('GET', `/reviews?hotel_id=${hotelId}`),
}
