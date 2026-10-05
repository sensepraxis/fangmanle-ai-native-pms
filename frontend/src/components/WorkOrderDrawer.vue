<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { computed } from 'vue'
import { useRouter } from 'vue-router'

export type WorkOrderTask = {
  woId: string
  title: string
  room?: string
  time?: string
  by?: string
  type?: string
  status?: string
  statusCls?: string
  assetId?: number
  assetName?: string
  assetNo?: string
  worker?: string
  part?: string
  executor?: string
  raw?: string
  step?: number
  done?: boolean
  createdAt?: string
}

const props = defineProps<{
  open: boolean
  task: WorkOrderTask | null
}>()

const emit = defineEmits<{
  close: []
}>()

const router = useRouter()
const flowSteps = [t('已报修'), t('已派工'), t('维修中'), t('已完成')]

const timeline = computed(() => {
  const task = props.task
  if (!task) return []
  return [
    { label: t('工单创建'), time: task.createdAt || task.time || '—', done: (task.step || 1) >= 1 },
    {
      label: t('派工确认'),
      time: task.worker
        ? t('指派 {name}', { name: String(task.worker).replace(/（.*$/, '') })
        : t('待指派'),
      done: (task.step || 1) >= 2,
    },
    {
      label: t('现场维修'),
      time: task.part || (task.raw === 'repairing' ? t('处理中') : '—'),
      done: (task.step || 1) >= 3,
    },
    { label: t('验收关单'), time: task.done ? t('已完成') : t('待完成'), done: !!task.done },
  ]
})

function goAsset() {
  if (props.task?.assetId) router.push(`/c8-assets/assets/${props.task.assetId}`)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open && task" class="wo-drawer-root" @click.self="emit('close')">
      <aside class="wo-drawer">
        <div class="wo-drawer-head">
          <div>
            <p class="wo-drawer-k">{{ t('工单编号') }}</p>
            <h2 class="wo-drawer-id">{{ task.woId }}</h2>
          </div>
          <button type="button" class="icon-btn" @click="emit('close')">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="wo-drawer-body">
          <div class="wo-drawer-top">
            <span v-if="task.status" class="pill" :class="'pill-' + (task.statusCls || 'slate')">{{
              task.status
            }}</span>
            <span class="wo-type-tag">{{ task.type || task.by || t('工单') }}</span>
          </div>

          <h3 class="wo-drawer-title">{{ task.title }}</h3>
          <p class="wo-drawer-meta">
            <span>{{ task.room || '—' }}</span>
            <span v-if="task.time">· {{ task.time }}</span>
            <span v-if="task.by">· {{ task.by }}</span>
          </p>

          <div v-if="task.assetId" class="wo-asset-card" @click="goAsset">
            <span class="material-symbols-outlined">inventory_2</span>
            <div class="min-w-0">
              <div class="font-semibold text-sm">{{ task.assetName || t('关联设备') }}</div>
              <div class="text-xs text-on-surface-variant">
                {{ task.assetNo }} · {{ t('点击查看资产画像') }}
              </div>
            </div>
            <span class="material-symbols-outlined text-on-surface-variant">chevron_right</span>
          </div>

          <div class="wo-flow">
            <div class="wo-flow-labels">
              <span
                v-for="(s, i) in flowSteps"
                :key="s"
                :class="{ on: (task.step || 1) > i || (task.done && i === 3) }"
                >{{ s }}</span
              >
            </div>
            <div class="wo-flow-track">
              <template v-for="(_, i) in flowSteps" :key="i">
                <span
                  class="wo-flow-dot"
                  :class="{ on: (task.step || 1) > i || (task.done && i <= 3) }"
                />
                <span
                  v-if="i < flowSteps.length - 1"
                  class="wo-flow-line"
                  :class="{ on: (task.step || 1) > i + 1 }"
                />
              </template>
            </div>
          </div>

          <div class="wo-timeline">
            <h4>{{ t('流转记录') }}</h4>
            <div v-for="(ev, i) in timeline" :key="i" class="wo-tl-item">
              <span class="wo-tl-dot" :class="{ on: ev.done }" />
              <div>
                <div class="wo-tl-label">{{ ev.label }}</div>
                <div class="wo-tl-time">{{ ev.time }}</div>
              </div>
            </div>
          </div>

          <p v-if="task.part" class="wo-part">
            <span class="material-symbols-outlined">inventory_2</span>
            {{ task.part }}
          </p>
          <p v-if="task.worker" class="wo-worker">
            <span class="material-symbols-outlined">engineering</span>
            {{ task.worker }}
            <span v-if="task.executor === 'vendor'" class="exec-tag">{{ t('外协') }}</span>
          </p>
        </div>

        <div class="wo-drawer-foot">
          <button v-if="task.assetId" type="button" class="btn btn-ghost w-full" @click="goAsset">
            {{ t('查看关联资产') }}
          </button>
          <button type="button" class="btn btn-ghost w-full" @click="emit('close')">
            {{ t('关闭') }}
          </button>
        </div>
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.wo-drawer-root {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  justify-content: flex-end;
}
.wo-drawer {
  width: min(420px, 100vw);
  height: 100%;
  background: var(--surface-container-lowest);
  border-left: 1px solid var(--outline-variant);
  display: flex;
  flex-direction: column;
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.12);
}
.wo-drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid var(--outline-variant);
}
.wo-drawer-k {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.wo-drawer-id {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  font-family: 'Roboto Mono', monospace;
}
.wo-drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.wo-drawer-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.wo-type-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--surface-container-high);
  color: var(--on-surface-variant);
}
.wo-drawer-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.4;
}
.wo-drawer-meta {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.wo-asset-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
  cursor: pointer;
}
.wo-asset-card:hover {
  border-color: var(--primary);
}
.wo-asset-card .material-symbols-outlined:first-child {
  color: var(--primary);
}
.wo-flow {
  padding: 12px 0;
}
.wo-flow-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-bottom: 8px;
}
.wo-flow-labels .on {
  color: var(--primary);
  font-weight: 600;
}
.wo-flow-track {
  display: flex;
  align-items: center;
}
.wo-flow-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--surface-variant);
  flex-shrink: 0;
}
.wo-flow-dot.on {
  background: var(--primary);
}
.wo-flow-line {
  flex: 1;
  height: 2px;
  background: var(--surface-variant);
  margin: 0 4px;
}
.wo-flow-line.on {
  background: var(--primary);
}
.wo-timeline h4 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 700;
}
.wo-tl-item {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
}
.wo-tl-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 5px;
  background: var(--outline-variant);
  flex-shrink: 0;
}
.wo-tl-dot.on {
  background: var(--primary);
}
.wo-tl-label {
  font-size: 14px;
  font-weight: 600;
}
.wo-tl-time {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-top: 2px;
}
.wo-part,
.wo-worker {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--surface-container);
}
.wo-drawer-foot {
  padding: 16px 20px;
  border-top: 1px solid var(--outline-variant);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.wo-drawer-foot .w-full {
  width: 100%;
  justify-content: center;
}
.exec-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: #e3f2fd;
  color: #1565c0;
}
.pill {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
}
.pill-rose {
  background: #ffe4e6;
  color: #be123c;
}
.pill-blue {
  background: #dbeafe;
  color: #1d4ed8;
}
.pill-slate {
  background: #f1f5f9;
  color: #475569;
}
</style>
