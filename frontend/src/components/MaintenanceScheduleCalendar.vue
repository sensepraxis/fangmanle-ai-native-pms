<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'
import { localizeSeedText } from '../lib/localizeSeed'

/**
 * 维修排期日历 —— 整月网格（周一为首列），展示当月全部排期
 */
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'

export type ScheduleItem = {
  id: string
  woId?: string
  label: string
  area: string
  sub: string
  startDay: number
  span: number
  lane: number
  status: 'scheduled' | 'repairing' | 'overdue' | 'completed' | 'ai'
  assetId?: number
}

type MonthCell = {
  day: number | null
  inMonth: boolean
}

const props = defineProps<{
  externalTasks?: any[]
}>()

const emit = defineEmits<{
  select: [item: ScheduleItem]
}>()

const todayRef = ref(new Date())
const viewDate = ref(new Date())
const WEEKDAY_LABELS = computed(() => [
  t('周一'),
  t('周二'),
  t('周三'),
  t('周四'),
  t('周五'),
  t('周六'),
  t('周日'),
])
const MAX_EVENTS_PER_DAY = 3

const allItems = ref<ScheduleItem[]>([])
const stats = ref({ total: 0, overdue: 0, repairing: 0 })
const loading = ref(true)
const boardCache = ref<{ maint: any[]; assets: any[] } | null>(null)

const viewYear = computed(() => viewDate.value.getFullYear())
const viewMonth = computed(() => viewDate.value.getMonth())
const daysInMonth = computed(() => new Date(viewYear.value, viewMonth.value + 1, 0).getDate())
const monthTitle = computed(() => t('{y}年{m}月', { y: viewYear.value, m: viewMonth.value + 1 }))

const monthInputValue = computed({
  get: () => {
    const y = viewYear.value
    const m = String(viewMonth.value + 1).padStart(2, '0')
    return `${y}-${m}`
  },
  set: (v: string) => {
    const m = /^(\d{4})-(\d{2})$/.exec(v)
    if (!m) return
    const y = Number(m[1])
    const mo = Number(m[2]) - 1
    if (mo < 0 || mo > 11) return
    viewDate.value = new Date(y, mo, 1)
  },
})

const isViewingCurrentMonth = computed(() => {
  const t = todayRef.value
  return t.getFullYear() === viewYear.value && t.getMonth() === viewMonth.value
})

const todayParts = computed(() => ({
  year: todayRef.value.getFullYear(),
  month: todayRef.value.getMonth(),
  day: todayRef.value.getDate(),
}))

const monthGrid = computed<MonthCell[]>(() => {
  const year = viewYear.value
  const month = viewMonth.value
  const dim = daysInMonth.value
  const firstDow = (new Date(year, month, 1).getDay() + 6) % 7
  const cells: MonthCell[] = []
  for (let i = 0; i < firstDow; i++) cells.push({ day: null, inMonth: false })
  for (let d = 1; d <= dim; d++) cells.push({ day: d, inMonth: true })
  while (cells.length % 7 !== 0) cells.push({ day: null, inMonth: false })
  return cells
})

const STATUS_META = computed(() => ({
  scheduled: { label: t('已排程'), cls: 'st-scheduled' },
  repairing: { label: t('维修中'), cls: 'st-repairing' },
  overdue: { label: t('逾期'), cls: 'st-overdue' },
  completed: { label: t('已完成'), cls: 'st-completed' },
  ai: { label: t('AI 安排'), cls: 'st-ai' },
}))

const legend = computed(() => Object.entries(STATUS_META.value).map(([k, v]) => ({ key: k, ...v })))

function parseIsoDate(raw?: string): Date | null {
  if (!raw) return null
  const s = String(raw).trim().slice(0, 10)
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s)
  if (!m) return null
  const y = Number(m[1])
  const mo = Number(m[2]) - 1
  const d = Number(m[3])
  const dt = new Date(y, mo, d)
  if (dt.getFullYear() !== y || dt.getMonth() !== mo || dt.getDate() !== d) return null
  return dt
}

function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

function dayInViewMonth(raw: string | undefined, year: number, month: number): number | null {
  const dt = parseIsoDate(raw)
  if (!dt) return null
  if (dt.getFullYear() !== year || dt.getMonth() !== month) return null
  return dt.getDate()
}

function mapStatus(st?: string, dueDate?: Date | null): ScheduleItem['status'] {
  if (st === 'done') return 'completed'
  if (st === 'doing') return 'repairing'
  if (st === 'overdue') return 'overdue'
  if (dueDate) {
    const today = startOfDay(todayRef.value)
    if (dueDate < today) return 'overdue'
  }
  return 'scheduled'
}

