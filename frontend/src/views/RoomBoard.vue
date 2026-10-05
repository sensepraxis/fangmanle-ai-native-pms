<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { STATUS_CN, toast, roomFloorLabel } from '../lib/ui'
import RoomOpsNav from '../components/RoomOpsNav.vue'
import RoomBoardDrawer from '../components/RoomBoardDrawer.vue'
import { canBoardAction, resolveBoardRole, type BoardRole } from '../lib/roomBoardPerms'

const router = useRouter()
const rooms = ref<any[]>([])
const oversell = ref<any>(null)

function oversellSummary(ov: any) {
  if (!ov) return ''
  const n = 7
  const count = Array.isArray(ov.alerts) ? ov.alerts.length : 0
  if (ov.has_alert || count) return t('近 {n} 日超售预警 {count} 条', { n, count })
  return (
    t(String(ov.summary || '近 {n} 日房量充足').replace(/\d+/, '{n}'), { n }) ||
    t('近 {n} 日房量充足', { n })
  )
}

function oversellAlertMsg(a: any) {
  if (a?.date != null && a?.demand != null && a?.physical_sellable != null) {
    return t('{date} {room} 超售风险：预订 {demand} > 可售物理 {sellable}', {
      date: a.date,
      room: a.room_type_name || '',
      demand: a.demand,
      sellable: a.physical_sellable,
    })
  }
  return a?.message || ''
}

const arriveN = ref(0)
const departN = ref(0)
const projected = ref(false)
const drawerOpen = ref(false)
const drawerRoom = ref<any | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const boardRole = computed<BoardRole>(() => resolveBoardRole(hotelStore.user?.role))
function perm(action: Parameters<typeof canBoardAction>[1]) {
  return canBoardAction(boardRole.value, action)
}

