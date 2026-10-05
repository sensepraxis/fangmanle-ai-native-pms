<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * 人效复盘 — 对照原型信息架构，沿用房务报表原有样式变量
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import HkAiPlanDrawer, { type HkAiScene } from '../../components/HkAiPlanDrawer.vue'

const router = useRouter()

const RANGES = [
  { code: 'week', label: t('本周') },
  { code: '7d', label: t('近 7 天') },
  { code: '30d', label: t('近 30 天') },
] as const

const EMPTY = {
  kpis: [] as any[],
  labor_gap: 0,
  labor_forecast: null as any,
  range_label: '',
  period_tag: '',
  trend: [] as (number | null)[],
  trend_labels: [] as string[],
  trend_samples: [] as number[],
  target: [] as number[],
  insights: [] as any[],
  load_heat: [] as any[],
  heat_labels: [] as string[],
  match: [] as any[],
  match_target: 90,
  staff_top: [] as any[],
  samples: {} as any,
}

const range = ref<'week' | '7d' | '30d'>('7d')
const aiOpen = ref(false)
const planOpen = ref(false)
const planScene = ref<HkAiScene>('staffing_gap')
const loading = ref(false)
const data = ref<any>({ ...EMPTY })
const hoverTrend = ref<any>(null)
const drill = ref<null | { title: string; lines: string[]; link?: string }>(null)

