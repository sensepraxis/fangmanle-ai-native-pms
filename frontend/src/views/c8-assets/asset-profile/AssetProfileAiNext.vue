<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'
import { commercialEnabled } from '../../../lib/branding'
import { localizeAssetAiText } from '../../../lib/localizeSeed'

import { formatAiModelMeta } from '../../../lib/aiModelMeta'
import { fmtInt } from './useAssetProfileDerived'

defineProps<{
  aiNextAction: any
  aiNextLoading: boolean
  aiSourceLabel: string
  nextAction: { conf: number | null; text: string }
  showAiActionButtons: boolean
  aiActionType: string
  openWorkOrdersCount: number
  perfRadar: {
    poly: string
    pts: Array<{ x: number; y: number }>
    axes: Array<{ label: string; score: number }>
  }
  costFingerprint: {
    total: number
    rows: Array<{ name: string; amount: number; pct: number; color: string; tip: string }>
    insightTitle: string
    insightBody: string
  }
}>()

const emit = defineEmits<{
  triggerAi: []
  goWorkOrderCreate: []
  goProcure: []
  scrollToValue: []
}>()
</script>

<template>
  <section class="pref-section">
    <div v-if="commercialEnabled()" class="ai-next-proto">
      <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div class="flex items-start gap-4 min-w-0">
          <div class="ai-next-ico">
            <span class="material-symbols-outlined text-[24px]">auto_awesome</span>
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              <h3 class="m-0 text-base font-bold">{{ t('AI 运维建议') }}</h3>
              <span
                v-if="aiSourceLabel"
                class="conf"
                :class="{ dim: aiNextAction?.source === 'fallback' }"
                >{{ aiSourceLabel }}</span
              >
              <span v-if="formatAiModelMeta(aiNextAction)" class="conf">{{
                formatAiModelMeta(aiNextAction)
              }}</span>
              <span v-if="nextAction.conf != null" class="conf">{{
                t('置信度 {n}%', { n: nextAction.conf })
              }}</span>
            </div>
            <p
              v-if="nextAction.text || aiNextLoading"
              class="m-0 text-sm leading-relaxed max-w-3xl ai-next-body text-on-surface-variant"
            >
              <template v-if="aiNextLoading && !nextAction.text">{{
                t('正在结合台账生成运维建议…')
              }}</template>
              <template v-else>{{ localizeAssetAiText(nextAction.text) }}</template>
              <span v-if="aiNextLoading" class="ai-cursor" aria-hidden="true">▍</span>
            </p>
            <p
              v-if="aiNextAction?.llm_error && !aiNextLoading"
              class="ai-fallback-hint m-0 mt-2 text-xs"
            >
              {{ t(aiNextAction.llm_error) }}
            </p>
          </div>
        </div>
        <div class="flex gap-2 shrink-0 w-full md:w-auto flex-wrap">
          <button
            v-if="!aiNextLoading"
            type="button"
            class="btn-primary flex-1 md:flex-none inline-flex items-center justify-center gap-1"
            @click="emit('triggerAi')"
          >
            <span class="material-symbols-outlined text-[18px]">auto_awesome</span>
            {{ aiNextAction?.text ? t('重新生成') : t('生成 AI 建议') }}
          </button>
          <button v-else type="button" class="btn-primary flex-1 md:flex-none opacity-70" disabled>
            {{ t('生成中…') }}
          </button>
          <template v-if="showAiActionButtons">
            <button type="button" class="btn-outline flex-1 md:flex-none">
              {{ t('忽略建议') }}
            </button>
            <button
              v-if="aiActionType === 'repair' && !openWorkOrdersCount"
              type="button"
              class="btn-primary flex-1 md:flex-none inline-flex items-center justify-center gap-1"
              @click="emit('goWorkOrderCreate')"
            >
              <span class="material-symbols-outlined text-[18px]">build</span>
              {{ t('生成维修工单') }}
            </button>
            <button
              v-else-if="aiActionType === 'replace'"
              type="button"
              class="btn-primary flex-1 md:flex-none inline-flex items-center justify-center gap-1"
              @click="emit('goProcure')"
            >
              <span class="material-symbols-outlined text-[18px]">shopping_cart</span>
              {{ t('发起采购更换') }}
            </button>
            <button
              v-else
              type="button"
              class="btn-primary flex-1 md:flex-none inline-flex items-center justify-center gap-1"
              @click="emit('scrollToValue')"
            >
              {{ t('查看价值分析') }}
            </button>
          </template>
        </div>
      </div>
    </div>

    <div class="pref-grid">
      <div class="card pref-radar-card">
        <h3 class="card-h flex items-center gap-2">
          <span class="material-symbols-outlined text-secondary text-[20px]">speed</span>
          {{ t('运行性能雷达') }}
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
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="50" y2="10" />
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="90" y2="30" />
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="90" y2="70" />
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="50" y2="90" />
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="10" y2="70" />
              <line stroke="#e1e3e4" stroke-width="0.5" x1="50" y1="50" x2="10" y2="30" />
              <polygon
                :points="perfRadar.poly"
                fill="rgba(26, 115, 232, 0.2)"
                stroke="#005bbf"
                stroke-width="1.5"
              />
              <circle
                v-for="(p, i) in perfRadar.pts"
                :key="i"
                :cx="p.x"
                :cy="p.y"
                r="2"
                fill="#005bbf"
              />
            </svg>
            <div class="radar-lab top">
              {{ perfRadar.axes[0].label }} ({{ perfRadar.axes[0].score }})
            </div>
            <div class="radar-lab tr">
              {{ perfRadar.axes[1].label }} ({{ perfRadar.axes[1].score }})
            </div>
            <div class="radar-lab br">
              {{ perfRadar.axes[2].label }} ({{ perfRadar.axes[2].score }})
            </div>
            <div class="radar-lab bottom">
              {{ perfRadar.axes[3].label }} ({{ perfRadar.axes[3].score }})
            </div>
            <div class="radar-lab bl">
              {{ perfRadar.axes[4].label }} ({{ perfRadar.axes[4].score }})
            </div>
            <div class="radar-lab tl">
              {{ perfRadar.axes[5].label }} ({{ perfRadar.axes[5].score }})
            </div>
          </div>
        </div>
      </div>

      <div class="card pref-fp-card">
        <div class="flex justify-between items-start gap-3 mb-5 flex-wrap">
          <div>
            <h3 class="card-h flex items-center gap-2 !mb-0">
              <span class="material-symbols-outlined text-secondary text-[20px]">payments</span>
              {{ t('成本指纹（原值 {n}）', { n: fmtInt(costFingerprint.total) }) }}
            </h3>
          </div>
          <span class="fp-filter">{{ t('全生命周期') }}</span>
        </div>
        <div class="fp-rows">
          <div v-for="r in costFingerprint.rows" :key="r.name">
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
            <p class="m-0 font-medium text-sm mb-1">{{ costFingerprint.insightTitle }}</p>
            <p class="m-0 text-sm text-on-surface-variant">{{ costFingerprint.insightBody }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
