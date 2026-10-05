<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * 积分规则 · 密度对齐原型（保留 PMS 蓝）
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { confidenceLabel } from '../../lib/aiConfidence'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'

const router = useRouter()
type Tab = 'get' | 'use' | 'rate' | 'exp'
const tab = ref<Tab>('get')
const saving = ref(false)
const kpi = ref<any>({})
const levels = ref<any[]>([])
const customers = ref<any[]>([])
const scenarios = ref<any[]>([])
const previewCust = ref('c_gold')
const previewSc = ref('BIRTHDAY_5X')
const preview = ref<any>(null)
const previewParams = ref<Record<string, any> | null>(null)

function pickPreviewScenario(key: string) {
  previewParams.value = null
  previewSc.value = key
}

/** 积分规则 AI · #15 #16 #17 */
type PointsAiKind = 'rate_suggest' | 'expire_wakeup' | 'scenario_nl'
type NarrativeSlot = { loading: boolean; insight: any | null; error: string }
const aiSlots = reactive<Record<PointsAiKind, NarrativeSlot>>({
  rate_suggest: { loading: false, insight: null, error: '' },
  expire_wakeup: { loading: false, insight: null, error: '' },
  scenario_nl: { loading: false, insight: null, error: '' },
})
const aiExecuting = ref<string | null>(null)
const nlQuery = ref(t('周中连住 2 晚 + 评价'))
const AI_UI: Record<
  PointsAiKind,
  { title: string; idle: string; run: string; rerun: string; wait: string }
