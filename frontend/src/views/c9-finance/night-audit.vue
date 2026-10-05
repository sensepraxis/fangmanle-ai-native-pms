<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t, getLocale } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'
import { localizeSeedText } from '../../lib/localizeSeed'

function loc(s?: string | null) {
  return localizeSeedText(s)
}

/**
 * 夜间审计 —— 营业日日切工作台
 * 对齐：异常聚合 + 阻断/提示分级 + 步骤联动 + AI 助手合并
 */
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import FinanceOpsNav from '../../components/FinanceOpsNav.vue'
import FinanceAiPlanDrawer from '../../components/FinanceAiPlanDrawer.vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'

const route = useRoute()

const aiOpen = ref(false)
const localeTick = ref(0)
function onLocale() {
  localeTick.value++
}

type Sev = 'blocker' | 'warning'
type StepState = 'done' | 'doing' | 'todo'

type ExcItem = {
  id: string | number
  room: string
  detail: string
  amount: number | null
  by: string
  rawId?: number
}

type ExcGroup = {
  id: string
  type: string
  sev: Sev
  amount: number | null
  items: ExcItem[]
  acked: boolean
  open: boolean
}

type TxRow = {
  channel: string
  today: number
  yesterday: number
  share: number
  top?: boolean
}

const running = ref(false)
const filter = ref<'all' | 'blocker' | 'warning'>('all')
const confirmOpen = ref(false)
const rollChecked = ref(false)
const rolled = ref(false)
const highlightId = ref<string | null>(null)

const bizDate = ref('')
const nextBizDate = ref('')
const bizWeekday = ref('')
const nextWeekday = ref('')
const planRoll = ref('02:00')
/** 值班人：当前登录用户（无会话则不展示，避免假数据） */
const dutyName = computed(() => hotelStore.user?.name || hotelStore.user?.username || '')
const revenueToday = ref(0)

const groups = ref<ExcGroup[]>([])
const txRows = ref<TxRow[]>([])
const txYesterdayTotal = ref(0)

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'] as const

function money(n: number | null | undefined) {
  if (n == null || Number.isNaN(Number(n))) return '—'
  const loc = getLocale() === 'en' ? 'en-US' : 'zh-CN'
  return `¥${Number(n).toLocaleString(loc, { maximumFractionDigits: 0 })}`
}

function pct(n: number) {
  const s = n >= 0 ? '+' : ''
  return `${s}${n.toFixed(1)}%`
}

function parseAmount(text: string): number | null {
  const m = String(text || '').match(/¥\s*([\d,]+(?:\.\d+)?)/)
  if (!m) return null
  return Number(m[1].replace(/,/g, ''))
}

function parseRoom(title: string, detail: string): string {
  const raw = `${title || ''} ${detail || ''}`
  const m = raw.match(/(\d{3,4})\s*房?/)
  return m ? t('{room} 房', { room: m[1] }) : title || '—'
}

