<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * 订单渠道归因分析 —— 视觉 1:1 对齐原型 download.html
 * 数据来自 /api/orders/attribution；接口失败时用原型静态兜底
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { confidenceLabel } from '../../lib/aiConfidence'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { ORDER_ST_CN, PAY_CN, toast } from '../../lib/ui'
import {
  ASSIGN_ST_CN,
  assignStatusOf,
  stayTypeLabel,
  formatOrderDateTime,
  localizeLineDesc,
} from '../../lib/orderFlow'
import AnalyticsFlowNav from '../../components/AnalyticsFlowNav.vue'
import AnalyticsAiActions from '../../components/AnalyticsAiActions.vue'
import ChannelBookingTrend from '../../components/ChannelBookingTrend.vue'

withDefaults(
  defineProps<{
    embedded?: boolean
    /** 仅展示高价值订单溯源列表（利润优化 Tab 底部） */
    ordersOnly?: boolean
  }>(),
  { embedded: false, ordersOnly: false },
)

const days = ref(7)
const loading = ref(false)
const data = ref<any>(null)

/** 行内展开的订单详情 */
const expandedId = ref<number | null>(null)
const detailCache = ref<Record<number, any>>({})
const detailLoading = ref(false)
const detailError = ref('')

const kpi = computed(
  () =>
    data.value?.kpi || {
      xhs_roi: 0,
      xhs_roi_delta_pct: 0,
      cac: 0,
      cac_delta_pct: 0,
      wechat_conv_rate: 0,
      wechat_conv_delta: 0,
    },
)
const pathSummary = computed(
  () =>
    data.value?.path_summary || {
      attributed_orders: 0,
      single_touch_orders: 0,
      cross_touch_orders: 0,
      single_pct: 0,
      cross_pct: 0,
    },
)
const paths = computed(() => {
  const list = data.value?.paths
  return Array.isArray(list) ? list : []
})
const pathMaxOrders = computed(() =>
  Math.max(1, ...paths.value.map((p: { orders?: number }) => Number(p.orders || 0))),
)
const highValue = computed(() => {
  const list = data.value?.high_value_orders
  return Array.isArray(list) ? list : []
})
const expandedDetail = computed(() =>
  expandedId.value != null ? detailCache.value[expandedId.value] : null,
)

const router = useRouter()
const aiInsight = ref<any>(null)
const aiLoading = ref(false)
const aiError = ref('')
const aiSourceLabel = computed(() => {
  const s = aiInsight.value?.source
  if (s === 'llm') return t('AI 解读')
  if (s === 'unavailable' || s === 'fallback') return t('AI 暂不可用')
  if (s === 'rules_disabled') return t('AI 未启用')
  return ''
})
const aiModelMeta = computed(() => formatAiModelMeta(aiInsight.value))
const confText = (c: string) => confidenceLabel(c)

const LINE_ST: Record<string, string> = {
  held: '待分房',
  assigned: '已预分',
  checked_in: '在住',
  checked_out: '已退',
  cancelled: '已取消',
}

const chipClass: Record<string, string> = {
  red: 'bg-red-50 text-red-600 text-xs px-2 py-1 rounded-md border border-red-100',
  blue: 'bg-blue-50 text-blue-600 text-xs px-2 py-1 rounded-md border border-blue-100',
  purple: 'bg-purple-50 text-purple-600 text-xs px-2 py-1 rounded-md border border-purple-100',
  orange: 'bg-orange-50 text-orange-600 text-xs px-2 py-1 rounded-md border border-orange-100',
  green:
    'bg-green-50 text-green-600 text-xs px-2 py-1 rounded-md border border-green-100 flex items-center',
}

