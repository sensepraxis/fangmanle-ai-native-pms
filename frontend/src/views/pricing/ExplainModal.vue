<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 算法推导卡：回放 explain_json + 调用系统配置的 LLM（本地/云端可切换）生成白话说明
 */
import { computed, ref, watch } from 'vue'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { api } from '../../lib/api'
import { fmt } from '../../lib/ui'
import { aggLabel, channelLabel, localizePricingCopy } from './labels'

const props = defineProps<{
  open: boolean
  reco: any | null
}>()
const emit = defineEmits<{ (e: 'close'): void }>()

const explain = computed(() => props.reco?.explain_json || null)
const factors = computed(() =>
  (explain.value?.factors || []).map((f: any) => ({
    ...f,
    name: localizePricingCopy(f?.name),
    source: localizePricingCopy(f?.source),
  })),
)
const compliance = computed(() => explain.value?.compliance || {})
const fair = computed(() => explain.value?.fair_price_band || {})
const params = computed(() => explain.value?.params || {})
const channelMatrix = computed(() => {
  const fromExplain = explain.value?.channel_matrix
  if (Array.isArray(fromExplain) && fromExplain.length) return fromExplain
  const fromReco = props.reco?.channel_matrix
  return Array.isArray(fromReco) ? fromReco : []
})
const factorSum = computed(() =>
  factors.value.reduce((a: number, f: any) => a + Number(f.delta || 0), 0),
)
const netAnchor = computed(() => {
  const n = props.reco?.est_n ?? props.reco?.suggested_base ?? explain.value?.suggested_base
  return Number(n || 0)
})
const title = computed(() => {
  if (!props.reco) return ''
  return `${props.reco.room_type_name} · ${props.reco.stay_date} · ${channelLabel(props.reco.channel)}`
})

const narrative = ref('')
const narrateLoading = ref(false)
const narrateError = ref('')
const narrateMeta = ref<{
  model?: string
  provider?: string
  provider_label?: string
  source?: string
}>({})

/** 标题不写死品牌：用「大模型」+ 实际接入标识 */
const narrateTitle = computed(() => {
  if (narrateMeta.value.source && narrateMeta.value.source !== 'llm') return t('AI 暂不可用')
  return t('大模型推导说明')
})

const narrateLoadingText = computed(() => {
  const meta = formatAiModelMeta(narrateMeta.value)
  return meta ? t('正在调用 {meta} 生成推导说明…', { meta }) : t('正在调用大模型生成推导说明…')
})

async function loadNarrative() {
  if (!props.reco?.reco_id) return
  narrateLoading.value = true
  narrateError.value = ''
  narrative.value = ''
  narrateMeta.value = {}
  try {
    const r = await api.paNarrateExplain(props.reco.reco_id)
    narrative.value = r.narrative || ''
    narrateMeta.value = {
      model: r.model,
      provider: r.provider,
      provider_label: r.provider_label,
      source: r.source,
    }
  } catch (e: any) {
    narrateError.value = e?.message || t('大模型调用失败')
  } finally {
    narrateLoading.value = false
  }
}

watch(
  () => [props.open, props.reco?.reco_id] as const,
  ([open]) => {
    if (open && props.reco?.reco_id) loadNarrative()
  },
)
</script>

