<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 定价日历 —— 严格对齐原型：
 * 上方房型 chips → 销售渠道（净价一致换算）→ 下方 15 列 × 2 行 = 30 天建议价格子
 */
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import ExplainModal from './ExplainModal.vue'
import SuggestDrawer from './SuggestDrawer.vue'
import { channelLabel, localizeKpiHint } from './labels'

const props = defineProps<{ config?: any; compOn?: boolean }>()

const data = ref<any>(null)
/** 默认选首个房型（原型主视图是单房型 30 天） */
const roomFilter = ref('')
const selectedKey = ref('')
const explainOpen = ref(false)
const drawerOpen = ref(false)
const detailLoading = ref(false)
const active = ref<any>(null)
const highlightRecoId = ref<number | null>(null)
const loading = ref(false)
/** 销售渠道：direct=官网直订（净到手锚点）；其它渠道按佣金换算挂价 */
const calChan = ref('direct')

/** 费率查询仍用完整 map；chip 展示仅用 OTA 佣金页同源列表 */
const commissionMap = computed(() => {
  const fromApi = data.value?.commission || {}
  const fromCfg = props.config?.commission || {}
  return { ...fromCfg, ...fromApi }
})

function formatChipPct(rate: number, pctHint?: number) {
  const pct =
    pctHint != null && !Number.isNaN(Number(pctHint))
      ? Math.round(Number(pctHint) * 100) / 100
      : Math.round(Number(rate) * 10000) / 100
  // 去掉多余尾零，但 0 仍显示为 0
  const text = String(pct)
    .replace(/(\.\d*?)0+$/, '$1')
    .replace(/\.$/, '')
  return text
}

const channelChips = computed(() => {
  const list =
    (Array.isArray(data.value?.commission_channels) && data.value.commission_channels.length
      ? data.value.commission_channels
      : null) ||
    (Array.isArray(props.config?.commission_channels) && props.config.commission_channels.length
      ? props.config.commission_channels
      : null) ||
    []

  if (list.length) {
    return list.map((row: any) => {
      const key = String(row.code || '')
      const rate = Number(row.commission_rate ?? commissionMap.value[key] ?? 0)
      const fromCode = channelLabel(key)
      // 已知档案码优先；否则库名当 msgid（如「携程」）再 t()
      const name =
        fromCode !== key && fromCode !== '—' ? fromCode : row.name ? t(String(row.name)) : fromCode
      const pctText = formatChipPct(rate, row.commission_pct)
      return { key, name, rate, label: `${name} ${pctText}%` }
    })
  }

  // 兜底：仅档案主码，避免再摊开订单侧渠道
  const FALLBACK = [
    'direct',
    'ota_ctrip',
    'ota_meituan',
    'ota_fliggy',
    'ota_douyin',
    'ota_tongcheng',
    'ota_elong',
    'jd',
    'member',
    'ota_agoda',
  ]
  const rates = commissionMap.value
  return FALLBACK.filter((k) => k in rates || k === 'direct').map((key) => {
    const rate = Number(rates[key] ?? 0)
    const name = channelLabel(key)
    const pctText = formatChipPct(rate)
    return { key, name, rate, label: `${name} ${pctText}%` }
  })
})

function roundTo(n: number, step = 10) {
  if (!step) return Math.round(n)
  return Math.round(n / step) * step
}

/** 本店在售价 = 净到手锚点；其它渠道挂价 = N / (1 - r) */
function displayPrice(c: any) {
  if (!c) return 0
  const net = Number(c.est_n ?? c.suggested_base ?? c.suggested_price ?? 0)
  const ch = calChan.value
  if (ch === 'direct') return Math.round(Number(c.suggested_price ?? net) || 0)
  const rate = Number(commissionMap.value[ch] ?? 0)
  if (rate <= 0) return Math.round(net)
  return roundTo(net / (1 - rate), 10)
}

function cellTitle(c: any, room: string, d: string) {
  const net = Number(c?.est_n ?? c?.suggested_base ?? c?.suggested_price ?? 0)
  const guest = displayPrice(c)
  const chanName =
    channelChips.value.find((x) => x.key === calChan.value)?.name || channelLabel('direct')
  const netPart = calChan.value === 'direct' ? '' : ` · ${t('净到手')} ¥${Math.round(net)}`
  return t('{date} {room} [{channel}] 挂价 ¥{guest}{net} · 点击确认建议', {
    date: formatMd(d),
    room,
    channel: chanName,
    guest,
    net: netPart,
  })
}

