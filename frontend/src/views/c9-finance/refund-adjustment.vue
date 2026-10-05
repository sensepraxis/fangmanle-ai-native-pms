<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'
import { localizeSeedText } from '../../lib/localizeSeed'

function loc(s?: string | null) {
  return localizeSeedText(s)
}

/**
 * 退改与反结账 —— 日常收银高风险区
 * 三类分入口：退款 / 改账·红冲 / 反结账（双授权）
 */
import { computed, onMounted, ref, watch } from 'vue'
import FinanceOpsNav from '../../components/FinanceOpsNav.vue'
import FinanceAiPlanDrawer from '../../components/FinanceAiPlanDrawer.vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

type OpType = 'refund' | 'adjust' | 'reverse'

const op = ref<OpType>('refund')
const loading = ref(false)
const toast = ref('')
const submitting = ref(false)
const aiOpen = ref(false)

const threshold = ref(2000)
const tickets = ref<any[]>([])
const myPending = ref<any[]>([])

/** 退款向导：手机号优先 + 原路锁定 */
const phoneInput = ref('')
const fallbackOpen = ref(false)
const fallbackQ = ref('')
const refundGuest = ref<any>(null)
const refundOrders = ref<any[]>([])
const refundEmpty = ref<any>(null)
const refundLookup = ref<any>(null)
const refundLines = ref<any[]>([])
const refundFee = ref(0)
const refundFaceOk = ref(false)
const refundLooking = ref(false)
const refundMode = ref<'original' | 'cash_special'>('original')
const cashSpecialOk = ref(false)
let phoneTimer: ReturnType<typeof setTimeout> | null = null

/** 改账向导 */
const adjustEntries = ref<any[]>([])
const adjustEntryId = ref('')
const adjustAction = ref('reverse')
const adjustReason = ref('')
const adjustFaceOk = ref(false)

/** 反结账向导 */
const reverseTargets = ref<any[]>([])
const reverseTargetId = ref('')
const reverseReason = ref(t('房费算错'))
const reverseNote = ref('')
const reverseTicketId = ref<number | null>(null)

const OP_CARDS: { key: OpType; icon: string; title: string; desc: string; danger?: boolean }[] = [
  {
    key: 'refund',
    icon: 'undo',
    title: t('退款'),
    desc: t('全额/部分退房费、押金退；原路退回优先'),
  },
  {
    key: 'adjust',
    icon: 'edit_note',
    title: t('改账 · 红冲'),
    desc: t('冲正、差额更正、发票红冲'),
  },
  {
    key: 'reverse',
    icon: 'warning',
    title: t('反结账'),
    desc: t('重开已日结账单；双授权 + 全量留痕'),
    danger: true,
  },
]

const METHOD_OPTIONS = [] as { value: string; label: string }[]

const ADJUST_ACTIONS = [
  { value: 'reverse', label: t('冲正（全额反向）') },
  { value: 'delta', label: t('差额更正') },
  { value: 'invoice_red', label: t('发票红冲') },
]

const REVERSE_REASONS = ['房费算错', '渠道重复入账', '折扣漏挂', '其他']