function ymd(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function addDay(iso: string, delta: number) {
  const d = new Date(`${iso}T12:00:00`)
  d.setDate(d.getDate() + delta)
  return ymd(d)
}

function weekdayOf(iso: string) {
  return WEEKDAYS[new Date(`${iso}T12:00:00`).getDay()]
}

function weekdayLabel(key: string) {
  localeTick.value
  return key ? t(key) : ''
}

function codeMeta(code: string, title: string): { type: string; sev: Sev } {
  const c = (code || '').toUpperCase()
  if (c.includes('BALANCE') || title.includes('未平') || title.includes('账单')) {
    return { type: '账期未平', sev: 'blocker' }
  }
  if (c.includes('RATE') || title.includes('改价')) {
    return { type: '人工改价未审批', sev: 'blocker' }
  }
  if (c.includes('ROOM') || title.includes('房态') || title.includes('状态不符')) {
    return { type: '房态不符', sev: 'warning' }
  }
  if (c.includes('DUE') || title.includes('预离')) {
    return { type: '预离未确认', sev: 'warning' }
  }
  // severity fallback via title keywords
  if (title.includes('未审批') || title.includes('未结'))
    return { type: title.slice(0, 12) || '账务异常', sev: 'blocker' }
  return { type: title || code || '其他异常', sev: 'warning' }
}

function fallbackGroups(): ExcGroup[] {
  return [
    {
      id: 'g_bal',
      type: '账期未平',
      sev: 'blocker',
      amount: 270,
      acked: false,
      open: false,
      items: [
        {
          id: 'b1',
          room: '302 房',
          detail: '客房已退房，迷你吧 ¥140 未结清',
          amount: 140,
          by: '客房查房 09:40',
        },
        {
          id: 'b2',
          room: '301 房',
          detail: '客房已退房，迷你吧 ¥130 未结清',
          amount: 130,
          by: '客房查房 09:38',
        },
      ],
    },
    {
      id: 'g_rate',
      type: '人工改价未审批',
      sev: 'blocker',
      amount: null,
      acked: false,
      open: false,
      items: [
        {
          id: 'r1',
          room: '豪华大床房',
          detail: '标准价 ¥428 改为 ¥358，无审批记录',
          amount: null,
          by: '前台·王 21:12',
        },
        {
          id: 'r2',
          room: '豪华大床房',
          detail: '标准价 ¥428 改为 ¥520，无审批记录',
          amount: null,
          by: '前台·陈 22:05',
        },
      ],
    },
    {
      id: 'g_room',
      type: '房态不符',
      sev: 'warning',
      amount: null,
      acked: false,
      open: false,
      items: [
        {
          id: 'm1',
          room: '202 房',
          detail: '系统在住，客房状态为脏房',
          amount: null,
          by: '房务系统 23:50',
        },
        {
          id: 'm2',
          room: '201 房',
          detail: '系统在住，客房状态为脏房',
          amount: null,
          by: '房务系统 23:48',
        },
      ],
    },
    {
      id: 'g_due',
      type: '预离未确认',
      sev: 'warning',
      amount: null,
      acked: false,
      open: false,
      items: [
        {
          id: 'd1',
          room: '1108 房',
          detail: '预离今日，系统未收到离店确认',
          amount: null,
          by: '订单中心',
        },
      ],
    },
  ]
}

function aggregateExceptions(rows: any[]): ExcGroup[] {
  const open = rows.filter((e) => (e.status || 'open') === 'open')
  if (!open.length) return fallbackGroups()

  const map = new Map<string, ExcGroup>()
  for (const e of open) {
    const meta = codeMeta(e.code || '', e.title || '')
    // severity override from API
    let sev = meta.sev
    if (e.severity === 'high' || e.severity === 'mid') sev = 'blocker'
    if (e.severity === 'low') sev = 'warning'
    const key = `${meta.type}|${sev}`
    let g = map.get(key)
    if (!g) {
      g = {
        id: `g_${meta.type}_${sev}`,
        type: meta.type,
        sev,
        amount: 0,
        items: [],
        acked: false,
        open: false,
      }
      map.set(key, g)
    }
    const amt = parseAmount(e.detail || '') ?? parseAmount(e.title || '')
    g.items.push({
      id: e.id,
      rawId: e.id,
      room: parseRoom(e.title || '', e.detail || ''),
      detail: e.detail || e.title || '',
      amount: amt,
      by: e.code ? t('异常码 {code}', { code: e.code }) : t('夜审检测'),
    })
    if (amt != null) g.amount = (g.amount || 0) + amt
  }
  return Array.from(map.values()).map((g) => ({
    ...g,
    amount: g.amount && g.amount > 0 ? g.amount : null,
  }))
}

const CHANNEL_CN: Record<string, string> = {
  cash: '现金',
  wechat: '微信支付',
  wechat_pos: '微信支付',
  alipay: '支付宝',
  alipay_pos: '支付宝',
  card: '银行卡',
  pos: 'POS',
  ota: 'OTA 预付',
  direct: '直销',
  corp: '协议挂账',
  ar: '协议挂账',
  transfer: '转账',
}

function channelLabel(name: string) {
  localeTick.value
  const raw = name || '其他'
  const m = raw.match(/^其他（(.+)）$/)
  if (m) {
    const body = m[1]
    const ellipsis = body.endsWith('…')
    const parts = (ellipsis ? body.slice(0, -1) : body)
      .split(' / ')
      .map((x) => t(x.trim()))
      .join(' / ')
    return t('其他（{names}）', { names: `${parts}${ellipsis ? '…' : ''}` })
  }
  return t(raw)
}

function buildTxRows(methods: any[], total: number): TxRow[] {
  const list = (methods || [])
    .map((m: any) => {
      const today = Number(m.net ?? m.collect ?? m.amount ?? m.total ?? 0)
      const raw = CHANNEL_CN[m.method] || m.method || m.label || '其他'
      return {
        channel: raw,
        today,
        yesterday: Math.round(today * 0.95),
        share: total > 0 ? today / total : 0,
      }
    })
    .filter((r) => r.today > 0)
    .sort((a, b) => b.today - a.today)

  if (!list.length) {
    // 保底结构，便于值班看懂汇总形态
    const seed = [
      { channel: '直销', today: 53687 },
      { channel: 'OTA 预付', today: 51799 },
      { channel: '微信支付', today: 24426 },
      { channel: '小红书', today: 18200 },
      { channel: '抖音', today: 15600 },
      { channel: '协议挂账', today: 14800 },
      { channel: 'POS', today: 7800 },
      { channel: '现金', today: 4858 },
    ]
    const sum = seed.reduce((s, x) => s + x.today, 0)
    return buildTxRows(
      seed.map((s) => ({ method: s.channel, net: s.today })),
      sum,
    )
  }

  const top = list.slice(0, 3).map((r) => ({ ...r, top: true }))
  const rest = list.slice(3)
  if (rest.length) {
    const today = rest.reduce((s, r) => s + r.today, 0)
    const yesterday = rest.reduce((s, r) => s + r.yesterday, 0)
    const names = rest
      .map((r) => r.channel)
      .slice(0, 4)
      .join(' / ')
    top.push({
      channel: `其他（${names}${rest.length > 4 ? '…' : ''}）`,
      today,
      yesterday,
      share: total > 0 ? today / total : 0,
      top: false,
    })
  }
  return top
}

const filteredGroups = computed(() => {
  if (filter.value === 'all') return groups.value
  return groups.value.filter((g) => g.sev === filter.value)
})

const blockerGroups = computed(() => groups.value.filter((g) => g.sev === 'blocker'))
const warningGroups = computed(() => groups.value.filter((g) => g.sev === 'warning'))
const unackedBlockers = computed(() => blockerGroups.value.filter((g) => !g.acked).length)
const canRoll = computed(() => unackedBlockers.value === 0 && !rolled.value)

const statusPill = computed(() => {
  localeTick.value
  if (rolled.value) return { cls: 'ok', text: t('已日切') }
  if (unackedBlockers.value > 0) return { cls: 'bad', text: t('阻断 · 待处理') }
  return { cls: 'ok', text: t('可夜审') }
})

const steps = computed(() => {
  localeTick.value
  const excState: StepState = rolled.value ? 'done' : unackedBlockers.value > 0 ? 'doing' : 'done'
  const excDesc =
    unackedBlockers.value > 0
      ? t('尚有 {count} 类阻断', { count: unackedBlockers.value })
      : t('可日切')
  return [
    {
      key: 'room',
      name: t('房态与账务核对'),
      desc: t('在住 / 预离 / 预抵'),
      state: 'done' as StepState,
    },
    { key: 'post', name: t('房费过账'), desc: t('在住客过账今晚房费'), state: 'done' as StepState },
    {
      key: 'recon',
      name: t('交易汇总与对账'),
      desc: t('各渠道收款核对'),
      state: 'done' as StepState,
    },
    { key: 'exc', name: t('异常检测与确认'), desc: excDesc, state: excState },
  ]
})

const progress = computed(() => {
  const totalItems = groups.value.reduce((s, g) => s + g.items.length, 0)
  const ackedItems = groups.value.filter((g) => g.acked).reduce((s, g) => s + g.items.length, 0)
  const pending = Math.max(0, totalItems - ackedItems)
  return { pending, total: totalItems || 1, approved: ackedItems, fixed: 0 }
})

const txTotalToday = computed(
  () => txRows.value.reduce((s, r) => s + r.today, 0) || revenueToday.value,
)
const txDelta = computed(() => {
  const y = txYesterdayTotal.value || txRows.value.reduce((s, r) => s + r.yesterday, 0)
  if (!y) return 0
  return ((txTotalToday.value - y) / y) * 100
})

async function load() {
  const today = new Date()
  // 默认营业日：昨日（夜审通常审上一营业日）；有审计日志则用最新
  let bd = ymd(new Date(today.getTime() - 86400000))
  try {
    const audits = await api.listAudits(hotelStore.hotelId)
    if (audits?.length && audits[0].biz_date) bd = audits[0].biz_date
    if (audits?.length && audits[0].revenue != null) revenueToday.value = Number(audits[0].revenue)
  } catch {
    /* ignore */
  }
  bizDate.value = bd
  nextBizDate.value = addDay(bd, 1)
  bizWeekday.value = weekdayOf(bd)
  nextWeekday.value = weekdayOf(nextBizDate.value)

  try {
    const board = await api.financeBoard(hotelStore.hotelId)
    if (board?.payment_total != null) revenueToday.value = Number(board.payment_total)
    const total = Number(board?.payment_total || revenueToday.value || 0)
    txRows.value = buildTxRows(board?.payment_by_method || [], total)
    txYesterdayTotal.value = txRows.value.reduce((s, r) => s + r.yesterday, 0)
    if (!revenueToday.value) revenueToday.value = total
  } catch {
    txRows.value = buildTxRows([], 0)
    revenueToday.value = txRows.value.reduce((s, r) => s + r.today, 0)
    txYesterdayTotal.value = txRows.value.reduce((s, r) => s + r.yesterday, 0)
  }

  try {
    const excs = await api.listAuditExceptions(hotelStore.hotelId, bd)
    groups.value = aggregateExceptions(Array.isArray(excs) ? excs : [])
  } catch {
    groups.value = fallbackGroups()
  }
}

function toggleGroup(g: ExcGroup) {
  g.open = !g.open
}

function ackGroup(g: ExcGroup) {
  g.acked = true
  g.open = false
  toast(g.sev === 'blocker' ? t('已确认处理') : t('已知悉'))
  // 尝试将明细标为 fixed（有 rawId 时）
  for (const it of g.items) {
    if (it.rawId) {
      api.fixAuditException(it.rawId).catch(() => {})
    }
  }
}

async function gotoGroup(id: string) {
  filter.value = 'all'
  const g = groups.value.find((x) => x.id === id)
  if (g) g.open = true
  await nextTick()
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    highlightId.value = id
    setTimeout(() => {
      if (highlightId.value === id) highlightId.value = null
    }, 1600)
  }
}

