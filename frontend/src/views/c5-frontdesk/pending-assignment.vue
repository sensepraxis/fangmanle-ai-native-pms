<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 待分房：从订单行「待分房」进入，左侧固定该客人，右侧展示全部房态供点选排房
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast, STATUS_CN, ORDER_ST_CN, roomFloorNum } from '../../lib/ui'
import OrdersFlowNav from '../../components/OrdersFlowNav.vue'

const route = useRoute()
const router = useRouter()
const hotelId = computed(() => hotelStore.hotelId)

const order = ref<any>(null)
const rooms = ref<any[]>([])
const loading = ref(false)
const assigning = ref(false)
const loadError = ref('')

/** 仅排房不入住 */
const assignOnly = ref(true)
const roomFilter = ref<'all' | 'assignable'>('all')
const floorView = ref<'all' | string>('all')
const selectedRoomId = ref<number | null>(null)

const STAT_COLOR: Record<string, string> = {
  vacant: '#1e8e3e',
  clean: '#1e8e3e',
  inspected: '#0d9488',
  dirty: '#d93025',
  cleaning: '#f9ab00',
  occupied: '#1a73e8',
  maintenance: '#f9ab00',
  ooo: '#9aa0a6',
}

const ASSIGNABLE = new Set(['vacant', 'clean', 'inspected'])

const orderId = computed(() => {
  const q = route.query.orderId ?? route.query.order_id
  const n = Number(q)
  return Number.isFinite(n) && n > 0 ? n : 0
})

function isAssignable(r: any) {
  return ASSIGNABLE.has(String(r?.status || ''))
}

function floorKey(r: any) {
  const n = roomFloorNum(r)
  return n > 0 ? t('{n}楼', { n }) : t('其他')
}

function statusLabel(s: string) {
  return STATUS_CN[s] || s || '—'
}

function typeMatch(room: any) {
  if (!order.value || !room) return false
  if (order.value.room_type_id && room.room_type_id) {
    return Number(order.value.room_type_id) === Number(room.room_type_id)
  }
  const ot = String(order.value.room_type_name || '')
  const rt = String(room.room_type_name || '')
  if (!ot || !rt) return true
  return rt.includes(ot.split(/[\s·]/)[0]) || ot.includes(rt.split(/[\s·]/)[0])
}

const selectedRoom = computed(() => rooms.value.find((r) => r.id === selectedRoomId.value) || null)

const vacantCount = computed(() => rooms.value.filter(isAssignable).length)
const matchVacantCount = computed(
  () => rooms.value.filter((r) => isAssignable(r) && typeMatch(r)).length,
)

const floors = computed(() => {
  const set = new Set<string>()
  for (const r of rooms.value) set.add(floorKey(r))
  return ['all', ...Array.from(set).sort((a, b) => a.localeCompare(b, 'zh'))]
})

const roomsByFloor = computed(() => {
  let list = rooms.value.slice()
  if (roomFilter.value === 'assignable') list = list.filter(isAssignable)
  if (floorView.value !== 'all') list = list.filter((r) => floorKey(r) === floorView.value)

  const map = new Map<string, any[]>()
  for (const r of list) {
    const f = floorKey(r)
    if (!map.has(f)) map.set(f, [])
    map.get(f)!.push(r)
  }
  for (const arr of map.values()) {
    arr.sort((a, b) => String(a.room_no).localeCompare(String(b.room_no), 'zh', { numeric: true }))
  }
  return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0], 'zh'))
})

function roomTone(r: any) {
  if (!isAssignable(r)) return 'blocked'
  if (typeMatch(r)) return 'match'
  return 'ok'
}

