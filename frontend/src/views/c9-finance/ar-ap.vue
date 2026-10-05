<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'
import { localizeSeedText } from '../../lib/localizeSeed'

/**
 * 应收应付中心 —— 对账与结算二级
 * 对齐原型：AR/AP KPI · 授信 · 单据列表 · 回款/付款/挂账/坏账二次确认
 */
import { computed, onMounted, ref, watch } from 'vue'
import FinanceOpsNav from '../../components/FinanceOpsNav.vue'
import FinanceAiPlanDrawer from '../../components/FinanceAiPlanDrawer.vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

function loc(s?: string | null) {
  return localizeSeedText(s)
}

type MainTab = 'ar' | 'ap' | 'age'
type ArFilter = 'all' | 'corp_on_account' | 'ota_settlement' | 'meeting' | 'longstay'

const arFilterOptions: { code: ArFilter; label: string }[] = [
  { code: 'all', label: '全部' },
  { code: 'corp_on_account', label: '企业挂账' },
  { code: 'ota_settlement', label: 'OTA结算' },
  { code: 'meeting', label: '会议' },
  { code: 'longstay', label: '长包房' },
]

const mainTab = ref<MainTab>('ar')
const arFilter = ref<ArFilter>('all')
const loading = ref(false)
const err = ref('')
const toast = ref('')

const kpi = ref({
  ar_balance: 0,
  ar_overdue: 0,
  ar_aging_90_plus: 0,
  ar_week_receipts: 0,
  ap_balance: 0,
  ap_pending: 0,
  ap_next_due: null as string | null,
  ap_week_payments: 0,
})
const aging = ref({ d0_30: 0, d30_60: 0, d60_90: 0, d90_plus: 0 })
const creditAccounts = ref<any[]>([])
const corps = ref<any[]>([])
const arInvoices = ref<any[]>([])
const apInvoices = ref<any[]>([])
const asOf = ref('')
const footnote = ref('')
const aiOpen = ref(false)
const todos = ref<any[]>([])
const todosCollapsed = ref(false)

const TODO_TYPE_LABEL: Record<string, string> = {
  overdue_collect: t('逾期催收'),
  credit_warn: t('授信预警'),
  aging_90: t('90+天预警'),
}

const receiptOpen = ref(false)
const paymentOpen = ref(false)
const chargeOpen = ref(false)
const writeOffOpen = ref(false)
const curAr = ref<any>(null)
const curAp = ref<any>(null)

const receiptAmt = ref(0)
const receiptChannel = ref('对公转账')
const receiptRef = ref('')
const receiptChecked = ref(false)

const paymentAmt = ref(0)
const paymentChannel = ref('对公转账')
const paymentRef = ref('')
const paymentChecked = ref(false)

const chargeCorpId = ref<number | null>(null)
const chargeAmt = ref(0)
const chargeNote = ref('')
const chargeChecked = ref(false)
const creditHint = ref('')

const writeReason = ref('')
const writeApprover = ref('')
const writeChecked = ref(false)

const AR_STATUS: Record<string, { label: string; cls: string }> = {
  open: { label: t('待结算'), cls: 'wait' },
  partial: { label: t('部分结清'), cls: 'part' },
  settled: { label: t('已结清'), cls: 'done' },
  overdue: { label: t('逾期'), cls: 'ovr' },
  bad_debt: { label: t('坏账'), cls: 'ovr' },
}
const AP_STATUS: Record<string, { label: string; cls: string }> = {
  open: { label: t('待付款'), cls: 'wait' },
  partial: { label: t('部分结清'), cls: 'part' },
  settled: { label: t('已结清'), cls: 'done' },
  pending_deduct: { label: t('待结算扣减'), cls: 'pend' },
  disputed: { label: t('争议中'), cls: 'ovr' },
}

const filteredAr = computed(() => {
  if (arFilter.value === 'all') return arInvoices.value
  return arInvoices.value.filter((r) => (r.type_code || r.type) === arFilter.value)
})