async function load() {
  loading.value = true
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId, { range: range.value })
    const perf = board?.performance || {}
    const insights = (Array.isArray(perf.insights) ? perf.insights : []).map(
      (ins: any, i: number) => ({
        t: ins.t || t('洞察'),
        d: ins.d || '',
        c: ins.c || ['var(--primary)', 'var(--tertiary)', 'var(--outline)'][i % 3],
        action: ins.action,
        link: ins.link,
      }),
    )
    data.value = {
      kpis: Array.isArray(perf.kpis) ? perf.kpis.filter((k: any) => !k.warn) : [],
      labor_gap: perf.labor_gap ?? 0,
      labor_forecast: perf.labor_forecast || null,
      range_label: perf.range_label || RANGES.find((r) => r.code === range.value)?.label,
      period_tag: perf.period_tag || '',
      trend: Array.isArray(perf.trend) ? perf.trend : [],
      trend_labels: Array.isArray(perf.trend_labels) ? perf.trend_labels : [],
      trend_samples: Array.isArray(perf.trend_samples) ? perf.trend_samples : [],
      target: Array.isArray(perf.target) ? perf.target : [],
      insights,
      load_heat: Array.isArray(perf.load_heat) ? perf.load_heat : perf.quality || [],
      heat_labels: Array.isArray(perf.heat_labels) ? perf.heat_labels : [],
      match: Array.isArray(perf.match) ? perf.match : [],
      match_target: perf.match_target ?? 90,
      staff_top: Array.isArray(perf.staff_top) ? perf.staff_top : [],
      samples: perf.samples || {},
    }
  } catch {
    data.value = { ...EMPTY }
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(range, load)

const forecast = computed(() => data.value.labor_forecast)
const showForecast = computed(() => !!forecast.value?.message)
const insightCount = computed(() => (data.value.insights || []).length)

const kpiCards = computed(() => {
  const order = ['efficiency', 'quality', 'planning']
  const list = data.value.kpis || []
  return order.map((g) => list.find((k: any) => k.group === g)).filter(Boolean)
})

function goStaffing() {
  router.push('/c6-housekeeping/staffing')
}
function goDispatch() {
  router.push('/c6-housekeeping/housekeeping')
}
function followDrill() {
  if (drill.value?.link?.includes('staff')) goStaffing()
  else goDispatch()
  drill.value = null
}
function goInsight(ins: any) {
  if (ins?.link) router.push(ins.link)
  else goStaffing()
}
function openPlan(scene: HkAiScene) {
  planScene.value = scene
  planOpen.value = true
}
function onPlanConfirmed() {
  load()
}

function loadColor(cell: any) {
  if (!cell || cell.rest) return '#e8eaed'
  if (cell.h == null) return '#f1f3f4'
  if (cell.h > 3) return '#fdba74'
  if (cell.h >= 2) return '#fde68a'
  return '#fef9c3'
}

function cellText(cell: any) {
  if (!cell) return ''
  if (cell.rest) return t('休')
  if (cell.h == null) return '—'
  return `${cell.h}h`
}

const heatLabels = computed(() => {
  const raw = data.value.heat_labels || []
  if (raw.length) return raw.map((d: string) => t(String(d)))
  return [t('一'), t('二'), t('三'), t('四'), t('五'), t('六'), t('日')]
})

/** 折线：仅连接有样本的点；目标线水平虚线；空位标「无」 */
const trendSvg = computed(() => {
  const vals: (number | null)[] = data.value.trend || []
  const samples: number[] = data.value.trend_samples || []
  const labels: string[] = data.value.trend_labels || []
  const W = 520
  const H = 210
  const padL = 40
  const padR = 12
  const padT = 20
  const padB = 34
  const plotW = W - padL - padR
  const plotH = H - padT - padB
  const numeric = vals
    .filter((v): v is number => v != null && Number.isFinite(Number(v)))
    .map(Number)
  const yMin = numeric.length ? Math.max(15, Math.floor(Math.min(...numeric, 28) - 3)) : 20
  const yMax = numeric.length ? Math.ceil(Math.max(...numeric, 28) + 3) : 40
  const n = Math.max(vals.length, 1)
  const xAt = (i: number) => padL + (n <= 1 ? plotW / 2 : (i / (n - 1)) * plotW)
  const yAt = (v: number) =>
    padT + (1 - (Math.min(yMax, Math.max(yMin, v)) - yMin) / Math.max(1, yMax - yMin)) * plotH
  const points = vals.map((v, i) => ({
    i,
    v: v == null ? null : Number(v),
    sample: samples[i] ?? 0,
    x: xAt(i),
    y: v == null ? null : yAt(Number(v)),
    label: t(String(labels[i] || i + 1)),
  }))
  const drawn = points.filter((p) => p.v != null && p.y != null)
  // 分段连线（跳过空点）
  const segs: string[] = []
  let buf: string[] = []
  for (const p of points) {
    if (p.y == null) {
      if (buf.length > 1) segs.push(buf.join(' '))
      buf = []
    } else {
      buf.push(`${p.x},${p.y}`)
    }
  }
  if (buf.length > 1) segs.push(buf.join(' '))
  const targetY = yAt(28)
  const step = Math.max(1, Math.round((yMax - yMin) / 4))
  const gridYs: { v: number; y: number }[] = []
  for (let v = yMin; v <= yMax; v += step) gridYs.push({ v, y: yAt(v) })
  return {
    W,
    H,
    padL,
    padT,
    plotH,
    segs,
    targetY,
    gridYs,
    points,
    hasData: drawn.length > 0,
    dayLabels: points.map((p) => ({ d: p.label, x: p.x, empty: p.v == null })),
  }
})

const matchSvg = computed(() => {
  const rows = data.value.match || []
  const W = 520
  const H = 220
  const padL = 40
  const padR = 12
  const padT = 16
  const padB = 34
  const plotW = W - padL - padR
  const plotH = H - padT - padB
  const maxY = Math.max(
    8,
    ...rows.map((m: any) => Math.max(Number(m.need ?? m.ai ?? 0), Number(m.actual || 0))),
  )
  const n = Math.max(rows.length, 1)
  const slot = plotW / n
  const barW = Math.min(12, slot * 0.28)
  const yAt = (v: number) => padT + (1 - Math.min(maxY, Math.max(0, v)) / maxY) * plotH
  const gridStep = Math.max(2, Math.round(maxY / 4))
  const gridYs: { v: number; y: number }[] = []
  for (let v = 0; v <= maxY; v += gridStep) gridYs.push({ v, y: yAt(v) })
  const bars = rows.map((m: any, i: number) => {
    const cx = padL + slot * i + slot / 2
    const need = Number(m.need ?? m.ai ?? 0)
    const actual = Number(m.actual || 0)
    const yN = yAt(need)
    const yA = yAt(actual)
    return {
      label: m.label,
      lx: cx,
      need,
      actual,
      align: m.align,
      surplus: m.surplus,
      on_shift: m.on_shift,
      need_rooms: m.need_rooms,
      nX: cx - barW - 2,
      nY: yN,
      nH: padT + plotH - yN,
      aX: cx + 2,
      aY: yA,
      aH: padT + plotH - yA,
      barW,
      i,
    }
  })
  return { W, H, padL, padT, plotH, gridYs, bars, hasData: rows.length > 0, unit: t('工时') }
})

function openTrendDrill(p: any) {
  if (p.v == null) {
    drill.value = {
      title: t('{day} · 无样本', { day: p.label }),
      lines: [t('该日没有带完成时间的已完成清扫任务。'), t('空位≠达标，仅表示暂无统计样本。')],
      link: '/c6-housekeeping/housekeeping',
    }
    return
  }
  drill.value = {
    title: t('{day} · 平均 {n} min', { day: p.label, n: p.v }),
    lines: [
      t('样本 {n} 单', { n: p.sample || '—' }),
      t('参考目标 28 min'),
      Number(p.v) > 30 ? t('偏高：建议查看当日退房集中时段派工') : t('处于正常区间'),
    ],
    link: '/c6-housekeeping/housekeeping',
  }
}

function openMatchDrill(b: any) {
  drill.value = {
    title: t('{day} · 排班吻合', { day: b.label }),
    lines: [
      t('需求工时 {h} h（预离 {rooms} 间 × 0.5）', { h: b.need, rooms: b.need_rooms ?? '—' }),
      t('实际工时 {h} h（在岗 {n} 人 × 4）', { h: b.actual, n: b.on_shift ?? '—' }),
      b.align != null ? t('当日吻合度 {pct}%', { pct: b.align }) : t('无需求样本'),
      b.surplus != null
        ? b.surplus >= 0
          ? t('富余 {h} h', { h: b.surplus })
          : t('缺口 {h} h', { h: Math.abs(b.surplus) })
        : '',
    ].filter(Boolean),
    link: '/c6-housekeeping/staffing',
  }
}

function openHeatDrill(row: any, ci: number, cell: any) {
  const day = heatLabels.value[ci] || `D${ci + 1}`
  drill.value = {
    title: t('{name} · {day}', { name: row.name, day }),
    lines: cell?.rest
      ? [t('排班休息')]
      : cell?.h == null
        ? [t('当日无完成任务记录')]
        : [
            `清扫负荷 ${cell.h} h`,
            `完成 ${cell.tasks} 单`,
            cell.avg_min != null ? `平均时长 ${cell.avg_min} min` : '',
            cell.h > 3 ? t('高负荷，建议关注加班风险') : '',
          ].filter(Boolean),
    link: '/c6-housekeeping/housekeeping',
  }
}
</script>

<template>
  <div class="perf-page">
    <div class="page-head head-row">
      <div>
        <h2 class="panel-title">{{ t('人效复盘') }}</h2>
      </div>
      <div class="head-actions">
        <div class="range-seg" role="tablist">
          <button
            v-for="r in RANGES"
            :key="r.code"
            type="button"
            :class="{ on: range === r.code }"
            @click="range = r.code"
          >
            {{ r.label }}
          </button>
        </div>
        <button
          v-if="commercialEnabled()"
          class="btn btn-ghost ai-btn"
          type="button"
          @click="aiOpen = !aiOpen"
        >
          <span class="material-symbols-outlined">lightbulb</span>
          {{ t('AI洞察') }}
          <span v-if="insightCount" class="badge">{{ insightCount }}</span>
        </button>
        <button
          v-if="commercialEnabled()"
          class="btn btn-primary"
          type="button"
          @click="openPlan('staffing_gap')"
        >
          {{ t('AI一键补班') }}
        </button>
      </div>
    </div>

    <!-- 未来预测 Banner（与历史 KPI 分离） -->
    <div v-if="showForecast" class="forecast-banner">
      <div class="fb-main">
        <span class="material-symbols-outlined">lightbulb</span>
        <div>
          <strong>{{ t('未来 5 天预测') }}</strong>
          <p>{{ t(forecast.message || '') }}</p>
        </div>
      </div>
      <button
        v-if="commercialEnabled()"
        class="btn btn-primary"
        type="button"
        @click="openPlan('staffing_gap')"
      >
        {{ t('AI生成补班安排') }}
      </button>
    </div>

    <HkAiPlanDrawer v-model:open="planOpen" :scene="planScene" @confirmed="onPlanConfirmed" />

    <!-- AI 洞察面板 -->
    <div v-if="aiOpen" class="ai-panel">
      <div class="ai-panel-head">
        <strong>{{ t('AI 效能洞察') }}</strong>
        <button type="button" class="x" @click="aiOpen = false">×</button>
      </div>
      <div v-if="insightCount" class="ai-list">
        <div v-for="(ins, i) in data.insights" :key="i" class="ai-item">
          <span class="dot" :style="{ background: ins.c }"></span>
          <div class="ai-body">
            <div class="t">{{ t(ins.t || '') }}</div>
            <p>{{ t(ins.d || '') }}</p>
            <button v-if="ins.action" type="button" class="act-link" @click="goInsight(ins)">
              {{ t(ins.action) }} →
            </button>
          </div>
        </div>
      </div>
      <p v-else class="empty-hint">{{ t('暂无洞察。') }}</p>
    </div>

    <!-- KPI：效率 / 质量 / 规划 -->
    <div class="kpi-row">
      <div v-for="(k, i) in kpiCards" :key="i" class="kpi-card">
        <div class="kpi-tag" :class="k.group">{{ t(k.group_label || '') }}</div>
        <div class="kpi-name">{{ t(k.label || '') }}</div>
        <div class="kpi-val">
          {{ k.value }}<span v-if="k.unit" class="unit">{{ k.unit }}</span>
        </div>
        <div class="kpi-foot">
          {{ t('目标') }} {{ k.target }}{{ k.target_unit || k.unit }} · {{ t('环比') }}
          {{ t(k.wow || '无上期数据') }}
          <template v-if="k.sample != null"> · {{ t('样本 {n} 单', { n: k.sample }) }}</template>
          <template v-if="k.note"><br />{{ t(k.note) }}</template>
        </div>
      </div>
    </div>
    <p v-if="!kpiCards.length" class="empty-hint">
      {{ t('暂无历史指标（等待完成任务 / 查房 / 排班样本）。') }}
    </p>

    <div class="main-grid">
      <!-- 左上：时长趋势 -->
      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('平均清扫时长趋势') }}</span>
          <span class="muted tiny warn-tip">{{ t('⚠ 无样本日不连线 · 点击下钻') }}</span>
        </div>
        <div class="card-pad">
          <svg
            v-if="trendSvg.hasData || (data.trend || []).length"
            class="chart"
            :viewBox="`0 0 ${trendSvg.W} ${trendSvg.H}`"
            @mouseleave="hoverTrend = null"
          >
            <line
              v-for="g in trendSvg.gridYs"
              :key="'gy' + g.v"
              :x1="trendSvg.padL"
              :x2="trendSvg.W - 12"
              :y1="g.y"
              :y2="g.y"
              stroke="var(--surface-high)"
              stroke-width="1"
            />
            <text
              v-for="g in trendSvg.gridYs"
              :key="'gt' + g.v"
              :x="trendSvg.padL - 6"
              :y="g.y + 4"
              text-anchor="end"
              font-size="11"
              font-weight="700"
              fill="var(--on-surface-variant)"
            >
              {{ g.v }}
            </text>
            <!-- 目标水平虚线 -->
            <line
              :x1="trendSvg.padL"
              :x2="trendSvg.W - 12"
              :y1="trendSvg.targetY"
              :y2="trendSvg.targetY"
              stroke="#16a34a"
              stroke-width="1.5"
              stroke-dasharray="6 4"
            />
            <text
              :x="trendSvg.W - 14"
              :y="trendSvg.targetY - 4"
              text-anchor="end"
              font-size="10"
              fill="#16a34a"
              font-weight="700"
            >
              {{ t('目标 28') }}
            </text>
            <polyline
              v-for="(seg, si) in trendSvg.segs"
              :key="'s' + si"
              :points="seg"
              fill="none"
              stroke="var(--primary)"
              stroke-width="2.5"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
            <g v-for="p in trendSvg.points" :key="'p' + p.i">
              <template v-if="p.y != null">
                <circle
                  :cx="p.x"
                  :cy="p.y"
                  r="12"
                  fill="transparent"
                  style="cursor: pointer"
                  @mouseenter="hoverTrend = p"
                  @click="openTrendDrill(p)"
                />
                <circle :cx="p.x" :cy="p.y" r="4" fill="var(--primary)" pointer-events="none" />
                <text
                  :x="p.x"
                  :y="p.y - 10"
                  text-anchor="middle"
                  font-size="10"
                  font-weight="700"
                  fill="var(--primary)"
                >
                  {{ p.v }}
                </text>
              </template>
              <template v-else>
                <text
                  :x="p.x"
                  :y="trendSvg.padT + trendSvg.plotH - 8"
                  text-anchor="middle"
                  font-size="9"
                  fill="var(--outline)"
                  style="cursor: pointer"
                  @click="openTrendDrill(p)"
                >
                  {{ t('无') }}
                </text>
              </template>
            </g>
            <text
              v-for="(lb, i) in trendSvg.dayLabels"
              :key="'d' + i"
              :x="lb.x"
              :y="trendSvg.H - 10"
              text-anchor="middle"
              font-size="11"
              font-weight="700"
              :fill="lb.empty ? 'var(--outline)' : 'var(--on-surface)'"
            >
              {{ lb.d }}
            </text>
            <g v-if="hoverTrend && hoverTrend.y != null">
              <rect
                :x="hoverTrend.x - 40"
                :y="hoverTrend.y - 40"
                width="80"
                height="28"
                rx="6"
                fill="#1f2937"
              />
              <text
                :x="hoverTrend.x"
                :y="hoverTrend.y - 22"
                text-anchor="middle"
                font-size="11"
                fill="#fff"
                font-weight="700"
              >
                {{ hoverTrend.v }}min · {{ hoverTrend.sample }}单
              </text>
            </g>
          </svg>
          <p v-else class="empty-hint">{{ t('本区间暂无时长样本。') }}</p>
          <div class="legend">
            <span><i class="lg-solid"></i>{{ t('有样本日') }}</span>
            <span><i class="lg-dash"></i>{{ t('目标 28min') }}</span>
            <span class="muted tiny">{{ t('「无」= 无样本，非达标') }}</span>
          </div>
        </div>
      </div>

      <!-- 右上：负荷热力 -->
      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('员工清扫负荷热力图') }}</span>
          <div class="heat-legend">
            <span><i style="background: #fef9c3"></i>&lt;2h</span>
            <span><i style="background: #fde68a"></i>2–3h</span>
            <span><i style="background: #fdba74"></i>&gt;3h</span>
            <span><i style="background: #e8eaed"></i>{{ t('休') }}</span>
          </div>
        </div>
        <div v-if="(data.load_heat || []).length" class="card-pad heat-pad">
          <div class="heat-row head">
            <div class="heat-name"></div>
            <div class="heat-cells">
              <span v-for="(d, i) in heatLabels" :key="i">{{ d }}</span>
            </div>
          </div>
          <div v-for="(row, ri) in data.load_heat" :key="ri" class="heat-row">
            <div class="heat-name">{{ row.name }}</div>
            <div class="heat-cells">
              <div
                v-for="(cell, ci) in row.cells || []"
                :key="ci"
                class="heat-cell"
                :class="{ rest: cell?.rest }"
                :style="{ background: loadColor(cell) }"
                :title="`${row.name} · ${heatLabels[ci]} · ${cellText(cell)}`"
                @click="openHeatDrill(row, ci, cell)"
              >
                {{ cellText(cell) }}
              </div>
            </div>
          </div>
        </div>
        <p v-else class="empty-hint pad">{{ t('本区间无员工完成/排班负荷样本。') }}</p>
      </div>

      <!-- 左下：双柱吻合度 -->
      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('排班吻合度追踪') }}</span>
          <span class="muted tiny">{{ t('单位：工时 · 点击下钻') }}</span>
        </div>
        <div class="card-pad">
          <svg v-if="matchSvg.hasData" class="chart" :viewBox="`0 0 ${matchSvg.W} ${matchSvg.H}`">
            <line
              v-for="g in matchSvg.gridYs"
              :key="'mgy' + g.v"
              :x1="matchSvg.padL"
              :x2="matchSvg.W - 12"
              :y1="g.y"
              :y2="g.y"
              stroke="var(--surface-high)"
              stroke-width="1"
            />
            <text
              v-for="g in matchSvg.gridYs"
              :key="'mgt' + g.v"
              :x="matchSvg.padL - 6"
              :y="g.y + 4"
              text-anchor="end"
              font-size="11"
              font-weight="700"
              fill="var(--on-surface-variant)"
            >
              {{ g.v }}
            </text>
            <g v-for="(b, i) in matchSvg.bars" :key="i">
              <rect
                :x="b.nX"
                :y="b.nY"
                :width="b.barW"
                :height="Math.max(0, b.nH)"
                fill="#d8e2ff"
                rx="3"
                style="cursor: pointer"
                @click="openMatchDrill(b)"
              />
              <rect
                :x="b.aX"
                :y="b.aY"
                :width="b.barW"
                :height="Math.max(0, b.aH)"
                fill="var(--primary)"
                rx="3"
                style="cursor: pointer"
                @click="openMatchDrill(b)"
              />
              <text
                :x="b.lx"
                :y="matchSvg.H - 10"
                text-anchor="middle"
                font-size="11"
                font-weight="700"
                fill="var(--on-surface)"
              >
                {{ b.label }}
              </text>
            </g>
          </svg>
          <p v-else class="empty-hint">{{ t('暂无排班/预离样本。') }}</p>
          <div class="legend">
            <span><i class="lg-box soft"></i>{{ t('需求工时') }}</span>
            <span><i class="lg-box solid"></i>{{ t('实际在岗工时') }}</span>
            <span class="muted tiny">{{ t('需求=预离×0.5h · 实际=在岗×4h') }}</span>
          </div>
        </div>
      </div>

      <!-- 右下：人效 TOP -->
      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('本周人效 TOP') }}</span>
          <span class="muted tiny">{{ t(data.period_tag || '本区间') }}</span>
        </div>
        <div v-if="(data.staff_top || []).length" class="card-pad top-list">
          <div
            v-for="(row, i) in data.staff_top"
            :key="i"
            class="top-row"
            :class="{ warn: row.kind === 'warn' }"
          >
            <span class="rank">{{ row.rank }}</span>
            <div class="top-body">
              <strong>{{ row.name }}</strong>
              <span class="metric">{{ t(row.metric || '') }}</span>
            </div>
            <span class="top-val" :class="{ warn: row.kind === 'warn' }">
              <span v-if="row.kind === 'warn'" class="material-symbols-outlined warn-ico"
                >error</span
              >
              {{ t(String(row.value || '')) }}</span
            >
          </div>
        </div>
        <p v-else class="empty-hint pad">{{ t('暂无员工业绩样本。') }}</p>
      </div>
    </div>

    <div v-if="drill" class="mask" @click.self="drill = null">
      <div class="panel" role="dialog">
        <header>
          <h3>{{ drill.title }}</h3>
          <button type="button" class="x" @click="drill = null">×</button>
        </header>
        <ul class="drill-list">
          <li v-for="(line, i) in drill.lines" :key="i">{{ line }}</li>
        </ul>
        <footer>
          <button type="button" class="btn btn-ghost" @click="drill = null">{{ t('关闭') }}</button>
          <button type="button" class="btn btn-primary" @click="followDrill">
            {{ drill.link?.includes('staff') ? t('去排班') : t('去派单') }}
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel-title {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 800;
}
.perf-page .page-head p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.head-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.range-seg {
  display: inline-flex;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.range-seg button {
  height: 32px;
  padding: 0 12px;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface-variant);
  cursor: pointer;
  font-family: inherit;
}
.range-seg button.on {
  background: var(--primary);
  color: #fff;
}
.ai-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.ai-btn .material-symbols-outlined {
  font-size: 18px;
}
.badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #ba1a1a;
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.forecast-banner {
  margin-bottom: 14px;
  padding: 12px 16px;
  border-radius: 12px;
  background: #fff8e1;
  border: 1px solid #f9ab00;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.fb-main {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  min-width: 0;
  flex: 1;
}
.fb-main .material-symbols-outlined {
  color: #b06000;
  margin-top: 2px;
}
.fb-main strong {
  display: block;
  font-size: 13px;
  color: #855e00;
  margin-bottom: 2px;
}
.fb-main p {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface);
  line-height: 1.45;
}

