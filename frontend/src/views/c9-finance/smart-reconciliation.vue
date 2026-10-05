<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * AI 财务对账中心
 * 薄壳：FinanceOpsNav + 工具栏/KPI + 子组件编排
 */
import { ref } from 'vue'
import FinanceOpsNav from '../../components/FinanceOpsNav.vue'
import FinanceAiPlanDrawer from '../../components/FinanceAiPlanDrawer.vue'
import type { BatchRow } from './smart-reconciliation/types'
import { money } from './smart-reconciliation/types'
import { useReconFilters } from './smart-reconciliation/useReconFilters'
import { useReconBatches } from './smart-reconciliation/useReconBatches'
import ReconBatchTable from './smart-reconciliation/ReconBatchTable.vue'
import ReconDetailDrawer from './smart-reconciliation/ReconDetailDrawer.vue'
import ReconCloseModal from './smart-reconciliation/ReconCloseModal.vue'
import ReconSyncModal from './smart-reconciliation/ReconSyncModal.vue'

const batches = ref<BatchRow[]>([])

const {
  dim,
  tab,
  channelFilter,
  dateLabel,
  filtered,
  dateOptions,
  channelOptions,
  counts,
  setDim,
} = useReconFilters(batches)

const {
  dutyName,
  loading,
  selectedId,
  checked,
  closeModal,
  syncConfirm,
  exportOpen,
  aiOpen,
  overrideNote,
  showOverride,
  aiLoading,
  selected,
  kpi,
  abnormalBatches,
  canCloseBatch,
  load,
  selectRow,
  jumpToAbnormal,
  runAiExplain,
  toggleCheck,
  selectAllAbnormal,
  doExport,
  forceSync,
  confirmSync,
  runAiMatch,
  acceptAi,
  markRefund,
  overrideAi,
  saveOverride,
  openCloseModal,
  confirmClose,
} = useReconBatches(batches, { dateLabel, channelFilter, tab, filtered })
</script>

<template>
  <div class="page recon-page">
    <FinanceOpsNav />

    <div class="page-head">
      <h1 class="font-display-lg text-display-lg text-on-background">{{ t('财务对账') }}</h1>
      <button v-if="commercialEnabled()" type="button" class="btn soft" @click="aiOpen = true">
        {{ t('AI 安排') }}
      </button>
    </div>

    <div class="page-tools">
      <div class="dim-switch">
        <button type="button" :class="{ on: dim === 'batch' }" @click="setDim('batch')">
          {{ t('批次日') }}
        </button>
        <button type="button" :class="{ on: dim === 'accrual' }" @click="setDim('accrual')">
          {{ t('应收日') }}
        </button>
        <button type="button" :class="{ on: dim === 'settle' }" @click="setDim('settle')">
          {{ t('到账日') }}
        </button>
      </div>
      <select class="tb-input" v-model="dateLabel">
        <option v-for="d in dateOptions" :key="d" :value="d">{{ d }}</option>
      </select>
      <select class="tb-input" v-model="channelFilter">
        <option value="all">{{ t('全部渠道') }}</option>
        <option v-for="c in channelOptions" :key="c" :value="c">{{ c }}</option>
      </select>
      <button type="button" class="btn" @click="forceSync">{{ t('强制同步') }}</button>
      <div class="export-wrap">
        <button type="button" class="btn" @click="exportOpen = !exportOpen">
          {{ t('导出报告 ▼') }}
        </button>
        <div v-if="exportOpen" class="export-menu">
          <button type="button" @click="doExport('all')">{{ t('全批次明细') }}</button>
          <button type="button" @click="doExport('abnormal')">{{ t('仅异常批次') }}</button>
          <button type="button" @click="doExport('closed')">{{ t('仅关账批次') }}</button>
        </div>
      </div>
      <button type="button" class="btn primary ml-auto" @click="openCloseModal">
        {{ t('批次关账 →') }}
      </button>
    </div>

    <FinanceAiPlanDrawer v-model:open="aiOpen" scene="recon" @confirmed="load" />

    <div class="kpi-row">
      <div class="kpi">
        <div class="kpi-label">{{ t('待对账总额') }} <span class="tag">T+1</span></div>
        <div class="kpi-num">{{ money(kpi.pendingTotal) }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">
          {{ t('异常批次') }} <span class="tag bad">{{ t('待处理') }}</span>
        </div>
        <div class="kpi-num">
          {{ kpi.abnormalCount }}
          <small class="err">{{ t('涉及') }} {{ money(kpi.abnormalAmount) }}</small>
        </div>
      </div>
    </div>

    <div class="alert">
      <b>{{ t('差异拆分口径') }}</b
      >{{
        t(
          '：优先按系统配置 OTA 佣金（如携程 12%、飞猪 8%）拆出平台佣金，其余再拆 T+1 / 退款在途 / 净差额。差异 ≠ 损失。',
        )
      }}
    </div>

    <div class="split">
      <ReconBatchTable
        :filtered="filtered"
        :counts="counts"
        :tab="tab"
        :loading="loading"
        :dim="dim"
        :checked="checked"
        :selected-id="selectedId"
        @update:tab="tab = $event"
        @select-all-abnormal="selectAllAbnormal"
        @run-ai-match="runAiMatch"
        @select-row="selectRow"
        @toggle-check="toggleCheck"
      />

      <ReconDetailDrawer
        :selected="selected"
        :duty-name="dutyName"
        :ai-loading="aiLoading"
        :show-override="showOverride"
        :override-note="overrideNote"
        @update:override-note="overrideNote = $event"
        @run-ai-explain="runAiExplain"
        @override-ai="overrideAi"
        @mark-refund="markRefund"
        @accept-ai="acceptAi"
        @save-override="saveOverride"
      />
    </div>

    <div class="archive">
      <span class="ttl">{{ t('对账历史归档') }}</span>
      <span class="day on">{{ dateLabel || t('今日') }} · {{ t('进行中') }}</span>
      <span class="day">{{ t('前一日 · 已关账') }}</span>
      <span class="day">{{ t('前二日 · 已关账') }}</span>
    </div>

    <ReconSyncModal :open="syncConfirm" @close="syncConfirm = false" @confirm="confirmSync" />

    <ReconCloseModal
      :open="closeModal"
      :date-label="dateLabel"
      :duty-name="dutyName"
      :can-close-batch="canCloseBatch"
      :kpi="kpi"
      :counts="counts"
      :abnormal-batches="abnormalBatches"
      @close="closeModal = false"
      @confirm="confirmClose"
      @jump-to-abnormal="jumpToAbnormal"
    />
  </div>
</template>

<style>
@import './smart-reconciliation/recon-shared.css';
</style>
