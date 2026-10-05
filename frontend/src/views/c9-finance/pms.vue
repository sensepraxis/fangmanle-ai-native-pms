<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 原「全自动结算与对账中心」已并入 AI财务对账，保留路由兼容跳转 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
onMounted(() => {
  router.replace('/c9-finance/smart-reconciliation')
})
</script>

<template>
  <div class="page text-on-surface-variant text-sm p-6">{{ t('正在跳转到对账中心…') }}</div>
</template>
