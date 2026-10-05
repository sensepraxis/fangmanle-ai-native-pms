<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 旧入口：换班交接工作台 → 财务管理 · 交接班 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
onMounted(() => {
  router.replace({ path: '/c9-finance/shift-handover/takeover' })
})
</script>

<template>
  <div class="page">
    <p>{{ t('正在跳转至财务管理 · 交接班…') }}</p>
  </div>
</template>
