<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 定价干活侧栏：从日历点开某日建议 → 确认 / 驳回 / 看推导
 */
import { computed, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { fmt, toast } from '../../lib/ui'
import { channelLabel, localizePricingCopy } from './labels'

const props = defineProps<{
  open: boolean
  reco: any | null
  loading?: boolean
  compOn?: boolean
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
/** 点「确认采纳」后才进入双签填写 */
const signing = ref(false)

watch(
  () => [props.open, props.reco?.reco_id],
  () => {
    staffNo.value = ''
    staffNo2.value = ''
    note.value = ''
    signing.value = false
  },
)

const canAccept = computed(() => props.reco?.status === 'pending')
const reasons = computed(() => {
  const raw = props.reco?.top_reasons || props.reco?.reasons || []
  const list = Array.isArray(raw) ? raw : [raw]
  return list.map((r) => localizePricingCopy(String(r || ''))).filter(Boolean)
})
const fair = computed(() => props.reco?.explain_json?.fair_price_band)
const channelMatrix = computed(() => {
  const m = props.reco?.channel_matrix || props.reco?.explain_json?.channel_matrix
  return Array.isArray(m) ? m : []
})
const netAnchor = computed(() => Number(props.reco?.est_n ?? props.reco?.suggested_base ?? 0))

const signals = computed(() => {
  const f = props.reco?.features_snapshot || {}
  return {
    comp: f.comp_median ?? f.signals?.comp,
    occ: f.occ_pct ?? f.signals?.occ,
    inv: f.rem_rooms ?? f.signals?.inv,
    pace: f.signals?.pace ?? (f.pace?.pace_ratio ? Math.round(f.pace.pace_ratio * 100) : null),
  }
})

function startSign() {
  if (!canAccept.value) {
    toast(t('当前状态不可采纳'), false)
    return
  }
  signing.value = true
}

function cancelSign() {
  signing.value = false
  staffNo.value = ''
  staffNo2.value = ''
  note.value = ''
}

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
    signing.value = false
    emit('done')
    emit('close')
  } catch (e: any) {
    toast(e?.message || t('采纳失败'), false)
  } finally {
    submitting.value = false
  }
}

async function reject() {
  if (!props.reco) return
  try {
    await api.paDecide(props.reco.reco_id, {
      action: 'reject',
      staff_no: 'view',
      note: note.value.trim() || t('店长驳回'),
    })
    toast(t('已驳回'))
    emit('done')
    emit('close')
  } catch (e: any) {
    toast(e?.message || t('驳回失败'), false)
  }
}
</script>

