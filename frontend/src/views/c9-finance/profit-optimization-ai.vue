<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 智能利润优化建议：KPI、毛利到净利瀑布图、成本结构与触发式 AI 解读
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import OrderAttribution from '../c5-frontdesk/order-attribution.vue'
import BoardAiPanel from '../../components/BoardAiPanel.vue'

const props = withDefaults(
  defineProps<{
    /** 嵌入经营分析工作台时隐藏页头跳转按钮 */
    embedded?: boolean
    /** Tab3：底部展示高价值订单溯源 */
    showHighValueOrders?: boolean
  }>(),
  { embedded: false, showHighValueOrders: false },
)

const router = useRouter()

type WaterfallStep = {
  key: string
  label: string
  amount: number
  kind: 'total' | 'down' | 'result'
  color: string
  note?: string
}

type CostItem = {
  name: string
  amount: string
  pct: number
  color: string
  dot: string
  note: string
}

const kpis = ref<any[]>([
  {
    label: t('毛收入'),
    value: '—',
    delta: t('加载中'),
    deltaClass: 'text-primary',
    highlight: false,
  },
  {
    label: t('净利润'),
    value: '—',
    delta: t('加载中'),
    tag: t('AI 优化'),
    deltaClass: 'text-primary',
    highlight: true,
  },
  {
    label: t('净利润率'),
    value: '—',
    delta: t('加载中'),
    deltaClass: 'text-tertiary',
    highlight: false,
  },
])

/** 瀑布拆解原始数值（毛收入 → 分项扣减 → 净利）；由 financeBoard.profit_waterfall 填充 */
const waterfallRaw = ref<WaterfallStep[]>([])

const costItems = ref<CostItem[]>([])

const period = ref(t('本月'))

const DOWN_COLORS = ['bg-error/70', 'bg-error/60', 'bg-error/50', 'bg-error/40', 'bg-error/30']

function colorForKind(kind: string, downIdx: number) {
  if (kind === 'total') return 'bg-secondary-container'
  if (kind === 'result') return 'bg-primary'
  return DOWN_COLORS[downIdx % DOWN_COLORS.length]
}

