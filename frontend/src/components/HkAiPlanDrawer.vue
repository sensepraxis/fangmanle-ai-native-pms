<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'
import { commercialEnabled } from '../lib/branding'

/**
 * 房务 AI 行动 — 内联：现状 → 行动计划 → 确认执行
 */
import { ref, watch, computed } from 'vue'
import { formatAiModelMeta } from '../lib/aiModelMeta'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { toast } from '../lib/ui'

export type HkAiScene = 'cleaning_plan' | 'dispatch_assign' | 'floor_rebalance' | 'staffing_gap'

const SCENE_TITLE: Record<HkAiScene, string> = {
  cleaning_plan: 'AI清扫安排',
  dispatch_assign: 'AI派工安排',
  floor_rebalance: 'AI楼层调拨',
  staffing_gap: 'AI补班安排',
}

const props = defineProps<{
  open: boolean
  scene: HkAiScene
}>()

const emit = defineEmits<{
  'update:open': [v: boolean]
  confirmed: [result: any]
}>()

const loading = ref(false)
const confirming = ref(false)
const plan = ref<any>(null)
const genToken = ref(0)

const OP_LABEL: Record<string, string> = {
  create_task: '新建任务',
  assign_start: '派工',
  reassign: '改派',
  upsert_shift: '调班',
  urge: '催办',
}

const title = computed(() => t(plan.value?.title || SCENE_TITLE[props.scene] || 'AI安排'))
const modelMeta = computed(() =>
  plan.value?.source === 'llm' ? formatAiModelMeta(plan.value) : '',
)
const situation = computed(() => plan.value?.situation || null)

function opLabel(op: string) {
  return t(OP_LABEL[op] || op)
}

async function generate() {
  if (!commercialEnabled()) {
    emit('update:open', false)
    return
  }
  const token = ++genToken.value
  loading.value = true
  plan.value = null
  try {
    const res = await api.hkAiPlanGenerate(hotelStore.hotelId, props.scene)
    if (token !== genToken.value) return
    plan.value = res
  } catch (e: any) {
    if (token !== genToken.value) return
    toast(e?.message || t('安排生成失败，请稍后重试'))
    emit('update:open', false)
  } finally {
    if (token === genToken.value) loading.value = false
  }
}

watch(
  () => [props.open, props.scene] as const,
  ([open]) => {
    if (open && commercialEnabled()) generate()
  },
)

function close() {
  genToken.value += 1
  emit('update:open', false)
}

function toggleAll(on: boolean) {
  for (const it of plan.value?.items || []) it.selected = on
}

const selectedCount = computed(
  () => (plan.value?.items || []).filter((it: any) => it.selected !== false).length,
)

async function confirm() {
  if (!plan.value || confirming.value) return
  if (plan.value.source !== 'llm') {
    toast(t('未能调用大模型，不能把规则数据当作 AI 安排执行'))
    return
  }
  if (!selectedCount.value) {
    toast(t('请至少选择一项'))
    return
  }
  confirming.value = true
  try {
    const res = await api.hkAiPlanConfirm(hotelStore.hotelId, plan.value)
    toast(res?.message || t('已生效'))
    emit('confirmed', res)
    close()
  } catch (e: any) {
    toast(e?.message || t('执行失败，请重试'))
  } finally {
    confirming.value = false
  }
}
</script>

