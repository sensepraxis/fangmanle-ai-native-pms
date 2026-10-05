<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 房态库存 —— 按日展示「已售出 / 还可卖」（数据：rooms + orders + reservations）
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import RoomOpsNav from '../../components/RoomOpsNav.vue'
import OccupancyHeatmap30 from '../../components/OccupancyHeatmap30.vue'

type RoomCell = {
  id: number
  room_no: string
  room_type_name: string
  status?: string
  guest_name?: string | null
  order_no?: string | null
  order_status?: string
  source?: string
  check_in?: string | null
  check_out?: string | null
  reason?: string
}

type DayPanel = {
  date: string
  label: string
  label_short?: string
  weekday: string
  is_today: boolean
  sold_count: number
  available_count: number
  blocked_count: number
  sold: RoomCell[]
  available: RoomCell[]
  blocked: RoomCell[]
}

const days = ref<DayPanel[]>([])
const selectedDate = ref('')
const roomTotal = ref(0)
const note = ref('')
const loadError = ref('')
const unassigned = ref<any[]>([])
const typeFilter = ref('all')
const q = ref('')
const activeTab = ref<'daily' | 'heatmap'>('daily')

const route = useRoute()
const router = useRouter()

function syncTabFromRoute() {
  const t = String(route.query.tab || '')
  activeTab.value = t === 'heatmap' ? 'heatmap' : 'daily'
}

function setTab(tab: 'daily' | 'heatmap') {
  activeTab.value = tab
  router.replace({
    path: '/c5-frontdesk/smart-inventory',
    query: tab === 'heatmap' ? { tab: 'heatmap' } : {},
  })
}

const selected = computed(
  () => days.value.find((d) => d.date === selectedDate.value) || days.value[0] || null,
)

const typeOptions = computed(() => {
  const set = new Set<string>()
  for (const d of days.value) {
    for (const r of [...d.sold, ...d.available, ...d.blocked]) {
      if (r.room_type_name) set.add(r.room_type_name)
    }
  }
  return ['all', ...Array.from(set).sort()]
})

function matchQ(r: RoomCell) {
  const kw = q.value.trim()
  if (!kw) return true
  return (
    String(r.room_no || '').includes(kw) ||
    String(r.room_type_name || '').includes(kw) ||
    String(r.guest_name || '').includes(kw) ||
    String(r.order_no || '').includes(kw)
  )
}

function matchType(r: RoomCell) {
  return typeFilter.value === 'all' || r.room_type_name === typeFilter.value
}

const soldList = computed(() =>
  (selected.value?.sold || []).filter((r) => matchType(r) && matchQ(r)),
)
const availableList = computed(() =>
  (selected.value?.available || []).filter((r) => matchType(r) && matchQ(r)),
)
const blockedList = computed(() =>
  (selected.value?.blocked || []).filter((r) => matchType(r) && matchQ(r)),
)

/** 还可卖：按房型汇总当日剩余库存数 */
const availableByType = computed(() => {
  const map = new Map<string, { room_type_name: string; count: number; rooms: RoomCell[] }>()
  for (const r of availableList.value) {
    const t = r.room_type_name || '客房'
    let bag = map.get(t)
    if (!bag) {
      bag = { room_type_name: t, count: 0, rooms: [] }
      map.set(t, bag)
    }
    bag.count += 1
    bag.rooms.push(r)
  }
  return Array.from(map.values()).sort((a, b) =>
    a.room_type_name.localeCompare(b.room_type_name, 'zh'),
  )
})

const showUnassigned = ref(false)

const summary = computed(() => {
  const d = selected.value
  if (!d) return { sold: 0, available: 0, blocked: 0, occ: 0 }
  const total = Math.max(1, roomTotal.value - d.blocked_count)
  return {
    sold: d.sold_count,
    available: d.available_count,
    blocked: d.blocked_count,
    occ: Math.round((100 * d.sold_count) / total),
  }
})

