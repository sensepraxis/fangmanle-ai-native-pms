<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * AI 定价建议（核心）：按本店全部房型切换 + 信号 + 采纳/驳回/推导
 */
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { fmt, toast } from '../../lib/ui'
import AcceptModal from './AcceptModal.vue'
import ExplainModal from './ExplainModal.vue'
import { channelLabel } from './labels'

const props = defineProps<{ compOn: boolean }>()

const rows = ref<any[]>([])
const hotelRoomTypes = ref<{ id: number; name: string }[]>([])
const loading = ref(false)
/** '' = 全部房型；否则按房型名筛选 */
const roomFilter = ref('')
const modalOpen = ref(false)
const explainOpen = ref(false)
const active = ref<any>(null)
const batchStaff = ref('')
const batchStaff2 = ref('')

async function load() {
  loading.value = true
  try {
    const hid = hotelStore.hotelId
    const [recs, rts] = await Promise.all([
      api.paRecommendations(hid, { status: 'pending' }),
      api.listRoomTypes(hid).catch(() => []),
    ])
    rows.value = recs
    hotelRoomTypes.value = (rts || [])
      .map((r: any) => ({ id: Number(r.id ?? r.room_type_id), name: String(r.name || '').trim() }))
      .filter((r: { id: number; name: string }) => r.id && r.name)
    // 默认落到第一个本店房型（有建议优先），避免「看不到分房型」
    if (!roomFilter.value) {
      const withPending = hotelRoomTypes.value.find((rt) =>
        rows.value.some((r) => r.room_type_name === rt.name),
      )
      roomFilter.value = withPending?.name || hotelRoomTypes.value[0]?.name || ''
    }
  } catch (e: any) {
    toast(e?.message || t('加载失败'), false)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(
  () => hotelStore.hotelId,
  () => {
    roomFilter.value = ''
    load()
  },
)

/** 本店全部房型；若主数据为空则回退到建议里出现过的名称 */
const roomTabs = computed(() => {
  if (hotelRoomTypes.value.length) return hotelRoomTypes.value.map((r) => r.name)
  const s = new Set(rows.value.map((r) => r.room_type_name).filter(Boolean))
  return Array.from(s)
})

function pendingCount(name: string) {
  return rows.value.filter((r) => r.room_type_name === name).length
}

const filtered = computed(() =>
  rows.value.filter((r) => !roomFilter.value || r.room_type_name === roomFilter.value),
)

const kpi = computed(() => {
  const list = filtered.value
  if (!list.length) {
    return { n: 0, up: 0, impactSum: 0, impactAvg: 0, pace: '—' }
  }
  const up = list.filter((r) => r.delta > 0).length
  const impactSum = Math.round(list.reduce((a, r) => a + Number(r.est_revpar_delta || 0), 0))
  const impactAvg = Math.round(impactSum / list.length)
  const paces = list.map((r) => r.features_snapshot?.pace?.pace_ratio).filter(Boolean)
  const paceAvg = paces.length
    ? (paces.reduce((a: number, b: number) => a + b, 0) / paces.length).toFixed(2)
    : '—'
  return { n: list.length, up, impactSum, impactAvg, pace: paceAvg }
})

function signedYen(n: number) {
  return `${n >= 0 ? '+' : ''}¥${n}`
}

function sig(r: any) {
  const f = r.features_snapshot || {}
  return {
    comp: f.comp_median ?? f.signals?.comp,
    occ: f.occ_pct ?? f.signals?.occ,
    inv: f.rem_rooms ?? f.signals?.inv,
    pace: f.signals?.pace ?? (f.pace?.pace_ratio ? Math.round(f.pace.pace_ratio * 100) : null),
  }
}

function openAccept(r: any) {
  active.value = r
  modalOpen.value = true
}

function openExplain(r: any) {
  active.value = r
  explainOpen.value = true
}

async function reject(r: any) {
  try {
    await api.paDecide(r.reco_id, { action: 'reject', staff_no: 'view', note: '店长驳回' })
    toast(t('已驳回'))
    load()
  } catch (e: any) {
    toast(e?.message || t('驳回失败'), false)
  }
}

async function generate() {
  try {
    // dense：各房型每日都落建议，避免小幅变价被跳过导致「看起来只有一个房型」
    const r = await api.paGenerate(hotelStore.hotelId, { days: 14, force: true, dense: true })
    toast(t('已生成 {n} 条建议（覆盖本店各房型）', { n: r.created }))
    await load()
  } catch (e: any) {
    toast(e?.message || t('生成失败'), false)
  }
}

async function batchAccept() {
  const ids = filtered.value
    .filter((r) => r.status === 'pending')
    .slice(0, 7)
    .map((r) => r.reco_id)
  if (!ids.length) {
    toast(t('当前房型无待采纳建议'), false)
    return
  }
  if ((batchStaff.value || '').trim().length < 4 || (batchStaff2.value || '').trim().length < 4) {
    toast(t('批量采纳须双签工号 ≥4 位'), false)
    return
  }
  try {
    await api.paBatchDecide(hotelStore.hotelId, {
      reco_ids: ids,
      action: 'accept',
      staff_no: batchStaff.value.trim(),
      staff_no2: batchStaff2.value.trim(),
    })
    toast(t('批量采纳 {n} 条', { n: ids.length }))
    load()
  } catch (e: any) {
    toast(e?.message || t('批量失败'), false)
  }
}

function reasonLine(r: any) {
  return (r.top_reasons || []).slice(0, 2).join(' · ')
}
</script>

<template>
  <div>
    <div class="compliance">
      <span class="icon">⚖</span>
      <div>
        <b>{{ t('合规底线') }}</b
        >{{ t('：所有调价建议须经店长人工采纳并工号二次确认（双人双签）。系统')
        }}<b>{{ t('绝不') }}</b
        >{{ t('直接改价、') }}<b>{{ t('绝不') }}</b
        >{{ t('自动跟价。') }}
        <span v-if="!compOn" class="muted">{{ t('（当前未开启竞品对比 · 内部基准模式）') }}</span>
      </div>
    </div>

    <div class="rtabs">
      <button
        type="button"
        class="rtab"
        :class="{ on: roomFilter === '' }"
        @click="roomFilter = ''"
      >
        {{ t('全部') }}
        <span class="cnt">{{ rows.length }}</span>
      </button>
      <button
        v-for="name in roomTabs"
        :key="name"
        type="button"
        class="rtab"
        :class="{ on: roomFilter === name }"
        @click="roomFilter = name"
      >
        {{ name }}
        <span class="cnt">{{ pendingCount(name) }}</span>
      </button>
      <div class="gap" />
      <button type="button" class="btn btn-ghost sm" @click="generate">{{ t('重新生成') }}</button>
    </div>
    <p v-if="!roomTabs.length" class="rt-hint">
      {{ t('本店尚未配置房型主数据，建议按渠道/日期汇总展示。') }}
    </p>

    <div class="kpi-row">
      <div class="kpi card-clean">
        <div class="label">{{ t('待处理建议') }}</div>
        <div class="value">{{ kpi.n }}</div>
      </div>
      <div class="kpi card-clean">
        <div class="label">{{ t('建议上调') }}</div>
        <div class="value">{{ kpi.up }}</div>
      </div>
      <div class="kpi card-clean">
        <div class="label">{{ t('预订进度均值') }}</div>
        <div class="value">{{ kpi.pace }}</div>
      </div>
      <div class="kpi card-clean kpi-impact">
        <div class="label">{{ t('预估日均影响') }}</div>
        <div class="value" :class="kpi.impactAvg >= 0 ? 'up' : 'down'">
          {{ signedYen(kpi.impactAvg) }}
        </div>
        <div v-if="kpi.n" class="calc">
          <div class="calc-line">
            {{ t('合计') }} {{ signedYen(kpi.impactSum) }} ÷ {{ kpi.n }} {{ t('条') }} =
            {{ t('日均') }} {{ signedYen(kpi.impactAvg) }}
          </div>
          <div class="calc-hint">{{ t('单条 ≈ (建议价 − 当前价) × 入住率预测') }}</div>
        </div>
      </div>
    </div>

    <div class="card-clean table-card">
      <div class="card-head">
        <span class="title">{{ roomFilter || t('全部') }} · {{ t('单日调价建议') }}</span>
        <span class="gap" />
        <input v-model="batchStaff" class="mini" :placeholder="t('店长工号')" maxlength="16" />
        <input v-model="batchStaff2" class="mini" :placeholder="t('值班经理')" maxlength="16" />
        <button type="button" class="btn btn-primary sm" @click="batchAccept">
          {{ t('批量采纳本房型') }}
        </button>
      </div>

      <div v-if="loading" class="empty">{{ t('加载中…') }}</div>
      <table v-else>
        <thead>
          <tr>
            <th>{{ t('日期') }}</th>
            <th>{{ t('本店在售（净到手锚点）') }}</th>
            <th>{{ t('智能参考信号') }}</th>
            <th style="width: 160px">{{ t('操作') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in filtered" :key="r.reco_id" @click="openExplain(r)" class="clickable">
            <td>
              <div class="dt">{{ r.stay_date?.slice(5) }}</div>
              <div class="ch">{{ channelLabel(r.channel) }}</div>
            </td>
            <td>
              <span class="cur">{{ fmt(r.current_price) }}</span>
              →
              <span class="new" :class="r.delta >= 0 ? 'up' : 'down'">{{
                fmt(r.suggested_price)
              }}</span>
              <span class="chg" :class="r.delta >= 0 ? 'up' : 'down'">
                {{ r.delta >= 0 ? '+' : '' }}{{ r.delta_pct }}%
              </span>
              <div class="net">
                {{ t('净到手') }} {{ fmt(r.est_n ?? r.suggested_base) }} ·
                {{ t('各渠道挂价按佣金换算') }}
              </div>
              <div class="reason">{{ reasonLine(r) }}</div>
            </td>
            <td>
              <div class="sigs">
                <span v-if="compOn && sig(r).comp != null" class="sig comp"
                  >{{ t('竞品中位') }} <b>{{ fmt(sig(r).comp) }}</b></span
                >
                <span v-else class="sig">{{ t('竞品 —') }}</span>
                <span class="sig occ"
                  >{{ t('在住') }} <b>{{ sig(r).occ != null ? sig(r).occ + '%' : '—' }}</b></span
                >
                <span class="sig inv"
                  >{{ t('库存') }}
                  <b>{{ sig(r).inv != null ? sig(r).inv + t('间') : '—' }}</b></span
                >
                <span class="sig sale"
                  >{{ t('预订进度') }}
                  <b>{{ sig(r).pace != null ? sig(r).pace + '%' : '—' }}</b></span
                >
              </div>
            </td>
            <td class="ops" @click.stop>
              <button
                type="button"
                class="btn btn-primary sm"
                :disabled="r.status !== 'pending'"
                @click="openAccept(r)"
              >
                {{ t('采纳') }}
              </button>
              <button type="button" class="btn btn-ghost sm" @click="reject(r)">
                {{ t('驳回') }}
              </button>
              <button type="button" class="btn btn-ghost sm" @click="openExplain(r)">
                {{ t('推导') }}
              </button>
            </td>
          </tr>
          <tr v-if="!filtered.length">
            <td colspan="4" class="empty">
              {{
                roomFilter
                  ? `「${roomFilter}」暂无待处理建议 · 可点「重新生成」覆盖全部房型`
                  : t('暂无建议 · 可点「重新生成」')
              }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AcceptModal
      :open="modalOpen"
      :reco="active"
      @close="modalOpen = false"
      @done="load()"
      @explain="explainOpen = true"
    />
    <ExplainModal :open="explainOpen" :reco="active" @close="explainOpen = false" />
  </div>
</template>

<style scoped>
.compliance {
  padding: 9px 14px;
  background: #f3e8ff;
  border-left: 3px solid #9333ea;
  border-radius: 6px;
  font-size: 12px;
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
}
.compliance .icon {
  color: #9333ea;
  font-weight: 700;
}
.muted {
  color: var(--on-surface-variant);
}
.rtabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.rtab {
  padding: 6px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  font-size: 12px;
  cursor: pointer;
  background: #fff;
  color: var(--on-surface-variant);
}
.rtab.on {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
  font-weight: 600;
}
.rtab .cnt {
  margin-left: 4px;
  font-size: 11px;
  opacity: 0.75;
  font-weight: 500;
}
.rtab.on .cnt {
  opacity: 0.9;
}
.rt-hint {
  margin: -4px 0 12px;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.gap {
  flex: 1;
}
.sm {
  padding: 5px 10px;
  font-size: 12px;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
.kpi {
  padding: 12px 14px;
}
.kpi .label {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.kpi .value {
  font-size: 22px;
  font-weight: 700;
  margin-top: 4px;
}
.kpi .value.up {
  color: #16a34a;
}
.kpi .value.down {
  color: #dc2626;
}
.kpi-impact .calc {
  margin-top: 6px;
  line-height: 1.35;
}
.kpi-impact .calc-line {
  font-size: 11px;
  color: var(--on-surface-variant);
  font-variant-numeric: tabular-nums;
}
.kpi-impact .calc-hint {
  margin-top: 2px;
  font-size: 10px;
  color: #94a3b8;
}
.table-card {
  padding: 0;
  overflow: hidden;
}
.card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid #edf1f6;
  flex-wrap: wrap;
}
.card-head .title {
  font-size: 14px;
  font-weight: 650;
}
.card-head .sub {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.mini {
  width: 100px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 5px 8px;
  font-size: 12px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
th {
  text-align: left;
  padding: 9px 12px;
  background: #f9fafb;
  color: var(--on-surface-variant);
  font-weight: 600;
  border-bottom: 1px solid #e5e7eb;
}
td {
  padding: 10px 12px;
  border-bottom: 1px solid #edf1f6;
  vertical-align: middle;
}
tr.clickable {
  cursor: pointer;
}
tr.clickable:hover td {
  background: #f9fafb;
}
.dt {
  font-weight: 600;
}
.ch {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.cur {
  color: #9ca3af;
  text-decoration: line-through;
}
.new {
  font-size: 15px;
  font-weight: 700;
}
.new.up,
.chg.up {
  color: #16a34a;
}
.new.down,
.chg.down {
  color: #dc2626;
}
.chg {
  font-size: 11px;
  font-weight: 600;
  margin-left: 4px;
}
.reason {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-top: 4px;
}
.net {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-top: 2px;
}
.sigs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.sig {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: #f3f4f6;
  border-radius: 5px;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.sig b {
  color: var(--on-surface);
}
.sig.comp {
  background: #eff4ff;
  color: var(--primary);
}
.sig.occ {
  background: #f0fdf4;
  color: #16a34a;
}
.sig.inv {
  background: #fff7ed;
  color: #d97706;
}
.sig.sale {
  background: #ede9fe;
  color: #7c3aed;
}
.ops {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  min-width: 168px;
}
.ops .btn.sm {
  flex-shrink: 0;
  padding: 4px 10px;
}
.empty {
  text-align: center;
  color: var(--on-surface-variant);
  padding: 28px;
}
@media (max-width: 900px) {
  .kpi-row {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
