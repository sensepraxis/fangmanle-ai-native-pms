<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

defineProps<{ open: boolean }>()

const emit = defineEmits<{
  close: []
  confirm: []
}>()
</script>

<template>
  <div v-if="open" class="modal" @click.self="emit('close')">
    <div class="modal-card">
      <div class="modal-h">
        <div class="ttl">{{ t('强制同步三方数据') }}</div>
        <div class="sub">
          {{ t('将按库内订单与收款记录重建对账批次，未关账差异会按最新金额重新计算') }}
        </div>
      </div>
      <div class="modal-f">
        <button type="button" class="btn" @click="emit('close')">{{ t('取消') }}</button>
        <button type="button" class="btn primary" @click="emit('confirm')">
          {{ t('确认同步') }}
        </button>
      </div>
    </div>
  </div>
</template>