async function load() {
  loading.value = true
  loadError.value = ''
  order.value = null
  selectedRoomId.value = null

  if (!orderId.value) {
    loadError.value = t('请从订单中心未排房订单的行内「待分房」进入，并指定具体客人。')
    loading.value = false
    rooms.value = await api.listRooms(hotelId.value).catch(() => [])
    return
  }

  try {
    const [o, rs] = await Promise.all([
      api.getOrder(orderId.value),
      api.listRooms(hotelId.value).catch(() => []),
    ])
    order.value = o
    rooms.value = rs || []

    if (o?.stay_room_no || o?.status === 'checked_in') {
      loadError.value = o?.stay_room_no
        ? t('该单已在住（{room}），请在详情办理换房。', { room: o.stay_room_no })
        : t('该单已在住，请在详情办理换房。')
    } else if (o?.pre_room_no && ['pending', 'confirmed'].includes(String(o?.status || ''))) {
      // 允许重新预分，不阻断
      loadError.value = ''
    } else if (!['pending', 'confirmed'].includes(String(o?.status || ''))) {
      loadError.value = t('当前状态「{status}」不可排房。', {
        status: ORDER_ST_CN[o?.status] || o?.status || '',
      })
    }
  } catch (e: any) {
    loadError.value = e?.message || t('加载订单失败')
    rooms.value = []
  } finally {
    loading.value = false
  }
}

function selectRoom(r: any) {
  if (!order.value || order.value.status === 'checked_in' || order.value.stay_room_no) return
  if (!isAssignable(r)) {
    toast(
      r.guest_name
        ? t('在住：{name}', { name: r.guest_name })
        : t('当前不可排（{status}）', { status: statusLabel(r.status) }),
      false,
    )
    return
  }
  selectedRoomId.value = selectedRoomId.value === r.id ? null : r.id
}

const canConfirm = computed(() => {
  if (!order.value || !selectedRoom.value) return false
  if (order.value.stay_room_no || order.value.status === 'checked_in') return false
  if (!['pending', 'confirmed'].includes(String(order.value.status || ''))) return false
  return isAssignable(selectedRoom.value)
})

async function confirmAssign() {
  if (!canConfirm.value || assigning.value) return
  const o = order.value!
  const room = selectedRoom.value!

  if (!typeMatch(room)) {
    if (
      !confirm(
        t('房型不完全匹配：\n客人预订「{booked}」\n房间「{room} · {type}」\n仍要分配？', {
          booked: o.room_type_name || t('未定'),
          room: room.room_no,
          type: room.room_type_name || '',
        }),
      )
    ) {
      return
    }
  } else {
    const action = assignOnly.value ? t('仅预分房（不入住）') : t('入住并分房')
    if (
      !confirm(
        t('确认将「{guest}」{action}到 {room}？', {
          guest: o.guest_name || t('客人'),
          action,
          room: room.room_no,
        }),
      )
    )
      return
  }

  assigning.value = true
  try {
    if (assignOnly.value) {
      await api.assignRoom(o.id, room.id)
      toast(t('已预分至 {room}（未入住）', { room: room.room_no }))
    } else {
      await api.checkin(o.id, room.id)
      toast(t('已入住分房至 {room}', { room: room.room_no }))
    }
    router.push(`/orders/${o.id}`)
  } catch (e: any) {
    toast(e?.message || t('分房失败'), false)
  } finally {
    assigning.value = false
  }
}

function goOrdersUnassigned() {
  router.push({ path: '/orders', query: { view: 'unassigned' } })
}

onMounted(load)
watch([orderId, hotelId], load)
</script>

