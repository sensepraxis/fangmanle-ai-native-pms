<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 旧入口：AI 智能派工控制台 → 已并入房务任务 · 今日任务 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
onMounted(() => {
  router.replace('/c6-housekeeping/housekeeping')
})
</script>

<template>
  <div class="page">
    <p>{{ t('正在跳转至房务任务 · 今日任务…') }}</p>
  </div>
</template>
