<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { localizeSeedText } from '../../lib/localizeSeed'

/**
 * 接班确认 —— 接收交班单、重盘比对、逐条认领、签字接收
 * 与 shift-handover.vue（交班）共用同一张 shift_handover 记录
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import FinanceOpsNav from '../../components/FinanceOpsNav.vue'
import ShiftAiDraftPanel from '../../components/ShiftAiDraftPanel.vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

function loc(s?: string | null) {
  return localizeSeedText(s)
}

const router = useRouter()
const loading = ref(false)
const loadError = ref('')
const toast = ref('')
const ws = ref<any>(null)
const handoverId = ref(0)

const floatDenoms = ref<any[]>([])
const floatReceivedInput = ref<number | null>(null)
const assets = ref<any[]>([])
const revAck = ref(false)
const depositAck = ref(false)
const ackMoney = ref(false)
const ackAssets = ref(false)
const ackTasks = ref(false)
const incomingUserId = ref('')

const diffModalOpen = ref(false)
const diffForm = ref({
  item_type: 'float',
  item_key: '',
  declared_val: 0,
  received_val: 0,
  reason: '',
})

const fmt = (n: number) =>
  Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const ready = computed(() => !!ws.value?.ready)
const floatDetailSum = computed(
  () =>
    Math.round(
      floatDenoms.value.reduce((s, d) => s + Number(d.denom) * Number(d.received_qty || 0), 0) *
        100,
    ) / 100,
)
const floatReceived = computed(() => {
  if (
    floatReceivedInput.value === null ||
    floatReceivedInput.value === undefined ||
    floatReceivedInput.value === ('' as any)
  ) {
    return null
  }
  return Math.round(Number(floatReceivedInput.value) * 100) / 100
})
const floatOutgoing = computed(() => ws.value?.float?.outgoing_actual ?? 0)
const floatMatch = computed(() => {
  if (floatReceived.value === null) return false
  return Math.abs(floatReceived.value - floatOutgoing.value) < 0.01
})
const floatRecvDiff = computed(() => {
  if (floatReceived.value === null) return 0
  return Math.round((floatReceived.value - floatOutgoing.value) * 100) / 100
})
const detailMismatch = computed(() => {
  if (floatReceived.value === null) return false
  const filled = floatDenoms.value.some(
    (d) => d.received_qty !== null && d.received_qty !== undefined && d.received_qty !== '',
  )
  if (!filled) return false
  return Math.abs(floatDetailSum.value - floatReceived.value) >= 0.01
})

const stepMoneyDone = computed(
  () =>
    ws.value?.revenue?.acknowledged &&
    ws.value?.deposit?.acknowledged &&
    ws.value?.float?.confirmed,
)
const stepAssetsDone = computed(() => !!ws.value?.flags?.assets_received_confirmed)
const assetsConfirmed = computed(() => {
  const rows = assets.value
  if (!rows.length) return true
  return rows.every((a) => {
    if (a.received_qty === null || a.received_qty === undefined || a.received_qty === '')
      return false
    const diff = Number(a.received_qty) - Number(a.outgoing_qty ?? 0)
    return diff === 0 || a.received_ack
  })
})
const stepMattersDone = computed(() => !!ws.value?.flags?.matters_confirmed)

function showToast(msg: string) {
  toast.value = msg
  setTimeout(() => {
    toast.value = ''
  }, 2600)
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.shiftTakeoverWorkspace(hotelStore.hotelId)
    ws.value = res?.data ?? res
    handoverId.value = ws.value?.handover_id || 0
    floatDenoms.value = (ws.value?.float?.denominations || [])
      .filter((d: any) => Number(d.denom) >= 1)
      .map((d: any) => ({
        ...d,
        received_qty: d.received_qty === '' || d.received_qty == null ? null : d.received_qty,
      }))
    assets.value = (ws.value?.assets || []).map((a: any) => ({ ...a }))
    revAck.value = !!ws.value?.revenue?.acknowledged
    depositAck.value = !!ws.value?.deposit?.acknowledged
    const ra = ws.value?.float?.received_actual
    floatReceivedInput.value = ws.value?.float?.confirmed && ra != null ? Number(ra) : null
  } catch (e: any) {
    ws.value = null
    loadError.value = e?.message || t('加载接班数据失败')
    showToast(loadError.value)
  } finally {
    loading.value = false
  }
}

async function saveRevenueAck() {
  if (!revAck.value) {
    showToast(t('请勾选营收核对确认'))
    return
  }
  try {
    await api.shiftTakeoverRevenueAck(hotelStore.hotelId, handoverId.value, { ok: true })
    showToast(t('营收核对已确认'))
    await load()
  } catch (e: any) {
    showToast(e?.message || t('确认失败'))
  }
}

async function saveDepositAck() {
  if (!depositAck.value) {
    showToast(t('请勾选押金承接确认'))
    return
  }
  try {
    await api.shiftTakeoverDepositAck(hotelStore.hotelId, handoverId.value, { ok: true })
    showToast(t('押金转交已承接'))
    await load()
  } catch (e: any) {
    showToast(e?.message || t('确认失败'))
  }
}

async function confirmFloatRecount() {
  if (floatReceived.value === null || Number.isNaN(floatReceived.value)) {
    showToast(t('请填写你重盘总额'))
    return
  }
  if (detailMismatch.value) {
    showToast(t('明细合计 ¥{sum} 与重盘总额不一致', { sum: fmt(floatDetailSum.value) }))
    return
  }
  try {
    const hasDetail = floatDenoms.value.some(
      (d) =>
        d.received_qty !== null && d.received_qty !== undefined && String(d.received_qty) !== '',
    )
    await api.shiftTakeoverFloatRecount(hotelStore.hotelId, handoverId.value, {
      received_actual: floatReceived.value,
      denominations: hasDetail ? floatDenoms.value : [],
      confirm: true,
    })
    showToast(t('备用金重盘已确认'))
    await load()
  } catch (e: any) {
    showToast(e?.message || t('重盘确认失败'))
  }
}

async function confirmAssetRecount() {
  try {
    await api.shiftTakeoverAssetRecount(hotelStore.hotelId, handoverId.value, {
      assets: assets.value,
      confirm: true,
    })
    showToast(t('实物复点已确认'))
    await load()
  } catch (e: any) {
    showToast(e?.message || t('复点确认失败'))
  }
}

async function toggleGuestAck(key: string, checked: boolean) {
  if (!ws.value) return
  const item = (ws.value.guest_situations || []).find((s: any) => s.key === key)
  if (!item) return
  const prev = !!item.acked
  item.acked = checked
  syncGuestProgress()
  try {
    await api.shiftTakeoverGuestAck(hotelStore.hotelId, handoverId.value, {
      keys: [key],
      acked: checked,
    })
  } catch (e: any) {
    item.acked = prev
    syncGuestProgress()
    showToast(e?.message || t('操作失败'))
  }
}

function syncGuestProgress() {
  if (!ws.value) return
  const list = ws.value.guest_situations || []
  ws.value.guest_progress = {
    done: list.filter((s: any) => s.acked).length,
    total: list.length,
  }
}

async function claimTask(index: number, action: 'claimed' | 'escalated') {
  if (!ws.value) return
  const item = (ws.value.tasks || []).find((t: any) => t.index === index)
  const prev = item?.claim_status
  if (item) item.claim_status = action
  syncTaskProgress()
  try {
    await api.shiftTakeoverTaskClaim(hotelStore.hotelId, handoverId.value, {
      task_index: index,
      action,
    })
    showToast(action === 'escalated' ? t('已升级店长') : t('已承接'))
  } catch (e: any) {
    if (item) item.claim_status = prev
    syncTaskProgress()
    showToast(e?.message || t('操作失败'))
  }
}

function syncTaskProgress() {
  if (!ws.value) return
  const list = ws.value.tasks || []
  ws.value.task_progress = {
    done: list.filter((t: any) => t.claim_status).length,
    total: list.length,
  }
}

async function ackCarryover(id: number, checked = true) {
  if (!ws.value) return
  const item = (ws.value.carryover || []).find((p: any) => p.id === id)
  if (!item) return
  const prev = !!item.acked
  item.acked = checked
  syncCarryProgress()
  try {
    await api.shiftTakeoverCarryoverAck(hotelStore.hotelId, handoverId.value, {
      carryover_ids: [id],
      acked: checked,
    })
  } catch (e: any) {
    item.acked = prev
    syncCarryProgress()
    showToast(e?.message || t('确认失败'))
  }
}

function syncCarryProgress() {
  if (!ws.value) return
  const list = ws.value.carryover || []
  ws.value.carryover_progress = {
    done: list.filter((p: any) => p.acked).length,
    total: list.length,
  }
}

async function confirmMatters() {
  try {
    await api.shiftTakeoverMattersConfirm(hotelStore.hotelId, handoverId.value)
    showToast(t('客情/待办/遗留已全部确认'))
    await load()
  } catch (e: any) {
    showToast(e?.message || t('请先完成逐条认领'))
  }
}

function openDiffReport(type: string, key: string, declared: number, received: number) {
  diffForm.value = {
    item_type: type,
    item_key: key,
    declared_val: declared,
    received_val: received,
    reason: '',
  }
  diffModalOpen.value = true
}

async function submitDiffReport() {
  if (diffForm.value.reason.trim().length < 4) {
    showToast(t('差异原因不少于 4 字'))
    return
  }
  try {
    await api.shiftTakeoverReportDiff(hotelStore.hotelId, handoverId.value, diffForm.value)
    diffModalOpen.value = false
    showToast(t('差异已上报 · 待店长审核'))
    await load()
  } catch (e: any) {
    showToast(e?.message || t('上报失败'))
  }
}

async function signReceive() {
  if (!ackMoney.value || !ackAssets.value || !ackTasks.value) {
    showToast(t('须完成钱/物/事 3 项必读确认'))
    return
  }
  try {
    await api.shiftTakeoverSign(hotelStore.hotelId, handoverId.value, {
      incoming_user_id: incomingUserId.value ? Number(incomingUserId.value) : undefined,
    })
    showToast(t('接班人已签字接收'))
    await load()
  } catch (e: any) {
    showToast(e?.message || t('签字失败'))
  }
}

async function completeReceive() {
  try {
    const res = await api.shiftTakeoverComplete(hotelStore.hotelId, handoverId.value)
    const data = res?.data ?? res
    showToast(data?.message || t('交接完成 · 归档保存 3 年'))
    await load()
  } catch (e: any) {
    showToast(e?.message || t('无法完成接收'))
  }
}

function assetDiffVsOut(a: any) {
  if (a.received_qty == null || a.received_qty === '') return null
  return Number(a.received_qty) - Number(a.outgoing_qty ?? 0)
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page shift-page">
    <FinanceOpsNav />

    <div class="flex justify-between items-start gap-4 flex-wrap mb-5">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background">{{ t('接班确认') }}</h1>
      </div>
    </div>

    <div v-if="loading" class="loading-hint">{{ t('加载中…') }}</div>

    <div v-else-if="loadError" class="panel empty-state">
      <span class="material-symbols-outlined empty-ic">cloud_off</span>
      <p>{{ t('接班数据加载失败：{err}', { err: loadError }) }}</p>
      <p class="text-sm text-on-surface-variant mt-2">
        {{ t('若提示 Not Found，请重启后端（python run_demo.py）以加载接班 API。') }}
      </p>
      <button type="button" class="btn-ghost mt-3" @click="load">{{ t('重试') }}</button>
    </div>

    <div v-else-if="!ready" class="panel empty-state">
      <span class="material-symbols-outlined empty-ic">hourglass_empty</span>
      <p>{{ ws?.message || t('暂无待接班确认的交班单') }}</p>
      <button
        type="button"
        class="btn-ghost"
        @click="router.push('/c9-finance/shift-handover/handover')"
      >
        {{ t('前往交班页') }}
      </button>
    </div>

    <template v-else>
      <div class="shift-overview mb-5">
        <div class="panel shift-info">
          <span class="recv-tag">{{ loc(ws.banner.state_tag) }}</span>
          <div class="shift-title">
            {{ t('接班确认 · {label} 已交班', { label: loc(ws.banner.shift_label) }) }}
          </div>
          <div class="shift-meta">
            {{ t('交班人') }} {{ ws.banner.outgoing_name }}
            {{ ws.banner.outgoing_signed_at ? ws.banner.outgoing_signed_at.replace('T', ' ') : '' }}
            {{ t('提交 · 你正在接收') }}
          </div>
        </div>
        <div class="kpi-grid cols-3">
          <div class="kpi-card">
            <div class="kpi-label">{{ t('交班人') }}</div>
            <div class="kpi-value sm">{{ ws.banner.outgoing_name || '—' }}</div>
            <div class="kpi-sub">
              {{ t('已签') }} {{ ws.banner.outgoing_signed_at?.slice(11) || '—' }}
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">{{ t('接班人（你）') }}</div>
            <div class="kpi-value sm">{{ ws.banner.incoming_name || t('待确认') }}</div>
            <div class="kpi-sub">
              {{ ws.signatures.incoming_signed ? t('已签字接收') : t('待签字接收') }}
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">{{ t('本班营收（交班单）') }}</div>
            <div class="kpi-value">¥ {{ fmt(ws.banner.total_revenue) }}</div>
            <div class="kpi-sub">{{ ws.banner.payment_count }} {{ t('笔 · 待你复核') }}</div>
          </div>
        </div>
      </div>

      <div class="alert warn">
        <span class="material-symbols-outlined alert-ic">info</span>
        <div class="body">
          <b>{{ t('本页是交班单的接收确认。') }}</b
          >{{
            t(
              '请逐块复核（钱/物/客/事）并签字——签字即代表你对上述数字负责。重盘不符请「差异上报」，不要硬签。',
            )
          }}
        </div>
      </div>

      <ShiftAiDraftPanel
        v-if="handoverId"
        :handover-id="handoverId"
        scene="takeover"
        @confirmed="load"
      />
      <div v-if="ws?.ai?.takeover_brief" class="panel mb-5">
        <div class="panel-h">
          <div class="t">{{ t('接班要点（已确认）') }}</div>
        </div>
        <p class="hint">{{ loc(ws.ai.takeover_brief) }}</p>
      </div>
      <div v-if="ws?.ai?.narrative" class="panel mb-5">
        <div class="panel-h">
          <div class="t">{{ t('交班叙事') }}</div>
        </div>
        <p class="hint">{{ loc(ws.ai.narrative) }}</p>
      </div>

      <!-- 闭环状态条 -->
      <div class="loop-strip mb-5">
        <template v-for="(node, i) in ws.loop" :key="node.key">
          <div v-if="i > 0" class="loop-arrow">→</div>
          <div class="loop-node" :class="node.state">
            <div class="dot">{{ node.state === 'done' ? '✓' : i + 1 }}</div>
            <div class="lbl">
              {{ loc(node.label) }}<br /><span class="sub">{{ loc(node.sub) }}</span>
            </div>
          </div>
        </template>
      </div>

      <div class="split">
        <div class="col">
          <div class="panel">
            <div class="steps">
              <div class="step" :class="{ done: stepMoneyDone, active: !stepMoneyDone }">
                <span class="num">1</span><span class="lbl">{{ t('钱复核') }}</span>
              </div>
              <div
                class="step"
                :class="{ done: stepAssetsDone, active: stepMoneyDone && !stepAssetsDone }"
              >
                <span class="num">2</span><span class="lbl">{{ t('物复核') }}</span>
              </div>
              <div
                class="step"
                :class="{ done: stepMattersDone, active: stepAssetsDone && !stepMattersDone }"
              >
                <span class="num">3</span><span class="lbl">{{ t('事确认') }}</span>
              </div>
              <div
                class="step"
                :class="{
                  done: ws.signatures.incoming_signed,
                  active: stepMattersDone && !ws.signatures.incoming_signed,
                }"
              >
                <span class="num">4</span><span class="lbl">{{ t('签字接收') }}</span>
              </div>
            </div>
          </div>

          <!-- 钱复核 -->
          <div class="panel">
            <div class="panel-h">
              <div class="t">{{ t('① 钱复核 · 营收 / 备用金 / 押金') }}</div>
              <div class="meta">{{ t('交班单快照 · 你独立复核') }}</div>
            </div>
            <div class="tri">
              <div class="item">
                <div class="lbl">{{ t('本班营收') }}</div>
                <div class="val">¥ {{ fmt(ws.revenue.total) }}</div>
              </div>
              <div class="item">
                <div class="lbl">{{ t('昨日同期') }}</div>
                <div class="val muted">¥ {{ fmt(ws.revenue.yesterday_total) }}</div>
              </div>
              <div class="item">
                <div class="lbl">{{ t('渠道数') }}</div>
                <div class="val">{{ ws.revenue.channels.length }}</div>
              </div>
            </div>
            <label class="ack-row">
              <input v-model="revAck" type="checkbox" @change="saveRevenueAck" />{{
                t('我已核对系统营收与交班单一致，无误（只读，不可重录）')
              }}</label
            >

            <div class="sec-lbl">{{ t('按渠道拆解（只读）') }}</div>
            <div class="table-card mb-3">
              <table class="data-tbl">
                <thead>
                  <tr>
                    <th>{{ t('渠道') }}</th>
                    <th class="ctr">{{ t('笔数') }}</th>
                    <th class="num">{{ t('金额') }}</th>
                    <th>{{ t('占比') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="c in ws.revenue.channels" :key="c.channel">
                    <td>{{ loc(c.channel) }}</td>
                    <td class="ctr">{{ c.count }}</td>
                    <td class="num">¥ {{ fmt(c.amount) }}</td>
                    <td>
                      <div class="bar sm">
                        <div class="fill" :style="{ width: c.share_pct + '%' }" />
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="sec-lbl">{{ t('备用金重盘 · 应有') }} ¥ {{ fmt(ws.float.expected) }}</div>
            <div v-if="ws.float.outgoing_diff_reason" class="hint-box">
              {{ t('交班人盘库') }}：{{
                ws.float.outgoing_diff_type_label ||
                (ws.float.outgoing_diff_type === 'short'
                  ? t('短款')
                  : ws.float.outgoing_diff_type === 'long'
                    ? t('长款')
                    : t('对平'))
              }}
              ¥ {{ fmt(Math.abs(ws.float.outgoing_diff)) }} · {{ ws.float.outgoing_diff_reason }}
            </div>

            <div class="float-total-row">
              <div class="float-ro">
                <span class="lbl">{{ t('交班人实点总额') }}</span>
                <b>¥ {{ fmt(floatOutgoing) }}</b>
              </div>
              <label class="float-total-field">
                <span>{{ t('你重盘总额') }}</span>
                <div class="amt-wrap">
                  <span class="yen">¥</span>
                  <input
                    v-model.number="floatReceivedInput"
                    class="inp amt"
                    type="number"
                    min="0"
                    step="0.01"
                    :placeholder="t('独立点数')"
                  />
                </div>
              </label>
            </div>

            <div
              class="diff-box"
              :class="floatReceived === null ? 'pending' : floatMatch ? 'flat' : 'short'"
            >
              <div>
                <div class="ttl">
                  <template v-if="floatReceived === null">{{ t('请填写重盘总额') }}</template>
                  <template v-else-if="floatMatch">{{ t('与交班人一致 ✓') }}</template>
                  <template v-else>
                    {{
                      t('比交班人{dir} ¥{amt}', {
                        dir: floatRecvDiff > 0 ? t('多') : t('少'),
                        amt: fmt(Math.abs(floatRecvDiff)),
                      })
                    }}</template
                  >
                </div>
                <div class="sub2">
                  <template v-if="floatReceived === null">{{ t('与交班人实点比对') }}</template>
                  <template v-else>{{
                    t('你重盘 ¥{recv} · 交班人 ¥{out}', {
                      recv: fmt(floatReceived),
                      out: fmt(floatOutgoing),
                    })
                  }}</template>
                </div>
              </div>
              <button
                v-if="floatReceived !== null && !floatMatch"
                type="button"
                class="link"
                @click="openDiffReport('float', t('备用金合计'), floatOutgoing, floatReceived)"
              >
                {{ t('差异上报') }}
              </button>
            </div>

            <details class="float-detail">
              <summary>{{ t('精细重盘（面额逐张比对，可选）') }}</summary>
              <p class="hint mt-2">
                {{
                  t(
                    '展开后可与交班人面额比对；无角票（100/50/20/10/5/1）。明细合计须与重盘总额一致。',
                  )
                }}
              </p>
              <div class="table-card mb-2 mt-2">
                <table class="data-tbl">
                  <thead>
                    <tr>
                      <th>{{ t('面额') }}</th>
                      <th class="ctr">{{ t('交班人') }}</th>
                      <th class="ctr">{{ t('你重盘张数') }}</th>
                      <th class="num">{{ t('小计') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="d in floatDenoms" :key="d.denom">
                      <td>{{ d.label }}</td>
                      <td class="ctr">{{ d.outgoing_qty }}</td>
                      <td class="ctr">
                        <input v-model.number="d.received_qty" class="inp" type="number" min="0" />
                      </td>
                      <td class="num">
                        ¥ {{ fmt(Number(d.denom) * Number(d.received_qty || 0)) }}
                      </td>
                    </tr>
                  </tbody>
                  <tfoot>
                    <tr>
                      <td>{{ t('明细合计') }}</td>
                      <td class="ctr muted">¥ {{ fmt(floatOutgoing) }}</td>
                      <td class="ctr">—</td>
                      <td class="num">¥ {{ fmt(floatDetailSum) }}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              <div v-if="detailMismatch" class="alert warn">
                {{ t('明细合计与重盘总额不一致') }}
              </div>
            </details>

            <div class="row-actions">
              <button
                type="button"
                class="btn-primary"
                :disabled="floatReceived === null"
                @click="confirmFloatRecount"
              >
                {{ t('确认备用金重盘') }}
              </button>
            </div>

            <div class="sec-lbl">{{ t('押金跨班转交') }}</div>
            <div class="deposit-row">
              <div class="lbl">
                {{ t('本班收押金（{n} 笔）', { n: ws.deposit.collected_count }) }}
              </div>
              <div class="val green">+ ¥ {{ fmt(ws.deposit.collected) }}</div>
            </div>
            <div class="deposit-row">
              <div class="lbl">
                {{ t('本班退押金（{n} 笔）', { n: ws.deposit.refunded_count }) }}
              </div>
              <div class="val red">− ¥ {{ fmt(ws.deposit.refunded) }}</div>
            </div>
            <div class="deposit-row">
              <div class="lbl">
                <b>{{ t('转交净（你承接）') }}</b>
              </div>
              <div class="val big">+ ¥ {{ fmt(ws.deposit.net) }}</div>
            </div>
            <label class="ack-row">
              <input v-model="depositAck" type="checkbox" @change="saveDepositAck" />
              {{ t('已承接 ¥ {amt} 退押压力', { amt: fmt(ws.deposit.net) }) }}
            </label>
          </div>

          <!-- 物复核 -->
          <div class="panel">
            <div class="panel-h">
              <div class="t">{{ t('② 物复核 · 实物复点接收') }}</div>
            </div>
            <div class="asset-head">
              <div>{{ t('物品') }}</div>
              <div>{{ t('交班人') }}</div>
              <div>{{ t('你重数') }}</div>
              <div>{{ t('差异') }}</div>
              <div>{{ t('已知晓差异') }}</div>
            </div>
            <div v-for="a in assets" :key="a.id" class="asset-row">
              <div class="lbl">
                {{ loc(a.name) }} <span v-if="a.hint" class="ch">（{{ loc(a.hint) }}）</span>
              </div>
              <div class="exp">{{ a.outgoing_qty ?? '—' }}</div>
              <input v-model.number="a.received_qty" class="inp" type="number" min="0" />
              <div
                class="diff"
                :class="{
                  zero: assetDiffVsOut(a) === 0,
                  minus: assetDiffVsOut(a) != null && assetDiffVsOut(a)! < 0,
                  plus: assetDiffVsOut(a) != null && assetDiffVsOut(a)! > 0,
                }"
              >
                {{
                  assetDiffVsOut(a) == null
                    ? '—'
                    : assetDiffVsOut(a) === 0
                      ? '0'
                      : (assetDiffVsOut(a)! > 0 ? '+' : '') + assetDiffVsOut(a)
                }}
              </div>
              <label class="recv-ack">
                <input
                  v-model="a.received_ack"
                  type="checkbox"
                  :disabled="assetDiffVsOut(a) === 0"
                />
                {{ assetDiffVsOut(a) === 0 ? t('无差异') : t('差异已知晓') }}</label
              >
            </div>
            <div class="row-actions">
              <button type="button" class="btn-primary" @click="confirmAssetRecount">
                {{ t('确认实物复点') }}
              </button>
            </div>
          </div>
        </div>

        <div class="col">
          <!-- 事确认 -->
          <div class="panel">
            <div class="panel-h">
              <div class="t">{{ t('③ 事 · 客情卡') }}</div>
              <span class="badge purple">{{
                t('{done}/{total} 已知晓', {
                  done: ws.guest_progress.done,
                  total: ws.guest_progress.total,
                })
              }}</span>
            </div>
            <div
              v-for="s in ws.guest_situations"
              :key="s.key"
              class="situation"
              :class="{ acked: s.acked }"
            >
              <div class="ic" :class="s.type">
                {{
                  s.type === 'vip'
                    ? 'V'
                    : s.type === 'complaint'
                      ? '!'
                      : s.type === 'inbound'
                        ? '↑'
                        : '·'
                }}
              </div>
              <div class="body">
                <div class="ttl">
                  {{ loc(s.title) }}
                  <span v-if="s.ai_generated" class="ai-tag">AI</span>
                </div>
                <div v-if="s.content" class="desc">{{ loc(s.content) }}</div>
              </div>
              <label class="ack-inline" :class="{ on: s.acked }" @click.stop>
                <input
                  type="checkbox"
                  :checked="!!s.acked"
                  @click.stop
                  @change="toggleGuestAck(s.key, ($event.target as HTMLInputElement).checked)"
                />{{ t('已知晓') }}</label
              >
            </div>
            <div v-if="!ws.guest_situations?.length" class="hint">{{ t('暂无客情需认领。') }}</div>
          </div>

          <div class="panel">
            <div class="panel-h">
              <div class="t">{{ t('③ 事 · 待办承接') }}</div>
              <span class="badge amber"
                >{{ ws.task_progress.done }}/{{ ws.task_progress.total }}</span
              >
            </div>
            <div
              v-for="task in ws.tasks"
              :key="task.index"
              class="task"
              :class="{ claimed: task.claim_status }"
            >
              <div class="pri" :class="task.priority" />
              <div>{{ loc(task.content) }}</div>
              <div class="owner">{{ loc(task.owner_name) }}</div>
              <template v-if="!task.claim_status">
                <button type="button" class="esc" @click="claimTask(task.index, 'claimed')">
                  {{ t('承接') }}
                </button>
                <button
                  v-if="task.can_escalate"
                  type="button"
                  class="esc warn"
                  @click="claimTask(task.index, 'escalated')"
                >
                  {{ t('↑ 升级') }}
                </button>
              </template>
              <span v-else class="esc done">{{
                task.claim_status === 'escalated' ? t('已升级') : t('已承接')
              }}</span>
            </div>
          </div>

          <div class="panel">
            <div class="panel-h">
              <div class="t">{{ t('③ 事 · 上轮遗留') }}</div>
              <span class="badge"
                >{{ ws.carryover_progress.done }}/{{ ws.carryover_progress.total }}</span
              >
            </div>
            <div
              v-for="p in ws.carryover"
              :key="p.id"
              class="prev-item"
              :class="{ pending: p.pending }"
            >
              <div class="shift-tag">{{ loc(String(p.shift_no) + ' 班') }}</div>
              <div class="body">{{ loc(p.content) }}</div>
              <label class="ack-inline" :class="{ on: p.acked }" @click.stop>
                <input
                  type="checkbox"
                  :checked="!!p.acked"
                  @click.stop
                  @change="ackCarryover(p.id, ($event.target as HTMLInputElement).checked)"
                />{{ t('已了解') }}</label
              >
            </div>
            <div class="row-actions">
              <button type="button" class="btn-ghost" @click="confirmMatters">
                {{ t('确认事項完成') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 签字接收 -->
      <div class="panel mt">
        <div class="panel-h">
          <div class="t">{{ t('④ 签字接收') }}</div>
          <div class="meta">{{ t('3 项必读 + 工号') }}</div>
        </div>
        <div v-if="!ws.signatures.incoming_signed" class="alert warn">
          <label class="ack-row"
            ><input v-model="ackMoney" type="checkbox" />{{
              t('① 钱（营收/备用金/押金）已复核')
            }}</label
          >
          <label class="ack-row"
            ><input v-model="ackAssets" type="checkbox" />{{ t('② 物（实物复点）已复核') }}</label
          >
          <label class="ack-row"
            ><input v-model="ackTasks" type="checkbox" />{{
              t('③ 事（客情/待办/遗留）已确认')
            }}</label
          >
          <div class="field-inline">
            <label>{{ t('接班人工号') }}</label>
            <input
              v-model="incomingUserId"
              class="inp left"
              :placeholder="t('留空则使用当前登录账号')"
            />
          </div>
        </div>
        <div class="sign-area">
          <div class="sign-cell signed readonly">
            <div class="role">{{ t('交班人') }}</div>
            <div class="name">{{ ws.banner.outgoing_name }}</div>
            <div class="meta2">
              {{ t('已签') }} {{ ws.banner.outgoing_signed_at?.slice(11) || '—' }}
            </div>
          </div>
          <div class="sign-cell" :class="{ signed: ws.signatures.incoming_signed }">
            <div class="role">{{ t('接班人（你）') }}</div>
            <div class="name">{{ ws.banner.incoming_name || '—' }}</div>
            <button
              v-if="!ws.signatures.incoming_signed"
              type="button"
              class="act"
              :disabled="!ws.flags.can_sign || !ackMoney || !ackAssets || !ackTasks"
              @click="signReceive"
            >
              {{ t('接班人签字接收') }}
            </button>
            <div v-else class="act ok">{{ t('✓ 已签字') }}</div>
          </div>
          <div class="sign-cell" :class="{ signed: ws.signatures.manager_signed }">
            <div class="role">{{ t('店长审核') }}</div>
            <div class="name">
              {{
                ws.signatures.manager_signed
                  ? t('已审核')
                  : ws.signatures.manager_required
                    ? t('待审核')
                    : t('暂无需')
              }}
            </div>
          </div>
        </div>
        <div class="foot-actions">
          <button
            type="button"
            class="btn-primary"
            :disabled="!ws.flags.can_complete"
            @click="completeReceive"
          >
            {{ t('确认接收 · 完成交接') }}
          </button>
        </div>
      </div>
    </template>

    <div v-if="diffModalOpen" class="modal-mask" @click.self="diffModalOpen = false">
      <div class="modal">
        <h3 class="red">{{ t('差异上报') }}</h3>
        <p>
          {{ t('与交班人盘库不符须上报，店长须尽快到岗审核。上报后可继续签字，归档前须闭合。') }}
        </p>
        <div class="fld">
          <div class="flbl">{{ t('差异原因（必填）') }}</div>
          <textarea v-model="diffForm.reason" class="inp full" rows="3" />
        </div>
        <div class="modal-acts">
          <button type="button" class="btn-ghost" @click="diffModalOpen = false">
            {{ t('取消') }}
          </button>
          <button type="button" class="btn-ghost danger" @click="submitDiffReport">
            {{ t('提交上报') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="toast" class="toast show">{{ toast }}</div>
  </div>
</template>

<style scoped>
@import './shift-handover-shared.css';
.recv-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  background: #e8def8;
  color: #6750a4;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}
.kpi-grid.cols-3 {
  grid-template-columns: repeat(3, 1fr);
}
.empty-state {
  text-align: center;
  padding: 48px 24px;
}
.empty-ic {
  font-size: 48px;
  color: #79747e;
  display: block;
  margin-bottom: 12px;
}
.loop-strip {
  display: flex;
  align-items: center;
  padding: 14px 18px;
  background: #f7f2fa;
  border: 1px solid #e7e0ec;
  border-radius: 12px;
  flex-wrap: wrap;
  gap: 4px;
}
.loop-node {
  flex: 1;
  min-width: 100px;
  text-align: center;
}
.loop-node .dot {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #e7e0ec;
  margin: 0 auto 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 12px;
}
.loop-node.done .dot {
  background: #2e7d32;
  color: #fff;
}
.loop-node.cur .dot {
  background: #6750a4;
  color: #fff;
  box-shadow: 0 0 0 4px #e8def8;
}
.loop-node.future .dot {
  background: #fff;
  border: 2px dashed #e7e0ec;
}
.loop-node .lbl {
  font-size: 11px;
  font-weight: 600;
}
.loop-node .sub {
  font-weight: 400;
  color: #79747e;
}
.loop-arrow {
  color: #79747e;
  padding: 0 4px;
}
.ack-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0;
  font-size: 13px;
}
.hint-box {
  background: #fff8e1;
  border: 1px solid #ffe082;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  margin-bottom: 10px;
  color: #8a5a11;
}
.situation.acked {
  border-color: #2e7d32;
  background: #e8f5e9;
}
.ack-inline {
  font-size: 12px;
  font-weight: 600;
  color: #6750a4;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}
.ack-inline.on {
  color: #2e7d32;
}
.ack-done {
  font-size: 12px;
  color: #2e7d32;
  font-weight: 700;
}
.task.claimed {
  background: #e8f5e9;
  border-color: #c8e6c9;
}
.esc.done {
  color: #2e7d32;
}
.esc.warn {
  color: #c5221f;
}
.recv-ack {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.diff-box.pending {
  background: #f5f5f5;
  color: #79747e;
  border: 1px solid #e0e0e0;
}
.float-total-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px 20px;
  margin-bottom: 12px;
  padding: 12px 14px;
  background: #faf8ff;
  border: 1px solid #e8def8;
  border-radius: 10px;
}
.float-ro {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 140px;
}
.float-ro .lbl {
  font-size: 12px;
  color: #79747e;
  font-weight: 600;
}
.float-ro b {
  font-size: 18px;
  color: #1c1b1f;
}
.float-total-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #49454f;
}
.amt-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
}
.amt-wrap .yen {
  font-size: 18px;
  font-weight: 700;
}
.inp.amt {
  width: 160px;
  font-size: 18px;
  font-weight: 700;
  padding: 8px 10px;
}
.float-detail {
  margin: 10px 0 12px;
  border: 1px solid #e7e0ec;
  border-radius: 10px;
  padding: 8px 12px;
  background: #fff;
}
.float-detail summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #6750a4;
  list-style: none;
}
.float-detail summary::-webkit-details-marker {
  display: none;
}
.float-detail summary::before {
  content: '▸ ';
  color: #9e9e9e;
}
.float-detail[open] summary::before {
  content: '▾ ';
}
.alert.warn {
  background: #fff8e1;
  color: #8a5a11;
  border: 1px solid #ffe082;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  margin-top: 8px;
}
.field-inline {
  margin-top: 12px;
}
.field-inline label {
  display: block;
  font-size: 12px;
  color: #79747e;
  margin-bottom: 4px;
}
.sign-cell.readonly {
  border-style: solid;
  border-color: #e7e0ec;
}
.step .lbl {
  font-weight: 600;
}
.ai-tag {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  color: #6750a4;
  background: #e8def8;
  padding: 1px 5px;
  border-radius: 4px;
  margin-left: 6px;
}
</style>
