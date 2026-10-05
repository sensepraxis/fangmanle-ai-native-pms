<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'
import { localizeSeedText } from '../lib/localizeSeed'

/**
 * 交班 / 接班 AI 草稿面板 — 生成 → 勾选 → 工号确认 → 写库
 */
import { computed, ref, watch } from 'vue'
import { formatAiModelMeta } from '../lib/aiModelMeta'
import { api } from '../lib/api'
import { commercialEnabled } from '../lib/branding'
import { hotelStore } from '../store/hotel'

function loc(s?: string | null) {
  return localizeSeedText(s)
}

function sourceLabel(code?: string) {
  const map: Record<string, string> = {
    oneid_history: '客史标签',
    restaurant_sys: '餐厅备注',
    feedback_sys: '客诉/客需',
    system_events: '本班事件',
    inventory_sys: '前台库存',
  }
  return t(map[code || ''] || '本班记录')
}

function categoryLabel(code?: string) {
  const map: Record<string, string> = {
    guest_situation: '客情',
    guest_focus: '客情关注',
    task: '待办',
    claim_hint: '承接建议',
    narrative: '口述摘要',
    takeover_brief: '接班要点',
    replenish: '补货',
    advice: '比对建议',
    diff_draft: '差异说明',
  }
  return t(map[code || ''] || code || '')
}

function typeBadge(code?: string) {
  const map: Record<string, string> = {
    vip: 'VIP 在店',
    special: '特殊需求',
    complaint: '客诉',
    inbound: '即将到店',
  }
  return t(map[code || ''] || '客情')
}

const props = defineProps<{
  handoverId: number
  scene: 'handover' | 'takeover'
  open?: boolean
}>()

const emit = defineEmits<{
  confirmed: []
  rejected: []
}>()

const loading = ref(false)
const confirming = ref(false)
const plan = ref<any>(null)
const staffId = ref('')
const confirmOpen = ref(false)

const title = computed(() => (props.scene === 'takeover' ? t('AI生成接班稿') : t('AI生成交班稿')))

const modelBadge = computed(() => {
  if (!plan.value) return ''
  if (plan.value.source === 'llm') return formatAiModelMeta(plan.value) || t('AI 建议')
  return t('AI 暂不可用')
})

const selectedCount = computed(
  () => (plan.value?.items || []).filter((it: any) => it.selected !== false).length,
)

async function generate() {
  if (!commercialEnabled()) return
  if (!props.handoverId) return
  loading.value = true
  plan.value = null
  try {
    const res = await api.shiftAiDraftGenerate(hotelStore.hotelId, props.handoverId, props.scene)
    plan.value = res?.data ?? res
  } catch (e: any) {
    plan.value = { error: e?.message || t('生成失败') }
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.handoverId, props.scene, props.open] as const,
  ([id, , open]) => {
    if (id && open !== false) generate()
  },
  { immediate: true },
)

function toggleAll(on: boolean) {
  for (const it of plan.value?.items || []) {
    it.selected = on
  }
}

function openConfirm() {
  if (plan.value?.source !== 'llm') return
  if (!selectedCount.value) return
  confirmOpen.value = true
}

async function confirm() {
  if (!plan.value || confirming.value) return
  confirming.value = true
  try {
    await api.shiftAiDraftConfirm(hotelStore.hotelId, props.handoverId, {
      plan: plan.value,
      approved_by_staff_id: staffId.value ? Number(staffId.value) : undefined,
    })
    confirmOpen.value = false
    emit('confirmed')
    await generate()
  } catch (e: any) {
    alert(e?.message || t('确认失败'))
  } finally {
    confirming.value = false
  }
}

async function rejectDraft() {
  try {
    await api.shiftAiDraftReject(hotelStore.hotelId, props.handoverId, {})
    plan.value = null
    emit('rejected')
  } catch {
    /* ignore */
  }
}

function editPayload(it: any, field: string, val: string) {
  if (it?.payload) it.payload[field] = val
}

function cardBadge(it: any) {
  if (it.category === 'guest_situation' || it.category === 'guest_focus') {
    return loc(it.payload?.type_label) || typeBadge(it.payload?.type)
  }
  return categoryLabel(it.category)
}

function cardTitle(it: any) {
  if (it.category === 'guest_situation' || it.category === 'guest_focus') {
    const who = it.payload?.guest_token
    const room = it.payload?.room_no
    if (who && room) return t('{guest} · {room} 房', { guest: loc(who), room })
    if (who) return loc(who)
  }
  return loc(it.label)
}

function cardSubtitle(it: any) {
  return loc(it.payload?.subtitle || '')
}

function cardNote(it: any) {
  return loc(it.payload?.note || it.payload?.content || it.reason || '')
}

function cardAction(it: any) {
  return loc(it.payload?.action || '')
}

