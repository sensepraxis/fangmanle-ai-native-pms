<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 客房服务与检查（VIP 排班与质检视图）—— housekeeping/board
import { ref, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const data = ref<{
  priorities: any[]
  staff: any[]
  inspections: any[]
}>({
  priorities: [],
  staff: [],
  inspections: [],
})

function buildPriorities(board: any) {
  const schedule = board?.schedule || board?.tasks || []
  const open = schedule.filter((t: any) => t.status !== 'done').slice(0, 6)
  const edges = ['border-tertiary', 'border-tertiary/50', 'border-outline-variant']
  const tags = [
    { tag: t('高优'), tagClass: 'bg-error-container text-on-error-container' },
    { tag: 'VIP', tagClass: 'bg-tertiary-fixed text-on-tertiary-fixed' },
    { tag: t('常规'), tagClass: 'bg-surface-container-high text-on-surface-variant' },
  ]
  return open.map((t: any, i: number) => {
    const urgent = t.priority || (t.priority_rank || 5) <= 2
    const tagMeta = urgent ? tags[0] : i === 1 ? tags[1] : tags[2]
    return {
      room: t.room_no || '—',
      title: t.title || t('清扫任务'),
      metaIcon: t.icon || 'schedule',
      meta: [t.assignee, t.tip || t.elapsed].filter(Boolean).join(' · ') || t('待安排'),
      edge: edges[Math.min(i, edges.length - 1)],
      tag: tagMeta.tag,
      tagClass: tagMeta.tagClass,
    }
  })
}

function buildStaff(board: any) {
  const staff = board?.staff || []
  return staff.slice(0, 4).map((s: any) => {
    const done = Number(s.done || 0)
    const total = Math.max(Number(s.total || 0), done, 1)
    const pct = Math.min(100, Math.round((done / total) * 100))
    const name = s.name || t('员工')
    return {
      name,
      initial: name.slice(0, 1),
      shift: s.area || t('当日班次'),
      status: s.busy ? t('忙碌中') : t('可接单'),
      statusClass: s.busy
        ? 'bg-tertiary-fixed text-on-tertiary-fixed'
        : 'bg-surface-container-high text-on-surface-variant',
      done,
      total,
      pct,
      barClass: pct >= 80 ? 'bg-[#1e8e3e]' : pct >= 40 ? 'bg-primary' : 'bg-tertiary',
      checkout: Math.max(1, Math.round(total * 0.6)),
      stay: Math.max(0, total - Math.max(1, Math.round(total * 0.6))),
    }
  })
}

function buildInspections(board: any) {
  const vision = board?.vision?.rooms || []
  const pending = vision.filter((v: any) => !v.aiReviewed).slice(0, 6)
  if (pending.length) {
    return pending.map((v: any) => ({
      room: v.room,
      type: v.type || t('查房'),
      meta: v.floor || v.time || t('待检'),
      owner: v.note || v.inspector || t('质检员'),
    }))
  }
  // 兜底：开放查房任务
  return (board?.tasks || [])
    .filter((t: any) => t.type === 'inspect' && t.status !== 'done')
    .slice(0, 4)
    .map((t: any) => ({
      room: t.room_no,
      type: t.title || t('查房'),
      meta: t.elapsed || t('待检'),
      owner: t.assignee || t('质检员'),
    }))
}

async function load() {
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId)
    data.value = {
      priorities: buildPriorities(board),
      staff: buildStaff(board),
      inspections: buildInspections(board),
    }
  } catch {
    data.value = { priorities: [], staff: [], inspections: [] }
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>{{ t('客房服务与检查') }}</h1>
        <p>{{ t('AI 优化排班与实时质检视图 · 数据来自房务作业台') }}</p>
      </div>
      <div class="head-actions">
        <button class="btn">
          <span class="material-symbols-outlined text-sm">print</span>{{ t('打印排班表') }}
        </button>
        <button class="btn btn-primary">
          <span class="material-symbols-outlined text-sm">add</span>{{ t('新增特殊任务') }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-4">
      <div class="col-span-8 flex flex-col gap-4">
        <section class="card-clean ai-glow overflow-hidden flex flex-col">
          <div class="card-head" style="background: rgba(235, 178, 255, 0.2)">
            <div class="flex items-center gap-2">
              <span
                class="material-symbols-outlined text-tertiary"
                style="font-variation-settings: 'FILL' 1"
                >auto_awesome</span
              >
              <h2>{{ t('AI 智能优先级推荐') }}</h2>
            </div>
            <span
              class="pill"
              style="background: var(--tertiary-fixed); color: var(--on-tertiary-fixed)"
              >{{ t('基于开放任务与 ETA') }}</span
            >
          </div>
          <div class="p-4 flex flex-col gap-3">
            <p v-if="!data.priorities.length" class="text-sm text-on-surface-variant">
              {{ t('暂无高优任务') }}
            </p>
            <div
              v-for="p in data.priorities"
              :key="p.room + p.title"
              class="flex items-center justify-between p-3 rounded-lg border-l-4 bg-surface transition-colors hover:bg-surface-variant cursor-pointer group"
              :class="p.edge"
            >
              <div class="flex items-center gap-4">
                <div
                  class="w-12 h-12 rounded-lg bg-surface-container flex items-center justify-center font-num-xl text-num-xl text-on-surface"
                >
                  {{ p.room }}
                </div>
                <div>
                  <h3 class="font-headline-md text-base text-on-background">{{ p.title }}</h3>
                  <p class="text-sm text-on-surface-variant flex items-center gap-1">
                    <span class="material-symbols-outlined text-[14px]">{{ p.metaIcon }}</span
                    >{{ p.meta }}
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <span class="px-3 py-1 rounded-full font-label-lg text-sm" :class="p.tagClass">{{
                  p.tag
                }}</span>
                <button
                  class="w-8 h-8 rounded-full flex items-center justify-center border border-outline text-on-surface-variant hover:bg-surface-container-highest"
                >
                  <span class="material-symbols-outlined text-sm">more_vert</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        <section>
          <h2 class="font-headline-md text-on-background mb-4">{{ t('今日排班与工作量') }}</h2>
          <p v-if="!data.staff.length" class="text-sm text-on-surface-variant">
            {{ t('暂无排班数据') }}
          </p>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="s in data.staff"
              :key="s.name"
              class="card-clean hover:shadow-sm transition-shadow"
            >
              <div class="flex justify-between items-start mb-4">
                <div class="flex items-center gap-3">
                  <div
                    class="w-12 h-12 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-headline-md"
                  >
                    {{ s.initial }}
                  </div>
                  <div>
                    <h3 class="font-headline-md text-lg text-on-background">{{ s.name }}</h3>
                    <p class="text-sm text-on-surface-variant">{{ s.shift }}</p>
                  </div>
                </div>
                <span class="px-2 py-1 rounded font-label-lg text-xs" :class="s.statusClass">{{
                  s.status
                }}</span>
              </div>
              <div class="flex justify-between items-center mb-2">
                <span class="text-on-surface-variant"
                  >{{ t('进度 (') }}{{ s.done }}/{{ s.total }})</span
                >
                <span class="font-num-md text-on-background">{{ s.pct }}%</span>
              </div>
              <div class="w-full bg-surface-container h-2 rounded-full overflow-hidden mb-4">
                <div
                  class="h-full rounded-full"
                  :class="s.barClass"
                  :style="{ width: s.pct + '%' }"
                ></div>
              </div>
              <div class="flex gap-2">
                <span
                  class="flex-1 py-1 text-center rounded bg-surface-container-high text-on-surface font-label-lg text-xs"
                  >{{ t('退房清洁:') }} {{ s.checkout }}</span
                >
                <span
                  class="flex-1 py-1 text-center rounded bg-surface-container-high text-on-surface font-label-lg text-xs"
                  >{{ t('连住打扫:') }} {{ s.stay }}</span
                >
              </div>
            </div>
          </div>
        </section>
      </div>

      <div class="col-span-4 flex flex-col h-full">
        <section class="card-clean flex flex-col h-full overflow-hidden">
          <div class="card-head" style="background: var(--surface-bright)">
            <h2>{{ t('质检待办') }}</h2>
            <span
              class="w-6 h-6 rounded-full bg-error text-on-error flex items-center justify-center font-label-lg text-xs"
              >{{ data.inspections.length }}</span
            >
          </div>
          <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
            <p v-if="!data.inspections.length" class="text-sm text-on-surface-variant">
              {{ t('暂无质检待办') }}
            </p>
            <div
              v-for="it in data.inspections"
              :key="it.room + it.type"
              class="border border-outline-variant rounded-lg p-3 bg-surface hover:border-primary transition-colors cursor-pointer"
            >
              <div class="flex justify-between items-start mb-2">
                <div class="flex items-center gap-2">
                  <span class="font-num-md font-bold text-on-background">{{ it.room }}</span>
                  <span
                    class="px-2 py-0.5 rounded text-[10px] font-label-lg bg-surface-container-highest text-on-surface-variant"
                    >{{ it.type }}</span
                  >
                </div>
                <span class="text-xs text-on-surface-variant">{{ it.meta }}</span>
              </div>
              <p class="text-sm text-on-surface mb-3">{{ t('负责人:') }} {{ it.owner }}</p>
              <div class="grid grid-cols-2 gap-2">
                <button
                  class="py-1.5 border border-error text-error rounded font-label-lg hover:bg-error-container transition-colors text-sm"
                >
                  {{ t('打回重扫') }}
                </button>
                <button
                  class="py-1.5 bg-[#1e8e3e] text-white rounded font-label-lg hover:opacity-90 transition-opacity text-sm"
                >
                  {{ t('通过检查') }}
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-glow {
  box-shadow: 0 0 15px -3px rgba(140, 51, 179, 0.3);
  border-left: 2px solid var(--tertiary);
}
.border-tertiary {
  border-left-color: var(--tertiary);
}
.border-tertiary\/50 {
  border-left-color: rgba(140, 51, 179, 0.5);
}
@media (max-width: 900px) {
  .grid-cols-12 > * {
    grid-column: span 12 !important;
  }
}
</style>
