<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'
import { commercialEnabled } from '../lib/branding'
import { localizeSeedText } from '../lib/localizeSeed'

function loc(s?: string | null) {
  return localizeSeedText(s)
}

/**
 * 财务 AI Harness — 现状 → 操作单勾选 → 确认写库
 */
import { ref, computed, watch } from 'vue'
import { formatAiModelMeta } from '../lib/aiModelMeta'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { toast } from '../lib/ui'

export type FinanceAiScene = 'deposit' | 'refund' | 'night_audit' | 'recon' | 'invoice' | 'ar_ap'

const SCENE_TITLE: Record<FinanceAiScene, string> = {
  deposit: 'AI 押金安排',
  refund: 'AI 退改操作单',
  night_audit: 'AI 夜审异常处理',
  recon: 'AI 对账安排',
  invoice: 'AI 开票安排',
  ar_ap: 'AI 应收应付安排',
}

const props = defineProps<{
  open: boolean
  scene: FinanceAiScene
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
  deposit_reauthorize: '重授权',
  deposit_note_dispute: '争议跟进',
  deposit_flag_receipt: '补收据',
  refund_remind_ticket: '催办',
  refund_create_adjust_ticket: '改账单',
  refund_create_reverse_ticket: '反结账单',
  night_fix_exception: '确认异常',
  recon_close_batch: '关账',
  recon_mark_matched: '标配对',
  recon_mark_conflict: '转复核',
  invoice_issue: '开票',
  invoice_red_flush: '红冲',
  ar_ap_sync: '同步单据',
  ar_overdue_remind: '催收备忘',
  ar_credit_warn: '授信预警',
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
    const res = await api.financeAiPlanGenerate(hotelStore.hotelId, props.scene)
    if (token !== genToken.value) return
    plan.value = res
  } catch (e: any) {
    if (token !== genToken.value) return
    toast(e?.message || t('安排生成失败，请稍后重试'), false)
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
  for (const it of plan.value?.items || []) {
    if (it.risk === 'high' && on) continue
    it.selected = on
  }
}

const selectedCount = computed(
  () => (plan.value?.items || []).filter((it: any) => it.selected !== false).length,
)

async function confirm() {
  if (!plan.value || confirming.value) return
  if (plan.value.source !== 'llm') {
    toast(t('未能调用大模型，不能把规则数据当作 AI 操作单执行'), false)
    return
  }
  if (!selectedCount.value) {
    toast(t('请至少勾选一张操作单'), false)
    return
  }
  confirming.value = true
  try {
    const res = await api.financeAiPlanConfirm(hotelStore.hotelId, plan.value)
    toast(res?.message || t('已生效'))
    emit('confirmed', res)
    close()
  } catch (e: any) {
    toast(e?.message || t('执行失败，请重试'), false)
  } finally {
    confirming.value = false
  }
}
</script>

<template>
  <section v-if="open" class="ai-plan-inline" :aria-label="title">
    <header class="head">
      <div class="head-main">
        <span class="badge">{{ t('AI 操作单') }}</span>
        <span v-if="modelMeta" class="model-meta">{{ modelMeta }}</span>
        <h3>{{ title }}</h3>
        <p class="sub">
          <template v-if="loading">{{ t('正在核对库内现状并生成操作单…') }}</template>
          <template v-else-if="plan?.source !== 'llm'">{{
            t('未能调用大模型，未生成 AI 操作单（规则数据不会冒充 AI）。')
          }}</template>
          <template v-else>{{
            t('先看清现状，勾选后点「AI确认执行」才会写库；高风险项默认不选')
          }}</template>
        </p>
      </div>
      <button type="button" class="x" :aria-label="t('收起')" @click="close">×</button>
    </header>

    <div v-if="loading" class="loading">
      <span class="spin" aria-hidden="true" />
      <span>{{ t('分析中…') }}</span>
    </div>

    <template v-else-if="plan">
      <div v-if="situation" class="block sit">
        <div class="block-label">{{ t('现状') }}</div>
        <p class="sit-head">{{ loc(situation.headline) }}</p>
        <div v-if="(situation.metrics || []).length" class="metrics">
          <div v-for="(m, i) in situation.metrics" :key="i" class="metric">
            <span class="m-val">{{ m.value }}</span>
            <span class="m-lab">{{ loc(m.label) }}</span>
          </div>
        </div>
        <ul v-if="(situation.bullets || []).length" class="bullets">
          <li v-for="(b, i) in situation.bullets" :key="i">{{ loc(b) }}</li>
        </ul>
      </div>

      <div class="block act">
        <div class="block-label">{{ t('操作单') }}</div>
        <p class="summary">{{ loc(plan.summary) }}</p>
        <ul v-if="(plan.reasons || []).length" class="reasons">
          <li v-for="(r, i) in plan.reasons" :key="i">{{ loc(r) }}</li>
        </ul>

        <div class="toolbar">
          <span>{{
            t('共 {n} 项 · 已选 {m}', { n: (plan.items || []).length, m: selectedCount })
          }}</span>
          <div class="tb-acts">
            <button type="button" class="link" @click="toggleAll(true)">
              {{ t('全选低风险') }}
            </button>
            <button type="button" class="link" @click="toggleAll(false)">{{ t('全不选') }}</button>
            <button type="button" class="link" :disabled="loading" @click="generate">
              {{ t('换一批') }}
            </button>
          </div>
        </div>

        <div v-if="!(plan.items || []).length" class="empty">{{ t('当前暂无可执行操作单。') }}</div>
        <label
          v-for="it in plan.items || []"
          :key="it.id"
          class="row"
          :class="{ high: it.risk === 'high' }"
        >
          <input v-model="it.selected" type="checkbox" />
          <div class="row-body">
            <div class="row-top">
              <span class="op">{{ opLabel(it.op) }}</span>
              <span v-if="it.risk === 'high'" class="risk">{{ t('高风险') }}</span>
              <strong>{{ loc(it.label) }}</strong>
            </div>
            <p>{{ loc(it.reason) }}</p>
          </div>
        </label>
      </div>

      <footer class="foot">
        <button type="button" class="btn-ghost" @click="close">{{ t('收起') }}</button>
        <button
          type="button"
          class="btn-primary"
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
  color: #6b7280;
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
  color: #1967d2;
  margin-bottom: 8px;
}
.sit {
  padding: 12px;
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
  padding: 10px 8px;
  border-radius: 8px;
  background: #f0f7ff;
  text-align: center;
  border: 1px solid #dce8fb;
}
.m-val {
  display: block;
  font-size: 18px;
  font-weight: 800;
  color: #174ea6;
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
.act .summary {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 700;
}
.reasons {
  margin: 0 0 12px;
  padding-left: 18px;
  font-size: 12px;
  color: #5b616e;
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
  color: #1a73e8;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
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
.row.high {
  border-color: #f4c8ca;
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
.risk {
  font-size: 10px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
  background: #fdecea;
  color: #b3261e;
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
}
.btn-ghost,
.btn-primary {
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
}
.btn-ghost {
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #5b616e;
}
.btn-primary {
  border: none;
  background: #1967d2;
  color: #fff;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
