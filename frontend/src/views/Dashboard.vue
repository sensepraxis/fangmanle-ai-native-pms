<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t, getLocale } from '../lib/i18n'

/**
 * 经营总览 · 经营看板（对齐数据看板 v2 原型）
 * KPI + sparkline / 7 日趋势 / 房型排行 / 时间轴 / 渠道 / 待办 / AI 线索
 * 数据全部来自 /api/dashboard
 */
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts/core'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import OverviewOpsNav from '../components/OverviewOpsNav.vue'

echarts.use([LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const router = useRouter()
const period = ref('今日')
const localeTick = ref(0)
const periodTabs = computed(() => {
  localeTick.value
  return [
    { value: '今日' as const, label: t('今日') },
    { value: '本周' as const, label: t('本周') },
    { value: '本月' as const, label: t('本月') },
  ]
})
const loading = ref(false)
const d = ref<any>(null)
const trendMetric = ref<'revenue' | 'occ' | 'adr'>('revenue')
const showOcc = ref(true)

const trendEl = ref<HTMLElement | null>(null)
const pieEl = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null
let timer: number | undefined

const WEEKDAY_KEYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'] as const

const bizDateLabel = computed(() => {
  localeTick.value
  const iso = d.value?.biz_date
  if (!iso) return ''
  const dt = new Date(iso + 'T12:00:00')
  return `${t('业务日期')} ${iso} ${t(WEEKDAY_KEYS[dt.getDay()])}`
})

const revenueLabel = computed(() => {
  localeTick.value
  return period.value === '今日' ? t('今日营收') : `${t(period.value)}${t('营收')}`
})

const channelNights = computed(() =>
  Math.round(
    (d.value?.channel_mix || []).reduce((a: number, m: any) => a + Number(m.nights || 0), 0),
  ),
)

function moneyNum(n: number | undefined | null, digits = 0) {
  const loc = getLocale() === 'en' ? 'en-US' : 'zh-CN'
  return Number(n || 0).toLocaleString(loc, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  })
}

/** 渠道分桶名（后端计算标签，非 DB 原始渠道名） */
function channelName(name: string) {
  localeTick.value
  return t(name || '')
}

function timelineBarLabel(b: any) {
  localeTick.value
  return t('{count} 间', { count: Number(b?.count || 0) })
}

function timelineBarTitle(b: any) {
  localeTick.value
  const start = `${String(b?.start_hour ?? 0).padStart(2, '0')}:00`
  const end = `${String(b?.end_hour ?? 0).padStart(2, '0')}:00`
  return t('{start}-{end} · {count} 间', { start, end, count: Number(b?.count || 0) })
}

const peakLabelText = computed(() => {
  localeTick.value
  const h = d.value?.timeline?.summary?.peak_hour
  if (h == null || Number.isNaN(Number(h))) {
    return d.value?.timeline?.summary?.peak_label || ''
  }
  const start = String(h).padStart(2, '0')
  const end = String(Number(h) + 1).padStart(2, '0')
  return t('{start}-{end} 点高峰', { start, end })
})

/** 待办：按 code + 结构化字段本地化（非 DB 原文） */
function alertView(a: any) {
  localeTick.value
  const count = Number(a?.count || 0)
  const amount = moneyNum(a?.amount ?? 0)
  switch (a?.code) {
    case 'night_audit':
      return {
        title: t('夜审异常 {count} 项', { count }),
        detail: t('房价倒挂 / 押金超额等需财务复核'),
      }
    case 'shortage':
      return {
        title: t('短款 {count} 笔 · ¥{amount}', { count, amount }),
        detail: t('收银台未结清 · 需当班复核'),
      }
    case 'rate_parity':
      return {
        title: t('渠道差价 ¥{amount}', { amount }),
        detail: t('{count} 条待处理调价建议 · 可至价格助手双签采纳', { count }),
      }
    case 'forecast_gap':
      return {
        title: t('最大缺口：{date} 应订 {need} / 实订 {have}，缺 {gap} 间夜', {
          date: a?.gap_day || '',
          need: a?.need ?? '—',
          have: a?.have ?? '—',
          gap: count,
        }),
        detail: t('缺口约 {count} 间夜 · 建议补散客/直订渠道', { count }),
      }
    case 'risk':
      return {
        title: t('经营风险 {count}', { count }),
        detail: t('请到数据洞察查看归因'),
      }
    default:
      return { title: a?.title || a?.label || '', detail: a?.detail || '' }
  }
}

function onLocale() {
  localeTick.value++
  nextTick(() => renderCharts())
}

function deltaBadge(pct: number | undefined | null, unit = '%') {
  if (pct == null || Number.isNaN(Number(pct))) return { text: t('实时'), cls: 'eq' }
  const v = Number(pct)
  if (v > 0) return { text: `▲ ${v}${unit}`, cls: 'up' }
  if (v < 0) return { text: `▼ ${Math.abs(v)}${unit}`, cls: 'dn' }
  return { text: t('持平'), cls: 'eq' }
}

function sparkPath(data: number[], w = 120, h = 30) {
  if (!data?.length) return { line: '', area: '', last: [0, h / 2] as [number, number] }
  const pad = 2
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const step = data.length > 1 ? (w - pad * 2) / (data.length - 1) : 0
  const pts = data.map((v, i) => {
    const x = pad + i * step
    const y = h - pad - ((v - min) / range) * (h - pad * 2)
    return [x, y] as [number, number]
  })
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')
  const area = `${line} L${pts[pts.length - 1][0]},${h} L${pts[0][0]},${h} Z`
  return { line, area, last: pts[pts.length - 1] }
}

async function load() {
  loading.value = true
  try {
    d.value = await api.dashboard(hotelStore.hotelId, period.value)
    await nextTick()
    renderCharts()
  } catch {
    d.value = null
  } finally {
    loading.value = false
  }
}

function drill(path: string) {
  router.push(path)
}

function setPeriod(p: string) {
  period.value = p
  load()
}

function renderTrend() {
  if (!trendEl.value || !d.value?.trend_7d) return
  if (!trendChart) trendChart = echarts.init(trendEl.value)
  const trend = d.value.trend_7d
  const revK = (trend.revenue || []).map((x: number) => Math.round(Number(x) / 100) / 10)
  const series: any[] = []
  if (trendMetric.value === 'revenue' || trendMetric.value === 'adr') {
    const data = trendMetric.value === 'revenue' ? revK : trend.adr
    const name = trendMetric.value === 'revenue' ? t('营收') : 'ADR'
    const color = trendMetric.value === 'revenue' ? '#2563eb' : '#d97706'
    series.push({
      name,
      type: 'line',
      smooth: true,
      symbolSize: 6,
      data,
      lineStyle: { width: 2.5, color },
      itemStyle: { color },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            {
              offset: 0,
              color: color === '#2563eb' ? 'rgba(37,99,235,.18)' : 'rgba(217,119,6,.18)',
            },
            { offset: 1, color: 'rgba(37,99,235,0)' },
          ],
        },
      },
    })
  }
  if (showOcc.value) {
    series.push({
      name: 'OCC',
      type: 'line',
      smooth: true,
      yAxisIndex: 1,
      symbolSize: 6,
      data: trend.occ_pct,
      lineStyle: { width: 2.5, color: '#16a34a' },
      itemStyle: { color: '#16a34a' },
    })
  }
  trendChart.setOption(
    {
      grid: { left: 50, right: 50, top: 30, bottom: 30 },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#fff',
        borderColor: '#e6ebf2',
        textStyle: { color: '#0f172a', fontSize: 12 },
      },
      legend: { show: false },
      xAxis: {
        type: 'category',
        data: trend.labels,
        axisLine: { lineStyle: { color: '#e6ebf2' } },
        axisTick: { show: false },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
      },
      yAxis: [
        {
          type: 'value',
          name: trendMetric.value === 'adr' ? 'ADR' : t('营收(千)'),
          position: 'left',
          nameTextStyle: { color: '#94a3b8', fontSize: 10 },
          axisLabel: { color: '#94a3b8', fontSize: 11 },
          splitLine: { lineStyle: { color: '#f1f5f9' } },
        },
        {
          type: 'value',
          name: 'OCC(%)',
          position: 'right',
          nameTextStyle: { color: '#94a3b8', fontSize: 10 },
          axisLabel: { color: '#94a3b8', fontSize: 11, formatter: '{value}%' },
          splitLine: { show: false },
        },
      ],
      series,
    },
    true,
  )
}