function ymd(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
function addDays(base: Date, n: number) {
  const d = new Date(base.getFullYear(), base.getMonth(), base.getDate())
  d.setDate(d.getDate() + n)
  return d
}
function parseYmd(s: string) {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}
function fmtCn(s: string) {
  const d = parseYmd(s)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

const todayStr = ymd(new Date())
const maxDateStr = ymd(addDays(new Date(), 90))
const viewDate = ref(todayStr)
const isToday = computed(() => viewDate.value === todayStr)
const viewDateLabel = computed(() => fmtCn(viewDate.value))
const canMutate = computed(() => isToday.value && !projected.value)

// 标准房态色（强化区分）+ 兼容旧值
const STATUS_COLOR: Record<string, string> = {
  VC: '#0d7a3f',
  VD: '#e65100',
  OCC: '#1565c0',
  EA: '#42a5f5',
  DO: '#7b1fa2',
  OOO: '#616161',
  BLK: '#757575',
  vacant: '#0d7a3f',
  clean: '#0d7a3f',
  occupied: '#1565c0',
  dirty: '#e65100',
  cleaning: '#e65100',
  maintenance: '#616161',
  ooo: '#616161',
}
/** 卡片浅底：一眼区分房态 */
const STATUS_BG: Record<string, string> = {
  VC: '#e8f5e9',
  VD: '#fff3e0',
  OCC: '#e3f2fd',
  EA: '#e1f5fe',
  DO: '#f3e5f5',
  OOO: '#eeeeee',
  BLK: '#f5f5f5',
  vacant: '#e8f5e9',
  clean: '#e8f5e9',
  occupied: '#e3f2fd',
  dirty: '#fff3e0',
  cleaning: '#fff3e0',
  maintenance: '#eeeeee',
  ooo: '#eeeeee',
}
const STATUS_BORDER: Record<string, string> = {
  VC: '#66bb6a',
  VD: '#ff9800',
  OCC: '#42a5f5',
  EA: '#4fc3f7',
  DO: '#ab47bc',
  OOO: '#9e9e9e',
  BLK: '#bdbdbd',
  vacant: '#66bb6a',
  clean: '#66bb6a',
  occupied: '#42a5f5',
  dirty: '#ff9800',
  cleaning: '#ff9800',
  maintenance: '#9e9e9e',
  ooo: '#9e9e9e',
}
function cardTone(status: string) {
  return {
    background: STATUS_BG[status] || '#fafafa',
    borderColor: STATUS_BORDER[status] || 'var(--outline-variant)',
  }
}
const STATUS_META: Record<string, { label: string; chipKey: string }> = {
  VC: { label: '空净房', chipKey: 'clean' },
  VD: { label: '空脏房', chipKey: 'dirty' },
  OCC: { label: '已入住房', chipKey: 'occ' },
  EA: { label: '预抵房', chipKey: 'ea' },
  DO: { label: '预离房', chipKey: 'do' },
  OOO: { label: '维修房', chipKey: 'maint' },
  BLK: { label: '锁房', chipKey: 'maint' },
  vacant: { label: '空净房', chipKey: 'clean' },
  clean: { label: '空净房', chipKey: 'clean' },
  occupied: { label: '已入住房', chipKey: 'occ' },
  dirty: { label: '空脏房', chipKey: 'dirty' },
  cleaning: { label: '空脏房', chipKey: 'dirty' },
  maintenance: { label: '维修房', chipKey: 'maint' },
  ooo: { label: '维修房', chipKey: 'maint' },
}
const FLOOR_FILTER = [
  { k: 'all', label: '全部', color: 'var(--primary)' },
  { k: 'clean', label: '空净房', color: '#0d7a3f' },
  { k: 'dirty', label: '空脏房', color: '#e65100' },
  { k: 'occ', label: '已入住房', color: '#1565c0' },
  { k: 'ea', label: '预抵房', color: '#42a5f5' },
  { k: 'do', label: '预离房', color: '#7b1fa2' },
  { k: 'maint', label: '维修/锁房', color: '#616161' },
]
const filter = ref('all')
const floorView = ref<'all' | string>('all') // 'all' 或单个楼层如 '3F'

function clearPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}
function startPollIfToday() {
  clearPoll()
  if (isToday.value) pollTimer = setInterval(load, 3000)
}

async function load() {
  const hid = hotelStore.hotelId
  try {
    const [rm, ov] = await Promise.all([
      api.listRooms(hid, isToday.value ? undefined : viewDate.value),
      isToday.value ? api.roomsOversell(hid, 7).catch(() => null) : Promise.resolve(null),
    ])
    rooms.value = rm || []
    oversell.value = ov
    projected.value = !isToday.value || !!(rooms.value[0] && rooms.value[0].projected)
    arriveN.value = rooms.value.filter((r) => r.status === 'EA').length
    departN.value = rooms.value.filter((r) => r.status === 'DO').length
  } catch (e: any) {
    toast(e?.message || t('加载房态失败'), false)
  }
}

function setViewDate(iso: string) {
  if (!iso) return
  if (iso < todayStr) {
    toast(t('仅支持今日及未来房态'), false)
    return
  }
  if (iso > maxDateStr) {
    toast(t('仅支持查看未来 90 天内房态'), false)
    return
  }
  viewDate.value = iso
}

function jumpToday() {
  setViewDate(todayStr)
}

function onDateInput(e: Event) {
  setViewDate((e.target as HTMLInputElement).value)
}

onMounted(() => {
  load()
  startPollIfToday()
})
onUnmounted(() => {
  clearPoll()
})
watch(
  () => hotelStore.hotelId,
  () => {
    floorView.value = 'all'
    viewDate.value = todayStr
    load()
    startPollIfToday()
  },
)
watch(viewDate, () => {
  load()
  startPollIfToday()
})

function floorOf(r: any) {
  return roomFloorLabel(r)
}
const byFloor = computed(() => {
  // 按楼层分
  const fmap: Record<string, any[]> = {}
  for (const r of rooms.value) {
    const f = floorOf(r)
    if (!fmap[f]) fmap[f] = []
    fmap[f].push(r)
  }
  return Object.entries(fmap).sort(([a], [b]) => Number(a) - Number(b))
})

// 楼层 tab + 全部楼层
const FLOORS = computed(() => {
  return byFloor.value.map(([f, list]) => ({ f, count: list.length }))
})
/** 多楼层才显示楼层 Tab；单层酒店不打扰前台 */
const showFloorTabs = computed(() => FLOORS.value.length > 1)

watch(FLOORS, (floors) => {
  // 切酒店或数据变化后：单层无需筛选；若当前选中楼层已不存在则回到全部
  if (floors.length <= 1) {
    floorView.value = 'all'
    return
  }
  if (floorView.value !== 'all' && !floors.some((f) => f.f === floorView.value)) {
    floorView.value = 'all'
  }
})

const filtered = computed(() => {
  let rs = rooms.value
  if (filter.value === 'clean') rs = rs.filter((r) => ['VC', 'vacant', 'clean'].includes(r.status))
  else if (filter.value === 'dirty')
    rs = rs.filter((r) => ['VD', 'dirty', 'cleaning'].includes(r.status))
  else if (filter.value === 'occ') rs = rs.filter((r) => ['OCC', 'occupied'].includes(r.status))
  else if (filter.value === 'ea') rs = rs.filter((r) => r.status === 'EA')
  else if (filter.value === 'do') rs = rs.filter((r) => r.status === 'DO')
  else if (filter.value === 'maint')
    rs = rs.filter((r) => ['OOO', 'BLK', 'maintenance', 'ooo'].includes(r.status))
  // 楼层过滤
  const map: Record<string, any[]> = {}
  for (const r of rs) {
    const f = floorOf(r)
    if (floorView.value !== 'all' && f !== floorView.value) continue
    if (!map[f]) map[f] = []
    map[f].push(r)
  }
  return Object.entries(map).sort(([a], [b]) => Number(a) - Number(b))
})

const counts = computed(() => {
  const c: any = { all: rooms.value.length, clean: 0, dirty: 0, occ: 0, ea: 0, do: 0, maint: 0 }
  rooms.value.forEach((r) => {
    const m = STATUS_META[r.status]
    if (!m) return
    c[m.chipKey] = (c[m.chipKey] || 0) + 1
  })
  return c
})

async function changeStatus(r: any, next: string) {
  if (!canMutate.value) {
    toast(t('规划日仅供查看，请切回今日再变更房态'), false)
    return
  }
  try {
    let note: string | undefined
    if (next === 'OOO') note = window.prompt(t('维修原因'), '设备故障') || '设置维修房'
    if (next === 'BLK') note = window.prompt(t('锁房原因'), '预留升级') || '锁房'
    await api.setRoomStatus(r.id, next, note || '前端快速变房态')
    toast(t('房间 {no} → {st}', { no: r.room_no, st: STATUS_CN[next] || next }))
    await load()
  } catch (e: any) {
    toast(e?.message || t('变更失败'), false)
  }
}
function openRoom(r: any) {
  drawerRoom.value = r
  drawerOpen.value = true
}
function closeDrawer() {
  drawerOpen.value = false
}
function onDrawerRefresh() {
  load()
}
// 取首字母作为头像
function avatar(n: string) {
  const s = (n || '').trim()
  return s ? s[0] : '客'
}
function statusLabel(s: string) {
  const raw = STATUS_CN[s] || STATUS_META[s]?.label || s
  return t(raw)
}
function floorLabel(floor: string) {
  return floor.endsWith('F') ? `${floor.slice(0, -1)}${t('楼')}` : floor
}
/** 维修/锁房等弹窗原因（及预计恢复日） */
function noteOf(r: any) {
  const note = String(r?.status_note || '').trim()
  if (!note) return ''
  const until = r?.status_until
  return until ? `${note} · 预计 ${until}` : note
}
</script>

<template>
  <div class="page">
    <RoomOpsNav />
    <div
      class="page-head"
      style="
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        flex-wrap: wrap;
        gap: 12px;
      "
    >
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background">{{ t('房态看板') }}</h1>
      </div>
    </div>

    <!-- 日期选择：今日 + 日期选择器 -->
    <div class="date-bar">
      <div class="date-bar-left">
        <span class="date-bar-label">{{ t('入住日') }}</span>
        <button type="button" class="date-chip" :class="{ active: isToday }" @click="jumpToday">
          {{ t('今日') }}
        </button>
        <input
          class="date-input"
          type="date"
          :value="viewDate"
          :min="todayStr"
          :max="maxDateStr"
          @change="onDateInput"
        />
        <span class="date-mode">{{ isToday ? t('实时房态') : `规划 · ${viewDateLabel}` }}</span>
      </div>
    </div>

    <!-- 楼层 Tab：贴标题下方；仅多楼层酒店显示 -->
    <div v-if="showFloorTabs" class="floor-tabs" role="tablist" :aria-label="t('楼层筛选')">
      <button
        type="button"
        role="tab"
        class="floor-tab"
        :class="{ active: floorView === 'all' }"
        :aria-selected="floorView === 'all'"
        @click="floorView = 'all'"
      >
        {{ t('全部') }} <span class="floor-tab-count">{{ rooms.length }}</span>
      </button>
      <button
        v-for="f in FLOORS"
        :key="f.f"
        type="button"
        role="tab"
        class="floor-tab"
        :class="{ active: floorView === f.f }"
        :aria-selected="floorView === f.f"
        @click="floorView = f.f"
      >
        {{ floorLabel(f.f) }}
        <span class="floor-tab-count">{{ f.count }}</span>
      </button>
    </div>

    <div
      v-if="oversell?.has_alert"
      class="card-clean"
      style="
        margin-bottom: 12px;
        padding: 12px 16px;
        border-left: 4px solid #ba1a1a;
        background: #fff5f4;
        display: flex;
        flex-direction: column;
        gap: 6px;
      "
    >
      <strong style="color: #ba1a1a">{{ t('超售 / 房量不足预警') }}</strong>
      <div style="font-size: 13px; color: var(--on-surface-variant)">
        {{ oversellSummary(oversell) }}
      </div>
      <div
        v-for="(a, i) in (oversell.alerts || []).slice(0, 3)"
        :key="i"
        style="font-size: 12px; color: #ba1a1a"
      >
        · {{ oversellAlertMsg(a) }}
      </div>
    </div>

    <!-- 工具栏：状态 chip + AI 提示 toggle -->
    <div
      class="card-clean"
      style="
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 12px 16px;
        flex-wrap: wrap;
      "
    >
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
        <button
          v-for="s in FLOOR_FILTER"
          :key="s.k"
          class="chip-pill"
          :class="{ active: filter === s.k }"
          @click="filter = s.k"
        >
          <span class="dot" :style="{ background: s.color }"></span>
          {{ t(s.label) }} ({{ counts[s.k] || 0 }})
        </button>
      </div>

      <button class="icon-btn" :title="t('刷新')" @click="load">
        <span class="ms">refresh</span>
      </button>
    </div>

    <!-- 房态网格（按楼层；单层或已选单层时不重复显示楼层标题） -->
    <template v-for="[floor, list] in filtered" :key="floor">
      <div
        v-if="showFloorTabs && floorView === 'all'"
        style="
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin: 16px 0 8px;
        "
      >
        <h3 style="font-size: 16px; font-weight: 600; color: var(--on-surface); margin: 0">
          {{ floorLabel(floor) }} ({{ list.length }})
        </h3>
      </div>
      <div
        class="card-grid"
        :style="showFloorTabs && floorView === 'all' ? undefined : { marginTop: '4px' }"
      >
        <div
          v-for="r in list"
          :key="r.id"
          class="room-card"
          :style="cardTone(r.status)"
          @click="openRoom(r)"
        >
          <!-- 顶部状态色条 -->
          <div
            class="room-card-strip"
            :style="{ background: STATUS_COLOR[r.status] || '#888' }"
          ></div>
          <!-- 房号 + 床型 chip -->
          <div
            style="
              display: flex;
              justify-content: space-between;
              align-items: flex-start;
              margin: 6px 0 12px;
            "
          >
            <div
              style="
                font:
                  500 22px 'Roboto Mono',
                  monospace;
                color: var(--on-surface);
                line-height: 1;
              "
            >
              {{ r.room_no }}
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px; align-items: flex-end">
              <span class="room-type-chip"> {{ r.room_type_name || t('标准') }}</span>
            </div>
          </div>
          <!-- 在住客人 / 空置占位 -->
          <div v-if="['OCC', 'occupied', 'DO'].includes(r.status)" class="room-guest">
            <div class="avatar">{{ avatar(r.guest_name || t('客')) }}</div>
            <div style="flex: 1; min-width: 0">
              <div
                style="
                  font-size: 13px;
                  font-weight: 500;
                  color: var(--on-surface);
                  white-space: nowrap;
                  overflow: hidden;
                  text-overflow: ellipsis;
                "
              >
                {{ r.guest_name || t('在住客人') }}
              </div>
              <div style="font-size: 11px; color: var(--on-surface-variant)">
                {{ r.check_out ? `退房：${r.check_out}` : t('退房：待确认') }}
              </div>
            </div>
          </div>
          <div v-else class="room-empty">
            <span class="ms">single_bed</span>
            <span>{{
              ['VC', 'vacant', 'clean', 'VD', 'dirty', 'cleaning'].includes(r.status)
                ? t('空置')
                : statusLabel(r.status)
            }}</span>
          </div>
          <div v-if="noteOf(r)" class="room-note" :title="noteOf(r)">
            <span class="ms">sticky_note_2</span>
            <span>{{ noteOf(r) }}</span>
          </div>
          <!-- 状态行：按角色显示快捷操作 -->
          <div class="room-foot">
            <span
              class="room-status-badge"
              :style="{
                color: STATUS_COLOR[r.status] || 'var(--on-surface-variant)',
                background: 'rgba(255,255,255,0.7)',
                borderColor: STATUS_BORDER[r.status] || 'var(--outline-variant)',
              }"
            >
              {{ statusLabel(r.status) }}</span
            >
            <span
              v-if="canMutate"
              style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap"
              @click.stop
            >
              <!-- 前台 / 店长 -->
              <button
                v-if="perm('checkin') && ['VC', 'vacant', 'clean', 'EA'].includes(r.status)"
                class="rb-act primary"
                @click="openRoom(r)"
              >
                {{ t('入住') }}
              </button>
              <button
                v-if="perm('book') && ['VC', 'vacant', 'clean'].includes(r.status)"
                class="rb-act"
                @click="openRoom(r)"
              >
                {{ t('预订') }}
              </button>
              <button
                v-if="perm('checkout') && ['OCC', 'occupied', 'DO'].includes(r.status)"
                class="rb-act primary"
                @click="openRoom(r)"
              >
                {{ t('退房') }}
              </button>
              <button
                v-if="perm('viewOrder') && r.order_id"
                class="rb-act"
                @click="router.push(`/orders/${r.order_id}`)"
              >
                {{ t('订单') }}
              </button>
              <button
                v-if="perm('extend') && r.status === 'DO'"
                class="rb-act"
                @click="changeStatus(r, 'OCC')"
              >
                {{ t('续住') }}
              </button>
              <!-- 房务 / 保洁 -->
              <button
                v-if="perm('hkTake') && ['VD', 'dirty', 'cleaning'].includes(r.status)"
                class="rb-act primary"
                @click="router.push('/c6-housekeeping/dispatch')"
              >
                {{ t('接单') }}
              </button>
              <button
                v-if="perm('hkDone') && ['VD', 'dirty', 'cleaning'].includes(r.status)"
                class="rb-act"
                @click="changeStatus(r, 'VC')"
              >
                {{ t('打扫完成') }}
              </button>
              <!-- 店长：锁房 / 维修 / 标脏 -->
              <button
                v-if="perm('dirty') && ['VC', 'vacant', 'clean'].includes(r.status)"
                class="rb-act"
                @click="changeStatus(r, 'VD')"
              >
                {{ t('标脏') }}
              </button>
              <button
                v-if="perm('ooo') && ['VC', 'vacant', 'clean', 'VD', 'dirty'].includes(r.status)"
                class="rb-act"
                @click="changeStatus(r, 'OOO')"
              >
                {{ t('维修') }}
              </button>
              <button
                v-if="perm('lock') && ['VC', 'vacant', 'clean'].includes(r.status)"
                class="rb-act"
                @click="changeStatus(r, 'BLK')"
              >
                {{ t('锁房') }}
              </button>
              <button
                v-if="perm('clearOoo') && r.status === 'OOO'"
                class="rb-act primary"
                @click="changeStatus(r, 'VC')"
              >
                {{ t('解除维修') }}
              </button>
              <button
                v-if="perm('clearLock') && r.status === 'BLK'"
                class="rb-act primary"
                @click="changeStatus(r, 'VC')"
              >
                {{ t('解锁') }}
              </button>
            </span>
            <span v-else class="plan-hint">{{ t('规划只读') }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- 底部图例条 -->
    <div
      class="card-clean"
      style="
        margin-top: 24px;
        padding: 12px 20px;
        display: flex;
        align-items: center;
        gap: 24px;
        flex-wrap: wrap;
        position: sticky;
        bottom: 0;
      "
    >
      <span style="font-size: 12px; font-weight: 600; color: var(--on-surface-variant)">{{
        t('图例')
      }}</span>
      <span class="legend-item">
        <span class="legend-swatch" style="background: #e8f5e9; border-color: #66bb6a"></span
        >{{ t('空净房') }}</span
      >
      <span class="legend-item">
        <span class="legend-swatch" style="background: #fff3e0; border-color: #ff9800"></span
        >{{ t('空脏房') }}</span
      >
      <span class="legend-item">
        <span class="legend-swatch" style="background: #e3f2fd; border-color: #42a5f5"></span
        >{{ t('已入住房') }}</span
      >
      <span class="legend-item">
        <span class="legend-swatch" style="background: #e1f5fe; border-color: #4fc3f7"></span
        >{{ t('预抵房') }}</span
      >
      <span class="legend-item">
        <span class="legend-swatch" style="background: #f3e5f5; border-color: #ab47bc"></span
        >{{ t('预离房') }}</span
      >
      <span class="legend-item">
        <span class="legend-swatch" style="background: #eeeeee; border-color: #9e9e9e"></span
        >{{ t('维修房') }}</span
      >
      <span class="legend-item">
        <span class="legend-swatch" style="background: #f5f5f5; border-color: #bdbdbd"></span
        >{{ t('锁房') }}</span
      >
    </div>

    <RoomBoardDrawer
      :open="drawerOpen"
      :room="drawerRoom"
      :can-mutate="canMutate"
      @close="closeDrawer"
      @refreshed="onDrawerRefresh"
    />
  </div>
</template>

<style scoped>
.date-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 0 0 14px;
  padding: 10px 12px;
  background: var(--surface-container-low);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
}
.date-bar-left {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.date-bar-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--on-surface-variant);
}
.date-chip {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  background: var(--surface);
  font-size: 12px;
  font-weight: 600;
  color: var(--on-surface-variant);
  cursor: pointer;
}
.date-chip.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}
.date-input {
  padding: 5px 8px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  background: var(--surface);
  font-size: 13px;
  color: var(--on-surface);
}
.date-mode {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-left: 4px;
}
.plan-hint {
  font-size: 11px;
  color: var(--on-surface-variant);
  opacity: 0.85;
}
.floor-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 14px;
  padding: 4px;
  background: var(--surface-container-low);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  width: fit-content;
  max-width: 100%;
}
.floor-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--on-surface-variant);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 0.15s,
    color 0.15s;
}
.floor-tab:hover {
  background: var(--surface);
  color: var(--on-surface);
}
.floor-tab.active {
  background: var(--primary);
  color: #fff;
}
.floor-tab-count {
  font-weight: 500;
  font-size: 12px;
  opacity: 0.85;
}
.floor-tab.active .floor-tab-count {
  opacity: 1;
}
.chip-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid var(--outline-variant);
  background: var(--surface);
  color: var(--on-surface-variant);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.chip-pill:hover {
  background: var(--surface-variant, #e1e3e4);
}
.chip-pill.active {
  background: rgba(0, 91, 191, 0.1);
  border-color: var(--primary);
  color: var(--primary);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.icon-btn {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  background: var(--surface);
  color: var(--on-surface-variant);
  cursor: pointer;
}
.icon-btn:hover {
  background: var(--surface-container-low);
}
.icon-btn .ms {
  font-family: 'Material Symbols Outlined';
  font-size: 18px;
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  margin-bottom: 8px;
}
.room-card {
  background: var(--surface-container-lowest, #fff);
  border: 1.5px solid var(--outline-variant);
  border-radius: 12px;
  padding: 0 16px 12px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition:
    box-shadow 0.18s,
    transform 0.18s,
    border-color 0.18s;
}
.room-card:hover {
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}
.room-card-strip {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
}
.room-type-chip {
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--on-surface-variant);
  font-size: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 999px;
  font-weight: 500;
}
.room-status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid;
  font-weight: 600;
  font-size: 12px;
}
.room-guest {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.55);
  border-radius: 8px;
  margin-bottom: 8px;
}
.room-guest .avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--secondary-container);
  color: var(--on-secondary-container);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}
.room-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 50px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.45);
  border: 1px dashed rgba(0, 0, 0, 0.12);
  border-radius: 8px;
  color: var(--on-surface-variant);
  font-size: 13px;
}
.room-empty .ms {
  font-family: 'Material Symbols Outlined';
  font-size: 16px;
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
.room-note {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 10px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--on-surface);
  font-weight: 500;
}
.room-note .ms {
  font-family: 'Material Symbols Outlined';
  font-size: 15px;
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--on-surface-variant);
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
.room-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  font-size: 12px;
  color: var(--on-surface-variant);
}
.rb-act {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(0, 0, 0, 0.12);
  padding: 2px 8px;
  font-size: 11px;
  border-radius: 6px;
  color: var(--on-surface-variant);
  cursor: pointer;
}
.rb-act.primary {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.legend-swatch {
  width: 16px;
  height: 12px;
  border-radius: 3px;
  border: 1.5px solid;
  display: inline-block;
  flex-shrink: 0;
}
.legend-item .ms {
  font-family: 'Material Symbols Outlined';
  font-size: 14px;
}
</style>