function money(n: number) {
  return `¥${Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function shortMoney(n: number) {
  const abs = Math.abs(n)
  if (abs >= 1000) return `${Math.round(abs / 1000)}k`
  return String(abs)
}

/** 瀑布图布局：浮动柱 + 顶标 + 连接桥 */
const waterfallBars = computed(() => {
  const steps = waterfallRaw.value
  const gross = Math.max(
    ...steps
      .filter((s) => s.kind === 'total' || s.kind === 'result')
      .map((s) => Math.abs(s.amount)),
    1,
  )
  let running = 0
  const bars: Array<{
    key: string
    label: string
    kind: string
    color: string
    note?: string
    topPct: number
    heightPct: number
    bridgeTopPct: number
    showBridge: boolean
    valueText: string
    shortText: string
    isPositive: boolean
  }> = []

  for (let i = 0; i < steps.length; i++) {
    const s = steps[i]
    let top = 0
    let bottom = 0
    if (s.kind === 'total' || s.kind === 'result') {
      bottom = 0
      top = Math.abs(s.amount)
      running = top
    } else {
      const ded = Math.abs(s.amount)
      top = running
      bottom = Math.max(0, running - ded)
      running = bottom
    }
    const heightPct = Math.max(2.5, ((top - bottom) / gross) * 100)
    const topPct = (1 - top / gross) * 100
    const prev = bars[i - 1]
    // 连接线落在「上一段结余」高度 = 本段柱顶
    const bridgeTopPct = topPct
    bars.push({
      key: s.key,
      label: s.label,
      kind: s.kind,
      color: s.color,
      note: s.note,
      topPct,
      heightPct,
      bridgeTopPct,
      showBridge: Boolean(prev) && (s.kind === 'down' || s.kind === 'result'),
      valueText: s.kind === 'down' ? `-${shortMoney(s.amount)}` : shortMoney(s.amount),
      shortText: s.kind === 'down' ? `-${shortMoney(s.amount)}` : shortMoney(s.amount),
      isPositive: s.kind !== 'down',
    })
  }
  return {
    bars,
    gross,
    yTicks: [gross, Math.round(gross * 0.75), Math.round(gross * 0.5), Math.round(gross * 0.25), 0],
  }
})

const deductionTotal = computed(() =>
  waterfallRaw.value.filter((s) => s.kind === 'down').reduce((a, s) => a + Math.abs(s.amount), 0),
)

const netAmount = computed(() => waterfallRaw.value.find((s) => s.kind === 'result')?.amount || 0)
const grossAmount = computed(() => waterfallRaw.value.find((s) => s.kind === 'total')?.amount || 0)

function syncCostFromWaterfall(gross: number, steps: WaterfallStep[]) {
  const downs = steps.filter((s) => s.kind === 'down')
  costItems.value = downs.map((s) => {
    const abs = Math.abs(s.amount)
    const pct = Math.round((abs / Math.max(gross, 1)) * 100)
    return {
      name: t(s.label),
      amount: money(abs),
      pct,
      color: s.color,
      dot: s.color,
      note: s.note
        ? t('{note} · 占毛利 {pct}%。', { note: s.note, pct })
        : t('占毛利 {pct}%。', { pct }),
    }
  })
}

async function load() {
  try {
    const board = await api.financeBoard(hotelStore.hotelId)
    const wf = board?.profit_waterfall
    if (wf?.length) {
      let downIdx = 0
      const steps: WaterfallStep[] = wf.map((s: any) => {
        const kind = (s.kind || 'down') as WaterfallStep['kind']
        const color = colorForKind(kind, kind === 'down' ? downIdx++ : 0)
        return {
          key: s.key || s.label,
          // 后端已按 X-Locale 翻译；再 t() 一次兼容未走 i18n 的旧响应
          label: t(String(s.label || '')),
          amount: Number(s.amount || 0),
          kind,
          color,
          note: s.note || undefined,
        }
      })
      waterfallRaw.value = steps
      const gross = Number(
        board?.profit_summary?.gross ?? steps.find((s) => s.kind === 'total')?.amount ?? 0,
      )
      syncCostFromWaterfall(gross, steps)
    }
    const ps = board?.profit_summary
    if (ps) {
      kpis.value = [
        {
          label: t('毛收入'),
          value: money(ps.gross),
          delta: t('{n} 种支付', { n: board.payment_by_method?.length || 0 }),
          deltaClass: 'text-primary',
          highlight: false,
        },
        {
          label: t('净利润'),
          value: money(ps.net),
          delta: t('按渠道/运营估算'),
          tag: t('AI 优化'),
          deltaClass: 'text-primary',
          highlight: true,
        },
        {
          label: t('净利润率'),
          value: `${ps.margin_pct ?? 0}%`,
          delta: t('按渠道/运营估算'),
          deltaClass: 'text-tertiary',
          highlight: false,
        },
      ]
    }
    if (board?.period_label) {
      period.value = String(board.period_label)
    } else {
      const trend = board?.revenue_trend || []
      if (trend.length) {
        period.value = t('近 {n} 日 · {range}', {
          n: trend.length,
          range: `${trend[0].biz_date} ~ ${trend[trend.length - 1].biz_date}`,
        })
      }
    }
  } catch {
    waterfallRaw.value = []
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page" :class="{ 'is-embedded': props.embedded }">
    <!-- Header Section（对齐原型：mb-4、成对 font/text、字重） -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-4 gap-4">
      <div v-if="!props.embedded">
        <header class="page-head" style="margin-bottom: 0">
          <h1>{{ t('智能利润优化建议') }}</h1>
          <p>{{ t('AI 驱动的净利、成本结构与可落地增效策略分析。') }}</p>
        </header>
      </div>
      <div class="flex gap-3 flex-wrap justify-end" :class="{ 'ml-auto': props.embedded }">
        <template v-if="!props.embedded">
          <button
            type="button"
            class="px-4 py-2 rounded-lg border border-outline-variant font-label-lg text-label-lg text-on-surface hover:bg-surface-container-low transition-colors"
            @click="router.push({ path: '/analytics', query: { tab: 'insights' } })"
          >
            {{ t('← 返回专题洞察') }}
          </button>
          <button
            type="button"
            class="px-4 py-2 rounded-lg border border-outline-variant font-label-lg text-label-lg text-on-surface hover:bg-surface-container-low transition-colors"
            @click="router.push({ path: '/analytics', query: { tab: 'insights' } })"
          >
            {{ t('专题洞察') }}
          </button>
        </template>
        <select
          class="bg-surface border border-outline-variant rounded-lg px-4 py-2 font-label-lg text-label-lg text-on-surface focus:ring-primary focus:border-primary"
        >
          <option>{{ period }}</option>
          <option>{{ t('上月') }}</option>
          <option>Q3 2023</option>
        </select>
        <button
          type="button"
          class="bg-surface-container border border-outline-variant rounded-lg px-4 py-2 font-label-lg text-label-lg text-on-surface hover:bg-surface-container-high transition-colors flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-[18px]">download</span>{{ t('导出') }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
      <!-- KPI Cards -->
      <template v-for="(k, i) in kpis" :key="i">
        <div
          v-if="!k.highlight"
          class="lg:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col justify-between"
        >
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="font-label-lg text-label-lg text-secondary uppercase tracking-wider">{{
                k.label
              }}</span>
            </div>
            <div class="font-num-xl text-num-xl text-on-surface">{{ k.value }}</div>
          </div>
          <div class="mt-4 flex items-center font-label-lg text-label-lg" :class="k.deltaClass">
            {{ k.delta }}
          </div>
        </div>
        <div
          v-else
          class="lg:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col justify-between ai-tinge relative overflow-hidden"
        >
          <div
            class="absolute inset-0 bg-gradient-to-br from-primary-fixed/20 to-transparent pointer-events-none"
          ></div>
          <div class="relative z-10">
            <div class="flex items-center justify-between mb-2">
              <span class="font-label-lg text-label-lg text-on-surface-variant font-bold">{{
                k.label
              }}</span>
            </div>
            <div class="font-num-xl text-num-xl text-primary">{{ k.value }}</div>
          </div>
          <div
            class="relative z-10 mt-4 flex items-center font-label-lg text-label-lg"
            :class="k.deltaClass"
          >
            {{ k.delta }}
            <span
              v-if="k.tag"
              class="ml-2 bg-primary/10 text-primary px-2 py-0.5 rounded text-[12px] font-bold"
              >{{ k.tag }}</span
            >
          </div>
        </div>
      </template>

      <!-- 毛利到净利瀑布图 -->
      <div
        class="lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
      >
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h3 class="font-headline-md text-headline-md text-on-surface">
            {{ t('毛利到净利拆解') }}
          </h3>
          <div class="flex flex-wrap items-center gap-3 font-label-lg text-[11px] text-secondary">
            <span class="inline-flex items-center gap-1.5"
              ><span class="w-2.5 h-2.5 rounded-sm bg-secondary-container"></span
              >{{ t('收入/净利') }}</span
            >
            <span class="inline-flex items-center gap-1.5"
              ><span class="w-2.5 h-2.5 rounded-sm bg-error/60"></span>{{ t('成本扣减') }}</span
            >
            <span class="text-on-surface-variant">{{ t('单位示意 · 千元') }}</span>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-3 mb-5">
          <div class="rounded-lg bg-surface border border-outline-variant/40 px-3 py-2">
            <div class="font-label-lg text-[11px] text-secondary uppercase tracking-wider">
              {{ t('毛收入') }}
            </div>
            <div class="font-num-md text-num-md text-on-surface font-bold">
              {{ money(grossAmount) }}
            </div>
          </div>
          <div class="rounded-lg bg-surface border border-outline-variant/40 px-3 py-2">
            <div class="font-label-lg text-[11px] text-secondary uppercase tracking-wider">
              {{ t('成本合计') }}
            </div>
            <div class="font-num-md text-num-md text-error font-bold">
              -{{ money(deductionTotal).slice(1) }}
            </div>
          </div>
          <div class="rounded-lg bg-primary/5 border border-primary/20 px-3 py-2">
            <div class="font-label-lg text-[11px] text-secondary uppercase tracking-wider">
              {{ t('净利') }}
            </div>
            <div class="font-num-md text-num-md text-primary font-bold">{{ money(netAmount) }}</div>
          </div>
        </div>

        <div class="relative h-72 pl-10 pr-2">
          <!-- Y 轴刻度 -->
          <div
            class="absolute left-0 top-2 bottom-10 flex flex-col justify-between font-num-md text-[10px] text-outline w-9 text-right pr-1"
          >
            <span v-for="(item, ti) in waterfallBars.yTicks" :key="ti">{{ shortMoney(t) }}</span>
          </div>

          <div class="h-full relative border-l border-b border-outline-variant/60 pb-10">
            <!-- 虚线网格 -->
            <div
              class="absolute inset-0 bottom-10 flex flex-col justify-between pointer-events-none z-0"
            >
              <div
                v-for="n in 5"
                :key="n"
                class="border-t border-dashed border-outline/25 w-full"
              ></div>
            </div>

            <div
              class="absolute inset-x-0 top-0 bottom-10 flex items-stretch gap-1 sm:gap-2 px-1 z-10"
            >
              <div
                v-for="b in waterfallBars.bars"
                :key="b.key"
                class="relative flex-1 min-w-0 group"
              >
                <!-- 瀑布连接：从上一段结余水平接到本柱 -->
                <div
                  v-if="b.showBridge"
                  class="absolute -left-1 right-1/2 h-px border-t border-dashed border-outline-variant z-0 pointer-events-none"
                  :style="{ top: b.bridgeTopPct + '%' }"
                ></div>

                <!-- 柱体 -->
                <div
                  class="absolute left-1/2 -translate-x-1/2 w-[72%] max-w-[52px] rounded-t-sm shadow-sm transition-opacity group-hover:opacity-90"
                  :class="[
                    b.color,
                    b.kind === 'result' ? 'ring-2 ring-primary/30' : '',
                    b.kind === 'down' ? 'rounded-sm' : 'rounded-t-sm',
                  ]"
                  :style="{ top: b.topPct + '%', height: b.heightPct + '%' }"
                >
                  <div
                    class="absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap font-num-md text-[11px] font-bold"
                    :class="
                      b.isPositive
                        ? b.kind === 'result'
                          ? 'text-primary'
                          : 'text-on-surface'
                        : 'text-error'
                    "
                  >
                    {{ b.valueText }}
                  </div>
                </div>

                <!-- X 轴标签（仅类目名，单行） -->
                <div
                  class="absolute left-0 right-0 text-center font-label-lg text-[11px] leading-tight px-0.5 truncate"
                  :class="b.kind === 'result' ? 'text-primary font-bold' : 'text-secondary'"
                  style="bottom: -2.35rem"
                  :title="b.label"
                >
                  {{ b.label }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 成本结构 -->
      <div
        class="lg:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col"
      >
        <h3 class="font-headline-md text-headline-md text-on-surface mb-4">{{ t('成本结构') }}</h3>
        <div class="flex-1 overflow-y-auto pr-2 space-y-3 max-h-[420px]">
          <div
            v-for="(c, i) in costItems"
            :key="i"
            class="p-3 bg-surface rounded-lg border border-outline-variant/30"
          >
            <div class="flex justify-between items-center mb-1 gap-2">
              <span
                class="font-label-lg text-label-lg text-on-surface flex items-center gap-2 min-w-0"
              >
                <span class="w-2 h-2 rounded-full shrink-0" :class="c.dot"></span>
                <span class="truncate">{{ c.name }}</span>
              </span>
              <span class="font-num-md text-num-md text-on-surface shrink-0">{{ c.amount }}</span>
            </div>
            <div class="w-full bg-surface-container h-1.5 rounded-full overflow-hidden mt-2">
              <div
                class="h-full transition-all"
                :class="c.color"
                :style="{ width: Math.min(c.pct, 100) + '%' }"
              ></div>
            </div>
            <p class="font-body-md text-[12px] text-secondary mt-2">{{ c.note }}</p>
          </div>
        </div>
      </div>

      <!-- 触发式利润解读（保留 BoardAiPanel；种子策略卡片已下线） -->
      <div class="lg:col-span-12 mt-4">
        <BoardAiPanel
          kind="profit_insights"
          :title="t('利润策略 AI 解读')"
          idle=""
          :run-label="t('生成利润解读')"
          :rerun-label="t('重新解读')"
          :wait-label="t('正在分析利润策略与潜在增收…')"
        />
      </div>
    </div>

    <div v-if="props.showHighValueOrders" class="mt-8 pt-6 border-t border-outline-variant">
      <OrderAttribution orders-only embedded />
    </div>
  </div>
</template>