function renderPie() {
  if (!pieEl.value || !d.value?.channel_mix) return
  if (!pieChart) pieChart = echarts.init(pieEl.value)
  const mix = (d.value.channel_mix || []).filter((m: any) => Number(m.nights || m.pct) > 0)
  const total = channelNights.value
  const nightsUnit = t('间夜')
  pieChart.setOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: (p: any) => `${p.name}<br/>${p.value} ${nightsUnit} (${p.percent}%)`,
        backgroundColor: '#fff',
        borderColor: '#e6ebf2',
        textStyle: { color: '#0f172a', fontSize: 12 },
      },
      series: [
        {
          type: 'pie',
          radius: ['58%', '80%'],
          center: ['38%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
          label: { show: false },
          labelLine: { show: false },
          data: mix.map((m: any) => ({
            value: Math.round(Number(m.nights || 0)),
            name: channelName(m.name),
            itemStyle: { color: m.color },
          })),
        },
        {
          type: 'pie',
          radius: ['0%', '48%'],
          center: ['38%', '50%'],
          label: {
            position: 'center',
            formatter: `${total}\n${nightsUnit}`,
            fontSize: 14,
            fontWeight: 700,
            color: '#0f172a',
            lineHeight: 20,
          },
          data: [{ value: 1, itemStyle: { color: 'transparent' } }],
          silent: true,
        },
      ],
    },
    true,
  )
}

