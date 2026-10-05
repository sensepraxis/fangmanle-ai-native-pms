<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 房务与房态 · 二级入口
 * 房态看板 / 房务任务 / 库存预售 / 设备设施 / 房务报表
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { filterByMenu } from '../store/rbac'

const route = useRoute()
const router = useRouter()

const TABS_ALL = [
  { label: '房态看板', icon: 'calendar_view_day', path: '/room-board', menu: 'menu.rooms.board' },
  {
    label: '房务任务',
    icon: 'cleaning_services',
    path: '/c6-housekeeping/housekeeping',
    menu: 'menu.rooms.hk',
  },
  {
    label: '库存预售',
    icon: 'inventory_2',
    path: '/c5-frontdesk/smart-inventory',
    menu: 'menu.rooms.inventory',
  },
  {
    label: '设备设施',
    icon: 'precision_manufacturing',
    path: '/c8-assets/inventory-2',
    menu: 'menu.rooms.assets',
  },
  {
    label: '房务报表',
    icon: 'monitoring',
    path: '/c6-housekeeping/reports',
    menu: 'menu.rooms.hk_reports',
  },
]

const TABS = computed(() => filterByMenu(TABS_ALL))

const TASK_PATHS = [
  '/c6-housekeeping/housekeeping',
  '/c6-housekeeping/room-board',
  '/c6-housekeeping/in-stay-guest-request-management',
  '/c6-housekeeping/staffing',
]

const REPORT_PATHS = ['/c6-housekeeping/reports']

const ASSET_PATHS = ['/c8-assets']

function normalize(p: string) {
  return (p || '').replace(/\/+$/, '') || '/'
}

function isActive(tabPath: string) {
  const cur = normalize(route.path)
  if (tabPath === '/room-board') return cur === '/room-board'
  if (tabPath === '/c5-frontdesk/smart-inventory') {
    return cur === '/c5-frontdesk/smart-inventory'
  }
  if (tabPath === '/c6-housekeeping/housekeeping') {
    return TASK_PATHS.some((p) => cur === normalize(p))
  }
  if (tabPath === '/c8-assets/inventory-2') {
    return ASSET_PATHS.some((p) => cur === normalize(p) || cur.startsWith(normalize(p) + '/'))
  }
  if (tabPath === '/c6-housekeeping/reports') {
    return REPORT_PATHS.some((p) => cur === normalize(p))
  }
  return cur === normalize(tabPath)
}

const activePath = computed(() => TABS.value.find((t) => isActive(t.path))?.path || '')
</script>

<template>
  <nav class="room-ops-nav" :aria-label="t('房务与房态')">
    <button
      v-for="tab in TABS"
      :key="tab.path"
      type="button"
      class="tab"
      :class="{ on: activePath === tab.path }"
      @click="router.push(tab.path)"
    >
      <span class="material-symbols-outlined">{{ tab.icon }}</span>
      {{ t(tab.label) }}
    </button>
  </nav>
</template>

<style scoped>
.room-ops-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px;
  background: #f3f4f6;
  border-radius: 12px;
  margin-bottom: 24px;
}
.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  border-radius: 9px;
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #5b616e;
  cursor: pointer;
}
.tab .material-symbols-outlined {
  font-size: 18px;
}
.tab:hover {
  background: #fff;
  color: #1f2329;
}
.tab.on {
  background: #1f2329;
  color: #fff;
}
</style>
