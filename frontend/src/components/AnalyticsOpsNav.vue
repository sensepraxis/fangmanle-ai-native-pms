<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 数据洞察 · 二级入口
 * 专题洞察 / 利润优化 / AI 问数
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { filterByMenu } from '../store/rbac'

const route = useRoute()
const router = useRouter()

type Tab = {
  key: string
  label: string
  icon: string
  path: string
  query?: Record<string, string>
  menu: string
}

const TABS_ALL: Tab[] = [
  {
    key: 'insights',
    label: '专题洞察',
    icon: 'insights',
    path: '/analytics',
    query: { tab: 'insights' },
    menu: 'menu.analytics.insights',
  },
  {
    key: 'profit',
    label: '利润优化',
    icon: 'trending_up',
    path: '/analytics',
    query: { tab: 'profit' },
    menu: 'menu.analytics.profit',
  },
  { key: 'assistant', label: 'AI 问数', icon: 'smart_toy', path: '/ai', menu: 'menu.analytics.ai' },
]

const TABS = computed(() => filterByMenu(TABS_ALL))

function normalize(p: string) {
  return (p || '').replace(/\/+$/, '') || '/'
}

function isActive(tab: Tab) {
  const cur = normalize(route.path)
  if (tab.key === 'assistant') return cur === '/ai'
  if (cur !== '/analytics') return false
  const qTab = String(route.query.tab || 'insights')
  if (tab.key === 'insights') return qTab === 'insights' || qTab === 'overview'
  if (tab.key === 'profit') return qTab === 'profit'
  return false
}

const activeKey = computed(() => TABS.value.find((t) => isActive(t))?.key || '')

function go(tab: Tab) {
  if (tab.path === '/ai') {
    router.push('/ai')
    return
  }
  const query: Record<string, string> = { ...(tab.query || {}) }
  if (tab.key === 'insights' && !query.section) {
    const cur = String(route.query.section || 'channel')
    query.section = ['channel', 'health', 'attribution'].includes(cur) ? cur : 'channel'
  }
  router.push({ path: '/analytics', query })
}
</script>

<template>
  <nav class="analytics-ops-nav" :aria-label="t('数据洞察')">
    <button
      v-for="tab in TABS"
      :key="tab.key"
      type="button"
      class="tab"
      :class="{ on: activeKey === tab.key }"
      @click="go(tab)"
    >
      <span class="material-symbols-outlined">{{ tab.icon }}</span>
      {{ t(tab.label) }}
    </button>
  </nav>
</template>

<style scoped>
.analytics-ops-nav {
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