<template>
  <div v-if="open && reco" class="mask" @click.self="emit('close')">
    <div class="modal card-clean" role="dialog" aria-modal="true">
      <div class="head">
        <div>
          <div class="kicker">{{ t('推荐价算法推导') }}</div>
          <div class="ttl">{{ title }}</div>
        </div>
        <button type="button" class="x" @click="emit('close')">×</button>
      </div>

      <div v-if="!explain" class="empty">{{ t('暂无推导快照（请重新生成建议）') }}</div>
      <template v-else>
        <!-- 大模型白话说明（模型来自系统配置，本地/云端均可） -->
        <div class="ai-box">
          <div class="ai-h">
            <span class="material-symbols-outlined">smart_toy</span>
            {{ narrateTitle }}
            <span
              v-if="formatAiModelMeta(narrateMeta)"
              class="model-tag"
              :title="narrateMeta.provider || ''"
            >
              {{ formatAiModelMeta(narrateMeta) }}</span
            >
            <span
              v-if="narrateMeta.source && narrateMeta.source !== 'llm'"
              class="model-tag muted"
              >{{ t('未能调用大模型') }}</span
            >
            <button
              type="button"
              class="btn btn-ghost sm"
              :disabled="narrateLoading"
              @click="loadNarrative"
            >
              {{ narrateLoading ? t('生成中…') : t('重新生成') }}
            </button>
          </div>
          <div v-if="narrateLoading" class="ai-loading">{{ narrateLoadingText }}</div>
          <div v-else-if="narrateError && !narrative" class="ai-err">{{ narrateError }}</div>
          <div v-else-if="narrateMeta.source && narrateMeta.source !== 'llm'" class="ai-err">
            {{ t('未能调用大模型生成说明。下方定价快照仍是规则计算结果，不是 AI 结论。') }}
          </div>
          <div v-else class="ai-body">{{ localizePricingCopy(narrative) }}</div>
        </div>

        <div class="formula">
          <div>
            {{ t('基准价（房型基准挂牌价）＝') }}
            <b class="base">{{ fmt(explain.base_rate) }}</b>
          </div>
          <div class="src">{{ t('来源：房型基础价表 (room_type_base_rate) · 基准价字段') }}</div>
          <div class="sum-line">
            {{ t('基准价') }} {{ fmt(explain.base_rate) }} ＋ {{ t('各因子贡献（合计') }}
            {{ fmt(factorSum) }}）＝
            <b>{{ fmt(explain.suggested_price) }}</b>
          </div>
        </div>

        <div class="factors">
          <div class="factors-h">{{ t('因子分解') }}</div>
          <div v-for="(f, i) in factors" :key="i" class="factor" :class="{ muted: f.muted }">
            <span class="material-symbols-outlined chk" aria-hidden="true">check_box</span>
            <div class="main">
              <div class="name">{{ f.name }}</div>
              <div class="src">{{ f.source }}</div>
            </div>
            <div class="delta" :class="f.delta >= 0 ? 'up' : 'down'">
              {{ f.delta >= 0 ? '+' : '' }}{{ fmt(f.delta) }}
            </div>
          </div>
        </div>

        <div class="result">
          {{ t('＝ 建议本店在售价（净到手锚点）') }}
          <b>{{ fmt(netAnchor || explain.suggested_price) }}</b> {{ t('｜ 建议结算底价') }}
          <b>{{ fmt(explain.suggested_base) }}</b>
        </div>

        <div v-if="channelMatrix.length" class="chan-box">
          <div class="ap-h">{{ t('渠道分发（净价一致 · 净到手') }} ≈ {{ fmt(netAnchor) }}）</div>
          <table class="chan-tbl">
            <thead>
              <tr>
                <th>{{ t('渠道') }}</th>
                <th class="r">{{ t('佣金') }}</th>
                <th class="r guest">{{ t('挂价') }}</th>
                <th class="r">{{ t('净到手') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in channelMatrix" :key="row.channel">
                <td>{{ channelLabel(row.channel) }}</td>
                <td class="r">
                  {{
                    row.commission_pct ??
                    Math.round(Number(row.commission_rate || 0) * 10000) / 100
                  }}%
                </td>
                <td class="r guest">{{ fmt(row.channel_price) }}</td>
                <td class="r">{{ fmt(row.net_price ?? netAnchor) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="gates">
          <div class="g" :class="compliance.cap_ok ? 'ok' : 'warn'">
            <span class="gt">{{ compliance.cap_ok ? '✓' : '✗' }} {{ t('涨幅合规') }}</span>
            {{ compliance.daily_uplift_pct }}% / {{ t('封顶') }} +{{ compliance.cap_pct }}%
          </div>
          <div class="g" :class="compliance.cost_floor_ok ? 'ok' : 'warn'">
            <span class="gt">{{ compliance.cost_floor_ok ? '✓' : '✗' }} {{ t('不低于成本') }}</span>
            {{ t('底线') }} {{ fmt(compliance.cost_floor) }}
          </div>
          <div class="g" :class="compliance.n_floor_ok ? 'ok' : 'warn'">
            <span class="gt"
              >{{ compliance.n_floor_ok ? '✓' : '✗' }} {{ t('净到手') }} ≥ {{ t('下限') }}</span
            >
            {{ t('净到手') }} {{ fmt(compliance.n_est) }} ≥ {{ fmt(compliance.n_floor) }}
          </div>
        </div>

        <div
          class="fair"
          :class="{
            'fair-ok': fair.status === 'ok',
            'fair-event': fair.status === 'event',
            'fair-over': fair.status === 'over',
            'fair-under': fair.status === 'under',
            'fair-na': fair.status === 'na',
          }"
        >
          <span class="ft">{{ localizePricingCopy(fair.title) || t('公平价带') }}</span>
          {{ localizePricingCopy(fair.msg) }}
        </div>

        <div class="params">
          <div class="ap-h">{{ t('本次生效参数（随建议写入推导快照，可审计复现）') }}</div>
          <table>
            <tr>
              <td>{{ t('策略档位') }}</td>
              <td>
                {{ aggLabel(params.agg) || localizePricingCopy(params.agg_label) }} ×{{
                  params.agg_mult
                }}
              </td>
            </tr>
            <tr>
              <td>{{ t('活动系数（热度模型）') }}</td>
              <td>
                <template v-if="params.event_uplift_pct">
                  +{{ params.event_uplift_pct }}%
                  <span v-if="params.event_heat != null"
                    >（{{ t('热度') }} {{ params.event_heat }}）</span
                  >
                  · {{ t('硬上限') }} +{{ params.ev_cap }}%
                </template>
                <template v-else>{{
                  t('本次无事件 · 硬上限 +{cap}%', { cap: params.ev_cap })
                }}</template>
              </td>
            </tr>
            <tr>
              <td>{{ t('四档锚点 / 假期长度') }}</td>
              <td>
                {{ t('弱') }}{{ params.ev_weak }}/{{ t('中') }}{{ params.ev_mid }}/{{ t('强')
                }}{{ params.ev_strong }}/{{ t('爆') }}{{ params.ev_boom }}% · {{ t('短')
                }}{{ params.hol_short }}/{{ t('中') }}{{ params.hol_mid }}/{{ t('长')
                }}{{ params.hol_long }}%
              </td>
            </tr>
            <tr>
              <td>{{ t('涨幅封顶（日环比）') }}</td>
              <td>{{ t('+{pct}%（与活动因子硬上限独立）', { pct: params.cap_pct }) }}</td>
            </tr>
            <tr>
              <td>{{ t('成本底线') }}</td>
              <td>{{ t('基准价 × {pct}%', { pct: params.cost_pct }) }}</td>
            </tr>
            <tr>
              <td>{{ t('净到手下限') }}</td>
              <td>{{ fmt(params.n_floor) }}</td>
            </tr>
            <tr>
              <td>{{ t('公平价带') }}</td>
              <td>
                {{
                  t('事件日 +{ev}% / 平日 +{day}%', {
                    ev: params.fair_ev,
                    day: params.fair_day,
                  })
                }}
              </td>
            </tr>
            <tr>
              <td>{{ t('竞品权重 / 取整') }}</td>
              <td>{{ t('权重 {w} / {round} 元', { w: params.comp_w, round: params.round }) }}</td>
            </tr>
            <tr>
              <td>{{ t('竞品对比') }}</td>
              <td>{{ params.comp_compare_enabled ? t('开启') : t('关闭（内部推导）') }}</td>
            </tr>
          </table>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 16px;
}
.modal {
  width: min(600px, 96vw);
  max-height: 90vh;
  overflow: auto;
  padding: 0;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 14px 16px;
  border-bottom: 1px solid #e5e7eb;
}
.kicker {
  font-size: 13px;
  font-weight: 700;
}
.ttl {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-top: 2px;
}
.x {
  border: none;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
  line-height: 1;
}
.ai-box {
  margin: 14px 16px 0;
  border: 1px solid #e9d5ff;
  border-radius: 8px;
  background: #faf5ff;
  overflow: hidden;
}
.ai-h {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
  color: #7c3aed;
  border-bottom: 1px solid #e9d5ff;
  flex-wrap: wrap;
}
.ai-h .material-symbols-outlined {
  font-size: 18px;
}
.model-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  background: #ede9fe;
  color: #6d28d9;
}
.model-tag.muted {
  background: #f3f4f6;
  color: #6b7280;
}
.ai-h .sm {
  margin-left: auto;
  padding: 3px 8px;
  font-size: 11px;
}
.ai-loading,
.ai-err,
.ai-body {
  padding: 12px;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
}
.ai-loading {
  color: var(--on-surface-variant);
}
.ai-err {
  color: #dc2626;
}
.formula {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px 14px;
  margin: 14px 16px;
  font-size: 13px;
  line-height: 1.7;
}
.base {
  color: var(--primary);
}
.src {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.sum-line {
  margin-top: 6px;
  font-weight: 600;
}
.factors {
  padding: 0 16px 4px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.factors-h {
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface-variant);
  margin-bottom: 2px;
}
.factor {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  font-size: 12px;
  background: #f8fafc;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
}
.factor.muted {
  opacity: 0.65;
}
.factor .chk {
  font-size: 20px;
  color: #16a34a;
  flex-shrink: 0;
  font-variation-settings:
    'FILL' 1,
    'wght' 500,
    'GRAD' 0,
    'opsz' 20;
}
.main {
  flex: 1;
  min-width: 0;
}
.name {
  font-weight: 650;
  color: #0f172a;
  line-height: 1.4;
}
.src {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-top: 3px;
  line-height: 1.45;
}
.delta {
  font-weight: 700;
  white-space: nowrap;
  padding-top: 1px;
}
.delta.up {
  color: #dc2626;
}
.delta.down {
  color: #16a34a;
}
.result {
  margin: 10px 16px;
  padding: 10px 12px;
  background: #eef2ff;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.55;
}
.chan-box {
  margin: 0 16px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}
.chan-tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.chan-tbl th,
.chan-tbl td {
  padding: 6px 10px;
  border-bottom: 1px solid #f1f5f9;
}
.chan-tbl th.r,
.chan-tbl td.r {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.chan-tbl th.guest,
.chan-tbl td.guest {
  color: #1565c0;
  font-weight: 600;
}
.gates {
  display: flex;
  gap: 8px;
  padding: 0 16px;
  flex-wrap: wrap;
}
.g {
  flex: 1;
  min-width: 140px;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.5;
  border: 1px solid #e5e7eb;
}
.g.ok {
  background: #dcfce7;
  border-color: #16a34a;
  color: #16a34a;
}
.g.warn {
  background: #fef3c7;
  border-color: #d97706;
  color: #d97706;
}
.gt {
  font-weight: 700;
  display: block;
  margin-bottom: 2px;
}
.fair {
  margin: 10px 16px;
  padding: 9px 12px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.65;
  border: 1px solid #e5e7eb;
}
.ft {
  font-weight: 700;
  display: block;
  margin-bottom: 3px;
}
.fair-ok {
  background: #dcfce7;
  border-color: #16a34a;
  color: #16a34a;
}
.fair-event {
  background: #eef2ff;
  border-color: var(--primary);
  color: var(--primary);
}
.fair-over {
  background: #fef3c7;
  border-color: #d97706;
  color: #d97706;
}
.fair-under,
.fair-na {
  background: #f9fafb;
  color: var(--on-surface-variant);
}
.params {
  margin: 10px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}
.ap-h {
  background: #f8fafc;
  padding: 7px 10px;
  font-size: 11px;
  font-weight: 700;
  border-bottom: 1px solid #e5e7eb;
}
.params table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}
.params td {
  padding: 5px 10px;
  border-bottom: 1px solid #edf1f6;
}
.params td:first-child {
  color: var(--on-surface-variant);
  width: 110px;
}
.params td:nth-child(2) {
  font-weight: 600;
}
.empty {
  padding: 40px;
  text-align: center;
  color: var(--on-surface-variant);
}
</style>
