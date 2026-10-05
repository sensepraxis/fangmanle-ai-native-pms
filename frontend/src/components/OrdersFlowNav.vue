<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 子页仅保留「返回订单中心」
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = withDefaults(
  defineProps<{
    variant?: 'hub' | 'minimal'
    mode?: string
    hideLinks?: boolean
  }>(),
  { hideLinks: false },
)

const route = useRoute()
const router = useRouter()

const showBack = computed(() => {
  if (props.hideLinks) return false
  return route.path !== '/orders' && route.path !== '/c5-frontdesk/orders'
})
</script>

<template>
  <button v-if="showBack" type="button" class="back-btn" @click="router.push('/orders')">
    <span class="material-symbols-outlined">arrow_back</span>
    {{ t('订单中心') }}
  </button>
</template>

<style scoped>
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant, #e2e5eb);
  background: var(--surface-container-lowest, #fff);
  font-size: 13px;
  cursor: pointer;
}
.back-btn:hover {
  background: var(--surface-container-low, #f3f4f6);
}
.back-btn .material-symbols-outlined {
  font-size: 18px;
}
</style>
