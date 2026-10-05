<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { STATUS_CN, TASK_ST_CN, TASK_ST_PILL, toast } from '../lib/ui'

const route = useRoute()
const router = useRouter()
const r = ref<any>(null)
const loading = ref(true)

const ALL = ['vacant', 'occupied', 'dirty', 'cleaning', 'maintenance', 'ooo']

async function load() {
  loading.value = true
  try {
    r.value = await api.getRoom(Number(route.params.id))
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => route.params.id, load)

async function changeStatus() {
  const next = prompt('改为状态 (' + ALL.join('/') + ')：', r.value.status)
  if (!next || !ALL.includes(next)) return
  const reason = prompt('原因（可选）：', '') || ''
  await api.setRoomStatus(r.value.id, next, reason)
  toast(t('房态已更新'))
  load()
}
</script>

<template>
  <div class="page">
    <a class="back-link" @click="router.push('/room-board')">
      <span class="material-symbols-outlined" style="font-size: 18px">arrow_back</span>
      {{ t('返回房态看板') }}</a
    >

    <div v-if="loading" style="color: #9aa1ad; font-size: 13px">{{ t('加载中…') }}</div>
    <div v-else-if="r">
      <div class="page-actions">
        <div class="page-head" style="margin: 0">
          <h1>{{ r.room_no }}</h1>
          <p>{{ r.room_type_name }} · {{ r.floor }}F · {{ r.building || t('主楼') }}</p>
        </div>
        <button class="btn btn-ghost" @click="changeStatus">{{ t('变更房态') }}</button>
      </div>

      <div style="display: flex; gap: 8px; margin-bottom: 16px">
        <span
          class="pill"
          :class="{
            'pill-green': r.status === 'vacant',
            'pill-blue': r.status === 'occupied',
            'pill-amber': r.status === 'dirty' || r.status === 'cleaning',
            'pill-slate': r.status === 'maintenance' || r.status === 'ooo',
          }"
          >{{ STATUS_CN[r.status] || r.status }}</span
        >
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px">
        <!-- 状态流 -->
        <div class="card-clean">
          <div class="card-head">
            <span>{{ t('房态变更记录') }}</span>
          </div>
          <div style="padding: 16px">
            <div
              v-for="(l, i) in r.status_log"
              :key="l.id"
              style="
                display: flex;
                gap: 10px;
                font-size: 13px;
                padding: 6px 0;
                border-bottom: 1px solid var(--surface-high);
              "
            >
              <span class="pill" :class="i === 0 ? 'pill-blue' : 'pill-slate'">{{
                l.to_status
              }}</span>
              <span style="color: var(--on-surface-variant)">{{ l.reason || '—' }}</span>
              <span style="margin-left: auto; color: #9aa1ad">{{
                (l.created_at || '').slice(0, 16).replace('T', ' ')
              }}</span>
            </div>
            <div
              v-if="!r.status_log?.length"
              style="color: #9aa1ad; font-size: 13px; padding: 8px 0"
            >
              {{ t('暂无记录') }}
            </div>
          </div>
        </div>

        <!-- 房务任务 -->
        <div class="card-clean">
          <div class="card-head">
            <span>{{ t('关联房务任务') }}</span>
          </div>
          <div style="padding: 16px">
            <div
              v-for="tag in r.housekeeping"
              :key="tag.id"
              style="
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 13px;
                padding: 6px 0;
                border-bottom: 1px solid var(--surface-high);
              "
            >
              <span class="pill" :class="TASK_ST_PILL[tag.status] || 'pill-slate'">{{
                TASK_ST_CN[tag.status] || tag.status
              }}</span>
              <span style="color: var(--on-surface)">{{ tag.task_type }}</span>
              <span style="margin-left: auto; color: #9aa1ad">{{
                (tag.due_at || '').slice(0, 10)
              }}</span>
            </div>
            <div
              v-if="!r.housekeeping?.length"
              style="color: #9aa1ad; font-size: 13px; padding: 8px 0"
            >
              {{ t('暂无房务任务') }}
            </div>
            <button
              class="btn btn-link"
              style="margin-top: 8px"
              @click="router.push('/housekeeping')"
            >
              {{ t('前往房务管理 ↗') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