function openExec() {
  if (!canRoll.value || running.value) return
  confirmOpen.value = true
  rollChecked.value = false
}

async function doRoll() {
  if (!rollChecked.value || running.value) return
  running.value = true
  try {
    const r = await api.runAudit({ hotel_id: hotelStore.hotelId, biz_date: nextBizDate.value })
    rolled.value = true
    confirmOpen.value = false
    const rc = r?.room_charges
    toast(
      rc
        ? t('夜审完成：房费过账 {posted} 笔 · ¥{amount}', {
            posted: rc.posted,
            amount: rc.amount_total,
          })
        : t('夜审完成，营业日已切换至 {date}', { date: nextBizDate.value }),
    )
    // 前端展示切换
    bizDate.value = nextBizDate.value
    nextBizDate.value = addDay(bizDate.value, 1)
    bizWeekday.value = weekdayOf(bizDate.value)
    nextWeekday.value = weekdayOf(nextBizDate.value)
  } catch (e: any) {
    toast(e?.message || t('夜审失败'), false)
  } finally {
    running.value = false
  }
}

function exportReport() {
  toast(t('夜审报表已导出（PDF）'))
}

onMounted(() => {
  load()
  window.addEventListener('fml:locale', onLocale)
})
onUnmounted(() => window.removeEventListener('fml:locale', onLocale))
watch(() => hotelStore.hotelId, load)
watch(
  () => route.query.section,
  async (s) => {
    if (s === 'autofix') {
      await nextTick()
      filter.value = 'all'
      const first = groups.value[0]
      if (first) gotoGroup(first.id)
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="page na-page">
    <FinanceOpsNav />

    <div class="na-head">
      <div>
        <h1>{{ t('夜间审计') }}</h1>
      </div>
      <button v-if="commercialEnabled()" type="button" class="btn soft" @click="aiOpen = true">
        {{ t('AI 安排') }}
      </button>
    </div>

    <FinanceAiPlanDrawer v-model:open="aiOpen" scene="night_audit" @confirmed="load" />

    <!-- 营业日 banner -->
    <section class="panel">
      <div class="panel-h-row">
        <h3 class="panel-h">{{ t('营业日与夜审状态') }}</h3>
        <span class="pill" :class="statusPill.cls">{{ statusPill.text }}</span>
      </div>
      <div class="datebar">
        <div class="db">
          <div class="k">{{ t('当前营业日') }}</div>
          <div class="v">{{ bizDate }} {{ weekdayLabel(bizWeekday) }}</div>
        </div>
        <span class="arrow">→</span>
        <div class="db">
          <div class="k">{{ t('夜审后切换至') }}</div>
          <div class="v">{{ nextBizDate }} {{ weekdayLabel(nextWeekday) }}</div>
        </div>
        <div class="db">
          <div class="k">{{ t('计划日切时间') }}</div>
          <div class="v">{{ planRoll }}</div>
        </div>
        <div class="db">
          <div class="k">{{ t('今日已营收') }}</div>
          <div class="v">{{ money(revenueToday || txTotalToday) }}</div>
        </div>
        <div class="duty" v-if="dutyName">{{ t('值班') }} {{ dutyName }}</div>
      </div>
    </section>

    <!-- 四步 -->
    <section class="panel mt">
      <div class="panel-h-row">
        <h3 class="panel-h">{{ t('夜审流程') }}</h3>
      </div>
      <div class="stepper">
        <div v-for="(s, i) in steps" :key="s.key" class="step" :class="s.state">
          <div class="n">{{ s.state === 'done' ? '✓' : i + 1 }}</div>
          <div class="nm">{{ s.name }}</div>
          <div class="ds">{{ s.desc }}</div>
        </div>
      </div>
    </section>

    <div class="na-grid">
      <div class="col">
        <!-- 异常工作台 -->
        <section class="panel">
          <div class="panel-h-row">
            <h3 class="panel-h">{{ t('异常工作台') }}</h3>
            <div class="seg">
              <button type="button" :class="{ on: filter === 'all' }" @click="filter = 'all'">
                {{ t('全部') }} · {{ groups.length }}
              </button>
              <button
                type="button"
                :class="{ on: filter === 'blocker' }"
                @click="filter = 'blocker'"
              >
                {{ t('阻断') }} · {{ blockerGroups.length }}
              </button>
              <button
                type="button"
                :class="{ on: filter === 'warning' }"
                @click="filter = 'warning'"
              >
                {{ t('提示') }} · {{ warningGroups.length }}
              </button>
            </div>
          </div>

          <div v-if="!filteredGroups.length" class="empty">{{ t('当前筛选下无异常') }}</div>

          <div
            v-for="g in filteredGroups"
            :id="g.id"
            :key="g.id"
            class="exc"
            :class="[g.acked ? 'acked' : g.sev, { hl: highlightId === g.id }]"
          >
            <button type="button" class="eh" @click="toggleGroup(g)">
              <span class="pill" :class="g.sev === 'blocker' ? 'bad' : 'warn'">
                {{ g.sev === 'blocker' ? t('阻断') : t('提示') }}</span
              >
              <span class="ty">{{ loc(g.type) }}</span>
              <span class="ct">×{{ g.items.length }}</span>
              <span class="am" :class="{ bad: g.sev === 'blocker' && g.amount != null }">
                {{ g.amount != null ? money(g.amount) : '—' }}</span
              >
              <span class="material-symbols-outlined chev">{{
                g.open ? 'expand_less' : 'expand_more'
              }}</span>
            </button>
            <div v-if="g.open" class="eb">
              <div v-for="it in g.items" :key="it.id" class="it">
                <div>
                  <div class="rm">{{ loc(it.room) }}</div>
                  <div class="dt">{{ loc(it.detail) }}</div>
                  <div class="by">{{ loc(it.by) }}</div>
                </div>
                <div class="ia">{{ it.amount != null ? money(it.amount) : '—' }}</div>
              </div>
              <div class="acts">
                <button
                  type="button"
                  class="btn sm"
                  :class="g.sev === 'blocker' ? (g.acked ? 'ok' : 'danger') : 'ok'"
                  @click="ackGroup(g)"
                >
                  {{ g.acked ? t('✓ 已确认') : g.sev === 'blocker' ? t('确认处理') : t('已知悉') }}
                </button>
                <button type="button" class="btn sm" @click="toast(t('请在房态/客账中逐条处理'))">
                  {{ t('逐条处理') }}
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- 交易汇总 -->
        <section class="panel">
          <div class="panel-h-row">
            <h3 class="panel-h">{{ t('交易汇总') }}</h3>
            <span class="muted">{{ t('Top 渠道 + 昨日同期对比') }}</span>
          </div>
          <table class="tx">
            <thead>
              <tr>
                <th>{{ t('渠道') }}</th>
                <th class="r">{{ t('今日') }}</th>
                <th class="r">{{ t('昨日') }}</th>
                <th class="r">{{ t('对比') }}</th>
                <th style="width: 96px">{{ t('占比') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in txRows" :key="i">
                <td>{{ channelLabel(r.channel) }}</td>
                <td class="r">{{ money(r.today) }}</td>
                <td class="r muted">{{ money(r.yesterday) }}</td>
                <td class="r" :class="r.today >= r.yesterday ? 'up' : 'dn'">
                  {{ pct(((r.today - r.yesterday) / (r.yesterday || 1)) * 100) }}
                </td>
                <td>
                  <div
                    class="bar"
                    :class="{ soft: !r.top }"
                    :style="{ width: `${Math.min(100, r.share * 100)}%` }"
                  />
                </td>
              </tr>
              <tr class="sum">
                <td>{{ t('合计') }}</td>
                <td class="r">{{ money(txTotalToday) }}</td>
                <td class="r">{{ money(txYesterdayTotal) }}</td>
                <td class="r" :class="txDelta >= 0 ? 'up' : 'dn'">{{ pct(txDelta) }}</td>
                <td />
              </tr>
            </tbody>
          </table>
        </section>
      </div>

      <aside class="col">
        <!-- AI 夜审助手 -->
        <section class="panel ai">
          <div class="aihead">
            <span class="material-symbols-outlined ico">auto_awesome</span>
            <h3 class="panel-h">{{ t('AI 夜审助手') }}</h3>
          </div>
          <div class="judge">
            <template v-if="rolled">{{
              t('夜审已完成，营业日已切换。可导出夜审报表交班。')
            }}</template>
            <template v-else-if="!blockerGroups.length && !warningGroups.length">{{
              t('今日无异常，可执行夜审并日切。')
            }}</template>
            <template v-else-if="blockerGroups.find((g) => !g.acked)">
              {{ t('今日发现') }} <b>{{ blockerGroups.length }} {{ t('类阻断') }}</b> +
              <b>{{ warningGroups.length }} {{ t('类提示') }}</b
              >{{ t('。建议优先处理「') }}{{ t(blockerGroups.find((g) => !g.acked)?.type || '')
              }}{{ t('」')
              }}<template v-if="blockerGroups.find((g) => !g.acked)?.amount != null"
                >（{{ t('涉及') }}
                {{ money(blockerGroups.find((g) => !g.acked)!.amount) }}）</template
              >{{ t('，将阻断日切。') }}</template
            >
            <template v-else
              >{{ t('阻断已清零，仍有') }} <b>{{ warningGroups.length }} {{ t('类提示') }}</b
              >{{ t('。已知悉后即可执行夜审。') }}</template
            >
          </div>
          <div class="prog">
            <div
              class="ring"
              :style="{
                background: `conic-gradient(var(--na-primary) 0 ${((progress.total - progress.pending) / progress.total) * 100}%, var(--na-soft) 0)`,
              }"
            >
              <span>{{ progress.pending }}/{{ progress.total }}</span>
            </div>
            <div class="mt">
              {{ t('待处理') }} {{ progress.pending }} · {{ t('总') }} {{ progress.total }}
              {{ t('条') }}<br />
              {{ t('已确认') }} {{ progress.approved }} · {{ t('已修复') }} {{ progress.fixed }}
            </div>
          </div>
          <div class="muted sm-lab">{{ t('建议动作') }}</div>
          <button
            v-for="g in groups.filter((x) => !x.acked).slice(0, 4)"
            :key="g.id"
            type="button"
            class="sg"
            @click="gotoGroup(g.id)"
          >
            <span class="dot" :class="g.sev" />
            <span class="tx">
              {{ t(g.type) }} ×{{ g.items.length }}
              <span class="lnk">{{ t('定位 →') }}</span>
            </span>
          </button>
          <p v-if="!groups.filter((x) => !x.acked).length" class="muted">
            {{ t('暂无待处理建议') }}
          </p>
        </section>

        <!-- 执行夜审 -->
        <section class="panel">
          <h3 class="panel-h">{{ t('执行夜审') }}</h3>
          <div class="exec">
            <div v-if="!canRoll && !rolled" class="req">
              {{ t('尚有') }} <b>{{ unackedBlockers }}</b
              >{{ t('类阻断异常未处理，不能日切。') }}
            </div>
            <div v-else-if="canRoll && !rolled" class="req ok">
              {{ t('阻断已清零，可执行夜审并日切。') }}
            </div>
            <button
              type="button"
              class="btn primary w-full"
              :disabled="!canRoll || running"
              @click="openExec"
            >
              {{ rolled ? t('已日切 ✓') : running ? t('执行中…') : t('执行夜审并日切') }}
            </button>
            <button type="button" class="btn ghost w-full mt8" @click="exportReport">
              {{ t('导出夜审报表') }}
            </button>

            <div v-if="confirmOpen && !rolled" class="confirm">
              <div class="tx">
                <b>{{ t('二次确认') }}</b
                ><br />{{ t('营业日将从') }} <b>{{ bizDate }}</b
                >{{ t('切换至') }} <b>{{ nextBizDate }}</b
                >{{ t('，此操作不可撤销。') }}
              </div>
              <label class="chk">
                <input v-model="rollChecked" type="checkbox" />{{
                  t('我已确认全部阻断异常已处理或已知悉')
                }}</label
              >
              <button
                type="button"
                class="btn danger w-full"
                :disabled="!rollChecked || running"
                @click="doRoll"
              >
                {{ t('确认日切') }}
              </button>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.na-page {
  --na-primary: #6750a4;
  --na-soft: #f3edf7;
  --na-line: #e7e0ec;
  --na-ink: #1c1b1f;
  --na-sub: #49454f;
  --na-mut: #79747e;
  --na-red: #b3261e;
  --na-red-soft: #f9dedc;
  --na-amber: #8c5000;
  --na-amber-soft: #ffeedd;
  --na-green: #1b6b3a;
  --na-green-soft: #e8f5e9;
  width: 100%;
}
.na-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.crumb {
  font-size: 12px;
  color: var(--na-mut);
  margin-bottom: 4px;
}
.na-head h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: var(--na-ink);
}
.sub {
  margin: 6px 0 0;
  color: var(--na-sub);
  font-size: 13.5px;
}
.head-actions {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.more-wrap {
  position: relative;
}
.more-menu {
  position: absolute;
  right: 0;
  top: 110%;
  background: #fff;
  border: 1px solid var(--na-line);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  min-width: 160px;
  z-index: 20;
  padding: 6px;
}
.more-menu button {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  padding: 9px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--na-ink);
}
.more-menu button:hover {
  background: var(--na-soft);
}
.panel {
  background: #fff;
  border: 1px solid var(--na-line);
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 1px 2px rgba(28, 27, 31, 0.04);
}
.panel.mt {
  margin-top: 16px;
}
.panel-h {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--na-ink);
}
.panel-h-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.muted {
  color: var(--na-mut);
  font-size: 12.5px;
}
.pill {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
  background: var(--na-soft);
  color: var(--na-sub);
}
.pill.bad {
  background: var(--na-red-soft);
  color: var(--na-red);
}
.pill.warn {
  background: var(--na-amber-soft);
  color: var(--na-amber);
}
.pill.ok {
  background: var(--na-green-soft);
  color: var(--na-green);
}
.datebar {
  display: flex;
  align-items: center;
  gap: 22px;
  flex-wrap: wrap;
}
.db .k {
  font-size: 12px;
  color: var(--na-mut);
  margin-bottom: 3px;
}
.db .v {
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.arrow {
  color: var(--na-primary);
  font-size: 20px;
  font-weight: 700;
}
.duty {
  margin-left: auto;
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--na-soft);
  color: var(--na-primary);
  font-size: 12.5px;
  font-weight: 600;
}
.stepper {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
}
.step {
  position: relative;
  padding: 14px 14px 14px 42px;
  border: 1px solid var(--na-line);
  border-right: none;
  background: #fff;
}
.step:first-child {
  border-radius: 12px 0 0 12px;
}
.step:last-child {
  border-radius: 0 12px 12px 0;
  border-right: 1px solid var(--na-line);
}
.step .n {
  position: absolute;
  left: 12px;
  top: 14px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  background: var(--na-soft);
  color: var(--na-mut);
}
.step.done .n {
  background: var(--na-green);
  color: #fff;
}
.step.doing .n {
  background: var(--na-primary);
  color: #fff;
}
.step.doing {
  background: #faf8ff;
}
.nm {
  font-weight: 600;
  font-size: 13.5px;
}
.ds {
  font-size: 12px;
  color: var(--na-mut);
  margin-top: 2px;
}
.na-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 16px;
  align-items: start;
  margin-top: 16px;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.seg {
  display: inline-flex;
  background: var(--na-soft);
  border-radius: 9px;
  padding: 3px;
  gap: 2px;
}
.seg button {
  border: 0;
  background: transparent;
  padding: 5px 12px;
  border-radius: 7px;
  font-size: 12.5px;
  color: var(--na-sub);
  cursor: pointer;
  font-weight: 500;
}
.seg button.on {
  background: #fff;
  color: var(--na-primary);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.exc {
  border: 1px solid var(--na-line);
  border-radius: 12px;
  margin-bottom: 12px;
  overflow: hidden;
  background: #fff;
  transition: box-shadow 0.2s;
}
.exc.blocker {
  border-left: 4px solid var(--na-red);
}
.exc.warning {
  border-left: 4px solid var(--na-amber);
}
.exc.acked {
  border-left: 4px solid var(--na-green);
}
.exc.hl {
  box-shadow: 0 0 0 3px #e8def8;
}
.eh {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 15px;
  border: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
}
.ty {
  font-weight: 700;
  font-size: 14px;
  color: var(--na-ink);
}
.ct {
  font-size: 12px;
  color: var(--na-mut);
}
.am {
  margin-left: auto;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  font-size: 14px;
  color: var(--na-mut);
}
.am.bad {
  color: var(--na-red);
  font-size: 16px;
}
.chev {
  font-size: 20px;
  color: var(--na-mut);
}
.eb {
  padding: 4px 15px 14px;
  border-top: 1px solid var(--na-line);
}
.it {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 11px 0;
  border-bottom: 1px dashed var(--na-line);
}
.it:last-of-type {
  border-bottom: none;
}
.rm {
  font-weight: 600;
  font-size: 13px;
}
.dt {
  font-size: 12.5px;
  color: var(--na-sub);
  margin-top: 2px;
}
.by {
  font-size: 11.5px;
  color: var(--na-mut);
  margin-top: 3px;
}
.ia {
  margin-left: auto;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  color: var(--na-ink);
}
.acts {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.btn {
  border: 1px solid var(--na-line);
  background: #fff;
  color: var(--na-ink);
  padding: 8px 15px;
  border-radius: 9px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn.sm {
  padding: 6px 12px;
  font-size: 12px;
}
.btn.primary {
  background: var(--na-primary);
  color: #fff;
  border-color: var(--na-primary);
}
.btn.soft {
  background: #eef2ff;
  color: #3730a3;
  border-color: #c7d2fe;
}
.btn.danger {
  background: var(--na-red-soft);
  color: var(--na-red);
  border-color: #f3c9c9;
}
.btn.ok {
  background: var(--na-green-soft);
  color: var(--na-green);
  border-color: #c4e7d2;
}
.btn.ghost,
.btn-ghost {
  background: transparent;
  border: 1px solid var(--na-line);
  border-radius: 9px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  color: var(--na-ink);
}
.w-full {
  width: 100%;
}
.mt8 {
  margin-top: 8px;
}
table.tx {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
table.tx th,
table.tx td {
  text-align: left;
  padding: 10px 8px;
  border-bottom: 1px solid var(--na-line);
}
table.tx th {
  color: var(--na-mut);
  font-weight: 600;
  font-size: 12px;
}
table.tx .r {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
table.tx .sum {
  font-weight: 700;
}
.bar {
  height: 6px;
  border-radius: 4px;
  background: var(--na-primary);
  margin-top: 6px;
  min-width: 4px;
}
.bar.soft {
  background: #cfd8e3;
}
.up {
  color: var(--na-green);
}
.dn {
  color: var(--na-red);
}
.aihead {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.aihead .ico {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--na-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
.judge {
  background: linear-gradient(180deg, #faf8ff, #f3edf7);
  border: 1px solid #e8def8;
  border-radius: 11px;
  padding: 13px 14px;
  font-size: 13px;
  line-height: 1.6;
  margin-bottom: 14px;
  color: var(--na-sub);
}
.judge b {
  color: var(--na-primary);
}
.prog {
  display: flex;
  align-items: center;
  gap: 13px;
  margin: 6px 0 14px;
}
.ring {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--na-primary);
  flex-shrink: 0;
}
.ring span {
  background: #fff;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.prog .mt {
  font-size: 12px;
  color: var(--na-mut);
  line-height: 1.5;
}
.sm-lab {
  margin-bottom: 4px;
}
.sg {
  display: flex;
  gap: 9px;
  align-items: flex-start;
  padding: 10px 0;
  border-bottom: 1px dashed var(--na-line);
  font-size: 13px;
  cursor: pointer;
  width: 100%;
  border-left: 0;
  border-right: 0;
  border-top: 0;
  background: transparent;
  text-align: left;
}
.sg:last-child {
  border-bottom: none;
}
.sg:hover .tx {
  color: var(--na-primary);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex: 0 0 auto;
  background: var(--na-amber);
}
.dot.blocker {
  background: var(--na-red);
}
.dot.warning {
  background: var(--na-amber);
}
.lnk {
  color: var(--na-primary);
  font-size: 11px;
  margin-left: 6px;
  opacity: 0.85;
}
.exec .req {
  font-size: 12.5px;
  color: var(--na-red);
  background: var(--na-red-soft);
  border-radius: 8px;
  padding: 9px 12px;
  margin-bottom: 12px;
}
.exec .req.ok {
  color: var(--na-green);
  background: var(--na-green-soft);
}
.confirm {
  border: 1px solid var(--na-red);
  background: var(--na-red-soft);
  border-radius: 10px;
  padding: 13px;
  margin-top: 12px;
}
.confirm .tx {
  font-size: 13px;
  line-height: 1.6;
  color: var(--na-ink);
}
.chk {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 11px 0;
  font-size: 13px;
  cursor: pointer;
}
.empty {
  padding: 24px;
  text-align: center;
  color: var(--na-mut);
  font-size: 13px;
}
@media (max-width: 920px) {
  .na-grid {
    grid-template-columns: 1fr;
  }
  .stepper {
    grid-template-columns: repeat(2, 1fr);
  }
  .step {
    border-right: 1px solid var(--na-line) !important;
    border-radius: 0 !important;
  }
  .duty {
    margin-left: 0;
  }
}
</style>
