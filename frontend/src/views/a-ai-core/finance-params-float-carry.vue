<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 系统设置 · 财务参数
 * 门店备用金 / 税率与账期 / 收单费率 / OTA佣金 / 信用与账龄
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SystemConfigNav from '../../components/SystemConfigNav.vue'
import OtaCommission from './ota-commission.vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

type TabKey = 'float' | 'tax' | 'acquiring' | 'ota' | 'credit'

const TABS = computed(
  () =>
    [
      { key: 'float', label: t('门店备用金') },
      { key: 'tax', label: t('税率与账期') },
      { key: 'acquiring', label: t('收单费率') },
      { key: 'ota', label: t('OTA佣金') },
      { key: 'credit', label: t('信用与账龄') },
    ] as const,
)

const EFFECTIVE_MODES = computed(() => [
  t('次月 1 日（推荐）'),
  t('次日 0 时'),
  t('指定日期'),
  t('立即生效'),
])
const TERM_LABEL_OPTS = computed(() => [
  t('即付 · 0 天'),
  t('现结 · 0 天'),
  'T+7',
  'T+10',
  'T+15',
  t('15 天'),
  t('30 天'),
  t('45 天'),
  t('60 天'),
])

const route = useRoute()
const router = useRouter()
const activeTab = ref<TabKey>('float')
const loading = ref(false)
const toast = ref('')

// ---------- 门店备用金 ----------
const ws = ref<any>(null)
const modalOpen = ref(false)
const newAmt = ref(2000)
const reasonSel = ref('')
const reasonText = ref('')
const showDenom = ref(false)
const reviewPassword = ref('')
const reviewModalOpen = ref(false)
const reviewAction = ref<'finance' | 'manager' | 'reject' | null>(null)

const active = computed(() => ws.value?.active)
const pending = computed(() => ws.value?.pending)
const floatHistory = computed(() => ws.value?.history || [])
const denomPreview = computed(() => active.value?.denom_breakdown || [])
const previewDenom = computed(() => {
  const v = Number(newAmt.value) || 0
  const ratios = ws.value?.default_ratios || []
  return ratios.map((r: any) => ({
    label: t(String(r.label || r.denom)),
    qty: r.denom > 0 ? Math.round((v * Number(r.ratio || 0)) / Number(r.denom)) : 0,
  }))
})
const previewDiff = computed(() => (Number(newAmt.value) || 0) - Number(active.value?.amount || 0))
const floatWarn = computed(() => {
  const v = Number(newAmt.value) || 0
  if (v < 500) return t('备用金低于 ¥500 可能影响高峰找零，建议不低于 ¥1,000。')
  if (v > 5000) return t('备用金高于 ¥5,000 增加保管与交接风险，建议评估保险箱限额。')
  return ''
})

// ---------- 税率与账期 ----------
const taxWs = ref<any>(null)
const taxModalOpen = ref(false)
const taxForm = ref({
  taxpayer_type: '一般纳税人',
  main_rate_pct: 6,
  price_mode: '价外',
  effective_mode: '次月 1 日（推荐）',
  specified_date: '',
  reason: '',
})
const termModalOpen = ref(false)
const termTarget = ref<any>(null)
const termForm = ref({ term_label: '', effective_mode: '立即生效', reason: '' })
const taxConfig = computed(() => taxWs.value?.tax)
const taxTerms = computed(() => taxWs.value?.terms || [])
const taxHistory = computed(() => taxWs.value?.history || [])

// ---------- 收单费率 ----------
const acqWs = ref<any>(null)
const acqKpi = computed(() => acqWs.value?.kpi || {})
const acqChannels = computed(() => acqWs.value?.channels || [])
const acqHistory = computed(() => acqWs.value?.history || [])
const rateModalOpen = ref(false)
const rateTarget = ref<any>(null)
const rateForm = ref({ rate_pct: 0.6, effective_mode: '次月 1 日（推荐）', reason: '' })
const rateImpact = computed(() => {
  if (!rateTarget.value) return 0
  const old = Number(rateTarget.value.rate_pct) || 0
  const neu = Number(rateForm.value.rate_pct) || 0
  const gmv = Number(rateTarget.value.month_gmv) || 0
  return ((neu - old) / 100) * gmv
})

// ---------- 信用与账龄 ----------
const creditWs = ref<any>(null)
const creditKpi = computed(() => creditWs.value?.kpi || {})
const creditCustomers = computed(() => creditWs.value?.customers || [])
const agingBuckets = computed(() => creditWs.value?.aging_buckets || [])
const badDebtRates = computed(() => creditWs.value?.bad_debt_rates || [])
const creditHistory = computed(() => creditWs.value?.history || [])
const creditModalOpen = ref(false)
const creditTarget = ref<any>(null)
const creditForm = ref({ new_limit: 0, reason: '' })
const creditRemainPreview = computed(() => {
  if (!creditTarget.value) return 0
  return (Number(creditForm.value.new_limit) || 0) - (Number(creditTarget.value.credit_used) || 0)
})
const createCreditModalOpen = ref(false)
const createCreditForm = ref({
  name: '',
  customer_type: '企业挂账',
  grade: 'B',
  credit_limit: 20000,
  term_label: t('30 天'),
  reason: '',
})
const badDebtModalOpen = ref(false)
const badDebtTarget = ref<any>(null)
const badDebtForm = ref({ rate_pct: 0, reason: '' })

// ---------- 通用 ----------
const fmt = (n: number) =>
  Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtInt = (n: number) => Number(n || 0).toLocaleString('zh-CN')

function showToast(msg: string) {
  toast.value = msg
  setTimeout(() => {
    toast.value = ''
  }, 2400)
}

function parseTab(q: unknown): TabKey {
  const v = String(q || '')
  if (v === 'tax' || v === 'acquiring' || v === 'ota' || v === 'credit') return v
  return 'float'
}

function switchTab(tab: TabKey) {
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
  loadActiveTab()
}

async function loadFloat() {
  const res = await api.financeParamsFloatCarry(hotelStore.hotelId)
  ws.value = (res as any)?.data ?? res
  newAmt.value = ws.value?.active?.amount ?? 2000
}

async function loadTax() {
  const res = await api.financeParamsTax(hotelStore.hotelId)
  taxWs.value = (res as any)?.data ?? res
}

async function loadAcquiring() {
  const res = await api.financeParamsAcquiring(hotelStore.hotelId)
  acqWs.value = (res as any)?.data ?? res
}

async function loadCredit() {
  const res = await api.financeParamsCredit(hotelStore.hotelId)
  creditWs.value = (res as any)?.data ?? res
}

