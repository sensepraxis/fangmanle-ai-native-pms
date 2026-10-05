<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * 会员体系设置 · 密度对齐原型（保留 PMS 蓝）
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { confidenceLabel } from '../../lib/aiConfidence'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'

const router = useRouter()
type Tab = 'lv' | 'ben' | 'rule' | 'pt'
const tab = ref<Tab>('lv')

const levels = ref<any[]>([])
const overview = ref<any>(null)
const catalog = ref<any[]>([])
const expirePreview = ref<any[]>([])
const customers = ref<any[]>([])
const scenarios = ref<any[]>([])
const pointsRule = ref<any>({})
const selectedCode = ref('supreme')
const saving = ref(false)

const levelRule = reactive({
  upgrade_mode: 'growth',
  benefit_effective: 'next_order',
  remind_before_expire_days: [30, 7, 1] as number[],
  demote_protect_days: 90,
  demote_action: 'one_level',
  notify_upgrade: true,
})

const edit = reactive({
  id: null as number | null,
  level_code: '',
  level_name: '',
  sort_order: 1,
  upgrade_points: 0,
  retain_points: 0,
  valid_months: 24,
  color_hex: '#64748b',
  growth_rule: { consume_yuan: 1, stay_night: 80, review: 20, signin: 5 } as Record<string, number>,
  benefits: {} as Record<string, { on: boolean; value: any }>,
})

const previewCust = ref('c_gold')
const previewSc = ref('BIRTHDAY_5X')
const preview = ref<any>(null)

/** 会员体系 AI · #12 #13 */
type MemberAiKind = 'threshold_calibrate' | 'benefit_pack'
type NarrativeSlot = { loading: boolean; insight: any | null; error: string }
const aiSlots = reactive<Record<MemberAiKind, NarrativeSlot>>({
  threshold_calibrate: { loading: false, insight: null, error: '' },
  benefit_pack: { loading: false, insight: null, error: '' },
})
const aiExecuting = ref<string | null>(null)
const AI_UI: Record<
  MemberAiKind,
  { title: string; idle: string; run: string; rerun: string; wait: string }
> = {
  threshold_calibrate: {
    title: t('等级门槛智能校准'),
    idle: '',
    run: t('开始校准'),
    rerun: t('重新校准'),
    wait: t('正在分析各等级人数分布与门槛…'),
  },
  benefit_pack: {
    title: t('权益包推荐'),
    idle: '',
    run: t('推荐权益包'),
    rerun: t('重新推荐'),
    wait: t('正在匹配房型能力与等级权益…'),
  },
}
const confText = (c: string) => confidenceLabel(c)

function aiSourceLabel(insight: any) {
  const s = insight?.source
  if (s === 'llm') return t('AI 解读')
  if (s === 'unavailable' || s === 'fallback') return t('AI 暂不可用')
  if (s === 'rules_disabled') return t('AI 未启用')
  return ''
}

async function runMemberAi(kind: MemberAiKind) {
  const slot = aiSlots[kind]
  if (slot.loading) return
  slot.loading = true
  slot.error = ''
  try {
    slot.insight = await api.mktMemberAiNarrate(hotelStore.hotelId, kind)
  } catch (e: any) {
    slot.insight = null
    slot.error = e?.message || t('生成失败')
    toast(slot.error, false)
  } finally {
    slot.loading = false
  }
}

async function runMemberAiAction(a: any) {
  if (!a || aiExecuting.value) return
  if (a.action_type === 'open_path') {
    const p = String(a.path || '/acquisition/members')
    if (p.includes('/points')) router.push('/acquisition/points')
    else if (p.includes('/coupons')) router.push('/acquisition/coupons')
    else tab.value = 'lv'
    return
  }
  aiExecuting.value = a.id
  try {
    const res = await api.mktMemberAiExecute(hotelStore.hotelId, a)
    toast(res?.message || t('已执行'))
    await load()
    if (a.action_type === 'apply_benefit_pack') {
      tab.value = 'ben'
      if (res?.level_code) pickLevel(res.level_code)
    } else if (a.action_type === 'apply_level_thresholds') {
      tab.value = 'lv'
      const first = (res?.thresholds || a.thresholds || [])[0]
      if (first?.level_code) pickLevel(first.level_code)
    }
  } catch (e: any) {
    toast(e?.message || t('执行失败'), false)
  } finally {
    aiExecuting.value = null
  }
}

const DEFAULT_SCENARIOS = [
  {
    key: 'BIRTHDAY_5X',
    label: t('生日入住 3 晚 ¥1800'),
    icon: '🎂',
    params: { amount: 1800, nights: 3, is_birthday_month: true },
  },
  {
    key: 'HOLIDAY',
    label: t('国庆 7 晚 ¥5500'),
    icon: '🎉',
    params: { amount: 5500, nights: 7, is_holiday: true },
  },
  {
    key: 'REVIEW_GOOD',
    label: t('首住 + 5 星好评'),
    icon: '⭐',
    params: { is_review: true, is_first_review: true, amount: 0, nights: 1 },
  },
  {
    key: 'REFUND',
    label: t('退款 1000 元'),
    icon: '↩️',
    params: { refund_amount: 1000, orig_points: 1500 },
  },
]

const DEFAULT_CUSTOMERS = [
  { id: 'c_gold', name: t('王女士'), level: 'gold', available_points: 3200, growth: 3200 },
  { id: 'c_plat', name: t('李先生'), level: 'platinum', available_points: 12800, growth: 12000 },
  { id: 'c_sil', name: t('新客·赵'), level: 'silver', available_points: 80, growth: 120 },
]

const LV_CLASS: Record<string, string> = {
  silver: 'l1',
  gold: 'l2',
  platinum: 'l3',
  diamond: 'l4',
  supreme: 'l5',
}
const LV_NAME: Record<string, string> = {
  silver: t('银卡'),
  gold: t('金卡'),
  platinum: t('白金卡'),
  diamond: t('钻石卡'),
  supreme: t('至尊卡'),
}

function upOf(l: any) {
  return Number(l?.upgrade_points ?? l?.upgrade_value ?? 0)
}
function retainOf(l: any) {
  return Number(l?.retain_points ?? l?.retention_value ?? 0)
}
function fmtNum(n: number) {
  return Number(n || 0).toLocaleString('zh-CN')
}

const sortedLevels = computed(() =>
  [...levels.value].sort((a, b) => {
    const d = upOf(b) - upOf(a)
    if (d !== 0) return d
    return Number(b.sort_order || 0) - Number(a.sort_order || 0)
  }),
)

