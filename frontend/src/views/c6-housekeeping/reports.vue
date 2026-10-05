<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 房务报表 —— 今日运营 + 人效复盘
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RoomOpsNav from '../../components/RoomOpsNav.vue'
import PerformanceReportPanel from './PerformanceReportPanel.vue'
import LaborEfficiencyReportPanel from './LaborEfficiencyReportPanel.vue'

const route = useRoute()
const router = useRouter()

const tab = computed(() => {
  const t = String(route.query.tab || 'labor')
  // labor = 今日运营；perf = 人效复盘（兼容旧 query）
  return t === 'perf' ? 'perf' : 'labor'
})

function setTab(t: 'perf' | 'labor') {
  router.replace({ path: '/c6-housekeeping/reports', query: { tab: t } })
}
</script>

<template>
  <div class="page reports-page">
    <RoomOpsNav />
    <header class="head">
      <div>
        <h1>{{ t('房务报表') }}</h1>
      </div>
    </header>

    <div class="tabs" role="tablist">
      <button
        type="button"
        role="tab"
        class="tab"
        :class="{ on: tab === 'labor' }"
        :aria-selected="tab === 'labor'"
        @click="setTab('labor')"
      >
        {{ t('今日运营') }}
      </button>
      <button
        type="button"
        role="tab"
        class="tab"
        :class="{ on: tab === 'perf' }"
        :aria-selected="tab === 'perf'"
        @click="setTab('perf')"
      >
        {{ t('人效复盘') }}
      </button>
    </div>

    <LaborEfficiencyReportPanel v-if="tab === 'labor'" />
    <PerformanceReportPanel v-else />
  </div>
</template>

<style scoped>
.reports-page {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.head {
  margin-bottom: 4px;
}
.head h1 {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 800;
}
.head p {
  margin: 0;
  color: #5b616e;
  font-size: 13px;
}
.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 14px;
}
.tab {
  border: none;
  background: transparent;
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 700;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.tab.on {
  color: #1a73e8;
  border-bottom-color: #1a73e8;
}
</style>
