<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 渠道预订趋势：可选时间窗 · 订单库聚合 · 统计叠在图内
 */
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'

const DAY_OPTS = [
  { value: 7, label: t('近 7 天') },
  { value: 14, label: t('近 14 天') },
  { value: 30, label: t('近 30 天') },
  { value: 60, label: t('近 60 天') },
  { value: 90, label: t('近 90 天') },
] as const

const days = ref(30)
const loading = ref(false)
const loadError = ref('')
const trendRaw = ref<any[]>([])
const hoverTrend = ref<number | null>(null)

const SEGS = [
  { key: 'direct', label: t('直接预订'), color: '#005bbf' },
  { key: 'xhs', label: t('小红书'), color: '#8c33b3' },
  { key: 'douyin', label: t('抖音/团购'), color: '#ba1a1a' },
  { key: 'ota', label: 'OTA', color: '#79747e' },
] as const

const trendBars = computed(() =>
  (trendRaw.value || []).map((r: any, i: number) => {
    const direct = Number(r.direct) || 0
    const xhs = Number(r.xhs) || 0
    const douyin = Number(r.douyin) || 0
    const ota = Number(r.ota) || 0
    const total = Number(r.total) || 0 || direct + xhs + douyin + ota
    return {
      day: i + 1,
      label: r.label || t('{n}日', { n: i + 1 }),
      direct,
      xhs,
      douyin,
      ota,
      total,
    }
  }),
)

const trendMax = computed(() => Math.max(1, ...trendBars.value.map((b) => b.total)))

const TW = 720
const TH = 260
const TPAD = { l: 48, r: 16, t: 20, b: 44 }
const trendPlotH = TH - TPAD.t - TPAD.b
const trendPlotW = TW - TPAD.l - TPAD.r
const barGap = 3
const barW = computed(() => {
  const n = Math.max(1, trendBars.value.length)
  return (trendPlotW - barGap * (n - 1)) / n
})

function trendX(i: number) {
  return TPAD.l + i * (barW.value + barGap)
}
function trendY(v: number) {
  return TPAD.t + trendPlotH * (1 - v / trendMax.value)
}
function trendH(v: number) {
  return (trendPlotH * v) / trendMax.value
}

const yTicks = computed(() => [0, 0.25, 0.5, 0.75, 1].map((r) => Math.round(trendMax.value * r)))

const labelStep = computed(() => {
  const n = trendBars.value.length
  if (n <= 10) return 1
  if (n <= 20) return 2
  if (n <= 40) return 5
  return 7
})

function showLabel(b: { day: number }, i: number, n: number) {
  const step = labelStep.value
  return b.day === 1 || b.day % step === 0 || i === n - 1
}

