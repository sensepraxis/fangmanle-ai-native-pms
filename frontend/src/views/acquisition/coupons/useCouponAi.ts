// SPDX-License-Identifier: Apache-2.0
import { nextTick, reactive, ref, type Ref } from 'vue'
import type { Router } from 'vue-router'
import { api } from '../../../lib/api'
import { hotelStore } from '../../../store/hotel'
import { toast } from '../../../lib/ui'
import type { CouponAiKind, CouponForm, GrantForm, GrantSub, NarrativeSlot, TabKey } from './types'
import { t } from '../../../lib/i18n'

export type { CouponAiKind }

export function useCouponAi(opts: {
  router: Router
  setTab: (t: TabKey) => void
  setGrantSub: (s: GrantSub) => void
  openWizard: (prefill?: any) => void
  form: CouponForm
  grantForm: GrantForm
  load: () => Promise<void>
  refreshSegmentPreview: () => Promise<void>
  rulesPanelKey: Ref<number>
}) {
  const {
    router,
    setTab,
    setGrantSub,
    openWizard,
    form,
    grantForm,
    load,
    refreshSegmentPreview,
    rulesPanelKey,
  } = opts

  const aiSlots = reactive<Record<CouponAiKind, NarrativeSlot>>({
    smart_create: { loading: false, insight: null, error: '' },
    audience: { loading: false, insight: null, error: '' },
    rule_recommend: { loading: false, insight: null, error: '' },
    budget: { loading: false, insight: null, error: '' },
    redeem_insight: { loading: false, insight: null, error: '' },
  })
  const aiExecuting = ref<string | null>(null)
  const aiGoal = ref(t('唤醒沉默客户'))
  const aiTargetRedeem = ref(25)
  const aiTargetRoi = ref('1:3')

  function makeFetcher(kind: CouponAiKind) {
    return async () => {
      const payload: Record<string, any> = { goal: aiGoal.value.trim() || undefined }
      if (kind === 'budget') {
        payload.target_redeem_rate = Number(aiTargetRedeem.value) || 25
        payload.target_roi = aiTargetRoi.value.trim() || undefined
      }
      return api.mktCouponAiNarrate(hotelStore.hotelId, kind, payload)
    }
  }

  async function runCouponAi(kind: CouponAiKind) {
    const slot = aiSlots[kind]
    if (slot.loading) return
    slot.loading = true
    slot.error = ''
    try {
      slot.insight = await makeFetcher(kind)()
    } catch (e: any) {
      slot.insight = null
      slot.error = e?.message || t('生成失败')
      toast(slot.error, false)
    } finally {
      slot.loading = false
    }
  }

  async function applyAiActionResult(a: any, res: any) {
    const doneType = res?.action_type || a.action_type
    if (doneType === 'open_wizard_prefill' && res?.prefill) {
      setTab('build')
      openWizard(res.prefill)
      if (res.prefill.name) form.name = res.prefill.name
      await nextTick()
      document.querySelector('.wizard')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    } else if (doneType === 'select_segment' && res?.segment_key != null) {
      setGrantSub('segment')
      grantForm.segment = res.segment_key
      await refreshSegmentPreview()
    } else if (doneType === 'create_coupon_draft') {
      setTab('build')
      await load()
    } else if (doneType === 'create_rule_draft' || doneType === 'create_coupon_rule_pack') {
      await load()
      setGrantSub('rules')
      rulesPanelKey.value += 1
    }
  }

  /** NarrativeInsightPanel executor：不重复 toast，由面板处理 */
  async function narrativeExecutor(a: Record<string, any>) {
    const res = await api.mktCouponAiExecute(hotelStore.hotelId, a)
    await applyAiActionResult(a, res)
    return res
  }

  async function runCouponAiAction(a: any) {
    if (!a || aiExecuting.value) return
    if (a.action_type === 'open_path') {
      const p = String(a.path || '/acquisition/coupons')
      if (p.includes('tab=grant') && p.includes('sub=segment')) setGrantSub('segment')
      else if (p.includes('tab=grant') && p.includes('sub=rules')) setGrantSub('rules')
      else if (p.includes('tab=redeem')) setTab('redeem')
      else if (p.includes('tab=build') || p === '/acquisition/coupons') setTab('build')
      else router.push(p)
      return
    }
    aiExecuting.value = a.id
    try {
      const res = await api.mktCouponAiExecute(hotelStore.hotelId, a)
      toast(res?.message || t('已执行'))
      await applyAiActionResult(a, res)
    } catch (e: any) {
      toast(e?.message || t('执行失败'), false)
    } finally {
      aiExecuting.value = null
    }
  }

  /** open_path 走路由 query，由壳层 watch 同步 tab/sub */
  function narrativeOpenPath(a: Record<string, any>) {
    if (a?.action_type === 'open_path') {
      const p = String(a.path || '/acquisition/coupons')
      if (p.includes('tab=grant') && p.includes('sub=segment')) setGrantSub('segment')
      else if (p.includes('tab=grant') && p.includes('sub=rules')) setGrantSub('rules')
      else if (p.includes('tab=redeem')) setTab('redeem')
      else if (p.includes('tab=build') || p === '/acquisition/coupons') setTab('build')
      else router.push(p)
      return true
    }
    return false
  }

  /**
   * 包装 executor：先拦截 open_path（NarrativeInsightPanel 默认 goPath 不调 setTab）
   * 实际用法：面板仍会先拦 open_path；故在面板外用 wrapExecutor 时需自定义。
   * 本项目用 NarrativeInsightPanel 时传入 narrativeExecutor，open_path 由面板 goPath 处理。
   */
  async function wrappedNarrativeExecutor(a: Record<string, any>) {
    if (narrativeOpenPath(a)) return { message: t('已跳转'), action_type: 'open_path' }
    return narrativeExecutor(a)
  }

  return {
    aiSlots,
    aiExecuting,
    aiGoal,
    aiTargetRedeem,
    aiTargetRoi,
    makeFetcher,
    runCouponAi,
    runCouponAiAction,
    narrativeExecutor,
    wrappedNarrativeExecutor,
  }
}
