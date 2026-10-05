<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

defineProps<{
  nextAction: { conf: number; text: string }
  psychRadar: { axes: any[]; pts: any[]; poly: string }
  fingerprint: {
    ttv: number
    rows: { name: string; amount: number; pct: number; color: string; tip: string }[]
    insightTitle: string
    insightBody: string
  }
  fmtInt: (n: number) => string
}>()

const emit = defineEmits<{
  care: []
}>()
</script>

<template>
  <section class="pref-section">
    <div class="ai-next-proto">
      <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div class="flex items-start gap-4 min-w-0">
          <div class="ai-next-ico">
            <span class="material-symbols-outlined text-[24px]">auto_awesome</span>
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              <h3 class="m-0 text-base font-bold">{{ t('AI 下一步行动建议') }}</h3>
              <span class="conf">{{ t('置信度') }} {{ nextAction.conf }}%</span>
            </div>
            <p class="m-0 text-sm text-on-surface-variant leading-relaxed max-w-3xl">
              {{ nextAction.text }}
            </p>
          </div>
        </div>
        <div class="flex gap-2 shrink-0 w-full md:w-auto">
          <button type="button" class="btn-outline flex-1 md:flex-none">{{ t('忽略建议') }}</button>
          <button
            type="button"
            class="btn-primary flex-1 md:flex-none inline-flex items-center justify-center gap-1"
            @click="emit('care')"
          >
            <span class="material-symbols-outlined text-[18px]">send</span>
            {{ t('一键配置营销策略') }}
          </button>
        </div>
      </div>
    </div>

    <div class="pref-grid">
      <div class="card pref-radar-card">
        <h3 class="card-h flex items-center gap-2">
          <span class="material-symbols-outlined text-secondary text-[20px]">psychology</span>
          {{ t('心理特征雷达') }}
        </h3>
        <div class="radar-box">
          <div class="radar-stage">
            <svg class="absolute inset-0 w-full h-full" viewBox="0 0 100 100">
              <polygon
                fill="none"
                points="50,10 90,30 90,70 50,90 10,70 10,30"
                stroke="#e1e3e4"
                stroke-width="0.5"
              />
              <polygon
                fill="none"
                points="50,25 75,40 75,60 50,75 25,60 25,40"
                stroke="#e1e3e4"
                stroke-width="0.5"
              />
              <polygon
                fill="none"
                points="50,40 60,45 60,55 50,60 40,55 40,45"
                stroke="#e1e3e4"
                stroke-width="0.5"
              />
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="50" y2="10" />
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="90" y2="30" />
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="90" y2="70" />
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="50" y2="90" />
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="10" y2="70" />
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="10" y2="30" />
              <polygon
                :points="psychRadar.poly"
                fill="rgba(26, 115, 232, 0.2)"
                stroke="#005bbf"
                stroke-width="1.5"
              />
              <circle
                v-for="(p, i) in psychRadar.pts"
                :key="i"
                :cx="p.x"
                :cy="p.y"
                r="2"
                fill="#005bbf"
              />
            </svg>
            <div class="radar-lab top">
              {{ psychRadar.axes[0].label }} ({{ psychRadar.axes[0].score }})
            </div>
            <div class="radar-lab tr">
              {{ psychRadar.axes[1].label }} ({{ psychRadar.axes[1].score }})
            </div>
            <div class="radar-lab br">
              {{ psychRadar.axes[2].label }} ({{ psychRadar.axes[2].score }})
            </div>
            <div class="radar-lab bottom">
              {{ psychRadar.axes[3].label }} ({{ psychRadar.axes[3].score }})
            </div>
            <div class="radar-lab bl">
              {{ psychRadar.axes[4].label }} ({{ psychRadar.axes[4].score }})
            </div>
            <div class="radar-lab tl">
              {{ psychRadar.axes[5].label }} ({{ psychRadar.axes[5].score }})
            </div>
          </div>
        </div>
      </div>

      <div class="card pref-fp-card">
        <div class="flex justify-between items-start gap-3 mb-5 flex-wrap">
          <div>
            <h3 class="card-h flex items-center gap-2 !mb-1">
              <span class="material-symbols-outlined text-secondary text-[20px]">fingerprint</span>
              {{ t('消费指纹 (') }}TTV: {{ fmtInt(fingerprint.ttv) }})
            </h3>
          </div>
          <span class="fp-filter">{{ t('过去 12 个月') }}</span>
        </div>
        <div class="fp-rows">
          <div v-for="r in fingerprint.rows" :key="r.name">
            <div class="flex justify-between text-sm mb-1.5">
              <span class="font-medium flex items-center gap-2">
                <span class="w-3 h-3 rounded-sm inline-block" :class="r.color" />
                {{ r.name }}</span
              >
              <span class="text-on-surface-variant font-mono"
                >{{ fmtInt(r.amount) }} ({{ r.pct }}%)</span
              >
            </div>
            <div class="w-full bg-surface-container-high rounded-full h-2.5 overflow-hidden">
              <div class="h-2.5 rounded-full" :class="r.color" :style="{ width: r.pct + '%' }" />
            </div>
            <p v-if="r.tip" class="text-xs text-on-surface-variant mt-1 ml-5 m-0">{{ r.tip }}</p>
          </div>
        </div>
        <div class="fp-insight">
          <span class="material-symbols-outlined text-primary text-[20px] mt-0.5">info</span>
          <div>
            <p class="m-0 font-medium text-sm mb-1">{{ fingerprint.insightTitle }}</p>
            <p class="m-0 text-sm text-on-surface-variant">{{ fingerprint.insightBody }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
@import './guest-detail-shared.css';
</style>
