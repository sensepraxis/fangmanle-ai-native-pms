<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 未来 30 天入住压力热力图
 * - 锚点日起 30 天（默认真日）
 * - 压力色：低压 #4ECDC4 / 中压 #F7B731 / 高压 #E74C3C
 * - 预测与已订分开展示；悬停看同比环比；高压可下钻房型
 */
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'

const days = ref<any[]>([])
const padBefore = ref(0)
const loadError = ref('')
const meta = ref<any>(null)
const loading = ref(false)

const anchor = ref(isoToday())
const customDate = ref(isoToday())

const HEAT: Record<string, string> = {
  low: '#4ECDC4',
  med: '#F7B731',
  high: '#E74C3C',
}
const HEAT_TX: Record<string, string> = {
  low: '#0f5c57',
  med: '#7a4d00',
  high: '#fff',
}

const hoverTip = ref('')
const drillOpen = ref(false)
const drillLoading = ref(false)
const drillError = ref('')
const drillLabel = ref('')
const drillItems = ref<any[]>([])

function isoToday() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function addDays(iso: string, n: number) {
  const d = new Date(iso + 'T12:00:00')
  d.setDate(d.getDate() + n)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const rangeHint = computed(() => {
  if (!days.value.length) return t('今日起未来 30 天')
  const a = days.value[0]
  const b = days.value[days.value.length - 1]
  return `${cellDateLabel(a)} – ${cellDateLabel(b)}`
})

function cellDateLabel(d: any) {
  if (!d) return ''
  if (d.label_cell) return d.label_cell
  const wd =
    d.weekday_cn ||
    (d.weekday != null
      ? t(['周一', '周二', '周三', '周四', '周五', '周六', '周日'][d.weekday] || '')
      : '')
  return `${d.label || d.date || ''}${wd ? ` ${wd}` : ''}`.trim()
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const fc = await api.inventoryForecast(hotelStore.hotelId, 30, anchor.value)
    const list = (fc?.days || []).slice(0, 30)
    days.value = list
    padBefore.value = list.length ? Number(list[0].weekday || 0) : 0
    meta.value = fc?.meta || null
  } catch (e: any) {
    days.value = []
    meta.value = null
    loadError.value = e?.message || t('热力图加载失败')
  } finally {
    loading.value = false
  }
}

function jumpToday() {
  anchor.value = isoToday()
  customDate.value = anchor.value
  load()
}

function jumpOffset(n: number) {
  anchor.value = addDays(isoToday(), n)
  customDate.value = anchor.value
  load()
}

function onCustomDate() {
  if (!customDate.value) return
  anchor.value = customDate.value
  load()
}

function cellTitle(d: any) {
  const bits = [cellDateLabel(d)]
  if (d.predicted_pct != null) bits.push(t('预测 {n}%', { n: d.predicted_pct }))
  bits.push(t('已订 {n}%', { n: d.booked_pct }))
  bits.push(
    t('已售 {sold} / 可售 {available}（停用 {blocked}）', {
      sold: d.sold,
      available: d.available,
      blocked: d.blocked || 0,
    }),
  )
  if (d.hist_yoy_pct != null) bits.push(t('去年同期 {n}%', { n: d.hist_yoy_pct }))
  if (d.hist_mom_pct != null) bits.push(t('上月同期 {n}%', { n: d.hist_mom_pct }))
  return bits.join(' · ')
}

function onEnter(d: any) {
  const lines = []
  if (d.hist_yoy_pct != null) lines.push(t('去年同期入住 {n}%', { n: d.hist_yoy_pct }))
  else lines.push(t('去年同期：暂无历史样本'))
  if (d.hist_mom_pct != null) lines.push(t('上月同期入住 {n}%', { n: d.hist_mom_pct }))
  else lines.push(t('上月同期：暂无历史样本'))
  lines.push(t('历史仅作参考，不并排展示热力'))
  hoverTip.value = lines.join(' · ')
}

function onLeave() {
  hoverTip.value = ''
}

async function onCellClick(d: any) {
  if (d.heat !== 'high') return
  drillOpen.value = true
  drillLoading.value = true
  drillError.value = ''
  drillLabel.value = d.label || d.date
  drillItems.value = []
  try {
    const res = await api.inventoryForecastDayDetail(hotelStore.hotelId, d.date)
    drillLabel.value = res?.label || d.label
    drillItems.value = res?.items || []
  } catch (e: any) {
    drillError.value = e?.message || t('房型明细加载失败')
  } finally {
    drillLoading.value = false
  }
}

function closeDrill() {
  drillOpen.value = false
}

onMounted(load)
watch(
  () => hotelStore.hotelId,
  () => {
    anchor.value = isoToday()
    customDate.value = anchor.value
    load()
  },
)

defineExpose({ reload: load })
</script>