function renderCharts() {
  renderTrend()
  renderPie()
}

function onResize() {
  trendChart?.resize()
  pieChart?.resize()
}

onMounted(() => {
  load()
  timer = window.setInterval(load, 30000)
  window.addEventListener('resize', onResize)
  window.addEventListener('fml:locale', onLocale)
})
onUnmounted(() => {
  if (timer) window.clearInterval(timer)
  window.removeEventListener('resize', onResize)
  window.removeEventListener('fml:locale', onLocale)
  trendChart?.dispose()
  pieChart?.dispose()
})
watch(() => hotelStore.hotelId, load)
watch([trendMetric, showOcc], () => renderTrend())
</script>

<template>
  <div class="page board-page">
    <OverviewOpsNav />

    <div class="board-top">
      <div class="top-left">
        <h1 class="font-display-lg text-display-lg text-on-surface">{{ t('经营看板') }}</h1>
        <span v-if="bizDateLabel" class="date-box">{{ bizDateLabel }}</span>
        <span class="live">{{ t('实时') }}</span>
      </div>
      <div class="top-right">
        <div class="seg" role="tablist" :aria-label="t('时间范围')">
          <button
            v-for="p in periodTabs"
            :key="p.value"
            type="button"
            :class="{ on: period === p.value }"
            @click="setPeriod(p.value)"
          >
            {{ p.label }}
          </button>
        </div>
        <button type="button" class="refresh" :disabled="loading" @click="load">
          {{ t('⟳ 刷新') }}
        </button>
      </div>
    </div>

    <div v-if="d" class="board-body">
      <!-- ① KPI -->
      <div class="kpi-grid">
        <button type="button" class="kpi-card" @click="drill('/c9-finance/daily-operations')">
          <div class="head">
            <span class="lab"><span class="ic">¥</span>{{ revenueLabel }}</span>
          </div>
          <div class="val">
            {{ moneyNum(d.kpi?.revenue) }}<span class="unit">{{ t('元') }}</span>
          </div>
          <div class="meta">
            <span class="delta" :class="deltaBadge(d.kpi?.deltas?.revenue_yoy_pct).cls">
              {{ deltaBadge(d.kpi?.deltas?.revenue_yoy_pct).text }} <small>{{ t('同比') }}</small>
            </span>
            <div class="spark">
              <svg
                v-if="d.trend_7d?.spark?.revenue?.length"
                width="100%"
                height="30"
                viewBox="0 0 120 30"
                preserveAspectRatio="none"
              >
                <defs>
                  <linearGradient id="gRev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#2563eb" stop-opacity=".25" />
                    <stop offset="100%" stop-color="#2563eb" stop-opacity="0" />
                  </linearGradient>
                </defs>
                <path :d="sparkPath(d.trend_7d.spark.revenue).area" fill="url(#gRev)" />
                <path
                  :d="sparkPath(d.trend_7d.spark.revenue).line"
                  fill="none"
                  stroke="#2563eb"
                  stroke-width="1.5"
                  stroke-linejoin="round"
                />
              </svg>
            </div>
          </div>
        </button>

        <button type="button" class="kpi-card g" @click="drill('/room-board')">
          <div class="head">
            <span class="lab"><span class="ic">▦</span>{{ t('出租率 OCC') }}</span>
          </div>
          <div class="val">{{ d.kpi?.occ_pct }}<span class="unit">%</span></div>
          <div class="meta">
            <span class="delta" :class="deltaBadge(d.kpi?.deltas?.occ_yoy_pt, 'pt').cls">
              {{ deltaBadge(d.kpi?.deltas?.occ_yoy_pt, 'pt').text }} <small>{{ t('同比') }}</small>
            </span>
            <div class="spark">
              <svg
                v-if="d.trend_7d?.spark?.occ?.length"
                width="100%"
                height="30"
                viewBox="0 0 120 30"
                preserveAspectRatio="none"
              >
                <defs>
                  <linearGradient id="gOcc" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#16a34a" stop-opacity=".25" />
                    <stop offset="100%" stop-color="#16a34a" stop-opacity="0" />
                  </linearGradient>
                </defs>
                <path :d="sparkPath(d.trend_7d.spark.occ).area" fill="url(#gOcc)" />
                <path
                  :d="sparkPath(d.trend_7d.spark.occ).line"
                  fill="none"
                  stroke="#16a34a"
                  stroke-width="1.5"
                  stroke-linejoin="round"
                />
              </svg>
            </div>
          </div>
        </button>

        <button type="button" class="kpi-card a" @click="drill('/pricing')">
          <div class="head">
            <span class="lab"><span class="ic">▤</span>{{ t('平均房价 ADR') }}</span>
          </div>
          <div class="val">
            {{ moneyNum(d.kpi?.adr) }}<span class="unit">{{ t('元') }}</span>
          </div>
          <div class="meta">
            <span class="delta" :class="deltaBadge(d.kpi?.deltas?.adr_yoy_pct).cls">
              {{ deltaBadge(d.kpi?.deltas?.adr_yoy_pct).text }} <small>{{ t('同比') }}</small>
            </span>
            <div class="spark">
              <svg
                v-if="d.trend_7d?.spark?.adr?.length"
                width="100%"
                height="30"
                viewBox="0 0 120 30"
                preserveAspectRatio="none"
              >
                <defs>
                  <linearGradient id="gAdr" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#d97706" stop-opacity=".25" />
                    <stop offset="100%" stop-color="#d97706" stop-opacity="0" />
                  </linearGradient>
                </defs>
                <path :d="sparkPath(d.trend_7d.spark.adr).area" fill="url(#gAdr)" />
                <path
                  :d="sparkPath(d.trend_7d.spark.adr).line"
                  fill="none"
                  stroke="#d97706"
                  stroke-width="1.5"
                  stroke-linejoin="round"
                />
              </svg>
            </div>
          </div>
        </button>

        <button type="button" class="kpi-card v" @click="drill('/c9-finance/revenue-forecast')">
          <div class="head">
            <span class="lab"><span class="ic">⌂</span>{{ t('每间可售房收入 RevPAR') }}</span>
          </div>
          <div class="val">
            {{ moneyNum(d.kpi?.revpar) }}<span class="unit">{{ t('元') }}</span>
          </div>
          <div class="meta">
            <span class="delta" :class="deltaBadge(d.kpi?.deltas?.revpar_yoy_pct).cls">
              {{ deltaBadge(d.kpi?.deltas?.revpar_yoy_pct).text }} <small>{{ t('同比') }}</small>
            </span>
            <div class="spark">
              <svg
                v-if="d.trend_7d?.spark?.revpar?.length"
                width="100%"
                height="30"
                viewBox="0 0 120 30"
                preserveAspectRatio="none"
              >
                <defs>
                  <linearGradient id="gRp" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#7c3aed" stop-opacity=".25" />
                    <stop offset="100%" stop-color="#7c3aed" stop-opacity="0" />
                  </linearGradient>
                </defs>
                <path :d="sparkPath(d.trend_7d.spark.revpar).area" fill="url(#gRp)" />
                <path
                  :d="sparkPath(d.trend_7d.spark.revpar).line"
                  fill="none"
                  stroke="#7c3aed"
                  stroke-width="1.5"
                  stroke-linejoin="round"
                />
              </svg>
            </div>
          </div>
        </button>
      </div>

      <!-- ② 趋势 + 渠道 -->
      <div class="row-2">
        <section class="panel">
          <div class="panel-head">
            <div>
              <h3>{{ t('近 7 天趋势') }}</h3>
            </div>
            <div class="actions">
              <button
                type="button"
                class="chip"
                :class="{ on: trendMetric === 'revenue' }"
                @click="trendMetric = 'revenue'"
              >
                {{ t('营收') }}
              </button>
              <button
                type="button"
                class="chip"
                :class="{ on: showOcc }"
                @click="showOcc = !showOcc"
              >
                {{ t('出租率') }}
              </button>
              <button
                type="button"
                class="chip"
                :class="{ on: trendMetric === 'adr' }"
                @click="trendMetric = 'adr'"
              >
                ADR
              </button>
            </div>
          </div>
          <div ref="trendEl" class="chart" />
        </section>
        <section class="panel channel-panel">
          <div class="panel-head">
            <div>
              <h3>{{ t('渠道实时占比') }}</h3>
            </div>
          </div>
          <div class="pie-wrap">
            <div ref="pieEl" class="pie-chart" />
            <div class="pie-leg">
              <div v-for="m in d.channel_mix || []" :key="m.name">
                <i :style="{ background: m.color }" />
                {{ channelName(m.name) }} <b>{{ m.pct }}%</b>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- ③ 时间轴 -->
      <section class="panel timeline-row">
        <div class="panel-head">
          <div>
            <h3>{{ t('今日房态时间轴') }}</h3>
          </div>
        </div>
        <div class="timeline-wrap">
          <div class="tl-axis">
            <div class="tl-grid">
              <div v-for="i in 13" :key="'g' + i" />
            </div>
            <div class="tl-row">
              <span class="tl-lab">{{ t('预抵') }}</span>
              <div
                v-for="(b, i) in d.timeline?.arrivals || []"
                :key="'a' + i"
                class="tl-bar"
                :style="{ left: b.left_pct + '%', width: b.width_pct + '%', background: b.color }"
                :title="timelineBarTitle(b)"
              >
                {{ timelineBarLabel(b) }}
              </div>
            </div>
            <div class="tl-row">
              <span class="tl-lab">{{ t('预离') }}</span>
              <div
                v-for="(b, i) in d.timeline?.departures || []"
                :key="'d' + i"
                class="tl-bar"
                :style="{ left: b.left_pct + '%', width: b.width_pct + '%', background: b.color }"
                :title="timelineBarTitle(b)"
              >
                {{ timelineBarLabel(b) }}
              </div>
            </div>
          </div>
          <div class="tl-axis-line" />
          <div class="tl-time">
            <span>00:00</span><span>03:00</span><span>06:00</span><span>09:00</span
            ><span>12:00</span><span>15:00</span><span>18:00</span><span>21:00</span
            ><span>24:00</span>
          </div>
          <div class="tl-summary">
            <span class="it"
              ><i style="background: #2563eb" />{{ t('预抵总计') }}
              <b>{{ d.timeline?.summary?.arrivals || 0 }} {{ t('间') }}</b></span
            >
            <span class="it"
              ><i style="background: #7c3aed" />{{ t('预离总计') }}
              <b>{{ d.timeline?.summary?.departures || 0 }} {{ t('间') }}</b></span
            >
            <span class="it">
              <i style="background: #16a34a" />{{ t('净增') }}
              <b
                >{{ (d.timeline?.summary?.net || 0) >= 0 ? '+' : ''
                }}{{ d.timeline?.summary?.net || 0 }} {{ t('间') }}</b
              >
            </span>
            <span v-if="d.timeline?.summary?.peak_count" class="it">
              <i style="background: #f59e0b" />{{ peakLabelText }}
              <b>{{ d.timeline.summary.peak_count }} {{ t('间') }}</b>
            </span>
          </div>
        </div>
      </section>

      <!-- ④ 待办（整行） -->
      <section class="panel alerts-panel">
        <div class="panel-head">
          <div>
            <h3>{{ t('待处理事项') }}</h3>
          </div>
        </div>
        <ul v-if="d.alerts?.length" class="alerts alerts-wide">
          <li
            v-for="a in d.alerts"
            :key="a.code"
            :class="a.level || 'blue'"
            @click="drill(a.to || '/analytics?tab=insights')"
          >
            <div class="desc">
              <b>{{ alertView(a).title }}</b>
              <small v-if="alertView(a).detail">{{ alertView(a).detail }}</small>
            </div>
            <button
              type="button"
              class="go-btn"
              @click.stop="drill(a.to || '/analytics?tab=insights')"
            >
              {{ t('去处理 →') }}
            </button>
          </li>
        </ul>
        <div v-else class="empty-alerts">{{ t('当前无待办 · 经营状态平稳') }}</div>
        <div class="alerts-footer">
          <button
            type="button"
            class="insight-btn"
            @click="drill(d.ai_hint?.to || '/analytics?tab=insights')"
          >
            {{ t('去数据洞察看原因 →') }}
          </button>
        </div>
      </section>
    </div>

    <div v-else class="loading">{{ loading ? t('加载中…') : t('暂无看板数据') }}</div>
  </div>