<template>
  <aside class="drawer" :class="{ open }" :aria-label="t('待确认调价建议')">
    <div class="drawer-head">
      <div>
        <div class="kicker">{{ t('待确认调价') }}</div>
        <div v-if="reco" class="title">{{ reco.room_type_name }} · {{ reco.stay_date }}</div>
        <div v-else class="title muted">{{ t('点击日历格子') }}</div>
      </div>
      <button type="button" class="x" :disabled="!open" @click="emit('close')">
        <span class="material-symbols-outlined">close</span>
      </button>
    </div>

    <div v-if="loading" class="body empty">{{ t('加载建议详情…') }}</div>
    <div v-else-if="!reco" class="body empty">
      {{ t('在左侧日历点选某日价格，这里打开该日的') }} <strong>{{ t('待确认建议') }}</strong
      >{{ t('，完成双签采纳或驳回。') }}
    </div>
    <div v-else class="body">
      <div class="meta">
        {{ channelLabel(reco.channel) }} · {{ t('置信度') }}
        {{
          ['高', 'high', 'High'].includes(String(reco.confidence))
            ? t('高')
            : ['中', 'medium', 'mid', 'Med', 'Medium'].includes(String(reco.confidence))
              ? t('中')
              : ['低', 'low', 'Low'].includes(String(reco.confidence))
                ? t('低')
                : reco.confidence || '—'
        }}
        <span v-if="reco.status" class="st">{{
          reco.status === 'pending' ? t('待采纳') : reco.status
        }}</span>
      </div>

      <div class="comparison">
        <div class="col">
          <div class="lbl">{{ t('当前在售') }}</div>
          <div class="val cur">{{ fmt(reco.current_price) }}</div>
        </div>
        <div class="arrow">→</div>
        <div class="col">
          <div class="lbl">{{ t('建议价') }}</div>
          <div class="val new" :class="(reco.delta || 0) >= 0 ? 'up' : 'down'">
            {{ fmt(reco.suggested_price) }}
          </div>
          <div class="sub" :class="(reco.delta || 0) >= 0 ? 'up' : 'down'">
            {{ (reco.delta || 0) >= 0 ? '+' : '' }}{{ reco.delta_pct }}% · {{ t('净到手') }}
            {{ fmt(netAnchor) }}
          </div>
        </div>
      </div>

      <div class="sigs">
        <span v-if="compOn && signals.comp != null" class="sig"
          >{{ t('竞品中位') }} <b>{{ fmt(signals.comp) }}</b></span
        >
        <span class="sig"
          >{{ t('在住') }} <b>{{ signals.occ != null ? signals.occ + '%' : '—' }}</b></span
        >
        <span class="sig"
          >{{ t('库存') }} <b>{{ signals.inv != null ? signals.inv + t('间') : '—' }}</b></span
        >
        <span class="sig"
          >{{ t('预订进度') }} <b>{{ signals.pace != null ? signals.pace + '%' : '—' }}</b></span
        >
      </div>

      <div v-if="channelMatrix.length" class="chan-preview">
        <div class="lbl">{{ t('渠道挂价预览') }}</div>
        <div class="chan-row">
          <span v-for="row in channelMatrix.slice(0, 6)" :key="row.channel" class="chan-pill">
            {{ channelLabel(row.channel) }} <b>{{ fmt(row.channel_price) }}</b>
          </span>
        </div>
      </div>

      <div class="mini-kpis">
        <div class="mk">
          <div class="l">{{ t('RevPAR 影响') }}</div>
          <div class="v">
            {{ (reco.est_revpar_delta || 0) >= 0 ? '+' : '' }}{{ fmt(reco.est_revpar_delta) }}
          </div>
        </div>
        <div class="mk">
          <div class="l">{{ t('预估入住') }}</div>
          <div class="v">{{ reco.est_occ_pct != null ? reco.est_occ_pct + '%' : '—' }}</div>
        </div>
      </div>

      <div v-if="fair && fair.status === 'over'" class="fair-warn">
        ⚠ {{ fair.title }}：{{ fair.msg }}
      </div>

      <div v-if="reasons.length" class="reasons">
        <div class="lbl">{{ t('建议理由') }}</div>
        <div class="reason-list">
          <div v-for="(r, i) in reasons" :key="i" class="reason-row">
            <span class="material-symbols-outlined chk" aria-hidden="true">check_box</span>
            <span class="reason-text">{{ r }}</span>
          </div>
        </div>
      </div>

      <template v-if="canAccept && signing">
        <div class="sign-box">
          <div class="sign-h">{{ t('双签确认采纳') }}</div>
          <div class="field">
            <label>{{ t('店长工号') }} <span class="req">*</span></label>
            <input
              v-model="staffNo"
              type="text"
              maxlength="16"
              :placeholder="t('≥4 位')"
              autofocus
            />
          </div>
          <div class="field">
            <label>{{ t('值班经理工号') }} <span class="req">*</span></label>
            <input v-model="staffNo2" type="text" maxlength="16" :placeholder="t('双签 ≥4 位')" />
          </div>
          <div class="field">
            <label>{{ t('备注（可选）') }}</label>
            <input v-model="note" type="text" maxlength="200" :placeholder="t('店长备注')" />
          </div>
          <p class="audit">{{ t('采纳后写审计三联单 · 不推线上渠道、不自动跟价') }}</p>
        </div>
      </template>
      <p v-else-if="!canAccept" class="audit">{{ t('该建议已处理，仅可查看。') }}</p>
    </div>

    <div v-if="reco" class="foot">
      <template v-if="signing">
        <button type="button" class="btn btn-ghost" :disabled="submitting" @click="cancelSign">
          {{ t('取消') }}
        </button>
        <span class="gap" />
        <button type="button" class="btn btn-primary" :disabled="submitting" @click="confirm">
          {{ submitting ? t('提交中…') : t('提交采纳') }}
        </button>
      </template>
      <template v-else>
        <button type="button" class="btn btn-ghost" @click="emit('explain')">
          {{ t('推导') }}
        </button>
        <button
          v-if="canAccept"
          type="button"
          class="btn btn-ghost"
          :disabled="submitting"
          @click="reject"
        >
          {{ t('驳回') }}
        </button>
        <span class="gap" />
        <button v-if="canAccept" type="button" class="btn btn-primary" @click="startSign">
          {{ t('确认采纳') }}
        </button>
      </template>
    </div>
  </aside>
