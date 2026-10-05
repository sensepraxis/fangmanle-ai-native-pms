<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 客户域动线导航：
 * 看客户（档案/分群）· 认身份 · 客群与洞察 · 口碑关怀（住中服务，≠客群）
 */
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

type FlowBtn = { label: string; icon: string; path: string; accent?: boolean; ghost?: boolean }
type JourneyKey = 'list' | 'oneid' | 'cohort' | 'care'

const journeys: Record<JourneyKey, { label: string; hint: string; steps: FlowBtn[] }> = {
  list: {
    label: '看客户',
    hint: '攻略：全景列表 · 客群列表 — 360（画像 / LTV / 轨迹）',
    steps: [
      { label: '全景列表', icon: 'groups', path: '/b-data/global-guest-directory', accent: true },
      { label: '客群运营', icon: 'filter_alt', path: '/b-data/cohort-list' },
    ],
  },
  oneid: {
    label: '认身份',
    hint: '动线2 · 归并台 → 冲突队列 → 归并审核 → 资产确认',
    steps: [
      { label: 'OneID台', icon: 'fingerprint', path: '/b-data/one-id', accent: true },
      { label: '冲突队列', icon: 'warning', path: '/b-data/ai-high-confidence-94' },
      { label: '归并审核', icon: 'fact_check', path: '/b-data/one-id-resolution' },
      {
        label: '资产确认',
        icon: 'account_balance_wallet',
        path: '/b-data/consolidated-asset-confirmation',
      },
      { label: '回客户列表', icon: 'groups', path: '/b-data/global-guest-directory', ghost: true },
    ],
  },
  cohort: {
    label: '客群与洞察',
    hint: '运营看客群列表 · 配置与洞察进枢纽',
    steps: [
      { label: '客群运营', icon: 'filter_alt', path: '/b-data/cohort-list', accent: true },
      { label: '配置客群', icon: 'hub', path: '/b-data/tag-ecosystem-overview' },
    ],
  },
  care: {
    label: '口碑关怀',
    hint: '动线G · 画像策略 → 客户画像（住中关怀）',
    steps: [
      {
        label: '画像策略',
        icon: 'psychology',
        path: '/c4-reputation/auto-awesome-ai-verified',
        accent: true,
      },
      { label: '回全景列表', icon: 'groups', path: '/b-data/global-guest-directory', ghost: true },
    ],
  },
}

const PATH_JOURNEY: { prefix: string; key: JourneyKey }[] = [
  { prefix: '/b-data/global-guest-directory', key: 'list' },
  { prefix: '/b-data/cohort-list', key: 'cohort' },
  { prefix: '/guests/', key: 'list' },
  { prefix: '/b-data/one-id-audit', key: 'oneid' },
  { prefix: '/b-data/guest-360-workspace', key: 'list' },
  { prefix: '/b-data/f-ngm-nl-pms', key: 'list' },
  { prefix: '/b-data/one-id-resolution', key: 'oneid' },
  { prefix: '/b-data/one-id', key: 'oneid' },
  { prefix: '/b-data/ai-high-confidence-94', key: 'oneid' },
  { prefix: '/b-data/consolidated-asset-confirmation', key: 'oneid' },
  { prefix: '/b-data/data-source-lineage', key: 'oneid' },
  { prefix: '/b-data/tag-ecosystem-overview', key: 'cohort' },
  { prefix: '/b-data/tag-management', key: 'cohort' },
  { prefix: '/b-data/master-tag-library', key: 'cohort' },
  { prefix: '/b-data/semantic-tag-rules', key: 'cohort' },
  { prefix: '/b-data/guest-segmentation', key: 'cohort' },
  { prefix: '/b-data/top-50', key: 'cohort' },
  { prefix: '/b-data/ota', key: 'cohort' },
  { prefix: '/c4-reputation/auto-awesome-ai-verified', key: 'care' },
  { prefix: '/c4-reputation/room-board', key: 'care' },
  { prefix: '/a-ai-core/ai-negative-review-warning', key: 'care' },
  { prefix: '/a-ai-core/automated-appeal-workspace', key: 'care' },
  { prefix: '/a-ai-core/ai-reputation-ai', key: 'care' },
]

function detectJourney(path: string): JourneyKey | null {
  const hit = [...PATH_JOURNEY]
    .sort((a, b) => b.prefix.length - a.prefix.length)
    .find(
      (x) =>
        path === x.prefix || path.startsWith(x.prefix + '/') || path.startsWith(x.prefix + '?'),
    )
  if (hit) return hit.key
  if (path.startsWith('/b-data/global-guest-directory')) return 'list'
  return null
}