async function loadActiveTab() {
  if (activeTab.value === 'ota') {
    loading.value = false
    return
  }
  loading.value = true
  try {
    if (activeTab.value === 'float') await loadFloat()
    else if (activeTab.value === 'tax') await loadTax()
    else if (activeTab.value === 'acquiring') await loadAcquiring()
    else await loadCredit()
  } catch (e: any) {
    showToast(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

// ---------- 备用金操作 ----------
function openModal() {
  newAmt.value = active.value?.amount ?? 2000
  reasonSel.value = ''
  reasonText.value = ''
  reviewPassword.value = ''
  modalOpen.value = true
}

function openReview(action: 'finance' | 'manager' | 'reject') {
  reviewAction.value = action
  reviewPassword.value = ''
  reviewModalOpen.value = true
}

function getReason() {
  if (reasonSel.value === '__other') return reasonText.value.trim()
  return reasonSel.value
}

async function confirmReview() {
  if (!reviewPassword.value.trim()) {
    showToast(t('请输入登录密码完成身份复核'))
    return
  }
  if (!pending.value?.id || !reviewAction.value) return
  try {
    const pwd = { review_password: reviewPassword.value }
    if (reviewAction.value === 'finance') {
      await api.financeParamsFloatCarryApproveFinance(hotelStore.hotelId, pending.value.id, pwd)
      showToast(t('财务复核通过，等待店长审批'))
    } else if (reviewAction.value === 'manager') {
      await api.financeParamsFloatCarryApproveManager(hotelStore.hotelId, pending.value.id, pwd)
      showToast(t('双授权通过，新备用金底数已生效'))
    } else {
      await api.financeParamsFloatCarryReject(hotelStore.hotelId, pending.value.id, {
        reason: '审批驳回',
        ...pwd,
      })
      showToast(t('变更已驳回，底数保持不变'))
    }
    reviewModalOpen.value = false
    await loadFloat()
  } catch (e: any) {
    showToast(e?.message || '操作失败')
  }
}

async function submitChange() {
  const reason = getReason()
  if ((Number(newAmt.value) || 0) <= 0) {
    showToast(t('请填写有效本金金额'))
    return
  }
  if (!reason) {
    showToast(t('请填写变更原因'))
    return
  }
  if (!reviewPassword.value.trim()) {
    showToast(t('提交变更须输入登录密码完成身份复核'))
    return
  }
  try {
    await api.financeParamsFloatCarryRequest(hotelStore.hotelId, {
      amount: Number(newAmt.value),
      reason,
      review_password: reviewPassword.value,
    })
    modalOpen.value = false
    showToast(t('已提交，等待财务经理审批'))
    await loadFloat()
  } catch (e: any) {
    showToast(e?.message || '提交失败')
  }
}

// ---------- 税率操作 ----------
function openTaxModal() {
  const tc = taxConfig.value
  taxForm.value = {
    taxpayer_type: tc?.taxpayer_type || '一般纳税人',
    main_rate_pct: tc?.main_rate ?? 6,
    price_mode: tc?.price_mode || '价外',
    effective_mode: '次月 1 日（推荐）',
    specified_date: '',
    reason: '',
  }
  taxModalOpen.value = true
}

async function submitTaxUpdate() {
  if (!taxForm.value.reason.trim()) {
    showToast(t('请填写变更原因'))
    return
  }
  try {
    const payload: Record<string, unknown> = { ...taxForm.value }
    if (taxForm.value.effective_mode !== '指定日期') delete payload.specified_date
    await api.financeParamsTaxUpdate(hotelStore.hotelId, payload)
    taxModalOpen.value = false
    showToast(t('税率配置已更新'))
    await loadTax()
  } catch (e: any) {
    showToast(e?.message || '提交失败')
  }
}

function openTermModal(row: any) {
  termTarget.value = row
  termForm.value = { term_label: row.term_label, effective_mode: '立即生效', reason: '' }
  termModalOpen.value = true
}

async function submitTermUpdate() {
  if (!termForm.value.reason.trim()) {
    showToast(t('请填写变更原因'))
    return
  }
  if (!termTarget.value?.id) return
  try {
    await api.financeParamsTermUpdate(hotelStore.hotelId, termTarget.value.id, termForm.value)
    termModalOpen.value = false
    showToast(t('账期已调整'))
    await loadTax()
  } catch (e: any) {
    showToast(e?.message || '提交失败')
  }
}

// ---------- 收单操作 ----------
function openRateModal(ch: any) {
  rateTarget.value = ch
  rateForm.value = { rate_pct: ch.rate_pct ?? 0.6, effective_mode: '次月 1 日（推荐）', reason: '' }
  rateModalOpen.value = true
}

async function submitRateUpdate() {
  if (!rateForm.value.reason.trim()) {
    showToast(t('请填写变更原因'))
    return
  }
  if (!rateTarget.value?.id) return
  try {
    await api.financeParamsAcquiringRate(hotelStore.hotelId, rateTarget.value.id, rateForm.value)
    rateModalOpen.value = false
    showToast(t('费率已更新'))
    await loadAcquiring()
  } catch (e: any) {
    showToast(e?.message || '提交失败')
  }
}

async function toggleChannel(ch: any) {
  try {
    await api.financeParamsAcquiringToggle(hotelStore.hotelId, ch.id, !ch.enabled)
    showToast(ch.enabled ? t('渠道已下线') : t('渠道已上线'))
    await loadAcquiring()
  } catch (e: any) {
    showToast(e?.message || '操作失败')
  }
}

// ---------- 信用操作 ----------
function openCreditModal(c: any) {
  creditTarget.value = c
  creditForm.value = { new_limit: c.credit_limit, reason: '' }
  creditModalOpen.value = true
}

function openCreateCreditModal() {
  createCreditForm.value = {
    name: '',
    customer_type: '企业挂账',
    grade: 'B',
    credit_limit: 20000,
    term_label: t('30 天'),
    reason: '',
  }
  createCreditModalOpen.value = true
}

async function submitCreateCredit() {
  const f = createCreditForm.value
  if (!f.name.trim() || f.name.trim().length < 2) {
    showToast(t('请填写客户名称（不少于 2 字）'))
    return
  }
  if (!f.reason.trim() || f.reason.trim().length < 4) {
    showToast(t('请填写变更原因（不少于 4 字）'))
    return
  }
  try {
    await api.financeParamsCreditCreate(hotelStore.hotelId, { ...f })
    createCreditModalOpen.value = false
    showToast(t('授信客户已新增'))
    await loadCredit()
  } catch (e: any) {
    showToast(e?.message || '提交失败')
  }
}

async function submitCreditLimit() {
  if (!creditForm.value.reason.trim()) {
    showToast(t('请填写变更原因'))
    return
  }
  if (!creditTarget.value?.id) return
  try {
    await api.financeParamsCreditLimit(hotelStore.hotelId, creditTarget.value.id, creditForm.value)
    creditModalOpen.value = false
    showToast(t('信用额度已调整'))
    await loadCredit()
  } catch (e: any) {
    showToast(e?.message || '提交失败')
  }
}

function openBadDebtModal(r: any) {
  badDebtTarget.value = r
  badDebtForm.value = { rate_pct: r.rate_pct, reason: '' }
  badDebtModalOpen.value = true
}

async function submitBadDebt() {
  if (!badDebtForm.value.reason.trim()) {
    showToast(t('请填写变更原因'))
    return
  }
  if (!badDebtTarget.value?.id) return
  try {
    await api.financeParamsBadDebt(hotelStore.hotelId, badDebtTarget.value.id, badDebtForm.value)
    badDebtModalOpen.value = false
    showToast(t('坏账准备率已更新'))
    await loadCredit()
  } catch (e: any) {
    showToast(e?.message || '提交失败')
  }
}

// ---------- 样式辅助 ----------
function statusBadge(st: string) {
  if (st === 'active' || st === '已生效') return 'green'
  if (st === 'rejected' || st === '已驳回' || st === '已停用') return 'red'
  if (st?.startsWith('pending') || st === '审核中') return 'amber'
  return 'gray'
}

function statusLabel(row: any) {
  if (row.status === 'active') return t('已生效')
  if (row.status === 'rejected') return t('已驳回')
  if (row.status === 'superseded') return t('已归档')
  if (row.status === 'pending_finance') return t('待财务审批')
  if (row.status === 'pending_manager') return t('待店长审批')
  return row.status
}

function gradeBadge(g: string) {
  const u = (g || 'B').toUpperCase()
  if (u === 'A') return 'green'
  if (u === 'B') return 'blue'
  if (u === 'C') return 'amber'
  if (u === 'D') return 'red'
  return 'gray'
}

function usageTone(pct: number) {
  if (pct >= 90) return 'danger'
  if (pct >= 70) return 'warn'
  return 'ok'
}

function acqStatusBadge(st: string) {
  if (st === '上线') return 'green'
  if (st === '审核中') return 'amber'
  if (st === '低用量') return 'blue'
  return 'gray'
}

function agingTone(tone: string) {
  if (tone === 'ok') return 'ok'
  if (tone === 'bad') return 'bad'
  return 'warn'
}

onMounted(() => {
  activeTab.value = parseTab(route.query.tab)
  if (!route.query.tab) {
    router.replace({ query: { ...route.query, tab: activeTab.value } })
  }
  loadActiveTab()
})

watch(
  () => route.query.tab,
  (q) => {
    const tabKey = parseTab(q)
    if (tabKey !== activeTab.value) {
      activeTab.value = tabKey
      loadActiveTab()
    }
  },
)

watch(
  () => hotelStore.hotelId,
  () => loadActiveTab(),
)
</script>

<template>
  <div class="page">
    <SystemConfigNav />
    <div class="page-head">
      <div>
        <h1>{{ t('财务参数') }}</h1>
      </div>
    </div>

    <div class="tabs">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        type="button"
        class="tab"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="loading" class="hint">{{ t('加载中…') }}</div>

    <!-- ========== 门店备用金 ========== -->
    <template v-else-if="activeTab === 'float'">
      <div class="card">
        <div class="card-h">
          <h3>{{ t('当前生效配置') }}</h3>
          <span v-if="active" class="badge green">{{ t('生效中') }}</span>
          <span v-else class="badge amber">{{ t('未配置') }}</span>
        </div>
        <div v-if="active" class="grid2">
          <div>
            <div class="kv">
              <span class="k">{{ t('备用金本金') }}</span
              ><span class="v mono">¥ {{ fmt(active.amount) }}</span>
            </div>
            <div class="kv">
              <span class="k">{{ t('币种') }}</span
              ><span class="v">{{
                active.currency === 'CNY' ? t('人民币（CNY）') : active.currency
              }}</span>
            </div>
            <div class="kv">
              <span class="k">{{ t('面额配比') }}</span>
              <span class="v"
                ><button type="button" class="link" @click="showDenom = !showDenom">
                  {{ t('查看明细') }}
                </button></span
              >
            </div>
            <div class="kv">
              <span class="k">{{ t('生效日期') }}</span
              ><span class="v mono">{{ active.effective_date || '—' }}</span>
            </div>
          </div>
          <div>
            <div class="kv">
              <span class="k">{{ t('最近维护人') }}</span
              ><span class="v">{{ ws.maintainer_name || '—' }}</span>
            </div>
            <div class="kv">
              <span class="k">{{ t('维护时间') }}</span
              ><span class="v mono">{{ ws.maintainer_at || '—' }}</span>
            </div>
            <div class="kv">
              <span class="k">{{ t('变更频次') }}}</span
              ><span class="v"
                >{{ t('低频 · 累计') }} {{ ws.change_count_8m || 0 }} {{ t('次变更') }}</span
              >
            </div>
            <div class="kv">
              <span class="k">{{ t('关联页面') }}</span
              ><span class="v">{{ t('交班管理 · 备用金盘库') }}</span>
            </div>
          </div>
        </div>
        <div v-else class="hint">{{ t('尚未配置备用金底数，请初始化或提交变更申请。') }}</div>
        <div v-if="showDenom && active" class="denom">
          <div v-for="d in denomPreview" :key="d.denom" class="d">
            <span>{{ t(String(d.label || d.denom)) }}</span
            ><b>× {{ d.expected_qty }}</b>
          </div>
        </div>
        <div class="btn-row">
          <button type="button" class="btn primary" @click="openModal">
            {{ t('修改备用金底数') }}
          </button>
        </div>
      </div>

      <div v-if="pending" class="card">
        <div class="card-h">
          <h3>{{ t('在途审批') }}</h3>
          <span class="badge amber">{{ t('审批中') }}</span>
        </div>
        <div class="preview">
          <div class="row">
            <span>{{ t('申请变更') }}</span>
            <b class="mono">
              ¥ {{ fmt(pending.old_amount ?? active?.amount ?? 0) }}
              <span class="arrow">→</span>
              ¥ {{ fmt(pending.amount) }}</b
            >
          </div>
          <div class="row">
            <span>{{ t('原因') }}</span
            ><b>{{ pending.change_reason }}</b>
          </div>
          <div class="row">
            <span>{{ t('申请人') }}</span
            ><b>{{ pending.applicant_name || '—' }} · {{ pending.created_at }}</b>
          </div>
        </div>
        <div class="approve-flow">
          <div class="flow-step" :class="pending.status === 'pending_finance' ? 'cur' : 'done'">
            <div class="num">{{ pending.status === 'pending_finance' ? '1' : '✓' }}</div>
            <div class="meta">
              <div class="t">{{ t('财务经理审批') }}</div>
              <div class="s">
                {{
                  pending.status === 'pending_finance'
                    ? t('待财务经理批准')
                    : `${pending.finance_approver_name || t('财务经理')}${t(' 已批准')}`
                }}
              </div>
            </div>
          </div>
          <div
            class="flow-step"
            :class="
              pending.status === 'pending_manager'
                ? 'cur'
                : pending.finance_approved_at
                  ? 'done'
                  : 'wait'
            "
          >
            <div class="num">
              {{
                pending.status === 'pending_manager' ? '2' : pending.finance_approved_at ? '✓' : '2'
              }}
            </div>
            <div class="meta">
              <div class="t">{{ t('店长审批') }}</div>
              <div class="s">
                {{
                  pending.status === 'pending_manager' ? t('待店长批准') : t('财务经理通过后触发')
                }}
              </div>
            </div>
          </div>
        </div>
        <div class="btn-row">
          <button
            v-if="pending.status === 'pending_finance'"
            type="button"
            class="btn green sm"
            @click="openReview('finance')"
          >
            {{ t('财务经理批准') }}
          </button>
          <button
            v-if="pending.status === 'pending_manager'"
            type="button"
            class="btn green sm"
            @click="openReview('manager')"
          >
            {{ t('店长批准') }}
          </button>
          <button type="button" class="btn sm" @click="openReview('reject')">
            {{ t('驳回') }}
          </button>
        </div>
      </div>

      <div class="card">
        <div class="card-h">
          <h3>{{ t('变更历史') }}</h3>
        </div>
        <table class="tbl">
          <thead>
            <tr>
              <th>{{ t('时间') }}</th>
              <th>{{ t('变更') }}</th>
              <th>{{ t('原因') }}</th>
              <th>{{ t('申请人') }}</th>
              <th>{{ t('审批') }}</th>
              <th>{{ t('状态') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!floatHistory.length">
              <td colspan="6" class="ctr muted">{{ t('暂无变更记录') }}</td>
            </tr>
            <tr v-for="h in floatHistory" :key="h.id">
              <td class="mono muted">{{ h.activated_at || h.created_at }}</td>
              <td class="mono">
                {{ h.old_amount != null ? `¥ ${fmt(h.old_amount)}` : '—' }}
                <span class="arrow">→</span> ¥ {{ fmt(h.amount) }}
              </td>
              <td>{{ h.change_reason }}</td>
              <td>{{ h.applicant_name || '—' }}</td>
              <td>{{ h.approver_names }}</td>
              <td>
                <span class="badge" :class="statusBadge(h.status)">{{ statusLabel(h) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- ========== 税率与账期 ========== -->
    <template v-else-if="activeTab === 'tax'">
      <div class="card">
        <div class="card-h">
          <h3>{{ t('税率配置') }}</h3>
          <span v-if="taxConfig" class="badge green">v{{ taxConfig.version }}</span>
        </div>
        <div v-if="taxConfig" class="grid2">
          <div>
            <div class="kv">
              <span class="k">{{ t('纳税人类型') }}</span
              ><span class="v">{{
                taxConfig.taxpayer_type ? t(taxConfig.taxpayer_type) : '—'
              }}</span>
            </div>
            <div class="kv">
              <span class="k">{{ t('主营税率') }}</span
              ><span class="v mono">{{ taxConfig.main_rate }}%</span>
            </div>
            <div class="kv">
              <span class="k">{{ t('计价方式') }}</span
              ><span class="v">{{ taxConfig.price_mode ? t(taxConfig.price_mode) : '—' }}</span>
            </div>
            <div class="kv">
              <span class="k">{{ t('税收编码') }}</span
              ><span class="v mono sm">{{ taxConfig.tax_code }}</span>
            </div>
          </div>
          <div>
            <div class="kv">
              <span class="k">{{ t('税号') }}</span
              ><span class="v mono">{{ taxConfig.tax_no || '—' }}</span>
            </div>
            <div class="kv">
              <span class="k">{{ t('附加税说明') }}</span
              ><span class="v">{{
                taxConfig.surcharge_note ? t(taxConfig.surcharge_note) : '—'
              }}</span>
            </div>
            <div class="kv">
              <span class="k">{{ t('生效日期') }}</span
              ><span class="v mono">{{ taxConfig.effective_date || '—' }}</span>
            </div>
            <div class="kv">
              <span class="k">{{ t('维护人') }}</span
              ><span class="v">{{
                taxConfig.maintainer_name ? t(taxConfig.maintainer_name) : '—'
              }}</span>
            </div>
          </div>
        </div>
        <div class="btn-row">
          <button type="button" class="btn primary" @click="openTaxModal">
            {{ t('修改税率配置') }}
          </button>
        </div>
      </div>

      <div class="card">
        <div class="card-h">
          <h3>{{ t('客户账期（8 类）') }}</h3>
        </div>
        <table class="tbl">
          <thead>
            <tr>
              <th>{{ t('客户类型') }}</th>
              <th>{{ t('账期') }}</th>
              <th>{{ t('说明') }}</th>
              <th>{{ t('生效日期') }}</th>
              <th>{{ t('操作') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="term in taxTerms" :key="term.id">
              <td>{{ term.customer_type }}</td>
              <td class="mono">
                <b>{{ term.term_label }}</b>
              </td>
              <td class="muted">{{ term.description }}</td>
              <td class="mono muted">{{ term.effective_date || '—' }}</td>
              <td>
                <button type="button" class="link" @click="openTermModal(term)">
                  {{ t('调整') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <div class="card-h">
          <h3>{{ t('变更历史') }}</h3>
        </div>
        <table class="tbl">
          <thead>
            <tr>
              <th>{{ t('时间') }}</th>
              <th>{{ t('类型') }}</th>
              <th>{{ t('变更') }}</th>
              <th>{{ t('生效日') }}</th>
              <th>{{ t('操作人') }}</th>
              <th>{{ t('状态') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!taxHistory.length">
              <td colspan="6" class="ctr muted">{{ t('暂无记录') }}</td>
            </tr>
            <tr v-for="h in taxHistory" :key="h.id">
              <td class="mono muted">{{ h.time }}</td>
              <td>{{ h.type }}</td>
              <td>{{ h.change }}</td>
              <td class="mono">{{ h.effective_date || '—' }}</td>
              <td>{{ h.who }}</td>
              <td>
                <span class="badge" :class="statusBadge(h.status)">{{ h.status }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- ========== 收单费率 ========== -->
    <template v-else-if="activeTab === 'acquiring'">
      <div class="kpi-row">
        <div class="kpi">
          <div class="kl">{{ t('上线渠道') }}</div>
          <div class="kv2">{{ acqKpi.active_channels ?? 0 }}</div>
        </div>
        <div class="kpi">
          <div class="kl">{{ t('加权费率') }}</div>
          <div class="kv2">{{ acqKpi.weighted_rate ?? 0 }}%</div>
        </div>
        <div class="kpi">
          <div class="kl">{{ t('月手续费') }}</div>
          <div class="kv2 mono">¥ {{ fmt(acqKpi.month_fee ?? 0) }}</div>
        </div>
        <div class="kpi">
          <div class="kl">{{ t('T+1 达标') }}</div>
          <div class="kv2">{{ acqKpi.t1_ok ?? '—' }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-h">
          <h3>{{ t('收单渠道') }}</h3>
        </div>
        <table class="tbl">
          <thead>
            <tr>
              <th>{{ t('渠道') }}</th>
              <th>{{ t('费率') }}</th>
              <th>{{ t('结算') }}</th>
              <th>{{ t('最低结算') }}</th>
              <th>{{ t('提现费') }}</th>
              <th>{{ t('月手续费') }}</th>
              <th>{{ t('状态') }}</th>
              <th>{{ t('开关') }}</th>
              <th>{{ t('操作') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ch in acqChannels" :key="ch.id">
              <td>
                <b>{{ ch.name }}</b>
                <div class="muted sm">{{ ch.code }}</div>
              </td>
              <td class="mono">{{ ch.rate_display }}</td>
              <td>{{ ch.settle_label }}</td>
              <td class="mono">{{ ch.min_settle != null ? `¥ ${fmt(ch.min_settle)}` : '—' }}</td>
              <td class="mono">
                {{ ch.withdraw_fee_pct != null ? `${ch.withdraw_fee_pct}%` : '—' }}
              </td>
              <td class="mono">¥ {{ fmt(ch.month_fee) }}</td>
              <td>
                <span class="badge" :class="acqStatusBadge(ch.status_label)">{{
                  ch.status_label
                }}</span>
              </td>
              <td>
                <label class="switch">
                  <input type="checkbox" :checked="ch.enabled" @change="toggleChannel(ch)" />
                  <span class="slider" />
                </label>
              </td>
              <td>
                <button type="button" class="link" @click="openRateModal(ch)">
                  {{ t('改费率') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <div class="card-h">
          <h3>{{ t('变更历史') }}</h3>
        </div>
        <table class="tbl">
          <thead>
            <tr>
              <th>{{ t('时间') }}</th>
              <th>{{ t('渠道') }}</th>
              <th>{{ t('动作') }}</th>
              <th>{{ t('变更') }}</th>
              <th>{{ t('原因') }}</th>
              <th>{{ t('操作人') }}</th>
              <th>{{ t('状态') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!acqHistory.length">
              <td colspan="7" class="ctr muted">{{ t('暂无记录') }}</td>
            </tr>
            <tr v-for="h in acqHistory" :key="h.id">
              <td class="mono muted">{{ h.time }}</td>
              <td>{{ h.channel }}</td>
              <td>{{ h.action }}</td>
              <td>{{ h.change }}</td>
              <td>{{ h.reason }}</td>
              <td>{{ h.who }}</td>
              <td>
                <span class="badge" :class="statusBadge(h.status)">{{ h.status }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- ========== OTA佣金 ========== -->
    <template v-else-if="activeTab === 'ota'">
      <OtaCommission embedded />
    </template>

    <!-- ========== 信用与账龄 ========== -->
    <template v-else-if="activeTab === 'credit'">
      <div class="kpi-row">
        <div class="kpi">
          <div class="kl">{{ t('授信客户') }}</div>
          <div class="kv2">{{ creditKpi.customer_count ?? 0 }}</div>
        </div>
        <div class="kpi">
          <div class="kl">{{ t('等级分布') }}</div>
          <div class="kv2 sm">{{ creditKpi.grade_breakdown || '—' }}</div>
        </div>
        <div class="kpi">
          <div class="kl">{{ t('总额度 / 剩余') }}</div>
          <div class="kv2 mono sm">
            ¥ {{ fmtInt(creditKpi.total_limit) }} / ¥ {{ fmtInt(creditKpi.remain) }}
          </div>
        </div>
        <div class="kpi">
          <div class="kl">{{ t('90+ 逾期（占应收）') }}</div>
          <div class="kv2">
            {{ creditKpi.overdue_90_pct ?? 0 }}% · ¥ {{ fmtInt(creditKpi.overdue_90_amt) }}
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-h">
          <h3>{{ t('授信客户') }}</h3>
        </div>
        <table class="tbl">
          <thead>
            <tr>
              <th>{{ t('客户') }}</th>
              <th>{{ t('等级') }}</th>
              <th>{{ t('额度') }}</th>
              <th>{{ t('已用') }}</th>
              <th>{{ t('使用率') }}</th>
              <th>{{ t('账期') }}</th>
              <th>{{ t('状态') }}</th>
              <th>{{ t('操作') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in creditCustomers" :key="c.id">
              <td>
                <b>{{ c.name }}</b>
                <div class="muted sm">{{ c.customer_type }}</div>
              </td>
              <td>
                <span class="badge" :class="gradeBadge(c.grade)">{{ c.grade }}</span>
              </td>
              <td class="mono">¥ {{ fmtInt(c.credit_limit) }}</td>
              <td class="mono">¥ {{ fmtInt(c.credit_used) }}</td>
              <td>
                <div class="usage-wrap">
                  <div class="usage-bar">
                    <div
                      class="usage-fill"
                      :class="usageTone(c.usage_pct)"
                      :style="{ width: Math.min(c.usage_pct, 100) + '%' }"
                    />
                  </div>
                  <span class="mono sm">{{ c.usage_pct }}%</span>
                </div>
              </td>
              <td>{{ c.term_label }}</td>
              <td>
                <span class="badge" :class="statusBadge(c.status_label)">{{ c.status_label }}</span>
              </td>
              <td>
                <button
                  type="button"
                  class="link"
                  :disabled="!c.enabled && c.credit_limit <= 0"
                  @click="openCreditModal(c)"
                >
                  {{ t('调额度') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="btn-row">
          <button type="button" class="btn" @click="openCreateCreditModal">
            {{ t('+ 新增授信客户') }}
          </button>
          <span class="muted note-inline">{{
            t('新增客户请先完成准入；此处维护已准入客户的额度')
          }}</span>
        </div>
      </div>

      <div class="card">
        <div class="card-h">
          <h3>{{ t('账龄分桶') }}</h3>
        </div>
        <div class="age-grid">
          <div v-for="b in agingBuckets" :key="b.key" class="age-cell" :class="agingTone(b.tone)">
            <div class="age-label">{{ b.label ? t(b.label) : '' }}</div>
            <div class="age-hint">{{ b.hint }}</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-h">
          <h3>{{ t('坏账准备率') }}</h3>
        </div>
        <table class="tbl">
          <thead>
            <tr>
              <th>{{ t('账龄段') }}</th>
              <th>{{ t('计提率') }}</th>
              <th>{{ t('说明') }}</th>
              <th>{{ t('操作') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in badDebtRates" :key="r.id">
              <td>{{ r.bucket_label }}</td>
              <td class="mono">
                <b>{{ r.rate_pct }}%</b>
              </td>
              <td class="muted">{{ r.description }}</td>
              <td>
                <button type="button" class="link" @click="openBadDebtModal(r)">
                  {{ t('调整') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <div class="card-h">
          <h3>{{ t('变更历史') }}</h3>
        </div>
        <table class="tbl">
          <thead>
            <tr>
              <th>{{ t('时间') }}</th>
              <th>{{ t('类型') }}</th>
              <th>{{ t('对象') }}</th>
              <th>{{ t('变更') }}</th>
              <th>{{ t('原因') }}</th>
              <th>{{ t('审批链') }}</th>
              <th>{{ t('状态') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!creditHistory.length">
              <td colspan="7" class="ctr muted">{{ t('暂无记录') }}</td>
            </tr>
            <tr v-for="h in creditHistory" :key="h.id">
              <td class="mono muted">{{ h.time }}</td>
              <td>{{ h.type }}</td>
              <td>{{ h.target }}</td>
              <td>{{ h.change }}</td>
              <td>{{ h.reason }}</td>
              <td class="sm">{{ h.who }}</td>
              <td>
                <span class="badge" :class="statusBadge(h.status)">{{ h.status }}</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="warn">
          {{
            t(
              '说明：调额授权链为「销售提 → 财务批 → 总经理备案」（视额度级别）。坏账核销必须总经理审批且不可逆，与本页调额是不同动作。',
            )
          }}
        </div>
      </div>
    </template>

    <!-- ========== 模态框 ========== -->
    <!-- 备用金修改 -->
    <div v-if="modalOpen" class="modal-mask" @click.self="modalOpen = false">
      <div class="modal">
        <h3>{{ t('修改门店备用金底数') }}</h3>
        <div class="msub">
          {{ t('当前生效：') }}<span class="mono">¥ {{ fmt(active?.amount || 0) }}</span>
          {{ t('· 修改需双授权后生效') }}
        </div>
        <div class="field">
          <label>{{ t('新备用金本金（元）') }}</label>
          <input v-model.number="newAmt" class="inp mono" type="number" min="0" step="100" />
        </div>
        <div class="field">
          <label>{{ t('变更原因（必填）') }}</label>
          <select v-model="reasonSel" class="inp">
            <option value="">{{ t('请选择') }}</option>
            <option>{{ t('节假日临时增配（春节 / 国庆客流高峰）') }}</option>
            <option>{{ t('门店升级 / 客流增长，长期上调') }}</option>
            <option>{{ t('多年后通胀或管理标准调整') }}</option>
            <option>{{ t('盘点发现长期不符，重新核定基数') }}</option>
            <option value="__other">{{ t('其他（请填写）') }}</option>
          </select>
          <input
            v-if="reasonSel === '__other'"
            v-model="reasonText"
            class="inp mt"
            :placeholder="t('请说明具体原因')"
          />
        </div>
        <div class="preview">
          <div class="row">
            <span>{{ t('旧本金') }}</span
            ><b>¥ {{ fmt(active?.amount || 0) }}</b>
          </div>
          <div class="row">
            <span>{{ t('新本金') }}</span
            ><b class="primary">¥ {{ fmt(newAmt) }}</b>
          </div>
          <div class="row">
            <span>{{ t('变动') }}</span>
            <b :class="previewDiff > 0 ? 'up' : previewDiff < 0 ? 'dn' : ''">
              {{ previewDiff >= 0 ? '+' : '' }}¥ {{ fmt(Math.abs(previewDiff)) }}</b
            >
          </div>
          <div class="row">
            <span>{{ t('建议面额配比') }}</span>
            <b class="sm">{{
              previewDenom
                .map((d) => `${String(d.label || '').replace(/\s*元\s*/g, '')}×${d.qty}`)
                .join(' / ')
            }}</b>
          </div>
        </div>
        <div v-if="floatWarn" class="warn">{{ floatWarn }}</div>
        <div class="field">
          <label>{{ t('身份复核（登录密码）') }}</label>
          <input
            v-model="reviewPassword"
            class="inp"
            type="password"
            :placeholder="t('请输入当前账号登录密码')"
          />
        </div>
        <div class="btn-row">
          <button type="button" class="btn primary" @click="submitChange">
            {{ t('提交审批') }}
          </button>
          <button type="button" class="btn ghost" @click="modalOpen = false">
            {{ t('取消') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 备用金复核 -->
    <div v-if="reviewModalOpen" class="modal-mask" @click.self="reviewModalOpen = false">
      <div class="modal">
        <h3>{{ t('身份复核') }}</h3>
        <div class="msub">{{ t('资金类参数变更须二次校验登录密码（§4.7 复核制度）') }}</div>
        <div class="field">
          <label>{{ t('登录密码') }}</label>
          <input
            v-model="reviewPassword"
            class="inp"
            type="password"
            :placeholder="t('请输入登录密码')"
            @keyup.enter="confirmReview"
          />
        </div>
        <div class="btn-row">
          <button type="button" class="btn primary" @click="confirmReview">
            {{ t('确认复核') }}
          </button>
          <button type="button" class="btn ghost" @click="reviewModalOpen = false">
            {{ t('取消') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 税率修改 -->
    <div v-if="taxModalOpen" class="modal-mask" @click.self="taxModalOpen = false">
      <div class="modal">
        <h3>{{ t('修改税率配置') }}</h3>
        <div class="msub">当前 v{{ taxConfig?.version }} · {{ taxConfig?.main_rate }}%</div>
        <div class="field">
          <label>{{ t('纳税人类型') }}</label>
          <select v-model="taxForm.taxpayer_type" class="inp">
            <option>{{ t('一般纳税人') }}</option>
            <option>{{ t('小规模纳税人') }}</option>
          </select>
        </div>
        <div class="field">
          <label>{{ t('主营税率（%）') }}</label>
          <select v-model.number="taxForm.main_rate_pct" class="inp">
            <option :value="6">{{ t('6%（一般纳税人住宿服务）') }}</option>
            <option :value="3">{{ t('3%（小规模）') }}</option>
            <option :value="1">{{ t('1%（减按征收）') }}</option>
          </select>
        </div>
        <div class="field">
          <label>{{ t('计价方式') }}</label>
          <select v-model="taxForm.price_mode" class="inp">
            <option>{{ t('价外') }}</option>
            <option>{{ t('价内') }}</option>
          </select>
        </div>
        <div class="field">
          <label>{{ t('生效方式') }}</label>
          <select v-model="taxForm.effective_mode" class="inp">
            <option v-for="m in EFFECTIVE_MODES" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
        <div v-if="taxForm.effective_mode === '指定日期'" class="field">
          <label>{{ t('指定生效日') }}</label>
          <input v-model="taxForm.specified_date" class="inp" type="date" />
        </div>
        <div class="field">
          <label>{{ t('变更原因（必填）') }}</label>
          <input v-model="taxForm.reason" class="inp" :placeholder="t('不少于 4 字')" />
        </div>
        <div class="warn">{{ t('税率变更不可追溯已开票/已入账期间，仅对未来交易生效。') }}</div>
        <div class="btn-row">
          <button type="button" class="btn primary" @click="submitTaxUpdate">
            {{ t('提交') }}
          </button>
          <button type="button" class="btn ghost" @click="taxModalOpen = false">
            {{ t('取消') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 账期调整 -->
    <div v-if="termModalOpen" class="modal-mask" @click.self="termModalOpen = false">
      <div class="modal">
        <h3>调整账期 · {{ termTarget?.customer_type }}</h3>
        <div class="msub">当前：{{ termTarget?.term_label }}</div>
        <div class="field">
          <label>{{ t('新账期') }}</label>
          <select v-model="termForm.term_label" class="inp">
            <option v-for="o in TERM_LABEL_OPTS" :key="o" :value="o">{{ o }}</option>
          </select>
        </div>
        <div class="field">
          <label>{{ t('生效方式') }}</label>
          <select v-model="termForm.effective_mode" class="inp">
            <option v-for="m in EFFECTIVE_MODES" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
        <div class="field">
          <label>{{ t('变更原因（必填）') }}</label>
          <input v-model="termForm.reason" class="inp" :placeholder="t('不少于 4 字')" />
        </div>
        <div class="btn-row">
          <button type="button" class="btn primary" @click="submitTermUpdate">
            {{ t('提交') }}
          </button>
          <button type="button" class="btn ghost" @click="termModalOpen = false">
            {{ t('取消') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 收单费率 -->
    <div v-if="rateModalOpen" class="modal-mask" @click.self="rateModalOpen = false">
      <div class="modal">
        <h3>改费率 · {{ rateTarget?.name }}</h3>
        <div class="msub">
          当前 {{ rateTarget?.rate_pct != null ? `${rateTarget.rate_pct}%` : '—' }} · 月 GMV ¥
          {{ fmt(rateTarget?.month_gmv ?? 0) }}
        </div>
        <div class="field">
          <label>{{ t('新费率（%）') }}</label>
          <input
            v-model.number="rateForm.rate_pct"
            class="inp mono"
            type="number"
            min="0"
            max="10"
            step="0.01"
          />
        </div>
        <div class="field">
          <label>{{ t('生效方式') }}</label>
          <select v-model="rateForm.effective_mode" class="inp">
            <option v-for="m in EFFECTIVE_MODES" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
        <div class="field">
          <label>{{ t('变更原因（必填）') }}</label>
          <input v-model="rateForm.reason" class="inp" :placeholder="t('不少于 4 字')" />
        </div>
        <div class="preview">
          <div class="row">
            <span>{{ t('预计月影响') }}</span>
            <b :class="rateImpact >= 0 ? 'dn' : 'up'"
              >{{ rateImpact >= 0 ? '+' : '' }}¥ {{ fmt(Math.abs(rateImpact)) }}</b
            >
          </div>
        </div>
        <div class="btn-row">
          <button type="button" class="btn primary" @click="submitRateUpdate">
            {{ t('提交') }}
          </button>
          <button type="button" class="btn ghost" @click="rateModalOpen = false">
            {{ t('取消') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 新增授信客户 -->
    <div
      v-if="createCreditModalOpen"
      class="modal-mask"
      @click.self="createCreditModalOpen = false"
    >
      <div class="modal">
        <h3>{{ t('新增授信客户') }}</h3>
        <div class="msub">
          {{ t('本页维护已准入客户额度 · 授权链：销售提 → 财务批 → 总经理备案') }}
        </div>
        <div class="field">
          <label>{{ t('客户名称（必填）') }}</label>
          <input
            v-model="createCreditForm.name"
            class="inp"
            :placeholder="t('如：某某旅行社 / 某某科技')"
          />
        </div>
        <div class="field">
          <label>{{ t('客户类型') }}</label>
          <select v-model="createCreditForm.customer_type" class="inp">
            <option>{{ t('企业挂账') }}</option>
            <option>{{ t('旅行社') }}</option>
            <option>OTA</option>
          </select>
        </div>
        <div class="field">
          <label>{{ t('信用等级') }}</label>
          <select v-model="createCreditForm.grade" class="inp">
            <option>A</option>
            <option>B</option>
            <option>C</option>
            <option>D</option>
          </select>
        </div>
        <div class="field">
          <label>{{ t('授信额度（元）') }}</label>
          <input
            v-model.number="createCreditForm.credit_limit"
            class="inp mono"
            type="number"
            min="0"
            step="1000"
          />
        </div>
        <div class="field">
          <label>{{ t('账期') }}</label>
          <select v-model="createCreditForm.term_label" class="inp">
            <option v-for="opt in TERM_LABEL_OPTS" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </div>
        <div class="field">
          <label>{{ t('变更原因（必填）') }}</label>
          <input
            v-model="createCreditForm.reason"
            class="inp"
            :placeholder="t('如：新增协议客户')"
          />
        </div>
        <div class="btn-row">
          <button type="button" class="btn primary" @click="submitCreateCredit">
            {{ t('提交新增') }}
          </button>
          <button type="button" class="btn ghost" @click="createCreditModalOpen = false">
            {{ t('取消') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 信用额度 -->
    <div v-if="creditModalOpen" class="modal-mask" @click.self="creditModalOpen = false">
      <div class="modal">
        <h3>调额度 · {{ creditTarget?.name }}</h3>
        <div class="msub">
          当前 ¥ {{ fmtInt(creditTarget?.credit_limit ?? 0) }} · 已用 ¥
          {{ fmtInt(creditTarget?.credit_used ?? 0) }}
        </div>
        <div class="field">
          <label>{{ t('新额度（元）') }}</label>
          <input
            v-model.number="creditForm.new_limit"
            class="inp mono"
            type="number"
            min="0"
            step="1000"
          />
        </div>
        <div class="field">
          <label>{{ t('变更原因（必填）') }}</label>
          <input v-model="creditForm.reason" class="inp" :placeholder="t('不少于 4 字')" />
        </div>
        <div class="preview">
          <div class="row">
            <span>{{ t('预计剩余额度') }}</span
            ><b class="mono">¥ {{ fmtInt(creditRemainPreview) }}</b>
          </div>
        </div>
        <div class="btn-row">
          <button type="button" class="btn primary" @click="submitCreditLimit">
            {{ t('提交') }}
          </button>
          <button type="button" class="btn ghost" @click="creditModalOpen = false">
            {{ t('取消') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 坏账准备率 -->
    <div v-if="badDebtModalOpen" class="modal-mask" @click.self="badDebtModalOpen = false">
      <div class="modal">
        <h3>调整坏账准备率 · {{ badDebtTarget?.bucket_label }}</h3>
        <div class="msub">当前 {{ badDebtTarget?.rate_pct }}%</div>
        <div class="field">
          <label>{{ t('新计提率（%）') }}</label>
          <input
            v-model.number="badDebtForm.rate_pct"
            class="inp mono"
            type="number"
            min="0"
            max="100"
            step="1"
          />
        </div>
        <div class="field">
          <label>{{ t('变更原因（必填）') }}</label>
          <input v-model="badDebtForm.reason" class="inp" :placeholder="t('不少于 4 字')" />
        </div>
        <div class="btn-row">
          <button type="button" class="btn primary" @click="submitBadDebt">{{ t('提交') }}</button>
          <button type="button" class="btn ghost" @click="badDebtModalOpen = false">
            {{ t('取消') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="toast" class="toast show">{{ toast }}</div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
  padding: 24px 20px 32px;
  background: #fff;
  width: 100%;
  max-width: none;
  margin: 0;
  box-sizing: border-box;
}
.page-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin: 0 0 16px;
}
.page-head h1 {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  color: var(--on-surface, #1f2329);
}
.page-head .sub {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--on-surface-variant, #5b616e);
}
.page-h {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  margin: 16px 0 4px;
  flex-wrap: wrap;
}
.page-h h1 {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
}
.sub {
  color: var(--on-surface-variant, #5b616e);
  font-size: 14px;
}
.tabs {
  display: flex;
  gap: 4px;
  margin: 0 0 20px;
  border-bottom: 1px solid var(--outline-variant, #c1c6d6);
}
.tab {
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
  border: none;
  background: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  cursor: pointer;
}
.tab.active {
  color: var(--primary, #005bbf);
  border-bottom-color: var(--primary, #005bbf);
}
.tab:hover {
  color: var(--primary, #005bbf);
}
.card {
  background: #fff;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: none;
}
.card-h {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.card-h h3 {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  color: var(--on-surface, #1f2329);
}
.card-h .hint {
  color: var(--on-surface-variant, #5b616e);
  font-size: 12px;
  margin-left: auto;
  font-weight: 400;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
@media (max-width: 720px) {
  .grid2 {
    grid-template-columns: 1fr;
  }
}
.kv {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid rgba(193, 198, 214, 0.45);
  font-size: 14px;
}
.kv:last-child {
  border-bottom: none;
}
.kv .k {
  color: var(--on-surface-variant, #5b616e);
}
.kv .v {
  font-weight: 600;
  color: var(--on-surface, #1f2329);
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
@media (max-width: 900px) {
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
.kpi {
  background: #fff;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  padding: 16px 18px;
}
.kpi .kl {
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  margin-bottom: 6px;
}
.kpi .kv2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
}
.mono {
  font-family: 'Roboto Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.badge {
  display: inline-flex;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
}
.badge.green {
  background: #e8f5e9;
  color: #2e7d32;
}
.badge.amber {
  background: #fff3e0;
  color: #e65100;
}
.badge.red {
  background: #fdebec;
  color: #c62828;
}
.badge.gray {
  background: #e6e8e9;
  color: #5b616e;
}
.badge.blue {
  background: rgba(0, 91, 191, 0.08);
  color: var(--primary, #005bbf);
}
.denom {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 14px;
}
.denom .d {
  display: flex;
  justify-content: space-between;
  background: var(--surface-container-low, #f2f4f5);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
}
.btn-row {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  flex-wrap: wrap;
  align-items: center;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  background: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  color: var(--on-surface, #1f2329);
}
.btn.primary {
  background: var(--primary, #005bbf);
  border-color: var(--primary, #005bbf);
  color: #fff;
}
.btn.primary:hover:not(:disabled) {
  filter: brightness(0.96);
}
.btn.green {
  background: #2e7d32;
  border-color: #2e7d32;
  color: #fff;
}
.btn.sm {
  padding: 6px 12px;
  font-size: 12px;
}
.btn.ghost {
  background: #fff;
  color: var(--on-surface-variant, #5b616e);
}
.btn.ghost:hover {
  background: var(--surface-container-low, #f2f4f5);
}
.link {
  background: none;
  border: none;
  color: var(--primary, #005bbf);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  padding: 0;
}
.link:disabled {
  color: #c0c6d0;
  cursor: not-allowed;
}
.preview {
  background: var(--surface-container-low, #f2f4f5);
  border: 1px solid rgba(193, 198, 214, 0.45);
  border-radius: 10px;
  padding: 14px;
  font-size: 13px;
}
.preview .row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
}
.arrow {
  color: var(--on-surface-variant, #5b616e);
  margin: 0 6px;
}
.approve-flow {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}
.flow-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 10px;
}
.flow-step .num {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--surface-container-low, #f2f4f5);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 12px;
  flex-shrink: 0;
}
.flow-step.done .num {
  background: #2e7d32;
  color: #fff;
}
.flow-step.cur .num {
  background: var(--primary, #005bbf);
  color: #fff;
}
.flow-step .meta .t {
  font-weight: 600;
  font-size: 13px;
}
.flow-step .meta .s {
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  text-align: left;
}
.tbl th {
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
  border-bottom: 1px solid var(--outline-variant, #c1c6d6);
  white-space: nowrap;
  background: transparent;
}
.tbl td {
  padding: 14px;
  border-bottom: 1px solid rgba(193, 198, 214, 0.45);
  vertical-align: middle;
  font-size: 14px;
}
.tbl tbody tr:hover {
  background: var(--surface-container-low, #f2f4f5);
}
.tbl .ctr {
  text-align: center;
}
.note {
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  background: var(--surface-container-low, #f2f4f5);
  border-radius: 8px;
  padding: 10px 12px;
  margin-top: 12px;
  line-height: 1.6;
}
.note-inline {
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
}
.hint {
  color: var(--on-surface-variant, #5b616e);
  font-size: 13px;
  padding: 12px 0;
}
.muted {
  color: var(--on-surface-variant, #5b616e);
}
.sm {
  font-size: 12px;
}
.warn {
  background: #fff3e0;
  color: #e65100;
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 12px;
  margin-top: 10px;
  line-height: 1.5;
}
.warn.orange {
  background: #fff3e0;
  color: #e65100;
  margin-bottom: 16px;
  margin-top: 0;
}
.primary {
  color: var(--primary, #005bbf);
}
.up {
  color: #2e7d32;
}
.dn {
  color: #c62828;
}
.switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: #d0d5dd;
  border-radius: 22px;
  transition: 0.2s;
}
.slider::before {
  content: '';
  position: absolute;
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background: #fff;
  border-radius: 50%;
  transition: 0.2s;
}
.switch input:checked + .slider {
  background: var(--primary, #005bbf);
}
.switch input:checked + .slider::before {
  transform: translateX(18px);
}
.usage-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.usage-bar {
  width: 100px;
  height: 8px;
  background: rgba(193, 198, 214, 0.45);
  border-radius: 4px;
  overflow: hidden;
}
.usage-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}
.usage-fill.ok {
  background: #2e7d32;
}
.usage-fill.warn {
  background: #e65100;
}
.usage-fill.danger {
  background: #c62828;
}
.age-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
@media (max-width: 720px) {
  .age-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
.age-cell {
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}
.age-cell.ok {
  background: #e8f5e9;
  color: #2e7d32;
  border-color: transparent;
}
.age-cell.warn {
  background: #fff3e0;
  color: #e65100;
  border-color: transparent;
}
.age-cell.bad {
  background: #fdebec;
  color: #c62828;
  border-color: transparent;
}
.age-label {
  font-weight: 700;
  font-size: 15px;
  margin-bottom: 4px;
}
.age-hint {
  font-size: 12px;
  opacity: 0.85;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(20, 30, 60, 0.38);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.modal {
  background: #fff;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  width: 440px;
  max-width: 92vw;
  padding: 22px;
  max-height: 90vh;
  overflow-y: auto;
}
.modal h3 {
  font-size: 16px;
  margin: 0 0 4px;
  font-weight: 700;
}
.msub {
  color: var(--on-surface-variant, #5b616e);
  font-size: 12px;
  margin-bottom: 16px;
}
.field {
  margin-bottom: 14px;
}
.field label {
  display: block;
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  margin-bottom: 6px;
  font-weight: 600;
}
.inp {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
}
.inp:focus {
  outline: none;
  border-color: var(--primary, #005bbf);
  box-shadow: 0 0 0 3px rgba(0, 91, 191, 0.12);
}
.inp.mt {
  margin-top: 8px;
}
.toast {
  position: fixed;
  bottom: 26px;
  left: 50%;
  transform: translateX(-50%);
  background: #1f2430;
  color: #fff;
  padding: 11px 18px;
  border-radius: 10px;
  font-size: 13px;
  opacity: 0;
  transition: 0.25s;
  z-index: 60;
  pointer-events: none;
}
.toast.show {
  opacity: 1;
}
</style>