function areaIcon(area: string) {
  if (/暖通|空调/.test(area)) return 'ac_unit'
  if (/弱电|门锁/.test(area)) return 'sensors'
  if (/客房|卫浴|电视/.test(area)) return 'bed'
  if (/电梯/.test(area)) return 'elevator'
  if (/公区/.test(area)) return 'storefront'
  return 'precision_manufacturing'
}

function isWeekend(day: number) {
  const jsDow = new Date(viewYear.value, viewMonth.value, day).getDay()
  return jsDow === 0 || jsDow === 6
}

function isToday(day: number) {
  const t = todayParts.value
  return t.year === viewYear.value && t.month === viewMonth.value && t.day === day
}

function formatYmd(day: number) {
  return t('{y}年{m}月{d}日', {
    y: viewYear.value,
    m: viewMonth.value + 1,
    d: day,
  })
}

function itemsOnDay(day: number) {
  return allItems.value
    .filter((item) => item.startDay === day)
    .sort((a, b) => {
      const w = (s: ScheduleItem['status']) =>
        ({ overdue: 0, repairing: 1, scheduled: 2, ai: 3, completed: 4 })[s] ?? 5
      return w(a.status) - w(b.status) || a.label.localeCompare(b.label, 'zh-CN')
    })
}

function visibleItems(day: number) {
  return itemsOnDay(day).slice(0, MAX_EVENTS_PER_DAY)
}

function overflowCount(day: number) {
  const n = itemsOnDay(day).length
  return n > MAX_EVENTS_PER_DAY ? n - MAX_EVENTS_PER_DAY : 0
}

function buildFromBoard(maint: any[], assets: any[]) {
  const year = viewYear.value
  const month = viewMonth.value
  const assetById = Object.fromEntries(assets.map((a) => [a.id, a]))
  const items: ScheduleItem[] = []
  const seenAssetDay = new Set<string>()

  const pushItem = (item: ScheduleItem) => {
    const key = `${item.assetId || item.id}-${item.startDay}`
    if (seenAssetDay.has(key)) return
    seenAssetDay.add(key)
    items.push(item)
  }

  for (const m of maint) {
    const due = parseIsoDate(m.due_date)
    const day = dayInViewMonth(m.due_date, year, month)
    if (day == null) continue

    const asset = assetById[m.asset_id]
    const area = t(String(asset?.category || '综合维保'))
    const label = [
      asset?.room_no ? t('{n} 房', { n: asset.room_no }) : '',
      localizeSeedText(asset?.name || m.task_type || t('维保')),
    ]
      .filter(Boolean)
      .join(' · ')

    pushItem({
      id: `m-${m.id}`,
      woId: `WO-${m.id}`,
      label,
      area,
      sub: localizeSeedText(m.task_type || ''),
      startDay: day,
      span: 1,
      lane: 0,
      status: mapStatus(m.status, due),
      assetId: m.asset_id,
    })
  }

  for (const a of assets.filter((x) => x.next_maintain_date)) {
    const due = parseIsoDate(a.next_maintain_date)
    const day = dayInViewMonth(a.next_maintain_date, year, month)
    if (day == null) continue
    if (items.some((x) => x.assetId === a.id)) continue

    pushItem({
      id: `a-${a.id}`,
      label: [a.room_no ? t('{n} 房', { n: a.room_no }) : '', localizeSeedText(a.name || t('设备'))]
        .filter(Boolean)
        .join(' · '),
      area: t(String(a.category || '计划维保')),
      sub: t('计划维保'),
      startDay: day,
      span: 1,
      lane: 0,
      status: 'ai',
      assetId: a.id,
    })
  }

  allItems.value = items
  stats.value = {
    total: items.length,
    overdue: items.filter((x) => x.status === 'overdue').length,
    repairing: items.filter((x) => x.status === 'repairing').length,
  }
}

function shiftMonth(delta: number) {
  const d = viewDate.value
  viewDate.value = new Date(d.getFullYear(), d.getMonth() + delta, 1)
}

function goTodayMonth() {
  const t = todayRef.value
  viewDate.value = new Date(t.getFullYear(), t.getMonth(), 1)
}

function applyBoard() {
  if (!boardCache.value) {
    allItems.value = []
    stats.value = { total: 0, overdue: 0, repairing: 0 }
    return
  }
  buildFromBoard(boardCache.value.maint, boardCache.value.assets)
}

function onSelect(item: ScheduleItem) {
  emit('select', item)
}

