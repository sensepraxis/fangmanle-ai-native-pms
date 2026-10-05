<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 客群比对抽屉：选基准分群 vs 另一分群，调用 /api/segments/compare
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'

export type CompareSegOption = {
  id: string
  name: string
  cover?: number
}

const props = defineProps<{
  open: boolean
  base?: CompareSegOption | null
  options?: CompareSegOption[]
}>()

const emit = defineEmits<{ close: [] }>()

const router = useRouter()
const otherName = ref('')
const loading = ref(false)
const err = ref('')
const result = ref<any>(null)

const choices = computed(() =>
  (props.options || []).filter((o) => o.name && o.name !== props.base?.name),
)

watch(
  () => [props.open, props.base?.name] as const,
  ([open]) => {
    if (!open) return
    otherName.value = ''
    result.value = null
    err.value = ''
    // 默认选第一个可选项
    if (choices.value.length) otherName.value = choices.value[0].name
  },
)

watch(otherName, () => {
  if (props.open && otherName.value) runCompare()
})

async function runCompare() {
  const a = props.base?.name
  const b = otherName.value
  if (!a || !b || a === b) {
    result.value = null
    return
  }
  loading.value = true
  err.value = ''
  try {
    result.value = await api.compareSegments(hotelStore.hotelId, a, b)
  } catch (e: any) {
    result.value = null
    err.value = e?.message || t('比对失败')
  } finally {
    loading.value = false
  }
}

const statA = computed(
  () => result.value?.a || { name: props.base?.name || '—', count: 0, avg_ltv: 0 },
)
const statB = computed(
  () => result.value?.b || { name: otherName.value || '—', count: 0, avg_ltv: 0 },
)
const deltaCount = computed(() => result.value?.delta_count ?? 0)
const deltaLtv = computed(() => result.value?.delta_ltv_pct ?? 0)

function goMembers(name: string) {
  if (!name) return
  router.push({ path: '/b-data/global-guest-directory', query: { segment: name } })
  emit('close')
}

function fmtMoney(n: number) {
  return `¥${Number(n || 0).toLocaleString('zh-CN')}`
}
</script>

