<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 兼容旧链接：归并审计已内联至 360 画像 OneID 框，自动跳转并展开
 */
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  const guestId = route.query.guestId
  if (guestId) {
    router.replace({ path: `/guests/${guestId}`, query: { oneid: 'open' } })
  } else {
    router.replace('/b-data/global-guest-directory')
  }
})
</script>

<template>
  <div class="page">
    <p class="muted">{{ t('正在跳转到 360 画像…') }}</p>
  </div>
</template>

<style scoped>
.page {
  padding: 24px;
}
.muted {
  color: var(--on-surface-variant);
  font-size: 14px;
}
</style>
