<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 订单异常与流失预警 —— 转化/取消趋势基于 /api/orders/monitor 真实聚合
 */
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { fmt, toast } from '../../lib/ui'
import AnalyticsFlowNav from '../../components/AnalyticsFlowNav.vue'
import AnalyticsAiActions from '../../components/AnalyticsAiActions.vue'

withDefaults(
  defineProps<{
    /** 嵌入经营分析总览时隐藏返回导航 */
    embedded?: boolean
  }>(),
  { embedded: false },
)

const range = ref<'24h' | '7d' | '14d'>('7d')
const loadError = ref('')
const loading = ref(false)
const data = ref<any>(null)

const alerts = ref<any[]>([])
const executing = ref<string | null>(null)
const doneKeys = ref<Record<string, boolean>>({})
const draftOpen = ref(false)
const draftText = ref('')
const draftTitle = ref(t('预付提醒话术'))

const kpi = computed(() => data.value?.kpi || {})
const series = computed(() => data.value?.series || [])
const hourly = computed(() => data.value?.hourly || [])
const channelChurn = computed(() => data.value?.channel_churn || [])
const funnel = computed(() => data.value?.funnel || {})
const topRisk = computed(() => data.value?.top_risk_orders || [])
const payRiskOrders = computed(() =>
  topRisk.value.filter((r: any) => r.risk_code === 'pay').slice(0, 5),
)
const collectOrders = computed(() =>
  topRisk.value.filter((r: any) => r.risk_code === 'collect').slice(0, 5),
)
const overdueOrders = computed(() =>
  topRisk.value.filter((r: any) => r.risk_code === 'overdue').slice(0, 5),
)

function markDone(key: string) {
  doneKeys.value = { ...doneKeys.value, [key]: true }
}

async function execWrite(
  key: string,
  action: Record<string, unknown>,
  opts?: { reload?: boolean },
) {
  if (executing.value || doneKeys.value[key]) return
  executing.value = key
  try {
    const res = await api.analyticsAiExecute(hotelStore.hotelId, action)
    toast(res?.message || t('已写入'))
    markDone(key)
    if (
      res?.draft_message &&
      (action.action_type === 'remind_pay' || action.action_type === 'prep_collect')
    ) {
      draftText.value = res.draft_message
      draftOpen.value = true
      draftTitle.value =
        action.action_type === 'prep_collect' ? t('前台交接草稿') : t('预付提醒话术')
    }
    if (opts?.reload || res?.wrote_noshow) {
      await loadMonitor()
    }
  } catch (e: any) {
    toast(e?.message || t('执行失败'), false)
  } finally {
    executing.value = null
  }
}

/** 流失排查：写入渠道复盘任务 */
function actInvestigate(a: any) {
  const topCh = channelChurn.value[0]
  return execWrite(`alert-${a.id}`, {
    id: `monitor-investigate-${a.id}`,
    action_type: 'open_channel_policy',
    title: topCh ? `渠道流失复盘 · ${topCh.channel}` : '渠道流失复盘',
    suggestion: a.suggestion || '排查高流失渠道取消原因，评估政策与竞对价差。',
    channel_hint: topCh?.channel,
    confidence: 'medium',
    module: 'health',
  })
}

/** 单笔预付跟进（核对到账 / 提醒付款） */
function actRemindPay(o: any) {
  return execWrite(`pay-${o.id}`, {
    id: `monitor-pay-${o.id}`,
    action_type: 'remind_pay',
    title: `预付跟进 · ${o.order_no}`,
    suggestion: o.hint || '应预付未到账：提醒客人付款，或核对 OTA/券商是否已结算。',
    order_id: o.id,
    order_no: o.order_no,
    confidence: 'high',
    module: 'health',
  })
}

/** 批量预付跟进 */
async function actRemindPayBatch() {
  const list = payRiskOrders.value.filter((o: any) => !doneKeys.value[`pay-${o.id}`])
  if (!list.length) {
    toast(t('暂无待跟进的预付订单'))
    return
  }
  for (const o of list) {
    await actRemindPay(o)
  }
}

/** 单笔到店收款准备 */
function actPrepCollect(o: any) {
  return execWrite(`collect-${o.id}`, {
    id: `monitor-collect-${o.id}`,
    action_type: 'prep_collect',
    title: `到店收款 · ${o.order_no}`,
    suggestion: o.hint || '到店付口径，前台办理时收款。',
    order_id: o.id,
    order_no: o.order_no,
    confidence: 'high',
    module: 'health',
  })
}