async function load() {
  loadError.value = ''
  try {
    const data = await api.inventoryCalendar(hotelStore.hotelId, 14)
    days.value = data?.days || []
    roomTotal.value = data?.room_total || 0
    note.value = data?.note || ''
    unassigned.value = data?.unassigned_orders || []
    if (!selectedDate.value || !days.value.some((d) => d.date === selectedDate.value)) {
      selectedDate.value = days.value.find((d) => d.is_today)?.date || days.value[0]?.date || ''
    }
  } catch (e: any) {
    days.value = []
    loadError.value = e?.message || t('库存日历加载失败，请确认已登录')
  }
}

onMounted(() => {
  syncTabFromRoute()
  load()
})
watch(() => hotelStore.hotelId, load)
watch(() => route.query.tab, syncTabFromRoute)

function fmtYmd(v?: string | null) {
  if (!v) return ''
  const s = String(v).slice(0, 10)
  const m = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(s)
  if (!m) return s
  const y = Number(m[1])
  const mo = Number(m[2])
  const d = Number(m[3])
  return t('{y}年{m}月{d}日', { y, m: mo, d })
}

function fmtMd(v?: string | null) {
  if (!v) return '—'
  const s = String(v).slice(0, 10)
  const m = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(s)
  if (!m) return s
  return t('{m}月{d}日', { m: Number(m[2]), d: Number(m[3]) })
}

function dayLabel(d: DayPanel) {
  return fmtYmd(d.date) || d.label
}

function weekdayLabel(d: DayPanel) {
  // 优先用 ISO 推算，避免后端已翻/未翻混用
  const iso = String(d.date || '').slice(0, 10)
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  if (m) {
    const dt = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
    if (!Number.isNaN(dt.getTime())) {
      const keys = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
      return t(keys[dt.getDay() === 0 ? 6 : dt.getDay() - 1])
    }
  }
  return d.weekday ? t(d.weekday) : ''
}

/** 客人姓氏：中文取首字，西文取空格前一段 */
function guestSurname(name?: string | null) {
  const s = String(name || '').trim()
  if (!s) return '—'
  if (/^[A-Za-z]/.test(s)) {
    const first = s.split(/\s+/)[0]
    return first || s[0]
  }
  return s[0]
}
</script>