<template>
  <section v-if="open" class="ai-plan-inline" :aria-label="title">
    <header class="head">
      <div class="head-main">
        <span class="badge">{{ t('AI安排') }}</span>
        <span v-if="modelMeta" class="model-meta">{{ modelMeta }}</span>
        <h3>{{ title }}</h3>
        <p class="sub">
          <template v-if="loading">{{ t('正在核对现状并生成行动计划…') }}</template>
          <template v-else-if="plan?.source !== 'llm'">{{
            t('未能调用大模型，未生成 AI 安排（规则数据不会冒充 AI）。')
          }}</template>
          <template v-else>{{ t('先看清现状，再勾选行动，点「AI确认执行」即可生效') }}</template>
        </p>
      </div>
      <button type="button" class="x" :aria-label="t('收起')" @click="close">×</button>
    </header>

    <div v-if="loading" class="loading">
      <span class="spin" aria-hidden="true"></span>
      <span>{{ t('分析中…') }}</span>
    </div>

    <template v-else-if="plan">
      <!-- ① 现状 -->
      <div v-if="situation" class="block sit">
        <div class="block-label">{{ t('现状') }}</div>
        <p class="sit-head">{{ t(situation.headline) }}</p>
        <div v-if="(situation.metrics || []).length" class="metrics">
          <div v-for="(m, i) in situation.metrics" :key="i" class="metric">
            <span class="m-val">{{ m.value }}</span>
            <span class="m-lab">{{ t(m.label) }}</span>
          </div>
        </div>
        <ul v-if="(situation.bullets || []).length" class="bullets">
          <li v-for="(b, i) in situation.bullets" :key="i">{{ t(b) }}</li>
        </ul>
      </div>

      <!-- ② 行动计划 -->
      <div class="block act">
        <div class="block-label">{{ t('行动计划') }}</div>
        <p class="summary">{{ t(plan.summary) }}</p>
        <ul v-if="(plan.reasons || []).length" class="reasons">
          <li v-for="(r, i) in plan.reasons" :key="i">{{ t(r) }}</li>
        </ul>

        <div class="toolbar">
          <span
            >{{ t('待执行') }} {{ (plan.items || []).length }} {{ t('项') }} · {{ t('已选') }}
            {{ selectedCount }}</span
          >
          <div class="tb-acts">
            <button type="button" class="link" @click="toggleAll(true)">{{ t('全选') }}</button>
            <button type="button" class="link" @click="toggleAll(false)">{{ t('全不选') }}</button>
            <button type="button" class="link" :disabled="loading" @click="generate">
              {{ t('换一批') }}
            </button>
          </div>
        </div>

        <div v-if="!(plan.items || []).length" class="empty">{{ t('当前暂无可执行安排。') }}</div>
        <label v-for="it in plan.items || []" :key="it.id" class="row">
          <input v-model="it.selected" type="checkbox" />
          <div class="row-body">
            <div class="row-top">
              <span class="op">{{ opLabel(it.op) }}</span>
              <strong>{{ t(it.label) }}</strong>
            </div>
            <p>{{ t(it.reason) }}</p>
          </div>
        </label>
      </div>

      <footer class="foot">
        <button type="button" class="btn btn-ghost" @click="close">{{ t('收起') }}</button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="confirming || !selectedCount || plan.source !== 'llm'"
          @click="confirm"
        >
          {{ confirming ? t('执行中…') : t('AI确认执行（{n}）', { n: selectedCount }) }}
        </button>
      </footer>
    </template>
  </section>
</template>

<style scoped>
.ai-plan-inline {
  margin: 12px 0 16px;
  padding: 14px 16px 12px;
  border-radius: 12px;
  border: 1px solid #c5d4f5;
  background: linear-gradient(180deg, #f5f8ff 0%, #fff 48%);
}
.head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.head-main {
  min-width: 0;
}
.badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 800;
  color: #1967d2;
  background: #e8f0fe;
  padding: 2px 8px;
  border-radius: 999px;
  margin-bottom: 6px;
}
.model-meta {
  display: inline-block;
  margin-left: 8px;
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #5f6368;
  font-variant-numeric: tabular-nums;
}
h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
}
.sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant, #6b7280);
  line-height: 1.4;
}
.x {
  border: none;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
  line-height: 1;
  color: #6b7280;
  padding: 0 4px;
}
.loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 4px;
  font-size: 13px;
  color: #5b616e;
}
.spin {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid #c5d4f5;
  border-top-color: #1967d2;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.block {
  margin-bottom: 14px;
}
.block-label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #1967d2;
  text-transform: none;
  margin-bottom: 8px;
}
.sit {
  padding: 12px 12px 10px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #e5e7eb;
}
.sit-head {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.4;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}
.metric {
  padding: 10px 10px 8px;
  border-radius: 8px;
  background: #f0f7ff;
  text-align: center;
  border: 1px solid #dce8fb;
}
.m-val {
  display: block;
  font-size: 20px;
  font-weight: 800;
  color: #174ea6;
  line-height: 1.2;
}
.m-lab {
  font-size: 11px;
  color: #5b616e;
  font-weight: 600;
}
.bullets {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #5b616e;
  line-height: 1.55;
}
.bullets li + li {
  margin-top: 4px;
}

.act .summary {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.45;
}
.reasons {
  margin: 0 0 12px;
  padding-left: 18px;
  font-size: 12px;
  color: #5b616e;
  line-height: 1.5;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.tb-acts {
  display: flex;
  gap: 12px;
}
.link {
  border: none;
  background: transparent;
  color: var(--primary, #1a73e8);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
}
.link:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.empty {
  padding: 16px;
  text-align: center;
  color: #9aa0a6;
  font-size: 13px;
}
.row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  background: #fff;
}
.row:has(input:checked) {
  border-color: #93c5fd;
  background: #f0f7ff;
}
.row input {
  margin-top: 4px;
  flex-shrink: 0;
}
.row-top {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.op {
  font-size: 11px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
  background: #e8f0fe;
  color: #1967d2;
}
.row-body strong {
  font-size: 13px;
}
.row-body p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.4;
}
.foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 8px;
  margin-top: 4px;
}
</style>