</template>

<style scoped>
.board-page {
  --ink: #0f172a;
  --ink-2: #475569;
  --ink-3: #94a3b8;
  --line: #d0d7e2;
  --line-strong: #b8c0cc;
  --green: #16a34a;
  --green-soft: #eafaf0;
  --red: #dc2626;
  --red-soft: #fee2e2;
  --amber: #d97706;
  --amber-soft: #fef3c7;
  --primary: #2563eb;
  --primary-d: #1d4ed8;
  --primary-soft: #eff4ff;
  --shadow: 0 1px 3px rgba(16, 24, 40, 0.06), 0 4px 14px rgba(16, 24, 40, 0.05);
  --shadow-md: 0 2px 6px rgba(16, 24, 40, 0.08), 0 8px 24px rgba(16, 24, 40, 0.08);
  padding-bottom: 2rem;
  color: var(--ink);
}

.board-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.top-left {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.top-left h1 {
  margin: 0;
  line-height: 1.2;
}
.date-box {
  display: inline-flex;
  align-items: center;
  color: var(--ink-2);
  font-size: 12.5px;
  font-weight: 600;
  padding: 5px 12px;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}
.live {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--green-soft);
  color: #15803d;
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 600;
}
.live::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.5);
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.5);
  }
  70% {
    box-shadow: 0 0 0 6px rgba(22, 163, 74, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(22, 163, 74, 0);
  }
}
.top-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.seg {
  display: flex;
  background: #f6f8fc;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  padding: 2px;
}
.seg button {
  border: 0;
  background: transparent;
  padding: 5px 14px;
  font-size: 12.5px;
  color: var(--ink-2);
  cursor: pointer;
  border-radius: 6px;
  font-weight: 500;
  font-family: inherit;
}
.seg button.on {
  background: #fff;
  color: var(--primary-d);
  font-weight: 700;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.08);
}
.refresh {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--primary-soft);
  color: var(--primary-d);
  border: 0;
  border-radius: 8px;
  padding: 7px 14px;
  font-size: 12.5px;
  cursor: pointer;
  font-weight: 600;
  font-family: inherit;
}
.refresh:hover {
  background: #dde7ff;
}
.refresh:disabled {
  opacity: 0.6;
  cursor: wait;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}
