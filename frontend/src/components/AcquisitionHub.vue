<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 营销获客 · 双渠道入口
 * 小红书（线索单轨）| 抖音（线索 + 交易双轨）
 */
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import XhsAcquisitionHub from './XhsAcquisitionHub.vue'
import DouyinAcquisitionHub from './DouyinAcquisitionHub.vue'

type ChannelId = 'xhs' | 'douyin'

const route = useRoute()
const router = useRouter()

const channels: { id: ChannelId; label: string; badge: string; badgeClass: string }[] = [
  { id: 'xhs', label: t('小红书'), badge: t('红'), badgeClass: 'bg-[#ff2442]/10 text-[#ff2442]' },
  { id: 'douyin', label: t('抖音'), badge: t('抖'), badgeClass: 'bg-[#1A1A1A]/10 text-[#1A1A1A]' },
]

const activeChannel = computed<ChannelId>(() =>
  route.query.channel === 'douyin' ? 'douyin' : 'xhs',
)

const segmentIdQ = computed(() => route.query.segment_id as string | undefined)
const segmentNameQ = computed(() => route.query.segment_name as string | undefined)
const crmBanner = computed(
  () => segmentNameQ.value || (segmentIdQ.value ? `分群 #${segmentIdQ.value}` : ''),
)

function selectChannel(id: ChannelId) {
  const tab = route.query.tab as string
  const q: Record<string, string> = {}
  if (id === 'douyin') q.channel = 'douyin'
  if (segmentIdQ.value) q.segment_id = segmentIdQ.value
  if (segmentNameQ.value) q.segment_name = segmentNameQ.value
  if (tab && tab !== 'leads') {
    if (id === 'douyin' || tab !== 'trade') q.tab = tab
  }
  router.replace({ path: '/acquisition', query: Object.keys(q).length ? q : undefined })
}

watch(
  () => route.query.channel,
  () => {
    const tab = route.query.tab as string
    if (activeChannel.value === 'xhs' && tab === 'trade') {
      router.replace({ path: '/acquisition', query: {} })
    }
  },
)
</script>

<template>
  <div class="page">
    <div class="max-w-[1440px] mx-auto w-full space-y-4">
      <div
        v-if="crmBanner"
        class="rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 flex items-center justify-between gap-3"
      >
        <div class="text-sm text-on-surface">
          {{ t('来自 CRM 客群推送：') }} <strong>{{ crmBanner }}</strong>
          {{ t('— 可在此配置获客活动触达该分群') }}
        </div>
      </div>
      <div
        class="inline-flex p-1 rounded-xl bg-surface-container-low border border-outline-variant gap-1"
      >
        <button
          v-for="c in channels"
          :key="c.id"
          type="button"
          class="px-5 py-2.5 rounded-lg font-label-lg text-label-lg transition-colors flex items-center gap-2"
          :class="
            activeChannel === c.id
              ? 'bg-surface-container-lowest text-on-surface shadow-sm border border-outline-variant'
              : 'text-on-surface-variant hover:text-on-surface'
          "
          @click="selectChannel(c.id)"
        >
          <span
            class="inline-flex items-center justify-center w-6 h-6 rounded-full text-[11px] font-bold"
            :class="c.badgeClass"
          >
            {{ c.badge }}</span
          >
          {{ c.label }}
        </button>
      </div>

      <XhsAcquisitionHub v-if="activeChannel === 'xhs'" />
      <DouyinAcquisitionHub v-else />
    </div>
  </div>
</template>

<style scoped>
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
</style>
