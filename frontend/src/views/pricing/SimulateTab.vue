<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const data = ref<any>(null)
const scenario = ref('balanced')

async function load() {
  data.value = await api.paSimulate(hotelStore.hotelId, scenario.value)
}
onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(scenario, load)
</script>

<template>
  <div v-if="data">
    <div class="banner card-clean">
      <span class="material-symbols-outlined">science</span>
      <div>
        <b>{{ t('价格策略仿真') }}</b
        >：{{ data.window }} {{ t('用') }} AI {{ t('建议价') }} vs {{ t('实际价回测。')
        }}{{ data.note }}
      </div>
    </div>

    <div class="scenarios">
      <button
        v-for="s in data.scenarios"
        :key="s.key"
        type="button"
        class="sc card-clean"
        :class="{ on: scenario === s.key }"
        @click="scenario = s.key"
      >
        <div class="name">{{ s.label }}</div>
        <div class="meta">{{ t('窗口') }} {{ s.horizon }}</div>
        <div class="m">RevPAR +{{ s.revpar_lift }}%</div>
        <div class="m">OCC {{ s.occ_lift >= 0 ? '+' : '' }}{{ s.occ_lift }}%</div>
        <div class="m">{{ t('净收入') }} +{{ s.net_lift }}%</div>
      </button>
    </div>

    <div class="card-clean">
      <div class="card-head">
        <span>{{ t('敏感度分析') }}</span>
      </div>
      <table class="data">
        <thead>
          <tr>
            <th>{{ t('因子') }}</th>
            <th>{{ t('对 RevPAR 影响') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(s, i) in data.sensitivity" :key="i">
            <td>{{ s.factor }}</td>
            <td>{{ s.revpar_impact }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 14px;
  margin-bottom: 14px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--on-surface-variant);
}
.banner .material-symbols-outlined {
  color: var(--tertiary);
  font-size: 22px;
}
.scenarios {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
@media (max-width: 800px) {
  .scenarios {
    grid-template-columns: 1fr;
  }
}
.sc {
  text-align: left;
  padding: 14px 16px;
  cursor: pointer;
  background: var(--surface-lowest);
}
.sc.on {
  border-color: var(--tertiary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--tertiary) 18%, transparent);
}
.name {
  font-weight: 650;
  margin-bottom: 4px;
  color: var(--on-surface);
}
.meta {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-bottom: 8px;
}
.m {
  font-size: 13px;
  color: var(--on-surface);
  line-height: 1.55;
}
</style>