<template>
  <section class="heat-panel">
    <div class="heat-head">
      <div>
        <h2>{{ t('30天入住率热力图') }}</h2>
        <p class="sub">{{ t('未来窗口 · 指导定价与促销（{range}）', { range: rangeHint }) }}</p>
      </div>
      <div class="legend">
        <span><i class="dot low" />{{ t('低压 0–40% · 宜促销') }}</span>
        <span><i class="dot med" />{{ t('中压 41–80%') }}</span>
        <span><i class="dot high" />{{ t('高压 81–100% · 宜提价') }}</span>
      </div>
    </div>

    <div class="anchor-bar">
      <button type="button" class="chip" :class="{ on: anchor === isoToday() }" @click="jumpToday">
        {{ t('今日') }}
      </button>
      <button type="button" class="chip" @click="jumpOffset(7)">{{ t('+7天') }}</button>
      <button type="button" class="chip" @click="jumpOffset(30)">{{ t('+30天') }}</button>
      <button type="button" class="chip" @click="jumpOffset(90)">{{ t('+90天') }}</button>
      <label class="date-pick">
        <span class="material-symbols-outlined">calendar_month</span>
        <input v-model="customDate" type="date" @change="onCustomDate" />
      </label>
      <span class="anchor-hint">{{ t('锚点') }} {{ anchor }} {{ t('起') }} 30 {{ t('天') }}</span>
    </div>

    <div class="formula-box">
      <div class="formula-title">
        <span class="material-symbols-outlined">functions</span>
        {{ t('口径说明') }}
      </div>
      <ol class="formula-list">
        <li>
          <strong>{{ t('已订率') }}</strong>
          <code>{{ t('已售 / (已售 + 可售) × 100') }}</code>
          {{ t('，停用/维修房不计入分母；展示如') }} <code>89%（40/45）</code>
        </li>
        <li>
          <strong>{{ t('预测 vs 已订') }}</strong>
          {{ t('有预测时主数字为预测入住率，括号内为当前已订率：') }}
          <code>{{ t('84%（已订 42%）') }}</code> {{ t('，避免混成一个数') }}
        </li>
        <li>
          <strong>{{ t('压力色') }}</strong>
          {{ t('优先按预测分级；无预测则按已订。蓝宜促 · 黄正常 · 红宜提价') }}
        </li>
        <li>
          <strong>{{ t('历史') }}</strong>
          {{ t('同比/环比仅悬停参考，不并排历史热力（过去 30 天归经营分析报表）') }}
        </li>
      </ol>
      <p v-if="meta" class="formula-meta">
        {{ t('库存行') }} {{ meta.night_rows ?? 0 }} · {{ t('覆盖') }} {{ meta.covered_days ?? 0 }}
        {{ t('天 · 在册') }} {{ meta.room_total ?? '—' }} {{ t('间') }}
      </p>
    </div>

    <p v-if="hoverTip" class="hover-tip">{{ hoverTip }}</p>
    <p v-if="loadError" class="err">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">{{ t('加载中…') }}</p>

    <div class="heat-grid">
      <div class="dow">{{ t('周一') }}</div>
      <div class="dow">{{ t('周二') }}</div>
      <div class="dow">{{ t('周三') }}</div>
      <div class="dow">{{ t('周四') }}</div>
      <div class="dow">{{ t('周五') }}</div>
      <div class="dow">{{ t('周六') }}</div>
      <div class="dow">{{ t('周日') }}</div>
      <div v-for="n in padBefore" :key="'pad' + n" class="heat-pad" />
      <button
        v-for="d in days"
        :key="d.date"
        type="button"
        class="heat-cell"
        :class="{ high: d.heat === 'high', clickable: d.heat === 'high' }"
        :style="{ background: HEAT[d.heat] || HEAT.med, color: HEAT_TX[d.heat] || HEAT_TX.med }"
        :title="cellTitle(d)"
        @mouseenter="onEnter(d)"
        @mouseleave="onLeave"
        @click="onCellClick(d)"
      >
        <div class="line1">{{ cellDateLabel(d) }}</div>
        <div class="line2">
          <template v-if="d.predicted_pct != null">
            <span class="pred">{{ d.predicted_pct }}%</span>
            <span class="booked-sub">{{ t('（已订 {n}%）', { n: d.booked_pct }) }}</span>
          </template>
          <template v-else>
            <span class="pred">{{ d.booked_pct }}%</span>
            <span class="booked-sub">{{ t('已订') }}</span>
          </template>
        </div>
        <div class="line3">
          {{ t('已售 {sold} / 可售 {available}', { sold: d.sold, available: d.available }) }}
        </div>
      </button>
      <div v-if="!days.length && !loadError && !loading" class="empty">{{ t('暂无热力数据') }}</div>
    </div>
    <p class="foot-hint">{{ t('点击红色高压日可下钻查看「房型 × 日」明细（哪类房先售罄）。') }}</p>

    <div v-if="drillOpen" class="drill-mask" @click.self="closeDrill">
      <div class="drill-panel" role="dialog" aria-modal="true">
        <header>
          <h3>{{ t('{label} · 房型压力明细', { label: drillLabel }) }}</h3>
          <button type="button" class="x" @click="closeDrill">{{ t('关闭') }}</button>
        </header>
        <p v-if="drillLoading" class="muted">{{ t('加载中…') }}</p>
        <p v-else-if="drillError" class="err">{{ drillError }}</p>
        <table v-else class="drill-table">
          <thead>
            <tr>
              <th>{{ t('房型') }}</th>
              <th>{{ t('已订率') }}</th>
              <th>{{ t('已售') }}</th>
              <th>{{ t('可售') }}</th>
              <th>{{ t('停用') }}</th>
              <th>{{ t('状态') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="it in drillItems" :key="it.room_type_name">
              <td>{{ it.room_type_name }}</td>
              <td>
                <span class="pill" :class="it.heat">{{ it.booked_pct }}%</span>
              </td>
              <td>{{ it.sold }}</td>
              <td>{{ it.available }}</td>
              <td>{{ it.blocked }}</td>
              <td>{{ it.sold_out ? t('已售罄') : t('有余量') }}</td>
            </tr>
            <tr v-if="!drillItems.length">
              <td colspan="6" class="muted">{{ t('暂无房型明细') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<style scoped>
.heat-panel {
  background: #fff;
  border: 1px solid var(--outline-variant, #e2e5eb);
  border-radius: 12px;
  padding: 20px 22px;
}
.heat-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.heat-head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}
.sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: #6b7280;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #5b616e;
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  display: inline-block;
}
.dot.low {
  background: #4ecdc4;
}
.dot.med {
  background: #f7b731;
}
.dot.high {
  background: #e74c3c;
}

.anchor-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.chip {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.chip.on {
  border-color: #1a73e8;
  color: #1a73e8;
  background: #eef5ff;
}
.date-pick {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  padding: 4px 8px;
  background: #fff;
}
.date-pick .material-symbols-outlined {
  font-size: 18px;
  color: #5b616e;
}
.date-pick input {
  border: none;
  outline: none;
  font-size: 12px;
  background: transparent;
}
.anchor-hint {
  font-size: 11px;
  color: #9aa1ad;
}

.formula-box {
  margin: 0 0 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f6f8fb;
  border: 1px solid #e2e8f0;
}
.formula-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
}
.formula-title .material-symbols-outlined {
  font-size: 18px;
  color: #1a73e8;
}
.formula-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.65;
  color: #3c4048;
}
.formula-list code {
  font-family: ui-monospace, 'Cascadia Code', 'Roboto Mono', monospace;
  font-size: 11px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 1px 5px;
}
.formula-meta {
  margin: 8px 0 0;
  font-size: 11px;
  color: #6b7280;
}
.hover-tip {
  margin: 0 0 8px;
  font-size: 12px;
  color: #5b616e;
  background: #fff8e8;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 8px 10px;
}
.err {
  margin: 0 0 10px;
  font-size: 12px;
  color: #b91c1c;
}
.muted {
  margin: 0 0 10px;
  font-size: 12px;
  color: #9aa1ad;
}

.heat-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
}
.dow {
  text-align: center;
  font-size: 12px;
  color: #5b616e;
  padding: 6px 0;
}
.heat-pad {
  min-height: 108px;
}
.heat-cell {
  min-height: 108px;
  border-radius: 10px;
  padding: 8px 9px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
  text-align: left;
  border: 1px solid transparent;
  cursor: default;
  transition:
    transform 0.12s ease,
    box-shadow 0.12s ease;
}
.heat-cell.clickable {
  cursor: pointer;
}
.heat-cell:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgb(0 0 0 / 0.12);
}
.heat-cell.high {
  border-color: #c0392b;
}
.line1 {
  font-size: 10px;
  font-weight: 700;
  line-height: 1.25;
}
.line2 {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px;
}
.pred {
  font-size: 18px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.booked-sub {
  font-size: 11px;
  font-weight: 600;
  opacity: 0.9;
}
.line3 {
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  opacity: 0.95;
}
.empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px 0;
  color: #5b616e;
  font-size: 13px;
}
.foot-hint {
  margin: 10px 0 0;
  font-size: 11px;
  color: #9aa1ad;
}

.drill-mask {
  position: fixed;
  inset: 0;
  background: rgb(15 23 42 / 0.45);
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.drill-panel {
  width: min(640px, 100%);
  max-height: 80vh;
  overflow: auto;
  background: #fff;
  border-radius: 12px;
  padding: 16px 18px;
  box-shadow: 0 16px 40px rgb(0 0 0 / 0.2);
}
.drill-panel header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.drill-panel h3 {
  margin: 0;
  font-size: 16px;
}
.drill-panel .x {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 6px;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 12px;
}
.drill-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.drill-table th,
.drill-table td {
  border-bottom: 1px solid #eef0f4;
  padding: 8px 6px;
  text-align: left;
}
.pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 12px;
}
.pill.low {
  background: #d9f7f5;
  color: #0f5c57;
}
.pill.med {
  background: #fff3d6;
  color: #7a4d00;
}
.pill.high {
  background: #fde2e0;
  color: #c0392b;
}
</style>