<template>
  <div class="page assign-page">
    <div class="head">
      <div>
        <button type="button" class="back" @click="router.push('/orders')">
          <span class="material-symbols-outlined">arrow_back</span>
          {{ t('返回订单中心') }}
        </button>
        <h1 class="title">{{ t('待分房') }}</h1>
        <p class="sub">{{ t('为当前预订选择预分房间 · 房号写入预分房，不写入订单主信息') }}</p>
      </div>
      <div class="head-right">
        <OrdersFlowNav mode="fulfill" hide-back />
        <div class="mode-bar">
          <button
            type="button"
            class="mode-btn"
            :class="{ on: assignOnly }"
            @click="assignOnly = true"
          >
            {{ t('仅预分房') }}
          </button>
          <button
            type="button"
            class="mode-btn"
            :class="{ on: !assignOnly }"
            @click="assignOnly = false"
          >
            {{ t('入住并分房') }}
          </button>
        </div>
      </div>
    </div>

    <p v-if="loadError && !order" class="err">
      {{ loadError }}
      <button type="button" class="link" @click="goOrdersUnassigned">
        {{ t('去未排房列表') }}
      </button>
    </p>

    <div class="board">
      <!-- 左侧：仅当前客人 -->
      <aside class="guest-panel">
        <div class="panel-label">{{ t('当前预订') }}</div>
        <div v-if="loading" class="empty">{{ t('加载中…') }}</div>
        <div v-else-if="order" class="guest-card">
          <div class="guest-name">{{ order.guest_name || t('散客') }}</div>
          <div class="guest-row">
            <span>{{ t('订单号') }}</span
            ><b class="mono">{{ order.order_no }}</b>
          </div>
          <div class="guest-row">
            <span>{{ t('预订房型') }}</span
            ><b>{{ order.room_type_name || '—' }}</b>
          </div>
          <div class="guest-row">
            <span>{{ t('入离') }}</span
            ><b>{{ order.check_in }} → {{ order.check_out }}</b>
          </div>
          <div class="guest-row">
            <span>{{ t('晚数') }}</span
            ><b>{{ order.nights || 1 }} {{ t('晚') }}</b>
          </div>
          <div class="guest-row">
            <span>{{ t('渠道') }}</span
            ><b>{{ order.channel_name || '—' }}</b>
          </div>
          <div class="guest-row">
            <span>{{ t('手机') }}</span
            ><b>{{ order.phone || '—' }}</b>
          </div>
          <div class="guest-row">
            <span>{{ t('订单状态') }}</span>
            <b>{{ t(ORDER_ST_CN[order.status] || order.status) }}</b>
          </div>
          <div class="guest-row">
            <span>{{ t('预分房') }}</span>
            <b>{{ order.pre_room_no || t('未排') }}</b>
          </div>
          <p v-if="loadError" class="guest-warn">{{ loadError }}</p>
          <p class="guest-hint">
            {{ t('同房型可排') }} <b>{{ matchVacantCount }}</b> {{ t('间 · 空净') }}{{ t('共') }}
            {{ vacantCount }} / {{ rooms.length }} <br />{{
              t('确认后写入预分房记录，订单主信息不含房间号。')
            }}
          </p>
        </div>
        <div v-else class="empty">{{ t('未指定客人') }}</div>
      </aside>

      <!-- 右侧：全部房态 -->
      <section class="rooms-panel">
        <div class="panel-head">
          <h2>{{ t('全部房态') }}</h2>
          <div class="room-filters">
            <button
              type="button"
              class="chip"
              :class="{ on: roomFilter === 'all' }"
              @click="roomFilter = 'all'"
            >
              {{ t('全部房间') }}
            </button>
            <button
              type="button"
              class="chip"
              :class="{ on: roomFilter === 'assignable' }"
              @click="roomFilter = 'assignable'"
            >
              {{ t('仅可排') }}
            </button>
            <select v-model="floorView" class="floor-select">
              <option value="all">{{ t('全部楼层') }}</option>
              <option v-for="f in floors.filter((x) => x !== 'all')" :key="f" :value="f">
                {{ f }}
              </option>
            </select>
          </div>
        </div>

        <div class="legend">
          <span><i class="lg" style="background: #1e8e3e" />{{ t('空净可排') }}</span>
          <span><i class="lg" style="background: #0d9488" />{{ t('同房型匹配') }}</span>
          <span><i class="lg" style="background: #1a73e8" />{{ t('在住') }}</span>
          <span><i class="lg" style="background: #d93025" />{{ t('脏房') }}</span>
          <span><i class="lg" style="background: #f9ab00" />{{ t('清扫/维修') }}</span>
        </div>

        <div class="floor-blocks">
          <div v-for="[floor, list] in roomsByFloor" :key="floor" class="floor-block">
            <div class="floor-label">{{ floor }} · {{ list.length }} {{ t('间') }}</div>
            <div class="room-grid">
              <button
                v-for="r in list"
                :key="r.id"
                type="button"
                class="room-tile"
                :class="[
                  roomTone(r),
                  { selected: selectedRoomId === r.id, assignable: isAssignable(r) },
                ]"
                :style="{ '--tone': STAT_COLOR[r.status] || '#9aa0a6' }"
                @click="selectRoom(r)"
              >
                <div class="room-no">{{ r.room_no }}</div>
                <div class="room-type">{{ r.room_type_name || '—' }}</div>
                <div class="room-st">
                  <span class="dot-st" />
                  <template v-if="r.guest_name">{{ r.guest_name }}</template>
                  <template v-else>{{ statusLabel(r.status) }}</template>
                </div>
              </button>
            </div>
          </div>
          <div v-if="!roomsByFloor.length && !loading" class="empty">{{ t('暂无房间') }}</div>
        </div>
      </section>
    </div>

    <div v-if="order && selectedRoom" class="confirm-bar">
      <div class="confirm-text">
        {{ t('将') }} <b>{{ order.guest_name || t('客人') }}</b> （{{
          order.room_type_name || t('未定房型')
        }}） →
        <b>{{ selectedRoom.room_no }}</b>
        （{{ selectedRoom.room_type_name }}）
        <span class="muted">· {{ assignOnly ? t('仅预分房') : t('入住并分房') }}</span>
        <span v-if="!typeMatch(selectedRoom)" class="warn">{{ t('房型不一致') }}</span>
      </div>
      <div class="confirm-actions">
        <button type="button" class="btn btn-ghost" @click="selectedRoomId = null">
          {{ t('取消') }}
        </button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="!canConfirm || assigning"
          @click="confirmAssign"
        >
          {{ assigning ? t('处理中…') : assignOnly ? t('确认预分房') : t('确认入住分房') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.assign-page {
  padding-bottom: 88px;
  max-width: 1400px;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: none;
  color: #5b616e;
  font-size: 13px;
  cursor: pointer;
  padding: 0;
  margin-bottom: 8px;
}
.back:hover {
  color: var(--primary, #1a73e8);
}
.back .material-symbols-outlined {
  font-size: 18px;
}
.title {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 700;
}
.sub {
  margin: 0;
  font-size: 13px;
  color: #5b616e;
}
.head-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}
.mode-bar {
  display: flex;
  gap: 6px;
}
.mode-btn {
  border: 1px solid var(--outline-variant, #e2e5eb);
  background: #fff;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
  color: #5b616e;
}
.mode-btn.on {
  border-color: var(--primary, #1a73e8);
  background: color-mix(in srgb, var(--primary, #1a73e8) 10%, white);
  color: var(--primary, #1a73e8);
  font-weight: 600;
}
.err {
  margin: 0 0 12px;
  padding: 10px 12px;
  background: #fef3c7;
  border-radius: 8px;
  font-size: 13px;
  color: #92400e;
}
.link {
  margin-left: 8px;
  border: none;
  background: none;
  color: var(--primary, #1a73e8);
  cursor: pointer;
  font-size: 13px;
  text-decoration: underline;
}

.board {
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
  gap: 14px;
  min-height: 480px;
}
@media (max-width: 900px) {
  .board {
    grid-template-columns: 1fr;
  }
}

.guest-panel,
.rooms-panel {
  background: #fff;
  border: 1px solid var(--outline-variant, #e2e5eb);
  border-radius: 12px;
  overflow: hidden;
}
.panel-label {
  padding: 12px 14px;
  font-size: 14px;
  font-weight: 700;
  border-bottom: 1px solid #eef0f4;
}
.guest-card {
  padding: 16px;
}
.guest-name {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 14px;
}
.guest-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  padding: 6px 0;
  border-bottom: 1px solid #f3f4f6;
}
.guest-row span {
  color: #9aa1ad;
  flex-shrink: 0;
}
.guest-row b {
  font-weight: 600;
  text-align: right;
}
.mono {
  font-family: ui-monospace, monospace;
  font-size: 12px;
}
.guest-warn {
  margin: 12px 0 0;
  padding: 8px 10px;
  background: #fef3c7;
  border-radius: 8px;
  font-size: 12px;
  color: #92400e;
}
.guest-hint {
  margin: 14px 0 0;
  font-size: 12px;
  color: #5b616e;
  line-height: 1.5;
}
.guest-hint b {
  color: var(--primary, #1a73e8);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid #eef0f4;
  flex-wrap: wrap;
}
.panel-head h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}
.room-filters {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.chip {
  border: 1px solid #e2e5eb;
  background: #fff;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  color: #5b616e;
}
.chip.on {
  border-color: var(--primary, #1a73e8);
  color: var(--primary, #1a73e8);
  background: color-mix(in srgb, var(--primary, #1a73e8) 10%, white);
  font-weight: 600;
}
.floor-select {
  border: 1px solid #e2e5eb;
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 12px;
  background: #fff;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  padding: 8px 14px;
  font-size: 11px;
  color: #5b616e;
  border-bottom: 1px solid #eef0f4;
}
.legend .lg {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}
.floor-blocks {
  overflow: auto;
  padding: 12px 14px 16px;
  max-height: calc(100vh - 280px);
}
.floor-block {
  margin-bottom: 16px;
}
.floor-label {
  font-size: 12px;
  font-weight: 700;
  color: #5b616e;
  margin-bottom: 8px;
}
.room-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(108px, 1fr));
  gap: 8px;
}
.room-tile {
  text-align: left;
  border: 1px solid #e2e5eb;
  border-radius: 10px;
  padding: 10px;
  background: #fff;
  cursor: pointer;
  border-top: 3px solid var(--tone, #9aa0a6);
  transition:
    box-shadow 0.15s,
    border-color 0.15s;
}
.room-tile.assignable:hover {
  border-color: var(--primary, #1a73e8);
  box-shadow: 0 2px 8px rgba(26, 115, 232, 0.12);
}
.room-tile.selected {
  border-color: var(--primary, #1a73e8);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary, #1a73e8) 35%, transparent);
}
.room-tile.match:not(.selected) {
  background: #f0fdfa;
  border-color: #0d9488;
}
.room-tile.blocked {
  cursor: default;
  background: #f8f9fb;
  opacity: 0.85;
}
.room-no {
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.room-type {
  font-size: 11px;
  color: #5b616e;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.room-st {
  margin-top: 6px;
  font-size: 11px;
  color: #9aa1ad;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dot-st {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--tone, #9aa0a6);
  flex-shrink: 0;
}
.empty {
  padding: 32px 16px;
  text-align: center;
  color: #9aa1ad;
  font-size: 13px;
}

.confirm-bar {
  position: fixed;
  left: 50%;
  bottom: 20px;
  transform: translateX(-50%);
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  min-width: min(720px, calc(100vw - 48px));
  max-width: calc(100vw - 48px);
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #e2e5eb;
  border-radius: 12px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.14);
}
.confirm-text {
  font-size: 13px;
  line-height: 1.5;
}
.confirm-actions {
  display: flex;
  gap: 8px;
}
.muted {
  color: #9aa1ad;
}
.warn {
  margin-left: 8px;
  color: #b45309;
  font-weight: 600;
  font-size: 12px;
}
</style>