async function load() {
  loading.value = true
  try {
    data.value = await api.paCalendar(hotelStore.hotelId, 30)
    // 数据到达后若未选房型，默认第一个
    if (!roomFilter.value || roomFilter.value === 'all') {
      const first = data.value?.rooms?.[0]?.name
      if (first) roomFilter.value = first
    }
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(
  () => hotelStore.hotelId,
  () => {
    roomFilter.value = ''
    load()
  },
)
watch(channelChips, (chips) => {
  if (!chips.some((c) => c.key === calChan.value)) calChan.value = 'direct'
})

/** 固定 30 天轴：以后端 date_axis 为准；绝不回退成「只有有建议的几天」 */
const dateAxis = computed(() => {
  const axis = (data.value?.date_axis || []) as string[]
  if (axis.length >= 14) return axis.slice(0, 30)
  // 极端兜底：本地生成 30 天，避免再出现只显示 7 天
  const out: string[] = []
  const t = new Date()
  t.setHours(0, 0, 0, 0)
  for (let i = 0; i < 30; i++) {
    const d = new Date(t)
    d.setDate(t.getDate() + i)
    const m = `${d.getMonth() + 1}`.padStart(2, '0')
    const day = `${d.getDate()}`.padStart(2, '0')
    out.push(`${d.getFullYear()}-${m}-${day}`)
  }
  return out
})

const roomMeta = computed(() => {
  const fromApi = data.value?.rooms as { name: string; count: number; short: string }[] | undefined
  if (fromApi?.length) return fromApi
  return []
})

const cellMap = computed(() => {
  const map = new Map<string, any>()
  for (const c of data.value?.cells || []) {
    if (c.channel && c.channel !== 'direct') continue
    const k = `${c.room_type_name}|${c.stay_date}`
    if (!map.has(k)) map.set(k, c)
  }
  return map
})

const isAll = computed(() => roomFilter.value === 'all')

const activeRoomName = computed(() => {
  if (isAll.value) return ''
  return roomFilter.value
})

const kpis = computed(() => data.value?.kpis || {})

const totalChipCount = computed(() => dateAxis.value.length * Math.max(roomMeta.value.length, 1))

const legendItems = computed(() => {
  const evCap = data.value?.params_snapshot?.ev_cap ?? 100
  const capPct = data.value?.params_snapshot?.cap_pct ?? 50
  const items: { icon: string; text: string; bad?: boolean }[] = [
    { icon: '💡', text: t('智能变价建议') },
  ]
  for (const ev of data.value?.events || []) {
    const start = formatMd(ev.start)
    const end = formatMd(ev.end)
    const range = start === end ? start : `${start}-${end}`
    const src =
      ev.type === 'holiday' || ev.icon === '🌕' || ev.icon === '🇳🇱' ? t('内置') : t('运营录入')
    items.push({
      icon: ev.icon || '🎤',
      text: `${ev.name || t('活动')} ${range}（${src}）`,
    })
  }
  items.push({
    icon: '🔴',
    text: t('活动因子硬上限 +{ev}%（日环比 +{cap}% 独立闸门）', { ev: evCap, cap: capPct }),
    bad: true,
  })
  return items
})

const roomTag = computed(() => {
  if (isAll.value) return t('（全部房型 · 每行一房型）')
  return activeRoomName.value ? `（${activeRoomName.value}）` : ''
})

function shortRoom(name: string) {
  const s = String(name || '')
    .replace('套房', '')
    .replace('房', '')
    .replace('套', '')
  return s.slice(0, 2) || '房'
}

function formatMd(iso?: string) {
  if (!iso) return ''
  const p = String(iso).slice(5).split('-')
  if (p.length < 2) return String(iso)
  return `${Number(p[0])}/${Number(p[1])}`
}

/** 原型价：¥420（不带小数） */
function priceLabel(v: any) {
  const n = Math.round(Number(v) || 0)
  return `¥${n}`
}

function cellFor(room: string, stayDate: string) {
  return cellMap.value.get(`${room}|${stayDate}`) || null
}

function cellClass(c: any) {
  if (!c) return 'empty'
  const tags = c.tags || []
  if (tags.includes('holiday') || tags.includes('national')) return 'holiday'
  if (tags.includes('concert') || tags.includes('ai')) return 'event'
  return ''
}

function cellIcon(c: any) {
  if (!c) return ''
  if (c.icons?.length) return c.icons[0]
  const tags = c.tags || []
  if (tags.includes('concert')) return '🎤'
  if (tags.includes('national')) return '🇳🇱'
  if (tags.includes('holiday')) return '🌕'
  if (tags.includes('ai')) return '💡'
  return ''
}

function cellKey(room: string, stayDate: string) {
  return `${room}|${stayDate}`
}

function isSelected(room: string, stayDate: string) {
  return selectedKey.value === cellKey(room, stayDate)
}

function isCap(c: any) {
  return (c?.tags || []).includes('cap') || (c?.tags || []).includes('national')
}

async function openCell(c: any, room: string, stayDate: string) {
  if (!c?.reco_id) {
    toast(t('该日暂无完整建议，可先重新生成'), false)
    return
  }
  selectedKey.value = cellKey(room, stayDate)
  highlightRecoId.value = c.reco_id
  active.value = c
  drawerOpen.value = true
  if (c.detail_lazy || !c.explain_json) {
    detailLoading.value = true
    try {
      const full = await api.paRecoDetail(String(c.reco_id))
      if (highlightRecoId.value === c.reco_id) active.value = { ...c, ...full, detail_lazy: false }
    } catch {
      /* 格子价仍可用 */
    } finally {
      detailLoading.value = false
    }
  }
}

function closeDrawer() {
  drawerOpen.value = false
  active.value = null
  selectedKey.value = ''
  highlightRecoId.value = null
}

function selectRoom(name: string) {
  roomFilter.value = name
}
</script>

<template>
  <div class="cal-page">
    <div v-if="loading && !data" class="loading">{{ t('加载 30 天建议价日历…') }}</div>
    <template v-else-if="data">
      <div class="cal-layout">
        <div class="cal-main">
          <div class="kpi-row">
            <div class="kpi card-clean">
              <div class="label">{{ t('未来 30 天建议价 cell') }}</div>
              <div class="value">{{ kpis.cells || dateAxis.length }}</div>
              <div class="delta">{{ localizeKpiHint(kpis.cells_hint) || t('未来 30 天') }}</div>
            </div>
            <div class="kpi card-clean">
              <div class="label">{{ t('智能变价事件') }}</div>
              <div class="value">{{ kpis.ai_changes || 0 }}</div>
              <div class="delta flat">{{ localizeKpiHint(kpis.ai_hint) || t('待采纳') }}</div>
            </div>
            <div class="kpi card-clean">
              <div class="label">{{ t('活动事件') }}</div>
              <div class="value">{{ kpis.event_count || 0 }}</div>
              <!-- 活动名库数据不翻；无活动时的兜底文案走 t -->
              <div class="delta flat">{{ localizeKpiHint(kpis.event_hint) || t('活动日历') }}</div>
            </div>
            <div class="kpi card-clean">
              <div class="label">{{ t('若全部采纳 · 净收入') }}</div>
              <div class="value up">+¥{{ Math.round(kpis.net_impact || 0).toLocaleString() }}</div>
              <div class="delta up">{{ localizeKpiHint(kpis.net_hint) || '—' }}</div>
            </div>
          </div>

          <div class="card-clean cal-card">
            <div class="card-head">
              <span class="title">{{ t('📆 未来 30 天建议价日历') }}</span>
              <span class="sub">{{ roomTag }} · {{ t('点格') }} → {{ t('右侧确认') }}</span>
              <span class="gap" />
              <div class="room-chips">
                <button
                  type="button"
                  class="chip"
                  :class="{ active: roomFilter === 'all' }"
                  @click="selectRoom('all')"
                >
                  {{ t('全部 ·') }} {{ totalChipCount }} {{ t('条') }}
                </button>
                <button
                  v-for="r in roomMeta"
                  :key="r.name"
                  type="button"
                  class="chip"
                  :class="{ active: roomFilter === r.name }"
                  @click="selectRoom(r.name)"
                >
                  {{ r.name }} · {{ r.count || dateAxis.length }}
                </button>
              </div>
            </div>

            <div class="chan-chips">
              <button
                v-for="ch in channelChips"
                :key="ch.key"
                type="button"
                class="chip"
                :class="{ active: calChan === ch.key }"
                @click="calChan = ch.key"
              >
                {{ ch.label }}
              </button>
            </div>

            <!-- 单房型：严格 15 列 × N 行，每格日期+价 —— 对齐原型主视图 -->
            <div v-if="!isAll && activeRoomName" class="cal-grid">
              <div
                v-for="d in dateAxis"
                :key="d"
                class="cal-cell"
                :class="[
                  cellClass(cellFor(activeRoomName, d)),
                  {
                    selected: isSelected(activeRoomName, d),
                    cap: isCap(cellFor(activeRoomName, d)),
                  },
                ]"
                :title="cellTitle(cellFor(activeRoomName, d), activeRoomName, d)"
                @click="openCell(cellFor(activeRoomName, d), activeRoomName, d)"
              >
                <span v-if="cellIcon(cellFor(activeRoomName, d))" class="tag-event">
                  {{ cellIcon(cellFor(activeRoomName, d)) }}</span
                >
                <div class="date">{{ formatMd(d) }}</div>
                <div
                  class="price"
                  :class="{
                    down:
                      (cellFor(activeRoomName, d)?.delta || 0) < 0 ||
                      (cellFor(activeRoomName, d)?.tags || []).includes('holiday'),
                  }"
                >
                  {{ priceLabel(displayPrice(cellFor(activeRoomName, d))) }}
                </div>
                <div v-if="calChan !== 'direct'" class="net-mini">
                  {{ t('净到手') }} ¥{{
                    Math.round(
                      Number(
                        cellFor(activeRoomName, d)?.est_n ??
                          cellFor(activeRoomName, d)?.suggested_base ??
                          0,
                      ),
                    )
                  }}
                </div>
              </div>
            </div>

            <!-- 全部：每行一房型，左短标签 + 30 格（只显价） -->
            <div v-else class="cal-all">
              <div v-for="room in roomMeta" :key="room.name" class="cal-room-row">
                <div class="row-label">{{ room.short || shortRoom(room.name) }}</div>
                <div class="cal-grid compact">
                  <div
                    v-for="d in dateAxis"
                    :key="d"
                    class="cal-cell"
                    :class="[
                      cellClass(cellFor(room.name, d)),
                      { selected: isSelected(room.name, d), cap: isCap(cellFor(room.name, d)) },
                    ]"
                    :title="cellTitle(cellFor(room.name, d), room.name, d)"
                    @click="openCell(cellFor(room.name, d), room.name, d)"
                  >
                    <span v-if="cellIcon(cellFor(room.name, d))" class="tag-event">
                      {{ cellIcon(cellFor(room.name, d)) }}</span
                    >
                    <div class="price" :class="{ down: (cellFor(room.name, d)?.delta || 0) < 0 }">
                      {{ priceLabel(displayPrice(cellFor(room.name, d))) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="(data.cap_ranges || []).length" class="cap-bar">
              <span v-for="(cr, i) in data.cap_ranges" :key="i" class="cap-pill">
                🔴 {{ formatMd(cr.start) }}–{{ formatMd(cr.end) }} ·
                {{ localizeKpiHint(cr.label || data.uplift_cap_note) || t('合规上限') }}</span
              >
            </div>

            <div class="legend">
              <span v-for="(it, i) in legendItems" :key="i" :class="{ bad: it.bad }">
                {{ it.icon }} <b>{{ it.text.split(' ')[0] }}</b>
                <template v-if="it.text.includes(' ')">
                  {{ it.text.slice(it.text.indexOf(' ') + 1) }}</template
                >
              </span>
            </div>
          </div>
        </div>

        <SuggestDrawer
          :open="drawerOpen || !!active"
          :reco="active"
          :loading="detailLoading"
          :comp-on="!!compOn || !!config?.comp_compare_enabled"
          @close="closeDrawer"
          @done="load"
          @explain="explainOpen = true"
        />
      </div>

      <ExplainModal :open="explainOpen" :reco="active" @close="explainOpen = false" />
    </template>
  </div>
</template>

<style scoped>
.cal-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 14px;
  align-items: start;
}
.cal-main {
  min-width: 0;
}
.loading {
  padding: 40px;
  text-align: center;
  color: var(--on-surface-variant);
  font-size: 13px;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
.kpi {
  padding: 12px 14px;
}
.kpi .label {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.kpi .value {
  font-size: 22px;
  font-weight: 700;
  margin-top: 4px;
}
.kpi .value.up {
  color: #16a34a;
}
.kpi .delta {
  font-size: 11px;
  margin-top: 4px;
  color: #16a34a;
}
.kpi .delta.flat {
  color: var(--on-surface-variant);
}
.cal-card {
  padding: 0 0 14px;
  overflow: hidden;
  margin-bottom: 14px;
}
.card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid #edf1f6;
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
.room-chips {
  display: inline-flex;
  gap: 4px;
  flex-wrap: wrap;
  align-items: center;
}
.chip {
  padding: 3px 10px;
  font-size: 11px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid #e5e7eb;
  color: var(--on-surface-variant);
  cursor: pointer;
  transition: all 0.15s;
}
.chip:hover:not(.active) {
  background: color-mix(in srgb, var(--primary) 8%, #fff);
  color: var(--primary);
}
.chip.active {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
  font-weight: 600;
}
.chan-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 14px 4px;
}
.chan-hint {
  margin: 0 14px 10px;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.net-mini {
  font-size: 9px;
  color: var(--on-surface-variant);
  margin-top: 1px;
  line-height: 1.2;
}
/* 原型核心：固定 15 列，30 天自然折成 2 行 */
.cal-grid {
  display: grid;
  grid-template-columns: repeat(15, minmax(0, 1fr));
  gap: 4px;
  padding: 0 14px;
}
.cal-grid.compact {
  padding: 0;
}
.cal-all {
  padding: 0 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cal-room-row {
  display: grid;
  grid-template-columns: 60px 1fr;
  gap: 0;
  align-items: stretch;
}
.row-label {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 10px;
  font-size: 11px;
  color: var(--on-surface-variant);
  font-weight: 600;
  border-right: 1px solid #edf1f6;
  background: #fafbfc;
}
.cal-cell {
  padding: 8px 4px;
  border: 1px solid #edf1f6;
  border-radius: 4px;
  text-align: center;
  font-size: 11px;
  background: #fff;
  cursor: pointer;
  position: relative;
  min-height: 52px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.cal-cell:hover {
  border-color: var(--primary);
}
.cal-cell.empty {
  opacity: 0.5;
  cursor: default;
}
.cal-cell.event {
  border-color: #7c3aed;
  background: #f3e8ff;
}
.cal-cell.holiday {
  border-color: #dc2626;
  background: #fee2e2;
}
.cal-cell.selected {
  border-color: #7c3aed;
  box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.35);
  z-index: 1;
}
.cal-cell.cap::after {
  content: '';
  position: absolute;
  left: 4px;
  right: 4px;
  bottom: 2px;
  height: 2px;
  background: #dc2626;
  border-radius: 1px;
}
.date {
  font-weight: 600;
  font-size: 11px;
  margin-bottom: 2px;
}
.price {
  font-weight: 700;
  color: var(--primary);
  font-size: 13px;
}
.compact .price {
  font-size: 12px;
}
.price.down {
  color: #dc2626;
}
.tag-event {
  position: absolute;
  top: -6px;
  right: -3px;
  font-size: 9px;
  background: #7c3aed;
  color: #fff;
  padding: 1px 4px;
  border-radius: 3px;
  line-height: 1.2;
}
.cap-bar {
  padding: 8px 14px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.cap-pill {
  font-size: 11px;
  color: #dc2626;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 4px;
  padding: 3px 8px;
}
.legend {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--on-surface-variant);
  padding: 12px 14px 0;
}
.legend .bad {
  color: #dc2626;
}
.up {
  color: #16a34a;
  font-weight: 600;
}
.down {
  color: #dc2626;
  font-weight: 600;
}
@media (max-width: 1100px) {
  .cal-layout {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 900px) {
  .kpi-row {
    grid-template-columns: 1fr 1fr;
  }
  .cal-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
  .cal-room-row {
    grid-template-columns: 1fr;
  }
  .row-label {
    justify-content: flex-start;
    border-right: none;
    padding: 4px 0;
    background: transparent;
  }
}
</style>
