<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 房态看板（前台）—— 移植自 C5-frontdesk-orders/room-board.html
import { ref, computed, onMounted } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import RoomBoardFlowNav from '../../components/RoomBoardFlowNav.vue'

const hotelId = hotelStore.hotelId
const filter = ref('all')
const aiPricing = ref(true)
const rooms = ref<any[]>([])

// 房态色（与原型图例一致）
const STAT: Record<string, { c: string; l: string }> = {
  clean: { c: '#1e8e3e', l: '已清洁' },
  vacant: { c: '#1e8e3e', l: '已清洁' },
  dirty: { c: '#d93025', l: '待清洁' },
  maintenance: { c: '#f9ab00', l: '维护' },
  ooo: { c: '#9aa0a6', l: '维护' },
  occupied: { c: '#1a73e8', l: '在住' },
}
function sc(s: string) {
  return (STAT[s] || STAT.clean).c
}
function sl(s: string) {
  return (STAT[s] || STAT.clean).l
}

const counts = computed(() => {
  const c: any = { clean: 0, dirty: 0, maint: 0 }
  rooms.value.forEach((r: any) => {
    if (r.status === 'clean' || r.status === 'vacant') c.clean++
    else if (r.status === 'dirty') c.dirty++
    else c.maint++
  })
  return c
})

const filtered = computed(() => {
  if (filter.value === 'clean')
    return rooms.value.filter((r) => r.status === 'clean' || r.status === 'vacant')
  if (filter.value === 'dirty') return rooms.value.filter((r) => r.status === 'dirty')
  if (filter.value === 'maint')
    return rooms.value.filter((r) => r.status === 'maintenance' || r.status === 'ooo')
  return rooms.value
})

