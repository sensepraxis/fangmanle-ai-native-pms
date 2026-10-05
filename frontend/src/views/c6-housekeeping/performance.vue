<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 旧入口兼容：客房服务能效 → 房务报表 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
onMounted(() => {
  router.replace({ path: '/c6-housekeeping/reports', query: { tab: 'perf' } })
})
</script>

<template>
  <div class="page">
    <p>{{ t('正在跳转至房务报表…') }}</p>
  </div>
</template>
