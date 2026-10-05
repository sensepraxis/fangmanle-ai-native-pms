<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 公域投放 — 复用智能投放配置能力，去掉渠道品牌壳 */
import { onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const rows = ref<any[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const r = await api.demo('geofencing')
    rows.value = Array.isArray(r) ? r : []
  } catch {
    rows.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="font-display-lg text-display-lg text-on-surface mb-2">{{ t('公域投放') }}</h1>
      <p class="font-body-md text-body-md text-on-surface-variant">
        {{ t('投放策略、商圈定向与预算配置（不绑定单一平台品牌页）') }}
      </p>
    </div>

    <p v-if="loading" class="text-on-surface-variant text-sm">{{ t('加载中…') }}</p>
    <div
      v-else-if="!rows.length"
      class="rounded-xl border border-outline-variant bg-surface-container-lowest p-8 text-on-surface-variant text-sm"
    >
      {{ t('暂无投放方案数据。可在系统配置对接广告账户后在此管理预算与定向。') }}
    </div>
    <div v-else class="grid grid-cols-12 gap-4">
      <div
        v-for="(item, i) in rows"
        :key="i"
        :class="
          item.cls ||
          'col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant p-6'
        "
        v-html="item.raw"
      />
    </div>
  </div>
</template>