const selectedLevel = computed(() => levels.value.find((l) => l.level_code === selectedCode.value))

const memberCount = computed(() =>
  Number(overview.value?.members ?? overview.value?.wallet_members ?? 0),
)
const avgDiscountText = computed(() => {
  const v = overview.value?.avg_discount
  if (v == null || v === '' || Number.isNaN(Number(v))) return '—'
  return String(v)
})

const scenarioList = computed(() =>
  (scenarios.value?.length ? scenarios.value : DEFAULT_SCENARIOS).slice(0, 5),
)
const customerList = computed(() => (customers.value?.length ? customers.value : DEFAULT_CUSTOMERS))

const FALLBACK_CATALOG = [
  {
    key: 'discount_rate',
    label: t('房费折扣'),
    unit: t('倍率'),
    input: 'number',
    hint: t('0.95=95折'),
  },
  { key: 'free_breakfast', label: t('免费早餐'), unit: t('份/日'), input: 'number' },
  {
    key: 'upgrade_room',
    label: t('免费升房'),
    unit: '',
    input: 'select',
    options: [
      { value: 'deluxe_to_exec', label: t('豪华→行政') },
      { value: 'any_one_level', label: t('任意升一级') },
    ],
  },
  { key: 'late_checkout', label: t('延迟退房'), unit: t('小时'), input: 'number' },
  { key: 'free_cancellation', label: t('免费取消窗口'), unit: t('小时'), input: 'number' },
  { key: 'welcome_fruit', label: t('迎宾果盘'), unit: '', input: 'bool' },
  {
    key: 'dedicated_concierge',
    label: t('专属管家'),
    unit: '',
    input: 'select',
    options: [
      { value: 'work_hours', label: t('工作时段') },
      { value: '12h', label: '12h' },
      { value: '24h', label: '24h' },
    ],
  },
  { key: 'points_acceleration', label: t('积分倍率加成'), unit: 'X', input: 'number' },
  {
    key: 'birthday_gift',
    label: t('生日礼包'),
    unit: '',
    input: 'select',
    options: [
      { value: 'points_1000', label: t('积分+1000') },
      { value: 'breakfast_coupon', label: t('免费早餐券') },
      { value: 'free_night', label: t('免费住1晚') },
    ],
  },
  { key: 'vip_lounge', label: t('行政酒廊'), unit: '', input: 'bool' },
]

function activeCatalog() {
  return catalog.value?.length ? catalog.value : FALLBACK_CATALOG
}

function benefitOf(lv: any, key: string) {
  const b = (lv?.benefits || {})[key]
  if (!b || !b.on) return '—'
  if (key === 'discount_rate') {
    const rate = Number(b.value)
    if (!rate) return '—'
    return `${(rate * 10).toFixed(1)} ${t('折')}`
  }
  if (key === 'free_breakfast') return `${b.value} ${t('份')}`
  if (key === 'late_checkout') return `+${b.value} ${t('时')}`
  if (key === 'points_acceleration') return `${b.value}X`
  if (key === 'upgrade_room') {
    const map: Record<string, string> = {
      any_one_level: t('任意+1'),
      deluxe_to_exec: t('豪华→行政'),
      suite_first: t('套房首选'),
    }
    return map[b.value] || String(b.value)
  }
  if (key === 'dedicated_concierge') return String(b.value || t('有'))
  if (typeof b.value === 'boolean') return b.on ? t('有') : '—'
  return String(b.value ?? t('有'))
}

function ensureBenefitDefaults(raw: any) {
  const out: Record<string, { on: boolean; value: any }> = {}
  for (const c of activeCatalog()) {
    const cur = (raw || {})[c.key]
    out[c.key] = {
      on: !!(cur && cur.on),
      value:
        cur?.value ??
        (c.input === 'bool' ? true : c.input === 'number' ? 0 : c.options?.[0]?.value || ''),
    }
  }
  return out
}

function pickLevel(code: string) {
  selectedCode.value = code
  const l = levels.value.find((x) => x.level_code === code)
  if (!l) return
  edit.id = l.id
  edit.level_code = l.level_code
  edit.level_name = l.level_name
  edit.sort_order = l.sort_order
  edit.upgrade_points = upOf(l)
  edit.retain_points = retainOf(l)
  edit.valid_months = Number(l.valid_months ?? 24)
  edit.color_hex = l.color_hex || '#64748b'
  edit.growth_rule = {
    consume_yuan: 1,
    stay_night: 80,
    review: 20,
    signin: 5,
    ...(l.growth_rule || {}),
  }
  edit.benefits = ensureBenefitDefaults(l.benefits)
}