function fmtYuan(v: number) {
  return `¥${(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
}

function showToast(msg: string) {
  toast.value = msg
  setTimeout(() => {
    toast.value = ''
  }, 2200)
}

async function load() {
  const hid = hotelStore.hotelId
  if (!hid) return
  loading.value = true
  err.value = ''
  try {
    const data = await api.arApWorkspace(hid)
    kpi.value = data.kpi || kpi.value
    aging.value = data.aging || aging.value
    creditAccounts.value = data.credit_accounts || []
    corps.value = data.corps || []
    arInvoices.value = data.ar_invoices || []
    apInvoices.value = data.ap_invoices || []
    todos.value = data.todos || []
    asOf.value = data.as_of || ''
    footnote.value = data.footnote || ''
  } catch (e: any) {
    err.value = e?.message || t('加载失败')
  } finally {
    loading.value = false
  }
}

async function checkCreditLive() {
  const hid = hotelStore.hotelId
  if (!hid || !chargeCorpId.value || chargeAmt.value <= 0) {
    creditHint.value = ''
    return
  }
  try {
    const r = await api.arApCheckCredit(hid, chargeCorpId.value, chargeAmt.value)
    creditHint.value = r.blocked
      ? `⚠ ${r.message}（可用 ${fmtYuan(r.credit_available)}）`
      : `✓ ${r.message} · 可用 ${fmtYuan(r.credit_available)}`
  } catch {
    creditHint.value = ''
  }
}

watch([chargeCorpId, chargeAmt], checkCreditLive)

function openReceipt(row: any) {
  curAr.value = row
  receiptAmt.value = row.balance
  receiptChannel.value = t('对公转账')
  receiptRef.value = ''
  receiptChecked.value = false
  receiptOpen.value = true
}

function openPayment(row: any) {
  curAp.value = row
  paymentAmt.value = row.balance
  paymentChannel.value = t('对公转账')
  paymentRef.value = ''
  paymentChecked.value = false
  paymentOpen.value = true
}

function openCharge() {
  chargeCorpId.value = corps.value[0]?.id ?? null
  chargeAmt.value = 3000
  chargeNote.value = ''
  chargeChecked.value = false
  creditHint.value = ''
  chargeOpen.value = true
  checkCreditLive()
}

function openWriteOff(row: any) {
  curAr.value = row
  writeReason.value = ''
  writeApprover.value = ''
  writeChecked.value = false
  writeOffOpen.value = true
}

function todoFromAr(arId: number) {
  return arInvoices.value.find((r) => r.id === arId) || null
}

function goTodoReceipt(todo: any) {
  const row = todo.ar_id ? todoFromAr(todo.ar_id) : null
  if (row) {
    mainTab.value = 'ar'
    openReceipt(row)
    return
  }
  showToast(t('该待办无关联应收单据，请在列表中手动处理'))
}

function goTodoWriteOff(todo: any) {
  const row = todo.ar_id ? todoFromAr(todo.ar_id) : null
  if (row) {
    mainTab.value = 'ar'
    openWriteOff(row)
    return
  }
  showToast(t('该待办无关联应收单据'))
}

async function dismissTodo(todo: any) {
  const hid = hotelStore.hotelId
  if (!hid) return
  try {
    await api.arApDismissTodo(hid, todo.id, t('前台已跟进'))
    showToast(t('待办已关闭'))
    await load()
  } catch (e: any) {
    showToast(e?.message || '操作失败')
  }
}

async function confirmReceipt() {
  if (!receiptChecked.value) {
    showToast(t('请先勾选「已核对回款金额与单据一致」'))
    return
  }
  const hid = hotelStore.hotelId
  if (!hid || !curAr.value) return
  try {
    await api.arApReceipt(hid, curAr.value.id, {
      amount: receiptAmt.value,
      channel: receiptChannel.value,
      ref_no: receiptRef.value,
    })
    receiptOpen.value = false
    showToast(`已回款 ${fmtYuan(receiptAmt.value)} · 审计日志已写入`)
    await load()
  } catch (e: any) {
    showToast(e?.message || '回款失败')
  }
}

async function confirmPayment() {
  if (!paymentChecked.value) {
    showToast(t('请先勾选「已核对付款金额与单据一致」'))
    return
  }
  const hid = hotelStore.hotelId
  if (!hid || !curAp.value) return
  try {
    await api.arApPayment(hid, curAp.value.id, {
      amount: paymentAmt.value,
      channel: paymentChannel.value,
      ref_no: paymentRef.value,
    })
    paymentOpen.value = false
    showToast(`已付款 ${fmtYuan(paymentAmt.value)} · 审计日志已写入`)
    await load()
  } catch (e: any) {
    showToast(e?.message || '付款失败')
  }
}

async function confirmCharge() {
  if (!chargeChecked.value) {
    showToast(t('请先勾选「已核对客户授权签单人与挂账额度」'))
    return
  }
  const hid = hotelStore.hotelId
  if (!hid || !chargeCorpId.value) return
  try {
    await api.arApCharge(hid, {
      corp_id: chargeCorpId.value,
      amount: chargeAmt.value,
      note: chargeNote.value || undefined,
    })
    chargeOpen.value = false
    showToast(`挂账 ${fmtYuan(chargeAmt.value)} 已入账`)
    await load()
  } catch (e: any) {
    showToast(e?.message || '挂账失败')
  }
}

async function confirmWriteOff() {
  if (!writeChecked.value) {
    showToast(t('请确认已获总经理审批'))
    return
  }
  const hid = hotelStore.hotelId
  if (!hid || !curAr.value) return
  try {
    await api.arApWriteOff(hid, curAr.value.id, {
      reason: writeReason.value,
      approver: writeApprover.value,
    })
    writeOffOpen.value = false
    showToast(t('坏账核销完成 · 不可逆留痕'))
    await load()
  } catch (e: any) {
    showToast(e?.message || '核销失败')
  }
}

function creditStatusLabel(c: any) {
  if (c.blocked) return { text: t('超额·已拦截'), cls: 'blocked' }
  if (c.status === 'overdue') return { text: t('逾期提醒'), cls: 'late' }
  return { text: t('正常'), cls: 'ok' }
}

function usageColor(rate: number) {
  if (rate > 90) return 'bg-red-500'
  if (rate > 80) return 'bg-amber-500'
  return 'bg-emerald-500'
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="arap-page">
    <FinanceOpsNav />
    <div class="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background">{{ t('应收应付中心') }}</h1>
      </div>
      <button
        v-if="commercialEnabled()"
        type="button"
        class="btn-sm primary flex items-center gap-1 px-4 py-2"
        @click="aiOpen = true"
      >
        <span class="material-symbols-outlined text-[18px]">auto_awesome</span>
        {{ t('AI 安排') }}
      </button>
    </div>

    <FinanceAiPlanDrawer v-model:open="aiOpen" scene="ar_ap" @confirmed="load" />

    <div v-if="err" class="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm">{{ err }}</div>

    <!-- KPI 双区 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-5">
      <div class="kpi-box ar">
        <h3>{{ t('应收（AR）') }}</h3>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div class="kpi-cell">
            <div class="v">{{ fmtYuan(kpi.ar_balance) }}</div>
            <div class="l">{{ t('应收余额') }}</div>
          </div>
          <div class="kpi-cell">
            <div class="v text-red-600">{{ fmtYuan(kpi.ar_overdue) }}</div>
            <div class="l">{{ t('逾期金额') }}</div>
          </div>
          <div class="kpi-cell">
            <div class="v" :class="kpi.ar_aging_90_plus > 0 ? 'text-red-600' : ''">
              {{ fmtYuan(kpi.ar_aging_90_plus) }}
            </div>
            <div class="l">{{ t('90+ 天预警') }}</div>
          </div>
          <div class="kpi-cell">
            <div class="v text-emerald-600">{{ fmtYuan(kpi.ar_week_receipts) }}</div>
            <div class="l">{{ t('本周回款') }}</div>
          </div>
        </div>
      </div>
      <div class="kpi-box ap">
        <h3>{{ t('应付（AP）') }}</h3>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div class="kpi-cell">
            <div class="v">{{ fmtYuan(kpi.ap_balance) }}</div>
            <div class="l">{{ t('应付余额') }}</div>
          </div>
          <div class="kpi-cell">
            <div class="v text-amber-600">{{ fmtYuan(kpi.ap_pending) }}</div>
            <div class="l">{{ t('待付款') }}</div>
          </div>
          <div class="kpi-cell">
            <div class="v text-sm">{{ kpi.ap_next_due || '—' }}</div>
            <div class="l">{{ t('最近账期') }}</div>
          </div>
          <div class="kpi-cell">
            <div class="v text-emerald-600">{{ fmtYuan(kpi.ap_week_payments) }}</div>
            <div class="l">{{ t('本周付款') }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 催收待办 -->
    <div v-if="todos.length" class="card todo-card mb-5">
      <div class="card-h">
        <div class="flex items-center gap-2">
          <b>{{ t('催收与预警待办') }}</b>
          <span class="todo-count">{{ todos.length }}</span>
        </div>
        <button type="button" class="filter-chip" @click="todosCollapsed = !todosCollapsed">
          {{ todosCollapsed ? t('展开') : t('收起') }}
        </button>
      </div>
      <div v-show="!todosCollapsed" class="card-b todo-list">
        <div v-for="tag in todos" :key="tag.id" class="todo-row" :class="tag.priority">
          <div class="todo-main">
            <div class="todo-tags">
              <span class="badge" :class="tag.priority === 'high' ? 'ovr' : 'wait'">
                {{ TODO_TYPE_LABEL[tag.type] || tag.type }}</span
              >
              <span v-if="tag.source === 'ai'" class="pill">AI</span>
            </div>
            <div class="todo-title">{{ loc(tag.title) }}</div>
            <div v-if="tag.detail" class="todo-detail">{{ loc(tag.detail) }}</div>
          </div>
          <div class="todo-actions">
            <button
              v-if="tag.ar_id && tag.type !== 'credit_warn'"
              type="button"
              class="btn-sm primary"
              @click="goTodoReceipt(tag)"
            >
              {{ t('去回款') }}
            </button>
            <button
              v-if="tag.type === 'aging_90' && tag.ar_id"
              type="button"
              class="btn-sm danger"
              @click="goTodoWriteOff(tag)"
            >
              {{ t('坏账') }}
            </button>
            <button type="button" class="btn-sm" @click="dismissTodo(tag)">
              {{ t('已跟进') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab -->
    <div class="flex flex-wrap gap-2 mb-4">
      <button
        type="button"
        class="tab-btn"
        :class="{ on: mainTab === 'ar' }"
        @click="mainTab = 'ar'"
      >
        {{ t('应收') }}
      </button>
      <button
        type="button"
        class="tab-btn"
        :class="{ on: mainTab === 'ap' }"
        @click="mainTab = 'ap'"
      >
        {{ t('应付') }}
      </button>
      <button
        type="button"
        class="tab-btn"
        :class="{ on: mainTab === 'age' }"
        @click="mainTab = 'age'"
      >
        {{ t('账龄与信用') }}
      </button>
    </div>

    <!-- 应收 -->
    <div v-show="mainTab === 'ar'" class="flex flex-col lg:flex-row gap-4">
      <div class="w-full lg:w-72 shrink-0">
        <div class="card">
          <div class="card-h">
            <b>{{ t('授信额度') }}</b>
            <button type="button" class="btn-sm primary" @click="openCharge">
              {{ t('新增挂账') }}
            </button>
          </div>
          <div class="card-b space-y-3">
            <div v-if="!creditAccounts.length" class="text-sm text-on-surface-variant">
              {{ t('暂无协议单位') }}
            </div>
            <div v-for="c in creditAccounts" :key="c.corp_id" class="credit-card">
              <div class="font-semibold text-sm">{{ c.name }}</div>
              <div class="text-xs text-on-surface-variant mt-0.5">
                {{ t('授信') }} {{ fmtYuan(c.credit_limit) }} · {{ t('账期') }} {{ c.term_days }}
                {{ t('天') }}
              </div>
              <div class="h-1.5 rounded bg-surface-container-high my-2 overflow-hidden">
                <div
                  class="h-full rounded transition-all"
                  :class="usageColor(c.usage_rate)"
                  :style="{ width: `${Math.min(100, c.usage_rate)}%` }"
                />
              </div>
              <div class="flex justify-between text-xs">
                <span>{{ t('已用') }} {{ fmtYuan(c.credit_used) }}（{{ c.usage_rate }}%）</span>
                <span
                  :class="{
                    'text-red-600 font-semibold': c.blocked,
                    'text-amber-600 font-semibold': c.status === 'overdue' && !c.blocked,
                    'text-emerald-600': c.status === 'normal',
                  }"
                >
                  {{ creditStatusLabel(c).text }}</span
                >
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="flex-1 min-w-0">
        <div class="card">
          <div class="card-h">
            <b>{{ t('应收单据') }}</b>
            <div class="flex flex-wrap gap-1">
              <button
                v-for="f in arFilterOptions"
                :key="f.code"
                type="button"
                class="filter-chip"
                :class="{ on: arFilter === f.code }"
                @click="arFilter = f.code"
              >
                {{ t(f.label) }}
              </button>
            </div>
          </div>
          <div class="overflow-x-auto">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t('客户 / 平台') }}</th>
                  <th>{{ t('类型') }}</th>
                  <th>{{ t('单据') }}</th>
                  <th>{{ t('计算过程') }}</th>
                  <th class="num">{{ t('金额') }}</th>
                  <th class="num">{{ t('已收') }}</th>
                  <th>{{ t('账期') }}</th>
                  <th>{{ t('状态') }}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading">
                  <td colspan="9" class="text-center text-on-surface-variant py-8">
                    {{ t('加载中…') }}
                  </td>
                </tr>
                <tr v-else-if="!filteredAr.length">
                  <td colspan="9" class="text-center text-on-surface-variant py-8">
                    {{ t('暂无应收单据') }}
                  </td>
                </tr>
                <tr v-for="r in filteredAr" :key="r.id">
                  <td>
                    {{ r.customer_name }}
                    <span v-if="r.pill_note" class="pill">{{ loc(r.pill_note) }}</span>
                  </td>
                  <td>{{ loc(r.type) }}</td>
                  <td class="max-w-[180px] truncate" :title="r.doc_label">{{ r.doc_label }}</td>
                  <td class="calc-cell" :title="loc(r.calc_process) || '—'">
                    {{ loc(r.calc_process) || '—' }}
                  </td>
                  <td class="num">{{ fmtYuan(r.amount) }}</td>
                  <td class="num">{{ fmtYuan(r.paid_amount) }}</td>
                  <td>{{ r.due_date || '—' }}</td>
                  <td>
                    <span class="badge" :class="AR_STATUS[r.status]?.cls || 'wait'">
                      {{ AR_STATUS[r.status]?.label || r.status }}</span
                    >
                  </td>
                  <td class="actions">
                    <template v-if="r.status === 'settled' || r.status === 'bad_debt'">—</template>
                    <template v-else>
                      <button type="button" class="btn-sm primary" @click="openReceipt(r)">
                        {{ t('回款') }}
                      </button>
                      <button
                        v-if="r.status === 'overdue'"
                        type="button"
                        class="btn-sm danger ml-1"
                        @click="openWriteOff(r)"
                      >
                        {{ t('坏账') }}
                      </button>
                    </template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- 应付 -->
    <div v-show="mainTab === 'ap'">
      <div class="card">
        <div class="card-h">
          <b>{{ t('应付单据') }}</b>
          <span class="sub">{{ t('OTA 佣金与应收对账') }}</span>
        </div>
        <div class="overflow-x-auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('收款方') }}</th>
                <th>{{ t('类型') }}</th>
                <th>{{ t('单据') }}</th>
                <th>{{ t('计算过程') }}</th>
                <th class="num">{{ t('金额') }}</th>
                <th class="num">{{ t('已付') }}</th>
                <th>{{ t('账期') }}</th>
                <th>{{ t('状态') }}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in apInvoices" :key="r.id">
                <td>
                  {{ r.vendor_name }}
                  <span v-if="r.note" class="pill pre">{{ r.note }}</span>
                </td>
                <td>{{ loc(r.type) }}</td>
                <td>{{ r.doc_label }}</td>
                <td class="calc-cell" :title="loc(r.calc_process) || '—'">
                  {{ loc(r.calc_process) || '—' }}
                </td>
                <td class="num">{{ fmtYuan(r.amount) }}</td>
                <td class="num">{{ fmtYuan(r.paid_amount) }}</td>
                <td>{{ r.due_date || '—' }}</td>
                <td>
                  <span class="badge" :class="AP_STATUS[r.status]?.cls || 'wait'">
                    {{ AP_STATUS[r.status]?.label || r.status }}</span
                  >
                </td>
                <td class="actions">
                  <template v-if="r.status === 'settled' || r.status === 'pending_deduct'"
                    >—</template
                  >
                  <button v-else type="button" class="btn-sm primary" @click="openPayment(r)">
                    {{ t('付款') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <p class="hint-amber mt-3 text-sm">
        {{ t('应付仅展示 OTA 佣金说明') }}
      </p>
    </div>

    <!-- 账龄与信用 -->
    <div v-show="mainTab === 'age'">
      <div class="card">
        <div class="card-h">
          <b>{{ t('应收账龄分析') }}</b>
          <span class="sub">截至 {{ asOf || t('今日') }}</span>
        </div>
        <div class="card-b">
          <div class="age-grid mb-5">
            <div class="age-cell">
              <div class="v">{{ fmtYuan(aging.d0_30) }}</div>
              <div class="l">{{ t('0–30 天') }}</div>
            </div>
            <div class="age-cell">
              <div class="v">{{ fmtYuan(aging.d30_60) }}</div>
              <div class="l">{{ t('30–60 天') }}</div>
            </div>
            <div class="age-cell">
              <div class="v">{{ fmtYuan(aging.d60_90) }}</div>
              <div class="l">{{ t('60–90 天') }}</div>
            </div>
            <div class="age-cell hot">
              <div class="v">{{ fmtYuan(aging.d90_plus) }}</div>
              <div class="l">{{ t('90+ 天') }}</div>
            </div>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('授信客户') }}</th>
                <th class="num">{{ t('授信额度') }}</th>
                <th class="num">{{ t('已用') }}</th>
                <th class="num">{{ t('使用率') }}</th>
                <th>{{ t('最近逾期') }}</th>
                <th>{{ t('状态') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in creditAccounts" :key="c.corp_id">
                <td>{{ c.name }}</td>
                <td class="num">{{ fmtYuan(c.credit_limit) }}</td>
                <td class="num">{{ fmtYuan(c.credit_used) }}</td>
                <td class="num" :class="c.usage_rate > 80 ? 'text-red-600' : ''">
                  {{ c.usage_rate }}%
                </td>
                <td>{{ c.overdue_count ? `${c.overdue_count} ${t('笔')}` : t('无') }}</td>
                <td>
                  <span
                    class="badge"
                    :class="
                      creditStatusLabel(c).cls === 'ok'
                        ? 'done'
                        : creditStatusLabel(c).cls === 'blocked'
                          ? 'ovr'
                          : 'wait'
                    "
                  >
                    {{ creditStatusLabel(c).text }}</span
                  >
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <p v-if="footnote" class="foot-note mt-6">{{ footnote }}</p>

    <!-- 回款模态 -->
    <div v-if="receiptOpen" class="modal-mask" @click.self="receiptOpen = false">
      <div class="modal">
        <div class="modal-h">
          <span>{{ t('回款核销') }}</span>
          <button type="button" class="close" @click="receiptOpen = false">✕</button>
        </div>
        <div class="modal-b">
          <div class="li">
            <span>{{ t('客户') }}</span
            ><b>{{ curAr?.customer_name }}</b>
          </div>
          <div class="li">
            <span>{{ t('应收单据') }}</span
            ><b>{{ curAr?.doc_label }}</b>
          </div>
          <div class="li">
            <span>{{ t('应收余额') }}</span
            ><b>{{ fmtYuan(curAr?.balance) }}</b>
          </div>
          <label class="field"
            >{{ t('本次回款金额') }}<input v-model.number="receiptAmt" type="number" class="inp"
          /></label>
          <label class="field"
            >{{ t('回款方式') }}
            <select v-model="receiptChannel" class="inp">
              <option>{{ t('对公转账') }}</option>
              <option>{{ t('原路退回账户') }}</option>
              <option>{{ t('现金（特批）') }}</option>
            </select>
          </label>
          <p class="hint-blue">
            {{ t('请当面/系统核对回款金额与单据，确认后核销应收并写入审计日志。') }}
          </p>
          <label class="chk"
            ><input v-model="receiptChecked" type="checkbox" />
            {{ t('我已核对回款金额与单据一致') }}</label
          >
        </div>
        <div class="modal-f">
          <button type="button" class="btn" @click="receiptOpen = false">{{ t('取消') }}</button>
          <button type="button" class="btn primary" @click="confirmReceipt">
            {{ t('确认回款') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 付款模态 -->
    <div v-if="paymentOpen" class="modal-mask" @click.self="paymentOpen = false">
      <div class="modal">
        <div class="modal-h">
          <span>{{ t('付款核销') }}</span>
          <button type="button" class="close" @click="paymentOpen = false">✕</button>
        </div>
        <div class="modal-b">
          <div class="li">
            <span>{{ t('收款方') }}</span
            ><b>{{ curAp?.vendor_name }}</b>
          </div>
          <div class="li">
            <span>{{ t('应付单据') }}</span
            ><b>{{ curAp?.doc_label }}</b>
          </div>
          <div class="li">
            <span>{{ t('应付余额') }}</span
            ><b>{{ fmtYuan(curAp?.balance) }}</b>
          </div>
          <label class="field"
            >{{ t('本次付款金额') }}<input v-model.number="paymentAmt" type="number" class="inp"
          /></label>
          <label class="field"
            >{{ t('付款方式') }}
            <select v-model="paymentChannel" class="inp">
              <option>{{ t('对公转账') }}</option>
              <option>{{ t('银行代扣') }}</option>
            </select>
          </label>
          <p class="hint-blue">{{ t('确认后核销应付并写入审计日志。') }}</p>
          <label class="chk"
            ><input v-model="paymentChecked" type="checkbox" />
            {{ t('我已核对付款金额与单据一致') }}</label
          >
        </div>
        <div class="modal-f">
          <button type="button" class="btn" @click="paymentOpen = false">{{ t('取消') }}</button>
          <button type="button" class="btn primary" @click="confirmPayment">
            {{ t('确认付款') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 挂账模态 -->
    <div v-if="chargeOpen" class="modal-mask" @click.self="chargeOpen = false">
      <div class="modal">
        <div class="modal-h">
          <span>{{ t('新增企业挂账') }}</span>
          <button type="button" class="close" @click="chargeOpen = false">✕</button>
        </div>
        <div class="modal-b">
          <label class="field"
            >{{ t('协议单位') }}
            <select v-model="chargeCorpId" class="inp">
              <option v-for="c in corps" :key="c.id" :value="c.id">
                {{ c.name }}（{{ t('可用') }} {{ fmtYuan(c.credit_available) }}）
              </option>
            </select>
          </label>
          <label class="field"
            >{{ t('挂账金额') }}<input v-model.number="chargeAmt" type="number" class="inp"
          /></label>
          <p
            v-if="creditHint"
            class="text-sm"
            :class="creditHint.startsWith('⚠') ? 'text-red-600' : 'text-emerald-600'"
          >
            {{ creditHint }}
          </p>
          <label class="field"
            >{{ t('备注') }}<input v-model="chargeNote" class="inp" :placeholder="t('可选')"
          /></label>
          <label class="chk"
            ><input v-model="chargeChecked" type="checkbox" />
            {{ t('已核对客户授权签单人与挂账额度') }}</label
          >
        </div>
        <div class="modal-f">
          <button type="button" class="btn" @click="chargeOpen = false">{{ t('取消') }}</button>
          <button type="button" class="btn primary" @click="confirmCharge">
            {{ t('确认挂账') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 坏账模态 -->
    <div v-if="writeOffOpen" class="modal-mask" @click.self="writeOffOpen = false">
      <div class="modal">
        <div class="modal-h">
          <span>{{ t('坏账') }}核销（需审批）</span>
          <button type="button" class="close" @click="writeOffOpen = false">✕</button>
        </div>
        <div class="modal-b">
          <div class="li">
            <span>{{ t('客户') }}</span
            ><b>{{ curAr?.customer_name }}</b>
          </div>
          <div class="li">
            <span>{{ t('应收单据') }}</span
            ><b>{{ curAr?.doc_label }}</b>
          </div>
          <div class="li">
            <span>{{ t('核销金额') }}</span
            ><b class="text-red-600">{{ fmtYuan(curAr?.balance) }}</b>
          </div>
          <label class="field"
            >{{ t('核销原因')
            }}<textarea
              v-model="writeReason"
              rows="2"
              class="inp"
              :placeholder="t('如：长期失联 / 破产')"
            />
          </label>
          <label class="field"
            >{{ t('审批人（总经理）')
            }}<input v-model="writeApprover" class="inp" :placeholder="t('输入审批人姓名')"
          /></label>
          <p class="hint-red">
            {{ t('坏账') }}核销不可逆，核销后将不再计入应收余额，全额留存审计日志。
          </p>
          <label class="chk"
            ><input v-model="writeChecked" type="checkbox" />
            {{ t('我确认该笔已无法收回，且已获总经理审批') }}</label
          >
        </div>
        <div class="modal-f">
          <button type="button" class="btn" @click="writeOffOpen = false">{{ t('取消') }}</button>
          <button type="button" class="btn danger" @click="confirmWriteOff">
            {{ t('确认核销') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

<style scoped>
.arap-page {
  width: 100%;
  padding-bottom: 2rem;
}
.kpi-box {
  background: var(--md-sys-color-surface-container-lowest, #fff);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  padding: 14px 16px;
}
.kpi-box h3 {
  font-size: 13px;
  color: var(--md-sys-color-on-surface-variant, #666);
  font-weight: 600;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 7px;
}
.kpi-box.ar h3::before {
  content: '';
  width: 3px;
  height: 14px;
  background: #2f6fed;
  border-radius: 2px;
}
.kpi-box.ap h3::before {
  content: '';
  width: 3px;
  height: 14px;
  background: #7b5bd6;
  border-radius: 2px;
}
.kpi-cell {
  padding: 8px 10px;
  border-radius: 9px;
  background: #f5f7fb;
}
.kpi-cell .v {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.kpi-cell .l {
  font-size: 11px;
  color: #7a8699;
  margin-top: 2px;
}
.tab-btn {
  padding: 8px 15px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e7ebf2;
  font-size: 13.5px;
  color: #465061;
  cursor: pointer;
}
.tab-btn.on {
  background: #2f6fed;
  color: #fff;
  border-color: #2f6fed;
}
.card {
  background: #fff;
  border: 1px solid #e7ebf2;
  border-radius: 12px;
  margin-bottom: 16px;
  overflow: hidden;
}
.card-h {
  padding: 13px 16px;
  border-bottom: 1px solid #e7ebf2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.card-h b {
  font-size: 14px;
}
.card-h .sub {
  font-size: 12px;
  color: #7a8699;
}
.card-b {
  padding: 14px 16px;
}
.credit-card {
  background: #f5f7fb;
  border: 1px solid #e7ebf2;
  border-radius: 10px;
  padding: 12px;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th,
.data-table td {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid #e7ebf2;
  white-space: nowrap;
}
.data-table th {
  font-size: 11.5px;
  color: #7a8699;
  font-weight: 600;
  background: #f5f7fb;
}
.data-table td.num,
.data-table th.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.data-table td.calc-cell {
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  max-width: 280px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-variant-numeric: tabular-nums;
}
.data-table tbody tr:hover {
  background: #fafcff;
}
.badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 20px;
  font-size: 11.5px;
  font-weight: 600;
}
.badge.wait {
  background: #fdf3e2;
  color: #d98a00;
}
.badge.part {
  background: #eaf1fe;
  color: #2f6fed;
}
.badge.done {
  background: #e6f7f0;
  color: #1f9d6b;
}
.badge.ovr {
  background: #fdecea;
  color: #d6453d;
}
.badge.pend {
  background: #f1ecfd;
  color: #7b5bd6;
}
.pill {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 7px;
  border-radius: 6px;
  font-size: 11px;
  background: #eaf1fe;
  color: #2f6fed;
}
.pill.pre {
  background: #f5f7fb;
  color: #7a8699;
}
.filter-chip {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  border: 1px solid #e7ebf2;
  background: #fff;
  cursor: pointer;
}
.filter-chip.on {
  background: #eaf1fe;
  border-color: #2f6fed;
  color: #2f6fed;
}
.btn-sm {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  border: 1px solid #e7ebf2;
  background: #fff;
  cursor: pointer;
}
.btn-sm.primary {
  background: #2f6fed;
  color: #fff;
  border-color: #2f6fed;
}
.btn-sm.danger {
  background: #d6453d;
  color: #fff;
  border-color: #d6453d;
}
.age-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.age-cell {
  padding: 12px;
  border-radius: 10px;
  background: #f5f7fb;
  text-align: center;
}
.age-cell.hot {
  background: #fdecea;
}
.age-cell .v {
  font-size: 18px;
  font-weight: 700;
}
.age-cell .l {
  font-size: 12px;
  color: #7a8699;
  margin-top: 4px;
}
.hint-amber {
  padding: 10px 14px;
  border-radius: 8px;
  background: #fdf3e2;
  color: #8a5a00;
}
.foot-note {
  font-size: 12px;
  color: #7a8699;
  line-height: 1.6;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 27, 51, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 16px;
}
.modal {
  background: #fff;
  border-radius: 12px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}
.modal-h {
  padding: 14px 16px;
  border-bottom: 1px solid #e7ebf2;
  display: flex;
  justify-content: space-between;
  font-weight: 600;
}
.modal-b {
  padding: 14px 16px;
}
.modal-f {
  padding: 12px 16px;
  border-top: 1px solid #e7ebf2;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.li {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 8px;
}
.li span {
  color: #7a8699;
}
.field {
  display: block;
  margin-top: 10px;
  font-size: 13px;
}
.inp {
  display: block;
  width: 100%;
  margin-top: 5px;
  padding: 8px 10px;
  border: 1px solid #e7ebf2;
  border-radius: 8px;
  font-size: 13px;
}
.hint-blue {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #eaf1fe;
  color: #1f55c7;
  font-size: 12px;
}
.hint-red {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fdecea;
  color: #d6453d;
  font-size: 12px;
}
.chk {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 12px;
  font-size: 13px;
  cursor: pointer;
}
.btn {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid #e7ebf2;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.btn.primary {
  background: #2f6fed;
  color: #fff;
  border-color: #2f6fed;
}
.btn.danger {
  background: #d6453d;
  color: #fff;
  border-color: #d6453d;
}
.close {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  color: #7a8699;
}
.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #1a2330;
  color: #fff;
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 13px;
  z-index: 200;
}
.todo-card .todo-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 11px;
  background: #fdecea;
  color: #d6453d;
  font-size: 12px;
  font-weight: 700;
}
.todo-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 0 !important;
}
.todo-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid #e7ebf2;
  border-radius: 10px;
  background: #fafcff;
}
.todo-row.high {
  border-color: #f5c6c2;
  background: #fffbfb;
}
.todo-title {
  font-weight: 600;
  font-size: 13.5px;
  margin-top: 6px;
}
.todo-detail {
  font-size: 12px;
  color: #7a8699;
  margin-top: 4px;
  line-height: 1.5;
}
.todo-tags {
  display: flex;
  align-items: center;
  gap: 6px;
}
.todo-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
</style>