async function load() {
  loading.value = true
  todayRef.value = new Date()
  try {
    const board = await api.assetsBoard(hotelStore.hotelId)
    boardCache.value = {
      maint: board?.maintenance || [],
      assets: board?.assets || [],
    }
    applyBoard()
  } catch {
    boardCache.value = null
    allItems.value = []
    stats.value = { total: 0, overdue: 0, repairing: 0 }
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(viewDate, () => applyBoard())
watch(
  () => props.externalTasks,
  () => {},
  { deep: true },
)

defineExpose({ reload: load })
</script>

<template>
  <section class="msc">
    <div class="msc-head">
      <div class="msc-head-l">
        <h2 class="msc-title">
          <span class="material-symbols-outlined">calendar_month</span>
          {{ t('维修排期日历') }}
        </h2>
        <div class="month-nav">
          <button type="button" class="nav-btn" :title="t('上一月')" @click="shiftMonth(-1)">
            <span class="material-symbols-outlined">chevron_left</span>
          </button>
          <label class="month-pick">
            <span class="month-pick-label">{{ monthTitle }}</span>
            <input
              v-model="monthInputValue"
              type="month"
              class="month-input"
              :max="`${todayRef.getFullYear() + 2}-12`"
              :min="`${todayRef.getFullYear() - 3}-01`"
            />
            <span class="material-symbols-outlined month-pick-ico">calendar_today</span>
          </label>
          <button type="button" class="nav-btn" :title="t('下一月')" @click="shiftMonth(1)">
            <span class="material-symbols-outlined">chevron_right</span>
          </button>
          <button
            v-if="!isViewingCurrentMonth"
            type="button"
            class="nav-today"
            @click="goTodayMonth"
          >
            {{ t('回到本月') }}
          </button>
        </div>
      </div>
      <div class="msc-stats">
        <span class="msc-stat"
          ><strong>{{ stats.total }}</strong> {{ t('项排期') }}</span
        >
        <span v-if="stats.repairing" class="msc-stat warn"
          ><strong>{{ stats.repairing }}</strong> {{ t('维修中') }}</span
        >
        <span v-if="stats.overdue" class="msc-stat err"
          ><strong>{{ stats.overdue }}</strong> {{ t('逾期') }}</span
        >
      </div>
    </div>

    <div class="msc-legend">
      <span v-for="lg in legend" :key="lg.key" class="msc-leg">
        <i class="leg-dot" :class="lg.cls" />{{ lg.label }}</span
      >
    </div>

    <div v-if="loading" class="msc-empty">{{ t('加载排期…') }}</div>

    <div v-else class="month-wrap">
      <div class="month-head-row">
        <div v-for="wd in WEEKDAY_LABELS" :key="wd" class="month-wd">{{ wd }}</div>
      </div>

      <div class="month-grid">
        <div
          v-for="(cell, idx) in monthGrid"
          :key="idx"
          class="month-cell"
          :class="{
            pad: !cell.inMonth,
            weekend: cell.day != null && isWeekend(cell.day),
            today: cell.day != null && isToday(cell.day),
          }"
        >
          <template v-if="cell.inMonth && cell.day != null">
            <div class="cell-head">
              <span class="cell-date">{{ formatYmd(cell.day) }}</span>
              <span v-if="isToday(cell.day)" class="day-today-badge">{{ t('今天') }}</span>
              <span v-if="itemsOnDay(cell.day).length" class="cell-count">{{
                itemsOnDay(cell.day).length
              }}</span>
            </div>
            <div class="cell-body">
              <button
                v-for="item in visibleItems(cell.day)"
                :key="item.id"
                type="button"
                class="event-chip"
                :class="STATUS_META[item.status]?.cls"
                :title="item.label"
                @click="onSelect(item)"
              >
                <span class="material-symbols-outlined chip-ico">{{ areaIcon(item.area) }}</span>
                <span class="chip-text">{{ item.label }}</span>
              </button>
              <button
                v-if="overflowCount(cell.day)"
                type="button"
                class="event-more"
                @click="onSelect(itemsOnDay(cell.day)[MAX_EVENTS_PER_DAY])"
              >
                +{{ overflowCount(cell.day) }} {{ t('项') }}
              </button>
              <p v-if="!itemsOnDay(cell.day).length" class="cell-empty">—</p>
            </div>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.msc {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 14px;
  overflow: hidden;
}
.msc-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px 18px;
  border-bottom: 1px solid var(--outline-variant);
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--primary) 4%, var(--surface-container-lowest)) 0%,
    var(--surface-container-lowest) 100%
  );
}
.msc-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--on-surface);
}
.msc-title .material-symbols-outlined {
  font-size: 20px;
  color: var(--primary);
}