function money(n: number | undefined | null) {
  const v = Number(n || 0)
  return `¥${v.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function showToast(msg: string) {
  toast.value = msg
  setTimeout(() => {
    if (toast.value === msg) toast.value = ''
  }, 2800)
}

function statusTone(st: string) {
  if (st === 'pending_approval') return 'tone-warn'
  if (st === 'pending_dual_auth') return 'tone-danger'
  if (st === 'approved' || st === 'done') return 'tone-ok'
  return 'tone-mute'
}

const selectedRefundYuan = computed(() =>
  refundLines.value.filter((l) => l.checked).reduce((s, l) => s + Number(l.amount_yuan || 0), 0),
)
const refundNetYuan = computed(() =>
  Math.max(0, selectedRefundYuan.value - Number(refundFee.value || 0)),
)
const refundOverThreshold = computed(() => refundNetYuan.value > Number(threshold.value || 0))
const paymentLock = computed(() => refundLookup.value?.payment_lock || null)

const selectedAdjust = computed(
  () => adjustEntries.value.find((e) => e.id === adjustEntryId.value) || null,
)
const selectedReverse = computed(
  () => reverseTargets.value.find((t) => t.id === reverseTargetId.value) || null,
)

const activeReverseTicket = computed(() => {
  if (reverseTicketId.value) {
    return tickets.value.find((t) => t.id === reverseTicketId.value) || null
  }
  return (
    myPending.value.find((t) => t.op_type === 'reverse' && t.status === 'pending_dual_auth') || null
  )
})

async function loadBoard() {
  loading.value = true
  try {
    const data = await api.refundAdjustBoard(hotelStore.hotelId)
    threshold.value = Number(data.config?.refund_threshold_yuan ?? 2000)
    tickets.value = data.tickets || []
    myPending.value = data.my_pending || []
  } catch (e: any) {
    showToast(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function saveThreshold() {
  try {
    await api.refundAdjustThreshold({ refund_threshold_yuan: Number(threshold.value) || 0 })
    showToast(t('阈值已生效'))
    await loadBoard()
  } catch (e: any) {
    showToast(e?.message || '保存失败')
  }
}

async function runPhoneLookup() {
  const phone = phoneInput.value.replace(/\D/g, '')
  if (phone.length < 3) {
    refundGuest.value = null
    refundOrders.value = []
    refundLookup.value = null
    refundLines.value = []
    refundEmpty.value = null
    return
  }
  refundLooking.value = true
  try {
    const data = await api.refundAdjustLookupByPhone(hotelStore.hotelId, phone)
    if (!data.matched) {
      refundGuest.value = null
      refundOrders.value = []
      refundLookup.value = null
      refundLines.value = []
      refundEmpty.value = null
      showToast(data.hint || '继续输入手机号')
      return
    }
    refundGuest.value = data.guest
    refundOrders.value = data.orders || []
    refundEmpty.value = data.empty_action || null
    if (data.auto_select_order_id) {
      await selectRefundOrder(data.auto_select_order_id)
    } else {
      refundLookup.value = null
      refundLines.value = []
    }
  } catch (e: any) {
    showToast(e?.message || '查找失败')
  } finally {
    refundLooking.value = false
  }
}

function onPhoneInput() {
  phoneInput.value = phoneInput.value.replace(/[^\d]/g, '').slice(0, 11)
  if (phoneTimer) clearTimeout(phoneTimer)
  phoneTimer = setTimeout(() => runPhoneLookup(), 280)
}

async function selectRefundOrder(orderId: number) {
  refundLooking.value = true
  try {
    const data = await api.refundAdjustOrderDetail(hotelStore.hotelId, orderId)
    applyRefundDetail(data)
  } catch (e: any) {
    showToast(e?.message || '加载订单失败')
  } finally {
    refundLooking.value = false
  }
}

function applyRefundDetail(data: any) {
  refundLookup.value = data
  refundLines.value = (data.lines || []).map((l: any) => ({ ...l }))
  refundFaceOk.value = false
  refundMode.value = 'original'
  cashSpecialOk.value = false
}

async function lookupFallback() {
  const q = fallbackQ.value.trim()
  if (!q) {
    showToast(t('请输入订单号或房号'))
    return
  }
  refundLooking.value = true
  try {
    const data = await api.refundAdjustLookupOrder(hotelStore.hotelId, q)
    if (data.orders && data.order_count != null && !data.lines) {
      // phone-style multi result
      refundGuest.value = data.guest
      refundOrders.value = data.orders
      refundEmpty.value = data.empty_action
      if (data.auto_select_order_id) await selectRefundOrder(data.auto_select_order_id)
      else {
        refundLookup.value = null
        refundLines.value = []
      }
    } else {
      applyRefundDetail(data)
      refundOrders.value = data.order_id
        ? [
            {
              order_id: data.order_id,
              order_no: data.order_no,
              room_no: data.room_no,
              guest_name_masked: data.guest_name_masked,
              received_yuan: data.received_yuan,
              check_in: data.check_in,
              check_out: data.check_out,
              payment_lock: data.payment_lock,
            },
          ]
        : []
      refundGuest.value = {
        name_masked: data.guest_name_masked,
        phone_mask: data.phone_mask,
        confirm_hint: data.confirm_hint,
      }
    }
  } catch (e: any) {
    showToast(e?.message || '未找到订单')
  } finally {
    refundLooking.value = false
  }
}

async function openTicket(t: any) {
  op.value = (t.op_type as OpType) || 'refund'
  if (t.op_type === 'refund') {
    if (t.order_id) {
      await selectRefundOrder(t.order_id)
    } else if (t.order_no) {
      fallbackQ.value = t.order_no
      fallbackOpen.value = true
      await lookupFallback()
    }
  } else if (t.op_type === 'reverse') {
    reverseTicketId.value = t.id
  }
}

async function loadAdjustEntries() {
  try {
    const data = await api.refundAdjustEntries(hotelStore.hotelId)
    adjustEntries.value = data.entries || []
    if (!adjustEntryId.value && adjustEntries.value.length) {
      adjustEntryId.value = adjustEntries.value[0].id
    }
  } catch {
    adjustEntries.value = []
  }
}

async function loadReverseTargets() {
  try {
    const data = await api.refundAdjustReverseTargets(hotelStore.hotelId)
    reverseTargets.value = data.targets || []
    if (!reverseTargetId.value && reverseTargets.value.length) {
      reverseTargetId.value = reverseTargets.value[0].id
    }
  } catch {
    reverseTargets.value = []
  }
}

async function submitRefund() {
  if (!refundLookup.value) {
    showToast(t('请先定位源单并口头核验'))
    return
  }
  if (!refundFaceOk.value) {
    showToast(t('请勾选当面核对确认'))
    return
  }
  if (refundMode.value === 'cash_special' && !cashSpecialOk.value) {
    showToast(t('现金特批须勾选财务经理特批'))
    return
  }
  submitting.value = true
  try {
    const res = await api.refundAdjustSubmitRefund({
      order_id: refundLookup.value.order_id,
      order_no: refundLookup.value.order_no,
      guest_name_masked: refundLookup.value.guest_name_masked,
      lines: refundLines.value,
      fee_yuan: Number(refundFee.value) || 0,
      face_confirmed: true,
      reason: t('前台退款'),
      payment_lock: paymentLock.value,
      transaction_id: paymentLock.value?.transaction_id,
      refund_mode: refundMode.value,
      special_approval: cashSpecialOk.value,
      demo: !!refundLookup.value.demo,
    })
    showToast(res.message || '已提交')
    refundFaceOk.value = false
    cashSpecialOk.value = false
    await loadBoard()
  } catch (e: any) {
    showToast(e?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function submitAdjust() {
  if (!selectedAdjust.value) {
    showToast(t('请选择账目'))
    return
  }
  if (!adjustReason.value.trim()) {
    showToast(t('原因必填'))
    return
  }
  if (!adjustFaceOk.value) {
    showToast(t('请完成二次确认'))
    return
  }
  submitting.value = true
  try {
    const res = await api.refundAdjustSubmitAdjust({
      entry: selectedAdjust.value,
      action: adjustAction.value,
      reason: adjustReason.value.trim(),
      face_confirmed: true,
    })
    showToast(res.message || '已提交')
    adjustFaceOk.value = false
    adjustReason.value = ''
    await loadBoard()
  } catch (e: any) {
    showToast(e?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function submitReverse() {
  if (!selectedReverse.value) {
    showToast(t('请选择营业日/账单'))
    return
  }
  if (!reverseReason.value) {
    showToast(t('原因必填'))
    return
  }
  submitting.value = true
  try {
    const res = await api.refundAdjustSubmitReverse({
      target: selectedReverse.value,
      reason: reverseReason.value,
      note: reverseNote.value,
    })
    reverseTicketId.value = res.ticket?.id || null
    showToast(res.message || '已申请')
    await loadBoard()
  } catch (e: any) {
    showToast(e?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function scanAuth(role: 'mgr' | 'fin') {
  const ticket = activeReverseTicket.value
  if (!ticket?.id) {
    showToast(t('请先提交反结账申请'))
    return
  }
  try {
    const res = await api.refundAdjustDualAuth(ticket.id, role)
    showToast(role === 'mgr' ? t('店长已授权') : t('财务经理已授权'))
    reverseTicketId.value = res.ticket?.id || ticket.id
    await loadBoard()
  } catch (e: any) {
    showToast(t(e?.message || '授权失败'))
  }
}

watch(op, (v) => {
  if (v === 'adjust') loadAdjustEntries()
  if (v === 'reverse') loadReverseTargets()
})

onMounted(async () => {
  await loadBoard()
  await loadAdjustEntries()
  await loadReverseTargets()
})
</script>

<template>
  <div class="page ra-page">
    <FinanceOpsNav />

    <div class="ra-head">
      <div>
        <div class="title-row">
          <h1>{{ t('退改与反结账') }}</h1>
          <span class="risk-badge">{{ t('最高风险 · 反结账') }}</span>
        </div>
      </div>
      <div class="head-actions">
        <button v-if="commercialEnabled()" type="button" class="btn-ghost" @click="aiOpen = true">
          {{ t('AI 安排') }}
        </button>
        <button type="button" class="btn-ghost" disabled>{{ t('打印') }}</button>
      </div>
    </div>

    <FinanceAiPlanDrawer v-model:open="aiOpen" scene="refund" @confirmed="loadBoard" />

    <div v-if="toast" class="toast">{{ toast }}</div>

    <div class="ra-grid">
      <!-- 左栏 -->
      <aside class="ra-left">
        <section class="panel">
          <h3 class="panel-h">{{ t('① 选择操作类型') }}</h3>
          <button
            v-for="c in OP_CARDS"
            :key="c.key"
            type="button"
            class="op-card"
            :class="{ on: op === c.key, danger: c.danger, 'on-danger': op === c.key && c.danger }"
            @click="op = c.key"
          >
            <span class="material-symbols-outlined op-ico" :class="{ warn: c.danger }">{{
              c.icon
            }}</span>
            <div>
              <div class="op-title">{{ c.title }}</div>
              <div class="op-desc">{{ c.desc }}</div>
            </div>
          </button>
        </section>

        <section class="panel">
          <h3 class="panel-h">{{ t('授权阈值（可配）') }}</h3>
          <label class="field-lab">{{ t('退款大额授权线') }}</label>
          <div class="thresh-row">
            <input v-model.number="threshold" type="number" min="0" step="100" class="field" />
            <span class="unit">{{ t('元') }}</span>
            <button type="button" class="btn-ghost sm" @click="saveThreshold">
              {{ t('保存') }}
            </button>
          </div>
          <div class="thresh-row mt">
            <span class="field-lab" style="margin: 0">{{ t('反结账') }}</span>
            <span class="pill-forced">{{ t('强制双授权') }}</span>
          </div>
          <p class="hint-box">
            {{
              t('阈值即时生效；超过此线的退款须经理扫码授权。反结账不受金额阈值限制，一律双授权。')
            }}
          </p>
        </section>

        <section class="panel">
          <h3 class="panel-h">{{ t('待我处理工单') }}</h3>
          <div v-if="loading" class="muted">{{ t('加载中…') }}</div>
          <div v-else-if="!myPending.length && !tickets.length" class="muted">
            {{ t('暂无工单') }}
          </div>
          <ul v-else class="ticket-list">
            <li
              v-for="tag in myPending.length ? myPending : tickets.slice(0, 5)"
              :key="tag.id"
              class="ticket-click"
              @click="openTicket(tag)"
            >
              <div class="tk-top">
                <b>{{ t(tag.title || '') }}</b>
                <span class="tk-st" :class="statusTone(tag.status)">{{
                  t(tag.status_label || tag.status || '')
                }}</span>
              </div>
              <div class="tk-sub">{{ t(tag.detail || '') }} · {{ t('点击载入向导') }}</div>
            </li>
          </ul>
        </section>
      </aside>
      <!-- 右栏向导 -->
      <section class="panel ra-wizard">
        <h3 class="panel-h">{{ t('② 操作向导') }}</h3>

        <!-- 退款：手机号优先 + 原路锁定 -->
        <div v-show="op === 'refund'" class="wiz">
          <div class="step">
            <div class="step-h">{{ t('① 定位源单（手机号优先）') }}</div>
            <p class="muted" style="margin-bottom: 8px">
              {{
                t(
                  '报预订手机号 → OneID 找客 → 选可退订单 → 口头核验。原路退回由系统锁定，不可手改渠道。',
                )
              }}
            </p>
            <div class="row-gap">
              <input
                v-model="phoneInput"
                class="field phone-lg"
                type="tel"
                maxlength="11"
                :placeholder="t('报一下预订手机号')"
                @input="onPhoneInput"
              />
              <span v-if="refundLooking" class="muted">{{ t('查找中…') }}</span>
            </div>
            <button type="button" class="link-quiet" @click="fallbackOpen = !fallbackOpen">
              {{ fallbackOpen ? t('收起边角入口') : t('无手机号？订单号 / 房号 / 会员码') }}
            </button>
            <div v-if="fallbackOpen" class="fallback-box">
              <div class="row-gap">
                <input
                  v-model="fallbackQ"
                  class="field"
                  :placeholder="t('如 No.8821 或房号 1203')"
                  @keyup.enter="lookupFallback"
                />
                <button type="button" class="btn-ghost sm" @click="lookupFallback">
                  {{ t('定位') }}
                </button>
              </div>
            </div>

            <div v-if="refundGuest" class="guest-verify">
              <div class="gv-title">{{ t('认人区') }}</div>
              <div>
                <b>{{ refundGuest.name_masked || refundGuest.guest_name_masked }}</b>
                <span class="muted"> · {{ refundGuest.phone_mask || '—' }}</span>
              </div>
              <div v-if="refundGuest.confirm_hint" class="gv-hint">
                {{ refundGuest.confirm_hint }}
              </div>
            </div>

            <div v-if="refundEmpty" class="empty-box">{{ refundEmpty.message }}</div>

            <div v-if="refundOrders.length" class="order-cards">
              <button
                v-for="o in refundOrders"
                :key="o.order_id || o.order_no"
                type="button"
                class="order-pick"
                :class="{ on: refundLookup?.order_id === o.order_id }"
                @click="o.order_id ? selectRefundOrder(o.order_id) : applyRefundDetail(o)"
              >
                <div class="flex-between">
                  <b>{{ o.order_no }}</b>
                  <span class="muted">{{ o.status_label || o.status || '' }}</span>
                </div>
                <div class="muted sm">
                  {{ t('房') }} {{ o.room_no || '—' }} · {{ o.check_in }} → {{ o.check_out }} ·
                  {{ t('已收') }} {{ money(o.received_yuan) }}
                </div>
                <div v-if="o.payment_lock" class="lock-mini">
                  {{ t('原路') }} {{ o.payment_lock.pay_channel_label }} ·
                  {{ o.payment_lock.transaction_id || t('无流水号') }}
                </div>
              </button>
            </div>
          </div>

          <template v-if="refundLookup">
            <div class="step">
              <div class="step-h">{{ t('② 退款范围') }}</div>
              <div class="line-list">
                <label v-for="l in refundLines" :key="l.id" class="line-row">
                  <input v-model="l.checked" type="checkbox" />
                  <span>{{ l.label }}</span>
                  <b>{{ money(l.amount_yuan) }}</b>
                </label>
              </div>
            </div>

            <div class="step">
              <div class="step-h">{{ t('③ 退款方式（系统锁定 · 二清红线）') }}</div>
              <div class="lock-box">
                <div class="lock-main">
                  {{ paymentLock?.method_display || t('原路退回（锁定中）') }}
                </div>
                <div class="muted sm">
                  {{ t('渠道不可手改。原支付流水') }}
                  <b>{{ paymentLock?.transaction_id || '—' }}</b>
                  {{ t('，退款 API 须按此流水原路退回。') }}
                </div>
              </div>
              <label
                v-if="paymentLock?.allow_cash_special"
                class="check-row"
                style="margin-top: 10px"
              >
                <input
                  type="checkbox"
                  :checked="refundMode === 'cash_special'"
                  @change="
                    refundMode = ($event.target as HTMLInputElement).checked
                      ? 'cash_special'
                      : 'original'
                  "
                />
                {{ t('例外：现金特批退（非原路 · 二清高风险 · 须财务经理特批）') }}</label
              >
              <label v-if="refundMode === 'cash_special'" class="check-row">
                <input v-model="cashSpecialOk" type="checkbox" />
                {{ t('已获财务经理特批，承担非原路合规责任') }}</label
              >
            </div>

            <div class="step">
              <div class="step-h">{{ t('④ 金额核对') }}</div>
              <div class="amt-box">
                {{ t('已收') }} {{ money(refundLookup.received_yuan) }} · {{ t('应退') }}
                <b>{{ money(refundNetYuan) }}</b>
                · {{ t('手续费') }} {{ money(refundFee) }}（{{ t('按规则）') }}
              </div>
              <p v-if="refundOverThreshold" class="warn-line">
                {{ t('超过大额线') }} {{ money(threshold) }}，{{ t('提交后进入经理授权。') }}
              </p>
            </div>

            <div class="confirm-card">
              <div class="confirm-title">{{ t('二次确认（防认错人）') }}</div>
              <p>
                {{ t('客人') }} <b>{{ refundLookup.guest_name_masked }}</b> {{ t('· 房') }}
                <b>{{ refundLookup.room_no || '—' }}</b> · {{ t('住期') }}
                {{ refundLookup.check_in }} → {{ refundLookup.check_out }}
              </p>
              <p>
                {{ t('订单') }} <b>{{ refundLookup.order_no }}</b> {{ t('· 应退') }}
                <b>{{ money(refundNetYuan) }}</b> ·
                {{ paymentLock?.pay_channel_label || t('原路') }}
              </p>
              <p class="muted">{{ t('请当面核验身份与金额后再提交；AI 不可直接落账。') }}</p>
              <label class="check-row">
                <input v-model="refundFaceOk" type="checkbox" />
                {{ t('我已当面与客人核对身份与退款金额') }}</label
              >
              <button
                type="button"
                class="btn-primary w-full"
                :disabled="submitting || !refundFaceOk"
                @click="submitRefund"
              >
                {{ submitting ? t('提交中…') : t('提交退款') }}
              </button>
            </div>
          </template>
        </div>

        <!-- 改账 -->
        <div v-show="op === 'adjust'" class="wiz">
          <div class="step">
            <div class="step-h">{{ t('① 选源账目') }}</div>
            <select v-model="adjustEntryId" class="field">
              <option v-for="e in adjustEntries" :key="e.id" :value="e.id">
                {{ loc(e.label) }}
              </option>
            </select>
          </div>
          <div class="step">
            <div class="step-h">{{ t('② 动作') }}</div>
            <select v-model="adjustAction" class="field">
              <option v-for="a in ADJUST_ACTIONS" :key="a.value" :value="a.value">
                {{ a.label }}
              </option>
            </select>
            <p v-if="adjustAction === 'invoice_red'" class="redline">
              {{ t('发票红冲须与原蓝字一一对应；跨月受税控限制，将联动发票模块校验。') }}
            </p>
          </div>
          <div class="step">
            <div class="step-h">{{ t('③ 原因（必填）') }}</div>
            <input v-model="adjustReason" class="field" :placeholder="t('如：误收早餐费')" />
          </div>
          <div class="confirm-card">
            <div class="confirm-title">{{ t('二次确认') }}</div>
            <p class="muted">
              {{
                t(
                  '改账/红冲直接影响营收与税金，提交后不可随意撤销，须财务授权。AI 仅可预填，不可直接改数据。',
                )
              }}
            </p>
            <label class="check-row">
              <input v-model="adjustFaceOk" type="checkbox" />{{
                t('我确认账目与原因无误，申请财务授权')
              }}</label
            >
            <button
              type="button"
              class="btn-primary w-full"
              :disabled="submitting || !adjustFaceOk"
              @click="submitAdjust"
            >
              {{ submitting ? t('提交中…') : t('提交改账') }}
            </button>
          </div>
        </div>

        <!-- 反结账 -->
        <div v-show="op === 'reverse'" class="wiz">
          <div class="step">
            <div class="step-h">{{ t('① 选营业日 + 账单') }}</div>
            <select v-model="reverseTargetId" class="field">
              <option v-for="tag in reverseTargets" :key="tag.id" :value="tag.id">
                {{ loc(tag.label) }}
              </option>
            </select>
          </div>
          <div class="step">
            <div class="step-h">{{ t('② 原账单快照') }}</div>
            <div class="amt-box">{{ loc(selectedReverse?.snapshot) || '—' }}</div>
          </div>
          <div class="redline-box">
            <div class="confirm-title">{{ t('反结账红线（§10.11）') }}</div>
            <p>
              {{
                t(
                  '将撤销当日日结，影响营收报表、税金申报基数、银行/渠道对账，并留下完整审计链。仅店长 + 财务经理双授权后可重开。',
                )
              }}
            </p>
          </div>
          <div class="step">
            <div class="step-h">{{ t('③ 原因（必填）') }}</div>
            <select v-model="reverseReason" class="field">
              <option v-for="r in REVERSE_REASONS" :key="r" :value="r">{{ t(r) }}</option>
            </select>
            <input v-model="reverseNote" class="field mt" :placeholder="t('补充说明（可选）')" />
          </div>
          <div class="step">
            <div class="step-h">{{ t('④ 双授权') }}</div>
            <div class="dual-grid">
              <div class="auth-box" :class="{ done: activeReverseTicket?.auth_mgr_done }">
                <div>
                  {{ t('店长') }} ·
                  {{ activeReverseTicket?.auth_mgr_done ? t('已授权') : t('待扫码') }}
                </div>
                <button
                  type="button"
                  class="btn-ghost"
                  :disabled="!!activeReverseTicket?.auth_mgr_done"
                  @click="scanAuth('mgr')"
                >
                  {{ t('店长扫码') }}
                </button>
              </div>
              <div class="auth-box" :class="{ done: activeReverseTicket?.auth_fin_done }">
                <div>
                  {{ t('财务经理') }} ·
                  {{ activeReverseTicket?.auth_fin_done ? t('已授权') : t('待扫码') }}
                </div>
                <button
                  type="button"
                  class="btn-ghost"
                  :disabled="!!activeReverseTicket?.auth_fin_done"
                  @click="scanAuth('fin')"
                >
                  {{ t('财务经理扫码') }}
                </button>
              </div>
            </div>
            <button
              type="button"
              class="btn-primary w-full mt"
              :disabled="submitting"
              @click="submitReverse"
            >
              {{
                submitting
                  ? t('提交中…')
                  : activeReverseTicket
                    ? t('再次发起反结账申请')
                    : t('确认申请重开')
              }}
            </button>
            <p v-if="activeReverseTicket" class="muted mt">
              {{ t('当前工单') }} {{ activeReverseTicket.ticket_no }} ·
              {{ t(activeReverseTicket.status_label || '') }}
            </p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ra-page {
  width: 100%;
}
.ra-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.crumb {
  font-size: 12px;
  color: #79747e;
  margin-bottom: 4px;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.title-row h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
}
.risk-badge {
  font-size: 11px;
  font-weight: 700;
  color: #b3261e;
  background: #fceeee;
  border: 1px solid #f2b8b5;
  padding: 3px 8px;
  border-radius: 6px;
}
.sub {
  margin: 6px 0 0;
  font-size: 13px;
  color: #79747e;
  max-width: 560px;
  line-height: 1.5;
}
.head-actions {
  display: flex;
  gap: 8px;
}
.toast {
  position: fixed;
  right: 24px;
  top: 72px;
  z-index: 50;
  background: #1d192b;
  color: #fff;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
}
.ra-grid {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 16px;
  align-items: start;
}
@media (max-width: 960px) {
  .ra-grid {
    grid-template-columns: 1fr;
  }
}
.panel {
  background: #fffbfe;
  border: 1px solid #e7e0ec;
  border-radius: 14px;
  padding: 14px 16px;
  margin-bottom: 12px;
}
.panel-h {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 700;
}
.op-card {
  width: 100%;
  display: flex;
  gap: 10px;
  text-align: left;
  border: 1px solid #e7e0ec;
  background: #fff;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 8px;
  cursor: pointer;
}
.op-card.on {
  border-color: #6750a4;
  background: #f7f2fa;
  box-shadow: 0 0 0 1px rgba(103, 80, 164, 0.25);
}
.op-card.danger {
  border-color: #f2b8b5;
}
.op-card.on-danger {
  border-color: #b3261e;
  background: #fceeee;
}
.op-ico {
  font-size: 22px;
  color: #6750a4;
}
.op-ico.warn {
  color: #b3261e;
}
.op-title {
  font-size: 14px;
  font-weight: 700;
}
.op-desc {
  font-size: 12px;
  color: #79747e;
  margin-top: 2px;
  line-height: 1.4;
}
.field-lab {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #79747e;
  margin-bottom: 6px;
}
.field {
  width: 100%;
  border: 1px solid #cac4d0;
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 13px;
  background: #fff;
  box-sizing: border-box;
}
.thresh-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.thresh-row.mt,
.mt {
  margin-top: 10px;
}
.unit {
  font-size: 13px;
  color: #79747e;
}
.pill-forced {
  font-size: 11px;
  font-weight: 700;
  color: #b3261e;
  background: #fceeee;
  padding: 4px 8px;
  border-radius: 999px;
}
.hint-box {
  margin: 10px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #e8f0fe;
  color: #1a56db;
  font-size: 12px;
  line-height: 1.5;
}
.ticket-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.ticket-list li {
  padding: 10px 0;
  border-bottom: 1px solid #f3edf7;
}
.ticket-list li:last-child {
  border-bottom: none;
}
.tk-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
}
.tk-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #79747e;
}
.tk-st {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}
.tone-warn {
  background: #fff3e0;
  color: #ef6c00;
}
.tone-danger {
  background: #fceeee;
  color: #b3261e;
}
.tone-ok {
  background: #e8f5e9;
  color: #2e7d32;
}
.tone-mute {
  background: #f3edf7;
  color: #49454f;
}
.muted {
  font-size: 12px;
  color: #79747e;
  line-height: 1.5;
}
.wiz .step {
  margin-bottom: 16px;
}
.step-h {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
}
.row-gap {
  display: flex;
  gap: 8px;
}
.line-list {
  margin-top: 8px;
  border: 1px solid #e7e0ec;
  border-radius: 10px;
  overflow: hidden;
}
.line-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid #f3edf7;
  font-size: 13px;
  cursor: pointer;
}
.line-row:last-child {
  border-bottom: none;
}
.line-row span {
  flex: 1;
}
.redline {
  margin: 8px 0 0;
  font-size: 12px;
  color: #b3261e;
  line-height: 1.45;
}
.redline.strong {
  font-weight: 700;
}
.amt-box {
  padding: 12px;
  border-radius: 10px;
  background: #f7f2fa;
  border: 1px solid #e7e0ec;
  font-size: 13px;
}
.warn-line {
  margin: 8px 0 0;
  font-size: 12px;
  color: #ef6c00;
}
.confirm-card {
  margin-top: 8px;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid #f0c36d;
  background: #fffbf0;
}
.confirm-title {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
}
.check-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  margin: 12px 0;
  cursor: pointer;
}
.redline-box {
  padding: 12px 14px;
  border-radius: 12px;
  background: #fceeee;
  border: 1px solid #f2b8b5;
  margin-bottom: 16px;
  font-size: 13px;
  line-height: 1.5;
  color: #410e0b;
}
.dual-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
@media (max-width: 640px) {
  .dual-grid {
    grid-template-columns: 1fr;
  }
}
.auth-box {
  border: 1px dashed #cac4d0;
  border-radius: 12px;
  padding: 14px;
  text-align: center;
  font-size: 13px;
  display: grid;
  gap: 10px;
  background: #faf8fc;
}
.auth-box.done {
  border-style: solid;
  border-color: #a7d7b0;
  background: #f1faf3;
}
.btn-primary {
  border: none;
  background: #6750a4;
  color: #fff;
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary.sm,
.btn-ghost.sm {
  padding: 8px 12px;
  white-space: nowrap;
}
.btn-primary.w-full,
.w-full {
  width: 100%;
}
.btn-ghost {
  border: 1px solid #cac4d0;
  background: #fff;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 12px;
  cursor: pointer;
}
.btn-ghost:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.ticket-click {
  cursor: pointer;
  border-radius: 8px;
  padding: 10px 6px !important;
}
.ticket-click:hover {
  background: #f7f2fa;
}
.phone-lg {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 12px 14px;
}
.link-quiet {
  margin-top: 8px;
  background: none;
  border: none;
  color: #6750a4;
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}
.fallback-box {
  margin-top: 8px;
  padding: 10px;
  border-radius: 10px;
  background: #f7f2fa;
  border: 1px dashed #cac4d0;
}
.guest-verify {
  margin-top: 12px;
  padding: 12px;
  border-radius: 12px;
  background: #e8f0fe;
  border: 1px solid #bfdbfe;
  font-size: 13px;
}
.gv-title {
  font-weight: 700;
  color: #1a56db;
  margin-bottom: 6px;
  font-size: 12px;
}
.gv-hint {
  margin-top: 6px;
  color: #1a56db;
  font-size: 12px;
}
.order-cards {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}
.order-pick {
  text-align: left;
  border: 1px solid #e7e0ec;
  background: #fff;
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
}
.order-pick.on {
  border-color: #6750a4;
  background: #f7f2fa;
}
.flex-between {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.sm {
  font-size: 12px;
  margin-top: 4px;
}
.lock-mini {
  margin-top: 6px;
  font-size: 11px;
  color: #1a56db;
  font-weight: 600;
}
.lock-box {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #a7d7b0;
  background: #f1faf3;
}
.lock-main {
  font-size: 14px;
  font-weight: 700;
  color: #1b5e20;
  margin-bottom: 6px;
}
.empty-box {
  margin-top: 10px;
  padding: 12px;
  border-radius: 10px;
  background: #fff8e1;
  font-size: 13px;
}
</style>
