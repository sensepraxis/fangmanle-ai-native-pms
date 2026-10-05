<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

import { localizeSeedText } from '../../../lib/localizeSeed'
import { ASSETS_EMPTY } from '../../../lib/assetsEmpty'

defineProps<{
  needsRepair: boolean
  alerts: any[]
  insight?: string
  timeline: any[]
}>()

const emit = defineEmits<{
  goWorkOrderCreate: []
  timelineAction: [action: string]
}>()
</script>

<template>
  <section id="section-detail" class="bento">
    <div v-if="needsRepair" class="bento-alert">
      <span class="material-symbols-outlined text-primary">info</span>
      <div class="min-w-0 flex-1">
        <div class="font-bold text-sm mb-1">{{ t('主动运维提醒：设备异常') }}</div>
        <p class="m-0 text-sm text-on-surface-variant leading-relaxed">
          {{
            localizeSeedText(alerts[0]?.message || insight) ||
            t('设备健康分偏低或状态异常，建议生成维修工单。')
          }}
        </p>
        <div class="mt-2 flex gap-2 flex-wrap">
          <button
            type="button"
            class="btn-primary !py-1.5 !px-3 !text-xs"
            @click="emit('goWorkOrderCreate')"
          >
            {{ t('生成维修工单') }}
          </button>
        </div>
      </div>
    </div>

    <div class="card-clean tl-card">
      <h2>{{ t('生命周期时间轴') }}</h2>
      <p v-if="!timeline.length" class="empty-hint">{{ ASSETS_EMPTY }}</p>
      <div v-else class="tl-scroll">
        <div class="tl-axis" />
        <div class="tl-list">
          <div v-for="(n, i) in timeline" :key="i" class="tl-item" :class="n.type">
            <div class="tl-dot" />
            <div class="tl-body" :class="{ ai: n.type === 'ai', future: n.type === 'future' }">
              <h3>{{ n.title }}</h3>
              <p v-if="n.time" class="num tl-time">{{ n.time }}</p>
              <p v-if="n.desc" class="tl-desc">{{ n.desc }}</p>
              <button
                v-if="n.action"
                class="tl-action"
                type="button"
                @click="emit('timelineAction', n.action)"
              >
                {{ n.action }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
