<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 旧路由兼容：订单渠道归因已迁至订单增强层 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
onMounted(() => {
  router.replace('/analytics/marketing-attribution/path')
})
</script>

<template>
  <div class="page p-8 text-on-surface-variant text-body-md">
    {{ t('正在跳转到订单渠道归因分析…') }}
  </div>
</template>
