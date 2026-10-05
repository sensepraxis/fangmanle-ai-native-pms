<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'
import { localizeSeedText } from '../../../lib/localizeSeed'

defineProps<{
  a: any
  assetNo: string
  statusLabel: string
  location: string
  maintCount: number
  needsRepair: boolean
  verdictTone: string
  openWorkOrdersCount: number
  metricsHealth: number
}>()

const emit = defineEmits<{
  goList: []
  goLossAnalysis: []
  scrollTo: [id: string]
  goWorkOrder: []
}>()
</script>

<template>
  <div class="hero-top">
    <div class="avatar-wrap">
      <div class="avatar">
        {{ (localizeSeedText(a.name) || t('设')).replace(/^\d+\s*/, '').slice(0, 1) || 'A' }}
      </div>
      <span class="online" :class="{ warn: needsRepair }" />
    </div>
    <div class="hero-main">
      <div class="title-row">
        <div class="title-left">
          <h1 class="name">{{ localizeSeedText(a.name) }}</h1>
          <span class="vip">{{ statusLabel }}</span>
          <span class="ai-badge">{{ t('台账监测') }}</span>
        </div>
        <div class="hero-actions">
          <button type="button" class="btn-hero" @click="emit('goList')">
            {{ t('返回资产清单') }}
          </button>
          <button type="button" class="btn-hero" @click="emit('goLossAnalysis')">
            {{ t('店级报损分析') }}
          </button>
          <button type="button" class="btn-hero" @click="emit('scrollTo', 'section-value')">
            {{ t('资产价值') }}
          </button>
          <button type="button" class="btn-hero" @click="emit('scrollTo', 'section-basic')">
            {{ t('资产详情') }}
          </button>
        </div>
      </div>
      <p class="meta">
        {{ assetNo }}
        <span v-if="a.brand_model"> · {{ localizeSeedText(a.brand_model) }}</span>
        · {{ location }} · {{ t('{n} 次维保记录', { n: maintCount }) }}
      </p>
      <div class="tags">
        <span class="tag">{{ localizeSeedText(a.category) || t('设备') }}</span>
        <span v-if="a.dept" class="tag">{{ localizeSeedText(a.dept) }}</span>
        <span v-if="needsRepair" class="tag tag-risk">{{ t('需维修') }}</span>
        <span v-if="verdictTone === 'replace'" class="tag tag-hi">{{ t('建议更换') }}</span>
        <span v-if="openWorkOrdersCount" class="tag tag-ai">{{
          t('{n} 条开放工单', { n: openWorkOrdersCount })
        }}</span>
      </div>
    </div>
  </div>

  <div class="oneid-bar">
    <div class="oneid-left">
      <div class="oneid-ico" :title="t('资产编号')">
        <span class="material-symbols-outlined">qr_code_2</span>
      </div>
      <div class="oneid-text">
        <div class="oneid-title-row">
          <span class="oneid-k">{{ t('资产唯一编号') }}</span>
          <span class="oneid-id">{{ assetNo }}</span>
          <span class="oneid-ok">
            <span class="material-symbols-outlined text-[14px]">verified</span>
            {{ t('台账已核验') }}</span
          >
          <span class="oneid-conf">{{ t('健康分') }} {{ metricsHealth || '—' }}</span>
        </div>
        <div class="oneid-chips">
          <span class="oneid-chip">{{ localizeSeedText(a.category) || t('设备') }}</span>
          <span class="oneid-chip">{{ localizeSeedText(a.supplier) || t('供应商未登记') }}</span>
          <span v-if="a.warranty_until" class="oneid-chip">{{
            t('质保至 {date}', { date: a.warranty_until })
          }}</span>
        </div>
      </div>
    </div>
    <button type="button" class="btn-hero oneid-link" @click="emit('goWorkOrder')">
      {{ t('查看关联工单') }}
    </button>
  </div>
</template>
