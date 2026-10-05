<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 退房结账 —— 必须绑定具体订单；按来源（OTA预付 / 直订现结 / 协议挂账）分支
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { fmt, PAY_CN, toast } from '../../lib/ui'
import { resolveCheckoutKind, SOURCE_LABEL, localizeLineDesc } from '../../lib/orderFlow'
import OrdersFlowNav from '../../components/OrdersFlowNav.vue'

const route = useRoute()
const router = useRouter()

const order = ref<any>(null)
const loadError = ref('')
const submitting = ref(false)

type CheckoutKind = 'prepaid' | 'collect' | 'corp'

const orderId = computed(() => {
  const q = route.query.orderId ?? route.query.order_id
  const n = Number(q)
  return Number.isFinite(n) && n > 0 ? n : 0
})

function resolveKind(o: any): CheckoutKind {
  return resolveCheckoutKind(o)
}

const kind = computed<CheckoutKind>(() => (order.value ? resolveKind(order.value) : 'collect'))

const ENTRY_CODE_CN: Record<string, string> = {
  room: '房费',
  room_charge: '房费',
  night_audit: '夜审',
  monthly_rent: '月租',
  misc: '杂费',
  fnb: '餐饮',
  deposit: '押金',
  tax: '税费',
  adjustment: '调账',
  rm: '房费',
  fb: '餐饮',
  pay: '收款',
}
const PAY_METHOD_CN: Record<string, string> = {
  wechat: '微信',
  alipay: '支付宝',
  card: '银行卡',
  cash: '现金',
  pos: '收银机',
  transfer: '转账',
  on_account: '挂账',
}

function entryCodeCn(raw?: string) {
  const k = String(raw || '').toLowerCase()
  return t(ENTRY_CODE_CN[k] || raw || '杂项')
}
function payMethodCn(raw?: string) {
  const k = String(raw || '').toLowerCase()
  return t(PAY_METHOD_CN[k] || raw || '收银')
}

const sourceLabel = computed(() => {
  const sg = order.value?.source_group
  if (SOURCE_LABEL[sg]) return t(SOURCE_LABEL[sg])
  if (order.value?.channel_name) return t(order.value.channel_name)
  return t('订单')
})