async function load() {
  loading.value = true
  expandedId.value = null
  aiInsight.value = null
  aiError.value = ''
  try {
    data.value = await api.ordersAttribution(hotelStore.hotelId, days.value)
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

async function runAiInsight() {
  if (aiLoading.value) return
  aiLoading.value = true
  aiError.value = ''
  try {
    aiInsight.value = await api.ordersAttributionAi(hotelStore.hotelId, days.value)
  } catch (e: any) {
    aiInsight.value = null
    aiError.value = e?.message || t('AI 解读失败')
    toast(aiError.value, false)
  } finally {
    aiLoading.value = false
  }
}

function runAiAction(a: any) {
  if (!a || a.action_type !== 'open_path') return
  const p = String(a.path || '').trim()
  if (!p) return
  router.push(p)
  toast(a.action_label || '已跳转')
}

function fmtMoney(n: number) {
  return `¥${Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function fmtMoney2(n: number | null | undefined) {
  if (n == null || !Number.isFinite(Number(n))) return '—'
  return `¥${Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
}

/** 仅展示真实时长；无 created_at 差值时显示 — */
function fmtHours(h: number | null | undefined) {
  if (h == null || !Number.isFinite(Number(h))) return '—'
  const v = Number(h)
  return t('{n} 小时', { n: Number.isInteger(v) ? v : v })
}

function statusLabel(st: string | undefined) {
  if (!st) return '—'
  return ORDER_ST_CN[st] || st
}

function payLabel(st: string | undefined) {
  if (!st) return '—'
  return PAY_CN[st] || st
}

function fmtDate(v: string | null | undefined) {
  if (!v) return '—'
  return String(v).slice(0, 10)
}

function assignLabel(o: any) {
  if (!o) return '—'
  const code = assignStatusOf(o)
  const msgid = ASSIGN_ST_CN[code]
  return msgid ? t(msgid) : code || '—'
}

function staySummary(o: any) {
  if (!o) return '—'
  const n = Number(o.nights || 0) || '—'
  const r = Number(o.rooms || 1)
  return `${fmtDate(o.check_in)} → ${fmtDate(o.check_out)} · ${n} ${t('晚')} · ${r} ${t('间')}`
}

function folioBalance(o: any) {
  const b = o?.folio?.balance ?? o?.folio_balance
  return b == null ? null : Number(b)
}

function roomItems(o: any) {
  const items = Array.isArray(o?.items) ? o.items : []
  return items.filter((it: any) => it.item_type === 'room' || it.description)
}

function checkinRows(o: any) {
  return Array.isArray(o?.checkins) ? o.checkins : []
}

function groupLines(o: any) {
  return Array.isArray(o?.group_lines) ? o.group_lines : []
}

/** 行内展开真实订单详情（不跳转） */
async function toggleOrderDetail(row: { order_id?: number | string }) {
  const id = Number(row?.order_id)
  if (!id) return
  if (expandedId.value === id) {
    expandedId.value = null
    return
  }
  expandedId.value = id
  detailError.value = ''
  if (detailCache.value[id]) return
  detailLoading.value = true
  try {
    const d = await api.getOrder(id)
    detailCache.value = { ...detailCache.value, [id]: d }
  } catch (e: any) {
    detailError.value = e?.message || t('加载订单详情失败')
  } finally {
    detailLoading.value = false
  }
}

watch(days, () => load())
onMounted(load)
</script>

<template>
  <div class="page" :class="{ 'is-embedded': embedded }">
    <template v-if="!ordersOnly">
      <AnalyticsFlowNav v-if="!embedded" hide-links />
      <AnalyticsAiActions v-if="!embedded" module="attribution" compact class="mb-4" />

      <div v-if="!embedded" class="page-title-block mb-8 flex justify-between items-end">
        <div>
          <h1 class="text-display-lg font-display-lg text-on-surface">
            {{ t('订单渠道归因分析') }}
          </h1>
        </div>
      </div>

      <ChannelBookingTrend />

      <p v-if="loading && !data" class="mb-4 text-on-surface-variant text-body-md text-sm">
        {{ t('加载中…') }}
      </p>

      <!-- AI 归因洞察：触发式 -->
      <div
        v-if="commercialEnabled()"
        class="mb-8 bg-[#F3E8F9] border-l-4 border-tertiary rounded-r-xl p-4 shadow-sm"
      >
        <div class="flex flex-wrap items-start justify-between gap-3 mb-2">
          <h3
            class="text-headline-md font-headline-md text-on-tertiary-container m-0 flex items-center gap-2"
          >
            <span class="material-symbols-outlined icon-fill text-tertiary" data-icon="sparkles"
              >auto_awesome</span
            >
            {{ t('AI 归因洞察') }}
          </h3>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-xs font-bold bg-primary text-on-primary disabled:opacity-50 shrink-0"
            :disabled="aiLoading || loading || !data"
            @click="runAiInsight"
          >
            {{ aiLoading ? t('解读中…') : aiInsight ? t('重新解读') : t('生成 AI 归因洞察') }}
          </button>
        </div>
        <template v-if="aiLoading">
          <p class="text-sm text-on-surface-variant m-0">
            {{ t('正在结合归因表与订单路径生成解读…') }}
          </p>
        </template>
        <template v-else-if="aiInsight">
          <p class="text-[11px] text-on-surface-variant mb-2 flex flex-wrap gap-2 items-center">
            <span>{{ aiSourceLabel }}</span>
            <span
              v-if="aiModelMeta"
              class="px-1.5 py-0.5 rounded bg-surface-container-high font-mono"
              >{{ aiModelMeta }}</span
            >
            <span
              v-if="aiInsight.confidence"
              class="px-1.5 py-0.5 rounded bg-surface-container-high"
              >{{ confText(aiInsight.confidence) }}</span
            >
            <span v-if="aiInsight.confidence_note">· {{ t(aiInsight.confidence_note) }}</span>
          </p>
          <div
            v-if="aiInsight.source === 'llm' && aiInsight.narrative_html"
            class="ai-insight-body"
            v-html="aiInsight.narrative_html"
          />
          <p v-else class="text-sm text-on-surface-variant m-0">
            {{ t('未能调用大模型生成解读。下面如有事实条目，来自查询数据，不是 AI 结论。') }}
          </p>
          <div
            v-if="aiInsight.source === 'llm' && (aiInsight.actions || []).length"
            class="flex flex-wrap gap-2 mt-3"
          >
            <button
              v-for="(a, i) in aiInsight.actions"
              :key="i"
              type="button"
              class="px-3 py-1.5 rounded-lg text-xs font-semibold border border-outline-variant bg-surface hover:bg-surface-container-low"
              @click="runAiAction(a)"
            >
              {{ a.action_label || t('执行') }}
            </button>
          </div>
          <p v-if="aiInsight.llm_error" class="text-xs text-on-surface-variant mt-2 mb-0">
            {{ t(aiInsight.llm_error) }}
          </p>
        </template>
        <p v-else class="text-sm text-on-surface-variant m-0">
          {{ t('点击「生成 AI 归因洞察」，结合当前窗口路径与 KPI 由模型给出事实与建议。') }}
        </p>
        <p v-if="aiError" class="text-sm text-error mt-2 mb-0">{{ aiError }}</p>
      </div>

      <!-- Metrics Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div
          class="bg-surface rounded-xl p-6 border border-surface-variant shadow-sm flex flex-col justify-between"
        >
          <div class="flex justify-between items-start mb-4">
            <h4 class="text-label-lg font-label-lg text-on-surface-variant">
              {{ t('小红书综合 ROI') }}
            </h4>
            <span
              class="material-symbols-outlined text-primary bg-primary-container/10 p-2 rounded-lg"
              >trending_up</span
            >
          </div>
          <div class="text-display-lg font-display-lg text-on-surface mb-2">{{ kpi.xhs_roi }}x</div>
          <div class="text-label-lg font-label-lg text-secondary flex items-center">
            <span
              class="flex items-center mr-2"
              :class="(kpi.xhs_roi_delta_pct || 0) >= 0 ? 'text-green-600' : 'text-red-500'"
            >
              <span class="material-symbols-outlined text-[16px]">{{
                (kpi.xhs_roi_delta_pct || 0) >= 0 ? 'arrow_upward' : 'arrow_downward'
              }}</span>
              {{ Math.abs(kpi.xhs_roi_delta_pct || 0) }}% </span
            >{{ t('较上月') }}
          </div>
        </div>
        <div
          class="bg-surface rounded-xl p-6 border border-surface-variant shadow-sm flex flex-col justify-between"
        >
          <div class="flex justify-between items-start mb-4">
            <h4 class="text-label-lg font-label-lg text-on-surface-variant">
              {{ t('平均获客成本 (CAC)') }}
            </h4>
            <span
              class="material-symbols-outlined text-primary bg-primary-container/10 p-2 rounded-lg"
              >account_balance_wallet</span
            >
          </div>
          <div class="text-display-lg font-display-lg text-on-surface mb-2 font-num-xl text-num-xl">
            ¥{{ Number(kpi.cac || 0).toFixed(2) }}
          </div>
          <div class="text-label-lg font-label-lg text-secondary flex items-center">
            <span
              class="flex items-center mr-2"
              :class="(kpi.cac_delta_pct || 0) >= 0 ? 'text-red-500' : 'text-green-600'"
            >
              <span class="material-symbols-outlined text-[16px]">{{
                (kpi.cac_delta_pct || 0) >= 0 ? 'arrow_upward' : 'arrow_downward'
              }}</span>
              {{ Math.abs(kpi.cac_delta_pct || 0) }}% </span
            >{{ t('较上月') }}
          </div>
        </div>
        <div
          class="bg-surface rounded-xl p-6 border border-surface-variant shadow-sm flex flex-col justify-between"
        >
          <div class="flex justify-between items-start mb-4">
            <h4 class="text-label-lg font-label-lg text-on-surface-variant">
              {{ t('微信直销转化率 (受辅助)') }}
            </h4>
            <span
              class="material-symbols-outlined text-primary bg-primary-container/10 p-2 rounded-lg"
              >check_circle</span
            >
          </div>
          <div class="text-display-lg font-display-lg text-on-surface mb-2 font-num-xl text-num-xl">
            {{ kpi.wechat_conv_rate }}%
          </div>
          <div class="text-label-lg font-label-lg text-secondary flex items-center">
            <span
              class="flex items-center mr-2"
              :class="(kpi.wechat_conv_delta || 0) >= 0 ? 'text-green-600' : 'text-red-500'"
            >
              <span class="material-symbols-outlined text-[16px]">{{
                (kpi.wechat_conv_delta || 0) >= 0 ? 'arrow_upward' : 'arrow_downward'
              }}</span>
              {{ Math.abs(kpi.wechat_conv_delta || 0) }}% </span
            >{{ t('较上月') }}
          </div>
        </div>
      </div>

      <!-- 种草 → 成单路径排行 -->
      <div class="bg-surface rounded-xl p-6 md:p-8 border border-surface-variant shadow-sm mb-8">
        <div class="flex flex-wrap items-end justify-between gap-3 mb-5">
          <div>
            <h3 class="text-headline-md font-headline-md text-on-surface">
              {{ t('种草到成单路径') }}
            </h3>
          </div>
          <div class="flex flex-wrap gap-3 text-sm">
            <span class="path-kpi path-kpi-single">
              {{
                t('单触点 {pct}%（{n} 单）', {
                  pct: pathSummary.single_pct,
                  n: pathSummary.single_touch_orders,
                })
              }}
            </span>
            <span class="path-kpi path-kpi-cross">
              {{
                t('跨渠道 {pct}%（{n} 单）', {
                  pct: pathSummary.cross_pct,
                  n: pathSummary.cross_touch_orders,
                })
              }}
            </span>
          </div>
        </div>

        <div v-if="paths.length" class="space-y-3">
          <div
            v-for="(p, idx) in paths"
            :key="`${p.from_code}-${p.to_code}-${idx}`"
            class="path-row"
            :class="{ 'path-row-single': p.single_touch }"
          >
            <div class="path-row-main">
              <div class="path-labels">
                <span :class="chipClass[p.from_tone] || chipClass.blue">{{ t(p.from_label) }}</span>
                <span class="material-symbols-outlined path-arrow">arrow_forward</span>
                <span :class="chipClass[p.to_tone] || chipClass.green">{{ t(p.to_label) }}</span>
                <span v-if="p.single_touch" class="path-same">{{ t('同渠道') }}</span>
              </div>
              <div class="path-meta">
                <strong>{{ t('{n} 单', { n: p.orders }) }}</strong>
                <span v-if="p.revenue">· {{ fmtMoney(p.revenue) }}</span>
                <span class="path-pct">{{ p.pct }}%</span>
              </div>
            </div>
            <div class="path-bar-track">
              <div
                class="path-bar-fill"
                :style="{ width: `${Math.round((100 * Number(p.orders || 0)) / pathMaxOrders)}%` }"
              />
            </div>
          </div>
        </div>
        <p v-else class="text-body-md text-on-surface-variant py-6 text-center">
          {{ t('当前窗口暂无归因路径数据') }}
        </p>
      </div>
    </template>

    <!-- High-Value Bookings Table -->
    <div class="bg-surface rounded-xl border border-surface-variant shadow-sm overflow-hidden">
      <div class="p-6 border-b border-surface-variant">
        <h3 class="text-headline-md font-headline-md text-on-surface">
          {{ t('近期高价值订单溯源列表') }}
        </h3>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr
              class="bg-surface-container-lowest text-label-lg font-label-lg text-on-surface-variant border-b border-surface-variant"
            >
              <th class="py-4 px-6 font-medium">{{ t('订单编号') }}</th>
              <th class="py-4 px-6 font-medium">{{ t('客户') }}</th>
              <th class="py-4 px-6 font-medium">{{ t('订单金额') }}</th>
              <th class="py-4 px-6 font-medium">{{ t('归因路径（首触 → 成单）') }}</th>
              <th class="py-4 px-6 font-medium text-right">{{ t('下单至入住时长') }}</th>
            </tr>
          </thead>
          <tbody class="text-body-md font-body-md text-on-surface divide-y divide-surface-variant">
            <template
              v-for="(row, idx) in highValue.slice(0, 8)"
              :key="row.order_id || row.order_no || idx"
            >
              <tr
                class="hv-row hover:bg-surface-container-lowest transition-colors"
                :class="{
                  'hv-row-clickable': !!row.order_id,
                  'hv-row-open': expandedId === row.order_id,
                }"
                @click="toggleOrderDetail(row)"
              >
                <td class="py-4 px-6 font-num-md">
                  <button
                    v-if="row.order_id"
                    type="button"
                    class="order-link"
                    @click.stop="toggleOrderDetail(row)"
                  >
                    {{ row.order_no }}
                    <span class="material-symbols-outlined">{{
                      expandedId === row.order_id ? 'expand_less' : 'expand_more'
                    }}</span>
                  </button>
                  <span v-else>{{ row.order_no }}</span>
                </td>
                <td class="py-4 px-6">{{ row.guest }}</td>
                <td class="py-4 px-6 font-num-md text-primary">{{ fmtMoney(row.amount) }}</td>
                <td class="py-4 px-6">
                  <div class="flex items-center space-x-2 flex-wrap gap-y-1">
                    <template v-for="(p, i) in row.path" :key="i">
                      <span v-if="i > 0" class="material-symbols-outlined text-[14px] text-outline"
                        >arrow_forward</span
                      >
                      <span :class="chipClass[p.tone] || chipClass.blue">
                        <span v-if="p.icon" class="material-symbols-outlined text-[12px] mr-1">{{
                          p.icon
                        }}</span>
                        {{ t(String(p.label || '')) }}</span
                      >
                    </template>
                  </div>
                </td>
                <td class="py-4 px-6 text-right text-on-surface-variant">
                  {{ fmtHours(row.hours_to_convert) }}
                </td>
              </tr>
              <tr v-if="expandedId === row.order_id" class="hv-detail-row">
                <td colspan="5" class="px-6 pb-4 pt-0">
                  <div class="hv-detail-panel" @click.stop>
                    <div v-if="detailLoading && !expandedDetail" class="hv-detail-muted">
                      {{ t('正在从订单库加载…') }}
                    </div>
                    <div v-else-if="detailError && !expandedDetail" class="hv-detail-error">
                      {{ detailError }}
                    </div>
                    <template v-else-if="expandedDetail">
                      <div class="hv-detail-head">
                        <div>
                          <div class="hv-detail-no">{{ expandedDetail.order_no }}</div>
                          <div class="hv-detail-sub">{{ staySummary(expandedDetail) }}</div>
                        </div>
                        <div class="hv-detail-pills">
                          <span class="hv-pill">{{ statusLabel(expandedDetail.status) }}</span>
                          <span class="hv-pill">{{ assignLabel(expandedDetail) }}</span>
                          <span class="hv-pill">{{ payLabel(expandedDetail.payment_status) }}</span>
                          <span class="hv-pill hv-pill-blue">{{
                            expandedDetail.channel_name || '—'
                          }}</span>
                        </div>
                      </div>

                      <div class="hv-sec">
                        <div class="hv-sec-title">{{ t('预订信息') }}</div>
                        <div class="hv-detail-grid">
                          <div>
                            <span class="hv-k">{{ t('系统订单号') }}</span>
                            <span class="hv-v mono">{{ expandedDetail.order_no }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('渠道订单号') }}</span>
                            <span class="hv-v mono">{{
                              expandedDetail.external_order_no || '—'
                            }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('预分房单号') }}</span>
                            <span class="hv-v mono">{{ expandedDetail.reception_no || '—' }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('入住类型') }}</span>
                            <span class="hv-v">{{ stayTypeLabel(expandedDetail) }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('主客') }}</span>
                            <span class="hv-v">{{ expandedDetail.guest_name || row.guest }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('手机') }}</span>
                            <span class="hv-v mono">{{ expandedDetail.phone || '—' }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('预订房型') }}</span>
                            <span class="hv-v">{{ expandedDetail.room_type_name || '—' }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('间数 / 晚数') }}</span>
                            <span class="hv-v"
                              >{{ expandedDetail.rooms || 1 }} {{ t('间') }} ·
                              {{ expandedDetail.nights || '—' }} {{ t('晚') }}</span
                            >
                          </div>
                          <div>
                            <span class="hv-k">{{ t('入离日期') }}</span>
                            <span class="hv-v"
                              >{{ fmtDate(expandedDetail.check_in) }} →
                              {{ fmtDate(expandedDetail.check_out) }}</span
                            >
                          </div>
                          <div>
                            <span class="hv-k">{{ t('预计到店') }}</span>
                            <span class="hv-v">{{ expandedDetail.arrival_time || '—' }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('成人 / 儿童') }}</span>
                            <span class="hv-v"
                              >{{ expandedDetail.adults ?? 1 }} /
                              {{ expandedDetail.children ?? 0 }}</span
                            >
                          </div>
                          <div>
                            <span class="hv-k">{{ t('创建时间') }}</span>
                            <span class="hv-v">{{
                              formatOrderDateTime(expandedDetail.created_at) || '—'
                            }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('订单金额') }}</span>
                            <span class="hv-v hv-v-em">{{
                              fmtMoney2(expandedDetail.total_amount ?? row.amount)
                            }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('定金') }}</span>
                            <span class="hv-v">{{ fmtMoney2(expandedDetail.deposit_amount) }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('客账余额') }}</span>
                            <span class="hv-v">{{
                              folioBalance(expandedDetail) == null
                                ? '—'
                                : fmtMoney2(folioBalance(expandedDetail)!)
                            }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('账本号') }}</span>
                            <span class="hv-v mono">{{
                              expandedDetail.folio_no || expandedDetail.folio?.folio_no || '—'
                            }}</span>
                          </div>
                          <div v-if="expandedDetail.voucher_code">
                            <span class="hv-k">{{ t('券码') }}</span>
                            <span class="hv-v mono">{{ expandedDetail.voucher_code }}</span>
                          </div>
                          <div v-if="expandedDetail.group_name">
                            <span class="hv-k">{{ t('团体名称') }}</span>
                            <span class="hv-v">{{ expandedDetail.group_name }}</span>
                          </div>
                          <div v-if="expandedDetail.sales_name">
                            <span class="hv-k">{{ t('销售') }}</span>
                            <span class="hv-v">{{ expandedDetail.sales_name }}</span>
                          </div>
                        </div>
                        <p v-if="expandedDetail.note" class="hv-note">
                          {{ t('备注：') }}{{ expandedDetail.note }}
                        </p>
                      </div>

                      <div class="hv-sec">
                        <div class="hv-sec-title">{{ t('分房与入住') }}</div>
                        <div class="hv-detail-grid">
                          <div>
                            <span class="hv-k">{{ t('分房状态') }}</span>
                            <span class="hv-v">{{ assignLabel(expandedDetail) }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('预分房号') }}</span>
                            <span class="hv-v mono">{{
                              expandedDetail.pre_room_no || t('未预分')
                            }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('在住房号') }}</span>
                            <span class="hv-v mono">{{ expandedDetail.stay_room_no || '—' }}</span>
                          </div>
                          <div>
                            <span class="hv-k">{{ t('入住记录') }}</span>
                            <span class="hv-v">{{
                              t('{n} 条', { n: checkinRows(expandedDetail).length })
                            }}</span>
                          </div>
                        </div>
                        <div v-if="checkinRows(expandedDetail).length" class="hv-mini-table-wrap">
                          <table class="hv-mini-table">
                            <thead>
                              <tr>
                                <th>{{ t('入住人') }}</th>
                                <th>{{ t('房号') }}</th>
                                <th>{{ t('状态') }}</th>
                                <th>{{ t('证件') }}</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr
                                v-for="ci in checkinRows(expandedDetail)"
                                :key="ci.id || ci.room_no"
                              >
                                <td>{{ ci.guest_name || '—' }}</td>
                                <td class="mono">{{ ci.room_no || '—' }}</td>
                                <td>{{ ci.status || '—' }}</td>
                                <td class="mono">{{ ci.id_doc_mask || '—' }}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                        <div
                          v-else-if="groupLines(expandedDetail).length"
                          class="hv-mini-table-wrap"
                        >
                          <table class="hv-mini-table">
                            <thead>
                              <tr>
                                <th>#</th>
                                <th>{{ t('客人') }}</th>
                                <th>{{ t('房型') }}</th>
                                <th>{{ t('房号') }}</th>
                                <th>{{ t('状态') }}</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="line in groupLines(expandedDetail)" :key="line.id">
                                <td>{{ line.line_no }}</td>
                                <td>{{ line.guest_name || '—' }}</td>
                                <td>{{ line.room_type_name || '—' }}</td>
                                <td class="mono">{{ line.room_no || t('待分配') }}</td>
                                <td>{{ t(LINE_ST[line.status] || line.status) }}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                        <p v-else class="hv-detail-muted hv-hint">
                          {{
                            t(
                              '订单订 {n} 间；当前尚无入住/团体分房明细（可能未全部分房或入住）。',
                              { n: expandedDetail.rooms || 1 },
                            )
                          }}
                        </p>
                      </div>

                      <div v-if="roomItems(expandedDetail).length" class="hv-sec">
                        <div class="hv-sec-title">{{ t('订单明细') }}</div>
                        <div class="hv-mini-table-wrap">
                          <table class="hv-mini-table">
                            <thead>
                              <tr>
                                <th>{{ t('项目') }}</th>
                                <th>{{ t('数量') }}</th>
                                <th>{{ t('单价') }}</th>
                                <th>{{ t('金额') }}</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr
                                v-for="it in roomItems(expandedDetail)"
                                :key="it.id || it.description"
                              >
                                <td>
                                  {{ localizeLineDesc(it.description) || it.item_type || '—' }}
                                </td>
                                <td>{{ it.qty ?? '—' }}</td>
                                <td>{{ fmtMoney2(it.unit_price) }}</td>
                                <td class="hv-v-em">{{ fmtMoney2(it.amount) }}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>

                      <div v-if="row.path?.length" class="hv-sec hv-sec-last">
                        <div class="hv-sec-title">{{ t('本单归因路径') }}</div>
                        <div class="flex items-center space-x-2 flex-wrap gap-y-1">
                          <template v-for="(p, i) in row.path" :key="'attr-' + i">
                            <span
                              v-if="i > 0"
                              class="material-symbols-outlined text-[14px] text-outline"
                              >arrow_forward</span
                            >
                            <span :class="chipClass[p.tone] || chipClass.blue">
                              {{ t(String(p.label || '')) }}</span
                            >
                          </template>
                          <span class="hv-detail-muted" style="margin-left: 0.5rem">
                            {{ t('下单至入住') }} {{ fmtHours(row.hours_to_convert) }}</span
                          >
                        </div>
                      </div>
                    </template>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hv-row-clickable {
  cursor: pointer;
}
.hv-row-open {
  background: #f5f8ff;
}
.order-link {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  color: #005bbf;
  font-weight: 600;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font: inherit;
}
.order-link:hover {
  text-decoration: underline;
}
.order-link .material-symbols-outlined {
  font-size: 18px;
  opacity: 0.75;
}
.hv-detail-panel {
  margin-top: 0.15rem;
  padding: 1rem 1.1rem 1.05rem;
  border-radius: 0.75rem;
  border: 1px solid #d6e3f8;
  background: linear-gradient(180deg, #f7faff 0%, #ffffff 55%);
}
.hv-detail-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem 1rem;
  margin-bottom: 0.9rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e4ecf7;
}
.hv-detail-no {
  font-size: 1rem;
  font-weight: 700;
  color: #1c1b1f;
  letter-spacing: 0.01em;
}
.hv-detail-sub {
  margin-top: 0.2rem;
  font-size: 0.8rem;
  color: #79747e;
}
.hv-detail-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.hv-pill {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: #eef1f5;
  color: #49454f;
}
.hv-pill-blue {
  background: #e8f0fe;
  color: #005bbf;
}
.hv-sec {
  margin-bottom: 0.95rem;
}
.hv-sec-last {
  margin-bottom: 0;
}
.hv-sec-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: #1c1b1f;
  margin-bottom: 0.55rem;
}
.hv-detail-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.7rem 1rem;
}
@media (max-width: 1100px) {
  .hv-detail-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 760px) {
  .hv-detail-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.hv-k {
  display: block;
  font-size: 0.68rem;
  color: #79747e;
  margin-bottom: 0.12rem;
}
.hv-v {
  display: block;
  font-size: 0.86rem;
  color: #1c1b1f;
  font-weight: 600;
  line-height: 1.35;
  word-break: break-word;
}
.hv-v-em {
  color: #005bbf;
}
.mono {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.82rem;
}
.hv-note {
  margin: 0.65rem 0 0;
  font-size: 0.78rem;
  color: #49454f;
  line-height: 1.45;
  padding: 0.45rem 0.6rem;
  background: #f4f6f8;
  border-radius: 0.45rem;
}
.hv-hint {
  margin: 0.5rem 0 0;
}
.hv-mini-table-wrap {
  margin-top: 0.55rem;
  overflow-x: auto;
  border: 1px solid #e7e0ec;
  border-radius: 0.55rem;
}
.hv-mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}
.hv-mini-table th,
.hv-mini-table td {
  padding: 0.45rem 0.65rem;
  text-align: left;
  border-bottom: 1px solid #f0ebf4;
}
.hv-mini-table th {
  background: #f8f6fb;
  color: #79747e;
  font-weight: 600;
}
.hv-mini-table tr:last-child td {
  border-bottom: none;
}
.hv-detail-muted {
  font-size: 0.78rem;
  color: #79747e;
}
.hv-detail-error {
  font-size: 0.85rem;
  color: #b3261e;
}
.path-kpi {
  display: inline-flex;
  align-items: baseline;
  gap: 0.25rem;
  padding: 0.35rem 0.75rem;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: 0.82rem;
}
.path-kpi em {
  font-style: normal;
  font-weight: 500;
  opacity: 0.75;
}
.path-kpi-single {
  background: #f1f3f5;
  color: #49454f;
}
.path-kpi-cross {
  background: #e8f0fe;
  color: #005bbf;
}
.path-row {
  padding: 0.75rem 0.9rem;
  border: 1px solid #e7e0ec;
  border-radius: 0.75rem;
  background: #fff;
}
.path-row-single {
  background: #faf9fb;
  border-color: #ece8f0;
}
.path-row-main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem 1rem;
  margin-bottom: 0.45rem;
}
.path-labels {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
}
.path-arrow {
  font-size: 16px;
  color: #79747e;
}
.path-same {
  font-size: 0.7rem;
  color: #79747e;
  padding: 0.1rem 0.4rem;
  border: 1px dashed #cac4d0;
  border-radius: 0.35rem;
}
.path-meta {
  font-size: 0.85rem;
  color: #49454f;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  white-space: nowrap;
}
.path-meta strong {
  color: #1c1b1f;
}
.path-pct {
  color: #79747e;
  min-width: 2.5rem;
  text-align: right;
}
.path-bar-track {
  height: 6px;
  border-radius: 999px;
  background: #eee8f4;
  overflow: hidden;
}
.path-bar-fill {
  height: 100%;
  border-radius: 999px;
  background: #5b8def;
  min-width: 4px;
  transition: width 0.25s ease;
}
.path-row-single .path-bar-fill {
  background: #b0a8b9;
}
.ai-insight-body :deep(.ai-insight) {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 720px) {
  .ai-insight-body :deep(.ai-insight) {
    grid-template-columns: 1fr;
  }
}
.ai-insight-body :deep(.ai-insight-sec) {
  border-radius: 10px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.72);
}
.ai-insight-body :deep(.ai-insight-h) {
  font-size: 12px;
  font-weight: 750;
  margin-bottom: 6px;
  color: #1c1b1f;
}
.ai-insight-body :deep(ul) {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 13px;
  line-height: 1.55;
  color: #49454f;
}
.ai-insight-body :deep(li strong) {
  color: #1c1b1f;
}
</style>