const activeKey = ref<JourneyKey>('list')
const HIDE_FLOW_PREFIXES = [
  // 首页用「3 张入口卡」承担导航，不再叠 Tab 条，避免与卡片重复
  '/b-data/global-guest-directory',
  // 客群列表 / 客群枢纽及子能力页：用页内返回或 TagDomainSubnav，不再叠 4 Tab
  '/b-data/cohort-list',
  '/b-data/tag-ecosystem-overview',
  '/b-data/tag-management',
  '/b-data/master-tag-library',
  '/b-data/semantic-tag-rules',
  '/b-data/guest-segmentation',
  '/b-data/top-50',
  // 客户 360 画像：页内自带导航，不再叠全局动线条
  '/guests/',
  '/b-data/ltv',
  '/b-data/life-time-value',
  '/b-data/data-source-lineage',
  // 单客归并审计：从 360 进入，用页内返回条
  '/b-data/one-id-audit',
  // OneID 四步 Wizard 自带精简步骤条，不再叠全局动线
  '/b-data/one-id',
  '/b-data/ai-high-confidence-94',
  '/b-data/one-id-resolution',
  '/b-data/consolidated-asset-confirmation',
  '/b-data/ai-auto-awesome',
  '/c4-reputation/ltv',
  '/c4-reputation/roi',
  '/c4-reputation/download',
  '/c4-reputation/one-id-tracing-path-to-purchase',
]
const show = computed(() => {
  const p = route.path
  if (HIDE_FLOW_PREFIXES.some((x) => p === x || p.startsWith(x + '/') || p.startsWith(x + '?')))
    return false
  return detectJourney(p) != null
})

watch(
  () => route.fullPath,
  () => {
    const d = detectJourney(route.path)
    if (d) activeKey.value = d
  },
  { immediate: true },
)

const current = computed(() => journeys[activeKey.value])

function normalize(p: string) {
  return (p || '').split('?')[0].replace(/\/+$/, '') || '/'
}

function isCurrent(path: string) {
  return normalize(route.path) === normalize(path)
}

const stepBtns = computed(() => current.value.steps.filter((b) => !isCurrent(b.path)))

const showStepRow = computed(() => stepBtns.value.length > 0)

const showHint = computed(
  () => !!current.value.hint && route.path !== '/b-data/consolidated-asset-confirmation',
)

function go(path: string) {
  router.push(path)
}

function switchJourney(k: JourneyKey) {
  activeKey.value = k
  const first = journeys[k].steps.find((s) => s.accent) || journeys[k].steps[0]
  if (first && !isCurrent(first.path)) router.push(first.path)
}
</script>

<template>
  <div v-if="show" class="crm-flow">
    <div class="crm-flow-top" :class="{ 'no-btns': !showStepRow }">
      <div class="tabs">
        <button
          v-for="(j, k) in journeys"
          :key="k"
          type="button"
          class="tab"
          :class="{ on: activeKey === k }"
          @click="switchJourney(k as JourneyKey)"
        >
          {{ t(j.label) }}
        </button>
      </div>
      <p v-if="showHint" class="hint">
        {{ t(current.hint) }}
      </p>
    </div>
    <div v-if="showStepRow" class="btns">
      <button
        v-for="b in stepBtns"
        :key="b.path + b.label"
        type="button"
        class="flow-btn"
        :class="{ accent: b.accent, ghost: b.ghost }"
        @click="go(b.path)"
      >
        <span class="material-symbols-outlined">{{ b.icon }}</span>
        {{ t(b.label) }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.crm-flow {
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 30;
  padding: 10px 20px 8px;
  background: var(--surface-container-lowest, #fff);
  border-bottom: 1px solid var(--outline-variant, #e2e5eb);
}
.crm-flow-top {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin-bottom: 8px;
}
.crm-flow-top.no-btns {
  margin-bottom: 0;
}
.tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.tab {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  color: var(--on-surface-variant);
  cursor: pointer;
}
.tab:hover {
  background: var(--surface-container-low);
  color: var(--on-surface);
}
.tab.on {
  background: color-mix(in srgb, var(--primary) 12%, transparent);
  color: var(--primary);
  border-color: color-mix(in srgb, var(--primary) 28%, transparent);
}
.hint {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  flex: 1;
  min-width: 160px;
}
.btns {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.flow-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 11px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  color: var(--on-surface);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.flow-btn .material-symbols-outlined {
  font-size: 16px;
}
.flow-btn:hover {
  background: var(--surface-container-low);
}
.flow-btn.accent {
  background: var(--primary);
  color: var(--on-primary);
  border-color: transparent;
}
.flow-btn.ghost {
  color: var(--on-surface-variant);
  font-weight: 500;
}
</style>