.kpi-card {
  text-align: left;
  background: #fff;
  border: 1px solid var(--line-strong);
  border-radius: 12px;
  padding: 18px 18px 14px;
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
  color: inherit;
}
.kpi-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
  border-color: var(--primary);
  border-style: solid;
}
.kpi-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--primary);
}
.kpi-card.g::before {
  background: var(--green);
}
.kpi-card.a::before {
  background: var(--amber);
}
.kpi-card.v::before {
  background: #7c3aed;
}
.kpi-card .head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.kpi-card .lab {
  font-size: 12.5px;
  color: var(--ink-2);
  font-weight: 700;
}
.kpi-card .lab .ic {
  color: var(--ink-3);
  margin-right: 5px;
}
.kpi-card .val {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -1px;
  line-height: 1.1;
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-variant-numeric: tabular-nums;
}
.kpi-card .val .unit {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-3);
}
.kpi-card .meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  gap: 8px;
}
.kpi-card .delta {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  white-space: nowrap;
}
.kpi-card .delta.up {
  background: var(--green-soft);
  color: var(--green);
}
.kpi-card .delta.dn {
  background: var(--red-soft);
  color: var(--red);
}
.kpi-card .delta.eq {
  background: #f1f5f9;
  color: var(--ink-3);
}
.kpi-card .delta small {
  font-weight: 500;
  opacity: 0.7;
}
.kpi-card .spark {
  flex: 1;
  height: 30px;
  min-width: 64px;
  margin-left: 8px;
}