/** 批量到店收款准备 */
async function actPrepCollectBatch() {
  const list = collectOrders.value.filter((o: any) => !doneKeys.value[`collect-${o.id}`])
  if (!list.length) {
    toast(t('暂无到店收款准备项'))
    return
  }
  for (const o of list) {
    await actPrepCollect(o)
  }
}

/** 标记未到店 */
function actConfirmNoshow(o: any) {
  if (!confirm(t('确认将订单 {no} 标记为未到店？此操作会写回订单状态。', { no: o.order_no })))
    return
  return execWrite(
    `noshow-${o.id}`,
    {
      id: `monitor-noshow-${o.id}`,
      action_type: 'confirm_noshow',
      title: `确认未到店 · ${o.order_no}`,
      suggestion: o.hint || '入住日已过仍未办入住。',
      order_id: o.id,
      order_no: o.order_no,
      confidence: 'high',
      module: 'health',
    },
    { reload: true },
  )
}

/** 写入定价复核任务 */
function actPricingReview(a: any) {
  return execWrite(`alert-${a.id}`, {
    id: `monitor-pricing-${a.id}`,
    action_type: 'open_pricing',
    title: '转化偏低 · 定价复核',
    suggestion: a.suggestion || '复核窗期价格与 OTA 竞对一致性。',
    confidence: 'medium',
    module: 'health',
  })
}

async function copyDraft() {
  try {
    await navigator.clipboard.writeText(draftText.value)
    toast(t('已复制'))
  } catch {
    toast(t('复制失败，请手动选择'), false)
  }
  draftOpen.value = false
}

const chartMode = computed(() =>
  range.value === '24h' && hourly.value.length ? 'hourly' : 'daily',
)

const chartRows = computed(() => {
  if (chartMode.value === 'hourly') {
    return hourly.value.map((h: any) => ({
      label: h.label,
      bookings: h.bookings || 0,
      converted: h.converted || 0,
      churn: h.churn || 0,
    }))
  }
  return series.value.map((s: any) => ({
    label: s.label,
    bookings: s.bookings || 0,
    converted: s.converted || 0,
    churn: s.churn || 0,
    isToday: !!s.is_today,
  }))
})

const maxBookings = computed(() => Math.max(1, ...chartRows.value.map((r: any) => r.bookings || 0)))

/** SVG 折线：预订量 / 取消量（双轴归一到同一高度） */
const W = 640
const H = 220
const PAD = { l: 36, r: 16, t: 16, b: 28 }

function yScale(v: number, maxV: number) {
  const plotH = H - PAD.t - PAD.b
  return PAD.t + plotH * (1 - (maxV ? v / maxV : 0))
}

function xAt(i: number, n: number) {
  const plotW = W - PAD.l - PAD.r
  if (n <= 1) return PAD.l + plotW / 2
  return PAD.l + (plotW * i) / (n - 1)
}

const bookingPoly = computed(() => {
  const rows = chartRows.value
  const n = rows.length
  const maxV = Math.max(1, ...rows.map((r: any) => r.bookings))
  return rows
    .map((r: any, i: number) => `${xAt(i, n).toFixed(1)},${yScale(r.bookings, maxV).toFixed(1)}`)
    .join(' ')
})

const churnPoly = computed(() => {
  const rows = chartRows.value
  const n = rows.length
  const maxV = Math.max(1, ...rows.map((r: any) => Math.max(r.bookings, r.churn * 3)))
  // 取消量放大到可视：相对 bookings 尺度，用同一 max 但 churn 通常小，另用 churnMax
  const churnMax = Math.max(1, ...rows.map((r: any) => r.churn))
  const useMax = Math.max(churnMax, Math.ceil(maxV * 0.25))
  return rows
    .map((r: any, i: number) => `${xAt(i, n).toFixed(1)},${yScale(r.churn, useMax).toFixed(1)}`)
    .join(' ')
})

const bookingArea = computed(() => {
  const rows = chartRows.value
  const n = rows.length
  if (!n) return ''
  const maxV = Math.max(1, ...rows.map((r: any) => r.bookings))
  const top = rows
    .map((r: any, i: number) => `${xAt(i, n).toFixed(1)},${yScale(r.bookings, maxV).toFixed(1)}`)
    .join(' ')
  const baseY = H - PAD.b
  const lastX = xAt(n - 1, n).toFixed(1)
  const firstX = xAt(0, n).toFixed(1)
  return `M ${firstX} ${baseY} L ${top.replace(/ /g, ' L ')} L ${lastX} ${baseY} Z`
})

