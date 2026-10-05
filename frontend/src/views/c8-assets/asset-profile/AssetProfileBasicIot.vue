<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

defineProps<{
  assetNo: string
  statusLabel: string
  assetInfo: {
    location: string
    inbound: string
    supplier: string
    dept: string
  }
  iotMetrics: Array<{
    label: string
    value: string
    unit: string
    iconBg: string
    iconFg: string
    icon: string
    primary: boolean
  }>
}>()
</script>

<template>
  <div id="section-basic" class="top-bento">
    <div class="card-clean info-card">
      <div class="thumb">
        <span class="material-symbols-outlined">tv</span>
      </div>
      <div class="info-body">
        <div class="info-top">
          <h2>{{ t('资产基本信息') }}</h2>
          <span class="status-pill">{{ statusLabel }}</span>
        </div>
        <div class="info-grid">
          <div>
            <p class="lbl">{{ t('设备编号') }}</p>
            <p class="val num">{{ assetNo }}</p>
          </div>
          <div>
            <p class="lbl">{{ t('当前位置') }}</p>
            <p class="val">{{ assetInfo.location }}</p>
          </div>
          <div>
            <p class="lbl">{{ t('入库日期') }}</p>
            <p class="val num">{{ assetInfo.inbound }}</p>
          </div>
          <div>
            <p class="lbl">{{ t('供应商') }}</p>
            <p class="val">{{ assetInfo.supplier }}</p>
          </div>
          <div>
            <p class="lbl">{{ t('责任部门') }}</p>
            <p class="val">{{ assetInfo.dept }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="card-clean iot-card">
      <h2>
        {{ t('运行数据看板') }}
        <span class="live">
          <span class="ping" />
          <span class="dot" />
        </span>
      </h2>
      <div class="iot-list">
        <div v-for="m in iotMetrics" :key="m.label" class="iot-row" :class="{ primary: m.primary }">
          <div class="iot-left">
            <div class="iot-ico" :style="{ background: m.iconBg, color: m.iconFg }">
              <span class="material-symbols-outlined">{{ m.icon }}</span>
            </div>
            <span class="iot-lbl">{{ m.label }}</span>
          </div>
          <span class="num iot-val" :class="{ hi: m.primary }">
            {{ m.value }}<span v-if="m.unit" class="unit">{{ m.unit }}</span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
