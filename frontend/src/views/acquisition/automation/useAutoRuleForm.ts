// SPDX-License-Identifier: Apache-2.0
/**
 * 自动发券规则 — 表单状态、事件参数、条件与 payload 构建
 */
import { computed, reactive, ref, type Ref } from 'vue'
import { toast } from '../../../lib/ui'
import { t } from '../../../lib/i18n'

export const EVENTS = [
  {
    key: 'NEW_WECHAT_MEMBER',
    ico: '👋',
    nm: '新客加入私域',
    desc: '客户首次加入私域通道时触发',
    pill: '实时',
    pill2: '1:1',
  },
  {
    key: 'REG_DAYS',
    ico: '📅',
    nm: '注册满 N 天',
    desc: '注册满指定天数时触发，每日扫描',
    pill: '每日',
    pill2: 'N 天',
  },
  {
    key: 'CHECKOUT_DAYS',
    ico: '🛏️',
    nm: '退房后 N 天',
    desc: '退房后指定天数召回',
    pill: '每日',
    pill2: 'PMS',
  },
  {
    key: 'SILENT_DAYS',
    ico: '😴',
    nm: '客户沉默 N 天',
    desc: '近 N 天无互动，每日扫描唤醒',
    pill: '每日',
    pill2: '唤醒',
  },
  {
    key: 'BIRTHDAY',
    ico: '🎂',
    nm: '客户生日',
    desc: '生日当日前 N 天推送',
    pill: '每日',
    pill2: '生日',
  },
  {
    key: 'HOLIDAY',
    ico: '🏮',
    nm: '节假日',
    desc: '指定节假日当日批量推送',
    pill: '指定日',
    pill2: '日历',
  },
  {
    key: 'HIGH_VALUE_NEW',
    ico: '💎',
    nm: '高价值新客',
    desc: '首次入住且单价达标',
    pill: '每日',
    pill2: 'PMS',
  },
  {
    key: 'CUSTOM',
    ico: '🛠️',
    nm: '自定义事件',
    desc: 'Webhook / API 显式触发',
    pill: 'API',
    pill2: '高级',
  },
]

/** 本地字段目录（与后端一致；接口失败时仍可用） */
export const FALLBACK_FIELDS = [
  {
    key: 'channel_reachable',
    label: '私域通道可达',
    type: 'bool',
    ops: ['=', '!='],
    hint: '是否已在当前私域 IM（企微/LINE/WhatsApp 等）建联。建议保留「= 是」。',
    example: '是',
  },
  {
    key: 'registered_days',
    label: '注册天数',
    type: 'number',
    ops: ['=', '>=', '<=', '>', '<'],
    hint: '从建档到今天的天数。例如「= 30」表示刚好注册满 30 天。',
    example: '30',
  },
  {
    key: 'last_stay_days',
    label: '距上次离店天数',
    type: 'number',
    ops: ['=', '>=', '<=', '>', '<'],
    hint: '离店后过了多少天。例如「= 7」做退房后 7 天召回。',
    example: '7',
  },
  {
    key: 'stay_records',
    label: '年内入住次数',
    type: 'number',
    ops: ['=', '>=', '<=', '>', '<'],
    hint: '今年已完成的入住次数。例如「>= 3」筛常客。',
    example: '3',
  },
  {
    key: 'avg_order_value',
    label: '平均房费',
    type: 'number',
    ops: ['=', '>=', '<=', '>', '<'],
    hint: '历史订单平均房费。例如「>= 600」筛高客单。',
    example: '600',
  },
  {
    key: 'customer_tag',
    label: '客户标签',
    type: 'enum',
    ops: ['in', 'contains'],
    enum: ['VIP', '商旅', '家庭', '新客'],
    hint: '客人身上的标签。选「属于」后点选标签。',
    example: 'VIP',
  },
  {
    key: 'first_private_member',
    label: '是否首加私域会员',
    type: 'bool',
    ops: ['='],
    hint: '是否刚成为私域会员（适合欢迎礼）。',
    example: '是',
  },
  {
    key: 'property_id',
    label: '指定酒店',
    type: 'number',
    ops: ['='],
    hint: '限定本店或指定酒店 ID。',
    example: '1',
  },
  {
    key: 'channel_flags',
    label: '渠道可达性',
    type: 'enum',
    ops: ['in'],
    enum: ['wecom', 'sms', 'mp'],
    hint: '客人可触达渠道。',
    example: 'wecom',
  },
]

export const OP_LABEL: Record<string, string> = {
  '=': '等于',
  '!=': '不等于',
  '>': '大于',
  '>=': '大于等于',
  '<': '小于',
  '<=': '小于等于',
  in: '属于',
  contains: '包含',
  between: '介于',
}

