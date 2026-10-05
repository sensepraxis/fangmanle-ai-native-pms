<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 设备设施子导航 —— 资产清单 / 维修追踪（挂在「房务与房态 → 设备设施」下）
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const chainBtns = [
  { label: '资产清单', icon: 'inventory_2', path: '/c8-assets/inventory-2', accent: true },
  { label: '维修追踪', icon: 'build', path: '/c8-assets/tracking' },
]

function normalize(p: string) {
  return (p || '').replace(/\/+$/, '') || '/'
}

function isCurrent(path: string) {
  const cur = normalize(route.path)
  if (path === '/c8-assets/inventory-2') {
    return cur === path || cur === '/c8-assets' || cur.startsWith('/c8-assets/assets/')
  }
  return cur === normalize(path)
}

const visibleBtns = computed(() => chainBtns.filter((b) => !isCurrent(b.path)))
</script>

<template>
  <nav v-if="visibleBtns.length" class="assets-flow" :aria-label="t('设备设施导航')">
    <div class="btns">
      <button
        v-for="b in visibleBtns"
        :key="b.path"
        type="button"
        class="flow-btn"
        :class="{ accent: b.accent }"
        @click="router.push(b.path)"
      >
        <span class="material-symbols-outlined">{{ b.icon }}</span>
        {{ t(b.label) }}
      </button>
    </div>
  </nav>
</template>

<style scoped>
.assets-flow {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--outline-variant);
}
.btns {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.flow-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest, #fff);
  font-size: 13px;
  cursor: pointer;
  color: var(--on-surface);
}
.flow-btn .material-symbols-outlined {
  font-size: 18px;
}
.flow-btn:hover {
  background: var(--surface-container-low);
}
.flow-btn.accent {
  font-weight: 600;
  border-color: var(--primary);
  color: var(--primary);
}
</style>