/** 本地试算兜底（API 未就绪时仍展示完整右侧栏） */
function localPreview(): any {
  const cust = customerList.value.find((c) => c.id === previewCust.value) || customerList.value[0]
  const sc = scenarioList.value.find((s) => s.key === previewSc.value) || scenarioList.value[0]
  const params = { ...(sc?.params || {}) }
  const rule = pointsRule.value || {}
  const level = cust?.level || 'gold'
  const levelM = Number((rule.level_multipliers || {})[level] ?? (level === 'gold' ? 1.5 : 1))
  const bdayM = Number((rule.birthday_bonus_by_level || {})[level] ?? 8)
  const holM = Number((rule.holiday_bonus_by_level || {})[level] ?? 3)
  const baseRate = Number(rule.base_rate ?? 1)
  const amount = Number(params.amount || 0)
  const nights = Number(params.nights || 0)
  const lines: any[] = []
  let total = 0
  const warnings: string[] = []

  if (previewSc.value === 'REFUND') {
    const delta = -Math.round(Number(params.orig_points || 1500) * 0.67)
    lines.push({ label: t('退款冲销'), points: delta })
    total = delta
  } else if (previewSc.value === 'REVIEW_GOOD') {
    let pts = Number(rule.review_points ?? 20)
    if (params.is_first_review) pts += Number(rule.review_photo_bonus ?? 50)
    lines.push({ label: t('评价奖励'), points: pts })
    if (nights) {
      lines.push({ label: t('入住加成'), points: nights * 30 })
      pts += nights * 30
    }
    total = pts
  } else {
    if (amount > 0) {
      const basePts = Math.round(amount * baseRate * levelM)
      lines.push({
        label: t('消费基础 × 等级{m}X', { m: levelM }),
        points: basePts,
        detail: `¥${amount} × ${levelM}`,
      })
      total += basePts
      if (params.is_birthday_month) {
        const b = Math.round(amount * bdayM)
        lines.push({ label: t('生日倍率 +{m}', { m: bdayM }), points: b })
        total += b
        warnings.push(t('生日倍率命中，将达到单笔上限的 60%。'))
      }
      if (params.is_holiday) {
        const h = Math.round(amount * holM)
        lines.push({ label: t('节假日倍率 +{m}', { m: holM }), points: h })
        total += h
      }
    }
    if (nights > 0) {
      const np = nights * 30
      lines.push({ label: t('入住 {n} 晚加成', { n: nights }), points: np })
      total += np
    }
  }

  const orderCap = Number(rule.single_order_cap || 10000)
  const dailyCap = Number(rule.daily_cap || 50000)
  const capped = Math.min(total, orderCap, dailyCap)
  if (capped < total) {
    lines.push({ label: t('上限钳制'), points: capped - total })
    warnings.push(t('已按单笔/日上限钳制至 {n}', { n: capped }))
    total = capped
  }

  const growthNow = Number(cust?.growth ?? cust?.available_points ?? 0)
  const growthAfter = growthNow + Math.max(0, Math.round(amount) + nights * 80)
  let expected = LV_NAME[level] || level
  const sorted = [...levels.value].sort((a, b) => upOf(a) - upOf(b))
  for (const lv of sorted) {
    if (growthAfter >= upOf(lv)) expected = lv.level_name
  }

  return {
    scenario_label: sc?.label,
    customer: {
      name: cust?.name,
      level: LV_NAME[level] || level,
      current_points: cust?.available_points ?? cust?.current_points ?? 0,
    },
    calc_lines: lines,
    total_delta: total,
    after_balance: Number(cust?.available_points || 0) + total,
    growth_before: growthNow,
    growth_after: growthAfter,
    expected_level_after: expected,
    warnings,
  }
}

async function runPreview() {
  try {
    preview.value = await api.mktMemberPointPreview(hotelStore.hotelId, {
      customer_id: previewCust.value,
      scenario: previewSc.value,
    })
    if (!preview.value?.calc_lines?.length) preview.value = localPreview()
  } catch {
    preview.value = localPreview()
  }
}

async function load() {
  const r = await api.mktMembers(hotelStore.hotelId)
  levels.value = r.levels || []
  overview.value = r.overview || null
  catalog.value = r.benefit_catalog || []
  expirePreview.value = r.expire_preview || []
  customers.value = r.customers || []
  scenarios.value = (r.scenarios || []).filter(
    (s: any) => !String(s.key || '').startsWith('RECHARGE'),
  )
  pointsRule.value = r.points || {}
  Object.assign(levelRule, r.level_rule || {})
  if (String(levelRule.upgrade_mode || '').includes('recharge')) {
    levelRule.upgrade_mode = 'growth'
  }
  // 对齐原型默认选中 L5
  const prefer =
    levels.value.find((l) => l.level_code === 'supreme') ||
    levels.value.find((l) => l.level_code === selectedCode.value) ||
    sortedLevels.value[0]
  if (prefer) pickLevel(prefer.level_code)
  // 试算场景：优先生日入住
  if (scenarioList.value.some((s) => s.key === 'BIRTHDAY_5X')) previewSc.value = 'BIRTHDAY_5X'
  await runPreview()
}

async function saveLevel() {
  saving.value = true
  try {
    await api.mktUpsertLevel(hotelStore.hotelId, {
      id: edit.id || undefined,
      level_code: edit.level_code,
      level_name: edit.level_name,
      sort_order: edit.sort_order,
      upgrade_points: edit.upgrade_points,
      retain_points: edit.retain_points,
      valid_months: edit.valid_months,
      color_hex: edit.color_hex,
      growth_rule: { ...edit.growth_rule },
      benefits: { ...edit.benefits },
      is_active: true,
    })
    toast(t('等级已保存'))
    await load()
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    saving.value = false
  }
}

async function saveBenefits() {
  saving.value = true
  try {
    await api.mktMemberBenefitsPut(hotelStore.hotelId, {
      level_code: edit.level_code,
      benefits: { ...edit.benefits },
    })
    toast(t('权益已保存'))
    await load()
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    saving.value = false
  }
}

async function saveRule() {
  saving.value = true
  try {
    await api.mktMemberLevelRuleSave(hotelStore.hotelId, { ...levelRule })
    toast(t('升降级规则已保存'))
    await load()
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    saving.value = false
  }
}

function onTab(t: Tab) {
  if (t === 'pt') {
    router.push('/acquisition/points')
    return
  }
  tab.value = t
}