<template>
  <div class="page inv-page">
    <RoomOpsNav />
    <div class="page-head">
      <div>
        <h1>{{ t('库存预售') }}</h1>
        <p v-if="activeTab === 'heatmap'">
          {{ t('未来 30 天入住压力热力图，辅助库存与排房决策。') }}
        </p>
        <p v-if="loadError && activeTab === 'daily'" class="err">{{ loadError }}</p>
      </div>
    </div>

    <div class="tabs" role="tablist">
      <button
        type="button"
        role="tab"
        class="tab"
        :class="{ on: activeTab === 'daily' }"
        :aria-selected="activeTab === 'daily'"
        @click="setTab('daily')"
      >
        {{ t('按日库存') }}
      </button>
      <button
        type="button"
        role="tab"
        class="tab"
        :class="{ on: activeTab === 'heatmap' }"
        :aria-selected="activeTab === 'heatmap'"
        @click="setTab('heatmap')"
      >
        {{ t('30天热力图') }}
      </button>
    </div>

    <template v-if="activeTab === 'heatmap'">
      <OccupancyHeatmap30 />
    </template>

    <template v-else>
      <!-- 日期条 -->
      <div class="day-strip">
        <button
          v-for="d in days"
          :key="d.date"
          type="button"
          class="day-chip"
          :class="{ on: d.date === selected?.date, today: d.is_today }"
          @click="selectedDate = d.date"
        >
          <span class="dow">{{ weekdayLabel(d) }}</span>
          <span class="dom">{{ dayLabel(d) }}</span>
          <span class="iso">{{ d.label_short || d.date }}</span>
          <span class="mini">
            <b>{{ d.sold_count }}</b
            >{{ t('售 /') }} <em>{{ d.available_count }}</em
            >{{ t('可售') }}</span
          >
        </button>
      </div>

      <!-- KPI -->
      <div v-if="selected" class="kpi-row">
        <div class="kpi sold">
          <div class="kpi-label">{{ t('当日已售') }}</div>
          <div class="kpi-num">
            {{ summary.sold }}<span class="u">{{ t('间') }}</span>
          </div>
        </div>
        <div class="kpi avail">
          <div class="kpi-label">{{ t('当日可售') }}</div>
          <div class="kpi-num">
            {{ summary.available }}<span class="u">{{ t('间') }}</span>
          </div>
        </div>
        <div class="kpi block">
          <div class="kpi-label">{{ t('停用不可售') }}</div>
          <div class="kpi-num">
            {{ summary.blocked }}<span class="u">{{ t('间') }}</span>
          </div>
        </div>
        <div class="kpi occ">
          <div class="kpi-label">{{ t('占用率（相对可售库存）') }}</div>
          <div class="kpi-num">{{ summary.occ }}<span class="u">%</span></div>
        </div>
      </div>

      <!-- 筛选 -->
      <div class="toolbar">
        <div class="types">
          <button
            v-for="tag in typeOptions"
            :key="tag"
            type="button"
            class="chip"
            :class="{ on: typeFilter === tag }"
            @click="typeFilter = tag"
          >
            {{ tag === 'all' ? t('全部房型') : tag }}
          </button>
        </div>
        <input v-model="q" class="search" type="search" :placeholder="t('搜房号 / 客人 / 单号')" />
      </div>

      <!-- 双栏面板 -->
      <div v-if="selected" class="panels">
        <section class="panel panel-sold">
          <header>
            <h2>
              <span class="material-symbols-outlined">event_busy</span>
              {{ dayLabel(selected) }} {{ t('已售出') }}
              <span class="count">{{ soldList.length }}</span>
            </h2>
            <p>{{ t('订单号 · 客人姓氏 · 离店日期') }}</p>
          </header>
          <div class="room-grid">
            <div v-for="r in soldList" :key="'s' + r.id" class="room-chip sold">
              <div class="top">
                <span class="no">{{ r.room_no }}</span>
                <span class="tag">{{ t('已售') }}</span>
              </div>
              <div class="type">{{ r.room_type_name }}</div>
              <div class="meta-line">
                <span class="k">{{ t('单号') }}</span>
                <span class="v mono">{{ r.order_no || '—' }}</span>
              </div>
              <div class="meta-line">
                <span class="k">{{ t('姓氏') }}</span>
                <span class="v">{{ guestSurname(r.guest_name) }}</span>
              </div>
              <div class="meta-line">
                <span class="k">{{ t('离店') }}</span>
                <span class="v">{{ fmtMd(r.check_out) }}</span>
              </div>
            </div>
            <div v-if="!soldList.length" class="empty">{{ t('该日暂无已售房间') }}</div>
          </div>
        </section>

        <section class="panel panel-avail">
          <header>
            <h2>
              <span class="material-symbols-outlined">event_available</span>
              {{ dayLabel(selected) }} {{ t('还可卖') }}
              <span class="count">{{ availableList.length }}</span>
            </h2>
            <p>{{ t('各房型当日剩余可售库存') }}</p>
          </header>
          <div class="type-stock-grid">
            <div v-for="tag in availableByType" :key="tag.room_type_name" class="type-stock-card">
              <div class="ts-name">{{ tag.room_type_name }}</div>
              <div class="ts-count">
                <strong>{{ tag.count }}</strong>
                <span>{{ t('间可售') }}</span>
              </div>
              <div class="ts-rooms" :title="tag.rooms.map((x) => x.room_no).join('、')">
                {{
                  tag.rooms
                    .map((x) => x.room_no)
                    .slice(0, 8)
                    .join('、')
                }}{{ tag.rooms.length > 8 ? '…' : '' }}
              </div>
            </div>
            <div v-if="!availableByType.length" class="empty">{{ t('该日已无可售库存') }}</div>
          </div>

          <div v-if="blockedList.length" class="blocked-block">
            <h3>停用不可售（{{ blockedList.length }}）</h3>
            <div class="room-grid dense">
              <div v-for="r in blockedList" :key="'b' + r.id" class="room-chip blocked">
                <div class="top">
                  <span class="no">{{ r.room_no }}</span>
                  <span class="tag">{{ t('停用') }}</span>
                </div>
                <div class="type">{{ r.room_type_name }}</div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- 未分房预订：默认折叠，避免干扰主视图 -->
      <section v-if="unassigned.length" class="unassigned">
        <button type="button" class="ua-toggle" @click="showUnassigned = !showUnassigned">
          <span class="material-symbols-outlined">{{
            showUnassigned ? 'expand_less' : 'expand_more'
          }}</span>
          <span
            >{{ showUnassigned ? t('收起') : t('展开') }} ·
            {{ t('窗口内未分房预订（{n}）', { n: unassigned.length }) }}</span
          >
        </button>
        <div v-if="showUnassigned" class="ua-body">
          <p>{{ t('这些订单尚未写入分房表；日历里已按房型临时占房展示，方便看库存压力。') }}</p>
          <div class="ua-list">
            <div v-for="o in unassigned.slice(0, 12)" :key="o.order_id" class="ua-item">
              <div class="ua-main">
                <strong>{{ o.order_no }}</strong>
                <span
                  >{{ o.guest_name || t('客人') }} · {{ o.room_type_name }} × {{ o.rooms }}</span
                >
              </div>
              <div class="ua-meta">
                {{ fmtYmd(o.check_in) }} → {{ fmtYmd(o.check_out) }}
                <span v-if="o.assigned_rooms?.length">
                  · 展示占房 {{ o.assigned_rooms.join('、') }}</span
                >
                <span v-else class="warn"> {{ t('· 库存不足未占满') }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.inv-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 12px;
}
.page-head h1 {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 800;
}
.page-head p {
  margin: 0;
  color: var(--on-surface-variant);
  font-size: 13px;
}
.err {
  color: var(--error, #b91c1c) !important;
  margin-top: 6px !important;
}
.hint {
  margin-top: 6px !important;
  font-size: 12px !important;
}

.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--outline-variant, #e2e5eb);
  padding-bottom: 0;
}
.tab {
  border: none;
  background: transparent;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.tab.on {
  color: var(--primary, #1a73e8);
  border-bottom-color: var(--primary, #1a73e8);
}

.day-strip {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.day-chip {
  flex: 0 0 auto;
  min-width: 118px;
  border: 1px solid var(--outline-variant, #c9ced8);
  background: #fff;
  border-radius: 12px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.day-chip.today {
  border-color: var(--primary, #1a73e8);
}
.day-chip.on {
  background: #1f2329;
  border-color: #1f2329;
  color: #fff;
}
.dow {
  font-size: 11px;
  opacity: 0.75;
}
.dom {
  font-size: 13px;
  font-weight: 700;
  line-height: 1.25;
}
.iso {
  font-size: 11px;
  font-family: 'Roboto Mono', ui-monospace, monospace;
  opacity: 0.75;
}
.mini {
  font-size: 11px;
  opacity: 0.85;
}
.mini b {
  font-weight: 700;
}
.mini em {
  font-style: normal;
  color: #146c2e;
}
.day-chip.on .mini em {
  color: #86efac;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
@media (max-width: 900px) {
  .kpi-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.kpi {
  background: #fff;
  border: 1px solid var(--outline-variant, #e2e5eb);
  border-radius: 12px;
  padding: 14px 16px;
}
.kpi-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface-variant);
}
.kpi-num {
  margin-top: 6px;
  font-size: 28px;
  font-weight: 800;
  line-height: 1.1;
}
.kpi-num .u {
  margin-left: 2px;
  font-size: 12px;
  font-weight: 500;
  opacity: 0.8;
}
.kpi.sold .kpi-num {
  color: #1a73e8;
}
.kpi.avail .kpi-num {
  color: #146c2e;
}
.kpi.block .kpi-num {
  color: #5b616e;
}
.kpi.occ .kpi-num {
  color: #8c33b3;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}
.types {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  border: 1px solid var(--outline-variant);
  background: #fff;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
}
.chip.on {
  background: var(--primary, #1a73e8);
  border-color: var(--primary, #1a73e8);
  color: #fff;
  font-weight: 600;
}
.search {
  min-width: 200px;
  border: 1px solid var(--outline-variant);
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 13px;
  outline: none;
}

.panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: start;
}
@media (max-width: 960px) {
  .panels {
    grid-template-columns: 1fr;
  }
}
.panel {
  background: #fff;
  border: 1px solid var(--outline-variant, #e2e5eb);
  border-radius: 12px;
  padding: 16px;
  min-height: 320px;
  max-height: calc(100vh - 280px);
  overflow: auto;
}
.panel header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 8px;
}
.panel header p {
  margin: 4px 0 12px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.count {
  margin-left: 4px;
  font-size: 12px;
  font-weight: 700;
  background: var(--surface-container, #eef0f4);
  border-radius: 999px;
  padding: 2px 8px;
}
.panel-sold {
  border-top: 3px solid #1a73e8;
}
.panel-avail {
  border-top: 3px solid #146c2e;
}

.room-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(128px, 1fr));
  gap: 8px;
}
.room-grid.dense {
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
}
.room-chip {
  border: 1px solid var(--outline-variant, #e2e5eb);
  border-radius: 10px;
  padding: 10px;
  background: var(--surface-container-lowest, #fff);
}
.room-chip.sold {
  background: #e8f0fe;
  border-color: #aecbfa;
}
.room-chip.avail {
  background: #e6f4ea;
  border-color: #a8dab5;
}
.room-chip.blocked {
  background: #f1f3f4;
  border-color: #dadce0;
  opacity: 0.9;
}
.top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
}
.no {
  font-family: 'Roboto Mono', ui-monospace, monospace;
  font-weight: 700;
  font-size: 15px;
}
.tag {
  font-size: 10px;
  font-weight: 700;
  opacity: 0.8;
}
.type {
  margin-top: 4px;
  font-size: 11px;
  color: var(--on-surface-variant);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta-line {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.35;
}
.meta-line .k {
  color: var(--on-surface-variant);
  flex-shrink: 0;
}
.meta-line .v {
  font-weight: 600;
  text-align: right;
  word-break: break-all;
}
.meta-line .mono {
  font-family: 'Roboto Mono', ui-monospace, monospace;
  font-size: 10px;
  font-weight: 600;
}
.empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 28px;
  color: var(--on-surface-variant);
  font-size: 13px;
}

.type-stock-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}
.type-stock-card {
  border: 1px solid #a8dab5;
  background: #e6f4ea;
  border-radius: 12px;
  padding: 14px 12px;
}
.ts-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--on-surface);
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ts-count {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.ts-count strong {
  font-size: 28px;
  font-weight: 800;
  color: #146c2e;
  line-height: 1;
}
.ts-count span {
  font-size: 12px;
  color: var(--on-surface-variant);
  font-weight: 600;
}
.ts-rooms {
  margin-top: 8px;
  font-size: 11px;
  color: var(--on-surface-variant);
  line-height: 1.4;
  word-break: break-all;
}

.blocked-block {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px dashed var(--outline-variant);
}
.blocked-block h3 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 700;
  color: var(--on-surface-variant);
}

.unassigned {
  background: #fff;
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 8px 12px;
}
.ua-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  border: none;
  background: transparent;
  padding: 8px 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  color: var(--on-surface-variant);
  text-align: left;
}
.ua-toggle .material-symbols-outlined {
  font-size: 20px;
}
.ua-toggle:hover {
  color: var(--on-surface);
}
.ua-body {
  padding: 0 4px 8px;
}
.ua-body > p {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.ua-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ua-item {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  background: var(--surface-container-low, #f2f4f5);
  border-radius: 8px;
}
.ua-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 13px;
}
.ua-meta {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.warn {
  color: var(--error, #b91c1c);
}
</style>