onMounted(async () => {
  try {
    const rs = await api.listRooms(hotelId)
    if (rs.length) rooms.value = rs
  } catch (e) {}
})
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
        margin-bottom: 16px;
      "
    >
      <div>
        <h1 style="margin: 0; font-size: 24px; font-weight: 800">{{ t('房态看板') }}</h1>
        <p style="margin: 4px 0 0; color: var(--on-surface-variant); font-size: 14px">
          {{ t('前台客房状态总览 · 侧栏「房态看板」支线') }}
        </p>
      </div>
      <RoomBoardFlowNav mode="ops" hide-back />
    </div>

    <!-- 工具栏 -->
    <div
      class="h-16 flex-shrink-0 bg-surface-container-lowest border-b border-outline-variant flex items-center justify-between px-6 shadow-sm z-10 mb-6 rounded-xl"
    >
      <div class="flex items-center gap-4">
        <div
          class="flex items-center bg-surface-container-low rounded-lg p-1 border border-outline-variant"
        >
          <span
            class="font-label-lg text-label-lg text-on-surface px-4 py-1 font-medium flex items-center gap-2"
            >{{ t('今日 10月24日') }}</span
          >
        </div>
        <div class="h-6 w-[1px] bg-outline-variant mx-2"></div>
        <div class="flex items-center gap-2">
          <button
            class="px-3 py-1.5 rounded-full border border-primary bg-primary/10 text-primary font-label-lg text-label-lg flex items-center gap-1 transition-colors"
          >
            <span class="w-2 h-2 rounded-full bg-primary"></span>{{ t('全部') }}
          </button>
          <button
            class="px-3 py-1.5 rounded-full border border-outline-variant bg-surface hover:bg-surface-variant text-on-surface-variant font-label-lg text-label-lg flex items-center gap-1 transition-colors"
          >
            <span class="w-2 h-2 rounded-full" style="background: #1e8e3e"></span>{{ t('已清洁（')
            }}{{ counts.clean }}）
          </button>
          <button
            class="px-3 py-1.5 rounded-full border border-outline-variant bg-surface hover:bg-surface-variant text-on-surface-variant font-label-lg text-label-lg flex items-center gap-1 transition-colors"
          >
            <span class="w-2 h-2 rounded-full" style="background: #d93025"></span>{{ t('待清洁（')
            }}{{ counts.dirty }}）
          </button>
          <button
            class="px-3 py-1.5 rounded-full border border-outline-variant bg-surface hover:bg-surface-variant text-on-surface-variant font-label-lg text-label-lg flex items-center gap-1 transition-colors"
          >
            <span class="w-2 h-2 rounded-full" style="background: #f9ab00"></span>{{ t('维护（')
            }}{{ counts.maint }}）
          </button>
        </div>
      </div>
      <div class="flex items-center gap-4">
        <label
          class="flex items-center gap-2 cursor-pointer bg-tertiary-container/20 px-3 py-1.5 rounded-lg border border-tertiary/30"
        >
          <span class="font-label-lg text-label-lg text-on-surface font-medium">{{
            t('AI 定价')
          }}</span>
          <div class="relative inline-block w-8 h-4 ml-2">
            <input v-model="aiPricing" type="checkbox" class="peer sr-only" />
            <div
              class="w-8 h-4 bg-outline-variant rounded-full peer-checked:bg-tertiary transition-colors"
            ></div>
            <div
              class="absolute left-0.5 top-0.5 w-3 h-3 bg-surface-container-lowest rounded-full transition-transform peer-checked:translate-x-4 shadow-sm"
            ></div>
          </div>
        </label>
      </div>
    </div>

    <!-- 房态网格 -->
    <div
      class="flex-1 overflow-auto p-6 bg-surface-container-low relative rounded-xl border border-outline-variant"
    >
      <div class="mb-8">
        <h3 class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2">
          {{ t('1 楼') }}
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <div
            v-for="r in filtered"
            :key="r.id || r.room_no"
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-sm hover:shadow-md transition-all cursor-pointer relative overflow-hidden group"
          >
            <div
              class="absolute top-0 left-0 w-full h-1.5"
              :style="{ background: sc(r.status) }"
            ></div>
            <div class="flex justify-between items-start mt-1 mb-3">
              <div class="font-num-xl text-num-xl text-on-surface">{{ r.room_no }}</div>
              <div class="flex flex-col items-end gap-1">
                <span
                  class="px-2 py-0.5 bg-primary-container/20 text-primary-container text-xs font-medium rounded-full border border-primary-container/30"
                  >{{ r.room_type_name || t('大床房') }}</span
                >
                <div
                  v-if="aiPricing"
                  class="flex items-center gap-1 text-tertiary font-num-md text-sm bg-tertiary/10 px-2 rounded border border-tertiary/20"
                >
                  ¥{{ r.ai_price || r.base_price || 450 }}
                </div>
              </div>
            </div>
            <div
              v-if="r.status === 'occupied' || r.guest_name"
              class="flex items-center gap-2 mb-3 bg-surface-container-low p-2 rounded-lg"
            >
              <div
                class="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-medium text-sm"
              >
                {{ (r.guest_name || t('客')).slice(0, 1) }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-on-surface truncate">
                  {{ r.guest_name || t('在住客人') }}
                </div>
                <div class="text-xs text-on-surface-variant truncate">
                  {{ t('退房：') }}{{ r.check_out || t('明日') }}
                </div>
              </div>
            </div>
            <div
              v-else
              class="flex items-center justify-center h-12 mb-3 bg-surface-container border border-dashed border-outline-variant rounded-lg text-on-surface-variant text-sm"
            >
              {{ t('空置') }}
            </div>
            <div
              class="flex justify-between items-center text-xs text-on-surface-variant pt-2 border-t border-outline-variant/50"
            >
              <span class="flex items-center gap-1" :style="{ color: sc(r.status) }">{{
                sl(r.status)
              }}</span>
              <span>{{ r.nights || 1 }} {{ t('晚') }}</span>
            </div>
          </div>
        </div>
      </div>
      <!-- 图例 -->
      <div
        class="h-12 border-t border-outline-variant bg-surface-container-lowest flex items-center px-6 gap-6 text-sm text-on-surface-variant shadow-[0_-2px_4px_rgba(0,0,0,0.02)] z-10 rounded-b-xl"
      >
        <span class="font-medium">{{ t('图例：') }}</span>
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-sm" style="background: #1e8e3e"></span>{{ t('已清洁') }}
        </div>
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-sm" style="background: #d93025"></span>{{ t('待清洁') }}
        </div>
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-sm" style="background: #f9ab00"></span>{{ t('维护') }}
        </div>
        <div class="w-[1px] h-4 bg-outline-variant mx-2"></div>
        <div class="flex items-center gap-1 text-tertiary">{{ t('AI 优化价') }}</div>
      </div>
    </div>
  </div>
</template>
