<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 即时客情预测已废弃，回流客群与洞察枢纽 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
onMounted(() => {
  router.replace('/b-data/tag-ecosystem-overview')
})
</script>

<template>
  <div class="page muted text-sm p-6">{{ t('正在返回客群与洞察…') }}</div>
</template>
