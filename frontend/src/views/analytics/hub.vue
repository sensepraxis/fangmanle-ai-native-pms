<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 数据洞察 · 二级入口见 AnalyticsOpsNav
 * 专题洞察（渠道/订单/归因）| 利润优化 | AI 问数
 */
import { ref, provide, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import OrderMonitor from '../c5-frontdesk/order-monitor.vue'
import ChannelInsight from '../c5-frontdesk/ai-new.vue'
import OrderAttribution from '../c5-frontdesk/order-attribution.vue'
import ProfitOptimizationAi from '../c9-finance/profit-optimization-ai.vue'
import AnalyticsOpsNav from '../../components/AnalyticsOpsNav.vue'

const route = useRoute()
const router = useRouter()
const aiBundle = ref<any>(null)
provide('analyticsAiBundle', aiBundle)

type MainTab = 'insights' | 'profit'
type InsightSection = 'channel' | 'health' | 'attribution'

const mainTab = ref<MainTab>('insights')
const insightSection = ref<InsightSection>('channel')

const INSIGHT_TABS: { key: InsightSection; label: string; icon: string }[] = [
  { key: 'channel', label: t('渠道洞察'), icon: 'storefront' },
  { key: 'health', label: t('订单健康'), icon: 'health_and_safety' },
  { key: 'attribution', label: t('营销归因'), icon: 'route' },
]

const PAGE_TITLES: Record<string, string> = {
  channel: t('全渠道订单洞察'),
  health: t('订单异常与流失预警'),
  attribution: t('订单渠道归因分析'),
  profit: t('智能利润优化建议'),
}

const pageTitle = computed(() => {
  if (mainTab.value === 'profit') return PAGE_TITLES.profit
  return PAGE_TITLES[insightSection.value] || PAGE_TITLES.channel
})

function parseTab(q: Record<string, unknown>): MainTab {
  const t = String(q.tab || 'insights')
  if (t === 'profit') return 'profit'
  return 'insights'
}

function parseSection(q: Record<string, unknown>): InsightSection {
  const s = String(q.section || 'channel')
  if (s === 'health' || s === 'attribution' || s === 'channel') return s
  return 'channel'
}

function syncFromRoute() {
  const raw = String(route.query.tab || '')
  // 旧「诊断总览」入口统一落到专题洞察
  if (!raw || raw === 'overview') {
    router.replace({
      path: '/analytics',
      query: { tab: 'insights', section: String(route.query.section || 'channel') },
    })
    return
  }
  mainTab.value = parseTab(route.query as Record<string, unknown>)
  insightSection.value = parseSection(route.query as Record<string, unknown>)
}

function setInsightSection(section: InsightSection) {
  insightSection.value = section
  router.replace({ path: '/analytics', query: { tab: 'insights', section } })
}

watch(() => route.query, syncFromRoute, { deep: true })
onMounted(syncFromRoute)
</script>

<template>
  <div class="page analytics-hub">
    <AnalyticsOpsNav />

    <div v-show="mainTab === 'insights'" class="tab-body">
      <nav class="sub-tabs" :aria-label="t('专题洞察')">
        <button
          v-for="s in INSIGHT_TABS"
          :key="s.key"
          type="button"
          class="sub-tab"
          :class="{ on: insightSection === s.key }"
          @click="setInsightSection(s.key)"
        >
          <span class="material-symbols-outlined">{{ s.icon }}</span>
          {{ s.label }}
        </button>
      </nav>

      <header class="page-head">
        <h1>{{ pageTitle }}</h1>
      </header>

      <section class="panel insight-panel">
        <ChannelInsight v-if="insightSection === 'channel'" embedded />
        <OrderMonitor v-else-if="insightSection === 'health'" embedded />
        <OrderAttribution v-else embedded />
      </section>
    </div>

    <div v-show="mainTab === 'profit'" class="tab-body">
      <header class="page-head">
        <h1>{{ pageTitle }}</h1>
      </header>
      <section class="panel profit-panel">
        <ProfitOptimizationAi embedded show-high-value-orders />
      </section>
    </div>
  </div>
</template>

<style scoped>
.analytics-hub {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding-bottom: 2.5rem;
}

.tab-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel {
  background: #fffbfe;
  border: 1px solid #cac4d0;
  border-radius: 0.85rem;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}

.sub-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 2px;
  margin-bottom: 24px;
}
.sub-tab {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: transparent;
  padding: 10px 14px 11px;
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.sub-tab .material-symbols-outlined {
  font-size: 17px;
}
.sub-tab:hover {
  color: #1f2329;
}
.sub-tab.on {
  color: #1f2329;
  border-bottom-color: #1f2329;
}

.insight-panel,
.profit-panel {
  padding: 0.85rem 1rem 1.1rem;
}

.insight-panel :deep(.is-embedded.page),
.profit-panel :deep(.is-embedded.page) {
  padding: 0;
  margin: 0;
  max-width: none;
  background: transparent;
}
.insight-panel :deep(.is-embedded .page-title-block),
.profit-panel :deep(.is-embedded .page-title-block) {
  display: none !important;
}
</style>