.ai-panel {
  margin-bottom: 14px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid var(--outline-variant);
  background: #fff;
}
.ai-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.ai-panel-head .x {
  border: none;
  background: transparent;
  font-size: 20px;
  cursor: pointer;
}
.ai-list {
  display: grid;
  gap: 10px;
}
.ai-item {
  display: flex;
  gap: 10px;
}
.ai-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}
.ai-item .t {
  font-weight: 700;
  font-size: 13px;
}
.ai-item p {
  margin: 2px 0 4px;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.act-link {
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
@media (max-width: 900px) {
  .kpi-row {
    grid-template-columns: 1fr;
  }
}
.kpi-card {
  background: #fff;
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 14px 16px;
}
.kpi-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 800;
  padding: 3px 8px;
  border-radius: 999px;
  margin-bottom: 8px;
}
.kpi-tag.efficiency {
  background: #e8f0fe;
  color: #1967d2;
}
.kpi-tag.quality {
  background: #e6f4ea;
  color: #137333;
}
.kpi-tag.planning {
  background: #fef7e0;
  color: #b06000;
}
.kpi-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--on-surface-variant);
}
.kpi-val {
  font-size: 32px;
  font-weight: 800;
  margin: 6px 0;
  line-height: 1.1;
}
.kpi-val .unit {
  font-size: 14px;
  margin-left: 4px;
  color: var(--on-surface-variant);
  font-weight: 600;
}
.kpi-foot {
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}

