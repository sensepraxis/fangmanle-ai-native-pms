<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 经营总览 · 价格助手外壳（v2）
 * 顶部：价格助手配置 + 竞品对比面板；下接：定价日历（干活台）/ 价格趋势分析
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'
import { forecastReturnLocation } from '../lib/askDataBridge'
import { hotelStore } from '../store/hotel'
import { toast } from '../lib/ui'
import OverviewOpsNav from '../components/OverviewOpsNav.vue'
import CompetitorPanel from './pricing/CompetitorPanel.vue'
import EventsPanel from './pricing/EventsPanel.vue'
import ParamsPanel from './pricing/ParamsPanel.vue'
import CalendarTab from './pricing/CalendarTab.vue'
import TrendTab from './pricing/TrendTab.vue'

const router = useRouter()
const route = useRoute()

const TABS = [
  { id: 'calendar', label: '定价日历', icon: 'calendar_month' },
  { id: 'trend', label: '价格趋势分析', icon: 'show_chart' },
] as const

const tab = computed(() => {
  const raw = String(route.query.tab || 'calendar')
  // 旧 tab（建议/空间雷达/竞品对比矩阵等）→ 定价日历
  if (
    ['suggest', 'overview', 'alerts', 'simulate', 'competitor', 'radar', 'compare'].includes(raw)
  ) {
    return 'calendar'
  }
  return TABS.some((x) => x.id === raw) ? raw : 'calendar'
})

const config = ref<any>(null)
const refreshKey = ref(0)
const bannerDismissed = ref(false)

const fromForecast = computed(() => route.query.from === 'forecast')
const contextAction = computed(() => String(route.query.action || '').trim())
const contextDimension = computed(() => String(route.query.dimension || '').trim())
const contextEvidence = computed(() => String(route.query.evidence || '').trim())
const contextImpact = computed(() => String(route.query.impact || '').trim())

const showCompBanner = computed(
  () => !bannerDismissed.value && config.value && Number(config.value.comp_count || 0) === 0,
)

async function loadConfig() {
  config.value = await api.paConfig(hotelStore.hotelId)
}

onMounted(loadConfig)
watch(() => hotelStore.hotelId, loadConfig)

function setTab(id: string) {
  router.replace({ path: '/pricing', query: { ...route.query, tab: id } })
}

function backToForecast() {
  router.push(forecastReturnLocation())
}

function dismissContext() {
  const {
    from: _f,
    action: _a,
    dimension: _d,
    evidence: _e,
    impact: _i,
    severity: _s,
    ...rest
  } = route.query
  router.replace({ path: '/pricing', query: { ...rest, tab: tab.value } })
}

function onConfigChange(cfg: any) {
  config.value = cfg
  refreshKey.value += 1
}

async function onParamsSaved(cfg: any) {
  config.value = cfg
  try {
    await api.paGenerate(hotelStore.hotelId, { days: 14, force: true })
    toast(t('参数已保存 · 建议已重算'))
  } catch {
    toast(t('参数已保存'))
  }
  refreshKey.value += 1
}
</script>

<template>
  <div class="page pa-page">
    <OverviewOpsNav />

    <div v-if="fromForecast" class="from-forecast card-clean">
      <div class="from-main">
        <div class="from-kicker">
          <span class="material-symbols-outlined">auto_awesome</span>
          {{ t('来自营收预测 · 智能问数') }}
        </div>
        <div class="from-title">
          {{
            contextAction
              ? t('建议动作：{action}', { action: contextAction })
              : t('请在此确认调价建议')
          }}
        </div>
        <div v-if="contextDimension || contextEvidence || contextImpact" class="from-meta">
          <span v-if="contextDimension">{{ t('诊断：{d}', { d: contextDimension }) }}</span>
          <span v-if="contextImpact">{{ t('影响 {n}', { n: contextImpact }) }}</span>
          <span v-if="contextEvidence">{{ contextEvidence }}</span>
        </div>
        <p class="from-hint">{{ t('处理完可返回营收预测。价格助手绝不自动改价。') }}</p>
      </div>
      <div class="from-actions">
        <button type="button" class="btn btn-primary" @click="backToForecast">
          {{ t('返回营收预测') }}
        </button>
        <button type="button" class="btn btn-ghost" @click="dismissContext">
          {{ t('知道了') }}
        </button>
      </div>
    </div>

    <div class="page-actions">
      <div class="page-head" style="margin: 0">
        <h1>{{ t('价格助手') }}</h1>
      </div>
    </div>

    <div v-if="showCompBanner" class="soft-banner card-clean">
      <span class="material-symbols-outlined">travel_explore</span>
      <div>
        {{ t('点竞品面板「编辑」手工添加对标酒店并录价，可解锁竞品对标与穿透分析。') }}
        <b>{{ t('不阻断任何操作') }}</b
        >{{ t('——无竞品时仍可使用内部基准定价。') }}
      </div>
      <button type="button" class="btn btn-ghost" @click="bannerDismissed = true">
        {{ t('稍后') }}
      </button>
    </div>

    <div class="pa-panels">
      <ParamsPanel :config="config" @saved="onParamsSaved" />
      <EventsPanel :config="config" @changed="refreshKey += 1" />
      <CompetitorPanel
        :config="config"
        @config-change="onConfigChange"
        @changed="refreshKey += 1"
      />
    </div>

    <nav class="pa-subnav" :aria-label="t('价格助手子模块')">
      <button
        v-for="item in TABS"
        :key="item.id"
        type="button"
        class="subtab"
        :class="{ on: tab === item.id }"
        @click="setTab(item.id)"
      >
        <span class="material-symbols-outlined">{{ item.icon }}</span>
        {{ t(item.label) }}
      </button>
    </nav>

    <div class="tab-body">
      <KeepAlive>
        <CalendarTab
          v-if="tab === 'calendar'"
          :key="'calendar-' + refreshKey"
          :config="config"
          :comp-on="!!config?.comp_compare_enabled"
        />
        <TrendTab
          v-else-if="tab === 'trend'"
          :key="'trend-' + refreshKey"
          :comp-on="!!config?.comp_compare_enabled"
        />
      </KeepAlive>
    </div>
  </div>
</template>

<style scoped>
.pa-page {
  padding-bottom: 2rem;
}
.from-forecast {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding: 14px 16px;
  background: linear-gradient(180deg, #f8faff, #fff);
}
.from-kicker {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--tertiary);
  margin-bottom: 4px;
}
.from-kicker .material-symbols-outlined {
  font-size: 16px;
}
.from-title {
  font-size: 15px;
  font-weight: 650;
  color: var(--on-surface);
  line-height: 1.4;
}
.from-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.from-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.from-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.pa-panels {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 4px;
}
.soft-banner {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 14px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--on-surface-variant);
  background: linear-gradient(180deg, #f5f3ff, #fff);
}
.soft-banner .material-symbols-outlined {
  color: var(--tertiary);
}
.soft-banner > div {
  flex: 1;
}
.pa-subnav {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin: 14px 0 18px;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 2px;
}
.subtab {
  border: none;
  background: transparent;
  padding: 10px 14px 11px;
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}
.subtab .material-symbols-outlined {
  font-size: 18px;
}
.subtab:hover {
  color: var(--on-surface);
}
.subtab.on {
  color: var(--primary);
  border-bottom-color: var(--primary);
}
</style>
