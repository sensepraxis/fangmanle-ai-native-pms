<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 采纳价格建议弹窗：双签工号 + 审计三联单 + 查看算法推导
 */
import { computed, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { fmt, toast } from '../../lib/ui'
import { channelLabel } from './labels'

const props = defineProps<{
  open: boolean
  reco: any | null
}>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'done'): void
  (e: 'explain'): void
}>()

const staffNo = ref('')
const staffNo2 = ref('')
const note = ref('')
const submitting = ref(false)

watch(
  () => props.open,
  (v) => {
    if (v) {
      staffNo.value = ''
      staffNo2.value = ''
      note.value = ''
    }
  },
)

const canAccept = computed(() => props.reco?.status === 'pending')
const reasons = computed(() => props.reco?.top_reasons || [])
const fair = computed(() => props.reco?.explain_json?.fair_price_band)
const channelMatrix = computed(() => {
  const m = props.reco?.channel_matrix || props.reco?.explain_json?.channel_matrix
  return Array.isArray(m) ? m : []
})
const netAnchor = computed(() => Number(props.reco?.est_n ?? props.reco?.suggested_base ?? 0))

async function confirm() {
  if (!props.reco) return
  if (!canAccept.value) {
    toast(t('当前状态不可采纳'), false)
    return
  }
  if ((staffNo.value || '').trim().length < 4) {
    toast(t('店长工号须 ≥4 位'), false)
    return
  }
  if ((staffNo2.value || '').trim().length < 4) {
    toast(t('值班经理工号须 ≥4 位'), false)
    return
  }
  if (staffNo.value.trim() === staffNo2.value.trim()) {
    toast(t('双签工号不可相同'), false)
    return
  }
  submitting.value = true
  try {
    await api.paDecide(props.reco.reco_id, {
      action: 'accept',
      staff_no: staffNo.value.trim(),
      staff_no2: staffNo2.value.trim(),
      note: note.value.trim(),
    })
    toast(t('已采纳 · 审计三联单已落库（不推线上渠道）'))
    emit('done')
    emit('close')
  } catch (e: any) {
    toast(e?.message || t('采纳失败'), false)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div v-if="open && reco" class="mask" @click.self="emit('close')">
    <div class="modal card-clean" role="dialog" aria-modal="true">
      <div class="modal-head">
        <div>
          <div class="kicker">
            <span class="material-symbols-outlined">verified</span>
            {{ t('采纳价格建议') }}
          </div>
          <div class="title">
            {{ reco.room_type_name }} · {{ reco.stay_date }} · {{ channelLabel(reco.channel) }}
          </div>
          <div class="rid">{{ reco.reco_id }} · {{ t('置信度') }} {{ reco.confidence }}</div>
        </div>
        <button type="button" class="x" @click="emit('close')">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>

      <div class="comparison">
        <div class="col">
          <div class="lbl">{{ t('采纳前 · 本店在售') }}</div>
          <div class="val cur">{{ fmt(reco.current_price) }}</div>
          <div class="sub">{{ t('净到手锚点') }}</div>
        </div>
        <div class="arrow">→</div>
        <div class="col">
          <div class="lbl">{{ t('采纳后 · 本店在售') }}</div>
          <div class="val new">{{ fmt(reco.suggested_price) }}</div>
          <div class="sub up">
            {{ reco.delta >= 0 ? '+' : '' }}{{ reco.delta_pct }}% · {{ t('净到手') }}
            {{ fmt(netAnchor || reco.est_n) }}
          </div>
        </div>
      </div>

      <div v-if="channelMatrix.length" class="chan-preview">
        <div class="lbl">{{ t('渠道挂价预览（净价一致，不自动跟价）') }}</div>
        <div class="chan-row">
          <span v-for="row in channelMatrix.slice(0, 6)" :key="row.channel" class="chan-pill">
            {{ channelLabel(row.channel) }} <b>{{ fmt(row.channel_price) }}</b>
          </span>
        </div>
      </div>

      <div class="mini-kpis">
        <div class="mk">
          <div class="l">{{ t('预估每间可售房收入') }}</div>
          <div class="v">
            {{ reco.est_revpar_delta >= 0 ? '+' : '' }}{{ fmt(reco.est_revpar_delta) }}
          </div>
        </div>
        <div class="mk">
          <div class="l">{{ t('预估入住率') }}</div>
          <div class="v">{{ reco.est_occ_pct }}%</div>
        </div>
        <div class="mk">
          <div class="l">{{ t('建议结算底价') }}</div>
          <div class="v">{{ fmt(reco.suggested_base) }}</div>
        </div>
        <div class="mk">
          <div class="l">{{ t('硬约束') }}</div>
          <div class="v ok">{{ t('✓ 通过') }}</div>
        </div>
      </div>

      <div v-if="fair && fair.status === 'over'" class="fair-warn">
        ⚠ {{ fair.title }}：{{ fair.msg }}（{{ t('软提示，不阻断采纳）') }}
      </div>

      <div class="reasons">
        <div class="lbl">{{ t('智能建议理由') }}</div>
        <ol>
          <li v-for="(r, i) in reasons" :key="i">{{ r }}</li>
        </ol>
      </div>

      <div class="field">
        <label>{{ t('店长工号') }} <span class="req">*</span>{{ t('（≥4 位）') }}</label>
        <input v-model="staffNo" type="text" maxlength="16" :placeholder="t('如：M2018')" />
      </div>
      <div class="field">
        <label>{{ t('值班经理工号') }} <span class="req">*</span>{{ t('（双签 ≥4 位）') }}</label>
        <input v-model="staffNo2" type="text" maxlength="16" :placeholder="t('如：M2035')" />
      </div>
      <div class="field">
        <label>{{ t('备注（可选）') }}</label>
        <input v-model="note" type="text" maxlength="200" :placeholder="t('店长备注')" />
      </div>

      <div class="audit">
        <b>{{ t('审计三联单') }}</b
        >{{ t('：建议单 → 决策单 → 效果单 · 留存 ≥7 年 ·') }}
        <b>{{ t('不写线上渠道、不自动跟价') }}</b>
      </div>

      <div class="actions">
        <button type="button" class="btn btn-ghost" @click="emit('explain')">
          {{ t('查看算法推导') }}
        </button>
        <span class="gap" />
        <button type="button" class="btn btn-ghost" @click="emit('close')">{{ t('取消') }}</button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="!canAccept || submitting"
          @click="confirm"
        >
          {{ submitting ? t('提交中…') : t('确认采纳') }}
        </button>
      </div>
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
  z-index: 90;
  padding: 16px;
}
.modal {
  width: min(560px, 96vw);
  max-height: 90vh;
  overflow: auto;
  padding: 0;
}
.modal-head {
  display: flex;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #e5e7eb;
}
.kicker {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--tertiary);
}
.title {
  font-size: 15px;
  font-weight: 650;
  margin-top: 4px;
}
.rid {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-top: 2px;
}
.x {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--on-surface-variant);
}
.comparison {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  justify-content: center;
}
.chan-preview {
  margin: 0 16px 12px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}