export type FilterRow = { group_id: number; field: string; op: string; value: string | number }
export type CouponPick = { batch_id: number; priority: number }

/** 事件参数：常用预设 + 自定义 */
export const CUSTOM = '__custom__'
export const PRESETS = {
  reg_days: [30, 90, 180, 365],
  checkout_days: [3, 7, 30, 90],
  silent_days: [30, 60, 90, 180],
  ahead_days: [0, 3, 7, 14],
  min_avg_order: [400, 600, 800, 1000],
} as const

export type ParamKey = keyof typeof PRESETS

export function useAutoRuleForm(deps: {
  fields: Ref<any[]>
  coupons: Ref<any[]>
  preview: Ref<any>
  onGotoPreview?: () => void
}) {
  const { fields, coupons, preview } = deps

  const step = ref(1)
  const form = reactive({
    id: null as number | null,
    name: '',
    description: '',
    event_type: 'NEW_WECHAT_MEMBER',
    event_params: {} as Record<string, any>,
    scan_frequency: 'realtime',
    filters: [{ group_id: 1, field: 'channel_reachable', op: '=', value: 1 }] as FilterRow[],
    coupons: [] as CouponPick[],
    max_per_customer_day: 1,
    rule_cooldown_days: 30,
    global_silence_days: 7,
    active_window_start: '09:00',
    active_window_end: '21:00',
    push_channel: 'wecom',
    enable_now: true,
  })

  const dry = reactive({
    rule_id: '' as string | number,
    guest_id: '' as string | number,
  })

  const paramPick = reactive<Record<ParamKey, { mode: number | typeof CUSTOM; custom: string }>>({
    reg_days: { mode: 30, custom: '' },
    checkout_days: { mode: 7, custom: '' },
    silent_days: { mode: 60, custom: '' },
    ahead_days: { mode: 7, custom: '' },
    min_avg_order: { mode: 600, custom: '' },
  })

  const fieldOptions = computed(() => (fields.value?.length ? fields.value : FALLBACK_FIELDS))
  const activeCoupons = computed(() => coupons.value.filter((c) => c.status === 'active'))

  function initParamPick(key: ParamKey, value: number | undefined, fallback: number) {
    const n = value == null || value === ('' as any) ? fallback : Number(value)
    const presets = PRESETS[key] as readonly number[]
    if (Number.isFinite(n) && presets.includes(n)) {
      paramPick[key].mode = n
      paramPick[key].custom = ''
    } else {
      paramPick[key].mode = CUSTOM
      paramPick[key].custom = Number.isFinite(n) ? String(Math.trunc(n)) : ''
    }
  }

  function resolvePositiveInt(
    key: ParamKey,
    label: string,
    opts: { allowZero?: boolean } = {},
  ): { ok: true; value: number } | { ok: false; msg: string } {
    const pick = paramPick[key]
    let n: number
    if (pick.mode === CUSTOM) {
      const raw = String(pick.custom ?? '').trim()
      if (!raw) return { ok: false, msg: t('请填写{label}', { label }) }
      if (!/^\d+$/.test(raw)) {
        return {
          ok: false,
          msg: opts.allowZero
            ? t('{label}须为 ≥0 的整数', { label })
            : t('{label}须为非零正整数', { label }),
        }
      }
      n = parseInt(raw, 10)
    } else {
      n = Number(pick.mode)
    }
    if (!Number.isInteger(n) || n < 0 || (!opts.allowZero && n < 1)) {
      return {
        ok: false,
        msg: opts.allowZero
          ? t('{label}须为 ≥0 的整数', { label })
          : t('{label}须为非零正整数', { label }),
      }
    }
    if (n > 9999) return { ok: false, msg: t('{label}过大，请填写 1–9999', { label }) }
    return { ok: true, value: n }
  }

  function applyEventParamsFromPick() {
    const et = form.event_type
    if (et === 'REG_DAYS') {
      const r = resolvePositiveInt('reg_days', '注册天数')
      if (!r.ok) return r
      form.event_params = { ...form.event_params, reg_days: r.value }
      return r
    }
    if (et === 'CHECKOUT_DAYS') {
      const r = resolvePositiveInt('checkout_days', '退房后天数')
      if (!r.ok) return r
      form.event_params = { ...form.event_params, checkout_days: r.value }
      return r
    }
    if (et === 'SILENT_DAYS') {
      const r = resolvePositiveInt('silent_days', '沉默天数')
      if (!r.ok) return r
      form.event_params = { ...form.event_params, silent_days: r.value }
      return r
    }
    if (et === 'BIRTHDAY') {
      const r = resolvePositiveInt('ahead_days', '提前天数', { allowZero: true })
      if (!r.ok) return r
      form.event_params = { ...form.event_params, ahead_days: r.value }
      return r
    }
    if (et === 'HIGH_VALUE_NEW') {
      const r = resolvePositiveInt('min_avg_order', '首住单价')
      if (!r.ok) return r
      form.event_params = { ...form.event_params, min_avg_order: r.value }
      return r
    }
    return { ok: true as const, value: 0 }
  }

  function onParamModeChange(key: ParamKey) {
    if (paramPick[key].mode !== CUSTOM) {
      paramPick[key].custom = ''
      const map: Partial<Record<ParamKey, string>> = {
        reg_days: 'reg_days',
        checkout_days: 'checkout_days',
        silent_days: 'silent_days',
        ahead_days: 'ahead_days',
        min_avg_order: 'min_avg_order',
      }
      const field = map[key]
      if (field) form.event_params[field] = paramPick[key].mode
    }
  }

  function validateEventParams(): boolean {
    const r = applyEventParamsFromPick()
    if (!r.ok) {
      toast(r.msg, false)
      return false
    }
    return true
  }

  function fieldMeta(key: string) {
    const list = fieldOptions.value
    return (
      list.find((f) => f.key === key) ||
      FALLBACK_FIELDS.find((f) => f.key === key) ||
      list[0] ||
      FALLBACK_FIELDS[0]
    )
  }

  function onFilterFieldChange(f: FilterRow) {
    const meta = fieldMeta(f.field)
    f.op = (meta?.ops && meta.ops[0]) || '='
    if (meta?.type === 'bool') f.value = 1
    else if (meta?.enum?.length) f.value = meta.enum[0]
    else f.value = meta?.example || ''
  }

  function goto(n: number) {
    step.value = n
    if (n === 5) deps.onGotoPreview?.()
  }

  function clearFilters() {
    form.filters = []
    goto(3)
  }

  function filterHumanSummary() {
    if (!form.filters.length) return t('不限')
    return form.filters
      .map((f, i) => {
        const meta = fieldMeta(f.field)
        const op = t(OP_LABEL[f.op] || f.op)
        let val: any = f.value
        if (meta?.type === 'bool') val = Number(f.value) ? t('是') : t('否')
        const logic =
          i === 0 ? '' : f.group_id !== form.filters[i - 1]?.group_id ? t('；或 ') : t('，且 ')
        return `${logic}${t(meta?.label || f.field)} ${op} ${val}`
      })
      .join('')
  }

  function selectEvent(key: string) {
    form.event_type = key
    const meta = EVENTS.find((e) => e.key === key)
    form.scan_frequency = key === 'NEW_WECHAT_MEMBER' || key === 'CUSTOM' ? 'realtime' : 'daily'
    if (key === 'REG_DAYS') {
      form.event_params = { reg_days: 30 }
      initParamPick('reg_days', 30, 30)
    } else if (key === 'CHECKOUT_DAYS') {
      form.event_params = { checkout_days: 7 }
      initParamPick('checkout_days', 7, 7)
    } else if (key === 'SILENT_DAYS') {
      form.event_params = { silent_days: 60 }
      initParamPick('silent_days', 60, 60)
    } else if (key === 'BIRTHDAY') {
      form.event_params = { ahead_days: 7 }
      initParamPick('ahead_days', 7, 7)
    } else if (key === 'HOLIDAY') form.event_params = { holiday: 'national_day' }
    else if (key === 'HIGH_VALUE_NEW') {
      form.event_params = { min_avg_order: 600 }
      initParamPick('min_avg_order', 600, 600)
    } else if (key === 'CUSTOM') form.event_params = { event_key: 'stay_completed' }
    else form.event_params = {}
    if (!form.name) form.name = meta?.nm || key
  }

  function gotoNextFromStep1() {
    if (!validateEventParams()) return
    goto(2)
  }

  function addFilter(newGroup = false) {
    const gid = newGroup
      ? Math.max(0, ...form.filters.map((x) => x.group_id), 0) + 1
      : form.filters[form.filters.length - 1]?.group_id || 1
    const meta = fieldOptions.value[0] || FALLBACK_FIELDS[0]
    const row: FilterRow = {
      group_id: gid,
      field: meta.key,
      op: (meta.ops && meta.ops[0]) || '=',
      value: meta.type === 'bool' ? 1 : meta.example || '',
    }
    form.filters.push(row)
  }

  function removeFilter(i: number) {
    form.filters.splice(i, 1)
  }

  function addCoupon() {
    const used = new Set(form.coupons.map((c) => c.batch_id))
    const next = activeCoupons.value.find((c) => !used.has(c.id))
    if (!next) {
      toast(t('没有更多可用批次'), false)
      return
    }
    form.coupons.push({ batch_id: next.id, priority: form.coupons.length + 1 })
  }

  function removeCoupon(i: number) {
    form.coupons.splice(i, 1)
    form.coupons.forEach((c, idx) => (c.priority = idx + 1))
  }

  function couponInfo(id: number) {
    return activeCoupons.value.find((c) => c.id === id) || coupons.value.find((c) => c.id === id)
  }

  function buildPayload(asDraft = false) {
    const filters = form.filters
      .filter((f) => f.field)
      .map((f, i) => {
        const meta = fieldMeta(f.field)
        let value_json: any = { v: f.value }
        if (meta?.type === 'bool') value_json = { v: Number(f.value) ? 1 : 0 }
        else if (f.op === 'in' || f.op === 'contains') {
          value_json = {
            list: String(f.value)
              .split(/[,，]/)
              .map((s) => s.trim())
              .filter(Boolean),
          }
        } else if (meta?.type === 'number') value_json = { v: Number(f.value) }
        return {
          group_id: f.group_id,
          field: f.field,
          op: f.op,
          value_json,
          sort_order: i,
        }
      })
    return {
      id: form.id || undefined,
      name: form.name.trim() || EVENTS.find((e) => e.key === form.event_type)?.nm || '未命名规则',
      description: form.description,
      event_type: form.event_type,
      event_params: { ...form.event_params },
      scan_frequency: form.scan_frequency,
      push_channel: form.push_channel,
      max_per_customer_day: form.max_per_customer_day,
      rule_cooldown_days: form.rule_cooldown_days,
      global_silence_days: form.global_silence_days,
      active_window_start:
        (form.active_window_start || '09:00').length === 5
          ? `${form.active_window_start}:00`
          : form.active_window_start,
      active_window_end:
        (form.active_window_end || '21:00').length === 5
          ? `${form.active_window_end}:00`
          : form.active_window_end,
      coupons: form.coupons.map((c, i) => ({
        batch_id: c.batch_id,
        priority: c.priority || i + 1,
      })),
      filters,
      as_draft: asDraft,
      enable_now: !asDraft && form.enable_now,
    }
  }

  function openNew() {
    form.id = null
    form.name = ''
    form.description = ''
    form.event_type = 'NEW_WECHAT_MEMBER'
    form.event_params = {}
    form.scan_frequency = 'realtime'
    initParamPick('reg_days', 30, 30)
    initParamPick('checkout_days', 7, 7)
    initParamPick('silent_days', 60, 60)
    initParamPick('ahead_days', 7, 7)
    initParamPick('min_avg_order', 600, 600)
    form.filters = [{ group_id: 1, field: 'channel_reachable', op: '=', value: 1 }]
    form.coupons = activeCoupons.value[0]
      ? [{ batch_id: activeCoupons.value[0].id, priority: 1 }]
      : []
    form.max_per_customer_day = 1
    form.rule_cooldown_days = 30
    form.global_silence_days = 7
    form.active_window_start = '09:00'
    form.active_window_end = '21:00'
    form.enable_now = true
    preview.value = null
    goto(1)
  }

  const summaryText = computed(() => {
    const ev = EVENTS.find((e) => e.key === form.event_type)
    const cps = form.coupons
      .map((c) => couponInfo(c.batch_id)?.name)
      .filter(Boolean)
      .join(' · ')
    return {
      event: ev ? t(ev.nm) : form.event_type,
      filters: form.filters.length,
      coupons: cps || t('未选'),
      anti: t('{max} 张/人/天 · {cool} 天冷却 · {sil} 天沉默 · {win}', {
        max: form.max_per_customer_day,
        cool: form.rule_cooldown_days,
        sil: form.global_silence_days,
        win: `${form.active_window_start}-${form.active_window_end}`,
      }),
    }
  })

  return {
    EVENTS,
    FALLBACK_FIELDS,
    OP_LABEL,
    CUSTOM,
    PRESETS,
    step,
    form,
    dry,
    paramPick,
    fieldOptions,
    activeCoupons,
    initParamPick,
    onParamModeChange,
    validateEventParams,
    fieldMeta,
    onFilterFieldChange,
    clearFilters,
    filterHumanSummary,
    goto,
    selectEvent,
    gotoNextFromStep1,
    addFilter,
    removeFilter,
    addCoupon,
    removeCoupon,
    couponInfo,
    buildPayload,
    openNew,
    summaryText,
  }
}
