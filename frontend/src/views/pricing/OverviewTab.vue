<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { fmt } from '../../lib/ui'
import BoardAiPanel from '../../components/BoardAiPanel.vue'

const data = ref<any>(null)
async function load() {
  data.value = await api.paOverview(hotelStore.hotelId)
}
onMounted(load)
watch(() => hotelStore.hotelId, load)

function deltaClass(n: number) {
  if (n > 0) return 'up'
  if (n < 0) return 'down'
  return 'flat'
}
</script>

<template>
  <div v-if="data">
    <div class="note-bar card-clean">
      <span class="material-symbols-outlined">rule</span>
      {{ data.price_basis_note }}
    </div>

    <div class="kpi-grid" style="grid-template-columns: repeat(5, minmax(0, 1fr))">
      <div v-for="k in data.kpis" :key="k.key" class="kpi">
        <div class="k">{{ k.label }}</div>
        <div class="v">
          <template v-if="k.unit === '¥'">{{ fmt(k.value) }}</template>
          <template v-else>{{ k.value }}{{ k.unit }}</template>
        </div>
        <div class="d" :class="deltaClass(k.delta)">{{ k.hint }}</div>
      </div>
    </div>

    <div class="grid2">
      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('7 日价格走势') }}</span>
          <span class="sub">{{ t('本店 vs 竞品中位 vs OTA 最低') }}</span>
        </div>
        <div class="bars">
          <div v-for="tag in data.trend_7d" :key="tag.date" class="bar-col">
            <div class="stack">
              <div
                class="b self"
                :style="{ height: Math.max(8, tag.self / 8) + 'px' }"
                :title="`${t('本店')} ${tag.self}`"
              />
              <div class="b comp" :style="{ height: Math.max(8, tag.comp_median / 8) + 'px' }" />
              <div class="b ota" :style="{ height: Math.max(8, tag.ota_min / 8) + 'px' }" />
            </div>
            <div class="dlabel">{{ tag.date.slice(5) }}</div>
          </div>
        </div>
        <div class="legend">
          <span><i class="c self" />{{ t('本店') }}</span>
          <span><i class="c comp" />{{ t('竞品中位') }}</span>
          <span><i class="c ota" />{{ t('OTA 最低') }}</span>
        </div>
      </div>

      <div class="card-clean">
        <div class="card-head">
          <span>{{ t('今日竞品排名') }}</span>
        </div>
        <table class="data">
          <thead>
            <tr>
              <th>#</th>
              <th>{{ t('酒店') }}</th>
              <th class="num">{{ t('客付挂牌价') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in data.ranking_today" :key="i" :class="{ self: r.is_self }">
              <td>{{ i + 1 }}</td>
              <td>{{ r.name }}{{ r.is_self ? '（本店）' : '' }}</td>
              <td class="num">{{ fmt(r.price) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="ai-card" style="margin-top: 14px">
      <div class="ttl">
        <span class="material-symbols-outlined">auto_awesome</span>{{ t('规则提示（只读）') }}
      </div>
      <ul>
        <li v-for="(h, i) in data.ai_hints" :key="i">{{ h }}</li>
      </ul>
    </div>
    <BoardAiPanel
      kind="pricing_compare"
      :title="t('竞品价格 AI 解读')"
      idle=""
      :run-label="t('生成比价解读')"
      :rerun-label="t('重新解读')"
      :wait-label="t('正在对比本店与竞品挂牌价…')"
      :payload="{ days: 7 }"
    />
  </div>
  <div v-else class="empty">{{ t('加载中…') }}</div>
</template>

<style scoped>
.note-bar {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 14px;
  margin-bottom: 14px;
  font-size: 12.5px;
  color: var(--on-surface-variant);
  line-height: 1.5;
}
.note-bar .material-symbols-outlined {
  font-size: 20px;
  color: var(--primary);
}
.sub {
  font-size: 11px;
  color: var(--on-surface-variant);
  font-weight: 400;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
@media (max-width: 900px) {
  .grid2 {
    grid-template-columns: 1fr;
  }
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
}
.bars {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  height: 140px;
  padding: 12px 16px 8px;
}
.bar-col {
  flex: 1;
  text-align: center;
}
.stack {
  display: flex;
  gap: 3px;
  align-items: flex-end;
  justify-content: center;
  height: 110px;
}
.b {
  width: 8px;
  border-radius: 3px 3px 0 0;
}
.b.self {
  background: var(--primary);
}
.b.comp {
  background: #d97706;
}
.b.ota {
  background: var(--outline);
}
.dlabel {
  font-size: 10px;
  color: var(--on-surface-variant);
  margin-top: 4px;
}
.legend {
  font-size: 11px;
  color: var(--on-surface-variant);
  padding: 0 16px 12px;
  display: flex;
  gap: 14px;
}
.legend .c {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  margin-right: 4px;
}
.legend .c.self {
  background: var(--primary);
}
.legend .c.comp {
  background: #d97706;
}
.legend .c.ota {
  background: var(--outline);
}
tr.self td {
  font-weight: 650;
  color: var(--primary);
}
.empty {
  color: var(--on-surface-variant);
  padding: 28px;
  text-align: center;
}
</style>
