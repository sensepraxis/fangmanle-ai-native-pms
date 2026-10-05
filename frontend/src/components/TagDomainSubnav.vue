<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 兼容旧子页导航（标签管理已合并为双 Tab）
 */
import { useRouter } from 'vue-router'

const router = useRouter()

function goBack() {
  router.push('/b-data/tag-management')
}
</script>

<template>
  <div class="tag-subnav">
    <button type="button" class="back" @click="goBack">
      <span class="material-symbols-outlined text-[16px]">arrow_back</span>
      {{ t('标签管理') }}
    </button>
  </div>
</template>

<style scoped>
.tag-subnav {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 24px;
  font-size: 13px;
}
.back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  padding: 0;
  color: var(--primary);
  font-weight: 650;
  cursor: pointer;
}
.back:hover {
  opacity: 0.85;
}
</style>
