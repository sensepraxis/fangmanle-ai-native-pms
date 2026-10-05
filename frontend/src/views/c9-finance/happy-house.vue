<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'
import { localizeSeedText } from '../../lib/localizeSeed'

/**
 * 发票管理：数电票 · 待开/已开/红冲 · 推送与归档
 * 信息架构对齐发票管理原型；视觉对齐财务对账中心
 */
import { computed, onMounted, ref, watch } from 'vue'
import FinanceOpsNav from '../../components/FinanceOpsNav.vue'
import FinanceAiPlanDrawer from '../../components/FinanceAiPlanDrawer.vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'

function loc(s?: string | null) {
  return localizeSeedText(s)
}

type Status = 'todo' | 'done' | 'red' | 'fail' | 'draft'
type Tab = 'all' | Status

type InvRow = {
  id: number | null
  key: string
  kind: string
  order_id: number
  order_no: string
  guest_name: string
  channel: string
  channel_cls: string
  title_type: string
  buyer_name: string
  tax_no: string
  invoice_no: string | null
  display_no: string | null
  status: Status
  issued_at: string | null
  overdue_days: number
  push_status: string
  nights: number
  check_in: string | null
  check_out: string | null
  gross_amount: number
  platform_fee: number
  net_amount: number
  tax_rate: number
  tax_amount: number
  amount_excl_tax: number
  commission_rate?: number
  commission_pct?: number
  commission_formula?: string
  original_invoice_no: string | null
  note?: string
}

type TitleOpt = {
  buyer_name: string
  tax_no: string
  title_type: string
  tax_validated?: boolean
}
type HistItem = { time: string; who: string; text: string; kind: string }

const loading = ref(false)
const q = ref('')
const period = ref('month')
const titleFilter = ref('all')
const channelFilter = ref('all')
const tab = ref<Tab>('all')
const items = ref<InvRow[]>([])
const titles = ref<TitleOpt[]>([])
const history = ref<HistItem[]>([])
const selectedKey = ref<string | null>(null)
const checked = ref<Set<string>>(new Set())
const kpi = ref({
  pending_amount: 0,
  pending_count: 0,
  pending_vs: '',
  issued_count: 0,
  issued_amount: 0,
  issued_vs: '',
  leak_count: 0,
  leak_amount: 0,
  leak_vs: '',
  compliance_rate: 0,
  compliance_vs: '',
})
const taxEst = ref({
  period: '',
  payable: 0,
  output_tax: 0,
  input_credit: 0,
  refund_risk: '—',
  disclaimer: '',
  note: '',
})
const counts = ref({ all: 0, todo: 0, done: 0, red: 0, fail: 0, draft: 0 })
const alertInfo = ref({
  count: 0,
  amount: 0,
  channels: [] as string[],
  message: '' as string | null,
})
const seller = ref({ name: '', tax_no: '', address: '', city: '' })
const taxDocumentsEnabled = ref(true)

const redModal = ref(false)
const redReasonCode = ref('抬头信息错误（税号/名称）')
const redReasonDetail = ref('')
const redTarget = ref<InvRow | null>(null)
const issueModal = ref(false)
const issueTarget = ref<InvRow | null>(null)
const issueTitleIdx = ref(0)
const pushModal = ref(false)
const pushChannels = ref({ sms: true, wechat: true, email: false })
const newWizard = ref(false)
const aiOpen = ref(false)
const wizardOrderKey = ref('')
const wizardTitleIdx = ref(0)
const wizardAmountMode = ref<'gross' | 'net'>('gross')
const wizardPush = ref({ sms: true, email: true, wechat: false })

const RED_REASON_KEYS = [
  '客人投诉房型与实际不符',
  '抬头信息错误（税号/名称）',
  '金额计算错误',
  '订单取消需冲销',
  '其他（必填详细说明）',
] as const

function statusLabel(st: Status) {
  const map: Record<Status, string> = {
    todo: t('待开'),
    done: t('已开'),
    red: t('红冲中'),
    fail: t('推送失败'),
    draft: t('草稿'),
  }
  return map[st] || st
}

const STATUS_META: Record<Status, { cls: string }> = {
  todo: { cls: 'info' },
  done: { cls: 'ok' },
  red: { cls: 'purple' },
  fail: { cls: 'err' },
  draft: { cls: 'gray' },
}