.row-2 {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
}
.channel-panel .pie-wrap {
  height: 280px;
}
.alerts-panel {
  margin-bottom: 14px;
}
.alerts-wide {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 10px;
}
.alerts-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
  padding-top: 4px;
}
.insight-btn {
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: #fff;
  padding: 7px 16px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.3);
  font-family: inherit;
  white-space: nowrap;
}
.insight-btn:hover {
  filter: brightness(1.05);
}
.panel {
  background: #fff;
  border: 1px solid var(--line-strong);
  border-radius: 12px;
  padding: 18px 20px;
  box-shadow: var(--shadow);
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.panel-head h3 {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: -0.2px;
  margin: 0;
}
.actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.chip {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11.5px;
  color: var(--ink-2);
  background: #f6f8fc;
  border: 1px solid var(--line-strong);
  cursor: pointer;
  font-family: inherit;
}
.chip.on {
  background: var(--primary-soft);
  color: var(--primary-d);
  border-color: #cfe0ff;
  font-weight: 600;
}
.chart {
  width: 100%;
  height: 280px;
}

.timeline-row {
  margin-bottom: 14px;
}
.timeline-wrap {
  padding: 8px 4px 10px;
}
.tl-axis {
  position: relative;
  height: 84px;
  padding: 0 8px;
}
.tl-grid {
  position: absolute;
  inset: 0 8px;
  display: flex;
  justify-content: space-between;
  pointer-events: none;
}
.tl-grid div {
  width: 1px;
  background: var(--line);
}
.tl-grid div:first-child,
.tl-grid div:last-child {
  background: transparent;
}
.tl-row {
  position: relative;
  height: 34px;
  margin-bottom: 6px;
}
.tl-lab {
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11.5px;
  color: var(--ink-2);
  font-weight: 600;
  z-index: 2;
  background: #fff;
  padding-right: 6px;
}
.tl-bar {
  position: absolute;
  height: 18px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  padding: 0 8px;
  color: #fff;
  font-size: 10.5px;
  font-weight: 700;
  top: 8px;
  box-sizing: border-box;
  overflow: hidden;
  white-space: nowrap;
}
.tl-axis-line {
  height: 0;
  border-top: 1px solid var(--line-strong);
  margin: 10px 8px 0;
}
.tl-time {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 700;
  color: var(--ink);
  padding: 10px 8px 0;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
}
.tl-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  padding: 18px 8px 0;
  margin-top: 14px;
}
.tl-summary .it {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--ink-2);
}
.tl-summary .it b {
  color: var(--ink);
  font-size: 13px;
  margin-left: 2px;
}
.tl-summary .it i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}

