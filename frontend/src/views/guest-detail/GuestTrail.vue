<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import type { TrailEvt } from './useGuest360'

defineProps<{
  channelTrail: TrailEvt[]
  sentimentScore: { score: number; label: string }
  stayCount: number
}>()
</script>

<template>
  <section id="section-trail" class="sec-block trail-block">
    <div class="sec-head">
      <div>
        <h2 class="sec-title">
          <span class="material-symbols-outlined text-primary">timeline</span>
          {{ t('全渠道行为轨迹') }}
        </h2>
      </div>
      <div class="trail-meta">
        <span>AI {{ t('情感') }} {{ sentimentScore.score }}/100 · {{ sentimentScore.label }}</span>
        <span>·</span>
        <span>{{ stayCount }} {{ t('次入住') }}</span>
      </div>
    </div>

    <div class="trail-layout">
      <div class="trail-rail">
        <div class="trail-line" />
        <div v-for="(e, idx) in channelTrail" :key="idx" class="trail-node">
          <div class="trail-dot" :class="'tone-' + e.tone">
            <span class="material-symbols-outlined text-[18px]">
              {{
                e.tone === 'ai' ? 'auto_awesome' : e.tone === 'ok' ? 'check' : 'travel_explore'
              }}</span
            >
          </div>
          <div class="card trail-card">
            <div class="flex justify-between items-start gap-3 mb-2">
              <div>
                <h3 class="m-0 text-[15px] font-bold">{{ e.title }}</h3>
                <p class="m-0 text-xs text-on-surface-variant mt-0.5">{{ e.sub }}</p>
              </div>
              <div class="text-right shrink-0 text-xs">
                <div class="font-semibold">{{ e.when }}</div>
                <div class="text-on-surface-variant">{{ e.time }}</div>
              </div>
            </div>
            <div class="trail-body" :class="{ 'is-ai': !!e.ai }">
              <div class="flex justify-between items-center gap-2 flex-wrap">
                <span class="text-sm">{{ e.body }}</span>
                <span v-if="e.mood" class="mood">{{ e.mood }}</span>
              </div>
              <div v-if="e.ai" class="text-xs text-tertiary mt-1.5">{{ e.ai }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
@import './guest-detail-shared.css';
</style>
