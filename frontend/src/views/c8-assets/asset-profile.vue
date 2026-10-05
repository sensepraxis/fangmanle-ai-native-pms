<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 资产画像 —— 薄壳：组合 asset-profile 子模块
 * 样式与结构对齐 GuestDetail（客户 360）
 */
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ASSETS_EMPTY } from '../../lib/assetsEmpty'
import { hotelStore } from '../../store/hotel'
import RoomOpsNav from '../../components/RoomOpsNav.vue'
import { useAssetProfileLoad } from './asset-profile/useAssetProfileLoad'
import { useAssetProfileDerived } from './asset-profile/useAssetProfileDerived'
import { useAssetAiStream } from './asset-profile/useAssetAiStream'
import AssetProfileHero from './asset-profile/AssetProfileHero.vue'
import AssetProfileBasicIot from './asset-profile/AssetProfileBasicIot.vue'
import AssetProfileAiNext from './asset-profile/AssetProfileAiNext.vue'
import AssetProfileValueRisk from './asset-profile/AssetProfileValueRisk.vue'
import AssetProfileTimeline from './asset-profile/AssetProfileTimeline.vue'
import AssetProfileWorkOrders from './asset-profile/AssetProfileWorkOrders.vue'

const route = useRoute()
const router = useRouter()

const assetId = computed(() => Number(route.params.id))

/** load 早于 ai 声明；onBeforeLoad 经持有对象在 setup 末尾接线 */
const aiBridge = { reset: () => {} }

const loader = useAssetProfileLoad({
  assetId,
  onBeforeLoad: () => aiBridge.reset(),
})

const {
  loading,
  empty,
  raw,
  timeline,
  workOrders,
  woDetail,
  woDetailLoading,
  selectedWoId,
  alerts,
  assetEvents,
  woDetailOpen,
  woProgressSteps,
  woProgressStep,
  woSummary,
  closeWorkOrderDetail,
  openWorkOrderDetail,
  load,
} = loader

const derived = useAssetProfileDerived({
  raw,
  alerts,
  assetEvents,
  workOrders,
})

const {
  a,
  assetNo,
  statusLabel,
  location,
  assetInfo,
  iotMetrics,
  metrics,
  failureRiskBreakdown,
  verdict,
  needsRepair,
  aiConf,
  fallbackNextAction,
  openWorkOrders,
  maintCount,
  perfRadar,
  costFingerprint,
  depChart,
  failurePct,
  failureLabel,
  needleDeg,
} = derived

const ai = useAssetAiStream({
  raw,
  fallbackNextAction,
  aiConf,
  verdict,
  needsRepair,
})

const {
  aiNextAction,
  aiNextLoading,
  nextAction,
  aiActionType,
  aiSourceLabel,
  showAiActionButtons,
  stopAiStream,
  resetAiState,
  triggerAiNextAction,
} = ai

aiBridge.reset = resetAiState

function goLossAnalysis() {
  router.push('/c8-assets/loss-analysis-replacement-strategy')
}
function goList() {
  router.push('/c8-assets/inventory-2')
}
function goWorkOrder(create = false, woId?: string) {
  const base = `/c8-assets/tracking?asset_id=${assetId.value}`
  if (create) {
    router.push(`${base}&action=repair`)
  } else if (woId) {
    router.push(`${base}&wo_id=${encodeURIComponent(woId)}`)
  } else {
    router.push(base)
  }
}
function goProcure() {
  router.push(`/c8-assets/inventory-2?action=register&replace_asset_id=${assetId.value}`)
}
function onTimelineAction(action: string) {
  if (action === t('生成预防性工单')) goWorkOrder(true)
}
function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(load)
onUnmounted(stopAiStream)
watch(() => [hotelStore.hotelId, route.params.id], load)
</script>

<template>
  <div class="page asset-profile-page">
    <RoomOpsNav />
    <div v-if="loading" class="text-on-surface-variant text-sm">{{ t('加载中…') }}</div>
    <p v-else-if="empty" class="empty-hint">{{ ASSETS_EMPTY }}</p>

    <template v-else>
      <header class="hero">
        <AssetProfileHero
          :a="a"
          :asset-no="assetNo"
          :status-label="statusLabel"
          :location="location"
          :maint-count="maintCount"
          :needs-repair="needsRepair"
          :verdict-tone="verdict.tone"
          :open-work-orders-count="openWorkOrders.length"
          :metrics-health="metrics.health"
          @go-list="goList"
          @go-loss-analysis="goLossAnalysis"
          @scroll-to="scrollTo"
          @go-work-order="goWorkOrder(false)"
        />
        <AssetProfileBasicIot
          :asset-no="assetNo"
          :status-label="statusLabel"
          :asset-info="assetInfo"
          :iot-metrics="iotMetrics"
        />
      </header>

      <AssetProfileAiNext
        :ai-next-action="aiNextAction"
        :ai-next-loading="aiNextLoading"
        :ai-source-label="aiSourceLabel"
        :next-action="nextAction"
        :show-ai-action-buttons="showAiActionButtons"
        :ai-action-type="aiActionType"
        :open-work-orders-count="openWorkOrders.length"
        :perf-radar="perfRadar"
        :cost-fingerprint="costFingerprint"
        @trigger-ai="triggerAiNextAction"
        @go-work-order-create="goWorkOrder(true)"
        @go-procure="goProcure"
        @scroll-to-value="scrollTo('section-value')"
      />

      <AssetProfileValueRisk
        :dep-chart="depChart"
        :metrics="metrics"
        :failure-pct="failurePct"
        :failure-label="failureLabel"
        :needle-deg="needleDeg"
        :failure-risk-breakdown="failureRiskBreakdown"
      />

      <AssetProfileTimeline
        :needs-repair="needsRepair"
        :alerts="alerts"
        :insight="a.insight"
        :timeline="timeline"
        @go-work-order-create="goWorkOrder(true)"
        @timeline-action="onTimelineAction"
      />

      <AssetProfileWorkOrders
        :work-orders="workOrders"
        :wo-summary="woSummary"
        :selected-wo-id="selectedWoId"
        :wo-detail-open="woDetailOpen"
        :wo-detail-loading="woDetailLoading"
        :wo-detail="woDetail"
        :wo-progress-steps="woProgressSteps"
        :wo-progress-step="woProgressStep"
        :asset-name="a.name"
        :asset-no="assetNo"
        @go-work-order-create="goWorkOrder(true)"
        @open-detail="openWorkOrderDetail"
        @close-detail="closeWorkOrderDetail"
      />
    </template>
  </div>
</template>

<style>
@import './asset-profile/asset-profile-shared.css';
</style>
