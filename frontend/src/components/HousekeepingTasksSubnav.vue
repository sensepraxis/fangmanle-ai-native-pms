<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 房务任务 · 二级类目
 * 任务 / 客中请求 / 排班
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const TABS = [
  { label: t('任务'), icon: 'checklist', path: '/c6-housekeeping/housekeeping' },
  {
    label: t('客中请求'),
    icon: 'room_service',
    path: '/c6-housekeeping/in-stay-guest-request-management',
  },
  { label: t('排班'), icon: 'calendar_month', path: '/c6-housekeeping/staffing' },
] as const

function normalize(p: string) {
  return (p || '').replace(/\/+$/, '') || '/'
}

function isActive(path: string) {
  const cur = normalize(route.path)
  if (path === '/c6-housekeeping/housekeeping') {
    return cur === path || cur === '/housekeeping' || cur === '/c6-housekeeping/room-board'
  }
  return cur === normalize(path)
}

const activePath = computed(() => TABS.find((t) => isActive(t.path))?.path || '')
</script>

<template>
  <nav class="hk-subnav" :aria-label="t('房务任务')">
    <button
      v-for="tab in TABS"
      :key="tab.path"
      type="button"
      class="subtab"
      :class="{ on: activePath === tab.path }"
      @click="router.push(tab.path)"
    >
      <span class="material-symbols-outlined">{{ tab.icon }}</span>
      {{ t(tab.label) }}
    </button>
  </nav>
</template>

<style scoped>
.hk-subnav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 24px;
}
.subtab {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid #e5e7eb;
  background: #fff;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  border-radius: 999px;
}
.subtab .material-symbols-outlined {
  font-size: 17px;
}
.subtab:hover {
  color: #1f2329;
  border-color: #d0d5dd;
}
.subtab.on {
  color: #fff;
  background: #2c241b;
  border-color: #2c241b;
}
</style>