const items = computed(() => {
  const o = order.value
  if (!o) return []
  const folio = o.folio
  if (folio?.entries?.length) {
    const rows = folio.entries.map((e: any) => ({
      id: e.id,
      date: String(e.biz_date || '').slice(5, 10) || '—',
      code: entryCodeCn(e.entry_type),
      desc: localizeLineDesc(e.description || entryCodeCn(e.entry_type) || t('分录')),
      charge: Number(e.amount) > 0 ? Number(e.amount) : 0,
      pay: Number(e.amount) < 0 ? Math.abs(Number(e.amount)) : 0,
    }))
    for (const p of folio.payments || []) {
      rows.push({
        id: `pay-${p.id}`,
        date: t('收款'),
        code: t('收款'),
        desc: `${payMethodCn(p.method)}${p.pos_slip_no ? ' · ' + t('小票') + ' ' + p.pos_slip_no : ''}`,
        charge: 0,
        pay: Number(p.received_amount ?? p.amount ?? 0),
      })
    }
    return rows
  }
  const rows: any[] = []
  const list = o.items || []
  if (list.length) {
    for (const it of list) {
      const amt = Number(it.amount ?? Number(it.unit_price || 0) * Number(it.qty || 1))
      const typ = String(it.item_type || '')
      rows.push({
        id: it.id,
        date: String(o.check_in || '').slice(5, 10) || '—',
        code: typ === 'room' ? t('房费') : typ === 'fnb' ? t('餐饮') : t('杂项'),
        desc: localizeLineDesc(it.description || typ || t('消费')),
        charge: amt > 0 ? amt : 0,
        pay: amt < 0 ? Math.abs(amt) : 0,
      })
    }
  } else {
    const nights = Math.max(1, Number(o.nights || 1))
    const total = Number(o.total_amount || 0)
    const per = Math.round((total / nights) * 100) / 100
    for (let i = 0; i < nights; i++) {
      const d = o.check_in ? new Date(o.check_in) : new Date()
      d.setDate(d.getDate() + i)
      rows.push({
        id: i + 1,
        date: `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
        code: t('房费'),
        desc: `${t('房费')}（${o.room_type_name || t('客房')}）`,
        charge: per,
        pay: 0,
      })
    }
  }
  if (kind.value === 'prepaid' && Number(o.total_amount || 0) > 0) {
    rows.push({
      id: 'pay-channel',
      date: t('渠道'),
      code: t('收款'),
      desc: t('{channel}已预付', { channel: o.channel_name ? t(o.channel_name) : t('渠道') }),
      charge: 0,
      pay: Number(o.total_amount || 0),
    })
  }
  return rows
})

const charges = computed(() => {
  if (order.value?.folio) return Number(order.value.folio.charge_total || 0)
  return items.value.reduce((s, i) => s + Number(i.charge || 0), 0)
})
const pays = computed(() => {
  if (order.value?.folio) return Number(order.value.folio.payment_total || 0)
  return items.value.reduce((s, i) => s + Number(i.pay || 0), 0)
})
const balance = computed(() => {
  if (order.value?.folio && order.value.folio.balance != null) {
    return Math.max(0, Number(order.value.folio.balance))
  }
  if (kind.value === 'prepaid') return Math.max(0, charges.value - pays.value)
  if (kind.value === 'corp') return 0
  return Math.max(0, Number(order.value?.total_amount || charges.value) - pays.value)
})

const methods = ref([
  { id: 'wechat', icon: 'qr_code_scanner', label: t('微信/支付宝') },
  { id: 'card', icon: 'credit_card', label: t('银行卡') },
  { id: 'cash', icon: 'payments', label: t('现金') },
  { id: 'points', icon: 'loyalty', label: t('积分抵扣') },
])
const payMethod = ref('wechat')
const payAmount = ref('0.00')
const posSlipNo = ref('')

const depositSummary = computed(() => order.value?.deposits || null)
const depositItems = computed(() => depositSummary.value?.items || [])
const depositHeld = computed(() => Number(depositSummary.value?.held_count || 0) > 0)

const creditCheck = ref<any>(null)
const creditLoading = ref(false)

const corpChargeAmount = computed(() => {
  const o = order.value
  if (!o) return 0
  if (o.folio?.balance != null) return Math.max(0, Number(o.folio.balance))
  return Math.max(0, Number(o.total_amount || 0))
})

const corpBlocked = computed(() => Boolean(creditCheck.value?.blocked))

async function loadCreditCheck() {
  creditCheck.value = null
  const o = order.value
  if (!o || kind.value !== 'corp') return
  const corpId = o.agreement_id
  if (!corpId) return
  creditLoading.value = true
  try {
    creditCheck.value = await api.arApCheckCredit(o.hotel_id || 1, corpId, corpChargeAmount.value)
  } catch {
    creditCheck.value = null
  } finally {
    creditLoading.value = false
  }
}

function depositStatusClass(st: string) {
  if (['RELEASED', 'RELEASED_AFTER_CAPTURE', 'CAPTURED'].includes(st)) return 'dep-ok'
  if (['EXPIRED', 'DISPUTED'].includes(st)) return 'dep-bad'
  if (st === 'PARTIAL_CAPTURE') return 'dep-warn'
  return 'dep-hold'
}

function goDeposit(depositId?: string) {
  if (depositId) {
    router.push({ path: '/c9-finance/deposit-management', query: { open: depositId } })
  } else {
    router.push('/c9-finance/deposit-management')
  }
}

const pageTitle = computed(() => {
  if (kind.value === 'prepaid') return t('预付退房核对')
  if (kind.value === 'corp') return t('协议挂账退房')
  return t('收银退房结账')
})

const pageHint = computed(() => {
  if (!order.value) return t('请从订单列表选择一笔在住单进入')
  if (kind.value === 'prepaid') {
    return t('{source} · 房费已由渠道结算，核对杂费后确认退房', { source: sourceLabel.value })
  }
  if (kind.value === 'corp') {
    return t('{source} · 房费挂企业账户，确认后离店', { source: sourceLabel.value })
  }
  return t('{source} · 前台现结收款后退房', { source: sourceLabel.value })
})

const ctaLabel = computed(() => {
  if (kind.value === 'prepaid') return t('确认核对并退房')
  if (kind.value === 'corp') return t('确认挂账退房')
  return t('确认收款并退房')
})

function syncPayAmount() {
  payAmount.value = balance.value.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

async function load() {
  loadError.value = ''
  order.value = null
  if (!orderId.value) {
    loadError.value = t('结账须绑定具体订单。请从订单中心的在住单点「退房结账」进入。')
    return
  }
  try {
    const detail = await api.getOrder(orderId.value)
    order.value = detail
    syncPayAmount()
    await loadCreditCheck()
  } catch (e: any) {
    loadError.value = e?.message || t('订单加载失败')
  }
}

async function confirmCheckout() {
  if (!order.value?.id || submitting.value) return
  if (order.value.status !== 'checked_in') {
    toast(t('仅在住订单可退房'))
    return
  }
  if (depositHeld.value) {
    const held = depositSummary.value
    const okGo = confirm(
      `本单仍有 ${held?.held_count || 0} 笔在押押金（合计 ¥${Number(held?.held_yuan || 0).toFixed(0)}）。\n建议先到押金管理释放/扣尽后再退房。\n\n仍要继续退房吗？`,
    )
    if (!okGo) {
      goDeposit(depositItems.value.find((d: any) => d.in_hold)?.deposit_id)
      return
    }
  }
  if (kind.value === 'corp' && corpBlocked.value) {
    toast(creditCheck.value?.message || t('授信额度不足，无法挂账退房'), false)
    return
  }
  const tip =
    kind.value === 'prepaid'
      ? '确认渠道预付无误并办理退房？'
      : kind.value === 'corp'
        ? t('确认将本单挂企业账并退房？')
        : t('确认已收款并办理退房？')
  if (!confirm(tip)) return
  if (kind.value === 'collect' && !posSlipNo.value.trim() && payMethod.value !== 'cash') {
    toast(t('请录入收银小票号（现金可空）'), false)
    return
  }
  submitting.value = true
  try {
    await api.checkout(order.value.id, {
      payment_mode: kind.value,
      method: payMethod.value,
      pos_slip_no: posSlipNo.value.trim() || undefined,
    })
    toast(
      kind.value === 'prepaid'
        ? '已核对退房'
        : kind.value === 'corp'
          ? t('已挂账退房')
          : t('已收款退房'),
    )
    router.push('/orders')
  } catch (e: any) {
    toast(e?.message || t('退房失败'), false)
  } finally {
    submitting.value = false
  }
}

onMounted(load)
watch(orderId, load)
watch(balance, syncPayAmount)
watch([corpChargeAmount, () => order.value?.agreement_id], loadCreditCheck)
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end">
      <OrdersFlowNav mode="checkout" hide-back />
    </div>

    <div v-if="loadError && !order" class="empty-bind">
      <span class="material-symbols-outlined ico">link_off</span>
      <h1 class="font-headline-md text-on-surface">{{ t('结账未绑定订单') }}</h1>
      <p class="font-body-md text-on-surface-variant mt-2">{{ loadError }}</p>
      <button type="button" class="btn-primary mt-6" @click="router.push('/orders')">
        {{ t('返回订单中心选单 →') }}
      </button>
    </div>

    <template v-else-if="order">
      <div class="flex flex-col lg:flex-row gap-gutter">
        <div
          class="flex-1 flex flex-col border border-outline-variant bg-surface-container-lowest rounded-xl overflow-hidden"
        >
          <div
            class="p-container-padding pb-4 sticky top-0 bg-surface-container-lowest z-10 border-b border-outline-variant"
          >
            <div class="flex justify-between items-end gap-4 flex-wrap">
              <div>
                <div class="flex items-center gap-2 mb-1 flex-wrap">
                  <span
                    class="font-label-lg px-2 py-1 rounded"
                    :class="{
                      'bg-primary/10 text-primary': kind === 'collect',
                      'bg-blue-50 text-blue-700': kind === 'prepaid',
                      'bg-amber-50 text-amber-800': kind === 'corp',
                    }"
                  >
                    {{
                      kind === 'prepaid'
                        ? t('渠道预付')
                        : kind === 'corp'
                          ? t('协议挂账')
                          : t('前台现结')
                    }}</span
                  >
                  <span class="text-outline font-num-md text-sm"
                    >{{ order.order_no }} · {{ order.guest_name }}</span
                  >
                  <span
                    v-if="order.stay_room_no || order.room_no"
                    class="text-outline font-label-lg text-sm"
                    >在住房 {{ order.stay_room_no || order.room_no }}</span
                  >
                </div>
                <h1 class="font-display-lg text-on-surface">{{ pageTitle }}</h1>
                <p class="font-body-md text-on-surface-variant mt-1">{{ pageHint }}</p>
              </div>
              <div class="text-right">
                <p class="font-label-lg text-on-surface-variant mb-1">
                  {{
                    kind === 'corp'
                      ? t('挂账金额')
                      : kind === 'prepaid'
                        ? t('待核杂费')
                        : t('应收总额')
                  }}
                </p>
                <p class="font-num-xl text-[32px] leading-tight text-primary">
                  {{ fmt(kind === 'corp' ? Number(order.total_amount || 0) : balance) }}
                </p>
                <p class="text-xs text-on-surface-variant mt-1">
                  {{ t('支付状态：') }}{{ t(PAY_CN[order.payment_status] || order.payment_status) }}
                </p>
              </div>
            </div>
          </div>

          <div class="p-container-padding flex-1">
            <div
              v-if="kind === 'prepaid'"
              class="mb-4 px-4 py-3 rounded-lg border border-blue-200 bg-blue-50 text-sm text-blue-900"
            >
              {{ t('本单来自') }}
              <b>{{ order.channel_name ? t(order.channel_name) : sourceLabel }}</b
              >{{ t('，房费已在渠道侧结算。前台只需核对加项/杂费后办理退房。') }}
            </div>
            <div
              v-else-if="kind === 'corp'"
              class="mb-4 px-4 py-3 rounded-lg border text-sm"
              :class="
                corpBlocked
                  ? 'border-red-200 bg-red-50 text-red-900'
                  : 'border-amber-200 bg-amber-50 text-amber-900'
              "
            >
              <p>
                {{ t('协议客挂账：房费计入') }}
                <b>{{ order.agreement_name || order.channel_name || t('协议企业') }}</b>
                {{ t('月结，不在前台现收。确认后离店并释放房间。') }}
              </p>
              <div v-if="creditLoading" class="text-xs mt-2 opacity-70">
                {{ t('正在校验授信额度…') }}
              </div>
              <div v-else-if="creditCheck" class="mt-2 text-xs space-y-1">
                <div>
                  {{ t('授信') }} ¥{{ creditCheck.credit_limit?.toLocaleString() }} ·
                  {{ t('已用') }} ¥{{ creditCheck.credit_used?.toLocaleString() }} ·
                  {{ t('可用') }} ¥{{ creditCheck.credit_available?.toLocaleString() }}
                </div>
                <div v-if="corpBlocked" class="font-semibold text-red-700">
                  {{ creditCheck.message }} — {{ t('挂账退房已拦截') }}
                </div>
              </div>
            </div>

            <!-- 本单押金（结账必看） -->
            <div
              class="deposit-panel mb-6"
              :class="{
                'deposit-panel--held': depositHeld,
                'deposit-panel--clear': depositSummary && !depositHeld && depositSummary.count > 0,
                'deposit-panel--empty': !depositSummary?.count,
              }"
            >
              <div class="deposit-panel__head">
                <div>
                  <div class="deposit-panel__title">{{ t('本单押金') }}</div>
                  <div class="deposit-panel__sub">
                    <template v-if="!depositSummary?.count">{{ t('暂无押金记录') }}</template>
                    <template v-else-if="depositHeld">
                      {{ depositSummary.count }} {{ t('笔') }} · {{ t('其中') }}
                      <b>{{ depositSummary.held_count }}</b> {{ t('笔仍在押，合计') }}
                      <b>{{ fmt(depositSummary.held_yuan) }}</b>
                      {{ t('— 退房前建议先释放/扣尽') }}</template
                    >
                    <template v-else>
                      {{ depositSummary.count }} {{ t('笔') }} · 已全部归零（可安全结账）
                    </template>
                  </div>
                </div>
                <button type="button" class="deposit-link" @click="goDeposit()">
                  {{ t('押金管理 →') }}
                </button>
              </div>

              <div v-if="depositItems.length" class="deposit-list">
                <button
                  v-for="d in depositItems"
                  :key="d.deposit_id"
                  type="button"
                  class="deposit-row"
                  @click="goDeposit(d.deposit_id)"
                >
                  <div class="deposit-row__main">
                    <span class="deposit-id">{{ d.deposit_id }}</span>
                    <span class="deposit-form">{{ d.form_label }}</span>
                  </div>
                  <div class="deposit-row__meta">
                    <span>原额 {{ fmt(d.original_yuan) }}</span>
                    <span>可退 {{ fmt(d.remaining_yuan) }}</span>
                    <span class="dep-pill" :class="depositStatusClass(d.status)">{{
                      d.status_label
                    }}</span>
                  </div>
                </button>
              </div>
              <p v-else class="deposit-empty-hint">
                {{
                  t('可在「押金管理 → 收押向导」按手机号为本单收押；有在押时本区会显示笔数与状态。')
                }}
              </p>
            </div>

            <div
              class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden mb-6"
            >
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="bg-surface-container-low border-b border-outline-variant">
                    <th class="py-3 px-4 font-label-lg text-on-surface-variant w-1/6">
                      {{ t('日期') }}
                    </th>
                    <th class="py-3 px-4 font-label-lg text-on-surface-variant w-1/6">
                      {{ t('代码') }}
                    </th>
                    <th class="py-3 px-4 font-label-lg text-on-surface-variant w-2/6">
                      {{ t('描述') }}
                    </th>
                    <th class="py-3 px-4 font-label-lg text-on-surface-variant w-1/6 text-right">
                      {{ t('消费') }}
                    </th>
                    <th class="py-3 px-4 font-label-lg text-on-surface-variant w-1/6 text-right">
                      {{ t('付款') }}
                    </th>
                  </tr>
                </thead>
                <tbody class="font-body-md">
                  <tr
                    v-for="it in items"
                    :key="it.id"
                    class="border-b border-outline-variant hover:bg-surface-container-low/50 transition-colors"
                  >
                    <td class="py-3 px-4 text-on-surface-variant">{{ it.date }}</td>
                    <td class="py-3 px-4 font-num-md text-sm">{{ it.code }}</td>
                    <td class="py-3 px-4 text-on-surface">{{ it.desc }}</td>
                    <td class="py-3 px-4 font-num-md text-right">
                      {{ it.charge ? fmt(it.charge) : '-' }}
                    </td>
                    <td
                      class="py-3 px-4 font-num-md text-right"
                      :class="it.pay ? 'text-error' : 'text-outline'"
                    >
                      {{ it.pay ? '(' + fmt(it.pay) + ')' : '-' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- 右侧：按结账类型切换 -->
        <div
          class="w-full lg:w-[400px] bg-surface-container-lowest flex flex-col shadow-sm rounded-xl border border-outline-variant z-10"
        >
          <div class="p-6 border-b border-outline-variant bg-surface-container-low">
            <h2 class="font-headline-md text-on-surface mb-2">
              {{
                kind === 'collect'
                  ? t('付款结算')
                  : kind === 'prepaid'
                    ? t('退房确认')
                    : t('挂账确认')
              }}
            </h2>
            <p class="font-body-md text-on-surface-variant">
              {{
                kind === 'collect'
                  ? t('选择支付方式完成现结')
                  : kind === 'prepaid'
                    ? t('核对无误后释放房间')
                    : t('确认企业挂账并释放房间')
              }}
            </p>
          </div>

          <div class="p-6 flex-1 overflow-y-auto">
            <template v-if="kind === 'collect'">
              <div class="grid grid-cols-2 gap-3 mb-6">
                <label
                  v-for="m in methods"
                  :key="m.id"
                  class="flex flex-col items-center justify-center p-4 border rounded-xl cursor-pointer transition-all hover:bg-surface-container-low"
                  :class="
                    payMethod === m.id
                      ? 'border-primary bg-primary/5'
                      : 'border-outline-variant opacity-60'
                  "
                  @click="payMethod = m.id"
                >
                  <span
                    class="material-symbols-outlined mb-2 text-[28px]"
                    :class="payMethod === m.id ? 'text-primary' : 'text-on-surface-variant'"
                    >{{ m.icon }}</span
                  >
                  <span
                    class="font-label-lg"
                    :class="
                      payMethod === m.id ? 'text-primary font-medium' : 'text-on-surface-variant'
                    "
                    >{{ m.label }}</span
                  >
                </label>
              </div>
              <div class="mb-6">
                <label class="block font-label-lg text-on-surface-variant mb-2">{{
                  t('支付金额')
                }}</label>
                <div class="relative">
                  <span
                    class="absolute left-4 top-1/2 -translate-y-1/2 font-num-xl text-on-surface-variant"
                    >¥</span
                  >
                  <input
                    v-model="payAmount"
                    class="w-full pl-10 pr-4 py-3 bg-surface border border-outline-variant rounded-lg font-num-xl text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                    type="text"
                  />
                </div>
              </div>
              <div class="mb-6">
                <label class="block font-label-lg text-on-surface-variant mb-2">{{
                  t('收银小票号')
                }}</label>
                <input
                  v-model="posSlipNo"
                  class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-lg text-sm focus:outline-none focus:border-primary"
                  :placeholder="t('店内收银机打印的小票号（必填，现金可空）')"
                />
                <p class="text-xs text-on-surface-variant mt-2">
                  {{ t('系统不对接支付网关；收款后在此人工录入小票号对账。') }}
                </p>
              </div>
              <div
                class="bg-surface-container-low rounded-xl p-4 flex flex-col items-center justify-center border border-dashed border-outline mb-6 h-24"
              >
                <span class="material-symbols-outlined text-outline mb-1">point_of_sale</span>
                <span class="font-label-lg text-outline text-center text-xs px-2">{{
                  t('请先在店内收银机完成收款，再回本页录入小票并退房')
                }}</span>
              </div>
            </template>

            <template v-else-if="kind === 'prepaid'">
              <ul class="space-y-3 text-sm text-on-surface mb-6">
                <li class="flex gap-2">
                  <span class="material-symbols-outlined text-primary text-[18px]"
                    >check_circle</span
                  >
                  {{ t('渠道预付房费已入账') }}
                </li>
                <li class="flex gap-2">
                  <span class="material-symbols-outlined text-primary text-[18px]"
                    >check_circle</span
                  >
                  {{ t('杂费余额') }}：{{ fmt(balance) }}
                </li>
                <li class="flex gap-2">
                  <span class="material-symbols-outlined text-on-surface-variant text-[18px]"
                    >meeting_room</span
                  >
                  {{ t('退房后房间将标为脏房交房务') }}
                </li>
              </ul>
              <p
                v-if="balance > 0"
                class="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4"
              >
                {{ t('仍有杂费未结，确认前请向客人补收或转入下单处理。') }}
              </p>
            </template>

            <template v-else>
              <ul class="space-y-3 text-sm text-on-surface mb-6">
                <li class="flex gap-2">
                  <span class="material-symbols-outlined text-amber-700 text-[18px]"
                    >account_balance</span
                  >
                  {{ t('挂账企业') }}：{{
                    order.agreement_name || order.channel_name || t('协议客户')
                  }}
                </li>
                <li class="flex gap-2">
                  <span class="material-symbols-outlined text-amber-700 text-[18px]"
                    >receipt_long</span
                  >
                  本单金额 {{ fmt(corpChargeAmount) }} 计入月结
                </li>
                <li v-if="creditCheck && !corpBlocked" class="flex gap-2">
                  <span class="material-symbols-outlined text-emerald-600 text-[18px]"
                    >verified</span
                  >
                  授信可用 ¥{{ creditCheck.credit_available?.toLocaleString() }}
                </li>
                <li class="flex gap-2">
                  <span class="material-symbols-outlined text-on-surface-variant text-[18px]"
                    >meeting_room</span
                  >
                  {{ t('退房后房间将标为脏房交房务') }}
                </li>
              </ul>
              <p
                v-if="corpBlocked"
                class="text-xs text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-4"
              >
                {{ creditCheck?.message }}。{{ t('请改现结/担保，或到') }}
                <button type="button" class="underline" @click="router.push('/c9-finance/ar-ap')">
                  {{ t('应收应付中心') }}
                </button>
                {{ t('处理回款后再挂账。') }}
              </p>
            </template>
          </div>

          <div class="p-6 border-t border-outline-variant bg-surface-container-lowest">
            <p
              v-if="depositHeld"
              class="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-3"
            >
              仍有在押{{ t('押金') }} {{ fmt(depositSummary?.held_yuan) }}（{{
                depositSummary?.held_count
              }}
              {{ t('笔') }}）。确认退房时会再次提示。
            </p>
            <button
              type="button"
              class="w-full py-4 bg-primary text-on-primary rounded-xl font-headline-md shadow-sm hover:bg-primary/90 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              :disabled="
                submitting || order.status !== 'checked_in' || (kind === 'corp' && corpBlocked)
              "
              @click="confirmCheckout"
            >
              {{ submitting ? t('处理中…') : ctaLabel }}
              <span class="material-symbols-outlined">arrow_forward</span>
            </button>
            <p
              v-if="order.status !== 'checked_in'"
              class="text-xs text-on-surface-variant text-center mt-2"
            >
              当前状态不可退房（{{ order.status }}）
            </p>
          </div>
        </div>
      </div>
    </template>
  </div>
  <div class="related-finance">
    <span>{{ t('本页属前台单客结账（绑定订单），不计入日结主线。') }}</span>
    <button type="button" class="related-btn" @click="router.push('/c9-finance/night-audit')">
      {{ t('进入 ⑨ 日结（夜审）→') }}
    </button>
  </div>
</template>

<style scoped>
.empty-bind {
  max-width: 480px;
  margin: 48px auto;
  text-align: center;
  padding: 32px 24px;
  border: 1px dashed var(--outline-variant, #e2e5eb);
  border-radius: 16px;
  background: var(--surface-container-lowest, #fff);
}
.empty-bind .ico {
  font-size: 40px;
  color: var(--outline, #9aa1ad);
  margin-bottom: 12px;
}
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 10px;
  background: var(--primary, #2563eb);
  color: #fff;
  font-size: 14px;
  border: none;
  cursor: pointer;
}
.related-finance {
  position: sticky;
  bottom: 0;
  z-index: 40;
  margin-top: 24px;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  border-top: 1px solid var(--outline-variant, #e2e5eb);
  background: var(--surface-container-lowest, #fff);
  box-shadow: 0 -4px 16px rgba(15, 23, 42, 0.06);
  font-size: 13px;
  color: var(--on-surface-variant, #5b616e);
}
.related-btn {
  border: 1px solid var(--primary, #2563eb);
  background: var(--primary, #2563eb);
  color: #fff;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
}
.deposit-panel {
  border-radius: 12px;
  border: 1px solid var(--outline-variant, #e2e5eb);
  background: var(--surface-container-low, #f5f6f8);
  padding: 14px 16px;
}
.deposit-panel--held {
  border-color: #f0c36d;
  background: #fff8e8;
}
.deposit-panel--clear {
  border-color: #a7d7b0;
  background: #f1faf3;
}
.deposit-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}
.deposit-panel__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--on-surface, #1a1c1e);
}
.deposit-panel__sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  line-height: 1.5;
}
.deposit-link {
  flex-shrink: 0;
  border: none;
  background: none;
  color: var(--primary, #2563eb);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
.deposit-list {
  display: grid;
  gap: 8px;
}
.deposit-row {
  width: 100%;
  text-align: left;
  border: 1px solid var(--outline-variant, #e2e5eb);
  background: #fff;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
}
.deposit-row:hover {
  border-color: var(--primary, #2563eb);
}
.deposit-row__main {
  display: flex;
  gap: 10px;
  align-items: baseline;
  flex-wrap: wrap;
}
.deposit-id {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  font-weight: 600;
}
.deposit-form {
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
}
.deposit-row__meta {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
}
.dep-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}
.dep-hold {
  background: #e8def8;
  color: #4a4458;
}
.dep-warn {
  background: #fff3e0;
  color: #ef6c00;
}
.dep-bad {
  background: #fdecea;
  color: #c62828;
}
.dep-ok {
  background: #e8f5e9;
  color: #2e7d32;
}
.deposit-empty-hint {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  line-height: 1.5;
}
</style>
