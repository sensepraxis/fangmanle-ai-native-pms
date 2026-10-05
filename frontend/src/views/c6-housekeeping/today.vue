<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 住中需求工单：看板四列 —— 数据来自 service_requests 表
import { ref, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

type Card = {
  id: number
  room: string
  title: string
  desc: string
  priority: boolean
  tag?: string
  assignee?: string
  time: string
  action?: string
  spent?: string
  progress?: number
  eta?: string
  aiNote?: string
}

type Col = {
  key: string
  title: string
  color: string
  done?: boolean
  count: number
  cards: Card[]
}

const columns = ref<Col[]>([])

function colOf(status?: string, assigneeId?: number | null, id?: number): string {
  const st = (status || 'open').toLowerCase()
  if (st in { done: 1, closed: 1, resolved: 1 }) return 'done'
  if (st === 'in_progress' || st === 'doing' || st === 'progress') return 'progress'
  if (st === 'assigned' || st === 'dispatched') return 'assigned'
  // 兼容旧种子仅 open/done：无指派→待接单；有指派按 id 分到已派单/处理中
  if (!assigneeId) return 'pending'
  return (id || 0) % 2 === 1 ? 'progress' : 'assigned'
}

function buildColumns(rows: any[]): Col[] {
  const buckets: Record<string, Card[]> = {
    pending: [],
    assigned: [],
    progress: [],
    done: [],
  }

  for (const sr of rows) {
    const key = colOf(sr.status, sr.assignee_id, sr.id)
    const urgent = Number(sr.priority || 5) <= 2
    const content = sr.content || sr.msg || t('客需服务')
    const room = sr.room_no || sr.room || '—'
    const card: Card = {
      id: sr.id,
      room,
      title: content.slice(0, 18),
      desc: content,
      priority: urgent && key !== 'done',
      tag: sr.channel || undefined,
      assignee: key === 'pending' ? undefined : sr.assignee || undefined,
      time: sr.time || (sr.created_at ? String(sr.created_at).slice(11, 16) : '—'),
      action:
        key === 'pending'
          ? t('接单')
          : key === 'assigned'
            ? t('开始处理')
            : key === 'progress'
              ? t('完成')
              : undefined,
      spent: key === 'done' ? t('已闭环') : undefined,
      progress: key === 'progress' ? 55 : undefined,
      eta: key === 'progress' ? t('约 20 分钟') : undefined,
      aiNote: urgent ? t('高优客需，建议对照客史偏好优先响应') : undefined,
    }
    buckets[key].push(card)
  }

  const meta: { key: string; title: string; color: string; done?: boolean }[] = [
    { key: 'pending', title: t('待接单'), color: 'var(--error, #ba1a1a)' },
    { key: 'assigned', title: t('已派单'), color: 'var(--primary, #2563eb)' },
    { key: 'progress', title: t('处理中'), color: 'var(--tertiary, #8c33b3)' },
    { key: 'done', title: t('已完成'), color: '#1e8e3e', done: true },
  ]
  return meta.map((m) => ({
    ...m,
    count: buckets[m.key].length,
    cards: buckets[m.key],
  }))
}

async function load() {
  try {
    // 优先专用列表；失败则用 board 聚合
    let rows: any[] = []
    try {
      rows = await api.listServiceRequests(hotelStore.hotelId)
    } catch {
      const board = await api.housekeepingBoard(hotelStore.hotelId)
      rows = board?.service_requests || []
    }
    columns.value = buildColumns(rows || [])
  } catch {
    columns.value = buildColumns([])
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>{{ t('住中需求工单') }}</h1>
        <p>{{ t('数据来自客需工单表 · 按状态分列') }}</p>
      </div>
      <div class="flex gap-3">
        <button class="btn btn-ghost">
          <span class="material-symbols-outlined">filter_list</span>{{ t('筛选') }}
        </button>
        <button class="btn btn-primary">
          <span class="material-symbols-outlined">add</span>{{ t('新建工单') }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
      <template v-for="col in columns" :key="col.key">
        <div class="flex flex-col gap-4">
          <div class="flex items-center justify-between pb-2 border-b-2 border-outline-variant">
            <div class="flex items-center gap-2">
              <div class="w-2.5 h-2.5 rounded-full" :style="{ background: col.color }"></div>
              <h2 class="font-semibold text-lg text-on-surface">
                {{ col.title
                }}<span class="text-on-surface-variant text-sm font-normal ml-1">{{
                  col.count
                }}</span>
              </h2>
            </div>
          </div>
          <p v-if="!col.cards.length" class="text-sm text-on-surface-variant px-1">
            {{ t('暂无工单') }}
          </p>
          <template v-for="c in col.cards" :key="c.id">
            <div
              class="bg-surface-lowest rounded-xl p-4 shadow-sm border border-outline-variant hover:shadow-md transition-shadow cursor-pointer flex flex-col"
              :class="col.done ? 'opacity-75' : ''"
            >
              <div class="flex justify-between items-start mb-3">
                <span
                  class="font-num-xl text-on-surface"
                  :class="col.done ? 'text-on-surface-variant line-through' : ''"
                  >{{ c.room }}</span
                >
                <span
                  v-if="c.priority"
                  class="px-2 py-1 bg-error-container text-on-error-container rounded font-label-lg text-[12px] flex items-center gap-1"
                  >{{ t('紧急') }}</span
                >
                <span
                  v-else-if="c.tag"
                  class="px-2 py-1 bg-surface-variant text-on-surface-variant rounded font-label-lg text-[12px]"
                  >{{ c.tag }}</span
                >
              </div>
              <h3 class="font-medium text-on-surface mb-1">{{ c.title }}</h3>
              <p class="text-sm text-on-surface-variant mb-4">{{ c.desc }}</p>
              <div
                v-if="c.aiNote"
                class="rounded-lg p-2.5 mb-4 flex items-start gap-2"
                :style="{
                  background: 'rgba(235,178,255,.2)',
                  borderLeft: '2px solid var(--tertiary)',
                }"
              >
                <div>
                  <p class="font-label-lg text-[12px] text-on-surface font-semibold">
                    {{ t('客史偏好') }}
                  </p>
                  <p class="text-[12px] text-on-surface-variant">{{ c.aiNote }}</p>
                </div>
              </div>
              <div
                v-if="c.assignee"
                class="flex items-center gap-2 mb-4 bg-surface-low p-2 rounded-lg"
              >
                <div
                  class="w-6 h-6 rounded-full bg-surface-high flex items-center justify-center text-xs"
                >
                  {{ c.assignee.charAt(0) }}
                </div>
                <span class="font-label-lg text-sm text-on-surface">{{ c.assignee }}</span>
              </div>
              <div
                v-if="c.progress != null"
                class="w-full bg-surface-highest rounded-full h-1.5 mb-2"
              >
                <div
                  class="h-1.5 rounded-full"
                  :style="{ width: c.progress + '%', background: 'var(--tertiary)' }"
                ></div>
              </div>
              <p v-if="c.eta" class="font-label-lg text-[11px] text-tertiary text-right mb-4">
                预计 {{ c.eta }} 完成
              </p>
              <div
                class="flex justify-between items-center mt-2 pt-3 border-t border-surface-highest"
              >
                <span class="flex items-center gap-1 text-on-surface-variant"
                  ><span class="font-num-md text-[12px]">{{ c.time }}</span></span
                >
                <button v-if="c.action" class="text-primary font-label-lg text-sm hover:underline">
                  {{ c.action }}
                </button>
                <span v-else-if="c.spent" class="font-label-lg text-[11px] text-on-surface-variant"
                  >耗时: {{ c.spent }}</span
                >
              </div>
            </div>
          </template>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
@media (max-width: 900px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