function priorityTag(it: any) {
  const p = it.payload?.priority
  if (p === 'P0') return t('紧急')
  if (
    (it.category === 'guest_situation' || it.category === 'guest_focus') &&
    (it.payload?.type === 'vip' || it.payload?.type === 'complaint')
  ) {
    return t('重点')
  }
  if (it.selected !== false && it.confidence >= 0.88) return t('建议交')
  return ''
}
</script>

<template>
  <section v-if="commercialEnabled()" class="shift-ai-panel">
    <header class="head">
      <div>
        <span class="badge">AI</span>
        <strong>{{ title }}</strong>
        <span v-if="modelBadge" class="model-badge" :class="{ ok: plan?.source === 'llm' }">
          {{ modelBadge }}</span
        >
      </div>
      <button type="button" class="btn-ghost sm" :disabled="loading" @click="generate">
        {{ loading ? t('调用模型中…') : t('重新生成') }}
      </button>
    </header>

    <div v-if="loading" class="loading">{{ t('正在分析本班数据…') }}</div>
    <div v-else-if="plan?.error" class="err">{{ plan.error }}</div>

    <template v-else-if="plan?.items?.length">
      <div v-if="plan.situation" class="sit-board">
        <div v-if="plan.situation.metrics?.length" class="metric-grid">
          <div
            v-for="m in plan.situation.metrics"
            :key="m.key || m.label"
            class="metric-card"
            :class="m.tone || 'neutral'"
          >
            <span class="metric-label">{{ m.label }}</span>
            <span class="metric-value">{{ m.value }}</span>
            <span v-if="m.hint" class="metric-hint">{{ loc(m.hint) }}</span>
            <span v-if="m.label" class="metric-label">{{ loc(m.label) }}</span>
          </div>
        </div>
        <div
          v-else-if="plan.situation.headline || plan.situation.bullets?.length"
          class="metric-grid"
        >
          <div v-if="plan.situation.headline" class="metric-card neutral wide">
            <span class="metric-label">{{ t('概况') }}</span>
            <span class="metric-value sm">{{ loc(plan.situation.headline) }}</span>
          </div>
          <div
            v-for="(b, i) in plan.situation.bullets || []"
            :key="'b' + i"
            class="metric-card neutral"
          >
            <span class="metric-value sm">{{ loc(b) }}</span>
          </div>
        </div>

        <div v-if="plan.summary" class="sit-card sit-summary">
          <span class="sit-card-label">{{ t('本班要点') }}</span>
          <p>{{ loc(plan.summary) }}</p>
        </div>

        <div v-if="plan.reasons?.length" class="reason-grid">
          <div v-for="(r, i) in plan.reasons" :key="i" class="sit-card sit-reason">
            <span class="sit-card-label">{{ t('依据') }} {{ i + 1 }}</span>
            <p>{{ loc(r) }}</p>
          </div>
        </div>

        <span v-if="plan.source && plan.source !== 'llm'" class="warn-tag">
          {{ t('未能调用大模型，未生成 AI 草稿（规则数据不会冒充 AI）。') }}</span
        >
      </div>

      <div class="toolbar">
        <button type="button" class="link" @click="toggleAll(true)">{{ t('全选') }}</button>
        <button type="button" class="link" @click="toggleAll(false)">{{ t('全不选') }}</button>
        <span class="cnt">{{
          t('已选 {n} / {m}', { n: selectedCount, m: plan.items.length })
        }}</span>
      </div>

      <div class="card-grid">
        <article
          v-for="it in plan.items"
          :key="it.id"
          class="card"
          :class="{
            off: !it.selected,
            wide:
              it.op === 'write_narrative' ||
              it.op === 'write_takeover_brief' ||
              it.op === 'write_diff_draft' ||
              it.op === 'write_advice',
            [`cat-${it.category}`]: true,
          }"
          @click="it.selected = !it.selected"
        >
          <div class="card-top">
            <input v-model="it.selected" type="checkbox" class="card-check" @click.stop />
            <span class="cat">{{ cardBadge(it) }}</span>
            <span v-if="priorityTag(it)" class="prio">{{ priorityTag(it) }}</span>
          </div>
          <h4 class="lbl" :title="cardTitle(it)">{{ cardTitle(it) }}</h4>
          <p v-if="cardSubtitle(it)" class="subline">{{ cardSubtitle(it) }}</p>
          <dl class="fields">
            <div v-if="cardNote(it)" class="field">
              <dt>{{ t('注意') }}</dt>
              <dd :title="cardNote(it)">{{ cardNote(it) }}</dd>
            </div>
            <div v-if="cardAction(it)" class="field act">
              <dt>{{ t('接班') }}</dt>
              <dd :title="cardAction(it)">{{ cardAction(it) }}</dd>
            </div>
          </dl>
          <div class="card-meta">
            <span class="src">{{ sourceLabel(it.source) }}</span>
          </div>
          <textarea
            v-if="it.op === 'write_narrative' && it.selected"
            class="edit"
            :value="it.payload?.narrative"
            rows="3"
            @click.stop
            @input="editPayload(it, 'narrative', ($event.target as HTMLTextAreaElement).value)"
          />
          <textarea
            v-if="it.op === 'write_takeover_brief' && it.selected"
            class="edit"
            :value="it.payload?.brief"
            rows="3"
            @click.stop
            @input="editPayload(it, 'brief', ($event.target as HTMLTextAreaElement).value)"
          />
          <textarea
            v-if="it.op === 'write_diff_draft' && it.selected"
            class="edit"
            :value="it.payload?.reason"
            rows="3"
            @click.stop
            @input="editPayload(it, 'reason', ($event.target as HTMLTextAreaElement).value)"
          />
          <textarea
            v-if="it.op === 'write_advice' && it.selected"
            class="edit"
            :value="it.payload?.note"
            rows="2"
            @click.stop
            @input="editPayload(it, 'note', ($event.target as HTMLTextAreaElement).value)"
          />
        </article>
      </div>

      <div class="acts">
        <button type="button" class="btn-ghost" @click="rejectDraft">{{ t('驳回') }}</button>
        <button type="button" class="btn-primary" :disabled="!selectedCount" @click="openConfirm">
          {{ selectedCount ? t('确认（{n}）', { n: selectedCount }) : t('确认') }}
        </button>
      </div>
    </template>

    <div v-else-if="plan && !plan.items?.length" class="empty">
      {{ t('暂无可用草稿项。') }}
    </div>

    <div v-if="confirmOpen" class="modal-mask" @click.self="confirmOpen = false">
      <div class="modal">
        <h3>{{ scene === 'takeover' ? t('确认写入接班') : t('确认写入交班') }}</h3>
        <p>
          {{
            scene === 'takeover'
              ? t('将把已选的 {n} 项写入接班记录，并标记为 AI 辅助生成。', { n: selectedCount })
              : t('将把已选的 {n} 项写入交班记录，并标记为 AI 辅助生成。', { n: selectedCount })
          }}
          {{ t('资金数、实盘与签字不会被改写。') }}
        </p>
        <label class="fld">
          {{ t('确认人工号') }}
          <input v-model="staffId" class="inp full" :placeholder="t('留空则使用当前登录账号')" />
        </label>
        <div class="modal-acts">
          <button type="button" class="btn-ghost" @click="confirmOpen = false">
            {{ t('取消') }}
          </button>
          <button type="button" class="btn-primary" :disabled="confirming" @click="confirm">
            {{ confirming ? t('提交中…') : t('确认') }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.shift-ai-panel {
  border: 1px solid #e8def8;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 16px;
  background: linear-gradient(180deg, #faf8ff 0%, #fff 100%);
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: #6750a4;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  margin-right: 8px;
}
.model-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  background: #e7e0ec;
  color: #49454f;
  vertical-align: middle;
}
.model-badge.ok {
  background: #e8f5e9;
  color: #2e7d32;
}
.model-badge.warn {
  background: #fff8e1;
  color: #8a5a11;
}
.loading,
.empty,
.err {
  font-size: 13px;
  color: #79747e;
  padding: 8px 0;
}
.err {
  color: #c5221f;
}
.warn-tag {
  display: inline-block;
  margin-top: 8px;
  font-size: 11px;
  color: #8a5a11;
  background: #fff8e1;
  padding: 2px 8px;
  border-radius: 4px;
}

.sit-board {
  margin-bottom: 12px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: 8px;
  margin-bottom: 8px;
}
.metric-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #e7e0ec;
  background: #fff;
  min-height: 72px;
}
.metric-card.wide {
  grid-column: 1 / -1;
}
.metric-card.neutral {
  background: #fff;
}
.metric-card.info {
  background: linear-gradient(180deg, #f0f7ff 0%, #fff 100%);
  border-color: #c5dbf5;
}
.metric-card.warn {
  background: linear-gradient(180deg, #fff8f0 0%, #fff 100%);
  border-color: #f0d5b8;
}
.metric-card.danger {
  background: linear-gradient(180deg, #fff5f5 0%, #fff 100%);
  border-color: #f0c2c2;
}
.metric-label {
  font-size: 11px;
  font-weight: 600;
  color: #79747e;
  letter-spacing: 0.02em;
}
.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: #1c1b1f;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}
.metric-value.sm {
  font-size: 13px;
  font-weight: 600;
}
.metric-hint {
  font-size: 11px;
  color: #9e9e9e;
}

.sit-card {
  border: 1px solid #e7e0ec;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
}
.sit-summary {
  margin-bottom: 8px;
  background: linear-gradient(135deg, #faf8ff 0%, #fff 70%);
  border-color: #e0d4f5;
}
.sit-card-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: #6750a4;
  margin-bottom: 4px;
}
.sit-card p {
  margin: 0;
  font-size: 13px;
  color: #1c1b1f;
  line-height: 1.45;
}
.reason-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 8px;
}
.sit-reason .sit-card-label {
  color: #79747e;
}
.sit-reason p {
  font-size: 12px;
  color: #49454f;
}

.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 12px;
  margin-bottom: 10px;
}
.link {
  background: none;
  border: none;
  color: #6750a4;
  cursor: pointer;
  font-size: 12px;
}
.cnt {
  margin-left: auto;
  color: #79747e;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  margin-bottom: 4px;
}
.card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 148px;
  padding: 10px 12px;
  border: 1px solid #e7e0ec;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition:
    border-color 0.15s,
    box-shadow 0.15s,
    opacity 0.15s,
    transform 0.12s;
}
.card:hover {
  border-color: #c9b6e8;
  box-shadow: 0 2px 8px rgba(103, 80, 164, 0.08);
  transform: translateY(-1px);
}
.card.off {
  opacity: 0.48;
  background: #fafafa;
}
.card.wide {
  grid-column: 1 / -1;
  min-height: auto;
}
.card-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.card-check {
  flex-shrink: 0;
  accent-color: #6750a4;
  cursor: pointer;
}
.cat {
  font-size: 11px;
  font-weight: 600;
  background: #e8def8;
  color: #6750a4;
  padding: 1px 7px;
  border-radius: 4px;
  line-height: 1.5;
}
.cat-guest_situation .cat {
  background: #e3f2fd;
  color: #1565c0;
}
.cat-task .cat {
  background: #fff3e0;
  color: #e65100;
}
.cat-replenish .cat {
  background: #e8f5e9;
  color: #2e7d32;
}
.cat-narrative .cat,
.cat-takeover_brief .cat {
  background: #f3e5f5;
  color: #7b1fa2;
}
.cat-guest_focus .cat {
  background: #e3f2fd;
  color: #1565c0;
}
.cat-claim_hint .cat {
  background: #fff3e0;
  color: #e65100;
}
.cat-advice .cat {
  background: #e0f2f1;
  color: #00695c;
}
.cat-diff_draft .cat {
  background: #fce4ec;
  color: #c62828;
}
.prio {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  color: #b45309;
  background: #fff7ed;
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}
.lbl {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #1c1b1f;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.subline {
  margin: 0;
  font-size: 12px;
  color: #6750a4;
  font-weight: 600;
}
.fields {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
.field {
  display: grid;
  grid-template-columns: 32px 1fr;
  gap: 6px;
  align-items: start;
  font-size: 12px;
  line-height: 1.4;
}
.field dt {
  margin: 0;
  color: #9e9e9e;
  font-weight: 600;
  font-size: 11px;
  padding-top: 1px;
}
.field dd {
  margin: 0;
  color: #49454f;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.field.act dd {
  color: #1c1b1f;
  font-weight: 500;
}
.card-meta {
  margin-top: auto;
}
.src {
  font-size: 11px;
  color: #9e9e9e;
}
.edit {
  width: 100%;
  margin-top: 4px;
  font-size: 12px;
  border: 1px solid #e7e0ec;
  border-radius: 6px;
  padding: 8px;
  resize: vertical;
  box-sizing: border-box;
  font-family: inherit;
}
.acts {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 14px;
  flex-wrap: wrap;
}
.btn-primary,
.btn-ghost {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  line-height: 1.2;
  transition:
    background-color 0.12s,
    border-color 0.12s,
    opacity 0.12s;
}
.btn-primary {
  background: #6750a4;
  color: #fff;
  border: none;
}
.btn-primary:hover:not(:disabled) {
  background: #5a4590;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-ghost {
  background: #fff;
  border: 1px solid #cac4d0;
  color: #1c1b1f;
}
.btn-ghost:hover:not(:disabled) {
  background: #f7f2fa;
}
.btn-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-ghost.sm {
  font-size: 12px;
  padding: 6px 12px;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  max-width: 420px;
  width: 90%;
}
.modal h3 {
  margin: 0 0 8px;
  font-size: 16px;
}
.modal p {
  margin: 0;
  font-size: 13px;
  color: #49454f;
  line-height: 1.5;
}
.fld {
  display: block;
  font-size: 12px;
  margin: 12px 0;
  color: #49454f;
}
.inp.full {
  width: 100%;
  margin-top: 4px;
  padding: 8px 10px;
  border: 1px solid #cac4d0;
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
  box-sizing: border-box;
}
.modal-acts {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