const gridYs = computed(() => {
  const plotH = H - PAD.t - PAD.b
  return [0.25, 0.5, 0.75].map((p) => PAD.t + plotH * p)
})

const trafficGap = computed(() => {
  const g = kpi.value.traffic_gap_pct
  if (g == null) return -30
  return g
})

async function loadMonitor() {
  loading.value = true
  loadError.value = ''
  try {
    data.value = await api.ordersMonitor(hotelStore.hotelId, range.value)
    // 用真实 KPI 刷新左侧关键告警文案
    const k = data.value?.kpi
    const topCh = data.value?.channel_churn?.[0]
    if (k) {
      alerts.value = [
        {
          id: 1,
          level: k.cancel_delta > 0 ? 'critical' : 'warning',
          title: t('已确认流失'),
          time: t('实时'),
          body: t(
            '取消 {cancelled} 单 + 确认未到店 {noshow} 单（不含待到店）；流失营收约 {rev}。',
            {
              cancelled: k.cancelled_count ?? 0,
              noshow: k.no_show_count ?? 0,
              rev: fmt(k.lost_revenue),
            },
          ),
          suggestion: topCh
            ? t('重点渠道：{channel}（已流失 {n} 单，占比 {pct}%）。', {
                channel: topCh.channel,
                n: topCh.churn,
                pct: (topCh.rate * 100).toFixed(1),
              })
            : t('持续观察渠道取消率。待到店订单不计入流失。'),
          action: t('写入渠道复盘任务'),
          actionKey: 'investigate',
        },
        {
          id: 2,
          level: (k.pay_risk_count || 0) > 0 ? 'warning' : 'info',
          title: t('收款与预付'),
          time: t('近 48h 入住'),
          body: t(
            '应预付未到账 {pay} 单需跟进；到店付待收 {collect} 单仅需前台准备；逾期未办 {od} 单另议。',
            {
              pay: k.pay_risk_count ?? 0,
              collect: k.collect_prep_count ?? 0,
              od: k.overdue_count ?? 0,
            },
          ),
          suggestion: t('预付未到账：提醒付款或核对渠道到账；到店付只写交接收款，勿发催付短信。'),
          action: '',
          actionKey: 'pay',
          showPayActions: !!(k.pay_risk_count || k.collect_prep_count || k.overdue_count),
        },
        {
          id: 3,
          level: 'warning',
          title: t('转化偏低'),
          time: t('窗口统计'),
          body: t(
            '窗口预订 {bookings} 单，待到店 {awaiting}，转化率 {conv}%，已流失率 {churn}%。',
            {
              bookings: k.bookings,
              awaiting: k.awaiting_count ?? 0,
              conv: (k.conversion_rate * 100).toFixed(1),
              churn: (k.churn_rate * 100).toFixed(1),
            },
          ),
          suggestion: topCh
            ? t('重点渠道：{channel}（已流失 {n} 单，占比 {pct}%）。', {
                channel: topCh.channel,
                n: topCh.churn,
                pct: (topCh.rate * 100).toFixed(1),
              })
            : '',
          action: t('写入定价复核任务'),
          actionKey: 'pricing',
        },
        {
          id: 4,
          level: 'info',
          title: t('漏斗概览'),
          time: data.value?.window ? `${data.value.window.from} ~ ${data.value.window.to}` : '',
          body: t(
            '待到店 {awaiting} · 逾期未办 {od} · 在住 {inhouse} · 已取消 {cancelled} · 确认未到店 {noshow}。',
            {
              awaiting: funnel.value.awaiting ?? funnel.value.pending ?? 0,
              od: funnel.value.overdue ?? 0,
              inhouse: funnel.value.in_house ?? 0,
              cancelled: funnel.value.cancelled ?? 0,
              noshow: funnel.value.no_show ?? 0,
            },
          ),
          suggestion: '',
          action: '',
        },
      ]
    }
  } catch (e: any) {
    loadError.value = e?.message || t('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadMonitor()
})

watch(range, loadMonitor)
watch(
  () => hotelStore.hotelId,
  () => {
    doneKeys.value = {}
    loadMonitor()
  },
)
</script>

<template>
  <div class="page" :class="{ 'is-embedded': embedded }">
    <div
      v-if="!embedded"
      class="page-title-block flex justify-between items-end border-b border-outline-variant pb-4 mb-6 flex-wrap gap-3"
    >
      <div>
        <h1 class="text-display-lg font-display-lg text-on-surface font-bold">
          {{ t('订单异常与流失预警') }}
        </h1>
        <p class="text-body-lg font-body-lg text-on-surface-variant mt-1">
          {{ t('基于订单库聚合：已取消 / 确认未到店（入住日已过）与待到店分开统计。') }}
        </p>
        <p v-if="loadError" class="text-sm text-error mt-1">{{ loadError }}</p>
      </div>
      <div class="flex flex-col items-end gap-2">
        <AnalyticsFlowNav hide-links />
        <div class="flex items-center gap-2 text-label-lg font-label-lg">
          <span class="relative flex h-3 w-3">
            <span
              class="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"
            ></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-primary"></span>
          </span>
          <span class="text-primary font-bold">{{ loading ? t('刷新中…') : t('数据已同步') }}</span>
        </div>
      </div>
    </div>

    <div v-else-if="loadError" class="mb-3">
      <p class="text-sm text-error">{{ loadError }}</p>
    </div>

    <AnalyticsAiActions v-if="!embedded" module="health" compact :show-briefing="true" />

    <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
      <!-- 告警流 -->
      <div
        class="md:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-4 flex flex-col h-[640px] shadow-sm"
      >
        <div class="flex items-center justify-between mb-4 border-b border-outline-variant pb-2">
          <h2 class="text-headline-md font-headline-md font-bold flex items-center gap-2">
            {{ t('监测动态') }}
          </h2>
        </div>
        <div class="flex-1 overflow-y-auto space-y-4 pr-2">
          <div
            v-for="a in alerts"
            :key="a.id"
            class="rounded-lg p-3 relative overflow-hidden border"
            :class="{
              'bg-orange-50 border-orange-300': a.level === 'warning',
              'bg-error-container/20 border-error': a.level === 'critical',
              'bg-primary-container/10 border-primary-container': a.level === 'info',
            }"
          >
            <div
              class="absolute top-0 left-0 w-1 h-full"
              :class="{
                'bg-orange-500': a.level === 'warning',
                'bg-error': a.level === 'critical',
                'bg-primary': a.level === 'info',
              }"
            />
            <div class="flex items-start gap-3 pl-2">
              <div class="w-full">
                <div class="flex justify-between items-center mb-1 gap-2">
                  <h3 class="text-label-lg font-label-lg font-bold text-on-surface">
                    {{ a.title }}
                  </h3>
                  <span class="text-[10px] text-on-surface-variant shrink-0">{{ a.time }}</span>
                </div>
                <p class="text-body-md font-body-md text-on-surface-variant text-sm mb-2">
                  {{ a.body }}
                </p>
                <div
                  v-if="a.suggestion"
                  class="bg-surface-container-highest p-2 rounded text-xs border border-outline-variant border-dashed"
                >
                  <span class="font-bold text-on-surface">{{ t('建议：') }}</span
                  >{{ a.suggestion }}
                </div>

                <!-- 页内写操作：流失复盘 / 定价复核 -->
                <div v-if="a.action" class="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    class="text-xs font-bold px-3 py-1.5 rounded border transition-colors cursor-pointer disabled:opacity-50"
                    :class="
                      doneKeys['alert-' + a.id]
                        ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                        : a.level === 'critical'
                          ? 'bg-error text-on-error border-error hover:bg-error/90'
                          : 'bg-primary text-on-primary border-primary hover:opacity-90'
                    "
                    :disabled="!!executing || doneKeys['alert-' + a.id]"
                    @click="a.actionKey === 'pricing' ? actPricingReview(a) : actInvestigate(a)"
                  >
                    {{
                      doneKeys['alert-' + a.id]
                        ? t('已写入')
                        : executing === 'alert-' + a.id
                          ? t('写入中…')
                          : a.action
                    }}
                  </button>
                </div>

                <!-- 页内写操作：预付跟进 / 到店收款 / 标记未到店 -->
                <div v-if="a.showPayActions" class="mt-2 space-y-2">
                  <div
                    v-if="payRiskOrders.length"
                    class="rounded-md border border-outline-variant bg-surface-container-lowest/80 p-2"
                  >
                    <div class="flex items-center justify-between gap-2 mb-1.5">
                      <span class="text-[11px] font-bold text-on-surface">{{
                        t('应预付未到账 · 跟进')
                      }}</span>
                      <button
                        type="button"
                        class="text-[10px] font-bold px-2 py-0.5 rounded border border-outline-variant hover:bg-surface-container-high disabled:opacity-50"
                        :disabled="!!executing"
                        @click="actRemindPayBatch"
                      >
                        {{ t('全部跟进') }}
                      </button>
                    </div>
                    <ul class="space-y-1.5">
                      <li
                        v-for="o in payRiskOrders"
                        :key="'pay-' + o.id"
                        class="flex items-center justify-between gap-2 text-[11px]"
                      >
                        <div class="min-w-0 flex-1">
                          <div class="font-medium truncate text-on-surface">
                            {{ o.guest }} · {{ o.order_no }}
                          </div>
                          <div class="text-on-surface-variant truncate">
                            {{ o.channel }} · {{ fmt(o.amount) }} · {{ o.check_in }}
                          </div>
                        </div>
                        <button
                          type="button"
                          class="shrink-0 text-[10px] font-bold px-2 py-1 rounded border transition-colors disabled:opacity-50"
                          :class="
                            doneKeys['pay-' + o.id]
                              ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                              : 'bg-primary text-on-primary border-primary'
                          "
                          :disabled="!!executing || doneKeys['pay-' + o.id]"
                          @click="actRemindPay(o)"
                        >
                          {{
                            doneKeys['pay-' + o.id]
                              ? t('已跟进')
                              : executing === 'pay-' + o.id
                                ? '…'
                                : t('跟进预付')
                          }}
                        </button>
                      </li>
                    </ul>
                  </div>

                  <div
                    v-if="collectOrders.length"
                    class="rounded-md border border-sky-200 bg-sky-50/70 p-2"
                  >
                    <div class="flex items-center justify-between gap-2 mb-1.5">
                      <span class="text-[11px] font-bold text-on-surface">{{
                        t('到店付 · 收款准备')
                      }}</span>
                      <button
                        type="button"
                        class="text-[10px] font-bold px-2 py-0.5 rounded border border-outline-variant hover:bg-surface-container-high disabled:opacity-50"
                        :disabled="!!executing"
                        @click="actPrepCollectBatch"
                      >
                        {{ t('全部准备') }}
                      </button>
                    </div>
                    <ul class="space-y-1.5">
                      <li
                        v-for="o in collectOrders"
                        :key="'collect-' + o.id"
                        class="flex items-center justify-between gap-2 text-[11px]"
                      >
                        <div class="min-w-0 flex-1">
                          <div class="font-medium truncate text-on-surface">
                            {{ o.guest }} · {{ o.order_no }}
                          </div>
                          <div class="text-on-surface-variant truncate">
                            {{ o.channel }} · {{ fmt(o.amount) }} · {{ o.check_in }}
                          </div>
                        </div>
                        <button
                          type="button"
                          class="shrink-0 text-[10px] font-bold px-2 py-1 rounded border transition-colors disabled:opacity-50"
                          :class="
                            doneKeys['collect-' + o.id]
                              ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                              : 'bg-sky-700 text-white border-sky-800'
                          "
                          :disabled="!!executing || doneKeys['collect-' + o.id]"
                          @click="actPrepCollect(o)"
                        >
                          {{
                            doneKeys['collect-' + o.id]
                              ? t('已准备')
                              : executing === 'collect-' + o.id
                                ? '…'
                                : t('到店收款')
                          }}
                        </button>
                      </li>
                    </ul>
                  </div>

                  <div
                    v-if="overdueOrders.length"
                    class="rounded-md border border-orange-200 bg-orange-50/60 p-2"
                  >
                    <div class="text-[11px] font-bold text-on-surface mb-1.5">
                      {{ t('逾期未办 · 可标记未到店') }}
                    </div>
                    <ul class="space-y-1.5">
                      <li
                        v-for="o in overdueOrders"
                        :key="'od-' + o.id"
                        class="flex items-center justify-between gap-2 text-[11px]"
                      >
                        <div class="min-w-0 flex-1">
                          <div class="font-medium truncate text-on-surface">
                            {{ o.guest }} · {{ o.order_no }}
                          </div>
                          <div class="text-on-surface-variant truncate">
                            {{ t('入住') }} {{ o.check_in }} · {{ fmt(o.amount) }}
                          </div>
                        </div>
                        <button
                          type="button"
                          class="shrink-0 text-[10px] font-bold px-2 py-1 rounded border transition-colors disabled:opacity-50"
                          :class="
                            doneKeys['noshow-' + o.id]
                              ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                              : 'bg-orange-600 text-white border-orange-700'
                          "
                          :disabled="!!executing || doneKeys['noshow-' + o.id]"
                          @click="actConfirmNoshow(o)"
                        >
                          {{
                            doneKeys['noshow-' + o.id]
                              ? t('已标记')
                              : executing === 'noshow-' + o.id
                                ? '…'
                                : t('标记未到店')
                          }}
                        </button>
                      </li>
                    </ul>
                  </div>

                  <p
                    v-if="!payRiskOrders.length && !collectOrders.length && !overdueOrders.length"
                    class="text-[11px] text-on-surface-variant"
                  >
                    {{ t('当前窗口暂无具体待处理订单。') }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="draftOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
        @click.self="draftOpen = false"
      >
        <div
          class="w-full max-w-md rounded-xl bg-surface-container-lowest border border-outline-variant p-4 shadow-lg"
        >
          <h4 class="font-bold text-on-surface mb-2">{{ draftTitle }}</h4>
          <textarea
            v-model="draftText"
            rows="5"
            class="w-full text-sm rounded-lg border border-outline-variant p-2 bg-surface-container-low text-on-surface"
          />
          <div class="mt-3 flex gap-2 justify-end">
            <button
              type="button"
              class="text-sm px-3 py-1.5 rounded border border-outline-variant"
              @click="draftOpen = false"
            >
              {{ t('关闭') }}
            </button>
            <button
              type="button"
              class="text-sm px-3 py-1.5 rounded bg-primary text-on-primary"
              @click="copyDraft"
            >
              {{ t('复制') }}
            </button>
          </div>
        </div>
      </div>

      <!-- 主指标 + 趋势 -->
      <div class="md:col-span-8 flex flex-col gap-gutter">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-gutter">
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-sm"
          >
            <h3 class="text-label-lg font-label-lg font-bold text-on-surface mb-1">
              {{ t('已确认流失') }}
            </h3>
            <div class="flex items-end gap-2 mb-2">
              <span class="text-num-xl font-num-xl text-error font-bold">{{
                kpi.cancel_count ?? '—'
              }}</span>
              <span class="text-body-md font-body-md text-on-surface-variant mb-1">{{
                t('/ 当前窗口')
              }}</span>
            </div>
            <div class="text-on-surface-variant text-sm font-label-lg mb-1">
              {{ t('取消') }} {{ kpi.cancelled_count ?? 0 }} · {{ t('确认未到店') }}
              {{ kpi.no_show_count ?? 0 }}
              <span v-if="(kpi.awaiting_count || 0) > 0">
                · {{ t('待到店 {n}（不计流失）', { n: kpi.awaiting_count }) }}</span
              >
            </div>
            <div
              class="text-sm font-label-lg"
              :class="(kpi.cancel_delta || 0) > 0 ? 'text-error' : 'text-green-700'"
            >
              {{ t('较上期') }} {{ (kpi.cancel_delta || 0) > 0 ? '+' : ''
              }}{{ kpi.cancel_delta ?? 0 }}
            </div>
          </div>
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-sm"
          >
            <h3 class="text-label-lg font-label-lg font-bold text-on-surface mb-1">
              {{ t('流失机会') }}
            </h3>
            <div class="flex items-end gap-2 mb-2">
              <span class="text-num-xl font-num-xl text-orange-600 font-bold">{{
                fmt(kpi.lost_revenue || 0)
              }}</span>
            </div>
            <div class="text-on-surface-variant text-sm font-label-lg">
              {{ t('已取消+确认未到店金额（不含待到店）') }}
            </div>
          </div>
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-sm"
          >
            <h3 class="text-label-lg font-label-lg font-bold text-on-surface mb-1">
              {{ t('预付跟进') }}
            </h3>
            <div class="flex items-end gap-2 mb-2">
              <span class="text-num-xl font-num-xl text-on-surface font-bold">{{
                kpi.pay_risk_count ?? '—'
              }}</span>
              <span class="text-body-md font-body-md text-on-surface-variant mb-1">{{
                t('应预付未到账')
              }}</span>
            </div>
            <div class="text-primary text-sm font-label-lg">
              {{ t('到店收款准备') }} {{ kpi.collect_prep_count ?? 0 }}
              <span v-if="(kpi.overdue_count || 0) > 0">
                · {{ t('逾期未办 {n}', { n: kpi.overdue_count }) }}</span
              >
            </div>
          </div>
        </div>

        <!-- 流失计算规则（紧贴 KPI，避免误解） -->
        <div
          class="churn-rule rounded-xl border border-outline-variant bg-surface-container-low px-4 py-3"
        >
          <div class="flex items-start gap-2">
            <span
              class="material-symbols-outlined text-[18px] text-on-surface-variant shrink-0 mt-0.5"
              >info</span
            >
            <div class="min-w-0 flex-1">
              <h4 class="text-sm font-bold text-on-surface m-0">{{ t('流失口径') }}</h4>
              <p class="text-xs text-on-surface-variant mt-1 mb-2 leading-relaxed">
                {{ t('按入住日落入当前时间窗统计；「已确认流失」=') }}
                <strong class="text-on-surface font-semibold">{{ t('取消') }}</strong>
                +
                <strong class="text-on-surface font-semibold">{{
                  t('入住日已到/已过且已标记未到店')
                }}</strong
                >。
              </p>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] leading-snug">
                <div class="rounded-lg bg-error/5 border border-error/20 px-2.5 py-2">
                  <div class="font-bold text-error mb-1">{{ t('计入流失') }}</div>
                  <ul class="m-0 pl-3.5 text-on-surface-variant space-y-0.5">
                    <li>{{ t('订单状态为「已取消」') }}</li>
                    <li>{{ t('状态为「未到店」，且入住日 ≤ 今天') }}</li>
                  </ul>
                </div>
                <div class="rounded-lg bg-emerald-50 border border-emerald-200 px-2.5 py-2">
                  <div class="font-bold text-emerald-800 mb-1">{{ t('不计入流失') }}</div>
                  <ul class="m-0 pl-3.5 text-on-surface-variant space-y-0.5">
                    <li>{{ t('待到店（入住日未到的有效预订）') }}</li>
                    <li>{{ t('逾期未办（入住日已过仍未入住、尚未标未到店）') }}</li>
                    <li>{{ t('未付/到店付（属收款动作，不是流失）') }}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-sm flex-1 flex flex-col min-h-[420px]"
        >
          <div class="flex justify-between items-center mb-3 flex-wrap gap-2">
            <div>
              <h3 class="text-headline-md font-headline-md font-bold text-on-surface">
                {{ t('转化与取消趋势') }}
              </h3>
              <p class="text-xs text-on-surface-variant mt-0.5">
                {{ chartMode === 'hourly' ? t('今日按时段') : t('按入住日') }}
                <span v-if="data?.window"> · {{ data.window.from }} ~ {{ data.window.to }}</span>
              </p>
            </div>
            <div class="flex gap-2">
              <button
                v-for="r in ['24h', '7d', '14d'] as const"
                :key="r"
                type="button"
                class="text-label-lg font-label-lg px-3 py-1 rounded border transition-colors"
                :class="
                  range === r
                    ? 'bg-surface-container-high border-outline-variant text-on-surface font-bold'
                    : 'border-transparent hover:bg-surface-container-low text-on-surface-variant'
                "
                @click="range = r"
              >
                {{ r }}
              </button>
            </div>
          </div>

          <!-- 折线 + 面积 -->
          <div
            class="relative rounded-lg border border-outline-variant bg-surface px-2 pt-2 pb-1 mb-3"
          >
            <div class="flex gap-4 text-xs mb-1 px-2">
              <span class="inline-flex items-center gap-1.5">
                <span class="w-3 h-0.5 bg-primary inline-block rounded" />{{ t('预订量') }}</span
              >
              <span class="inline-flex items-center gap-1.5 text-error">
                <span class="w-3 h-0.5 bg-error inline-block rounded" />{{ t('已确认流失') }}</span
              >
            </div>
            <svg class="w-full h-[220px]" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none">
              <defs>
                <linearGradient id="bookFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#2563eb" stop-opacity="0.22" />
                  <stop offset="100%" stop-color="#2563eb" stop-opacity="0.02" />
                </linearGradient>
              </defs>
              <line
                v-for="(gy, i) in gridYs"
                :key="i"
                :x1="PAD.l"
                :y1="gy"
                :x2="W - PAD.r"
                :y2="gy"
                stroke="#e5e7eb"
                stroke-dasharray="4 4"
              />
              <path v-if="bookingArea" :d="bookingArea" fill="url(#bookFill)" />
              <polyline
                :points="bookingPoly"
                fill="none"
                stroke="#2563eb"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <polyline
                :points="churnPoly"
                fill="none"
                stroke="#dc2626"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <div
              class="flex justify-between text-[10px] text-on-surface-variant px-1 pb-1 overflow-hidden"
            >
              <span
                v-for="(r, i) in chartRows"
                :key="i"
                class="flex-1 text-center truncate"
                :class="r.isToday ? 'font-bold text-primary' : ''"
              >
                {{ r.label }}</span
              >
            </div>
          </div>

          <!-- 柱状对比：预订 / 转化 / 流失 -->
          <div class="h-28 flex items-end gap-1.5 px-1 mb-4">
            <div
              v-for="(r, i) in chartRows"
              :key="i"
              class="flex-1 flex flex-col items-center gap-1 min-w-0"
            >
              <div class="w-full flex items-end justify-center gap-0.5 h-20">
                <div
                  class="w-[30%] max-w-[14px] bg-primary/70 rounded-t-sm"
                  :style="{ height: Math.max(4, (r.bookings / maxBookings) * 72) + 'px' }"
                  :title="t('预订 {n}', { n: r.bookings })"
                />
                <div
                  class="w-[30%] max-w-[14px] bg-emerald-500/80 rounded-t-sm"
                  :style="{
                    height: Math.max(r.converted ? 4 : 0, (r.converted / maxBookings) * 72) + 'px',
                  }"
                  :title="t('转化 {n}', { n: r.converted })"
                />
                <div
                  class="w-[30%] max-w-[14px] bg-error/80 rounded-t-sm"
                  :style="{
                    height: Math.max(r.churn ? 4 : 0, (r.churn / maxBookings) * 72) + 'px',
                  }"
                  :title="t('流失 {n}', { n: r.churn })"
                />
              </div>
              <span class="text-[10px] text-on-surface-variant truncate w-full text-center">{{
                r.label
              }}</span>
            </div>
          </div>
          <div class="flex gap-4 text-[11px] text-on-surface-variant mb-3 px-1">
            <span
              ><i class="inline-block w-2.5 h-2.5 rounded-sm bg-primary/70 mr-1 align-middle" />{{
                t('预订')
              }}</span
            >
            <span
              ><i
                class="inline-block w-2.5 h-2.5 rounded-sm bg-emerald-500/80 mr-1 align-middle"
              />{{ t('已转化') }}</span
            >
            <span
              ><i class="inline-block w-2.5 h-2.5 rounded-sm bg-error/80 mr-1 align-middle" />{{
                t('已确认流失')
              }}</span
            >
          </div>

          <!-- 渠道流失表 -->
          <div
            id="monitor-channel-churn"
            v-if="channelChurn.length"
            class="mb-4 overflow-x-auto rounded-lg border border-outline-variant scroll-mt-4"
          >
            <table class="w-full text-left text-sm">
              <thead class="bg-surface-container-low text-xs text-on-surface-variant">
                <tr>
                  <th class="p-2 font-bold text-on-surface">{{ t('渠道') }}</th>
                  <th class="p-2 font-bold text-on-surface">{{ t('预订') }}</th>
                  <th class="p-2 font-bold text-on-surface">{{ t('流失') }}</th>
                  <th class="p-2 font-bold text-on-surface">{{ t('流失率') }}</th>
                  <th class="p-2 font-bold text-on-surface">{{ t('流失金额') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="c in channelChurn"
                  :key="c.channel"
                  class="border-t border-outline-variant/60"
                >
                  <td class="p-2 font-medium">{{ t(String(c.channel || '')) }}</td>
                  <td class="p-2 font-num-md">{{ c.bookings }}</td>
                  <td class="p-2 font-num-md text-error">{{ c.churn }}</td>
                  <td class="p-2">
                    <div class="flex items-center gap-2">
                      <div
                        class="flex-1 h-1.5 bg-surface-container-high rounded-full overflow-hidden max-w-[80px]"
                      >
                        <div
                          class="h-full bg-error/80 rounded-full"
                          :style="{ width: Math.min(100, (c.rate || 0) * 100 * 4) + '%' }"
                        />
                      </div>
                      <span class="text-xs">{{ ((c.rate || 0) * 100).toFixed(1) }}%</span>
                    </div>
                  </td>
                  <td class="p-2 font-num-md">{{ fmt(c.lost_amt) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="mt-auto grid grid-cols-1 gap-4 border-t border-outline-variant pt-4">
            <div>
              <span class="text-label-lg font-label-lg font-bold text-on-surface block mb-2">{{
                t('流量转化差值')
              }}</span>
              <div class="flex items-center gap-2">
                <div class="w-full bg-surface-container-high rounded-full h-2.5">
                  <div
                    class="bg-orange-500 h-2.5 rounded-full"
                    :style="{ width: Math.min(100, Math.abs(trafficGap)) + '%' }"
                  />
                </div>
                <span class="text-body-md font-body-md text-orange-600 font-bold">
                  {{ trafficGap > 0 ? '+' : '' }}{{ trafficGap }}%
                </span>
              </div>
              <p class="text-xs text-on-surface-variant mt-2">
                {{ t('相对基准流失率的偏离。') }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