> = {
  rate_suggest: {
    title: t('积分倍率智能建议'),
    idle: '',
    run: t('生成倍率建议'),
    rerun: t('重新建议'),
    wait: t('正在测算倍率与积分负债…'),
  },
  expire_wakeup: {
    title: t('积分失效与唤醒策略'),
    idle: '',
    run: t('生成唤醒策略'),
    rerun: t('重新生成'),
    wait: t('正在扫描高积分与将失效积分…'),
  },
  scenario_nl: {
    title: t('场景试算自然语言'),
    idle: t('用自然语言描述场景，自动映射到右侧试算'),
    run: t('理解并映射'),
    rerun: t('重新映射'),
    wait: t('正在理解场景并映射试算参数…'),
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

async function runPointsAi(kind: PointsAiKind) {
  const slot = aiSlots[kind]
  if (slot.loading) return
  slot.loading = true
  slot.error = ''
  try {
    const payload = kind === 'scenario_nl' ? { query: nlQuery.value.trim() } : {}
    slot.insight = await api.mktPointsAiNarrate(hotelStore.hotelId, kind, payload)
  } catch (e: any) {
    slot.insight = null
    slot.error = e?.message || t('生成失败')
    toast(slot.error, false)
  } finally {
    slot.loading = false
  }
}

async function runPointsAiAction(a: any) {
  if (!a || aiExecuting.value) return
  if (a.action_type === 'open_path') {
    const p = String(a.path || '/acquisition/points')
    if (p.includes('/coupons')) router.push(p)
    else if (p.includes('/members')) router.push('/acquisition/members')
    else if (p.includes('tab=exp') || a.tab === 'exp') tab.value = 'exp'
    else if (a.tab === 'rate') tab.value = 'rate'
    return
  }
  aiExecuting.value = a.id
  try {
    const res = await api.mktPointsAiExecute(hotelStore.hotelId, a)
    toast(res?.message || t('已执行'))
    const done = res?.action_type || a.action_type
    if (done === 'apply_point_rates') {
      tab.value = 'rate'
      await load()
    } else if (done === 'apply_expire_policy') {
      tab.value = 'exp'
      await load()
    } else if (done === 'create_expire_coupon') {
      if (res?.deep_link)
        router.push(
          String(res.deep_link).split('?')[0] === '/acquisition/coupons'
            ? res.deep_link
            : '/acquisition/coupons',
        )
    } else if (done === 'run_preview' && res?.preview) {
      previewCust.value = res.preview.customer_id || previewCust.value
      previewSc.value = res.preview.scenario || previewSc.value
      previewParams.value = res.preview.params || null
      if (res.preview_result?.calc_lines?.length) preview.value = res.preview_result
      else await runPreview()
    }
  } catch (e: any) {
    toast(e?.message || t('执行失败'), false)
  } finally {
    aiExecuting.value = null
  }
}

const rule = reactive({
  base_rate: 1,
  first_stay_bonus: 500,
  first_stay_enabled: true,
  night_bonus: 30,
  signin_points: 5,
  signin_streak_bonus: 30,
  review_points: 20,
  review_first_bonus: 50,
  review_photo_bonus: 40,
  referral_points: 200,
  birthday_multiplier: 5,
  holiday_multiplier: 2,
  holiday_enabled: true,
  points_per_yuan: 100,
  max_deduct_ratio: 0.3,
  min_reserve_points: 100,
  usage_channels: 'all',
  usage_scenes: ['order_pay', 'room_upgrade', 'gift'] as string[],
  level_multipliers: {} as Record<string, number>,
  birthday_bonus_by_level: {} as Record<string, number>,
  holiday_bonus_by_level: {} as Record<string, number>,
  upgrade_double_enabled: false,
  expire_after_days: 365,
  expiry_remind_days: [30, 7, 1] as number[],
  frozen_before_days: 7,
  year_end_clear: false,
  daily_cap: 50000,
  single_order_cap: 10000,
  single_customer_cap: 1000000,
  scope_note: t('积分全渠道累计；使用范围可配置为前台 / 前台+企微H5 / 全渠道。'),
})

const LEVEL_CODES = ['silver', 'gold', 'platinum', 'diamond', 'supreme']
const LEVEL_NAMES: Record<string, string> = {
  silver: t('银卡'),
  gold: t('金卡'),
  platinum: t('白金卡'),
  diamond: t('钻石卡'),
  supreme: t('至尊卡'),
}

const scenarioList = computed(() => scenarios.value || []) // 无数据 → 空数组（无 hardcode 兜底）
const customerList = computed(() => customers.value || []) // 无数据 → 空数组（无 hardcode 兜底）

const displayKpi = computed(() => {
  // 无数据时返 0 fallback（数字层面，不硬编码任何具体值）
  const k = kpi.value || {}
  return {
    total_issued: Number(k.total_issued || 0),
    month_earn: Number(k.month_earn || 0),
    month_use: Number(k.month_use || 0),
    expire_soon: Number(k.expire_soon || 0),
  }
})

function fmtK(n: number) {
  const v = Number(n || 0)
  if (v >= 1000) return `${(v / 1000).toFixed(v % 1000 === 0 || v >= 10000 ? 0 : 1)}K`
  return String(v)
}
function fmtNum(n: number) {
  return Number(n || 0).toLocaleString('zh-CN')
}

function localPreview(): any {
  const cust = customerList.value.find((c) => c.id === previewCust.value) || customerList.value[0]
  const sc = scenarioList.value.find((s) => s.key === previewSc.value) || scenarioList.value[0]
  // 无场景时返空预览（前端可显示「暂无场景」）
  if (!sc || !cust) {
    return {
      scenario_label: sc?.label || '',
      customer: { name: cust?.name || '', level: '', current_points: cust?.available_points || 0 },
      calc_lines: [],
      total_delta: 0,
      after_balance: cust?.available_points || 0,
      redeem_yuan_est: 0,
      expected_level: '',
      warnings: [t('请先在营销自动化中配置场景')],
      timeline: [],
    }
  }
  const params = { ...(sc?.params || {}) }
  const level = cust?.level || 'gold'
  const levelM = Number(rule.level_multipliers[level] ?? 1.5)
  const bdayM = Number(rule.birthday_bonus_by_level[level] ?? 8)
  const holM = Number(rule.holiday_bonus_by_level[level] ?? 3)
  const amount = Number(params.amount || 0)
  const nights = Number(params.nights || 0)
  const lines: any[] = []
  let total = 0
  const warnings: string[] = []
  const timeline: any[] = []

  if (previewSc.value === 'REFUND') {
    const delta = -Math.round(Number(params.orig_points || 1500) * 0.67)
    lines.push({ label: t('退款冲销'), points: delta })
    total = delta
    timeline.push({
      ts: t('即时'),
      text: t('退款冲销 {n} 积分', { n: Math.abs(delta) }),
    })
  } else if (previewSc.value === 'EXPIRE') {
    const delta = -Number(params.expire_points || 300)
    lines.push({ label: t('积分失效'), points: delta })
    total = delta
    timeline.push({
      ts: t('02:00 定时'),
      text: t('失效扣减 {n} 积分', { n: Math.abs(delta) }),
    })
  } else if (previewSc.value === 'REVIEW_GOOD') {
    let pts = Number(rule.review_points || 20)
    if (params.is_first_review) pts += Number(rule.review_first_bonus || 50)
    lines.push({ label: t('评价奖励'), points: pts })
    total = pts
    timeline.push({ ts: t('评价提交'), text: t('好评奖励 +{n}', { n: pts }) })
  } else {
    if (amount > 0) {
      const basePts = Math.round(amount * Number(rule.base_rate || 1) * levelM)
      lines.push({ label: t('消费基础 × 等级{m}X', { m: levelM }), points: basePts })
      total += basePts
      if (params.is_birthday_month) {
        const b = Math.round(amount * bdayM)
        lines.push({ label: t('生日倍率 +{m}', { m: bdayM }), points: b })
        total += b
        warnings.push(t('生日倍率已触发'))
      }
      if (params.is_holiday && rule.holiday_enabled) {
        const h = Math.round(amount * holM)
        lines.push({ label: t('节假日倍率 +{m}', { m: holM }), points: h })
        total += h
      }
    }
    if (nights > 0) {
      const np = nights * Number(rule.night_bonus || 30)
      lines.push({ label: t('入住 {n} 晚加成', { n: nights }), points: np })
      total += np
    }
    const capped = Math.min(
      total,
      Number(rule.single_order_cap || 10000),
      Number(rule.daily_cap || 50000),
    )
    if (capped < total) {
      lines.push({ label: t('上限钳制'), points: capped - total })
      warnings.push(t('已按单笔上限钳制至 {n}', { n: capped }))
      total = capped
    }
    timeline.push({ ts: t('下单完成'), text: t('获取 +{n} 积分', { n: total }) })
    if (params.is_birthday_month) timeline.push({ ts: t('规则引擎'), text: t('生日月倍率叠加') })
  }

  const ppy = Number(rule.points_per_yuan || 100)
  const maxRatio = Number(rule.max_deduct_ratio || 0.3)
  const redeem = amount > 0 && total > 0 ? Math.min(total / ppy, amount * maxRatio) : 0

  return {
    scenario_label: sc?.label,
    customer: {
      name: cust?.name,
      level: LEVEL_NAMES[level] || level,
      current_points: cust?.available_points || 0,
    },
    calc_lines: lines,
    total_delta: total,
    after_balance: Number(cust?.available_points || 0) + total,
    redeem_yuan_est: Math.round(redeem * 100) / 100,
    expected_level_after: LEVEL_NAMES[level] || level,
    warnings,
    timeline,
  }
}

async function runPreview() {
  try {
    const r = await api.mktMemberPointPreview(hotelStore.hotelId, {
      customer_id: previewCust.value,
      scenario: previewSc.value,
      params: previewParams.value || undefined,
    })
    preview.value = r?.calc_lines?.length ? r : localPreview()
  } catch {
    preview.value = localPreview()
  }
}

async function load() {
  try {
    const r = await api.mktMemberPointRule(hotelStore.hotelId)
    kpi.value = r.kpi || {}
    levels.value = r.levels || []
    customers.value = r.customers || []
    scenarios.value = (r.scenarios || []).filter(
      (s: any) => !String(s.key || '').startsWith('RECHARGE'),
    )
    const src = r.rule || {}
    Object.assign(rule, src)
    if (typeof rule.max_deduct_ratio === 'number' && rule.max_deduct_ratio > 1) {
      rule.max_deduct_ratio = rule.max_deduct_ratio / 100
    }
  } catch {
    kpi.value = {} // 加载失败 → 0 兜底（前端 displayKpi 处理）
  }
  rule.level_multipliers = {
    silver: 1,
    gold: 1.5,
    platinum: 2,
    diamond: 2.5,
    supreme: 3,
    ...(rule.level_multipliers || {}),
  }
  rule.birthday_bonus_by_level = {
    silver: 5,
    gold: 8,
    platinum: 10,
    diamond: 15,
    supreme: 20,
    ...(rule.birthday_bonus_by_level || {}),
  }
  rule.holiday_bonus_by_level = {
    silver: 2,
    gold: 3,
    platinum: 5,
    diamond: 8,
    supreme: 10,
    ...(rule.holiday_bonus_by_level || {}),
  }
  if (!Array.isArray(rule.usage_scenes)) rule.usage_scenes = ['order_pay', 'room_upgrade']
  if (!Array.isArray(rule.expiry_remind_days)) rule.expiry_remind_days = [30, 7, 1]
  if (rule.night_bonus == null) rule.night_bonus = 30
  await runPreview()
}

async function save() {
  saving.value = true
  try {
    await api.mktMemberPointRuleSave(hotelStore.hotelId, { rule: { ...rule } })
    toast(t('积分规则已保存并下发'))
    await load()
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    saving.value = false
  }
}

function toggleScene(s: string) {
  const i = rule.usage_scenes.indexOf(s)
  if (i >= 0) rule.usage_scenes.splice(i, 1)
  else rule.usage_scenes.push(s)
}

const maxRatioPct = computed({
  get: () => Math.round(Number(rule.max_deduct_ratio || 0) * 100),
  set: (v: number) => {
    rule.max_deduct_ratio = Number(v || 0) / 100
  },
})

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch([previewCust, previewSc], runPreview)
</script>

<template>
  <div class="pts">
    <div class="head">
      <h1>{{ t('积分规则') }}</h1>
    </div>

    <div class="layout">
      <div class="main">
        <div class="kpis">
          <div class="kpi">
            <div class="label">{{ t('积分总发行') }}</div>
            <div class="num">{{ fmtK(displayKpi.total_issued) }}</div>
          </div>
          <div class="kpi">
            <div class="label">{{ t('本月获取') }}</div>
            <div class="num">{{ fmtK(displayKpi.month_earn) }}</div>
          </div>
          <div class="kpi">
            <div class="label">{{ t('本月使用') }}</div>
            <div class="num">{{ fmtK(displayKpi.month_use) }}</div>
          </div>
          <div class="kpi">
            <div class="label">{{ t('30 日将失效') }}</div>
            <div class="num warn">{{ fmtK(displayKpi.expire_soon) }}</div>
          </div>
        </div>

        <div class="workspace">
          <div class="tabs" role="tablist">
            <button
              type="button"
              role="tab"
              class="tab"
              :class="{ active: tab === 'get' }"
              :aria-selected="tab === 'get'"
              @click="tab = 'get'"
            >
              {{ t('积分获取') }}
            </button>
            <button
              type="button"
              role="tab"
              class="tab"
              :class="{ active: tab === 'use' }"
              :aria-selected="tab === 'use'"
              @click="tab = 'use'"
            >
              {{ t('积分使用') }}
            </button>
            <button
              type="button"
              role="tab"
              class="tab"
              :class="{ active: tab === 'rate' }"
              :aria-selected="tab === 'rate'"
              @click="tab = 'rate'"
            >
              {{ t('积分倍率') }}
            </button>
            <button
              type="button"
              role="tab"
              class="tab"
              :class="{ active: tab === 'exp' }"
              :aria-selected="tab === 'exp'"
              @click="tab = 'exp'"
            >
              {{ t('积分失效') }}
            </button>
          </div>

          <div class="workspace-body">
            <template v-if="tab === 'get'">
              <div class="panel">
                <h3>{{ t('消费基础倍率') }}</h3>
                <div class="row3">
                  <label class="field"
                    >{{ t('消费基础倍率') }}
                    <div class="inline">
                      <input v-model.number="rule.base_rate" type="number" step="0.1" /><span
                        class="unit"
                        >{{ t('分/元') }}</span
                      >
                    </div>
                  </label>
                  <label class="field"
                    >{{ t('首住加成') }}
                    <div class="inline">
                      <label class="switch"
                        ><input v-model="rule.first_stay_enabled" type="checkbox" /><span
                          class="slider"
                      /></label>
                      <input
                        v-model.number="rule.first_stay_bonus"
                        type="number"
                        :disabled="!rule.first_stay_enabled"
                      /><span class="unit">{{ t('积分') }}</span>
                    </div>
                  </label>
                  <label class="field"
                    >{{ t('入住夜奖励') }}
                    <div class="inline">
                      <input v-model.number="rule.night_bonus" type="number" /><span class="unit">{{
                        t('分/晚')
                      }}</span>
                    </div>
                  </label>
                </div>
              </div>
              <div class="panel">
                <h3>{{ t('行为奖励') }}</h3>
                <div class="row4">
                  <label class="field"
                    >{{ t('签到') }}
                    <div class="inline">
                      <input v-model.number="rule.signin_points" type="number" /><span
                        class="unit"
                        >{{ t('分/天') }}</span
                      >
                    </div>
                  </label>
                  <label class="field"
                    >{{ t('评价') }}
                    <div class="inline">
                      <input v-model.number="rule.review_points" type="number" /><span
                        class="unit"
                        >{{ t('分/条') }}</span
                      >
                    </div>
                  </label>
                  <label class="field"
                    >{{ t('追评（图文）') }}
                    <div class="inline">
                      <input v-model.number="rule.review_photo_bonus" type="number" /><span
                        class="unit"
                        >{{ t('分/次') }}</span
                      >
                    </div>
                  </label>
                  <label class="field"
                    >{{ t('推荐注册') }}
                    <div class="inline">
                      <input v-model.number="rule.referral_points" type="number" /><span
                        class="unit"
                        >{{ t('分/人') }}</span
                      >
                    </div>
                  </label>
                </div>
              </div>
              <div class="panel">
                <h3>{{ t('获取上限') }}</h3>
                <div class="row">
                  <label class="field"
                    >{{ t('单笔订单积分上限') }}
                    <div class="inline">
                      <input v-model.number="rule.single_order_cap" type="number" /><span
                        class="unit"
                        >{{ t('积分') }}</span
                      >
                    </div>
                  </label>
                  <label class="field"
                    >{{ t('每日获取上限') }}
                    <div class="inline">
                      <input v-model.number="rule.daily_cap" type="number" /><span class="unit">{{
                        t('积分')
                      }}</span>
                    </div>
                  </label>
                  <label class="field"
                    >{{ t('单客户持有上限') }}
                    <div class="inline">
                      <input v-model.number="rule.single_customer_cap" type="number" /><span
                        class="unit"
                        >{{ t('积分') }}</span
                      >
                    </div>
                  </label>
                  <label class="field switch-field"
                    >{{ t('节假日倍率是否启用') }}
                    <label class="switch"
                      ><input v-model="rule.holiday_enabled" type="checkbox" /><span class="slider"
                    /></label>
                  </label>
                </div>
              </div>
              <div class="panel">
                <h3>{{ t('适用范围说明') }}</h3>
                <textarea v-model="rule.scope_note" rows="2" class="ta" />
              </div>
            </template>

            <template v-if="tab === 'use'">
              <div class="panel">
                <h3>{{ t('兑换方向') }}</h3>
                <div class="row3">
                  <label class="field"
                    >{{ t('积分兑人民币 (points_per_yuan)') }}
                    <div class="inline">
                      <input v-model.number="rule.points_per_yuan" type="number" /><span
                        class="unit"
                        >{{ t('积分抵 ¥1') }}</span
                      >
                    </div>
                  </label>
                  <label class="field"
                    >{{ t('单笔订单最多抵扣') }}
                    <div class="inline">
                      <input v-model.number="maxRatioPct" type="number" min="0" max="100" /><span
                        class="unit"
                        >%</span
                      >
                    </div>
                  </label>
                  <label class="field"
                    >{{ t('抵扣后最低保留积分') }}
                    <div class="inline">
                      <input v-model.number="rule.min_reserve_points" type="number" /><span
                        class="unit"
                        >{{ t('积分') }}</span
                      >
                    </div>
                  </label>
                </div>
              </div>
              <div class="panel">
                <h3>{{ t('使用范围') }}</h3>
                <div class="scope-grid use-grid">
                  <button
                    type="button"
                    class="scope-card"
                    :class="{ on: rule.usage_scenes.includes('order_pay') }"
                    @click="toggleScene('order_pay')"
                  >
                    <div class="name">{{ t('抵扣房费') }}</div>
                    <div class="desc">{{ t('按 points_per_yuan 直接抵房费') }}</div>
                  </button>
                  <button
                    type="button"
                    class="scope-card"
                    :class="{ on: rule.usage_scenes.includes('room_upgrade') }"
                    @click="toggleScene('room_upgrade')"
                  >
                    <div class="name">{{ t('兑换升房') }}</div>
                    <div class="desc">{{ t('积分换豪华房升级券') }}</div>
                  </button>
                  <button
                    type="button"
                    class="scope-card"
                    :class="{ on: rule.usage_scenes.includes('gift') }"
                    @click="toggleScene('gift')"
                  >
                    <div class="name">{{ t('兑换礼品') }}</div>
                    <div class="desc">{{ t('对接商城 / 实物兑换') }}</div>
                  </button>
                  <button
                    type="button"
                    class="scope-card"
                    :class="{ on: rule.usage_scenes.includes('cash_voucher') }"
                    @click="toggleScene('cash_voucher')"
                  >
                    <div class="name">{{ t('兑换现金券') }}</div>
                    <div class="desc">{{ t('→ 生成现金券') }}</div>
                  </button>
                </div>
              </div>
              <div class="panel">
                <h3>{{ t('使用渠道') }}</h3>
                <div class="scope-grid">
                  <button
                    type="button"
                    class="scope-card"
                    :class="{ on: rule.usage_channels === 'front_desk' }"
                    @click="rule.usage_channels = 'front_desk'"
                  >
                    <div class="name">{{ t('仅前台下单') }}</div>
                    <div class="desc">{{ t('收银台抵扣') }}</div>
                  </button>
                  <button
                    type="button"
                    class="scope-card"
                    :class="{ on: rule.usage_channels === 'front_wecom' }"
                    @click="rule.usage_channels = 'front_wecom'"
                  >
                    <div class="name">{{ t('前台 + 企微 H5') }}</div>
                    <div class="desc">{{ t('不含小程序') }}</div>
                  </button>
                  <button
                    type="button"
                    class="scope-card"
                    :class="{ on: rule.usage_channels === 'all' }"
                    @click="rule.usage_channels = 'all'"
                  >
                    <div class="name">{{ t('全渠道') }}</div>
                    <div class="desc">{{ t('PMS + 企微 + 小程序') }}</div>
                  </button>
                </div>
              </div>
            </template>

            <template v-if="tab === 'rate'">
              <section v-if="commercialEnabled()" class="ai-block panel">
                <div class="ai-head">
                  <div class="ai-head-l">
                    <h3>{{ AI_UI.rate_suggest.title }}</h3>
                    <span class="ai-mark">AI</span>
                  </div>
                  <button
                    type="button"
                    class="ai-run"
                    :disabled="aiSlots.rate_suggest.loading"
                    @click="runPointsAi('rate_suggest')"
                  >
                    {{
                      aiSlots.rate_suggest.loading
                        ? t('生成中…')
                        : aiSlots.rate_suggest.insight
                          ? AI_UI.rate_suggest.rerun
                          : AI_UI.rate_suggest.run
                    }}
                  </button>
                </div>
                <template v-if="aiSlots.rate_suggest.loading"
                  ><p class="ai-wait">{{ AI_UI.rate_suggest.wait }}</p></template
                >
                <template v-else-if="aiSlots.rate_suggest.insight">
                  <p class="ai-meta">
                    <span>{{ aiSourceLabel(aiSlots.rate_suggest.insight) }}</span>
                    <span
                      v-if="formatAiModelMeta(aiSlots.rate_suggest.insight)"
                      class="conf-pill"
                      >{{ formatAiModelMeta(aiSlots.rate_suggest.insight) }}</span
                    >
                    <span v-if="aiSlots.rate_suggest.insight.confidence" class="conf-pill">{{
                      confText(aiSlots.rate_suggest.insight.confidence)
                    }}</span>
                    <span v-if="aiSlots.rate_suggest.insight.confidence_note">
                      · {{ aiSlots.rate_suggest.insight.confidence_note }}</span
                    >
                  </p>
                  <div class="ai-insight-body">
                    <div v-html="aiSlots.rate_suggest.insight.narrative_html" />
                  </div>
                  <div v-if="aiSlots.rate_suggest.insight.actions?.length" class="dx-actions">
                    <div class="dx-actions-h">{{ t('可执行操作') }}</div>
                    <div class="dx-action-list">
                      <article
                        v-for="a in aiSlots.rate_suggest.insight.actions"
                        :key="a.id"
                        class="dx-action-card"
                      >
                        <div class="dx-action-title">{{ a.title }}</div>
                        <div v-if="a.body" class="dx-action-body">{{ a.body }}</div>
                        <button
                          type="button"
                          class="dx-act"
                          :disabled="!!aiExecuting"
                          @click="runPointsAiAction(a)"
                        >
                          {{ aiExecuting === a.id ? t('执行中…') : a.action_label || t('执行') }}
                        </button>
                      </article>
                    </div>
                  </div>
                  <p v-if="aiSlots.rate_suggest.insight.llm_error" class="ai-soft-err">
                    {{ t(aiSlots.rate_suggest.insight.llm_error) }}
                  </p>
                </template>
                <div v-else-if="AI_UI.rate_suggest.idle" class="ai-idle">
                  {{ AI_UI.rate_suggest.idle }}
                </div>
                <p v-if="aiSlots.rate_suggest.error" class="ai-err">
                  {{ aiSlots.rate_suggest.error }}
                </p>
              </section>

              <div class="panel">
                <h3>{{ t('等级倍率') }}</h3>
                <table class="tbl">
                  <thead>
                    <tr>
                      <th>{{ t('等级') }}</th>
                      <th>{{ t('基础倍率') }}</th>
                      <th>{{ t('生日倍率（额外）') }}</th>
                      <th>{{ t('节假日倍率（额外）') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="code in LEVEL_CODES" :key="code">
                      <td>
                        <span class="lv-pill" :class="'l' + (LEVEL_CODES.indexOf(code) + 1)">{{
                          LEVEL_NAMES[code]
                        }}</span>
                      </td>
                      <td>
                        <input
                          v-model.number="rule.level_multipliers[code]"
                          type="number"
                          step="0.1"
                          class="mini"
                        />
                        X
                      </td>
                      <td>
                        <input
                          v-model.number="rule.birthday_bonus_by_level[code]"
                          type="number"
                          step="0.1"
                          class="mini"
                        />{{ t('分/元') }}
                      </td>
                      <td>
                        <input
                          v-model.number="rule.holiday_bonus_by_level[code]"
                          type="number"
                          step="0.1"
                          class="mini"
                        />{{ t('分/元') }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="panel">
                <h3>{{ t('特殊倍率开关') }}</h3>
                <div class="row3">
                  <label class="field switch-field"
                    >{{ t('生日倍率') }}
                    <label class="switch"
                      ><input type="checkbox" checked disabled /><span class="slider"
                    /></label>
                  </label>
                  <label class="field switch-field"
                    >{{ t('节假日倍率') }}
                    <label class="switch"
                      ><input v-model="rule.holiday_enabled" type="checkbox" /><span class="slider"
                    /></label>
                  </label>
                  <label class="field switch-field"
                    >{{ t('升级双倍') }}
                    <label class="switch"
                      ><input v-model="rule.upgrade_double_enabled" type="checkbox" /><span
                        class="slider"
                    /></label>
                  </label>
                </div>
              </div>
            </template>

            <template v-if="tab === 'exp'">
              <section v-if="commercialEnabled()" class="ai-block panel">
                <div class="ai-head">
                  <div class="ai-head-l">
                    <h3>{{ AI_UI.expire_wakeup.title }}</h3>
                    <span class="ai-mark">AI</span>
                  </div>
                  <button
                    type="button"
                    class="ai-run"
                    :disabled="aiSlots.expire_wakeup.loading"
                    @click="runPointsAi('expire_wakeup')"
                  >
                    {{
                      aiSlots.expire_wakeup.loading
                        ? t('生成中…')
                        : aiSlots.expire_wakeup.insight
                          ? AI_UI.expire_wakeup.rerun
                          : AI_UI.expire_wakeup.run
                    }}
                  </button>
                </div>
                <template v-if="aiSlots.expire_wakeup.loading"
                  ><p class="ai-wait">{{ AI_UI.expire_wakeup.wait }}</p></template
                >
                <template v-else-if="aiSlots.expire_wakeup.insight">
                  <p class="ai-meta">
                    <span>{{ aiSourceLabel(aiSlots.expire_wakeup.insight) }}</span>
                    <span
                      v-if="formatAiModelMeta(aiSlots.expire_wakeup.insight)"
                      class="conf-pill"
                      >{{ formatAiModelMeta(aiSlots.expire_wakeup.insight) }}</span
                    >
                    <span v-if="aiSlots.expire_wakeup.insight.confidence" class="conf-pill">{{
                      confText(aiSlots.expire_wakeup.insight.confidence)
                    }}</span>
                    <span v-if="aiSlots.expire_wakeup.insight.confidence_note">
                      · {{ aiSlots.expire_wakeup.insight.confidence_note }}</span
                    >
                  </p>
                  <div class="ai-insight-body">
                    <div v-html="aiSlots.expire_wakeup.insight.narrative_html" />
                  </div>
                  <div v-if="aiSlots.expire_wakeup.insight.actions?.length" class="dx-actions">
                    <div class="dx-actions-h">{{ t('可执行操作') }}</div>
                    <div class="dx-action-list">
                      <article
                        v-for="a in aiSlots.expire_wakeup.insight.actions"
                        :key="a.id"
                        class="dx-action-card"
                      >
                        <div class="dx-action-title">{{ a.title }}</div>
                        <div v-if="a.body" class="dx-action-body">{{ a.body }}</div>
                        <button
                          type="button"
                          class="dx-act"
                          :disabled="!!aiExecuting"
                          @click="runPointsAiAction(a)"
                        >
                          {{ aiExecuting === a.id ? t('执行中…') : a.action_label || t('执行') }}
                        </button>
                      </article>
                    </div>
                  </div>
                  <p v-if="aiSlots.expire_wakeup.insight.llm_error" class="ai-soft-err">
                    {{ t(aiSlots.expire_wakeup.insight.llm_error) }}
                  </p>
                </template>
                <div v-else-if="AI_UI.expire_wakeup.idle" class="ai-idle">
                  {{ AI_UI.expire_wakeup.idle }}
                </div>
                <p v-if="aiSlots.expire_wakeup.error" class="ai-err">
                  {{ aiSlots.expire_wakeup.error }}
                </p>
              </section>

              <div class="panel">
                <h3>{{ t('失效规则') }}</h3>
                <div class="row3">
                  <label class="field"
                    >{{ t('有效天数') }}
                    <div class="inline">
                      <input v-model.number="rule.expire_after_days" type="number" /><span
                        class="unit"
                        >{{ t('天') }}</span
                      >
                    </div>
                  </label>
                  <label class="field"
                    >{{ t('提前冻结') }}
                    <div class="inline">
                      <input v-model.number="rule.frozen_before_days" type="number" /><span
                        class="unit"
                        >{{ t('天') }}</span
                      >
                    </div>
                  </label>
                  <label class="field"
                    >{{ t('提前提醒') }}
                    <div class="inline remind">
                      <input v-model.number="rule.expiry_remind_days[0]" type="number" />
                      <span>+</span>
                      <input v-model.number="rule.expiry_remind_days[1]" type="number" />
                      <span>+</span>
                      <input v-model.number="rule.expiry_remind_days[2]" type="number" />
                    </div>
                  </label>
                </div>
              </div>
              <div class="panel">
                <h3>{{ t('每日失效任务') }}</h3>
                <div class="pipeline">
                  <div><span class="ts">[02:00:00]</span>{{ t('扫描即将失效的流水') }}</div>
                  <div>
                    <span class="ts">[02:00:00]</span>{{ t('命中约') }}
                    <b>{{ fmtK(displayKpi.expire_soon) }}</b
                    >{{ t('分 · 写入冻结标记') }}
                  </div>
                  <div>
                    <span class="ts">[02:00:30]</span
                    >{{ t('通知营销自动化 → 推送「积分失效提醒」') }}
                  </div>
                  <div>
                    <span class="ts">[02:00:45]</span> <span class="ok">{{ t('完成') }}</span>
                  </div>
                </div>
                <div class="expire-meta">{{ t('下一次失效扫描') }}</div>
                <div class="expire-bar"><div class="fill" style="width: 42%" /></div>
              </div>
              <div class="panel">
                <h3>{{ t('年末清零') }}</h3>
                <label class="field switch-field"
                  >{{ t('启用年末清零') }}
                  <label class="switch"
                    ><input v-model="rule.year_end_clear" type="checkbox" /><span class="slider"
                  /></label>
                </label>
              </div>
            </template>

            <div class="foot-acts">
              <button class="btn primary" type="button" :disabled="saving" @click="save">
                {{ t('保存并下发') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <aside class="side">
        <div v-if="commercialEnabled()" class="side-panel ai-block">
          <div class="ai-head">
            <div class="ai-head-l">
              <h3>{{ AI_UI.scenario_nl.title }}</h3>
              <span class="ai-mark">AI</span>
            </div>
            <button
              type="button"
              class="ai-run"
              :disabled="aiSlots.scenario_nl.loading"
              @click="runPointsAi('scenario_nl')"
            >
              {{
                aiSlots.scenario_nl.loading
                  ? t('映射中…')
                  : aiSlots.scenario_nl.insight
                    ? AI_UI.scenario_nl.rerun
                    : AI_UI.scenario_nl.run
              }}
            </button>
          </div>
          <div class="ai-inputs">
            <label>{{ t('场景描述') }}</label>
            <textarea
              v-model="nlQuery"
              rows="2"
              class="ta"
              :placeholder="t('例：周中连住 2 晚 + 评价')"
            />
          </div>
          <template v-if="aiSlots.scenario_nl.loading"
            ><p class="ai-wait">{{ AI_UI.scenario_nl.wait }}</p></template
          >
          <template v-else-if="aiSlots.scenario_nl.insight">
            <p class="ai-meta">
              <span>{{ aiSourceLabel(aiSlots.scenario_nl.insight) }}</span>
              <span v-if="formatAiModelMeta(aiSlots.scenario_nl.insight)" class="conf-pill">{{
                formatAiModelMeta(aiSlots.scenario_nl.insight)
              }}</span>
              <span v-if="aiSlots.scenario_nl.insight.confidence" class="conf-pill">{{
                confText(aiSlots.scenario_nl.insight.confidence)
              }}</span>
            </p>
            <div class="ai-insight-body">
              <div v-html="aiSlots.scenario_nl.insight.narrative_html" />
            </div>
            <div v-if="aiSlots.scenario_nl.insight.actions?.length" class="dx-actions">
              <div class="dx-actions-h">{{ t('可执行操作') }}</div>
              <div class="dx-action-list">
                <article
                  v-for="a in aiSlots.scenario_nl.insight.actions"
                  :key="a.id"
                  class="dx-action-card"
                >
                  <div class="dx-action-title">{{ a.title }}</div>
                  <div v-if="a.body" class="dx-action-body">{{ a.body }}</div>
                  <button
                    type="button"
                    class="dx-act"
                    :disabled="!!aiExecuting"
                    @click="runPointsAiAction(a)"
                  >
                    {{ aiExecuting === a.id ? t('执行中…') : a.action_label || t('执行') }}
                  </button>
                </article>
              </div>
            </div>
          </template>
          <div v-else class="ai-idle">{{ AI_UI.scenario_nl.idle }}</div>
          <p v-if="aiSlots.scenario_nl.error" class="ai-err">{{ aiSlots.scenario_nl.error }}</p>
        </div>

        <div class="side-panel">
          <h3>{{ t('规则试算') }}</h3>
          <label class="field"
            >{{ t('客户') }}
            <select v-model="previewCust">
              <option v-for="c in customerList" :key="c.id" :value="c.id">
                {{
                  t('{name}（{level} · {n}分）', {
                    name: c.name,
                    level: LEVEL_NAMES[c.level] || c.level,
                    n: c.available_points,
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
              @click="pickPreviewScenario(s.key)"
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
              <span class="val" :class="(line.points || 0) >= 0 ? 'good' : 'bad'"
                >{{ (line.points || 0) >= 0 ? '+' : '' }}{{ fmtNum(line.points) }}</span
              >
            </div>
            <div class="calc-final">
              <span class="lbl">{{ t('合计变化') }}</span>
              <span class="val"
                >{{ preview.total_delta >= 0 ? '+' : '' }}{{ fmtNum(preview.total_delta) }}</span
              >
            </div>
            <div class="calc-line">
              <span class="lbl">{{ t('试算后余额') }}</span
              ><span class="val">{{ fmtNum(preview.after_balance) }}</span>
            </div>
            <div class="calc-line">
              <span class="lbl">{{ t('可抵房费约') }}</span
              ><span class="val">¥ {{ preview.redeem_yuan_est || 0 }}</span>
            </div>
            <div class="calc-line">
              <span class="lbl">{{ t('预期等级') }}</span
              ><span class="val">{{ preview.expected_level_after }}</span>
            </div>
            <div v-if="preview.timeline?.length" class="timeline">
              <div v-for="(item, i) in preview.timeline" :key="i" class="tl-item">
                <div class="ts">{{ item.ts }}</div>
                <div class="txt">{{ item.text }}</div>
              </div>
            </div>
            <div v-if="preview.warnings?.length" class="warn-box">
              ⚠ {{ preview.warnings.join('；') }}
            </div>
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.pts {
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
  grid-template-columns: repeat(4, 1fr);
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
.kpi .num.warn {
  color: #b91c1c;
}
.workspace {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 12px;
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
  min-width: 120px;
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
.panel:last-of-type {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}
.panel h3 {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 800;
}
.foot-acts {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
  padding-top: 4px;
}
.row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
.row3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
.row4 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
@media (max-width: 900px) {
  .row,
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
.ta,
.mini {
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  font-size: 13px;
  font: inherit;
  font-weight: 500;
}
.mini {
  width: 80px;
}
.inline {
  display: flex;
  gap: 8px;
  align-items: center;
}
.inline.remind input {
  width: 56px;
}
.unit {
  font-size: 11px;
  color: var(--ink3);
  white-space: nowrap;
}
.ta {
  width: 100%;
  resize: vertical;
}
.scope-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.use-grid {
  grid-template-columns: repeat(2, 1fr);
}
.scope-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
  text-align: left;
  cursor: pointer;
  background: #fff;
  font: inherit;
}
.scope-card.on {
  border-color: var(--brand);
  background: var(--soft);
}
.scope-card .name {
  font-weight: 700;
  font-size: 13px;
}
.scope-card .desc {
  font-size: 11px;
  color: var(--ink3);
  margin-top: 2px;
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
}
.tbl td {
  padding: 10px;
  border-bottom: 1px solid #f1f5f9;
}
.lv-pill {
  padding: 3px 10px;
  border-radius: 6px;
  font-weight: 700;
  font-size: 11px;
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
.switch-field {
  gap: 10px;
}
.pipeline {
  background: #f8fafc;
  border-radius: 10px;
  padding: 14px;
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Source Sans 3', system-ui, sans-serif;
  font-size: 13px;
  line-height: 1.7;
  color: #1e293b;
}
.pipeline .ts {
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
  font-family: inherit;
}
.pipeline .ok {
  color: #16a34a;
  font-weight: 700;
}
.expire-meta {
  margin-top: 14px;
  font-weight: 700;
  font-size: 13px;
}
.expire-bar {
  height: 8px;
  background: #f1f5f9;
  border-radius: 99px;
  overflow: hidden;
  margin-top: 6px;
}
.expire-bar .fill {
  height: 100%;
  background: linear-gradient(90deg, #60a5fa, #005bbf);
}
.side {
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
}
.scenario-btn.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}
.scenario-btn .ico {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 4px;
  font-size: 11px;
  color: var(--brand);
}
.scenario-btn.active .ico {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
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
.calc-line .val.good {
  color: #16a34a;
  font-weight: 700;
}
.calc-line .val.bad {
  color: #dc2626;
  font-weight: 700;
}
.calc-final {
  margin-top: 8px;
  padding: 10px;
  background: var(--soft);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  font-weight: 800;
}
.calc-final .val {
  color: var(--brand);
  font-size: 18px;
}
.warn-box {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  margin-top: 8px;
}
.timeline {
  position: relative;
  padding-left: 20px;
  margin-top: 12px;
}
.timeline:before {
  content: '';
  position: absolute;
  left: 6px;
  top: 4px;
  bottom: 4px;
  width: 2px;
  background: #e2e8f0;
}
.tl-item {
  position: relative;
  padding: 6px 0;
}
.tl-item:before {
  content: '';
  position: absolute;
  left: -17px;
  top: 10px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--brand);
}
.tl-item .ts {
  font-size: 11px;
  color: var(--ink3);
}
.tl-item .txt {
  font-size: 12px;
  font-weight: 600;
}
.sc-list {
  margin: 10px 0;
  max-height: 260px;
  overflow: auto;
}

/* 积分 AI */
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
  font-size: 14px;
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
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}
.ai-run:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.ai-inputs {
  margin-bottom: 8px;
}
.ai-inputs label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink3);
  margin-bottom: 4px;
}
.ai-wait,
.ai-idle {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--ink3);
}
.ai-meta {
  font-size: 11px;
  color: var(--ink3);
  margin: 0 0 8px;
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
  margin-top: 8px;
}
.ai-soft-err {
  font-size: 12px;
  color: var(--ink3);
  margin: 8px 0 0;
}
.ai-insight-body {
  margin-bottom: 10px;
}
.ai-insight-body :deep(.ai-insight) {
  display: grid;
  gap: 8px;
}
.ai-insight-body :deep(.ai-insight-sec) {
  border-radius: 10px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  background: #f8fafc;
}
.ai-insight-body :deep(.ai-insight-h) {
  font-size: 12px;
  font-weight: 800;
  color: var(--brand);
  margin-bottom: 6px;
}
.ai-insight-body :deep(ul) {
  margin: 0;
  padding-left: 18px;
}
.ai-insight-body :deep(li) {
  font-size: 12px;
  line-height: 1.45;
  color: #1e293b;
  margin-bottom: 3px;
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
  grid-template-columns: 1fr;
  gap: 8px;
}
.dx-action-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px;
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
  margin-top: 2px;
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
.side .ai-block {
  margin-bottom: 12px;
}
@media (min-width: 900px) {
  .workspace-body .ai-insight-body :deep(.ai-insight) {
    grid-template-columns: 1fr 1fr;
  }
  .workspace-body .dx-action-list {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }
}
</style>