.month-nav {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  background: var(--surface-container-low);
  color: var(--on-surface);
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s;
}
.nav-btn:hover {
  background: var(--surface-container);
  border-color: var(--primary);
  color: var(--primary);
}
.nav-btn .material-symbols-outlined {
  font-size: 20px;
}

.month-pick {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 0 10px 0 12px;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  background: var(--surface-container-lowest);
  cursor: pointer;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.month-pick:hover {
  border-color: var(--primary);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--primary) 18%, transparent);
}
.month-pick-label {
  font-size: 14px;
  font-weight: 700;
  color: var(--on-surface);
  white-space: nowrap;
}
.month-pick-ico {
  font-size: 18px !important;
  color: var(--primary);
}
.month-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  width: 100%;
  height: 100%;
}

.nav-today {
  border: none;
  background: none;
  color: var(--primary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
}
.nav-today:hover {
  background: color-mix(in srgb, var(--primary) 10%, transparent);
}

.msc-stats {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.msc-stat strong {
  font-size: 15px;
  color: var(--on-surface);
  margin-right: 2px;
}
.msc-stat.warn strong {
  color: #c77700;
}
.msc-stat.err strong {
  color: var(--error);
}

.msc-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  padding: 10px 18px;
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
  font-size: 12px;
  color: var(--on-surface-variant);
}
.msc-leg {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.leg-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  display: inline-block;
}
.leg-dot.st-scheduled {
  background: var(--primary);
}
.leg-dot.st-repairing {
  background: #0d9488;
}
.leg-dot.st-overdue {
  background: var(--error);
}
.leg-dot.st-completed {
  background: #64748b;
}
.leg-dot.st-ai {
  background: var(--tertiary);
}

.msc-empty {
  padding: 40px 24px;
  text-align: center;
  font-size: 13px;
  color: var(--on-surface-variant);
}

.month-wrap {
  padding: 12px 16px 16px;
  overflow-x: auto;
}

.month-head-row {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 6px;
  min-width: 720px;
}
.month-wd {
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface-variant);
  padding: 6px 4px;
}

.month-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 6px;
  min-width: 720px;
}

.month-cell {
  min-height: 108px;
  border: 1px solid var(--outline-variant);
  border-radius: 10px;
  background: var(--surface-container-lowest);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.month-cell.pad {
  min-height: 108px;
  background: transparent;
  border-color: transparent;
  pointer-events: none;
}
.month-cell.weekend:not(.today) {
  background: color-mix(
    in srgb,
    var(--surface-container-high) 35%,
    var(--surface-container-lowest)
  );
}
.month-cell.today {
  border-color: var(--primary);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--primary) 22%, transparent);
}

.cell-head {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  padding: 6px 8px;
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
}
.month-cell.today .cell-head {
  background: color-mix(in srgb, var(--primary) 10%, var(--surface-container-low));
}
.cell-date {
  font-size: 11px;
  font-weight: 700;
  color: var(--on-surface);
  line-height: 1.3;
}
.month-cell.today .cell-date {
  color: var(--primary);
}
.day-today-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--primary);
  color: #fff;
}
.cell-count {
  margin-left: auto;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--primary-container);
  color: var(--on-primary-container);
}

.cell-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  min-height: 0;
}
.cell-empty {
  margin: auto;
  font-size: 11px;
  color: var(--on-surface-variant);
  opacity: 0.5;
}

.event-chip {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  text-align: left;
  border-radius: 6px;
  border: 1px solid var(--outline-variant);
  border-left-width: 3px;
  padding: 4px 6px;
  background: var(--surface-container-lowest);
  cursor: pointer;
  transition: box-shadow 0.12s ease;
}
.event-chip:hover {
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}
.chip-ico {
  font-size: 13px !important;
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--on-surface-variant);
}
.chip-text {
  font-size: 10px;
  font-weight: 600;
  color: var(--on-surface);
  line-height: 1.35;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.event-more {
  border: none;
  background: none;
  color: var(--primary);
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
  padding: 2px 4px;
  text-align: left;
}
.event-more:hover {
  text-decoration: underline;
}

.st-scheduled {
  border-left-color: var(--primary);
}
.st-repairing {
  border-left-color: #0d9488;
}
.st-overdue {
  border-left-color: var(--error);
}
.st-completed {
  border-left-color: #94a3b8;
  opacity: 0.85;
}
.st-ai {
  border-left-color: var(--tertiary);
}
</style>
