<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/** 经营分析子页：返回经营分析枢纽 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ANALYTICS_PATH, ANALYTICS_CARDS } from '../lib/analyticsNav'

withDefaults(
  defineProps<{
    hideLinks?: boolean
  }>(),
  { hideLinks: false },
)

const route = useRoute()
const router = useRouter()

const showBack = computed(() => route.path !== ANALYTICS_PATH)

const siblings = computed(() => ANALYTICS_CARDS.filter((c) => c.path !== route.path))
</script>

<template>
  <div class="an-nav">
    <button v-if="showBack" type="button" class="back-btn" @click="router.push(ANALYTICS_PATH)">
      <span class="material-symbols-outlined">arrow_back</span>
      {{ t('经营分析') }}
    </button>
    <div v-if="!hideLinks && siblings.length" class="links">
      <button
        v-for="c in siblings"
        :key="c.key"
        type="button"
        class="chip"
        :class="{ muted: c.muted }"
        @click="router.push(c.path)"
      >
        <span class="material-symbols-outlined">{{ c.icon }}</span>
        {{ t(c.title) }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.an-nav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
}
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant, #e2e5eb);
  background: var(--surface-container-lowest, #fff);
  font-size: 13px;
  cursor: pointer;
}
.back-btn:hover {
  background: var(--surface-container-low, #f3f4f6);
}
.back-btn .material-symbols-outlined {
  font-size: 18px;
}
.links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #e9d5ff;
  background: #faf5ff;
  font-size: 12px;
  color: #6d28d9;
  cursor: pointer;
}
.chip:hover {
  background: #f3e8ff;
}
.chip.muted {
  border-style: dashed;
  color: #64748b;
  background: #f8fafc;
  border-color: #e2e8f0;
}
.chip .material-symbols-outlined {
  font-size: 16px;
}
</style>