</template>

<style scoped>
.drawer {
  display: flex;
  flex-direction: column;
  width: 360px;
  max-width: 100%;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #d0d7e2;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.06);
  min-height: 420px;
  max-height: calc(100vh - 180px);
  position: sticky;
  top: 12px;
  overflow: hidden;
  opacity: 0.92;
}
.drawer.open {
  opacity: 1;
  border-color: color-mix(in srgb, var(--primary, #2563eb) 35%, #d0d7e2);
}
.drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 14px 10px;
  border-bottom: 1px solid #e6ebf2;
}
.kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--primary, #2563eb);
  margin-bottom: 4px;
}
.title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
}
.title.muted {
  font-weight: 600;
  color: #94a3b8;
}
.x {
  border: none;
  background: #f3f4f6;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  flex-shrink: 0;
}
.x .material-symbols-outlined {
  font-size: 18px;
}
.body {
  flex: 1;
  overflow: auto;
  padding: 12px 14px 8px;
}
.body.empty {
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
  padding-top: 24px;
}
.meta {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.st {
  background: #eff4ff;
  color: #1d4ed8;
  font-weight: 650;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
}
.comparison {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e6ebf2;
  margin-bottom: 12px;
}
.col {
  flex: 1;
  min-width: 0;
}
.lbl {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
  margin-bottom: 4px;
}
.val {
  font-size: 20px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.val.cur {
  color: #475569;
}
.val.new.up {
  color: #16a34a;
}
.val.new.down {
  color: #dc2626;
}
.arrow {
  color: #94a3b8;
  font-weight: 700;
}
.sub {
  font-size: 11px;
  margin-top: 2px;
}
.sub.up {
  color: #16a34a;
}
.sub.down {
  color: #dc2626;
}
.sigs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.sig {
  font-size: 11px;
  background: #f1f5f9;
  padding: 4px 8px;
  border-radius: 6px;
  color: #475569;
}
.sig b {
  color: #0f172a;
}
.chan-preview {
  margin-bottom: 12px;
}
.chan-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chan-pill {
  font-size: 11px;
  background: #fff;
  border: 1px solid #e6ebf2;
  border-radius: 999px;
  padding: 4px 8px;
  color: #64748b;
}
.chan-pill b {
  color: #0f172a;
  margin-left: 4px;
}
.mini-kpis {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}
.mk {
  padding: 8px 10px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #eef2f7;
}
.mk .l {
  font-size: 10.5px;
  color: #94a3b8;
}
.mk .v {
  font-size: 14px;
  font-weight: 700;
  margin-top: 2px;
}
.fair-warn {
  font-size: 12px;
  color: #92400e;
  background: #fef3c7;
  padding: 8px 10px;
  border-radius: 8px;
  margin-bottom: 10px;
}
.reasons {
  margin-bottom: 12px;
}
.reason-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 6px;
}
.reason-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
}
.reason-row .chk {
  font-size: 20px;
  color: #16a34a;
  flex-shrink: 0;
  margin-top: 0;
  font-variation-settings:
    'FILL' 1,
    'wght' 500,
    'GRAD' 0,
    'opsz' 20;
}
.reason-text {
  font-size: 12.5px;
  line-height: 1.5;
  color: #334155;
  font-weight: 550;
}
.sign-box {
  margin-top: 4px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e6ebf2;
  border-radius: 10px;
}
.sign-h {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 10px;
}
.field {
  margin-bottom: 10px;
}
.field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #475569;
}
.req {
  color: #dc2626;
}
.field input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
}
.audit {
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.5;
  margin: 0 0 4px;
}
.foot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px 14px;
  border-top: 1px solid #e6ebf2;
  background: #fff;
}
.gap {
  flex: 1;
}
.btn {
  border-radius: 8px;
  padding: 7px 12px;
  font-size: 12.5px;
  font-weight: 650;
  cursor: pointer;
  font-family: inherit;
  border: 1px solid #e6ebf2;
  background: #fff;
}
.btn-ghost {
  color: #475569;
}
.btn-primary {
  background: var(--primary, #2563eb);
  border-color: var(--primary, #2563eb);
  color: #fff;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (max-width: 960px) {
  .drawer {
    width: 100%;
    max-height: none;
    position: static;
  }
}
</style>