.chan-preview .lbl {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-bottom: 8px;
}
.chan-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chan-pill {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 6px;
  background: #fff;
  border: 1px solid #e5e7eb;
}
.chan-pill b {
  margin-left: 4px;
  font-variant-numeric: tabular-nums;
}
.col {
  text-align: center;
  padding: 12px 20px;
  background: #f9fafb;
  border-radius: 8px;
  min-width: 120px;
}
.lbl {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.val {
  font-size: 28px;
  font-weight: 700;
  margin-top: 4px;
}
.val.cur {
  color: #9ca3af;
  text-decoration: line-through;
}
.val.new {
  color: var(--primary);
}
.sub {
  font-size: 11px;
  margin-top: 4px;
  color: var(--on-surface-variant);
}
.sub.up {
  color: #16a34a;
}
.arrow {
  font-size: 22px;
  color: var(--on-surface-variant);
}
.mini-kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 0 16px 12px;
}
.mk {
  padding: 10px;
  border-radius: 6px;
  text-align: center;
  background: #f0fdf4;
}
.mk .l {
  font-size: 11px;
  color: #16a34a;
}
.mk .v {
  font-size: 16px;
  font-weight: 700;
  margin-top: 2px;
}
.mk .v.ok {
  color: #16a34a;
}
.fair-warn {
  margin: 0 16px 10px;
  padding: 8px 10px;
  background: #fef3c7;
  border: 1px solid #d97706;
  border-radius: 6px;
  font-size: 12px;
  color: #92400e;
  line-height: 1.5;
}
.reasons {
  margin: 0 16px 12px;
  padding: 10px;
  background: #f3e8ff;
  border-radius: 6px;
  border-left: 3px solid #9333ea;
  font-size: 12px;
}
.reasons .lbl {
  font-weight: 700;
  color: #9333ea;
  margin-bottom: 4px;
}
.reasons ol {
  margin: 4px 0 0;
  padding-left: 18px;
}
.field {
  padding: 0 16px 10px;
}
.field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
}
.req {
  color: #dc2626;
}
.field input {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 13px;
}
.audit {
  margin: 0 16px 12px;
  padding: 10px;
  background: #f8fafc;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--on-surface-variant);
}
.actions {
  display: flex;
  gap: 8px;
  padding: 12px 16px 16px;
  align-items: center;
  flex-wrap: wrap;
  border-top: 1px solid #e5e7eb;
}
.gap {
  flex: 1;
}
</style>
