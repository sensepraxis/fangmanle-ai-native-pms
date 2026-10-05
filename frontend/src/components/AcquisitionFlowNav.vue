<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 营销获客动线页头 CTA
 * main   = E 私域闭环主线（线索跟进，不含 PMS 内发帖）
 * douyin / geo / ota / ads = 渠道支线
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = withDefaults(
  defineProps<{
    mode?: 'main' | 'douyin' | 'geo' | 'ota' | 'ads'
    hint?: string
  }>(),
  { mode: 'main', hint: '' },
)

const route = useRoute()
const router = useRouter()

type FlowBtn = {
  label: string
  icon: string
  path: string
  accent?: boolean
  ghost?: boolean
}

const HUB = '/acquisition'
const LEADS = '/c3-acquisition/one-id'

const mainBtns: FlowBtn[] = [
  { label: t('作业台'), icon: 'home', path: HUB, ghost: true },
  { label: t('线索跟进'), icon: 'link', path: LEADS, accent: true },
  { label: t('私域漏斗'), icon: 'filter_alt', path: '/c3-acquisition/content-ai' },
  { label: t('全链路'), icon: 'route', path: '/c3-acquisition/flow' },
  {
    label: t('转预订'),
    icon: 'storefront',
    path: '/c3-acquisition/wecom-mini-program-direct-sales',
  },
  { label: t('获客ROI'), icon: 'monitoring', path: '/c4-reputation/roi', ghost: true },
]

const douyinBtns: FlowBtn[] = [
  { label: t('作业台'), icon: 'home', path: HUB, ghost: true },
  { label: t('线索跟进'), icon: 'link', path: LEADS, ghost: true },
  {
    label: t('抖音获客'),
    icon: 'smart_display',
    path: '/c3-acquisition/douyin-acquisition',
    accent: true,
  },
  { label: 'POI', icon: 'location_on', path: '/c3-acquisition/poi' },
  { label: t('达人合作'), icon: 'star', path: '/c3-acquisition/filter-list' },
  { label: t('实时出价'), icon: 'speed', path: '/c3-acquisition/auto-awesome-ai-active' },
  { label: t('全链路'), icon: 'route', path: '/c3-acquisition/flow', ghost: true },
]

const geoBtns: FlowBtn[] = [
  { label: t('作业台'), icon: 'home', path: HUB, ghost: true },
  { label: t('线索跟进'), icon: 'link', path: LEADS, ghost: true },
  { label: t('品牌植入'), icon: 'public', path: '/c3-acquisition/geo', accent: true },
  { label: t('AI引擎'), icon: 'auto_fix_high', path: '/c3-acquisition/ai-engine-optimization' },
  { label: t('地图曝光'), icon: 'map', path: '/c3-acquisition/5-2-4-geo' },
  { label: t('效果归因'), icon: 'query_stats', path: '/c3-acquisition/geo-attribution-roi' },
  { label: t('获客ROI'), icon: 'monitoring', path: '/c4-reputation/roi', ghost: true },
]

const otaBtns: FlowBtn[] = [
  { label: t('作业台'), icon: 'home', path: HUB, ghost: true },
  { label: t('线索跟进'), icon: 'link', path: LEADS, ghost: true },
  {
    label: t('商圈竞品'),
    icon: 'compare_arrows',
    path: '/c3-acquisition/competitor-set',
    ghost: true,
  },
  { label: t('流量商圈'), icon: 'travel_explore', path: '/c3-acquisition/ota' },
  { label: t('调价活动'), icon: 'local_offer', path: '/c3-acquisition/ota-2', accent: true },
  { label: t('转私域'), icon: 'swap_horiz', path: '/c3-acquisition/ota-3' },
  { label: t('全链路'), icon: 'route', path: '/c3-acquisition/flow', ghost: true },
  {
    label: t('转预订'),
    icon: 'storefront',
    path: '/c3-acquisition/wecom-mini-program-direct-sales',
    ghost: true,
  },
]

const adsBtns: FlowBtn[] = [
  { label: t('作业台'), icon: 'home', path: HUB, ghost: true },
  { label: t('线索跟进'), icon: 'link', path: LEADS, ghost: true },
  { label: t('投放配置'), icon: 'ads_click', path: '/c3-acquisition/geofencing', accent: true },
  { label: t('商圈竞品'), icon: 'compare_arrows', path: '/c3-acquisition/competitor-set' },
  {
    label: t('实时出价'),
    icon: 'speed',
    path: '/c3-acquisition/auto-awesome-ai-active',
    ghost: true,
  },
  { label: t('获客ROI'), icon: 'monitoring', path: '/c4-reputation/roi', ghost: true },
]

function normalize(p: string) {
  return (p || '').replace(/\/+$/, '') || '/'
}

function isCurrent(path: string) {
  return normalize(route.path) === normalize(path)
}

const modeBtns: Record<string, FlowBtn[]> = {
  main: mainBtns,
  douyin: douyinBtns,
  geo: geoBtns,
  ota: otaBtns,
  ads: adsBtns,
}

const visibleBtns = computed(() => {
  const list = modeBtns[props.mode] || mainBtns
  return list.filter((b) => !isCurrent(b.path))
})
</script>

<template>
  <div class="acq-flow">
    <p v-if="hint" class="hint">{{ hint }}</p>
    <div class="btns">
      <button
        v-for="b in visibleBtns"
        :key="b.path + b.label"
        type="button"
        class="flow-btn"
        :class="{ accent: b.accent, ghost: b.ghost }"
        @click="router.push(b.path)"
      >
        <span class="material-symbols-outlined">{{ b.icon }}</span>
        {{ t(b.label) }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.acq-flow {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}
.hint {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
}
.btns {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.flow-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant, #c9ced8);
  background: var(--surface-container-lowest, #fff);
  color: var(--on-surface, #1f2329);
  font-size: 13px;
  cursor: pointer;
}
.flow-btn .material-symbols-outlined {
  font-size: 16px;
}
.flow-btn:hover {
  background: var(--surface-container-low, #f3f4f6);
}
.flow-btn.accent {
  border-color: #1f2329;
  background: #1f2329;
  color: #fff;
  font-weight: 600;
}
.flow-btn.ghost {
  opacity: 0.85;
  border-style: solid;
}
</style>