.main-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
@media (max-width: 960px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
}
.card-clean {
  background: #fff;
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  overflow: hidden;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 12px 14px 0;
  font-weight: 700;
  font-size: 14px;
}
.card-pad {
  padding: 10px 14px 14px;
}
.muted.tiny {
  font-size: 11px;
  color: var(--on-surface-variant);
  font-weight: 500;
}
.warn-tip {
  color: #855e00 !important;
  font-weight: 600;
}
.chart {
  width: 100%;
  height: auto;
  display: block;
}
.legend {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-top: 8px;
  align-items: center;
}
.lg-solid,
.lg-dash,
.lg-box {
  display: inline-block;
  width: 14px;
  height: 3px;
  margin-right: 4px;
  vertical-align: middle;
  background: var(--primary);
}
.lg-dash {
  background: transparent;
  border-top: 2px dashed #16a34a;
  height: 0;
}
.lg-box {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}
.lg-box.soft {
  background: #d8e2ff;
}
.lg-box.solid {
  background: var(--primary);
}
.empty-hint {
  margin: 12px 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.empty-hint.pad {
  padding: 16px;
}

.heat-pad {
  overflow-x: auto;
}
.heat-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.heat-name {
  width: 72px;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.heat-cells {
  display: flex;
  gap: 4px;
  flex: 1;
}
.heat-cells > span {
  flex: 1;
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--on-surface-variant);
}
.heat-cell {
  flex: 1;
  min-width: 36px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  color: #5f6368;
  cursor: pointer;
}
.heat-cell.rest {
  color: #9aa0a6;
}
.heat-legend {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--on-surface-variant);
  align-items: center;
}
.heat-legend i {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  display: inline-block;
  margin-right: 2px;
  vertical-align: -2px;
}

.top-list {
  display: grid;
  gap: 8px;
}
.top-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--outline-variant);
  border-radius: 10px;
  background: var(--surface-low);
}
.top-row.warn {
  border-color: #f9ab00;
  background: #fffbf0;
}
.rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.top-row.warn .rank {
  background: #ba1a1a;
}
.top-body {
  flex: 1;
  min-width: 0;
}
.top-body strong {
  display: block;
  font-size: 13px;
}
.top-body .metric {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.top-val {
  font-size: 14px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.top-val.warn {
  color: #ba1a1a;
}
.warn-ico {
  font-size: 18px;
}

.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 40;
  padding: 16px;
}
.panel {
  background: #fff;
  border-radius: 14px;
  width: min(440px, 100%);
  padding: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}
.panel header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel h3 {
  margin: 0;
  font-size: 16px;
}
.panel .x {
  border: none;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
}
.drill-list {
  margin: 12px 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.6;
}
.panel footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
