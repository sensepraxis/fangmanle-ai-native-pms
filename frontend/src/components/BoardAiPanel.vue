<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 看板 AI 解读 · 薄封装 NarrativeInsightPanel（订单风险 / 利润 / 竞品）。
 */
import { computed, ref } from 'vue'
import NarrativeInsightPanel from './NarrativeInsightPanel.vue'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'

const props = withDefaults(
  defineProps<{
    kind: 'order_risks' | 'profit_insights' | 'pricing_compare'
    title: string
    idle?: string
    runLabel?: string
    rerunLabel?: string
    waitLabel?: string
    payload?: Record<string, any>
    compact?: boolean
  }>(),
  {
    idle: '点击后结合当前看板事实生成解读与可执行建议',
    runLabel: '生成 AI 解读',
    rerunLabel: '重新解读',
    waitLabel: '正在结合规则事实生成解读…',
    payload: () => ({}),
    compact: false,
  },
)

const emit = defineEmits<{
  (e: 'result', insight: any): void
}>()

const panel = ref<InstanceType<typeof NarrativeInsightPanel> | null>(null)
const resetKey = computed(() => `${props.kind}:${JSON.stringify(props.payload || {})}`)

function fetcher() {
  return api.boardAiNarrate(hotelStore.hotelId, props.kind, props.payload || {})
}

function executor(action: Record<string, any>) {
  return api.boardAiExecute(hotelStore.hotelId, action)
}

defineExpose({
  run: () => panel.value?.run(),
  insight: computed(() => panel.value?.insight ?? null),
})
</script>

<template>
  <NarrativeInsightPanel
    ref="panel"
    :title="t(title)"
    :idle="t(idle)"
    :run-label="t(runLabel)"
    :rerun-label="t(rerunLabel)"
    :wait-label="t(waitLabel)"
    :compact="compact"
    :reset-key="resetKey"
    :fetcher="fetcher"
    :executor="executor"
    @result="emit('result', $event)"
  />
</template>
