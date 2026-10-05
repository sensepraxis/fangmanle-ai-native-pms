<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import RoomBoardFlowNav from '../../components/RoomBoardFlowNav.vue'

// 数据来源：房间状态网格 → api.listRooms（真实 DB）
const rooms = ref<any[]>([])
const floor = ref<string>('all')
onMounted(async () => {
  rooms.value = await api.listRooms(hotelStore.hotelId)
})
watch(
  () => hotelStore.hotelId,
  async () => {
    rooms.value = await api.listRooms(hotelStore.hotelId)
  },
)

const floors = computed(() => {
  const set = new Set<string>()
  for (const r of rooms.value) {
    if (r.floor != null && r.floor !== 't(') set.add(`${Number(r.floor)}层`)
    else {
      const digits = String(r.room_no || '').replace(/[^0-9]/g, '')
      if (digits.length >= 3) set.add(`${Number(digits.slice(0, 2))}层`)
      else if (digits) set.add(`${Number(digits[0])}层`)
    }
  }
  return Array.from(set).sort((a, b) => parseInt(a, 10) - parseInt(b, 10))
})
const floorCounts = computed(() => {
  const c: Record<string, number> = { all: rooms.value.length }
  for (const r of rooms.value) {
    let f: string
    if (r.floor != null && r.floor !== 't(') f = `${Number(r.floor)}层`
    else {
      const digits = String(r.room_no || '').replace(/[^0-9]/g, '')
      f = `${Number(digits.length >= 3 ? digits.slice(0, 2) : digits[0] || 0)}层`
    }
    c[f] = (c[f] || 0) + 1
  }
  return c
})
const shown = computed(() =>
  floor.value === 'all'
    ? rooms.value
    : rooms.value.filter((r) => {
        let f: string
        if (r.floor != null && r.floor !== 't(') f = `${Number(r.floor)}层`
        else {
          const digits = String(r.room_no || '').replace(/[^0-9]/g, '')
          f = `${Number(digits.length >= 3 ? digits.slice(0, 2) : digits[0] || 0)}层`
        }
        return f === floor.value
      }),
)

// 房态 → 视觉（与原型一致：净房绿 / 脏房橙 / 打扫中蓝 / 维修红）
const ROOM_UI: Record<string, { label: string; strip: string; pill: string; pillBg: string }> = {
  vacant: { label: t('净房'), strip: '#1e8e3e', pill: '#1e8e3e', pillBg: 'rgba(30,142,62,0.1)' },
  clean: { label: t('净房'), strip: '#1e8e3e', pill: '#1e8e3e', pillBg: 'rgba(30,142,62,0.1)' },
  occupied: { label: t('净房'), strip: '#1e8e3e', pill: '#1e8e3e', pillBg: 'rgba(30,142,62,0.1)' },
  dirty: { label: t('脏房'), strip: '#d97706', pill: '#d97706', pillBg: 'rgba(217,119,6,0.1)' },
  cleaning: {
    label: t('打扫中'),
    strip: '#1a73e8',
    pill: '#2563eb',
    pillBg: 'rgba(26,115,232,0.1)',
  },
  ooo: { label: t('维修中'), strip: '#ba1a1a', pill: '#dc2626', pillBg: 'rgba(186,26,26,0.1)' },
}
function ui(s: string) {
  return (
    ROOM_UI[s] || {
      label: s || t('净房'),
      strip: '#1e8e3e',
      pill: '#1e8e3e',
      pillBg: 'rgba(30,142,62,0.1)',
    }
  )
}
function icon(s: string) {
  return s === 'dirty'
    ? 'warning'
    : s === 'cleaning'
      ? 'sync'
      : s === 'ooo'
        ? 'lock'
        : 'check_circle'
}
</script>

