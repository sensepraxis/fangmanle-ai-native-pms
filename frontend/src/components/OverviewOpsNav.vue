<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 经营总览 · 二级入口
 * 价格助手（事前决策） / 营收预测（事前预测） / 经营看板
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { forecastReturnLocation, loadAskDataCache } from '../lib/askDataBridge'
import { hotelStore } from '../store/hotel'
import { filterByMenu } from '../store/rbac'

const route = useRoute()
const router = useRouter()

const TABS_ALL = [
  { label: '经营看板', icon: 'dashboard', path: '/overview', menu: 'menu.overview.dashboard' },
  { label: '价格助手', icon: 'auto_graph', path: '/pricing', menu: 'menu.overview.pricing' },
  {
    label: '营收预测',
    icon: 'trending_up',
    path: '/c9-finance/revenue-forecast',
    menu: 'menu.overview.forecast',
  },
]

const TABS = computed(() => filterByMenu(TABS_ALL))

function normalize(p: string) {
  return (p || '').replace(/\/+$/, '') || '/'
}

function isActive(tabPath: string) {
  const cur = normalize(route.path)
  if (tabPath === '/') return cur === '/'
  if (tabPath === '/pricing') {
    return cur === '/pricing' || cur.startsWith('/pricing/')
  }
  if (tabPath === '/c9-finance/revenue-forecast') {
    return cur === '/c9-finance/revenue-forecast'
  }
  return cur === normalize(tabPath)
}

const activePath = computed(() => TABS.value.find((t) => isActive(t.path))?.path || '')

function goTab(tabPath: string) {
  if (tabPath === '/c9-finance/revenue-forecast') {
    const fromAsk = route.query.from === 'forecast'
    const onPricing = route.path === '/pricing' || route.path.startsWith('/pricing/')
    if (fromAsk || (onPricing && loadAskDataCache(hotelStore.hotelId))) {
      router.push(forecastReturnLocation())
      return
    }
  }
  router.push(tabPath)
}
</script>

<template>
  <nav class="overview-ops-nav" :aria-label="t('经营总览')">
    <button
      v-for="tab in TABS"
      :key="tab.path"
      type="button"
      class="tab"
      :class="{ on: activePath === tab.path }"
      @click="goTab(tab.path)"
    >
      <span class="material-symbols-outlined">{{ tab.icon }}</span>
      {{ t(tab.label) }}
    </button>
  </nav>
</template>

<style scoped>
.overview-ops-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  width: 100%;
  padding: 4px;
  background: #f3f4f6;
  border-radius: 12px;
  margin-bottom: 24px;
  box-sizing: border-box;
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
