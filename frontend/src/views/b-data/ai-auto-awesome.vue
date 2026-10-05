<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 兼容旧链接：内容已内嵌到客户 360，带 guestId 时回跳画像页。
 */
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  const id = route.query.guestId
  if (id) {
    router.replace(`/guests/${id}`)
    return
  }
  router.replace('/b-data/global-guest-directory')
})
</script>

<template>
  <div class="page muted text-sm p-6">{{ t('正在跳转到客户 360…') }}</div>
</template>