const stats = computed(() => {
  const bars = trendBars.value
  const sum = { direct: 0, xhs: 0, douyin: 0, ota: 0, total: 0 }
  for (const b of bars) {
    sum.direct += b.direct
    sum.xhs += b.xhs
    sum.douyin += b.douyin
    sum.ota += b.ota
    sum.total += b.total
  }
  const n = Math.max(1, bars.length)
  const peak = bars.reduce(
    (best, b) => (b.total > (best?.total ?? -1) ? b : best),
    null as (typeof bars)[0] | null,
  )
  const half = Math.floor(n / 2)
  const recent = bars.slice(half).reduce((s, b) => s + b.total, 0)
  const earlier = bars.slice(0, half).reduce((s, b) => s + b.total, 0)
  const deltaPct =
    earlier > 0 ? Math.round(((recent - earlier) / earlier) * 100) : recent > 0 ? 100 : 0
  const channels = SEGS.map((s) => {
    const value = sum[s.key]
    const pct = sum.total > 0 ? Math.round((value / sum.total) * 1000) / 10 : 0
    return { ...s, value, pct }
  }).sort((a, b) => b.value - a.value)

  return {
    total: sum.total,
    avgDaily: Math.round((sum.total / n) * 10) / 10,
    peakLabel: peak?.label || '—',
    peakTotal: peak?.total ?? 0,
    deltaPct,
    channels,
  }
})

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await api.ordersChannelInsight(hotelStore.hotelId, days.value, null)
    trendRaw.value = Array.isArray(data?.trend) ? data.trend : []
  } catch (e: any) {
    trendRaw.value = []
    loadError.value = e?.message || t('趋势加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(days, load)
</script>

<template>
  <div class="trend-panel">
    <div class="trend-head">
      <div>
        <h3 class="trend-title">
          <span class="material-symbols-outlined">stacked_bar_chart</span>
          {{ t('渠道预订趋势') }}
        </h3>
      </div>
      <div class="day-tabs" role="tablist" :aria-label="t('时间范围')">
        <button
          v-for="opt in DAY_OPTS"
          :key="opt.value"
          type="button"
          role="tab"
          class="day-tab"
          :class="{ active: days === opt.value }"
          :aria-selected="days === opt.value"
          :disabled="loading"
          @click="days = opt.value"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <p v-if="loading && !trendBars.length" class="trend-hint">{{ t('加载中…') }}</p>
    <p v-else-if="loadError" class="trend-err">{{ loadError }}</p>

    <div v-else class="chart-frame" :class="{ dim: loading }">
      <!-- 统计叠在图内顶部，非独立侧栏 -->
      <div class="inchart-stats" :aria-label="t('区间汇总')">
        <div class="hero">
          <span class="hero-k">{{ t('合计') }}</span>
          <span class="hero-v">{{ stats.total }}</span>
          <span class="hero-u">{{ t('间夜') }}</span>
        </div>
        <div class="ch-row">
          <span v-for="c in stats.channels" :key="c.key" class="ch-chip">
            <i :style="{ background: c.color }" />
            {{ c.label }} <b>{{ c.value }}</b>
            <em>{{ c.pct }}%</em>
          </span>
        </div>
        <div class="meta-row">
          <span
            >{{ t('平均每天约') }} <b>{{ stats.avgDaily }}</b> {{ t('间夜') }}</span
          >
          <span
            >{{ t('最多一天：') }} <b>{{ stats.peakLabel }}</b
            >（{{ stats.peakTotal }} {{ t('间') }}{{ t('夜）') }}</span
          >
          <span>
            {{ t('后半段比前半段') }}
            <b :class="stats.deltaPct >= 0 ? 'up' : 'down'">
              {{ stats.deltaPct >= 0 ? t('多') : t('少') }} {{ Math.abs(stats.deltaPct) }}%
            </b>
          </span>
        </div>
      </div>

      <svg class="chart-svg" :viewBox="`0 0 ${TW} ${TH}`" preserveAspectRatio="xMidYMid meet">
        <g v-for="(item, ti) in yTicks" :key="'yt-' + ti">
          <line
            :x1="TPAD.l"
            :y1="trendY(t)"
            :x2="TW - TPAD.r"
            :y2="trendY(t)"
            stroke="#e7e0ec"
            stroke-width="1"
            :stroke-dasharray="t === 0 ? '0' : '4 3'"
          />
          <text :x="TPAD.l - 8" :y="trendY(t) + 3" text-anchor="end" class="axis-tick">
            {{ t }}
          </text>
        </g>
        <line
          :x1="TPAD.l"
          :y1="TPAD.t"
          :x2="TPAD.l"
          :y2="TH - TPAD.b"
          stroke="#79747e"
          stroke-width="1.5"
        />
        <line
          :x1="TPAD.l"
          :y1="TH - TPAD.b"
          :x2="TW - TPAD.r"
          :y2="TH - TPAD.b"
          stroke="#79747e"
          stroke-width="1.5"
        />
        <text
          :x="14"
          :y="TH / 2"
          text-anchor="middle"
          class="axis-lab"
          :transform="`rotate(-90, 14, ${TH / 2})`"
        >
          {{ t('预订量') }}
        </text>

        <g v-for="(b, i) in trendBars" :key="b.day">
          <rect
            :x="trendX(i)"
            :y="trendY(b.direct)"
            :width="barW"
            :height="trendH(b.direct)"
            fill="#005bbf"
            rx="1"
            class="seg"
            @mouseenter="hoverTrend = i"
            @mouseleave="hoverTrend = null"
          />
          <rect
            :x="trendX(i)"
            :y="trendY(b.direct + b.xhs)"
            :width="barW"
            :height="trendH(b.xhs)"
            fill="#8c33b3"
            class="seg"
            @mouseenter="hoverTrend = i"
            @mouseleave="hoverTrend = null"
          />
          <rect
            :x="trendX(i)"
            :y="trendY(b.direct + b.xhs + b.douyin)"
            :width="barW"
            :height="trendH(b.douyin)"
            fill="#ba1a1a"
            class="seg"
            @mouseenter="hoverTrend = i"
            @mouseleave="hoverTrend = null"
          />
          <rect
            :x="trendX(i)"
            :y="trendY(b.total)"
            :width="barW"
            :height="trendH(b.ota)"
            fill="#79747e"
            rx="1"
            class="seg"
            @mouseenter="hoverTrend = i"
            @mouseleave="hoverTrend = null"
          />
          <text
            v-if="showLabel(b, i, trendBars.length)"
            :x="trendX(i) + barW / 2"
            :y="TH - TPAD.b + 16"
            text-anchor="middle"
            class="axis-tick"
          >
            {{ b.label }}
          </text>
        </g>

        <g v-if="hoverTrend !== null">
          <template v-for="(b, i) in trendBars" :key="'tip-' + b.day">
            <g v-if="i === hoverTrend">
              <rect
                :x="Math.min(trendX(i) + barW + 6, TW - 130)"
                :y="Math.max(trendY(b.total) - 8, TPAD.t)"
                width="118"
                height="88"
                rx="6"
                fill="#313033"
              />
              <text
                :x="Math.min(trendX(i) + barW + 14, TW - 122)"
                :y="Math.max(trendY(b.total) + 10, TPAD.t + 18)"
                fill="#fff"
                font-size="11"
                font-weight="600"
              >
                {{ b.label }} · {{ t('合计') }} {{ b.total }}
              </text>
              <text
                :x="Math.min(trendX(i) + barW + 14, TW - 122)"
                :y="Math.max(trendY(b.total) + 26, TPAD.t + 34)"
                fill="#a8c7fa"
                font-size="10"
              >
                {{ t('直订') }} {{ b.direct }}
              </text>
              <text
                :x="Math.min(trendX(i) + barW + 14, TW - 122)"
                :y="Math.max(trendY(b.total) + 40, TPAD.t + 48)"
                fill="#e9b3ff"
                font-size="10"
              >
                {{ t('小红书') }} {{ b.xhs }}
              </text>
              <text
                :x="Math.min(trendX(i) + barW + 14, TW - 122)"
                :y="Math.max(trendY(b.total) + 54, TPAD.t + 62)"
                fill="#ffb4ab"
                font-size="10"
              >
                {{ t('抖音') }} {{ b.douyin }}
              </text>
              <text
                :x="Math.min(trendX(i) + barW + 14, TW - 122)"
                :y="Math.max(trendY(b.total) + 68, TPAD.t + 76)"
                fill="#cac4d0"
                font-size="10"
              >
                OTA {{ b.ota }}
              </text>
            </g>
          </template>
        </g>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.trend-panel {
  background: #fff;
  border: 1px solid rgba(202, 196, 208, 0.55);
  border-radius: 0.85rem;
  padding: 1.15rem 1.25rem 1.25rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.trend-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem 1rem;
  margin-bottom: 0.75rem;
}
.trend-title {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 1.05rem;
  font-weight: 700;
  color: #1c1b1f;
}
.trend-title .material-symbols-outlined {
  color: #005bbf;
  font-size: 1.25rem;
}
.trend-sub {
  margin: 0.25rem 0 0;
  font-size: 0.75rem;
  color: #79747e;
}
.day-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.day-tab {
  border: 1px solid rgba(202, 196, 208, 0.7);
  background: #fff;
  color: #49454f;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.35rem 0.65rem;
  border-radius: 0.45rem;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s,
    color 0.15s;
}
.day-tab:hover:not(:disabled) {
  border-color: rgba(0, 91, 191, 0.45);
  color: #005bbf;
}
.day-tab.active {
  background: #005bbf;
  border-color: #005bbf;
  color: #fff;
}
.day-tab:disabled {
  opacity: 0.55;
  cursor: wait;
}
.trend-hint,
.trend-err {
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
}
.trend-err {
  color: #ba1a1a;
}

.chart-frame {
  border: 1px solid rgba(202, 196, 208, 0.45);
  border-radius: 0.75rem;
  background: #f7f2fa;
  overflow: hidden;
  transition: opacity 0.15s;
}
.chart-frame.dim {
  opacity: 0.65;
}

.inchart-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem 1rem;
  padding: 0.7rem 0.9rem 0.55rem;
  border-bottom: 1px solid rgba(202, 196, 208, 0.4);
  background: rgba(255, 255, 255, 0.55);
}
.hero {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35rem;
  margin-right: 0.25rem;
}
.hero-k {
  font-size: 0.7rem;
  color: #79747e;
  font-weight: 600;
}
.hero-v {
  font-size: 1.35rem;
  font-weight: 800;
  color: #1c1b1f;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.hero-u {
  font-size: 0.7rem;
  color: #9a94a0;
}
.ch-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 0.65rem;
  flex: 1;
  min-width: 0;
}
.ch-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.28rem;
  font-size: 0.72rem;
  color: #49454f;
  font-weight: 600;
  white-space: nowrap;
}
.ch-chip i {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 2px;
  display: inline-block;
}
.ch-chip b {
  font-variant-numeric: tabular-nums;
  color: #1c1b1f;
}
.ch-chip em {
  font-style: normal;
  color: #79747e;
  font-weight: 600;
  font-size: 0.68rem;
}
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.85rem;
  width: 100%;
  font-size: 0.7rem;
  color: #79747e;
}
.meta-row b {
  color: #1c1b1f;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.meta-row .up {
  color: #1b6b3a;
}
.meta-row .down {
  color: #ba1a1a;
}

.chart-svg {
  width: 100%;
  height: 260px;
  display: block;
}
.axis-lab {
  font-size: 11px;
  fill: #79747e;
}
.axis-tick {
  font-size: 9px;
  fill: #9a94a0;
}
.seg {
  cursor: pointer;
}
</style>
