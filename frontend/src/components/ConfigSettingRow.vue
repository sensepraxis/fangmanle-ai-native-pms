<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 系统配置统一字段行：
 * - 已配置：展示当前值（敏感则掩码）+「重新配置」
 * - 未配置：空输入框 +「配置」
 */
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    /** 库中是否已有值 */
    configured: boolean
    /** 已配置时的展示文案（明文或掩码） */
    displayValue?: string
    /** 是否敏感（编辑态用 password） */
    sensitive?: boolean
    /** 编辑中的草稿 */
    modelValue?: string
    saving?: boolean
    disabled?: boolean
    hint?: string
    inputType?: string
  }>(),
  {
    displayValue: '',
    sensitive: false,
    modelValue: '',
    saving: false,
    disabled: false,
    hint: '',
    inputType: 'text',
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'save', value: string): void
}>()

const editing = ref(!props.configured)

watch(
  () => props.configured,
  (set) => {
    if (set) editing.value = false
    else editing.value = true
  },
)

const showInput = computed(() => !props.configured || editing.value)

const btnLabel = computed(() => {
  if (props.saving) return t('保存中…')
  if (!props.configured) return t('配置')
  if (editing.value) return t('保存')
  return t('重新配置')
})

function onBtn() {
  if (props.disabled || props.saving) return
  if (props.configured && !editing.value) {
    editing.value = true
    emit('update:modelValue', '')
    return
  }
  emit('save', String(props.modelValue || '').trim())
}

function cancelEdit() {
  if (!props.configured) return
  editing.value = false
  emit('update:modelValue', '')
}
</script>

<template>
  <div class="cfg-row" :class="{ sensitive }">
    <div class="cfg-label">{{ label }}</div>
    <div class="cfg-body">
      <div v-if="!showInput" class="cfg-view">
        <span class="cfg-value" :class="{ mask: sensitive }">{{ displayValue || '—' }}</span>
        <button type="button" class="btn-primary" :disabled="disabled || saving" @click="onBtn">
          {{ btnLabel }}
        </button>
      </div>
      <div v-else class="cfg-edit">
        <input
          :type="sensitive ? 'password' : inputType"
          :value="modelValue"
          :disabled="disabled || saving"
          autocomplete="off"
          @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
          @keydown.enter.prevent="onBtn"
        />
        <button type="button" class="btn-primary" :disabled="disabled || saving" @click="onBtn">
          {{ btnLabel }}
        </button>
        <button
          v-if="configured && editing"
          type="button"
          class="btn-ghost"
          :disabled="saving"
          @click="cancelEdit"
        >
          {{ t('取消') }}
        </button>
      </div>
      <p v-if="hint" class="cfg-hint">{{ t(hint) }}</p>
    </div>
  </div>
</template>

<style scoped>
.cfg-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.cfg-label {
  flex: 0 0 auto;
  min-width: 4.5em;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
  line-height: 1.2;
}
.cfg-body {
  flex: 1;
  min-width: 0;
}
.cfg-view,
.cfg-edit {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.cfg-value {
  flex: 1;
  min-width: 160px;
  padding: 8px 12px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  background: #f8fafc;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
  word-break: break-all;
}
.cfg-value.mask {
  letter-spacing: 0.04em;
  color: #334155;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.cfg-edit input {
  flex: 1;
  min-width: 160px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
  font-size: 14px;
  box-sizing: border-box;
}
.btn-primary,
.btn-ghost {
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.btn-primary {
  border: none;
  background: var(--primary, #005bbf);
  color: #fff;
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-ghost {
  border: 1px solid var(--outline, #727785);
  background: transparent;
}
.cfg-hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  line-height: 1.45;
}
@media (max-width: 640px) {
  .cfg-row {
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
  }
  .cfg-label {
    min-width: 0;
  }
}
</style>
