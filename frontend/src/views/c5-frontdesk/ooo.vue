<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 旧「状态登记」已下线 → 系统配置 · 房间档案 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
onMounted(() => {
  router.replace('/a-ai-core/room-master')
})
</script>

<template>
  <p style="padding: 24px; color: var(--on-surface-variant)">{{ t('正在跳转到「房间档案」…') }}</p>
</template>
