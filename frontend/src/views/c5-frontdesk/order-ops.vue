<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 旧「渠道运营台」入口 → 经营分析枢纽 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ANALYTICS_PATH } from '../../lib/analyticsNav'

const router = useRouter()
onMounted(() => {
  router.replace(ANALYTICS_PATH)
})
</script>

<template>
  <div class="page" style="padding: 40px; color: #9aa1ad; font-size: 13px">
    {{ t('正在前往经营分析…') }}
  </div>
</template>