<template>
  <div v-if="open" class="drawer-mask" @click.self="emit('close')">
    <aside class="drawer">
      <header class="drawer-head">
        <h3>{{ t('比对客群') }}</h3>
        <button type="button" class="x" :aria-label="t('关闭')" @click="emit('close')">×</button>
      </header>

      <p class="hint">{{ t('以左侧选中的分群为基准，再选一个分群做规模与 LTV 对比。') }}</p>

      <div class="base-box">
        <div class="k">{{ t('基准分群') }}</div>
        <div class="v">{{ base?.name || '—' }}</div>
        <div class="meta">
          {{ Number(base?.cover || 0).toLocaleString('zh-CN') }} {{ t('人覆盖') }}
        </div>
      </div>

      <label class="field">
        <span class="k">{{ t('要比对的其他客群') }}</span>
        <select v-model="otherName" class="select">
          <option disabled value="">{{ t('请选择分群') }}</option>
          <option v-for="o in choices" :key="o.id" :value="o.name">
            {{ o.name }}（{{ Number(o.cover || 0).toLocaleString('zh-CN') }} {{ t('人）') }}
          </option>
        </select>
      </label>

      <p v-if="!choices.length" class="empty">{{ t('暂无其他分群可对比，请先保存更多分群。') }}</p>
      <p v-else-if="loading" class="loading">{{ t('正在比对…') }}</p>
      <p v-else-if="err" class="err">{{ err }}</p>

      <div v-if="result && !loading" class="result">
        <div class="summary">
          <div class="sum-title">
            <span class="material-symbols-outlined">compare_arrows</span>
            {{ t('漂移摘要') }}
          </div>
          <ul>
            <li>
              {{ t('人数变化') }}
              <strong :class="deltaCount >= 0 ? 'up' : 'down'">
                {{ deltaCount >= 0 ? '+' : '' }}{{ deltaCount }}</strong
              >
              <span class="sub">{{ statA.count }} → {{ statB.count }}</span>
            </li>
            <li>
              {{ t('平均 LTV 变化') }}
              <strong :class="deltaLtv >= 0 ? 'up' : 'down'">
                {{ deltaLtv >= 0 ? '+' : '' }}{{ deltaLtv }}%
              </strong>
            </li>
          </ul>
        </div>

        <div class="pair">
          <div class="card">
            <div class="card-h">
              <span class="chip">{{ t('基准') }}</span>
              <strong>{{ statA.name }}</strong>
            </div>
            <div class="row">
              <span>{{ t('覆盖人数') }}</span
              ><b>{{ statA.count }}</b>
            </div>
            <div class="row">
              <span>{{ t('平均 LTV') }}</span
              ><b>{{ fmtMoney(statA.avg_ltv) }}</b>
            </div>
            <button type="button" class="mini" @click="goMembers(statA.name)">
              {{ t('看成员') }}
            </button>
          </div>
          <div class="card accent">
            <div class="card-h">
              <span class="chip on">{{ t('对比') }}</span>
              <strong>{{ statB.name }}</strong>
            </div>
            <div class="row">
              <span>{{ t('覆盖人数') }}</span
              ><b>{{ statB.count }}</b>
            </div>
            <div class="row">
              <span>{{ t('平均 LTV') }}</span
              ><b>{{ fmtMoney(statB.avg_ltv) }}</b>
            </div>
            <button type="button" class="mini" @click="goMembers(statB.name)">
              {{ t('看成员') }}
            </button>
          </div>
        </div>
      </div>

      <div class="actions">
        <button
          type="button"
          class="btn primary"
          :disabled="loading || !otherName"
          @click="runCompare"
        >
          {{ loading ? t('比对中…') : t('重新比对') }}
        </button>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.drawer-mask {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  justify-content: flex-end;
}
.drawer {
  width: min(420px, 100%);
  max-height: 100%;
  overflow: auto;
  background: var(--surface-container-lowest, #fff);
  padding: 20px;
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.drawer-head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 750;
}
.x {
  border: none;
  background: transparent;
  font-size: 24px;
  cursor: pointer;
  line-height: 1;
}
.hint {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.base-box {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-bright, #fff);
}
.base-box .k,
.field .k {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: var(--on-surface-variant);
  margin-bottom: 4px;
}
.base-box .v {
  font-size: 16px;
  font-weight: 750;
}
.base-box .meta {
  margin-top: 4px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: #fff;
  font-size: 13px;
  font-weight: 600;
}
.empty,
.loading {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.err {
  margin: 0;
  font-size: 13px;
  font-weight: 650;
  color: #c2410c;
}
.result {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.summary {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--primary) 25%, var(--outline-variant));
  background: color-mix(in srgb, var(--primary) 6%, #fff);
}
.sum-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 750;
  color: var(--primary);
  margin-bottom: 8px;
}
.sum-title .material-symbols-outlined {
  font-size: 18px;
}
.summary ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.summary li {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 8px;
  font-size: 13px;
}
.summary strong.up {
  color: #16a34a;
}
.summary strong.down {
  color: #c2410c;
}
.summary .sub {
  font-size: 11px;
  color: var(--on-surface-variant);
  width: 100%;
}
.pair {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.card {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--outline-variant);
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.card.accent {
  border-color: color-mix(in srgb, var(--primary) 35%, var(--outline-variant));
}
.card-h {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.card-h strong {
  font-size: 14px;
}
.chip {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-container-high);
  color: var(--on-surface-variant);
}
.chip.on {
  background: var(--primary-container, #d6e3ff);
  color: var(--on-primary-container, #001a41);
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.row b {
  color: var(--on-surface);
  font-size: 15px;
}
.mini {
  align-self: flex-start;
  margin-top: 2px;
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}
.actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: auto;
  padding-top: 8px;
}
.btn {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  border: 1px solid var(--outline-variant);
}
.btn:disabled {
  opacity: 0.55;
  cursor: wait;
}
.btn.ghost {
  background: transparent;
  color: var(--primary);
}
.btn.primary {
  background: var(--primary);
  color: var(--on-primary);
  border-color: transparent;
}
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
</style>