.pie-wrap {
  height: 240px;
  position: relative;
}
.pie-chart {
  width: 100%;
  height: 100%;
}
.pie-leg {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  color: var(--ink-2);
  line-height: 2;
}
.pie-leg div {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 110px;
}
.pie-leg i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}
.pie-leg b {
  color: var(--ink);
  font-size: 13px;
  margin-left: auto;
  min-width: 40px;
  text-align: right;
}

.alerts {
  list-style: none;
  margin: 0;
  padding: 0;
}
.alerts:not(.alerts-wide) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.alerts li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid;
  border-style: solid;
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.15s;
}
.alerts li:hover {
  transform: translateX(2px);
}
.alerts li.red {
  background: var(--red-soft);
  border-color: #fecaca;
  color: #991b1b;
}
.alerts li.amber {
  background: var(--amber-soft);
  border-color: #fde68a;
  color: #92400e;
}
.alerts li.blue {
  background: var(--primary-soft);
  border-color: #bfdbfe;
  color: #1e40af;
}
.alerts li .desc {
  flex: 1;
  min-width: 0;
}
.alerts li .desc b {
  color: inherit;
}
.alerts li .desc small {
  display: block;
  font-size: 10.5px;
  opacity: 0.75;
  margin-top: 2px;
}
.alerts li .go-btn {
  flex-shrink: 0;
  border: 1px solid currentColor;
  background: #fff;
  color: inherit;
  font-weight: 700;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-family: inherit;
  opacity: 0.92;
  transition:
    opacity 0.15s,
    background 0.15s;
}
.alerts li .go-btn:hover {
  opacity: 1;
  background: color-mix(in srgb, #fff 70%, transparent);
}
.empty-alerts {
  font-size: 13px;
  color: var(--ink-3);
  padding: 24px 8px;
}

.loading {
  color: var(--ink-3);
  font-size: 13px;
  padding: 24px 0;
}

@media (max-width: 1100px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .row-2 {
    grid-template-columns: 1fr;
  }
  .pie-leg {
    position: static;
    transform: none;
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    margin-top: 8px;
    line-height: 1.6;
  }
}
@media (max-width: 640px) {
  .kpi-grid {
    grid-template-columns: 1fr;
  }
  .kpi-card .val {
    font-size: 24px;
  }
}
</style>
