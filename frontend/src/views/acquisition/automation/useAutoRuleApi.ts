// SPDX-License-Identifier: Apache-2.0
/**
 * 自动发券规则 — 列表/KPI/预览/试跑等 API 与状态
 */
import { computed, ref, type Ref } from 'vue'
import { api } from '../../../lib/api'
import { hotelStore } from '../../../store/hotel'
import { toast } from '../../../lib/ui'
import { FALLBACK_FIELDS, useAutoRuleForm } from './useAutoRuleForm'
import { t } from '../../../lib/i18n'

type FormApi = ReturnType<typeof useAutoRuleForm>

export function useAutoRuleApi(
  formApi: FormApi,
  shared: {
    fields: Ref<any[]>
    coupons: Ref<any[]>
    preview: Ref<any>
  },
) {
  const { fields, coupons, preview } = shared
  const { form, dry, step, activeCoupons, buildPayload, validateEventParams, initParamPick, goto } =
    formApi

  const busy = ref(false)
  const kpi = ref<any>({})
  const rules = ref<any[]>([])
  const guests = ref<any[]>([])
  const statusFilter = ref('all')
  const dryResult = ref<any>(null)
  const showHistory = ref(false)
  const historyRows = ref<any[]>([])

  const filteredRules = computed(() => {
    if (statusFilter.value === 'all') return rules.value.filter((r) => r.status !== 'expired')
    return rules.value.filter((r) => r.status === statusFilter.value)
  })
  const statusCounts = computed(() => {
    const all = rules.value.filter((r) => r.status !== 'expired')
    return {
      all: all.length,
      active: all.filter((r) => r.status === 'active').length,
      draft: all.filter((r) => r.status === 'draft').length,
      paused: all.filter((r) => r.status === 'paused').length,
    }
  })
  const h5Guests = computed(() => guests.value.slice(0, 100))

  function fmtNum(n: any) {
    const v = Number(n || 0)
    return v.toLocaleString('zh-CN')
  }

  async function load() {
    const hid = hotelStore.hotelId
    const [k, r, f, c, g] = await Promise.all([
      api.mktAutoRulesKpi(hid).catch(() => ({})),
      api.mktAutoRulesList(hid).catch(() => []),
      api.mktAutoRulesFields().catch(() => []),
      api.mktCoupons(hid).catch(() => []),
      api.mktCustomers(hid, undefined, true).catch(() => []),
    ])
    kpi.value = k || {}
    rules.value = r || []
    fields.value =
      Array.isArray(f) && f.length
        ? f.map((x: any) => {
            const fb = FALLBACK_FIELDS.find((b) => b.key === x.key)
            return { ...fb, ...x, hint: x.hint || fb?.hint, example: x.example || fb?.example }
          })
        : [...FALLBACK_FIELDS]
    coupons.value = c || []
    guests.value = g || []
    if (!form.coupons.length && activeCoupons.value[0]) {
      form.coupons = [{ batch_id: activeCoupons.value[0].id, priority: 1 }]
    }
    if (!dry.rule_id && rules.value.find((x) => x.status === 'active')) {
      dry.rule_id = rules.value.find((x) => x.status === 'active').id
    }
  }

  async function refreshPreview() {
    try {
      preview.value = await api.mktAutoRulesPreview(hotelStore.hotelId, buildPayload(true))
    } catch (e: any) {
      preview.value = null
      toast(e?.message || t('预览失败'), false)
    }
  }

  async function save(asDraft = false) {
    if (!form.event_type) {
      toast(t('请选择触发器'), false)
      goto(1)
      return
    }
    if (!validateEventParams()) {
      goto(1)
      return
    }
    if (!form.coupons.length) {
      toast(t('请选择至少一张券'), false)
      goto(3)
      return
    }
    if (!form.name.trim()) {
      form.name = formApi.EVENTS.find((e) => e.key === form.event_type)?.nm || '未命名规则'
    }
    busy.value = true
    try {
      const payload = buildPayload(asDraft)
      const r = form.id
        ? await api.mktAutoRulesUpdate(hotelStore.hotelId, form.id, payload)
        : await api.mktAutoRulesCreate(hotelStore.hotelId, payload)
      toast(asDraft ? '已存为草稿' : form.enable_now ? '规则已启用' : '规则已保存')
      form.id = r.id
      await load()
    } catch (e: any) {
      toast(e?.message || t('保存失败'), false)
    } finally {
      busy.value = false
    }
  }

  async function editRule(r: any) {
    const detail = await api.mktAutoRulesGet(hotelStore.hotelId, r.id)
    form.id = detail.id
    form.name = detail.name
    form.description = detail.description || ''
    form.event_type = detail.event_type
    form.event_params = detail.event_params || {}
    form.scan_frequency = detail.scan_frequency || 'daily'
    initParamPick('reg_days', form.event_params.reg_days, 30)
    initParamPick('checkout_days', form.event_params.checkout_days, 7)
    initParamPick('silent_days', form.event_params.silent_days, 60)
    initParamPick('ahead_days', form.event_params.ahead_days, 7)
    initParamPick('min_avg_order', form.event_params.min_avg_order, 600)
    form.max_per_customer_day = detail.max_per_customer_day ?? 1
    form.rule_cooldown_days = detail.rule_cooldown_days ?? 30
    form.global_silence_days = detail.global_silence_days ?? 7
    form.active_window_start = (detail.active_window_start || '09:00:00').slice(0, 5)
    form.active_window_end = (detail.active_window_end || '21:00:00').slice(0, 5)
    form.push_channel = detail.push_channel || 'wecom'
    form.enable_now = detail.status === 'active'
    form.coupons = (detail.coupons || []).map((c: any) => ({
      batch_id: c.batch_id,
      priority: c.priority,
    }))
    form.filters = (detail.filters || []).map((f: any) => ({
      group_id: f.group_id,
      field: f.field,
      op: f.op,
      value: f.value_json?.v ?? f.value_json?.list?.join(',') ?? '',
    }))
    if (!form.filters.length) {
      form.filters = [{ group_id: 1, field: 'channel_reachable', op: '=', value: 1 }]
    }
    goto(1)
    toast(`已载入`)
  }

  async function toggleRule(r: any) {
    try {
      if (r.status === 'active') await api.mktAutoRulesPause(hotelStore.hotelId, r.id)
      else await api.mktAutoRulesEnable(hotelStore.hotelId, r.id)
      toast(r.status === 'active' ? '已暂停' : '已启用')
      await load()
    } catch (e: any) {
      toast(e?.message || t('操作失败'), false)
    }
  }

  async function removeRule(r: any) {
    if (!confirm(`确定删除规则「${r.name}」？已发券不会收回。`)) return
    await api.mktAutoRulesDelete(hotelStore.hotelId, r.id)
    toast(t('已删除'))
    await load()
  }

  async function runDry() {
    if (!dry.rule_id || !dry.guest_id) {
      toast(t('请选择规则和客户'), false)
      return
    }
    try {
      dryResult.value = await api.mktAutoRulesDryRun(hotelStore.hotelId, Number(dry.rule_id), [
        Number(dry.guest_id),
      ])
    } catch (e: any) {
      toast(e?.message || t('试跑失败'), false)
    }
  }

  async function openHistory() {
    const r = rules.value.find((x) => x.id === Number(dry.rule_id)) || rules.value[0]
    if (!r) {
      toast(t('暂无规则'), false)
      return
    }
    showHistory.value = true
    historyRows.value = (await api.mktAutoRulesTriggers(hotelStore.hotelId, r.id)).items || []
  }

  return {
    busy,
    kpi,
    rules,
    guests,
    statusFilter,
    preview,
    dryResult,
    showHistory,
    historyRows,
    filteredRules,
    statusCounts,
    h5Guests,
    fmtNum,
    load,
    refreshPreview,
    save,
    editRule,
    toggleRule,
    removeRule,
    runDry,
    openHistory,
  }
}