<template>
  <div class="page">
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
        <h1>{{ t('房态总览看板') }}</h1>
        <p>{{ t('按楼层筛选查看客房清洁状态与 AI 指派建议。') }}</p>
      </div>
      <RoomBoardFlowNav mode="ops" hide-back />
    </div>

    <!-- 楼层筛选 + 图例 -->
    <div class="toolbar" style="flex-wrap: wrap">
      <span style="font-size: 13px; color: var(--on-surface-variant); margin-right: 4px">{{
        t('楼层筛选:')
      }}</span>
      <button class="chip" :class="{ active: floor === 'all' }" @click="floor = 'all'">
        全部 ({{ floorCounts.all }})
      </button>
      <button
        v-for="f in floors"
        :key="f"
        class="chip"
        :class="{ active: floor === f }"
        @click="floor = f"
      >
        {{ f }} ({{ floorCounts[f] || 0 }})
      </button>
      <div style="margin-left: auto; display: flex; gap: 16px; flex-wrap: wrap">
        <span class="legend"
          ><span class="dot" style="background: #1e8e3e"></span>{{ t('净房') }}</span
        >
        <span class="legend"
          ><span class="dot" style="background: #d97706"></span>{{ t('脏房') }}</span
        >
        <span class="legend"
          ><span class="dot" style="background: #1a73e8"></span>{{ t('打扫中') }}</span
        >
        <span class="legend"
          ><span class="dot" style="background: #ba1a1a"></span>{{ t('维修') }}</span
        >
      </div>
    </div>

    <!-- 房卡网格 -->
    <div class="grid">
      <div
        v-for="r in shown"
        :key="r.id"
        class="rc"
        :style="{ borderColor: ui(r.status).strip + '66' }"
      >
        <div class="strip" :style="{ background: ui(r.status).strip }"></div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start">
          <h3 class="num" style="font-size: 22px; font-weight: 700; margin: 0">{{ r.room_no }}</h3>
          <span
            class="pill-badge"
            :style="{ color: ui(r.status).pill, background: ui(r.status).pillBg }"
          >
            <span
              class="material-symbols-outlined"
              style="font-size: 14px"
              :class="{ spin: r.status === 'cleaning' }"
              >{{ icon(r.status) }}</span
            >
            {{ ui(r.status).label }}</span
          >
        </div>
        <div v-if="r.status === 'dirty'" class="ai-tip">
          <span class="material-symbols-outlined" style="font-size: 14px; color: var(--tertiary)"
            >smart_toy</span
          >
          <div>
            <p style="margin: 0; font-size: 12px; font-weight: 500; color: var(--on-surface)">
              AI {{ t('指派:') }} {{ r.assignee || t('最近保洁') }}
            </p>
            <p style="margin: 2px 0 0; font-size: 11px; color: var(--on-surface-variant)">
              {{ t('预计清理需要 45 分钟') }}
            </p>
          </div>
        </div>
        <div v-if="r.status === 'cleaning'" class="progress">
          <div class="pf" style="background: #1a73e8; width: 60%"></div>
        </div>
        <div style="margin-top: auto">
          <p style="font-size: 12px; color: var(--on-surface-variant); margin: 0">
            {{ r.room_type_name || t('客房') }} /
            {{
              r.status === 'occupied'
                ? r.guest_name || t('在住')
                : r.status === 'ooo'
                  ? '报修 ' + (r.note || '#402')
                  : t('空闲')
            }}
          </p>
        </div>
      </div>
      <div v-if="!shown.length" class="empty">{{ t('该楼层暂无房间') }}</div>
    </div>
  </div>
</template>

<style scoped>
.chip {
  padding: 6px 16px;
  border-radius: 999px;
  border: 1px solid var(--outline-variant);
  background: #fff;
  color: var(--on-surface);
  font-size: 13px;
  cursor: pointer;
}
.chip.active {
  background: var(--primary-container);
  color: var(--on-primary-container);
  border-color: var(--primary-container);
}
.legend {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.legend .dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.rc {
  background: var(--surface-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow);
}
.strip {
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
}
.pill-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-weight: 500;
}
.ai-tip {
  background: var(--surface-low);
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 8px;
  display: flex;
  gap: 6px;
}
.progress {
  width: 100%;
  background: var(--surface-high);
  border-radius: 999px;
  height: 6px;
  overflow: hidden;
}
.pf {
  height: 6px;
  border-radius: 999px;
}
.spin {
  animation: spin 1.5s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.empty {
  grid-column: 1 / -1;
  text-align: center;
  color: var(--on-surface-variant);
  padding: 30px;
}
</style>
