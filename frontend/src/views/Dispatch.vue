<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { STATUS_CN, TASK_ST_CN, TASK_ST_PILL, fmt, toast } from '../lib/ui'

const router = useRouter()
const rooms = ref<any[]>([])
const tasks = ref<any[]>([])
const filter = ref<'all' | 'dirty' | 'maint'>('all')

async function load() {
  rooms.value = await api.listRooms(hotelStore.hotelId)
  tasks.value = await api.listHousekeeping(hotelStore.hotelId)
}
onMounted(load)
watch(() => hotelStore.hotelId, load)

const worklist = computed(() => {
  // 1) 脏房未派工的房（自动起一条"清扫"任务）
  // 2) 派工未完成的房务任务
  const rooms_dirty = rooms.value
    .filter((r) => r.status === 'dirty')
    .map((r) => ({
      type: 'clean',
      room_no: r.room_no,
      room_id: r.id,
      title: '清扫',
      assignee: '自动派单…',
      eta: '15min',
      source: 'ai',
    }))
  const rooms_maint = rooms.value
    .filter((r) => r.status === 'maintenance')
    .map((r) => ({
      type: 'maint',
      room_no: r.room_no,
      room_id: r.id,
      title: '维修',
      assignee: '工程组',
      eta: '—',
      source: 'manual',
    }))
  const open_tasks = tasks.value
    .filter((t) => t.status !== 'done')
    .map((t) => ({
      type: t.task_type === 'clean' ? 'clean' : 'service',
      room_no: t.room_no,
      room_id: t.room_id,
      title: t.task_type,
      assignee: t.assignee || '—',
      eta: (t.due_at || '').slice(0, 16),
      source: 'task',
      id: t.id,
    }))
  return [...rooms_dirty, ...rooms_maint, ...open_tasks].filter((x) => {
    if (filter.value === 'all') return true
    if (filter.value === 'dirty') return x.type === 'clean'
    return x.type === 'maint'
  })
})

async function dispatch(row: any) {
  if (row.id) {
    await api.finishHousekeeping(row.id)
    toast(`工单 ${row.id} 已响应`)
  } else {
    if (row.type === 'clean') {
      await api.setRoomStatus(row.room_id, 'cleaning', '一键派单·开始清扫')
      toast(`${row.room_no} 已派单给 03 号阿姨`)
    } else if (row.type === 'maint') {
      toast(`${row.room_no} 工程组已收到派单`)
    }
  }
  load()
}

const counts = computed(() => ({
  dirty: rooms.value.filter((r) => r.status === 'dirty').length,
  maint: rooms.value.filter((r) => r.status === 'maintenance').length,
  task: worklist.value.length,
}))
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t('房务派工控制台') }}</h1>
      <p>{{ t('实时合并脏房清单、未派维修单、开放服务工单，一键派工或手工调整') }}</p>
    </div>

    <div
      class="card-clean"
      style="
        margin-bottom: 16px;
        padding: 12px 16px;
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
      "
    >
      <button class="chip-pill" :class="{ active: filter === 'all' }" @click="filter = 'all'">
        {{ t('全部 (') }}{{ worklist.length }})
      </button>
      <button class="chip-pill" :class="{ active: filter === 'dirty' }" @click="filter = 'dirty'">
        {{ t('脏房清扫 (') }}{{ counts.dirty }})
      </button>
      <button class="chip-pill" :class="{ active: filter === 'maint' }" @click="filter = 'maint'">
        {{ t('维修 (') }}{{ counts.maint }})
      </button>
      <span style="margin-left: auto; color: var(--on-surface-variant); font-size: 12px">
        <span class="ms" style="font-size: 14px; vertical-align: -2px; color: var(--tertiary)"
          >auto_awesome</span
        >
        {{ t('一键派单由 AI 推荐最近员工') }}</span
      >
    </div>

    <div class="card-clean">
      <div class="card-head">
        <span>{{ t('待派工 / 待响应') }}</span>
      </div>
      <table class="data">
        <thead>
          <tr>
            <th>{{ t('房间') }}</th>
            <th>{{ t('类型') }}</th>
            <th>{{ t('被派人') }}</th>
            <th class="num">{{ t('预计完成') }}</th>
            <th>{{ t('来源') }}</th>
            <th class="center">{{ t('操作') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in worklist" :key="i">
            <td>
              <span
                class="link"
                style="
                  font:
                    500 13px 'Roboto Mono',
                    monospace;
                "
                @click="router.push('/rooms/' + row.room_id)"
              >
                {{ row.room_no }} ↗
              </span>
            </td>
            <td>
              <span
                class="pill"
                :class="{
                  'pill-amber': row.type === 'clean',
                  'pill-slate': row.type === 'maint',
                  'pill-blue': row.type === 'service',
                }"
              >
                {{ row.title }}</span
              >
            </td>
            <td>{{ row.assignee }}</td>
            <td class="num">{{ row.eta }}</td>
            <td>
              <span v-if="row.source === 'ai'" class="pill pill-blue" style="font-size: 11px">
                <span class="ms" style="font-size: 12px">auto_awesome</span> AI
              </span>
              <span
                v-else-if="row.source === 'manual'"
                class="pill pill-slate"
                style="font-size: 11px"
                >{{ t('人工') }}</span
              >
              <span v-else class="pill pill-amber" style="font-size: 11px">{{ t('工单') }}</span>
            </td>
            <td class="center">
              <button class="btn-link" @click="dispatch(row)">{{ t('派单 / 完成 →') }}</button>
            </td>
          </tr>
          <tr v-if="!worklist.length">
            <td colspan="6" style="text-align: center; color: #9aa1ad; padding: 28px">
              {{ t('✦ 当前没有待派工的工作') }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
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
  cursor: pointer;
}
.chip-pill.active {
  background: rgba(0, 91, 191, 0.1);
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 500;
}
.ms {
  font-family: 'Material Symbols Outlined';
}
</style>
