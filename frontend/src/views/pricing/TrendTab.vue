<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 价格趋势分析：本店 vs 竞品中位 vs OTA 最低 + 房态 + 竞品变价表
 */
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { fmt } from '../../lib/ui'

defineProps<{ compOn: boolean }>()

const data = ref<any>(null)
const win = ref<'7' | '14' | '30'>('30')

async function load() {
  data.value = await api.paTrend(hotelStore.hotelId)
}
onMounted(load)
watch(() => hotelStore.hotelId, load)

const series = computed(() => data.value?.series?.[win.value] || [])
const enabledComp = computed(() => !!data.value?.comp_compare_enabled)

/** 图表坐标系：留边距给 Y 轴价格、X 轴日期 */
const CHART = { w: 640, h: 228, padL: 52, padR: 16, padT: 14, padB: 44 }

const chartScale = computed(() => {
  const pts = series.value as {
    date?: string
    self_adr?: number | null
    comp_median?: number | null
    ota_min?: number | null
  }[]
  const vals: number[] = []
  for (const p of pts) {
    for (const k of ['self_adr', 'comp_median', 'ota_min'] as const) {
      const v = p[k]
      if (v != null && v !== ('' as any) && !Number.isNaN(Number(v))) vals.push(Number(v))
    }
  }
  if (!vals.length) {
    return {
      min: 0,
      max: 100,
      yTicks: [0, 25, 50, 75, 100],
      xTicks: [] as { i: number; label: string; x: number }[],
      n: 0,
    }
  }
  let min = Math.min(...vals)
  let max = Math.max(...vals)
  if (min === max) {
    min = Math.max(0, min * 0.9)
    max = max * 1.1 || 100
  } else {
    const pad = (max - min) * 0.08
    min = Math.max(0, min - pad)
    max = max + pad
  }
  // 取整到较整齐的刻度
  const span = max - min
  const step = niceStep(span / 4)
  const y0 = Math.floor(min / step) * step
  const y1 = Math.ceil(max / step) * step
  const yTicks: number[] = []
  for (let v = y0; v <= y1 + step * 0.01; v += step) yTicks.push(Math.round(v))
  const n = pts.length
  const xTicks: { i: number; label: string; x: number }[] = []
  const maxLabels = win.value === '7' ? 7 : win.value === '14' ? 7 : 6
  const stepI = Math.max(1, Math.ceil((n - 1) / Math.max(maxLabels - 1, 1)))
  for (let i = 0; i < n; i += stepI) {
    xTicks.push({ i, label: formatAxisDate(pts[i]?.date), x: xAt(i, n) })
  }
  if (n > 1 && xTicks[xTicks.length - 1]?.i !== n - 1) {
    xTicks.push({ i: n - 1, label: formatAxisDate(pts[n - 1]?.date), x: xAt(n - 1, n) })
  }
  return { min: y0, max: y1, yTicks, xTicks, n }
})

const emptySelf = computed(() => {
  if (data.value?.empty_self_series) return true
  return !series.value.some((p: any) => p.self_adr != null && p.self_adr !== '')
})

const pathSelf = computed(() => buildPath(series.value.map((p: any) => p.self_adr)))
const pathComp = computed(() => buildPath(series.value.map((p: any) => p.comp_median)))
const pathOta = computed(() => buildPath(series.value.map((p: any) => p.ota_min)))

function niceStep(raw: number) {
  if (raw <= 0) return 50
  const pow = Math.pow(10, Math.floor(Math.log10(raw)))
  const n = raw / pow
  if (n <= 1) return pow
  if (n <= 2) return 2 * pow
  if (n <= 5) return 5 * pow
  return 10 * pow
}

function formatAxisDate(iso?: string) {
  if (!iso) return ''
  const p = String(iso).slice(5).split('-')
  if (p.length < 2) return String(iso).slice(5)
  return `${Number(p[0])}/${Number(p[1])}`
}

function xAt(i: number, n: number) {
  const { padL, padR, w } = CHART
  const plotW = w - padL - padR
  if (n <= 1) return padL + plotW / 2
  return padL + (i / (n - 1)) * plotW
}

