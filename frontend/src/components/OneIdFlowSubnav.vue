<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * OneID 归并 Wizard（串行）：归并台 → 冲突队列 → 归并审核 → 资产确认
 * 页顶仅保留返回 + 精简步骤条 + 上一步/下一步（不再叠 CustomerFlowNav）
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const props = defineProps<{
  /** 覆盖默认「下一步」跳转（如冲突队列需携带主档选择） */
  onNext?: () => void | Promise<void>
  nextDisabled?: boolean
  nextLoading?: boolean
  /** 覆盖下一步按钮文案 */
  nextLabel?: string
}>()

const HOME = '/b-data/global-guest-directory'

const STEPS = [
  { path: '/b-data/one-id', label: '归并台', short: '手机号冲突裁定' },
  { path: '/b-data/ai-high-confidence-94', label: '冲突队列', short: '核对疑似重复' },
  { path: '/b-data/one-id-resolution', label: '归并审核', short: '确认合并档案' },
  { path: '/b-data/consolidated-asset-confirmation', label: '资产确认', short: '权益落地' },
] as const

const currentIdx = computed(() => {
  const i = STEPS.findIndex((s) => route.path === s.path || route.path.startsWith(s.path + '/'))
  return i
})
const current = computed(() => (currentIdx.value >= 0 ? STEPS[currentIdx.value] : null))
const prevStep = computed(() => (currentIdx.value > 0 ? STEPS[currentIdx.value - 1] : null))
const nextStep = computed(() =>
  currentIdx.value >= 0 && currentIdx.value < STEPS.length - 1 ? STEPS[currentIdx.value + 1] : null,
)

function go(path: string) {
  if (path !== route.path) router.push(path)
}

function goNext() {
  if (props.onNext) {
    void props.onNext()
    return
  }
  if (nextStep.value) go(nextStep.value.path)
}

function goFinish() {
  if (props.onNext) {
    void props.onNext()
    return
  }
  router.push(HOME)
}

function goStep(i: number) {
  if (i < 0 || i >= STEPS.length) return
  if (i > currentIdx.value + 1) return
  go(STEPS[i].path)
}
</script>

<template>
  <div v-if="current" class="wiz">
    <div class="wiz-bar">
      <button type="button" class="back" @click="router.push(HOME)">
        <span class="material-symbols-outlined">arrow_back</span>
        {{ t('客户全景') }}
      </button>
      <span class="sep">/</span>
      <span class="crumb">{{ t('OneID归并') }}</span>
      <span class="sep">·</span>
      <span class="here">{{ t(current.label) }}</span>
    </div>

    <nav class="steps" :aria-label="t('OneID 归并步骤')">
      <template v-for="(s, i) in STEPS" :key="s.path">
        <button
          type="button"
          class="step"
          :class="{
            on: i === currentIdx,
            done: i < currentIdx,
            locked: i > currentIdx + 1,
          }"
          :disabled="i > currentIdx + 1"
          :title="t(s.short)"
          @click="goStep(i)"
        >
          <span class="num">{{ i + 1 }}</span>
          <span class="lab">{{ t(s.label) }}</span>
        </button>
        <span v-if="i < STEPS.length - 1" class="pipe" aria-hidden="true" />
      </template>
    </nav>

    <div class="wiz-nav">
      <button v-if="prevStep" type="button" class="btn ghost" @click="go(prevStep.path)">
        <span class="material-symbols-outlined">chevron_left</span>
        {{ t('上一步') }}：{{ t(prevStep.label) }}
      </button>
      <span v-else class="spacer" />
      <button
        v-if="nextStep"
        type="button"
        class="btn primary"
        :disabled="nextDisabled || nextLoading"
        @click="goNext"
      >
        {{
          nextLoading
            ? t('处理中…')
            : nextLabel
              ? t(nextLabel)
              : `${t('下一步')}：${t(nextStep.label)}`
        }}
        <span v-if="!nextLoading" class="material-symbols-outlined">chevron_right</span>
      </button>
      <button
        v-else
        type="button"
        class="btn primary"
        :disabled="nextDisabled || nextLoading"
        @click="goFinish"
      >
        {{ nextLoading ? t('处理中…') : nextLabel ? t(nextLabel) : t('完成并回全景') }}
        <span v-if="!nextLoading" class="material-symbols-outlined">{{
          onNext ? 'chevron_right' : 'check'
        }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.wiz {
  margin-bottom: 24px;
}
.wiz-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
  margin-bottom: 10px;
  font-size: 13px;
}
.back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  padding: 0;
  color: var(--primary);
  font-weight: 650;
  cursor: pointer;
}
.back .material-symbols-outlined {
  font-size: 16px;
}
.sep {
  color: var(--outline);
}
.crumb {
  color: var(--on-surface-variant);
  font-weight: 650;
}
.here {
  font-weight: 750;
  color: var(--on-surface);
}

.steps {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
}
.step {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  padding: 4px 8px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--on-surface-variant);
  font-size: 12px;
  font-weight: 650;
}
.step:hover:not(:disabled) {
  background: var(--surface-container-low);
  color: var(--on-surface);
}
.step.on {
  background: color-mix(in srgb, var(--primary) 12%, transparent);
  color: var(--primary);
}
.step.done .num {
  background: var(--primary);
  color: var(--on-primary);
}
.step.locked {
  opacity: 0.45;
  cursor: not-allowed;
}
.num {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 750;
  background: var(--surface-container-high);
  color: var(--on-surface-variant);
}
.step.on .num {
  background: var(--primary);
  color: var(--on-primary);
}
.lab {
  white-space: nowrap;
}
.pipe {
  width: 12px;
  height: 1px;
  background: var(--outline-variant);
  flex-shrink: 0;
}

.wiz-nav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 10px;
}
.spacer {
  flex: 1;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  color: var(--on-surface);
}
.btn .material-symbols-outlined {
  font-size: 18px;
}
.btn.ghost:hover {
  background: var(--surface-container-low);
}
.btn.primary {
  border-color: var(--primary);
  background: var(--primary);
  color: var(--on-primary);
}
.btn.primary:hover:not(:disabled) {
  opacity: 0.92;
}
.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 450,
    'GRAD' 0,
    'opsz' 24;
}
</style>
