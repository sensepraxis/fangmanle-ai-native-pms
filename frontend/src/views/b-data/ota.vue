<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 兼容旧链接：全渠道行为轨迹已并入客户 360 */
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  const id = route.query.guestId
  if (id) {
    router.replace(`/guests/${id}?focus=trail`)
    return
  }
  router.replace('/b-data/global-guest-directory')
})
</script>

<template>
  <div class="page muted text-sm p-6">{{ t('正在跳转到客户 360 · 行为轨迹…') }}</div>
</template>