function yAt(v: number) {
  const { padT, padB, h } = CHART
  const plotH = h - padT - padB
  const { min, max } = chartScale.value
  const t = (v - min) / Math.max(max - min, 1)
  return padT + (1 - t) * plotH
}

function buildPath(vals: (number | null | undefined)[]) {
  const n = vals.length
  if (!n) return ''
  const parts: string[] = []
  let started = false
  for (let i = 0; i < n; i++) {
    const v = vals[i]
    if (v == null || v === ('' as any) || Number.isNaN(Number(v))) {
      started = false
      continue
    }
    const x = xAt(i, n)
    const y = yAt(Number(v))
    parts.push(`${started ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`)
    started = true
  }
  return parts.join(' ')
}

function kpiDeltaText(k: any) {
  if (k.delta == null || k.delta === '') return '—'
  const n = Number(k.delta)
  if (Number.isNaN(n)) return '—'
  return `${n > 0 ? '+' : ''}${n}%`
}

const chartTitle = computed(() => `近 ${win.value} 天平均房价走势`)
const yAxisLabel = '房价 (¥)'
</script>

<template>
  <div v-if="data">
    <div class="kpi-row">
      <div v-for="(k, i) in data.kpis" :key="i" class="kpi card-clean">
        <div class="label">{{ k.label }}</div>
        <div class="value">
          {{ typeof k.value === 'number' ? fmt(k.value) : k.value }}
        </div>
        <div v-if="k.hint" class="hint">{{ k.hint }}</div>
        <div
          v-else
          class="delta"
          :class="(k.delta || 0) > 0 ? 'up' : (k.delta || 0) < 0 ? 'down' : 'flat'"
        >
          {{ kpiDeltaText(k) }}
        </div>
      </div>
    </div>

    <div class="card-clean" style="margin-bottom: 14px">
      <div class="card-head">
        <span class="title">{{ chartTitle }}</span>
        <span class="sub">
          {{
            enabledComp
              ? t('本店 vs 竞品中位 vs 线上最低价')
              : t('内部版 · 仅本店平均房价（开启竞品对比后叠加）')
          }}</span
        >
        <span class="gap" />
        <div class="seg">
          <button type="button" :class="{ on: win === '7' }" @click="win = '7'">
            {{ t('7 天') }}
          </button>
          <button type="button" :class="{ on: win === '14' }" @click="win = '14'">
            {{ t('14 天') }}
          </button>
          <button type="button" :class="{ on: win === '30' }" @click="win = '30'">
            {{ t('30 天') }}
          </button>
        </div>
      </div>
      <div class="chart">
        <div v-if="emptySelf" class="na chart-empty">
          {{ t('暂无本店平均房价样本。有订单房价或生成定价建议后将自动绘制走势。') }}
        </div>
        <svg
          v-else
          :viewBox="`0 0 ${CHART.w} ${CHART.h}`"
          class="price-svg"
          role="img"
          :aria-label="chartTitle"
        >
          <!-- 绘图区背景 -->
          <rect
            :x="CHART.padL"
            :y="CHART.padT"
            :width="CHART.w - CHART.padL - CHART.padR"
            :height="CHART.h - CHART.padT - CHART.padB"
            fill="#fafbfc"
          />
          <!-- Y 轴网格 + 刻度 -->
          <g v-for="(tick, ti) in chartScale.yTicks" :key="'y' + ti">
            <line
              :x1="CHART.padL"
              :x2="CHART.w - CHART.padR"
              :y1="yAt(tick)"
              :y2="yAt(tick)"
              stroke="#e5e9f0"
              stroke-dasharray="3 3"
            />
            <text :x="CHART.padL - 8" :y="yAt(tick) + 4" text-anchor="end" class="axis-label">
              {{ tick }}
            </text>
          </g>
          <!-- 坐标轴线 -->
          <line
            :x1="CHART.padL"
            :y1="CHART.padT"
            :x2="CHART.padL"
            :y2="CHART.h - CHART.padB"
            stroke="#94a3b8"
            stroke-width="1.25"
          />
          <line
            :x1="CHART.padL"
            :y1="CHART.h - CHART.padB"
            :x2="CHART.w - CHART.padR"
            :y2="CHART.h - CHART.padB"
            stroke="#94a3b8"
            stroke-width="1.25"
          />
          <!-- Y 轴标题 -->
          <text
            :x="14"
            :y="CHART.h / 2"
            text-anchor="middle"
            class="axis-title"
            :transform="`rotate(-90 14 ${CHART.h / 2})`"
          >
            {{ yAxisLabel }}
          </text>
          <!-- X 轴刻度 -->
          <g v-for="(xt, xi) in chartScale.xTicks" :key="'x' + xi">
            <line
              :x1="xt.x"
              :x2="xt.x"
              :y1="CHART.h - CHART.padB"
              :y2="CHART.h - CHART.padB + 5"
              stroke="#94a3b8"
            />
            <text :x="xt.x" :y="CHART.h - CHART.padB + 18" text-anchor="middle" class="axis-label">
              {{ xt.label }}
            </text>
          </g>
          <text
            :x="(CHART.padL + CHART.w - CHART.padR) / 2"
            :y="CHART.h - 4"
            text-anchor="middle"
            class="axis-title"
          >
            {{ t('日期') }}
          </text>
          <!-- 折线 -->
          <path :d="pathSelf" fill="none" stroke="#1d4ed8" stroke-width="2" />
          <path
            v-if="enabledComp && pathComp"
            :d="pathComp"
            fill="none"
            stroke="#d97706"
            stroke-width="2"
            stroke-dasharray="4 3"
          />
          <path
            v-if="enabledComp && pathOta"
            :d="pathOta"
            fill="none"
            stroke="#9ca3af"
            stroke-width="2"
          />
        </svg>
      </div>
      <div class="legend">
        <span class="leg-title">{{ t('图例') }}</span>
        <span class="leg-item">
          <span class="swatch solid" style="--sw: #1d4ed8"></span>
          {{ t('本店平均房价') }}</span
        >
        <template v-if="enabledComp">
          <span class="leg-item">
            <span class="swatch dashed" style="--sw: #d97706"></span>
            {{ t('竞品中位') }}</span
          >
          <span class="leg-item">
            <span class="swatch solid" style="--sw: #9ca3af"></span>
            {{ t('线上最低价') }}</span
          >
        </template>
        <span v-else class="leg-hint">{{ t('开启竞品对比后显示竞品中位与线上最低价') }}</span>
      </div>
    </div>

    <div class="grid2">
      <div class="card-clean">
        <div class="card-head">
          <span class="title">{{ t('房态 / 库存趋势（本店）') }}</span>
        </div>
        <div class="trend-bar">
          <div v-for="p in data.occ_series || []" :key="p.date" class="col">
            <div
              class="bar"
              :style="{
                height: Math.max(8, Math.min(100, p.occ)) + '%',
                background: p.occ >= 70 ? '#16a34a' : '#d97706',
              }"
            />
            <div class="v">{{ p.occ }}%</div>
            <div class="lbl">{{ p.date?.slice(5) }}</div>
          </div>
        </div>
        <div class="foot-hint">
          {{ t('在住率与可售库存反向：低入住日是主动降价释放的触发点。') }}
        </div>
      </div>

      <div class="card-clean">
        <div class="card-head">
          <span class="title">{{ t('竞品变价事件') }}</span>
        </div>
        <div v-if="!enabledComp" class="na">
          {{
            t('竞品对比未开启：此处为内部版占位。配置竞品并开启开关后，展示竞品公开价变价推断。')
          }}
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>{{ t('日期') }}</th>
              <th>{{ t('竞品') }}</th>
              <th class="num">{{ t('原→新') }}</th>
              <th class="num">{{ t('幅度') }}</th>
              <th>{{ t('推断原因') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(e, i) in data.comp_events" :key="i">
              <td>{{ e.date?.slice(5) }}</td>
              <td>{{ e.comp_name }}</td>
              <td class="num">{{ fmt(e.from) }}→{{ fmt(e.to) }}</td>
              <td class="num" :class="e.delta_pct >= 0 ? 'up' : 'down'">
                {{ e.delta_pct >= 0 ? '+' : '' }}{{ e.delta_pct }}%
              </td>
              <td>{{ e.inferred_reason }}</td>
            </tr>
            <tr v-if="!(data.comp_events || []).length">
              <td colspan="5" class="empty">{{ t('暂无显著变价') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="ai-card" style="margin-top: 14px">
      <div class="ttl">
        <span class="material-symbols-outlined">auto_awesome</span>{{ t('AI 总结') }}
      </div>
      <p>{{ data.ai_summary }}</p>
    </div>
  </div>
</template>

<style scoped>
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
.kpi {
  padding: 12px 14px;
}
.label {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.value {
  font-size: 22px;
  font-weight: 700;
  margin-top: 4px;
}
.hint {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-top: 4px;
}
.delta.up {
  color: #16a34a;
  font-size: 11px;
}
.delta.down {
  color: #dc2626;
  font-size: 11px;
}
.delta.flat {
  color: var(--on-surface-variant);
  font-size: 11px;
}
.card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.title {
  font-weight: 650;
  font-size: 14px;
}
.sub {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.gap {
  flex: 1;
}
.seg {
  display: inline-flex;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}
.seg button {
  border: none;
  background: transparent;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;
  color: var(--on-surface-variant);
}
.seg button.on {
  background: var(--primary);
  color: #fff;
}
.chart {
  padding: 8px 8px 4px;
  border: 1px solid #edf1f6;
  border-radius: 6px;
  background: #fff;
}
.price-svg {
  width: 100%;
  height: 240px;
  display: block;
}
.axis-label {
  fill: #64748b;
  font-size: 11px;
  font-family: ui-sans-serif, system-ui, sans-serif;
}
.axis-title {
  fill: #94a3b8;
  font-size: 11px;
  font-family: ui-sans-serif, system-ui, sans-serif;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 20px;
  /* 与卡片框体底边、左边留白，避免贴边 */
  margin: 12px 16px 16px;
  padding: 10px 14px;
  border-radius: 8px;
  background: #f5f7fa;
  border: 1px solid #eef1f5;
  font-size: 12px;
  color: #475569;
  line-height: 1.3;
  box-sizing: border-box;
}
.leg-title {
  font-weight: 650;
  font-size: 12px;
  color: #334155;
  margin-right: 4px;
  flex-shrink: 0;
}
.leg-title::after {
  content: '：';
}
.leg-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.swatch {
  display: inline-block;
  width: 22px;
  height: 0;
  border-top-width: 2.5px;
  border-top-style: solid;
  border-top-color: var(--sw, #64748b);
  flex-shrink: 0;
  border-radius: 1px;
}
.swatch.dashed {
  border-top-style: dashed;
}
.leg-hint {
  font-size: 11px;
  color: #94a3b8;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.trend-bar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 120px;
  padding: 10px 0;
  border-bottom: 1px solid #edf1f6;
}
.col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.bar {
  width: 100%;
  border-radius: 3px 3px 0 0;
  min-height: 4px;
}
.v {
  font-size: 10px;
  font-weight: 600;
}
.lbl {
  font-size: 10px;
  color: var(--on-surface-variant);
}
.foot-hint {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-top: 8px;
}
.na {
  padding: 24px 12px;
  text-align: center;
  font-size: 12px;
  color: var(--on-surface-variant);
  background: #f9fafb;
  border-radius: 6px;
}
.chart-empty {
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1.55;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
th {
  text-align: left;
  padding: 8px;
  background: #f9fafb;
  color: var(--on-surface-variant);
  border-bottom: 1px solid #e5e7eb;
}
td {
  padding: 8px;
  border-bottom: 1px solid #edf1f6;
}
.num {
  text-align: right;
}
.up {
  color: #16a34a;
  font-weight: 600;
}
.down {
  color: #dc2626;
  font-weight: 600;
}
.empty {
  text-align: center;
  color: var(--on-surface-variant);
}
.ai-card {
  padding: 14px;
  background: #f3e8ff;
  border-left: 3px solid #9333ea;
  border-radius: 8px;
}
.ai-card .ttl {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 650;
  color: #9333ea;
  margin-bottom: 6px;
}
.ai-card p {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
}
@media (max-width: 900px) {
  .kpi-row,
  .grid2 {
    grid-template-columns: 1fr;
  }
}
</style>