function saveCurrent() {
  if (tab.value === 'ben') return saveBenefits()
  if (tab.value === 'rule') return saveRule()
  return saveLevel()
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch([previewCust, previewSc], runPreview)
</script>

<template>
  <div class="ms">
    <div class="head">
      <h1>{{ t('会员体系设置') }}</h1>
    </div>

    <div class="layout">
      <div class="main">
        <div class="kpis">
          <div class="kpi">
            <div class="label">{{ t('会员总数') }}</div>
            <div class="num">{{ fmtNum(memberCount) }}</div>
          </div>
          <div class="kpi">
            <div class="label">{{ t('积分余额合计') }}</div>
            <div class="num">{{ fmtNum(overview?.total_points || 0) }}</div>
          </div>
          <div class="kpi">
            <div class="label">{{ t('平均折扣') }}</div>
            <div class="num">
              {{ avgDiscountText }}<span class="unit-zh">{{ t('折') }}</span>
            </div>
          </div>
        </div>

        <div class="workspace">
          <div class="tabs" role="tablist">
            <button
              type="button"
              role="tab"
              class="tab"
              :class="{ active: tab === 'lv' }"
              :aria-selected="tab === 'lv'"
              @click="onTab('lv')"
            >
              {{ t('等级体系') }}
            </button>
            <button
              type="button"
              role="tab"
              class="tab"
              :class="{ active: tab === 'ben' }"
              :aria-selected="tab === 'ben'"
              @click="onTab('ben')"
            >
              {{ t('等级权益') }}
            </button>
            <button
              type="button"
              role="tab"
              class="tab"
              :class="{ active: tab === 'rule' }"
              :aria-selected="tab === 'rule'"
              @click="onTab('rule')"
            >
              {{ t('升降级规则') }}
            </button>
            <button type="button" role="tab" class="tab" @click="onTab('pt')">
              {{ t('积分规则') }}
            </button>
          </div>

          <div class="workspace-body">
            <template v-if="tab === 'lv'">
              <section v-if="commercialEnabled()" class="ai-block panel">
                <div class="ai-head">
                  <div class="ai-head-l">
                    <h3>{{ AI_UI.threshold_calibrate.title }}</h3>
                    <span class="ai-mark">AI</span>
                  </div>
                  <button
                    type="button"
                    class="ai-run"
                    :disabled="aiSlots.threshold_calibrate.loading"
                    @click="runMemberAi('threshold_calibrate')"
                  >
                    {{
                      aiSlots.threshold_calibrate.loading
                        ? t('校准中…')
                        : aiSlots.threshold_calibrate.insight
                          ? AI_UI.threshold_calibrate.rerun
                          : AI_UI.threshold_calibrate.run
                    }}
                  </button>
                </div>
                <template v-if="aiSlots.threshold_calibrate.loading">
                  <p class="ai-wait">{{ AI_UI.threshold_calibrate.wait }}</p>
                </template>
                <template v-else-if="aiSlots.threshold_calibrate.insight">
                  <p class="ai-meta">
                    <span>{{ aiSourceLabel(aiSlots.threshold_calibrate.insight) }}</span>
                    <span
                      v-if="formatAiModelMeta(aiSlots.threshold_calibrate.insight)"
                      class="conf-pill"
                      >{{ formatAiModelMeta(aiSlots.threshold_calibrate.insight) }}</span
                    >
                    <span v-if="aiSlots.threshold_calibrate.insight.confidence" class="conf-pill">{{
                      confText(aiSlots.threshold_calibrate.insight.confidence)
                    }}</span>
                    <span v-if="aiSlots.threshold_calibrate.insight.confidence_note">
                      · {{ aiSlots.threshold_calibrate.insight.confidence_note }}</span
                    >
                  </p>
                  <div class="ai-insight-body">
                    <div v-html="aiSlots.threshold_calibrate.insight.narrative_html" />
                  </div>
                  <div
                    v-if="aiSlots.threshold_calibrate.insight.actions?.length"
                    class="dx-actions"
                  >
                    <div class="dx-actions-h">{{ t('可执行操作') }}</div>
                    <div class="dx-action-list">
                      <article
                        v-for="a in aiSlots.threshold_calibrate.insight.actions"
                        :key="a.id"
                        class="dx-action-card"
                      >
                        <div class="dx-action-title">{{ a.title }}</div>
                        <div v-if="a.body" class="dx-action-body">{{ a.body }}</div>
                        <button
                          type="button"
                          class="dx-act"
                          :disabled="!!aiExecuting"
                          @click="runMemberAiAction(a)"
                        >
                          {{ aiExecuting === a.id ? t('执行中…') : a.action_label || t('执行') }}
                        </button>
                      </article>
                    </div>
                  </div>
                  <p v-if="aiSlots.threshold_calibrate.insight.llm_error" class="ai-soft-err">
                    {{ t(aiSlots.threshold_calibrate.insight.llm_error) }}
                  </p>
                </template>
                <div v-else-if="AI_UI.threshold_calibrate.idle" class="ai-idle">
                  {{ AI_UI.threshold_calibrate.idle }}
                </div>
                <p v-if="aiSlots.threshold_calibrate.error" class="ai-err">
                  {{ aiSlots.threshold_calibrate.error }}
                </p>
              </section>

              <div class="panel">
                <h3>{{ t('等级一览') }}</h3>
                <div class="lv-row">
                  <button
                    v-for="l in sortedLevels"
                    :key="l.level_code"
                    type="button"
                    class="lv-card"
                    :class="[
                      LV_CLASS[l.level_code] || 'l1',
                      { active: selectedCode === l.level_code },
                    ]"
                    @click="pickLevel(l.level_code)"
                  >
                    <span class="lv-code">{{ l.level_disp || 'L' + (l.sort_order || '') }}</span>
                    <div class="lv-name">{{ l.level_name }}</div>
                    <div class="lv-up">
                      {{ upOf(l) === 0 ? t('入门级') : t('升级所需成长值') }}
                      <b>{{ fmtNum(upOf(l)) }}</b>
                    </div>
                  </button>
                </div>
              </div>
              <div class="panel">
                <h3>{{ t('编辑等级') }} · {{ edit.level_name || '—' }}</h3>
                <div class="row3">
                  <label class="field"
                    >{{ t('等级代码') }}<span class="req">*</span><input v-model="edit.level_code"
                  /></label>
                  <label class="field"
                    >{{ t('等级名称') }}<span class="req">*</span><input v-model="edit.level_name"
                  /></label>
                  <label class="field"
                    >{{ t('展示顺序')
                    }}<input v-model.number="edit.sort_order" type="number" min="1" max="9"
                  /></label>
                </div>
                <div class="row3">
                  <label class="field"
                    >{{ t('升级所需成长值')
                    }}<input v-model.number="edit.upgrade_points" type="number" />
                  </label>
                  <label class="field"
                    >{{ t('保级所需成长值')
                    }}<input v-model.number="edit.retain_points" type="number" />
                  </label>
                  <label class="field"
                    >{{ t('等级有效期（月）')
                    }}<input v-model.number="edit.valid_months" type="number" />
                  </label>
                </div>
                <div class="field-block">
                  <div class="flabel">{{ t('成长值来源权重') }}</div>
                  <div class="row4">
                    <label class="field"
                      >{{ t('消费（¥ / 1 成长值）')
                      }}<input
                        v-model.number="edit.growth_rule.consume_yuan"
                        type="number"
                        step="0.1"
                    /></label>
                    <label class="field"
                      >{{ t('入住每晚 → 成长值')
                      }}<input v-model.number="edit.growth_rule.stay_night" type="number"
                    /></label>
                    <label class="field"
                      >{{ t('评价 → 成长值')
                      }}<input v-model.number="edit.growth_rule.review" type="number"
                    /></label>
                    <label class="field"
                      >{{ t('签到 → 成长值')
                      }}<input v-model.number="edit.growth_rule.signin" type="number"
                    /></label>
                  </div>
                </div>
                <div class="acts">
                  <button class="btn primary" type="button" @click="saveLevel">
                    {{ t('保存本等级') }}
                  </button>
                </div>
              </div>
            </template>

            <template v-if="tab === 'ben'">
              <section v-if="commercialEnabled()" class="ai-block panel">
                <div class="ai-head">
                  <div class="ai-head-l">
                    <h3>{{ AI_UI.benefit_pack.title }}</h3>
                    <span class="ai-mark">AI</span>
                  </div>
                  <button
                    type="button"
                    class="ai-run"
                    :disabled="aiSlots.benefit_pack.loading"
                    @click="runMemberAi('benefit_pack')"
                  >
                    {{
                      aiSlots.benefit_pack.loading
                        ? t('推荐中…')
                        : aiSlots.benefit_pack.insight
                          ? AI_UI.benefit_pack.rerun
                          : AI_UI.benefit_pack.run
                    }}
                  </button>
                </div>
                <template v-if="aiSlots.benefit_pack.loading">
                  <p class="ai-wait">{{ AI_UI.benefit_pack.wait }}</p>
                </template>
                <template v-else-if="aiSlots.benefit_pack.insight">
                  <p class="ai-meta">
                    <span>{{ aiSourceLabel(aiSlots.benefit_pack.insight) }}</span>
                    <span
                      v-if="formatAiModelMeta(aiSlots.benefit_pack.insight)"
                      class="conf-pill"
                      >{{ formatAiModelMeta(aiSlots.benefit_pack.insight) }}</span
                    >
                    <span v-if="aiSlots.benefit_pack.insight.confidence" class="conf-pill">{{
                      confText(aiSlots.benefit_pack.insight.confidence)
                    }}</span>
                    <span v-if="aiSlots.benefit_pack.insight.confidence_note">
                      · {{ aiSlots.benefit_pack.insight.confidence_note }}</span
                    >
                  </p>
                  <div class="ai-insight-body">
                    <div v-html="aiSlots.benefit_pack.insight.narrative_html" />
                  </div>
                  <div v-if="aiSlots.benefit_pack.insight.actions?.length" class="dx-actions">
                    <div class="dx-actions-h">{{ t('可执行操作') }}</div>
                    <div class="dx-action-list">
                      <article
                        v-for="a in aiSlots.benefit_pack.insight.actions"
                        :key="a.id"
                        class="dx-action-card"
                      >
                        <div class="dx-action-title">{{ a.title }}</div>
                        <div v-if="a.body" class="dx-action-body">{{ a.body }}</div>
                        <button
                          type="button"
                          class="dx-act"
                          :disabled="!!aiExecuting"
                          @click="runMemberAiAction(a)"
                        >
                          {{ aiExecuting === a.id ? t('执行中…') : a.action_label || t('执行') }}
                        </button>
                      </article>
                    </div>
                  </div>
                  <p v-if="aiSlots.benefit_pack.insight.llm_error" class="ai-soft-err">
                    {{ t(aiSlots.benefit_pack.insight.llm_error) }}
                  </p>
                </template>
                <div v-else-if="AI_UI.benefit_pack.idle" class="ai-idle">
                  {{ AI_UI.benefit_pack.idle }}
                </div>
                <p v-if="aiSlots.benefit_pack.error" class="ai-err">
                  {{ aiSlots.benefit_pack.error }}
                </p>
              </section>

              <div class="panel">
                <div class="ben-head">
                  <h3>{{ t('{name} 权益', { name: selectedLevel?.level_name || '—' }) }}</h3>
                  <div class="lv-mini">
                    <button
                      v-for="l in sortedLevels"
                      :key="l.level_code"
                      type="button"
                      class="pill"
                      :class="{ on: selectedCode === l.level_code }"
                      @click="pickLevel(l.level_code)"
                    >
                      {{ l.level_name }}
                    </button>
                  </div>
                </div>
                <div
                  v-for="c in activeCatalog()"
                  :key="c.key"
                  class="benefit-edit"
                  :class="{ on: edit.benefits[c.key]?.on }"
                >
                  <span class="lbl"
                    >{{ t(c.label) }} <small v-if="c.hint">（{{ t(c.hint) }}）</small></span
                  >
                  <label class="switch"
                    ><input v-model="edit.benefits[c.key].on" type="checkbox" /><span
                      class="slider"
                  /></label>
                  <template v-if="c.input === 'number'">
                    <input
                      v-model.number="edit.benefits[c.key].value"
                      type="number"
                      step="0.01"
                      class="val"
                      :disabled="!edit.benefits[c.key]?.on"
                    />
                    <span class="unit">{{ c.unit ? t(c.unit) : '' }}</span>
                  </template>
                  <select
                    v-else-if="c.input === 'select'"
                    v-model="edit.benefits[c.key].value"
                    :disabled="!edit.benefits[c.key]?.on"
                  >
                    <option v-for="o in c.options || []" :key="o.value" :value="o.value">
                      {{ t(o.label) }}
                    </option>
                  </select>
                </div>
                <div class="acts">
                  <button class="btn primary" type="button" @click="saveBenefits">
                    {{ t('保存权益') }}
                  </button>
                </div>
              </div>
              <div class="panel">
                <h3>{{ t('等级权益对比') }}</h3>
                <div class="table-wrap">
                  <table class="tbl">
                    <thead>
                      <tr>
                        <th>{{ t('权益') }}</th>
                        <th v-for="l in [...sortedLevels].reverse()" :key="l.level_code">
                          {{ l.level_name }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="c in activeCatalog().slice(0, 7)" :key="c.key">
                        <td>{{ t(c.label) }}</td>
                        <td v-for="l in [...sortedLevels].reverse()" :key="l.level_code">
                          {{ benefitOf(l, c.key) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </template>

            <template v-if="tab === 'rule'">
              <div class="panel">
                <h3>{{ t('升级策略') }}</h3>
                <div class="row">
                  <label class="field"
                    >{{ t('升级判定方式')
                    }}<select v-model="levelRule.upgrade_mode">
                      <option value="growth">{{ t('成长值达标即升（推荐）') }}</option>
                    </select>
                  </label>
                  <label class="field"
                    >{{ t('升级后权益生效')
                    }}<select v-model="levelRule.benefit_effective">
                      <option value="current_order">{{ t('本订单（含当前）') }}</option>
                      <option value="next_order">{{ t('下笔订单') }}</option>
                      <option value="next_day">{{ t('次日 00:00') }}</option>
                    </select>
                  </label>
                </div>
              </div>
              <div class="panel">
                <h3>{{ t('保级 / 降级策略') }}</h3>
                <div class="row3">
                  <label class="field"
                    >{{ t('降级保护期（天）')
                    }}<input v-model.number="levelRule.demote_protect_days" type="number" />
                  </label>
                  <label class="field"
                    >{{ t('未保级处理')
                    }}<select v-model="levelRule.demote_action">
                      <option value="one_level">{{ t('降一级（L5→L4）') }}</option>
                      <option value="lowest_retain">{{ t('降到最低可保级档') }}</option>
                      <option value="freeze">{{ t('保留等级但冻结权益') }}</option>
                    </select>
                  </label>
                  <label class="field switch-field"
                    >{{ t('升级通知')
                    }}<label class="switch"
                      ><input v-model="levelRule.notify_upgrade" type="checkbox" /><span
                        class="slider"
                    /></label>
                  </label>
                </div>
                <div class="acts">
                  <button class="btn primary" type="button" @click="saveRule">
                    {{ t('保存规则') }}
                  </button>
                </div>
              </div>
              <div class="panel">
                <h3>{{ t('等级到期处理预览（接下来 90 天）') }}</h3>
                <table class="tbl">
                  <thead>
                    <tr>
                      <th>{{ t('等级') }}</th>
                      <th>{{ t('客户数') }}</th>
                      <th>{{ t('已发提醒') }}</th>
                      <th>{{ t('预计保留') }}</th>
                      <th>{{ t('预计降级') }}</th>
                      <th>{{ t('预计回归') }}</th>
                      <th>{{ t('状态') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="r in expirePreview" :key="r.level_code">
                      <td>
                        <span class="lv-pill" :class="LV_CLASS[r.level_code]">{{
                          r.level_name
                        }}</span>
                      </td>
                      <td>{{ r.members }}</td>
                      <td>{{ r.reminded || '—' }}</td>
                      <td>{{ r.retain_est ?? '—' }}</td>
                      <td>{{ r.demote_est ?? '—' }}</td>
                      <td>{{ r.recover_est ?? '—' }}</td>
                      <td>
                        <span
                          class="s-badge"
                          :class="
                            r.status === 'lifelong'
                              ? 'gray'
                              : r.status === 'watch'
                                ? 'amber'
                                : 'green'
                          "
                        >
                          {{
                            r.status === 'lifelong'
                              ? t('终身')
                              : r.status === 'watch'
                                ? t('需监控')
                                : t('良好')
                          }}</span
                        >
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </div>
        </div>
      </div>

      <aside class="side">
        <div class="side-panel">
          <h3>{{ t('等级预览') }}</h3>
          <div class="preview-card" :class="selectedCode">
            <div class="lv">
              {{ selectedLevel?.level_disp || 'LEVEL' }} · {{ selectedLevel?.level_name }}
            </div>
            <div class="name">{{ selectedLevel?.level_name || '—' }}</div>
            <div class="row-mini">
              <span>{{ t('升级所需') }}</span
              ><b>{{ t('{n} 成长值', { n: fmtNum(upOf(selectedLevel)) }) }}</b>
            </div>
            <div class="row-mini">
              <span>{{ t('保级所需') }}</span
              ><b>{{ t('{n} 成长值', { n: fmtNum(retainOf(selectedLevel)) }) }}</b>
            </div>
            <div class="row-mini">
              <span>{{ t('有效期') }}</span
              ><b>{{
                selectedLevel?.valid_months
                  ? t('{n} 月', { n: selectedLevel.valid_months })
                  : t('终身')
              }}</b>
            </div>
          </div>
          <div class="ben-title">{{ t('权益清单') }}</div>
          <div class="ben-grid">
            <div
              v-for="c in activeCatalog().filter(
                (x) => (selectedLevel?.benefits || edit.benefits)?.[x.key]?.on,
              )"
              :key="c.key"
              class="ben on"
            >
              <span class="name">{{ t(c.label) }}</span>
              <span class="val">{{
                benefitOf(selectedLevel || { benefits: edit.benefits }, c.key)
              }}</span>
            </div>
            <div
              v-if="
                !activeCatalog().some(
                  (x) => (selectedLevel?.benefits || edit.benefits)?.[x.key]?.on,
                )
              "
              class="empty-hint"
            >
              {{ t('暂无启用权益') }}
            </div>
          </div>
        </div>

        <div class="side-panel">
          <h3>{{ t('规则试算') }}</h3>
          <label class="field"
            >{{ t('示例客户')
            }}<select v-model="previewCust">
              <option v-for="c in customerList" :key="c.id" :value="c.id">
                {{
                  t('{name} · {level}（{n} 分）', {
                    name: c.name,
                    level: LV_NAME[c.level] || c.level,
                    n: c.available_points ?? c.current_points,
                  })
                }}
              </option>
            </select>
          </label>
          <div class="sc-list">
            <button
              v-for="s in scenarioList"
              :key="s.key"
              type="button"
              class="scenario-btn"
              :class="{ active: previewSc === s.key }"
              @click="previewSc = s.key"
            >
              <span class="ico">{{ s.icon }}</span
              >{{ s.label }}
            </button>
          </div>
          <template v-if="preview">
            <div class="cust-line">
              {{
                t('客户：{name}（{n} 积分）', {
                  name: preview.customer?.level || preview.customer?.name,
                  n: preview.customer?.current_points,
                })
              }}
            </div>
            <div v-for="(line, i) in preview.calc_lines" :key="i" class="calc-line">
              <span class="lbl">{{ line.label || line.type }}</span>
              <span class="val" :class="(line.points || 0) >= 0 ? 'good' : 'bad'">
                <template v-if="line.detail && !line.points">{{ line.detail }}</template>
                <template v-else
                  >{{ (line.points || 0) >= 0 ? '+' : '' }}{{ fmtNum(line.points) }}</template
                >
              </span>
            </div>
            <div class="calc-final">
              <span class="lbl">{{ t('本笔预计获得') }}</span>
              <span class="val"
                >{{ preview.total_delta >= 0 ? '+' : '' }}{{ fmtNum(preview.total_delta) }}</span
              >
            </div>
            <div class="after-block">
              <div class="after-title">{{ t('积分变化后') }}</div>
              <div class="calc-line">
                <span class="lbl">{{ t('余额') }}}</span
                ><span class="val">{{ fmtNum(preview.after_balance) }}</span>
              </div>
              <div v-if="preview.growth_before != null" class="calc-line">
                <span class="lbl">{{ t('成长值') }}</span>
                <span class="val"
                  >{{ fmtNum(preview.growth_before) }} → {{ fmtNum(preview.growth_after) }}</span
                >
              </div>
              <div class="calc-line">
                <span class="lbl">{{ t('等级变化') }}</span
                ><span class="val good">→ {{ preview.expected_level_after }}</span>
              </div>
            </div>
            <div v-if="preview.warnings?.length" class="warn-box">
              ⚠ {{ preview.warnings.join(' ') }}
            </div>
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.ms {
  --brand: #005bbf;
  --soft: #eef5ff;
  --line: #c1c6d6;
  --ink2: #475569;
  --ink3: #7b8794;
  padding-bottom: 24px;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
  line-height: 1.2;
}
.actions {
  display: flex;
  gap: 8px;
}
.layout {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 16px;
}
@media (max-width: 1100px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
.kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}
.kpi {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
}
.kpi .label {
  color: var(--ink3);
  font-size: 12px;
  font-weight: 600;
}
.kpi .num {
  font-size: 22px;
  font-weight: 700;
  margin-top: 4px;
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Source Sans 3', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
}
.kpi .num .unit-zh {
  margin-left: 2px;
  font-weight: 700;
  font-size: 0.82em;
}
.tabs {
  display: flex;
  gap: 0;
  flex-wrap: wrap;
  padding: 0 8px;
  border-bottom: 1px solid var(--line);
  background: #f8fafc;
}
.tab {
  position: relative;
  flex: 1;
  min-width: 100px;
  margin-bottom: -1px;
  padding: 12px 10px 14px;
  border: none;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  font-weight: 600;
  font-size: 13px;
  color: var(--ink2);
  cursor: pointer;
  text-align: center;
  background: transparent;
  font: inherit;
  font-weight: 600;
}
.tab:hover {
  color: var(--brand);
  background: rgba(0, 91, 191, 0.04);
}
.tab.active {
  color: var(--brand);
  background: #fff;
  border-bottom-color: var(--brand);
  box-shadow: none;
}
.workspace-body {
  padding: 16px;
  background: #fff;
}
.panel {
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 0 0 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--line);
}
.panel:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}
.workspace {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 12px;
}
.panel h3 {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.row,
.row3,
.row4 {
  display: grid;
  gap: 12px;
  margin-bottom: 12px;
}
.row {
  grid-template-columns: repeat(2, 1fr);
}
.row3 {
  grid-template-columns: repeat(3, 1fr);
}
.row4 {
  grid-template-columns: repeat(4, 1fr);
}
@media (max-width: 900px) {
  .row3,
  .row4,
  .kpis {
    grid-template-columns: 1fr 1fr;
  }
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink2);
}
.field input,
.field select,
.benefit-edit select,
.benefit-edit .val,
.side-panel select {
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  font-size: 13px;
  font: inherit;
  font-weight: 500;
}
.req {
  color: #dc2626;
}
.field-block {
  margin-bottom: 12px;
}
.flabel {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink2);
  margin-bottom: 8px;
}
.lv-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}
@media (max-width: 900px) {
  .lv-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
.lv-card {
  border-radius: 10px;
  padding: 12px;
  color: #fff;
  font-weight: 700;
  cursor: pointer;
  border: 2px solid transparent;
  text-align: left;
  font: inherit;
}
.lv-card.l1 {
  background: linear-gradient(135deg, #9aa3af, #6b7280);
}
.lv-card.l2 {
  background: linear-gradient(135deg, #fbbf24, #d4a14a);
}
.lv-card.l3 {
  background: linear-gradient(135deg, #a78bfa, #7c3aed);
}
.lv-card.l4 {
  background: linear-gradient(135deg, #60a5fa, #2563eb);
}
.lv-card.l5 {
  background: linear-gradient(135deg, #1f1f29, #000);
}
.lv-card.active {
  outline: 3px solid var(--brand);
  outline-offset: 2px;
}
.lv-code {
  font-size: 11px;
  opacity: 0.85;
  letter-spacing: 0.04em;
}
.lv-name {
  font-size: 16px;
  margin: 6px 0 10px;
}
.lv-up {
  font-size: 11px;
  opacity: 0.85;
}
.lv-up b {
  font-size: 14px;
  display: block;
  margin-top: 2px;
}
.btn {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn.primary {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}
.btn.danger {
  color: #dc2626;
}
.acts {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.benefit-edit {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #f8fafc;
  margin-bottom: 8px;
}
.benefit-edit.on {
  border-style: solid;
  border-color: var(--brand);
  background: var(--soft);
}
.benefit-edit .lbl {
  flex: 1;
  font-weight: 600;
  font-size: 13px;
}
.benefit-edit .lbl small {
  color: var(--ink3);
  font-weight: 500;
}
.benefit-edit .val {
  width: 72px;
  text-align: center;
}
.unit {
  font-size: 11px;
  color: var(--ink3);
}
.switch {
  position: relative;
  display: inline-block;
  width: 38px;
  height: 22px;
  flex-shrink: 0;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: #cbd5e1;
  border-radius: 22px;
  transition: 0.2s;
}
.slider:before {
  content: '';
  position: absolute;
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background: #fff;
  border-radius: 50%;
  transition: 0.2s;
}
.switch input:checked + .slider {
  background: var(--brand);
}
.switch input:checked + .slider:before {
  transform: translateX(16px);
}
.ben-head {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.pill {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 99px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.pill.on {
  background: var(--soft);
  border-color: var(--brand);
  color: var(--brand);
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.tbl th {
  padding: 10px;
  background: #f1f5f9;
  text-align: left;
  font-weight: 700;
  color: var(--ink2);
}
.tbl td {
  padding: 10px;
  border-bottom: 1px solid #f1f5f9;
}
.table-wrap {
  overflow-x: auto;
}
.lv-pill {
  padding: 3px 10px;
  border-radius: 6px;
  font-weight: 700;
  font-size: 11px;
  display: inline-block;
}
.lv-pill.l1 {
  background: #e5e7eb;
  color: #374151;
}
.lv-pill.l2 {
  background: #fef3c7;
  color: #92400e;
}
.lv-pill.l3 {
  background: #ede9fe;
  color: #5b21b6;
}
.lv-pill.l4 {
  background: #dbeafe;
  color: #1e40af;
}
.lv-pill.l5 {
  background: #1f1f29;
  color: #fff;
}
.s-badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  border-radius: 4px;
}
.s-badge.green {
  background: #dcfce7;
  color: #166534;
}
.s-badge.amber {
  background: #fef3c7;
  color: #92400e;
}
.s-badge.gray {
  background: #e5e7eb;
  color: #374151;
}
.rc-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
@media (max-width: 900px) {
  .rc-grid {
    grid-template-columns: 1fr 1fr;
  }
}
.rc-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px;
  text-align: center;
  background: linear-gradient(135deg, #fef9e7, #fef3c7);
  cursor: pointer;
}
.rc-name {
  font-size: 11px;
  color: var(--ink3);
  font-weight: 600;
}
.amt {
  font-size: 22px;
  font-weight: 800;
  color: #b45309;
}
.gift {
  color: #d97706;
  font-size: 12px;
  margin-top: 4px;
  font-weight: 700;
}
.pct {
  font-size: 20px;
  font-weight: 800;
  color: var(--brand);
  margin-top: 4px;
}
.pts {
  margin-top: 6px;
  font-size: 11px;
  color: var(--ink3);
}
.ft {
  margin-top: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #991b1b;
}
.pay-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 10px;
}
.tag {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 99px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.tag.on {
  background: var(--soft);
  border-color: var(--brand);
  color: var(--brand);
}
.side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 12px;
  align-self: start;
  max-height: calc(100vh - 24px);
  overflow: auto;
}
.side-panel {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px;
}
.side-panel h3 {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 800;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.preview-card {
  border-radius: 10px;
  padding: 12px;
  color: #fff;
  margin-bottom: 10px;
}
.preview-card.silver {
  background: linear-gradient(135deg, #94a3b8, #64748b);
}
.preview-card.gold {
  background: linear-gradient(135deg, #fbbf24, #b45309);
}
.preview-card.platinum {
  background: linear-gradient(135deg, #a78bfa, #7c3aed);
}
.preview-card.diamond {
  background: linear-gradient(135deg, #60a5fa, #1d4ed8);
}
.preview-card.supreme {
  background: linear-gradient(135deg, #0f0f1a, #000);
}
.preview-card .name {
  font-weight: 800;
  font-size: 14px;
  margin-bottom: 6px;
}
.preview-card .lv {
  font-size: 11px;
  opacity: 0.8;
  margin-bottom: 4px;
}
.row-mini {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  margin-top: 4px;
}
.ben-title {
  font-size: 11px;
  color: var(--ink3);
  margin: 6px 0 8px;
}
.ben-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-bottom: 4px;
}
.ben {
  background: #f8fafc;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  gap: 6px;
}
.ben.on {
  background: var(--soft);
  border-color: var(--brand);
}
.ben .name {
  font-weight: 600;
  color: #15212d;
}
.ben .val {
  font-weight: 700;
  color: var(--brand);
  white-space: nowrap;
}
.empty-hint {
  font-size: 12px;
  color: var(--ink3);
  grid-column: 1 / -1;
}
.scenario-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  cursor: pointer;
  width: 100%;
  text-align: left;
  margin-bottom: 6px;
  font: inherit;
  font-weight: 600;
  color: #15212d;
}
.scenario-btn.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}
.scenario-btn .ico {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 4px;
  font-size: 11px;
}
.scenario-btn.active .ico {
  background: rgba(255, 255, 255, 0.2);
}
.cust-line {
  font-size: 11px;
  font-weight: 700;
  margin: 10px 0 8px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}
.calc-line {
  display: flex;
  justify-content: space-between;
  padding: 7px 0;
  border-bottom: 1px solid var(--line);
  font-size: 12px;
}
.calc-line .lbl {
  color: var(--ink2);
}
.calc-line .val {
  font-weight: 700;
}
.calc-line .val.good {
  color: #16a34a;
}
.calc-line .val.bad {
  color: #dc2626;
}
.calc-final {
  margin-top: 8px;
  padding: 10px;
  background: var(--soft);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 800;
}
.calc-final .lbl {
  color: var(--brand);
  font-size: 12px;
}
.calc-final .val {
  color: var(--brand);
  font-size: 18px;
}
.after-block {
  margin-top: 10px;
}
.after-title {
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 4px;
}
.warn-box {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  margin-top: 8px;
  line-height: 1.45;
}
.switch-field {
  gap: 10px;
}
.sc-list {
  margin: 8px 0;
}

/* 会员体系 AI */
.ai-block {
  margin-bottom: 12px;
}
.ai-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}
.ai-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
}
.ai-head-l {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-mark {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--brand);
  background: var(--soft);
  border: 1px solid #bfd4f5;
  border-radius: 4px;
  padding: 1px 6px;
}
.ai-run {
  border: none;
  background: var(--brand);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 14px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}
.ai-run:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.ai-wait,
.ai-idle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--ink3);
}
.ai-meta {
  font-size: 11px;
  color: var(--ink3);
  margin: 0 0 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.conf-pill {
  background: #e2e8f0;
  border-radius: 4px;
  padding: 1px 6px;
  font-weight: 700;
  color: #475569;
}
.ai-err {
  font-size: 12px;
  color: #dc2626;
  background: #fef2f2;
  border-radius: 6px;
  padding: 8px 10px;
  margin-top: 10px;
}
.ai-soft-err {
  font-size: 12px;
  color: var(--ink3);
  margin: 8px 0 0;
}
.ai-insight-body {
  margin-bottom: 12px;
}
.ai-insight-body :deep(.ai-insight) {
  display: grid;
  gap: 10px;
}
@media (min-width: 720px) {
  .ai-insight-body :deep(.ai-insight) {
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
}
.ai-insight-body :deep(.ai-insight-sec) {
  border-radius: 10px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  background: #f8fafc;
}
.ai-insight-body :deep(.ai-insight-h) {
  font-size: 12px;
  font-weight: 800;
  color: var(--brand);
  margin-bottom: 8px;
}
.ai-insight-body :deep(ul) {
  margin: 0;
  padding-left: 18px;
}
.ai-insight-body :deep(li) {
  font-size: 13px;
  line-height: 1.5;
  color: #1e293b;
  margin-bottom: 4px;
}
.dx-actions {
  margin-top: 4px;
}
.dx-actions-h {
  font-size: 12px;
  font-weight: 800;
  color: var(--ink2);
  margin-bottom: 8px;
}
.dx-action-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.dx-action-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dx-action-title {
  font-size: 13px;
  font-weight: 700;
}
.dx-action-body {
  font-size: 12px;
  color: var(--ink2);
  line-height: 1.45;
  flex: 1;
}
.dx-act {
  align-self: flex-start;
  margin-top: 4px;
  border: 1px solid #bfd4f5;
  background: var(--soft);
  color: var(--brand);
  font-size: 12px;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  white-space: normal;
  text-align: left;
  line-height: 1.3;
  max-width: 100%;
}
.dx-act:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
