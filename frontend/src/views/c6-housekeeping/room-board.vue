<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 旧「任务看板」独立页 → 任务看板列表 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
onMounted(() => {
  router.replace('/c6-housekeeping/housekeeping')
})
</script>

<template>
  <div class="page">
    <p>{{ t('正在跳转至任务看板…') }}</p>
  </div>
</template>
