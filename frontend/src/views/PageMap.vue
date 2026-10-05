<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { computed } from 'vue'
import { pageManifest } from '../pages.manifest'

// 按域分组
const groups = computed(() => {
  const m: Record<string, { route: string; title: string }[]> = {}
  for (const p of pageManifest) {
    if (!m[p.domain]) m[p.domain] = []
    m[p.domain].push({ route: p.route, title: p.title })
  }
  return Object.entries(m).map(([domain, pages]) => ({ domain, pages }))
})
const total = pageManifest.length
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t('页面地图') }}</h1>
      <p>
        {{ t('原型') }} 188 {{ t('页全量接入系统 · 共') }} {{ total }}
        {{ t('个可跳转页面（按业务域分组）') }}
      </p>
    </div>

    <div class="map-grid">
      <div v-for="g in groups" :key="g.domain" class="card-clean card-pad map-card">
        <div class="card-head" style="border: 0; padding: 0 0 10px; margin-bottom: 8px">
          <span class="domain-tag">{{ g.domain }}</span>
          <span class="num" style="color: var(--on-surface-variant); font-size: 12px">{{
            g.pages.length
          }}</span>
        </div>
        <div class="map-list">
          <RouterLink v-for="p in g.pages" :key="p.route" :to="p.route" class="map-item">
            <span class="material-symbols-outlined">chevron_right</span>
            {{ p.title }}</RouterLink
          >
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.map-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.map-card {
  display: flex;
  flex-direction: column;
}
.domain-tag {
  font-size: 14px;
  font-weight: 700;
  color: var(--primary);
}
.map-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 320px;
  overflow: auto;
}
.map-item {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 12.5px;
  color: var(--on-surface-variant);
  text-decoration: none;
  cursor: pointer;
  transition:
    background 0.1s,
    color 0.1s;
}
.map-item .material-symbols-outlined {
  font-size: 16px;
  color: var(--outline);
}
.map-item:hover {
  background: var(--surface-low);
  color: var(--primary);
}
.map-item:hover .material-symbols-outlined {
  color: var(--primary);
}
</style>
