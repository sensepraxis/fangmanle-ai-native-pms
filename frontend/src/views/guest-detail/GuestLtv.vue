<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

defineProps<{
  estLtv: number
  ltvChart: any
  g: any
  stayCount: number
  churnPct: number
  needleDeg: number
  riskLabel: { text: string; cls: string; tip: string; badge: string }
  fmtInt: (n: number) => string
}>()
</script>

<template>
  <section id="section-ltv" class="sec-block">
    <div class="sec-head">
      <div>
        <h2 class="sec-title">
          <span class="material-symbols-outlined text-primary">trending_up</span>
          {{ t('客户终身价值') }}
        </h2>
      </div>
      <div class="flex items-center gap-2 text-xs text-on-surface-variant">
        <span class="legend-dot bg-primary" />{{ t('当前客户') }}
        <span class="legend-dot bg-outline-variant opacity-70" />{{ t('同期群平均') }}
      </div>
    </div>

    <div class="ltv-grid">
      <div class="card ltv-chart-card">
        <div class="ltv-chart-h">
          <h3 class="card-h !mb-0 flex items-center gap-2">
            <span class="material-symbols-outlined text-primary text-[20px]">show_chart</span>
            {{ t('累积价值曲线') }}
          </h3>
          <div class="text-right">
            <div class="text-xl font-bold text-primary font-mono">{{ fmtInt(estLtv) }}</div>
            <div class="text-xs text-on-surface-variant">{{ t('预估 LTV') }}</div>
          </div>
        </div>
        <div class="chart-wrap">
          <div class="chart-ylab">
            <span v-for="lb in ltvChart.labels" :key="lb">{{ lb }}</span>
          </div>
          <div class="chart-grid">
            <svg
              class="absolute inset-0 w-full h-full overflow-visible"
              preserveAspectRatio="none"
              viewBox="0 0 100 100"
            >
              <path
                :d="ltvChart.cohortPath"
                fill="none"
                stroke="#c1c6d6"
                stroke-dasharray="4 4"
                stroke-width="2"
                vector-effect="non-scaling-stroke"
              />
              <path :d="ltvChart.areaPath" fill="rgba(0,91,191,0.08)" stroke="none" />
              <path
                :d="ltvChart.guestPath"
                fill="none"
                stroke="#005bbf"
                stroke-width="3"
                vector-effect="non-scaling-stroke"
              />
              <path
                :d="ltvChart.projPath"
                fill="none"
                stroke="#a84fce"
                stroke-dasharray="4 4"
                stroke-width="2"
                vector-effect="non-scaling-stroke"
              />
              <circle
                v-for="(p, i) in ltvChart.points"
                :key="i"
                :cx="p.x"
                :cy="p.y"
                :r="i === ltvChart.points.length - 1 ? 3.2 : 2"
                :fill="i === ltvChart.points.length - 1 ? '#ffffff' : '#005bbf'"
                :stroke="i === ltvChart.points.length - 1 ? '#005bbf' : 'none'"
                :stroke-width="i === ltvChart.points.length - 1 ? 2 : 0"
                vector-effect="non-scaling-stroke"
              />
            </svg>
            <div class="chart-tip" :style="{ left: ltvChart.tipX + '%', top: ltvChart.tipY + '%' }">
              <div class="text-xs text-on-surface-variant mb-0.5">{{ t('当前累计') }}</div>
              <div class="font-bold text-primary">{{ fmtInt(Number(g.ltv || 0)) }}</div>
              <div class="text-[11px] text-tertiary mt-0.5">
                {{ stayCount }} {{ t('次入住 · 高于同期群') }}
              </div>
            </div>
          </div>
          <div class="chart-xlab">
            <span>{{ t('第1年') }}</span
            ><span>{{ t('第2年') }}</span
            ><span>{{ t('第3年') }}</span
            ><span>{{ t('第4年') }}</span
            ><span>{{ t('第5年(预估)') }}</span>
          </div>
        </div>
      </div>

      <div class="ltv-side">
        <div class="card churn-card">
          <h3 class="card-h flex items-center gap-2">
            <span class="material-symbols-outlined text-secondary text-[20px]">data_usage</span>
            {{ t('流失预警') }}
          </h3>
          <div class="churn-gauge">
            <div class="gauge-arc">
              <div class="gauge-ring" />
              <div
                class="gauge-fill"
                :class="churnPct >= 50 ? 'is-high' : churnPct >= 30 ? 'is-mid' : 'is-low'"
              />
              <div
                class="gauge-needle"
                :style="{ transform: `translateX(-50%) rotate(${needleDeg}deg)` }"
              />
              <div class="gauge-hub" />
            </div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold" :class="riskLabel.cls">{{ churnPct }}%</div>
            <span
              class="inline-block mt-1 text-xs font-bold px-2.5 py-0.5 rounded-full border"
              :class="[riskLabel.cls, riskLabel.badge]"
            >
              {{ riskLabel.text }}</span
            >
            <p class="m-0 mt-2 text-xs text-on-surface-variant">{{ riskLabel.tip }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
@import './guest-detail-shared.css';
</style>