function money(n: number | null | undefined) {
  if (n == null || Number.isNaN(Number(n))) return '—'
  const v = Number(n)
  const sign = v < 0 ? '−' : ''
  return `${sign}¥${Math.abs(v).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function titleTypeLabel(typ: string) {
  if (typ === 'corp_special') return t('企业专票')
  if (typ === 'corp_normal') return t('企业普票')
  return t('个人')
}

const channelOptions = computed(() =>
  [...new Set(items.value.map((i) => i.channel).filter(Boolean))].sort(),
)

const filtered = computed(() => {
  let list = items.value
  if (tab.value !== 'all') list = list.filter((i) => i.status === tab.value)
  if (titleFilter.value !== 'all') {
    if (titleFilter.value === 'personal') list = list.filter((i) => i.title_type === 'personal')
    else if (titleFilter.value === 'corp')
      list = list.filter((i) => i.title_type === 'corp_special' || i.title_type === 'corp_normal')
  }
  if (channelFilter.value !== 'all') list = list.filter((i) => i.channel === channelFilter.value)
  const s = q.value.trim().toLowerCase()
  if (s) {
    list = list.filter(
      (i) =>
        i.order_no.toLowerCase().includes(s) ||
        (i.guest_name || '').toLowerCase().includes(s) ||
        (i.buyer_name || '').toLowerCase().includes(s) ||
        (i.invoice_no || '').includes(s) ||
        (i.tax_no || '').toLowerCase().includes(s),
    )
  }
  return list
})

const selected = computed(() => items.value.find((i) => i.key === selectedKey.value) || null)

const alertText = computed(() => {
  if (alertInfo.value.message) return loc(alertInfo.value.message)
  const ch =
    alertInfo.value.channels
      ?.slice(0, 3)
      .map((c) => loc(c))
      .join(', ') || t('多渠道')
  const n = alertInfo.value.count
  const amt = money(alertInfo.value.amount)
  if (!n) return t('当前无明显漏开；客人离店后再索票会进入待开票池，不会因关账清空。')
  return t('涉及 {ch}。有 {n} 单已结账仍未开票，合计 {amt}，建议优先处理。', {
    ch,
    n,
    amt,
  })
})

const pendingPool = computed(() => items.value.filter((i) => i.status === 'todo'))

const wizardOrder = computed(
  () =>
    pendingPool.value.find((i) => i.key === wizardOrderKey.value) || pendingPool.value[0] || null,
)

const wizardTitles = computed(() => {
  const base = titles.value.length ? [...titles.value] : []
  const o = wizardOrder.value
  if (o) {
    const exists = base.some((t) => t.buyer_name === o.buyer_name && t.tax_no === o.tax_no)
    if (!exists) {
      base.unshift({
        buyer_name: o.buyer_name,
        tax_no: o.tax_no,
        title_type: o.title_type,
        tax_validated: !!(o.tax_no && o.tax_no.length >= 15),
      })
    }
  }
  return base
})

const issueTitles = computed(() => {
  const row = issueTarget.value
  const base = titles.value.length ? [...titles.value] : []
  if (row) {
    const exists = base.some((t) => t.buyer_name === row.buyer_name && t.tax_no === row.tax_no)
    if (!exists) {
      base.unshift({
        buyer_name: row.buyer_name,
        tax_no: row.tax_no,
        title_type: row.title_type,
        tax_validated: !!(row.tax_no && row.tax_no.length >= 15),
      })
    }
  }
  return base
})

const redReasonFinal = computed(() => {
  const code = redReasonCode.value
  if (code.startsWith('其他')) {
    return redReasonDetail.value.trim() || ''
  }
  const extra = redReasonDetail.value.trim()
  // 审计落库用已翻译展示文案，跟当前 Locale
  const label = t(code)
  return extra ? `${label}: ${extra}` : label
})

async function load() {
  loading.value = true
  try {
    const data = await api.invoiceWorkspace(hotelStore.hotelId)
    items.value = (data?.items || []) as InvRow[]
    titles.value = (data?.titles || []) as TitleOpt[]
    history.value = (data?.history || []) as HistItem[]
    kpi.value = { ...kpi.value, ...(data?.kpi || {}) }
    taxEst.value = { ...taxEst.value, ...(data?.tax_estimate || {}) }
    counts.value = { all: 0, todo: 0, done: 0, red: 0, fail: 0, draft: 0, ...(data?.counts || {}) }
    alertInfo.value = {
      count: data?.alert?.count || 0,
      amount: data?.alert?.amount || 0,
      channels: data?.alert?.channels || [],
      message: data?.alert?.message || null,
    }
    seller.value = {
      name: data?.seller?.name || '',
      tax_no: data?.seller?.tax_no || '',
      address: data?.seller?.address || '',
      city: data?.seller?.city || '',
    }
    if (typeof data?.tax_documents_enabled === 'boolean') {
      taxDocumentsEnabled.value = data.tax_documents_enabled
    }
    if (!selectedKey.value && items.value.length) {
      const prefer = items.value.find((i) => i.status === 'todo') || items.value[0]
      selectedKey.value = prefer.key
    }
  } catch (e: any) {
    toast(e?.message || t('加载发票工作台失败'), false)
    items.value = []
  } finally {
    loading.value = false
  }
}

function selectRow(row: InvRow) {
  selectedKey.value = row.key
}

function toggleCheck(key: string, e: Event) {
  e.stopPropagation()
  const next = new Set(checked.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  checked.value = next
}

function selectAllFiltered(on: boolean) {
  const next = new Set(checked.value)
  for (const r of filtered.value) {
    if (on) next.add(r.key)
    else next.delete(r.key)
  }
  checked.value = next
}

function locateLeaks() {
  tab.value = 'todo'
  channelFilter.value = 'all'
  titleFilter.value = 'all'
  q.value = ''
  const first = items.value.find((i) => i.status === 'todo')
  if (first) selectedKey.value = first.key
  toast(t('已定位到待开票池'))
}

function openRed(row: InvRow) {
  if (!row.id || row.status !== 'done') {
    toast(t('仅已开发票可红冲'), false)
    return
  }
  redTarget.value = row
  redReasonCode.value = '抬头信息错误（税号/名称）'
  redReasonDetail.value = ''
  redModal.value = true
}

async function confirmRed() {
  const row = redTarget.value
  if (!row?.id) return
  if (!redReasonFinal.value) {
    toast(t('请填写红冲原因（审计留痕）'), false)
    return
  }
  try {
    await api.redFlushInvoice(hotelStore.hotelId, row.id, redReasonFinal.value)
    redModal.value = false
    toast(t('红字发票已生成 · 操作已记入审计日志'))
    await load()
  } catch (e: any) {
    toast(e?.message || t('红冲失败'), false)
  }
}

function openIssue(row: InvRow) {
  issueTarget.value = row
  issueTitleIdx.value = 0
  issueModal.value = true
}

function openNewWizard() {
  wizardOrderKey.value = pendingPool.value[0]?.key || ''
  wizardTitleIdx.value = 0
  wizardAmountMode.value = 'gross'
  newWizard.value = true
}

async function confirmIssue() {
  const row = issueTarget.value
  if (!row?.order_id) return
  const title = issueTitles.value[issueTitleIdx.value]
  if (title && (title.title_type || '').startsWith('corp') && !title.tax_no) {
    toast(t('抬头库中暂无该企业税号（未编造），请人工核对后开票'), false)
  }
  try {
    await api.issueInvoice(hotelStore.hotelId, row.order_id)
    issueModal.value = false
    toast(t('已写入数据库发票记录'))
    await load()
  } catch (e: any) {
    toast(t(e?.message || '开票失败'), false)
  }
}

async function confirmWizardIssue() {
  const row = wizardOrder.value
  if (!row?.order_id) {
    toast(t('请先选择待开订单'), false)
    return
  }
  const title = wizardTitles.value[wizardTitleIdx.value]
  if (title && (title.title_type || '').startsWith('corp') && !title.tax_no) {
    toast(t('抬头库中暂无该企业税号（未编造），请人工核对后开票'), false)
  }
  try {
    await api.issueInvoice(hotelStore.hotelId, row.order_id)
    newWizard.value = false
    toast(t('已写入数据库发票记录'))
    await load()
  } catch (e: any) {
    toast(t(e?.message || '开票失败'), false)
  }
}

function openBatchPush() {
  if (!checked.value.size) {
    toast(t('请先勾选要推送的已开发票'), false)
    return
  }
  pushModal.value = true
}

function confirmPush() {
  pushModal.value = false
  toast(t('推送通道尚未接入，未改动数据库记录'), false)
}

function retryPush(_row: InvRow) {
  toast(t('推送通道尚未接入，请稍后在乐企/短信网关就绪后重试'), false)
}

function downloadPdf(row: InvRow) {
  toast(t('当前仅预览库内票面信息：{no}', { no: row.invoice_no || row.order_no }))
}

function exportZip() {
  toast(t('导出将基于当前筛选的库内发票列表（文件通道待接入）'))
}

function goPendingPool() {
  newWizard.value = false
  locateLeaks()
}

function reissueAfterRed(row: InvRow) {
  toast(t('已带入源票信息，请从待开池为 {order} 重开正确票', { order: row.order_no }))
  tab.value = 'todo'
  const pending = items.value.find((i) => i.order_id === row.order_id && i.status === 'todo')
  if (pending) {
    selectedKey.value = pending.key
    openIssue(pending)
  } else {
    locateLeaks()
  }
}

const isCrossMonth = computed(() => {
  const row = redTarget.value
  if (!row?.issued_at) return false
  const d = new Date(row.issued_at.replace(/-/g, '/'))
  const now = new Date()
  return d.getMonth() !== now.getMonth() || d.getFullYear() !== now.getFullYear()
})

const taxPeriodLabel = computed(() => {
  if (period.value === 'last') return t('上月')
  if (period.value === 'quarter') return t('本季度')
  return taxEst.value.period || t('本月')
})

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(wizardOrderKey, () => {
  wizardTitleIdx.value = 0
})
</script>

<template>
  <div class="page inv-page">
    <FinanceOpsNav />

    <div class="page-head">
      <h1>{{ t('发票管理') }}</h1>
      <button v-if="commercialEnabled()" type="button" class="btn soft" @click="aiOpen = true">
        {{ t('AI 安排') }}
      </button>
    </div>

    <div class="alert" v-if="!taxDocumentsEnabled">
      {{ t('本部署未启用税务凭证') }}
    </div>

    <div class="page-tools">
      <input
        class="tb-input search"
        v-model="q"
        :placeholder="t('搜订单号 / 手机号 / 发票号 / 抬头…')"
      />
      <select class="tb-input" v-model="period">
        <option value="month">{{ t('本月') }}</option>
        <option value="last">{{ t('上月') }}</option>
        <option value="quarter">{{ t('本季度') }}</option>
      </select>
      <select class="tb-input" v-model="titleFilter">
        <option value="all">{{ t('全部抬头类型') }}</option>
        <option value="corp">{{ t('企业') }}</option>
        <option value="personal">{{ t('个人') }}</option>
      </select>
      <select class="tb-input" v-model="channelFilter">
        <option value="all">{{ t('全部渠道') }}</option>
        <option v-for="c in channelOptions" :key="c" :value="c">{{ loc(c) }}</option>
      </select>
      <button type="button" class="btn" :disabled="!taxDocumentsEnabled" @click="openBatchPush">
        {{ t('批量推送') }}
      </button>
      <button type="button" class="btn" @click="exportZip">{{ t('导出 ZIP') }}</button>
      <button
        type="button"
        class="btn primary ml-auto"
        :disabled="!taxDocumentsEnabled"
        @click="openNewWizard"
      >
        {{ t('新建发票') }}
      </button>
    </div>

    <FinanceAiPlanDrawer v-model:open="aiOpen" scene="invoice" @confirmed="load" />

    <div class="alert err" v-if="alertInfo.count">
      <b
        >{{ t('漏开告警 ·') }} {{ alertInfo.count }} {{ t('单') }} {{ money(alertInfo.amount) }}
        {{ t('待处理') }}</b
      >
      <div class="alert-body">{{ alertText }}</div>
      <button type="button" class="btn danger sm" @click="locateLeaks">
        {{ t('一键定位 →') }}
      </button>
    </div>

    <div class="kpi-row">
      <div class="kpi">
        <i class="stripe blue" />
        <div class="kpi-label">
          {{ t('待开票池金额') }} <span class="tag">{{ t('需关注') }}</span>
        </div>
        <div class="kpi-num">{{ money(kpi.pending_amount) }}</div>
        <div class="kpi-vs">{{ loc(kpi.pending_vs) }} · {{ kpi.pending_count }} {{ t('单') }}</div>
      </div>
      <div class="kpi">
        <i class="stripe green" />
        <div class="kpi-label">{{ t('当月已开') }}</div>
        <div class="kpi-num">
          {{ kpi.issued_count }} <small>{{ t('张') }}</small>
          <span class="amt">· {{ money(kpi.issued_amount) }}</span>
        </div>
        <div class="kpi-vs ok">{{ loc(kpi.issued_vs) }}</div>
      </div>
      <div class="kpi">
        <i class="stripe red" />
        <div class="kpi-label">{{ t('漏开告警') }}</div>
        <div class="kpi-num">
          {{ kpi.leak_count }} <small>{{ t('单') }}</small>
        </div>
        <div class="kpi-vs err">{{ loc(kpi.leak_vs) }}</div>
      </div>
      <div class="kpi">
        <i class="stripe purple" />
        <div class="kpi-label">{{ t('合规率') }}</div>
        <div class="kpi-num">{{ kpi.compliance_rate }} <small>%</small></div>
        <div class="kpi-vs">{{ loc(kpi.compliance_vs) }}</div>
      </div>
    </div>

    <div class="alert info">
      <div>
        <b>{{ t('报税汇总 ·') }} {{ taxPeriodLabel }}</b>
        <span class="disc" v-if="taxEst.disclaimer">（{{ loc(taxEst.disclaimer) }}）</span>
        <span class="est">
          {{ t('应纳税额') }} <b>{{ money(taxEst.payable) }}</b> · {{ t('销项') }}
          {{ money(taxEst.output_tax) }} · {{ t('进项可抵扣') }} {{ money(taxEst.input_credit) }} ·
          {{ t('退税风险') }} <b class="ok">{{ taxEst.refund_risk }}</b>
        </span>
        <span class="disc" v-if="taxEst.note"> · {{ loc(taxEst.note) }}</span>
      </div>
    </div>

    <div class="split">
      <section class="list">
        <div class="list-tabs">
          <button type="button" :class="{ on: tab === 'all' }" @click="tab = 'all'">
            {{ t('全部') }} <span class="num">{{ counts.all }}</span>
          </button>
          <button type="button" :class="{ on: tab === 'todo' }" @click="tab = 'todo'">
            {{ t('待开') }} <span class="num">{{ counts.todo }}</span>
          </button>
          <button type="button" :class="{ on: tab === 'done' }" @click="tab = 'done'">
            {{ t('已开') }} <span class="num">{{ counts.done }}</span>
          </button>
          <button type="button" :class="{ on: tab === 'red' }" @click="tab = 'red'">
            {{ t('红冲中') }} <span class="num">{{ counts.red }}</span>
          </button>
          <button type="button" :class="{ on: tab === 'fail' }" @click="tab = 'fail'">
            {{ t('失败') }} <span class="num">{{ counts.fail }}</span>
          </button>
          <button type="button" :class="{ on: tab === 'draft' }" @click="tab = 'draft'">
            {{ t('草稿') }} <span class="num">{{ counts.draft }}</span>
          </button>
        </div>
        <div class="list-filter">
          <label class="chk">
            <input
              type="checkbox"
              :checked="checked.size > 0"
              @change="selectAllFiltered(($event.target as HTMLInputElement).checked)"
            />
            {{ t('全选当前列表') }}</label
          >
          <span class="muted">{{
            loading ? t('加载中…') : t('共 {n} 条', { n: filtered.length })
          }}</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th style="width: 36px" />
                <th>{{ t('订单 · 客人') }}</th>
                <th>{{ t('渠道') }}</th>
                <th>{{ t('抬头') }}</th>
                <th class="r">{{ t('开票金额') }}</th>
                <th class="r">{{ t('税额') }}</th>
                <th>{{ t('开票时间') }}</th>
                <th>{{ t('状态') }}</th>
                <th>{{ t('操作') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in filtered"
                :key="row.key"
                :class="{ cur: selectedKey === row.key, red: row.status === 'red' }"
                @click="selectRow(row)"
              >
                <td @click.stop>
                  <input
                    type="checkbox"
                    :checked="checked.has(row.key)"
                    @change="toggleCheck(row.key, $event)"
                  />
                </td>
                <td>
                  <div class="code">{{ row.order_no }} · {{ loc(row.guest_name) }}</div>
                  <div class="sub">
                    <template v-if="row.invoice_no">{{ t('票号') }} {{ row.invoice_no }}</template>
                    <template v-else>{{ t('尚未开票') }}</template>
                    <template v-if="row.nights"> · {{ row.nights }} {{ t('晚') }}</template>
                  </div>
                </td>
                <td>
                  <span class="chan" :class="row.channel_cls">{{ loc(row.channel) }}</span>
                </td>
                <td>
                  <div>{{ loc(row.buyer_name) }}</div>
                  <div class="sub" v-if="row.tax_no">{{ row.tax_no }}</div>
                </td>
                <td class="r" :class="{ err: row.gross_amount < 0 }">
                  {{ money(row.gross_amount) }}
                </td>
                <td class="r mut">{{ money(row.tax_amount) }}</td>
                <td>
                  <span v-if="row.status === 'todo' && row.overdue_days >= 3" class="err">
                    {{ t('已结 · 超 {n} 天未开', { n: row.overdue_days }) }}
                  </span>
                  <span v-else-if="row.issued_at">{{ row.issued_at }}</span>
                  <span v-else class="mut">—</span>
                </td>
                <td>
                  <span class="badge" :class="STATUS_META[row.status].cls">
                    {{ statusLabel(row.status) }}</span
                  >
                </td>
                <td class="ops" @click.stop>
                  <template v-if="row.status === 'todo'">
                    <button type="button" class="link" @click="openIssue(row)">
                      {{ t('立即开票') }}
                    </button>
                  </template>
                  <template v-else-if="row.status === 'done'">
                    <button type="button" class="link" @click="downloadPdf(row)">PDF</button>
                    <button type="button" class="link warn" @click="openRed(row)">
                      {{ t('红冲') }}
                    </button>
                  </template>
                  <template v-else-if="row.status === 'fail'">
                    <button type="button" class="link err" @click="retryPush(row)">
                      {{ t('重试推送') }}
                    </button>
                  </template>
                  <template v-else-if="row.status === 'red'">
                    <button type="button" class="link" @click="reissueAfterRed(row)">
                      {{ t('重开') }}
                    </button>
                    <span class="mut">{{ t('源') }} {{ row.original_invoice_no || '—' }}</span>
                  </template>
                </td>
              </tr>
              <tr v-if="!filtered.length">
                <td colspan="9" class="empty">{{ t('当前筛选下无发票') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <aside class="drawer" v-if="selected">
        <div class="drawer-h">
          <div class="ttl">{{ selected.order_no }} · {{ loc(selected.guest_name) }}</div>
          <span class="badge" :class="STATUS_META[selected.status].cls">
            {{ statusLabel(selected.status) }}</span
          >
          <span class="meta">{{ titleTypeLabel(selected.title_type) }}</span>
        </div>

        <div class="section" v-if="selected.platform_fee > 0 || selected.channel_cls === 'booking'">
          <div class="sec-t">{{ t('票面金额明细 · 客人报销口径') }}</div>
          <div class="breakdown">
            <div class="bd-row">
              <span>{{ t('客人票面金额（毛额）') }}</span
              ><b>{{ money(selected.gross_amount) }}</b>
            </div>
            <div class="bd-row warn" v-if="selected.platform_fee">
              <span>{{
                selected.commission_pct
                  ? t('平台佣金（{pct}%）', { pct: selected.commission_pct })
                  : t('平台佣金')
              }}</span>
              <b>−{{ money(selected.platform_fee) }}</b>
            </div>
            <div class="bd-row ok">
              <span>{{ t('酒店实际入账（净额）') }}</span
              ><b>{{ money(selected.net_amount) }}</b>
            </div>
          </div>
          <div v-if="selected.commission_formula" class="formula-box">
            <div class="formula-label">{{ t('OTA 佣金公式（配置）') }}</div>
            <div class="formula-body">{{ loc(selected.commission_formula) }}</div>
          </div>
        </div>

        <div class="section">
          <div class="sec-t">{{ t('数电票预览') }}</div>
          <div class="preview">
            <div class="inv-head">
              <div>
                {{ t('开票方') }}：{{ seller.name || '—' }}
                <template v-if="seller.city || seller.address">
                  <br />
                  {{ [seller.city, seller.address].filter(Boolean).join(' · ') }}</template
                >
                <br />
                {{ t('纳税人识别号') }}：{{ seller.tax_no || t('（门店税号未录入）') }}
              </div>
              <div class="r">
                {{ t('发票号码') }}：{{ selected.invoice_no || t('（开具后生成）') }}<br />
                {{ selected.issued_at || t('待开具') }}
              </div>
            </div>
            <div class="inv-title">{{ t('电子发票') }}</div>
            <div class="preview-row">
              <div>
                <div class="lbl">{{ t('购买方') }}</div>
                <div class="val">{{ loc(selected.buyer_name) }}</div>
              </div>
              <div>
                <div class="lbl">{{ t('统一社会信用代码') }}</div>
                <div class="val">{{ selected.tax_no || '—' }}</div>
              </div>
            </div>
            <div class="preview-row">
              <div>
                <div class="lbl">{{ t('项目') }}</div>
                <div class="val">{{ t('*住宿服务*住宿费') }}</div>
              </div>
              <div>
                <div class="lbl">{{ t('规格') }}</div>
                <div class="val">
                  {{ selected.nights || '—' }} {{ t('晚') }} · {{ loc(selected.channel) }}
                </div>
              </div>
            </div>
            <div class="preview-totals">
              <div class="row">
                <span>{{ t('不含税金额') }}</span
                ><span>{{ money(selected.amount_excl_tax) }}</span>
              </div>
              <div class="row">
                <span>{{ t('税率') }} {{ Math.round(selected.tax_rate * 100) }}%</span>
                <span>{{ money(selected.tax_amount) }}</span>
              </div>
              <div class="row total">
                <span>{{ t('价税合计') }}</span
                ><span>{{ money(selected.gross_amount) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="section">
          <div class="sec-t">{{ t('推送记录') }}</div>
          <div class="push-log mut">
            {{
              t(
                '暂无推送落库记录（短信 / 微信 / 邮箱通道未接入）。开票状态以数据库 `invoices` 为准。',
              )
            }}
          </div>
        </div>

        <div class="drawer-foot">
          <button
            v-if="selected.status === 'todo'"
            type="button"
            class="btn primary sm"
            @click="openIssue(selected)"
          >
            {{ t('立即开票') }}
          </button>
          <button
            v-if="selected.status === 'done'"
            type="button"
            class="btn sm"
            @click="downloadPdf(selected)"
          >
            {{ t('下载 PDF') }}
          </button>
          <button
            v-if="selected.status === 'done'"
            type="button"
            class="btn sm"
            @click="retryPush(selected)"
          >
            {{ t('重新推送') }}
          </button>
          <button
            v-if="selected.status === 'done'"
            type="button"
            class="btn danger sm"
            @click="openRed(selected)"
          >
            {{ t('红冲本票') }}
          </button>
          <button
            v-if="selected.status === 'fail'"
            type="button"
            class="btn danger sm"
            @click="retryPush(selected)"
          >
            {{ t('重试推送') }}
          </button>
          <button
            v-if="selected.status === 'red'"
            type="button"
            class="btn primary sm"
            @click="reissueAfterRed(selected)"
          >
            {{ t('重开正确票') }}
          </button>
        </div>
      </aside>
      <aside v-else class="drawer empty-drawer">{{ t('选中左侧发票查看票面与推送') }}</aside>
    </div>

    <div class="history" v-if="history.length">
      <div class="ttl">{{ t('发票合规历史 · 本周') }}</div>
      <div v-for="(h, i) in history" :key="i" class="hist-item">
        <span class="dot" />
        <span class="time">{{ h.time }}</span>
        <span class="who" v-if="h.who && h.who !== '系统' && h.who !== 'System'">{{ h.who }}</span>
        <span>{{ loc(h.text) }}</span>
      </div>
    </div>

    <!-- 红冲向导 -->
    <div v-if="redModal" class="modal" @click.self="redModal = false">
      <div class="modal-card lg">
        <div class="modal-h">
          <div class="ttl">{{ t('红冲发票 · 不可逆') }}</div>
          <div class="sub">{{ t('红字发票生成后上传税局；系统不会自动红冲，须人工确认') }}</div>
        </div>
        <div class="modal-b">
          <div class="item">
            <span>{{ t('原票号码') }}</span
            ><b>{{ redTarget?.invoice_no }}</b>
          </div>
          <div class="item">
            <span>{{ t('原开票时间') }}</span
            ><b>{{ redTarget?.issued_at || '—' }}</b>
          </div>
          <div class="item">
            <span>{{ t('订单') }}</span
            ><b>{{ redTarget?.order_no }} · {{ loc(redTarget?.guest_name) }}</b>
          </div>
          <div class="item">
            <span>{{ t('不含税金额') }}</span
            ><b>{{ money(redTarget?.amount_excl_tax) }}</b>
          </div>
          <div class="item">
            <span>{{ t('税额') }}</span
            ><b>{{ money(redTarget?.tax_amount) }}</b>
          </div>
          <div class="item">
            <span>{{ t('价税合计') }}</span
            ><b>{{ money(redTarget?.gross_amount) }}</b>
          </div>
          <div class="danger-line" v-if="isCrossMonth">
            {{ t('本票已跨月：不能作废，只能走红字发票；红冲会留下痕迹，原票不可恢复。') }}
          </div>
          <div class="warn-line" v-else>
            {{
              t('本月内开具的票：红冲将生成红字发票冲回原蓝字；红冲后如需正确票，请再点「重开」。')
            }}
          </div>
          <label class="field">
            <span>{{ t('红冲原因（必填 · 写入审计日志）') }}</span>
            <select v-model="redReasonCode">
              <option v-for="r in RED_REASON_KEYS" :key="r" :value="r">{{ t(r) }}</option>
            </select>
          </label>
          <label class="field">
            <span>{{
              redReasonCode.startsWith('其他') ? t('详细说明（必填）') : t('补充说明（可选）')
            }}</span>
            <textarea
              v-model="redReasonDetail"
              rows="2"
              :placeholder="t('例如：税号少写一位 / 金额多开了房费')"
            />
          </label>
        </div>
        <div class="modal-f">
          <button type="button" class="btn" @click="redModal = false">{{ t('取消') }}</button>
          <button type="button" class="btn danger" @click="confirmRed">
            {{ t('确认生成红字发票') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 开票确认（含抬头库） -->
    <div v-if="issueModal" class="modal" @click.self="issueModal = false">
      <div class="modal-card lg">
        <div class="modal-h">
          <div class="ttl">{{ t('确认开具数电票') }}</div>
          <div class="sub">{{ t('开票即上传税务链路；请核对抬头与金额，防认错公司') }}</div>
        </div>
        <div class="modal-b">
          <div class="item">
            <span>{{ t('订单') }}</span
            ><b>{{ issueTarget?.order_no }} · {{ loc(issueTarget?.guest_name) }}</b>
          </div>
          <div class="sec-t" style="margin: 12px 0 8px">{{ t('选抬头（企业须税号校验）') }}</div>
          <div class="title-pick">
            <button
              v-for="(titleRow, i) in issueTitles"
              :key="i"
              type="button"
              class="title-opt"
              :class="{ sel: issueTitleIdx === i }"
              @click="issueTitleIdx = i"
            >
              <span>
                <b>{{ loc(titleRow.buyer_name) }}</b>
                <div class="meta">
                  {{ titleRow.tax_no || t('个人无需税号') }} ·
                  {{ titleTypeLabel(titleRow.title_type) }}
                </div>
              </span>
              <span class="check" v-if="titleRow.tax_no">{{ t('有税号') }}</span>
              <span class="check warn" v-else-if="(titleRow.title_type || '').startsWith('corp')">{{
                t('缺税号')
              }}</span>
            </button>
          </div>
          <div class="item" style="margin-top: 12px">
            <span>{{ t('价税合计（毛额）') }}</span
            ><b>{{ money(issueTarget?.gross_amount) }}</b>
          </div>
          <div class="item" v-if="issueTarget && issueTarget.platform_fee > 0">
            <span>{{ t('平台佣金（另账）') }}</span
            ><b>−{{ money(issueTarget.platform_fee) }}</b>
          </div>
          <div v-if="issueTarget?.commission_formula" class="formula-box" style="margin-top: 10px">
            <div class="formula-label">{{ t('OTA 佣金公式') }}</div>
            <div class="formula-body">{{ loc(issueTarget.commission_formula) }}</div>
          </div>
          <div class="warn-line">
            {{ t('请确认没认错公司；税号错了客人报销不了，只能再红冲重开。') }}
          </div>
        </div>
        <div class="modal-f">
          <button type="button" class="btn" @click="issueModal = false">{{ t('取消') }}</button>
          <button type="button" class="btn primary" @click="confirmIssue">
            {{ t('确认开票') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 批量推送 -->
    <div v-if="pushModal" class="modal" @click.self="pushModal = false">
      <div class="modal-card">
        <div class="modal-h">
          <div class="ttl">{{ t('批量推送发票到客人') }}</div>
          <div class="sub">
            {{
              t('已勾选 {n} 条 · 仅对「已开」生效 · 可选短信 / 微信 / 邮箱', { n: checked.size })
            }}
          </div>
        </div>
        <div class="modal-b">
          <div class="push-row">
            <button
              type="button"
              class="push-chip"
              :class="{ on: pushChannels.sms }"
              @click="pushChannels.sms = !pushChannels.sms"
            >
              {{ t('短信') }}
            </button>
            <button
              type="button"
              class="push-chip"
              :class="{ on: pushChannels.wechat }"
              @click="pushChannels.wechat = !pushChannels.wechat"
            >
              {{ t('微信卡包') }}
            </button>
            <button
              type="button"
              class="push-chip"
              :class="{ on: pushChannels.email }"
              @click="pushChannels.email = !pushChannels.email"
            >
              {{ t('邮箱') }}
            </button>
          </div>
        </div>
        <div class="modal-f">
          <button type="button" class="btn" @click="pushModal = false">{{ t('取消') }}</button>
          <button type="button" class="btn primary" @click="confirmPush">
            {{ t('确认推送') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 新建发票向导 -->
    <div v-if="newWizard" class="modal" @click.self="newWizard = false">
      <div class="modal-card lg">
        <div class="modal-h">
          <div class="ttl">{{ t('新建发票 · 数电票开具向导') }}</div>
          <div class="sub">{{ t('将通过乐企平台开具，开票即上传税局（约 3–5 秒）') }}</div>
        </div>
        <div class="modal-b">
          <div class="step">
            <div class="num">1</div>
            <div class="body">
              <b>{{ t('选订单') }}</b>
              <small>{{ t('从待开票池选一张（离店后索票也会在这里）') }}</small>
              <select class="field-sel" v-model="wizardOrderKey" v-if="pendingPool.length">
                <option v-for="o in pendingPool" :key="o.key" :value="o.key">
                  {{ o.order_no }} · {{ loc(o.guest_name) }} · {{ money(o.gross_amount) }}
                  <template v-if="o.overdue_days"
                    >（{{ t('已等 {n} 天', { n: o.overdue_days }) }}）</template
                  >
                </option>
              </select>
              <p class="hint" v-else>
                {{ t('暂无待开订单。可先去订单结账，或点下方回待开池查看。') }}
              </p>
            </div>
          </div>
          <div class="step" v-if="wizardOrder">
            <div class="num">2</div>
            <div class="body">
              <b>{{ t('选抬头') }}</b>
              <small>{{ t('企业抬头须税号校验通过，防认错公司') }}</small>
              <div class="title-pick" style="margin-top: 8px">
                <button
                  v-for="(titleRow, i) in wizardTitles"
                  :key="i"
                  type="button"
                  class="title-opt"
                  :class="{ sel: wizardTitleIdx === i }"
                  @click="wizardTitleIdx = i"
                >
                  <span>
                    <b>{{ loc(titleRow.buyer_name) }}</b>
                    <div class="meta">
                      {{ titleRow.tax_no || t('个人') }} · {{ titleTypeLabel(titleRow.title_type) }}
                    </div>
                  </span>
                  <span class="check" v-if="titleRow.tax_no">{{ t('有税号') }}</span>
                  <span
                    class="check warn"
                    v-else-if="(titleRow.title_type || '').startsWith('corp')"
                    >{{ t('缺税号') }}</span
                  >
                </button>
              </div>
            </div>
          </div>
          <div class="step" v-if="wizardOrder">
            <div class="num">3</div>
            <div class="body">
              <b>{{ t('金额口径') }}</b>
              <small>{{ t('预订平台客人通常按毛额报销；协议挂账可按净额') }}</small>
              <div class="amt-pick">
                <button
                  type="button"
                  class="title-opt"
                  :class="{ sel: wizardAmountMode === 'gross' }"
                  @click="wizardAmountMode = 'gross'"
                >
                  <span>
                    <b>{{ t('客人报销口径（毛额）') }} {{ money(wizardOrder.gross_amount) }}</b>
                    <div class="meta">{{ t('推荐 · 与客人实付对齐') }}</div>
                  </span>
                  <span class="check" v-if="wizardAmountMode === 'gross'">{{ t('推荐') }}</span>
                </button>
                <button
                  type="button"
                  class="title-opt"
                  :class="{ sel: wizardAmountMode === 'net' }"
                  @click="wizardAmountMode = 'net'"
                >
                  <span>
                    <b>{{ t('酒店入账口径（净额）') }} {{ money(wizardOrder.net_amount) }}</b>
                    <div class="meta" v-if="wizardOrder.platform_fee">
                      {{ t('已扣平台佣金') }} {{ money(wizardOrder.platform_fee) }}
                    </div>
                  </span>
                </button>
              </div>
            </div>
          </div>
          <div class="step">
            <div class="num">4</div>
            <div class="body">
              <b>{{ t('推送渠道') }}</b>
              <div class="push-row" style="margin-top: 6px">
                <button
                  type="button"
                  class="push-chip"
                  :class="{ on: wizardPush.sms }"
                  @click="wizardPush.sms = !wizardPush.sms"
                >
                  {{ t('短信') }}
                </button>
                <button
                  type="button"
                  class="push-chip"
                  :class="{ on: wizardPush.email }"
                  @click="wizardPush.email = !wizardPush.email"
                >
                  {{ t('邮箱') }}
                </button>
                <button
                  type="button"
                  class="push-chip"
                  :class="{ on: wizardPush.wechat }"
                  @click="wizardPush.wechat = !wizardPush.wechat"
                >
                  {{ t('微信卡包') }}
                </button>
              </div>
            </div>
          </div>
          <div class="danger-line">
            {{ t('开票即上传税局，无法删除。开错只能红冲（本月可冲回，跨月走红字发票）。') }}
          </div>
        </div>
        <div class="modal-f">
          <button type="button" class="btn" @click="goPendingPool">{{ t('去待开票池') }}</button>
          <button type="button" class="btn" @click="newWizard = false">{{ t('取消') }}</button>
          <button
            type="button"
            class="btn primary"
            :disabled="!wizardOrder"
            @click="confirmWizardIssue"
          >
            {{ t('确认开票') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inv-page {
  --brand: #6750a4;
  --brand-soft: #f3edf7;
  --ink: #1c1b1f;
  --mut: #79747e;
  --line: #e7e0ec;
  --ok: #1b6b3a;
  --ok-soft: #e8f5e9;
  --warn: #8c5000;
  --warn-soft: #ffeedd;
  --err: #b3261e;
  --err-soft: #f9dedc;
  --info: #4a5fbf;
  --info-soft: #e8eefc;
  --purple: #7e47c7;
  --purple-soft: #f3ebff;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.page-head h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: var(--ink);
}
.page-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.ml-auto {
  margin-left: auto;
}
.tb-input {
  padding: 7px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  font-size: 12px;
}
.tb-input.search {
  min-width: 220px;
  flex: 1;
  max-width: 320px;
}
.btn {
  padding: 7px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
}
.btn:hover {
  border-color: var(--brand);
  color: var(--brand);
}
.btn.primary {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}
.btn.primary:hover {
  color: #fff;
  filter: brightness(0.95);
}
.btn.danger {
  color: var(--err);
  border-color: #f4c8ca;
}
.btn.danger:hover {
  background: var(--err);
  color: #fff;
}
.btn.sm {
  padding: 5px 10px;
  font-size: 12px;
}
.btn.soft {
  background: var(--brand-soft);
  color: var(--brand);
  border-color: #d8e4fb;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
.kpi {
  position: relative;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px 16px 14px 18px;
  overflow: hidden;
}
.kpi .stripe {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
}
.stripe.blue {
  background: var(--info);
}
.stripe.green {
  background: var(--ok);
}
.stripe.red {
  background: var(--err);
}
.stripe.purple {
  background: var(--purple);
}
.kpi-label {
  font-size: 12px;
  color: var(--mut);
  display: flex;
  align-items: center;
  gap: 6px;
}
.kpi-num {
  font-size: 22px;
  font-weight: 700;
  margin: 6px 0 4px;
  font-variant-numeric: tabular-nums;
}
.kpi-num small {
  font-size: 12px;
  font-weight: 400;
  color: var(--mut);
}
.kpi-num .amt {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}
.kpi-vs {
  font-size: 11px;
  color: var(--mut);
}
.tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  background: var(--brand-soft);
  color: var(--brand);
}
.alert {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 12px;
  line-height: 1.55;
}
.alert.err {
  background: var(--err-soft);
  border: 1px solid #f4c8ca;
  color: #7a2a2a;
}
.alert.info {
  background: var(--info-soft);
  border: 1px solid #d8e4fb;
  color: #2a3f8f;
}
.alert-body {
  flex: 1;
  font-size: 12px;
}
.alert .disc {
  font-size: 12px;
  opacity: 0.85;
}
.alert .est {
  display: block;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}
.split {
  display: grid;
  grid-template-columns: 1.45fr 1fr;
  gap: 14px;
  align-items: start;
}
.list,
.drawer {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
}
.list-tabs {
  display: flex;
  gap: 4px;
  padding: 0 12px;
  border-bottom: 1px solid var(--line);
  overflow-x: auto;
}
.list-tabs button {
  border: 0;
  background: none;
  padding: 12px 10px;
  font-size: 13px;
  color: var(--mut);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
}
.list-tabs button.on {
  color: var(--brand);
  border-bottom-color: var(--brand);
  font-weight: 600;
}
.list-tabs .num {
  margin-left: 4px;
  background: #f1f4f8;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 11px;
}
.list-tabs button.on .num {
  background: var(--brand-soft);
  color: var(--brand);
}
.list-filter {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid #f1f4f8;
  background: #fbfcfd;
}
.chk {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--mut);
}
.muted,
.mut {
  color: var(--mut);
  font-size: 12px;
}
.table-wrap {
  overflow: auto;
  max-height: 560px;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th {
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: var(--mut);
  padding: 10px 12px;
  background: #fbfcfd;
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
}
td {
  padding: 12px;
  border-bottom: 1px solid #f1f4f8;
  font-size: 13px;
  vertical-align: middle;
}
tr.cur {
  background: var(--brand-soft);
}
tr.cur td:first-child {
  box-shadow: inset 3px 0 0 var(--brand);
}
tr.red td {
  color: var(--err);
}
tr:hover {
  cursor: pointer;
  background: #fbfcfd;
}
tr.cur:hover {
  background: var(--brand-soft);
}
.r {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.code {
  font-weight: 700;
  color: var(--brand);
}
.sub {
  font-size: 11px;
  color: var(--mut);
  margin-top: 2px;
}
.chan {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 11px;
  background: #f1f4f8;
}
.chan.wechat {
  background: #e8fbf1;
  color: #12825a;
}
.chan.alipay {
  background: #e8f4fe;
  color: #1a6bc9;
}
.chan.bank,
.chan.direct {
  background: #fdf1e5;
  color: #b05e2d;
}
.chan.booking {
  background: #e8f1ff;
  color: #1a56c9;
}
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}
.badge.ok {
  background: var(--ok-soft);
  color: var(--ok);
}
.badge.info {
  background: var(--info-soft);
  color: var(--info);
}
.badge.err {
  background: var(--err-soft);
  color: var(--err);
}
.badge.purple {
  background: var(--purple-soft);
  color: var(--purple);
}
.badge.gray {
  background: #f1f4f8;
  color: var(--mut);
}
.ops {
  white-space: nowrap;
}
.link {
  border: 0;
  background: none;
  color: var(--brand);
  cursor: pointer;
  font-size: 12px;
  padding: 0 4px;
}
.link.warn {
  color: var(--warn);
}
.link.err {
  color: var(--err);
}
.empty {
  text-align: center;
  color: var(--mut);
  padding: 28px !important;
}
.err {
  color: var(--err);
}
.ok {
  color: var(--ok);
}
.drawer-h {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
  flex-wrap: wrap;
}
.drawer-h .ttl {
  font-weight: 700;
  font-size: 14px;
}
.drawer-h .meta {
  margin-left: auto;
  font-size: 11px;
  color: var(--mut);
}
.section {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f4f8;
}
.sec-t {
  font-size: 12px;
  color: var(--mut);
  font-weight: 600;
  margin-bottom: 10px;
}
.breakdown {
  padding: 10px 12px;
  background: #f7f8fa;
  border-radius: 8px;
  font-size: 12px;
}
.bd-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
}
.bd-row.warn {
  color: var(--warn);
}
.bd-row.ok {
  color: var(--ok);
  font-weight: 600;
  border-top: 1px dashed var(--line);
  margin-top: 4px;
  padding-top: 8px;
}
.formula-box {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--primary, #005bbf) 28%, transparent);
  background: color-mix(in srgb, var(--primary, #005bbf) 6%, #fff);
}
.formula-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary, #005bbf);
  margin-bottom: 4px;
}
.formula-body {
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color: var(--on-surface, #1a1c1e);
  line-height: 1.5;
  word-break: break-all;
}
.hint {
  font-size: 11px;
  color: var(--mut);
  line-height: 1.55;
  margin: 8px 0 0;
}
.preview {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  background: linear-gradient(180deg, #fcfcfd, #f7f8fa);
}
.inv-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 11px;
  color: var(--mut);
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--line);
  margin-bottom: 10px;
}
.inv-title {
  text-align: center;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.2em;
  margin-bottom: 12px;
}
.preview-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 8px;
}
.preview-row .lbl {
  font-size: 11px;
  color: var(--mut);
}
.preview-row .val {
  font-size: 13px;
}
.preview-totals {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
}
.preview-totals .row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 3px 0;
  font-variant-numeric: tabular-nums;
}
.preview-totals .row.total {
  font-size: 15px;
  font-weight: 700;
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px solid var(--line);
}
.push-log {
  font-size: 12px;
  line-height: 1.8;
}
.drawer-foot {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--line);
  background: #fbfcfd;
  flex-wrap: wrap;
}
.empty-drawer {
  padding: 40px 20px;
  text-align: center;
  color: var(--mut);
  font-size: 13px;
}
.modal {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.modal-card {
  background: #fff;
  border-radius: 12px;
  width: min(560px, 92vw);
  max-height: 85vh;
  overflow: auto;
}
.modal-h {
  padding: 18px 20px 10px;
  border-bottom: 1px solid #f1f4f8;
}
.modal-h .ttl {
  font-size: 16px;
  font-weight: 700;
}
.modal-h .sub {
  font-size: 12px;
  color: var(--mut);
  margin-top: 4px;
}
.modal-b {
  padding: 14px 20px;
}
.modal-b .item {
  display: flex;
  justify-content: space-between;
  padding: 7px 0;
  font-size: 13px;
}
.modal-b .item span {
  color: var(--mut);
}
.warn-line {
  margin-top: 10px;
  background: var(--warn-soft);
  border: 1px solid #f5dca0;
  color: var(--warn);
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.55;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 12px;
  font-size: 12px;
  color: var(--mut);
}
.field textarea {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
  color: var(--ink);
  resize: vertical;
}
.modal-f {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--line);
  background: #fbfcfd;
}
.push-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.push-chip {
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 16px;
  font-size: 12px;
  background: #fff;
  cursor: pointer;
}
.push-chip.on {
  background: var(--brand-soft);
  border-color: var(--brand);
  color: var(--brand);
}
.modal-card.lg {
  width: min(720px, 94vw);
}
.danger-line {
  margin-top: 12px;
  background: var(--err-soft);
  border: 1px solid #f4c8ca;
  color: #a4302f;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.55;
}
.field select,
.field-sel {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
  color: var(--ink);
  width: 100%;
  margin-top: 6px;
  background: #fff;
}
.title-pick,
.amt-pick {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.title-opt {
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  text-align: left;
  gap: 10px;
}
.title-opt:hover {
  border-color: var(--brand);
  background: var(--brand-soft);
}
.title-opt.sel {
  border-color: var(--brand);
  background: var(--brand-soft);
}
.title-opt .meta {
  font-size: 11px;
  color: var(--mut);
  margin-top: 2px;
}
.title-opt .check {
  color: var(--brand);
  font-weight: 600;
  font-size: 12px;
  flex-shrink: 0;
}
.title-opt .check.warn {
  color: var(--warn);
}
.step {
  display: flex;
  gap: 10px;
  padding: 10px 0;
  font-size: 13px;
  align-items: flex-start;
}
.step .num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--brand-soft);
  color: var(--brand);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}
.step .body {
  flex: 1;
  min-width: 0;
}
.step .body small {
  color: var(--mut);
  font-size: 11px;
  display: block;
  margin-top: 2px;
}
.history {
  margin-top: 14px;
  padding: 14px 18px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.history .ttl {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--ink);
}
.hist-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 0;
  font-size: 12px;
  color: var(--ink);
  border-bottom: 1px dashed #f1f4f8;
  line-height: 1.5;
}
.hist-item:last-child {
  border-bottom: 0;
}
.hist-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ok);
  margin-top: 5px;
  flex-shrink: 0;
}
.hist-item .time {
  color: var(--mut);
  font-variant-numeric: tabular-nums;
  min-width: 72px;
}
.hist-item .who {
  color: var(--brand);
  font-weight: 600;
}
.foot-note {
  margin-top: 12px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 12px;
  color: var(--mut);
  line-height: 1.7;
}
.badge.gray {
  background: #f1f4f8;
  color: #9aa3b2;
}
@media (max-width: 1100px) {
  .kpi-row {
    grid-template-columns: 1fr 1fr;
  }
  .split {
    grid-template-columns: 1fr;
  }
}
</style>
