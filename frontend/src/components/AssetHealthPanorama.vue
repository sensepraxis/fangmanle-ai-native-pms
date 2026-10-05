<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'
import { localizeSeedText } from '../lib/localizeSeed'

/**
 * 设备设施总览仪表盘（可嵌入首页）
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { ASSETS_EMPTY } from '../lib/assetsEmpty'
import { hotelStore } from '../store/hotel'

const props = defineProps<{
  board?: any | null
}>()

const emit = defineEmits<{
  scrollToList: []
  registerAsset: []
}>()

const router = useRouter()

const summary = ref<any[]>([])
const pendingWorkOrders = ref<PendingWo[]>([])
const alerts = ref<any[]>([])
const aiSuggestion = ref({ title: '', tag: '', body: '' })
const radarScores = ref<{ label: string; score: number }[]>([])
const budgetPts = ref<number[]>([])
const bubbles = ref<{ x: number; y: number; r: number; tone: string; name: string }[]>([])

const RADAR_CX = 150
const RADAR_CY = 138
const RADAR_R = 92
/** 行业健康分参考线 */
const RADAR_BASELINE = 75
const RADAR_RING_SCORES = [25, 50, 75, 100] as const
/** 折线图布局（Y 轴上限由数据动态计算） */
const BUDGET = {
  W: 320,
  H: 210,
  padL: 8,
  padR: 8,
  padT: 12,
  padB: 8,
  xTicks: [1, 5, 10, 15, 20, 25, 30],
}

const SUPPLY_CATS = /布草|消耗|易耗|耗材|linen|amenity/i

type PendingWo = {
  id: string
  maintId: number
  assetId: number
  assetName: string
  assetNo: string
  room: string
  title: string
  taskType: string
  dueDate: string
  status: string
  statusLabel: string
  statusCls: 'overdue' | 'doing' | 'scheduled'
  owner: string
}

const OPEN_MAINT_STATUS = new Set(['scheduled', 'overdue', 'doing'])

function roomLabel(room?: string, loc?: string, name?: string) {
  if (room) return t('{n} 房', { n: room })
  if (loc) return localizeSeedText(String(loc))
  return localizeSeedText(name) || t('公共区')
}

function maintStatusUi(status?: string) {
  if (status === 'overdue') return { label: t('已逾期'), cls: 'overdue' as const }
  if (status === 'doing') return { label: t('处理中'), cls: 'doing' as const }
  return { label: t('待执行'), cls: 'scheduled' as const }
}

function buildPendingWorkOrders(board: any): PendingWo[] {
  const assets = board?.assets || []
  const byId: Record<number, any> = {}
  for (const a of assets) {
    if (!isEquipmentAsset(a)) continue
    byId[a.id] = a
  }

  const list: PendingWo[] = []
  for (const m of board?.maintenance || []) {
    if (!OPEN_MAINT_STATUS.has(String(m.status || ''))) continue
    const a = byId[m.asset_id]
    if (!a) continue
    const ui = maintStatusUi(m.status)
    list.push({
      id: `WO-${m.id}`,
      maintId: Number(m.id),
      assetId: Number(m.asset_id),
      assetName: localizeSeedText(a.name || t('设备')),
      assetNo: String(a.asset_no || a.sn || `EQ-${String(m.asset_id).padStart(5, '0')}`),
      room: roomLabel(a.room_no, a.location, a.name),
      title: localizeSeedText(m.note || m.task_type || a.insight || a.name || t('维保工单')),
      taskType: t(String(m.task_type || '维保')),
      dueDate: m.due_date ? String(m.due_date).slice(0, 10) : '',
      status: String(m.status || 'scheduled'),
      statusLabel: ui.label,
      statusCls: ui.cls,
      owner: m.owner ? localizeSeedText(String(m.owner)) : t('待指派'),
    })
  }

  const rank = { overdue: 0, doing: 1, scheduled: 2 } as const
  list.sort((x, y) => {
    const sr = rank[x.statusCls] - rank[y.statusCls]
    if (sr !== 0) return sr
    if (x.dueDate && y.dueDate) return x.dueDate.localeCompare(y.dueDate)
    return x.maintId - y.maintId
  })
  return list
}

function isEquipmentAsset(a: any) {
  const cat = String(a.category || '').trim()
  return !!cat && !SUPPLY_CATS.test(cat)
}

function buildRadarFromAssets(assetList: any[]) {
  const buckets: Record<string, { sum: number; n: number }> = {}
  for (const a of assetList) {
    if (!isEquipmentAsset(a)) continue
    const label = String(a.category || '其他').trim() || '其他'
    const b = buckets[label] || { sum: 0, n: 0 }
    b.sum += Number(a.health_score || 0)
    b.n += 1
    buckets[label] = b
  }
  return Object.entries(buckets)
    .map(([label, b]) => ({
      label: localizeSeedText(label) || t(label),
      score: Math.round(b.sum / b.n),
      count: b.n,
    }))
    .sort((x, y) => y.count - x.count || x.label.localeCompare(y.label))
}

function buildBudget30Days(maintenance: any[]) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const buckets = Array.from({ length: 30 }, () => 0)
  for (const m of maintenance || []) {
    const raw = m.due_date
    if (!raw) continue
    if (m.status === 'done' || m.status === 'cancelled') continue
    const due = new Date(String(raw).slice(0, 10))
    if (Number.isNaN(due.getTime())) continue
    due.setHours(0, 0, 0, 0)
    const diff = Math.round((due.getTime() - today.getTime()) / 86400000)
    if (diff < 0 || diff >= 30) continue
    buckets[diff] += Number(m.cost || 0)
  }
  return buckets
}

function niceCeil(n: number) {
  if (n <= 0) return 0
  const mag = 10 ** Math.floor(Math.log10(n))
  return Math.ceil(n / mag) * mag
}

function buildBudgetYTicks(maxY: number) {
  if (maxY <= 0) return []
  const step =
    maxY <= 2000
      ? 500
      : maxY <= 20000
        ? Math.ceil(maxY / 4 / 1000) * 1000
        : Math.ceil(maxY / 4 / 10000) * 10000
  const ticks: number[] = []
  for (let v = maxY; v >= 0; v -= step) ticks.push(v)
  if (ticks[ticks.length - 1] !== 0) ticks.push(0)
  return ticks
}

function buildBubblesFromAssets(assetList: any[]) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const items: { x: number; y: number; r: number; tone: string; name: string }[] = []
  for (const a of assetList) {
    if (!isEquipmentAsset(a)) continue
    const y = Number(a.current_value ?? a.purchase_value ?? 0)
    if (y <= 0) continue
    let x = 0
    if (a.purchase_date) {
      const pd = new Date(String(a.purchase_date).slice(0, 10))
      if (!Number.isNaN(pd.getTime())) {
        x = Math.max(0, (today.getTime() - pd.getTime()) / (365.25 * 86400000))
      }
    }
    const health = Number(a.health_score ?? 100)
    let tone = 'ok'
    if (a.status === 'abnormal' || health < 55) tone = 'risk'
    else if (a.status === 'maintenance' || health < 75) tone = 'warn'
    const r = Math.max(7, Math.min(26, 8 + Math.sqrt(y) / 120))
    items.push({
      x: Math.round(x * 10) / 10,
      y: Math.round(y),
      r,
      tone,
      name: String(a.name || a.asset_no || '设备'),
    })
  }
  return items
}

const budgetMaxY = ref(0)
const bubbleScale = ref({ maxX: 1, maxY: 1000 })

function alertCls(severity?: string) {
  if (severity === 'high') return 'orange'
  if (severity === 'mid') return 'yellow'
  return 'primary'
}

const lossInsight = ref({ total: 0, highPriority: 0, delta: '' })

function goKeyAssets() {
  emit('scrollToList')
}

function goRootCause() {
  const list = lastBoard.value?.assets || []
  const worst = [...list].sort(
    (a: any, b: any) => Number(a.health_score || 100) - Number(b.health_score || 100),
  )[0]
  if (worst?.id) router.push(`/c8-assets/assets/${worst.id}`)
  else emit('scrollToList')
}

function goTracking() {
  router.push('/c8-assets/tracking')
}

function goWorkOrder(wo: PendingWo) {
  router.push({
    path: '/c8-assets/tracking',
    query: { asset_id: String(wo.assetId) },
  })
}

function goProcurement() {
  emit('registerAsset')
}

function goLossAnalysis() {
  router.push('/c8-assets/loss-analysis-replacement-strategy')
}

const lastBoard = ref<any>(null)

function escapeHtml(s: string) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** 原型：建议文案中数量短语用 primary 加粗 */
const aiBodyHtml = computed(() => {
  const raw = aiSuggestion.value.body || ASSETS_EMPTY
  return escapeHtml(raw).replace(/(\d+\s*套[\u4e00-\u9fffA-Za-z0-9·\-]+)/g, '<strong>$1</strong>')
})

function radarPoint(i: number, n: number, score: number) {
  const angle = -Math.PI / 2 + (i * 2 * Math.PI) / n
  const r = (Math.max(0, Math.min(100, score)) / 100) * RADAR_R
  return {
    x: RADAR_CX + r * Math.cos(angle),
    y: RADAR_CY + r * Math.sin(angle),
  }
}

function radarLabelPos(i: number, n: number) {
  const angle = -Math.PI / 2 + (i * 2 * Math.PI) / n
  const r = RADAR_R + 28
  return {
    x: RADAR_CX + r * Math.cos(angle),
    y: RADAR_CY + r * Math.sin(angle),
  }
}

const radarPoly = computed(() => {
  const items = radarScores.value
  if (!items.length) return ''
  return items
    .map((it, i) => {
      const p = radarPoint(i, items.length, it.score)
      return `${p.x},${p.y}`
    })
    .join(' ')
})

const radarBaseline = computed(() => {
  const n = radarScores.value.length
  if (n < 3) return ''
  return Array.from({ length: n }, (_, i) => {
    const p = radarPoint(i, n, RADAR_BASELINE)
    return `${p.x},${p.y}`
  }).join(' ')
})

const radarGrid = computed(() => {
  const n = radarScores.value.length
  if (n < 3) return []
  return RADAR_RING_SCORES.map((score) =>
    Array.from({ length: n }, (_, i) => {
      const p = radarPoint(i, n, score)
      return `${p.x},${p.y}`
    }).join(' '),
  )
})

const radarRingLabels = computed(() => {
  const n = radarScores.value.length
  if (n < 3) return []
  return RADAR_RING_SCORES.map((score) => {
    const p = radarPoint(0, n, score)
    return { score, x: p.x - 12, y: p.y + 4 }
  })
})

const radarAxes = computed(() => {
  const n = radarScores.value.length
  if (n < 3) return []
  return Array.from({ length: n }, (_, i) => radarPoint(i, n, 100))
})

const radarLabels = computed(() => {
  const items = radarScores.value
  return items.map((it, i) => ({
    ...radarLabelPos(i, items.length),
    label: it.label,
  }))
})

/** 当前健康评分顶点（原型 Chart.js point） */
const radarPoints = computed(() => {
  const items = radarScores.value
  return items.map((it, i) => ({
    ...radarPoint(i, items.length, it.score),
    score: it.score,
  }))
})

function budgetXY(dayIdx: number, value: number) {
  const { padL, padR, padT, padB, W, H } = BUDGET
  const maxY = budgetMaxY.value || 1
  const n = Math.max(1, budgetPts.value.length - 1)
  return {
    x: padL + (dayIdx / n) * (W - padL - padR),
    y: padT + (1 - Math.min(maxY, Math.max(0, value)) / maxY) * (H - padT - padB),
  }
}

const budgetPath = computed(() => {
  const pts = budgetPts.value
  if (pts.length < 2) return ''
  return pts
    .map((v, i) => {
      const p = budgetXY(i, v)
      return `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`
    })
    .join(' ')
})

const budgetArea = computed(() => {
  const pts = budgetPts.value
  if (pts.length < 2) return ''
  const { padL, padR, W, H, padB } = BUDGET
  const line = pts
    .map((v, i) => {
      const p = budgetXY(i, v)
      return `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`
    })
    .join(' ')
  const y0 = H - padB
  return `${line} L${W - padR},${y0} L${padL},${y0} Z`
})

const budgetHasData = computed(() => budgetPts.value.some((v) => v > 0))

const budgetDots = computed(() => {
  const pts = budgetPts.value
  if (!pts.length || !budgetHasData.value) return []
  return pts.map((v, i) => ({ ...budgetXY(i, v), v: Math.round(v) }))
})

const budgetYTicks = computed(() =>
  buildBudgetYTicks(budgetMaxY.value).map((v) => ({
    v,
    label: v === 0 ? '¥0' : `¥${v.toLocaleString('zh-CN')}`,
    y: budgetXY(0, v).y,
  })),
)

const budgetXTicks = computed(() => {
  const pts = budgetPts.value
  if (!pts.length) return []
  return BUDGET.xTicks.map((day) => {
    const i = Math.min(pts.length - 1, Math.max(0, day - 1))
    return {
      day,
      label: day === 1 ? t('今天') : t('+{n}天', { n: day - 1 }),
      x: budgetXY(i, 0).x,
    }
  })
})

const budgetGridY = computed(() =>
  buildBudgetYTicks(budgetMaxY.value)
    .filter((v) => v > 0)
    .map((v) => budgetXY(0, v).y),
)

async function applyBoard(board: any) {
  lastBoard.value = board
  const s = board?.summary || {}
  const assetList = board?.assets || []

  const totalVal = Number(s.total_value || 0)
  const avgHealth = s.avg_health != null ? Math.round(Number(s.avg_health)) : 0

  summary.value = [
    {
      label: t('总资产价值'),
      value: totalVal
        ? `¥ ${totalVal.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
        : '¥ 0',
      delta: '',
      deltaTxt: '',
    },
    {
      label: t('平均健康评分'),
      value: s.avg_health != null ? String(avgHealth) : '—',
      unit: '/100',
      pct: avgHealth,
      barCls: 'var(--primary)',
      accent: 'primary',
    },
  ]

  pendingWorkOrders.value = buildPendingWorkOrders(board)

  // 雷达：按库内 category 聚合 health_score 均值（无示意分兜底）
  radarScores.value = buildRadarFromAssets(assetList)

  // 折线：未来 30 天按维保 due_date 汇总 cost
  budgetPts.value = buildBudget30Days(board?.maintenance || [])
  const budgetPeak = Math.max(...budgetPts.value, 0)
  budgetMaxY.value = budgetPeak > 0 ? niceCeil(budgetPeak * 1.12) : 0

  // 气泡：purchase_date → 使用年限，current_value / purchase_value → 价值
  const bubbleList = buildBubblesFromAssets(assetList)
  bubbles.value = bubbleList
  if (bubbleList.length) {
    const maxX = Math.max(0.5, ...bubbleList.map((b) => b.x))
    const maxY = Math.max(1000, ...bubbleList.map((b) => b.y))
    bubbleScale.value = {
      maxX: Math.ceil(maxX * 1.15 * 2) / 2,
      maxY: niceCeil(maxY * 1.12),
    }
  } else {
    bubbleScale.value = { maxX: 1, maxY: 1000 }
  }

  alerts.value = (board?.alerts || []).slice(0, 5).map((a: any) => {
    const room = a.room_no ? t('{n} 房', { n: a.room_no }) : t(a.floor || '公共区')
    const cls = alertCls(a.severity)
    const rawTitle = a.message || a.asset_name || t('设备告警')
    return {
      room,
      title: t(String(rawTitle).slice(0, 40)),
      desc: t(String(a.message || '')),
      cls,
      btn: cls === 'orange' ? t('派发工单') : cls === 'yellow' ? t('安排更换') : '',
      btnCls: cls === 'orange' ? 'orange' : 'primary',
      showIgnore: cls === 'orange',
    }
  })

  // 原型文案优先：有 replace/roi 用库表；否则用「集中采购」风格洞察
  const ins =
    (board?.insights || []).find((x: any) => ['replace', 'roi', 'maintain'].includes(x.category)) ||
    (board?.insights || [])[0]
  if (ins) {
    aiSuggestion.value = {
      title: t(String(ins.title || '集中采购建议')),
      tag: ins.category === 'replace' || ins.category === 'roi' ? t('高ROI') : t('AI 洞察'),
      body: t(String(ins.recommendation || '')),
    }
  } else {
    aiSuggestion.value = { title: '', tag: '', body: '' }
  }

  const repairLoss = assetList.reduce(
    (acc: number, a: any) => acc + Number(a.repair_cost_total || 0),
    0,
  )
  const maintLoss = (board?.maintenance || [])
    .filter((m: any) => m.status === 'done')
    .reduce((acc: number, m: any) => acc + Number(m.cost || 0), 0)
  const lossTotal = Math.round(repairLoss + maintLoss)
  const highPriority = (board?.insights || []).filter(
    (x: any) => x.asset_id && ['replace', 'roi'].includes(x.category),
  ).length
  lossInsight.value = {
    total: lossTotal,
    highPriority,
    delta: '',
  }
}

async function load() {
  try {
    const board = props.board ?? (await api.assetsBoard(hotelStore.hotelId))
    await applyBoard(board)
  } catch {
    summary.value = []
    pendingWorkOrders.value = []
    alerts.value = []
    radarScores.value = []
    budgetPts.value = []
    budgetMaxY.value = 0
    bubbles.value = []
    bubbleScale.value = { maxX: 1, maxY: 1000 }
    aiSuggestion.value = { title: '', tag: '', body: '' }
    lossInsight.value = { total: 0, highPriority: 0, delta: '' }
  }
}

const BUBBLE = {
  W: 640,
  H: 300,
  padL: 56,
  padR: 24,
  padT: 36,
  padB: 44,
}

function bubbleXY(x: number, y: number) {
  const { padL, padR, padT, padB, W, H } = BUBBLE
  const { maxX, maxY } = bubbleScale.value
  const denomX = maxX || 1
  const denomY = maxY || 1
  return {
    cx: padL + (Math.min(denomX, Math.max(0, x)) / denomX) * (W - padL - padR),
    cy: padT + (1 - Math.min(denomY, Math.max(0, y)) / denomY) * (H - padT - padB),
  }
}

const bubblePlot = computed(() => bubbles.value.map((b) => ({ ...b, ...bubbleXY(b.x, b.y) })))

const bubbleGridX = computed(() => {
  const maxX = Math.ceil(bubbleScale.value.maxX)
  const step = maxX <= 6 ? 1 : Math.max(1, Math.ceil(maxX / 6))
  const ticks: number[] = []
  for (let v = 0; v <= maxX; v += step) ticks.push(Math.round(v * 10) / 10)
  if (ticks[ticks.length - 1] !== maxX) ticks.push(maxX)
  return ticks.map((v) => ({ v, x: bubbleXY(v, 0).cx }))
})

const bubbleGridY = computed(() => {
  const maxY = bubbleScale.value.maxY || 1
  const steps = 4
  const out: { v: number; y: number; label: string }[] = []
  for (let i = 0; i <= steps; i++) {
    const v = Math.round((maxY / steps) * i)
    out.push({
      v,
      y: bubbleXY(0, v).cy,
      label:
        v >= 10000
          ? `${Math.round(v / 10000)}万`
          : v >= 1000
            ? `${Math.round(v / 1000)}k`
            : String(v),
    })
  }
  return out
})

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(
  () => props.board,
  (b) => {
    if (b) applyBoard(b)
  },
  { deep: true },
)
</script>

<template>
  <section class="health-panorama">
    <!-- KPI -->
    <div class="kpi-row">
      <div v-for="(s, i) in summary" :key="i" class="kpi-card" :class="s.accent">
        <p class="kpi-label" :class="{ err: s.accent === 'error' }">{{ s.label }}</p>
        <div class="kpi-val">
          <span :class="{ err: s.accent === 'error', primary: s.accent === 'primary' }">{{
            s.value
          }}</span>
          <span v-if="s.unit" class="unit">{{ s.unit }}</span>
        </div>
        <div v-if="s.delta || s.deltaTxt" class="kpi-sub">
          <span v-if="s.delta" class="delta">{{ s.delta }}</span>
          <span v-if="s.deltaTxt" class="delta-txt">{{ s.deltaTxt }}</span>
        </div>
        <div v-if="s.pct !== undefined" class="kpi-bar">
          <div :style="{ width: s.pct + '%', background: s.barCls }" />
        </div>
      </div>

      <div class="kpi-pending-panel">
        <div class="pending-head">
          <p class="kpi-label">{{ t('待处理事项') }}</p>
          <button
            v-if="pendingWorkOrders.length"
            type="button"
            class="pending-all"
            @click="goTracking"
          >
            {{ t('全部') }} {{ pendingWorkOrders.length }} {{ t('项') }}
            <span class="material-symbols-outlined">chevron_right</span>
          </button>
        </div>
        <div v-if="!pendingWorkOrders.length" class="pending-empty">
          <span class="material-symbols-outlined">task_alt</span>
          <p>{{ t('暂无待处理工单') }}</p>
        </div>
        <div v-else class="pending-list">
          <button
            v-for="wo in pendingWorkOrders"
            :key="wo.id"
            type="button"
            class="pending-wo-card"
            :class="wo.statusCls"
            @click="goWorkOrder(wo)"
          >
            <div class="wo-card-main">
              <div class="wo-card-top">
                <span class="wo-id">{{ wo.id }}</span>
                <span class="wo-status">{{ wo.statusLabel }}</span>
              </div>
              <p class="wo-title">{{ localizeSeedText(wo.title) }}</p>
              <div class="wo-meta">
                <span>{{ localizeSeedText(wo.assetName) }}</span>
                <span class="dot" />
                <span>{{ localizeSeedText(wo.room) }}</span>
                <span v-if="wo.dueDate" class="dot" />
                <span v-if="wo.dueDate">{{ t('到期 {date}', { date: wo.dueDate }) }}</span>
              </div>
            </div>
            <div class="wo-card-side">
              <span class="wo-type">{{ wo.taskType }}</span>
              <span class="wo-owner">{{ localizeSeedText(wo.owner) }}</span>
              <span class="material-symbols-outlined wo-arrow">arrow_forward</span>
            </div>
          </button>
        </div>
      </div>
    </div>

    <div class="loss-insight-banner">
      <button type="button" class="loss-insight-main" @click="goLossAnalysis">
        <span class="material-symbols-outlined loss-ico">analytics</span>
        <div class="loss-copy">
          <strong>{{ t('年度设备损耗洞察') }}</strong>
          <p v-if="lossInsight.total > 0">
            {{ t('过去 12 个月累计约') }} <em>¥{{ lossInsight.total.toLocaleString('zh-CN') }}</em>
            <span v-if="lossInsight.highPriority">
              ·
              {{ t('{n} 台设备建议优先评估', { n: lossInsight.highPriority }) }}</span
            >
          </p>
          <p v-else>{{ t('查看报损归因与设备更新策略建议') }}</p>
        </div>
      </button>
      <div class="loss-actions">
        <button type="button" class="btn btn-ghost loss-act-btn" @click="goLossAnalysis">
          <span class="material-symbols-outlined">analytics</span>
          {{ t('报损洞察') }}
        </button>
        <button type="button" class="btn btn-ghost loss-act-btn" @click="goTracking">
          <span class="material-symbols-outlined">assignment</span>
          {{ t('维修追踪') }}
        </button>
      </div>
    </div>

    <div class="main-grid">
      <div class="charts-col">
        <div class="charts-top">
          <!-- 雷达：对照原型 Chart.js healthRadarChart -->
          <div class="card-clean chart-card">
            <h3>{{ t('设备分类健康度') }}</h3>
            <div class="chart-box radar-box">
              <p v-if="radarScores.length < 3" class="empty-hint">{{ ASSETS_EMPTY }}</p>
              <template v-else>
                <svg viewBox="0 0 300 300" class="radar-svg">
                  <polygon
                    v-for="(g, gi) in radarGrid"
                    :key="gi"
                    :points="g"
                    fill="none"
                    stroke="#e1e3e4"
                    stroke-width="1"
                  />
                  <text
                    v-for="ring in radarRingLabels"
                    :key="'ring' + ring.score"
                    :x="ring.x"
                    :y="ring.y"
                    text-anchor="end"
                    class="radar-ring-label"
                  >
                    {{ ring.score }}
                  </text>
                  <line
                    v-for="(a, ai) in radarAxes"
                    :key="'ax' + ai"
                    :x1="RADAR_CX"
                    :y1="RADAR_CY"
                    :x2="a.x"
                    :y2="a.y"
                    stroke="#e1e3e4"
                    stroke-width="1"
                  />
                  <!-- 行业基准虚线 -->
                  <polygon
                    :points="radarBaseline"
                    fill="none"
                    stroke="#94a3b8"
                    stroke-width="1.75"
                    stroke-dasharray="5 4"
                  />
                  <!-- 当前健康评分 -->
                  <polygon
                    :points="radarPoly"
                    fill="rgba(26, 115, 232, 0.22)"
                    stroke="#1a73e8"
                    stroke-width="2"
                    stroke-linejoin="round"
                  />
                  <circle
                    v-for="(pt, pi) in radarPoints"
                    :key="'pt' + pi"
                    :cx="pt.x"
                    :cy="pt.y"
                    r="3.5"
                    fill="#1a73e8"
                    stroke="#fff"
                    stroke-width="1.5"
                  />
                  <text
                    v-for="(lb, li) in radarLabels"
                    :key="'lb' + li"
                    :x="lb.x"
                    :y="lb.y"
                    text-anchor="middle"
                    dominant-baseline="middle"
                    class="radar-label"
                  >
                    {{ lb.label }}
                  </text>
                </svg>
                <!-- 原型图例：圆点样式（非色块） -->
                <div class="radar-legend">
                  <span class="leg-item">
                    <i class="leg-dot fill" />{{ t('当前健康评分（按品类均值）') }}</span
                  >
                  <span class="leg-item">
                    <i class="leg-dot hollow" />{{ t('行业基准') }} {{ RADAR_BASELINE }}
                    {{ t('分') }}
                  </span>
                  <span class="leg-item muted">{{ t('同心环：25 / 50 / 75 / 100 分') }}</span>
                </div>
              </template>
            </div>
          </div>

          <!-- 折线：对照原型 Chart.js budgetLineChart -->
          <div class="card-clean chart-card">
            <h3>{{ t('未来30天维保预算预测') }}</h3>
            <p class="chart-sub">{{ t('按维保工单计划日期汇总预算（未完成工单 cost）') }}</p>
            <div class="chart-box line-box">
              <p v-if="!budgetHasData" class="empty-hint">{{ ASSETS_EMPTY }}</p>
              <div v-else class="line-wrap">
                <div class="y-labels">
                  <span v-for="tag in budgetYTicks" :key="'yt' + tag.v">{{ tag.label }}</span>
                </div>
                <svg
                  :viewBox="`0 0 ${BUDGET.W} ${BUDGET.H}`"
                  class="line-svg"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <linearGradient id="budgetFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stop-color="#8c33b3" stop-opacity="0.28" />
                      <stop offset="100%" stop-color="#8c33b3" stop-opacity="0.02" />
                    </linearGradient>
                  </defs>
                  <line
                    v-for="(gy, gi) in budgetGridY"
                    :key="'g' + gi"
                    :x1="BUDGET.padL"
                    :y1="gy"
                    :x2="BUDGET.W - BUDGET.padR"
                    :y2="gy"
                    stroke="#eef0f3"
                    stroke-width="1"
                  />
                  <path :d="budgetArea" fill="url(#budgetFill)" />
                  <path
                    :d="budgetPath"
                    fill="none"
                    stroke="#8c33b3"
                    stroke-width="2.5"
                    stroke-linejoin="round"
                    stroke-linecap="round"
                  />
                  <circle
                    v-for="(d, i) in budgetDots"
                    :key="i"
                    :cx="d.x"
                    :cy="d.y"
                    r="4"
                    fill="#8c33b3"
                    stroke="#fff"
                    stroke-width="2"
                  >
                    <title>¥{{ d.v.toLocaleString('zh-CN') }}</title>
                  </circle>
                </svg>
                <div class="x-labels">
                  <span v-for="tag in budgetXTicks" :key="'xt' + tag.day">{{ tag.label }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 气泡：对照原型 Chart.js valueBubbleChart -->
        <div class="card-clean chart-card bubble-card">
          <div class="bubble-head">
            <h3>{{ t('资产价值与年限分布') }}</h3>
            <span class="pill">{{ t('净值 × 使用年限（库内台账）') }}</span>
          </div>
          <div class="chart-box bubble-box">
            <p v-if="!bubblePlot.length" class="empty-hint">{{ ASSETS_EMPTY }}</p>
            <div v-else class="bubble-chart-wrap">
              <svg
                :viewBox="`0 0 ${BUBBLE.W} ${BUBBLE.H}`"
                class="bubble-svg"
                preserveAspectRatio="xMidYMid meet"
              >
                <!-- 网格 -->
                <line
                  v-for="g in bubbleGridX"
                  :key="'vx' + g.v"
                  :x1="g.x"
                  :y1="BUBBLE.padT"
                  :x2="g.x"
                  :y2="BUBBLE.H - BUBBLE.padB"
                  stroke="#eef0f3"
                  stroke-width="1"
                />
                <line
                  v-for="g in bubbleGridY"
                  :key="'hy' + g.v"
                  :x1="BUBBLE.padL"
                  :y1="g.y"
                  :x2="BUBBLE.W - BUBBLE.padR"
                  :y2="g.y"
                  stroke="#eef0f3"
                  stroke-width="1"
                />
                <!-- 坐标轴 -->
                <line
                  :x1="BUBBLE.padL"
                  :y1="BUBBLE.padT"
                  :x2="BUBBLE.padL"
                  :y2="BUBBLE.H - BUBBLE.padB"
                  stroke="#c1c6d6"
                  stroke-width="1"
                />
                <line
                  :x1="BUBBLE.padL"
                  :y1="BUBBLE.H - BUBBLE.padB"
                  :x2="BUBBLE.W - BUBBLE.padR"
                  :y2="BUBBLE.H - BUBBLE.padB"
                  stroke="#c1c6d6"
                  stroke-width="1"
                />
                <!-- Y 刻度 -->
                <g v-for="g in bubbleGridY" :key="'yl' + g.v">
                  <text :x="BUBBLE.padL - 8" :y="g.y + 3" text-anchor="end" class="axis-tick">
                    {{ g.label }}
                  </text>
                </g>
                <!-- X 刻度 -->
                <g v-for="g in bubbleGridX" :key="'xl' + g.v">
                  <text
                    :x="g.x"
                    :y="BUBBLE.H - BUBBLE.padB + 16"
                    text-anchor="middle"
                    class="axis-tick"
                  >
                    {{ g.v }}
                  </text>
                </g>
                <!-- 轴标题 -->
                <text
                  :x="18"
                  :y="BUBBLE.H / 2"
                  text-anchor="middle"
                  class="axis-title"
                  :transform="`rotate(-90 18 ${BUBBLE.H / 2})`"
                >
                  {{ t('当前账面残值 (¥)') }}
                </text>
                <text
                  :x="(BUBBLE.padL + BUBBLE.W - BUBBLE.padR) / 2"
                  :y="BUBBLE.H - 8"
                  text-anchor="middle"
                  class="axis-title"
                >
                  {{ t('使用年限 (年)') }}
                </text>
                <!-- 图例（原型位于图内右上） -->
                <g class="bubble-legend-svg" :transform="`translate(${BUBBLE.W - 268}, 8)`">
                  <circle cx="6" cy="6" r="5" class="bubble-ok" />
                  <text x="16" y="9" class="legend-txt">{{ t('健康资产') }}</text>
                  <circle cx="88" cy="6" r="5" class="bubble-warn" />
                  <text x="98" y="9" class="legend-txt">{{ t('需关注（近报废期）') }}</text>
                  <circle cx="210" cy="6" r="5" class="bubble-risk" />
                  <text x="220" y="9" class="legend-txt">{{ t('极高风险') }}</text>
                </g>
                <!-- 气泡 -->
                <circle
                  v-for="(b, i) in bubblePlot"
                  :key="i"
                  :cx="b.cx"
                  :cy="b.cy"
                  :r="b.r"
                  :class="'bubble-' + b.tone"
                >
                  <title>
                    {{ b.name }} · {{ b.x.toFixed(1) }}年 · ¥{{ Math.round(b.y).toLocaleString() }}
                  </title>
                </circle>
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧 -->
      <div class="side-col">
        <div class="ai-panel">
          <div class="ai-glow" />
          <div class="ai-title">
            <div class="ai-ico">
              <span class="material-symbols-outlined">auto_awesome</span>
            </div>
            <h3>{{ t('AI 决策建议') }}</h3>
          </div>
          <div class="ai-body">
            <div class="ai-row">
              <span class="ai-h">{{ aiSuggestion.title || '—' }}</span>
              <span v-if="aiSuggestion.tag" class="ai-tag">{{ aiSuggestion.tag }}</span>
            </div>
            <p v-html="aiBodyHtml" />
          </div>
          <button class="ai-cta" type="button" @click="goLossAnalysis">
            {{ t('查看报损与更新策略') }}
          </button>
        </div>

        <div class="card-clean alerts-panel">
          <div class="alerts-head">
            <h3>{{ t('异常监控与高风险项') }}</h3>
            <button class="link" type="button" @click="goKeyAssets">{{ t('查看全部') }}</button>
          </div>
          <p v-if="!alerts.length" class="empty-hint">{{ ASSETS_EMPTY }}</p>
          <div v-for="(a, i) in alerts" :key="i" class="alert-item" :class="a.cls">
            <div class="alert-top">
              <span class="room">{{ a.room }}</span>
              <span class="ttl">{{ a.title }}</span>
            </div>
            <p>{{ a.desc }}</p>
            <div v-if="a.btn || a.showIgnore" class="alert-actions">
              <button v-if="a.showIgnore" class="btn-ignore" type="button">{{ t('忽略') }}</button>
              <button
                v-if="a.btn"
                class="btn-act"
                :class="a.btnCls"
                type="button"
                @click="goTracking"
              >
                {{ a.btn }}
              </button>
            </div>
          </div>
          <div v-if="alerts.length" class="rca-banner">
            <div class="rca-copy">
              <span class="material-symbols-outlined">troubleshoot</span>
              <div>
                <strong>{{ t('同类故障是否扎堆？') }}</strong>
                <p>{{ t('对低健康分设备按楼栋 / 品牌型号做根因溯源，避免反复维修。') }}</p>
              </div>
            </div>
            <button class="btn-rca" type="button" @click="goLossAnalysis">
              {{ t('报损分析 &amp; 更新策略 →') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.health-panorama {
  margin-bottom: 24px;
}
.loss-insight-banner {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding: 14px 18px;
  border-radius: 12px;
  border: 1px solid var(--outline-variant);
  background: linear-gradient(105deg, rgba(216, 226, 255, 0.6) 0%, rgba(255, 255, 255, 0.98) 70%);
  text-align: left;
  transition: border-color 0.15s;
}
.loss-insight-banner:hover {
  border-color: color-mix(in srgb, var(--primary) 40%, var(--outline-variant));
}
.loss-insight-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
}
.loss-insight-main:hover .loss-copy strong {
  color: var(--primary);
}
.loss-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.loss-act-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.loss-act-btn .material-symbols-outlined {
  font-size: 18px;
}
.loss-ico {
  font-size: 22px;
  color: var(--primary);
  margin-top: 2px;
}
.loss-copy strong {
  display: block;
  font-size: 14px;
  margin-bottom: 4px;
}
.loss-copy p {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.loss-copy em {
  font-style: normal;
  font-weight: 700;
  color: var(--on-surface);
}
.kpi-row {
  display: grid;
  grid-template-columns: minmax(200px, 1fr) minmax(200px, 1fr) minmax(320px, 2.4fr);
  gap: 16px;
  margin-bottom: 16px;
  align-items: stretch;
}
.kpi-pending-panel {
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 20px 20px 16px;
  border-left: 4px solid #f59e0b;
  background: linear-gradient(
    120deg,
    rgba(255, 247, 237, 0.75) 0%,
    rgba(255, 252, 245, 0.55) 38%,
    rgba(255, 255, 255, 0.98) 100%
  );
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.pending-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.pending-all {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 4px 0;
  font-family: inherit;
}
.pending-all .material-symbols-outlined {
  font-size: 18px;
}
.pending-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--on-surface-variant);
  min-height: 88px;
}
.pending-empty .material-symbols-outlined {
  font-size: 28px;
  opacity: 0.55;
}
.pending-empty p {
  margin: 0;
  font-size: 13px;
}
.pending-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 220px;
  overflow-y: auto;
  padding-right: 2px;
}
.pending-wo-card {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  text-align: left;
  border: 1px solid rgba(193, 198, 214, 0.55);
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  font-family: inherit;
  transition:
    transform 0.15s,
    box-shadow 0.15s,
    border-color 0.15s;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.pending-wo-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
  border-color: color-mix(in srgb, var(--primary) 35%, var(--outline-variant));
}
.pending-wo-card.scheduled {
  background: linear-gradient(105deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.95));
  border-left: 3px solid #94a3b8;
}
.pending-wo-card.doing {
  background: linear-gradient(105deg, rgba(239, 246, 255, 0.95), rgba(255, 255, 255, 0.98));
  border-left: 3px solid #3b82f6;
}
.pending-wo-card.overdue {
  background: linear-gradient(105deg, rgba(255, 241, 242, 0.92), rgba(255, 255, 255, 0.98));
  border-left: 3px solid #ef4444;
}
.wo-card-main {
  flex: 1;
  min-width: 0;
}
.wo-card-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.wo-id {
  font-size: 11px;
  font-weight: 700;
  color: var(--on-surface-variant);
  font-family: 'Roboto Mono', monospace;
}
.wo-status {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  letter-spacing: 0.02em;
}
.pending-wo-card.scheduled .wo-status {
  background: #f1f5f9;
  color: #475569;
}
.pending-wo-card.doing .wo-status {
  background: #dbeafe;
  color: #1d4ed8;
}
.pending-wo-card.overdue .wo-status {
  background: #fee2e2;
  color: #b91c1c;
}
.wo-title {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface);
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.wo-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.wo-meta .dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--outline);
  flex-shrink: 0;
}
.wo-card-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  gap: 4px;
  flex-shrink: 0;
}
.wo-type {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(193, 198, 214, 0.45);
  color: var(--on-surface-variant);
  white-space: nowrap;
}
.wo-owner {
  font-size: 11px;
  color: var(--on-surface-variant);
  white-space: nowrap;
}
.wo-arrow {
  font-size: 18px;
  color: var(--outline);
  margin-top: 2px;
}
.pending-wo-card:hover .wo-arrow {
  color: var(--primary);
}
.kpi-card {
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 24px;
  position: relative;
  overflow: hidden;
}
.kpi-card.primary {
  border-left: 4px solid var(--primary);
  /* 原型 ai-gradient：浅蓝渐变底 */
  background: linear-gradient(
    105deg,
    rgba(216, 226, 255, 0.95) 0%,
    rgba(232, 240, 254, 0.75) 42%,
    rgba(255, 255, 255, 0.98) 100%
  );
}
.kpi-card.yellow {
  border-left: 4px solid #f59e0b;
}
.kpi-card.error {
  border-left: 4px solid var(--error);
  background: linear-gradient(
    105deg,
    rgba(255, 218, 214, 0.55) 0%,
    rgba(255, 241, 239, 0.35) 50%,
    rgba(255, 255, 255, 0.95) 100%
  );
}
.kpi-label {
  margin: 0 0 4px;
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface-variant);
}
.kpi-label.err {
  color: var(--error);
}
.kpi-val {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.kpi-val > span:first-child {
  font-size: 28px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.kpi-val .primary {
  color: var(--primary);
}
.kpi-val .err {
  color: var(--error);
}
.kpi-val .unit {
  font-size: 12px;
  color: var(--on-surface-variant);
}
/* 原型：涨跌单独一行在数值下方 */
.kpi-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.kpi-sub .delta {
  font-size: 13px;
  font-weight: 500;
  color: #16a34a;
}
.kpi-sub .delta-txt {
  font-size: 13px;
  color: var(--on-surface-variant);
}
.kpi-bar {
  margin-top: 16px;
  height: 8px;
  background: var(--surface-container-highest);
  border-radius: 999px;
  overflow: hidden;
}
.kpi-bar > div {
  height: 100%;
  border-radius: 999px;
}
.avatars {
  display: flex;
  margin-top: 16px;
}
.av {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  margin-left: -8px;
  border: 2px solid #fff;
}
.av:first-child {
  margin-left: 0;
}
.av.t0 {
  background: #fef3c7;
  color: #b45309;
}
.av.t1 {
  background: #dbeafe;
  color: #1d4ed8;
}
.av.t2 {
  background: #f1f5f9;
  color: #475569;
}
.kpi-btn {
  width: 100%;
  margin-top: 16px;
  background: var(--error);
  color: var(--on-error, #ffffff);
  border: 0;
  border-radius: 8px;
  padding: 6px 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
}
.kpi-btn:hover {
  filter: brightness(0.92);
}

.main-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  align-items: start;
}
.charts-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.charts-top {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.chart-card {
  padding: 24px;
}
.chart-card h3 {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
}
.chart-box {
  min-height: 250px;
}
.radar-box {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.radar-svg {
  width: 100%;
  max-width: 320px;
  height: auto;
}
.radar-label {
  font-size: 11px;
  fill: var(--on-surface-variant);
  font-family: 'Source Sans 3', sans-serif;
}
.radar-ring-label {
  font-size: 9px;
  fill: #94a3b8;
  font-family: 'Roboto Mono', monospace;
}
.chart-sub {
  margin: -8px 0 12px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
/* 原型 Chart.js 图例：圆点 + 文案，底居中 */
.radar-legend {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px 20px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.leg-item.muted {
  color: var(--outline);
  font-size: 11px;
}
.leg-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.leg-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  box-sizing: border-box;
}
.leg-dot.fill {
  background: #1a73e8;
  border: 1px solid #1a73e8;
}
.leg-dot.hollow {
  background: #fff;
  border: 2px solid #94a3b8;
}

.line-wrap {
  display: grid;
  grid-template-columns: 56px 1fr;
  grid-template-rows: 1fr auto;
  gap: 4px 8px;
  height: 230px;
}
.y-labels {
  grid-row: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: 11px;
  color: var(--on-surface-variant);
  text-align: right;
  padding: 8px 0;
  font-family: 'Roboto Mono', monospace;
}
.line-svg {
  grid-column: 2;
  grid-row: 1;
  width: 100%;
  height: 100%;
}
.x-labels {
  grid-column: 2;
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--on-surface-variant);
  padding: 0 4px;
}

.bubble-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.bubble-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.pill {
  font-size: 12px;
  font-weight: 400;
  color: var(--on-surface-variant);
  background: var(--surface-container);
  padding: 4px 12px;
  border-radius: 999px;
  border: none;
}
.bubble-chart-wrap {
  position: relative;
  width: 100%;
  min-height: 300px;
}
.bubble-svg {
  width: 100%;
  height: 300px;
  display: block;
}
.axis-tick {
  font-size: 10px;
  fill: var(--on-surface-variant);
  font-family: 'Roboto Mono', monospace;
}
.axis-title {
  font-size: 11px;
  fill: var(--on-surface-variant);
}
.legend-txt {
  font-size: 11px;
  fill: var(--on-surface-variant);
}
/* 原型 Chart.js 默认气泡色：半透明填充 + 同色描边 */
.bubble-ok {
  fill: rgba(54, 162, 235, 0.55);
  stroke: rgba(54, 162, 235, 0.95);
  stroke-width: 1.5;
}
.bubble-warn {
  fill: rgba(255, 205, 86, 0.6);
  stroke: rgba(230, 170, 40, 0.95);
  stroke-width: 1.5;
}
.bubble-risk {
  fill: rgba(255, 99, 132, 0.55);
  stroke: rgba(220, 70, 100, 0.95);
  stroke-width: 1.5;
}

.side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
/* 原型：bg-tertiary-fixed text-on-tertiary-fixed border-tertiary/20 */
.ai-panel {
  background: var(--tertiary-fixed);
  color: var(--on-tertiary-fixed);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid rgba(140, 51, 179, 0.2);
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
}
.ai-glow {
  position: absolute;
  top: -40px;
  right: -40px;
  width: 128px;
  height: 128px;
  background: var(--tertiary);
  border-radius: 50%;
  opacity: 0.2;
  filter: blur(40px);
  mix-blend-mode: multiply;
}
.ai-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}
.ai-ico {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--tertiary);
  color: var(--on-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ai-ico .material-symbols-outlined {
  font-size: 18px;
  color: var(--on-tertiary);
}
.ai-title h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(90deg, var(--tertiary) 0%, var(--tertiary-container) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.ai-body {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(4px);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid rgba(193, 198, 214, 0.3);
  position: relative;
  z-index: 1;
  margin-bottom: 16px;
}
.ai-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.ai-h {
  font-size: 13px;
  font-weight: 700;
  color: var(--on-surface);
}
.ai-tag {
  background: var(--primary-container);
  color: var(--on-primary-container);
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
  font-weight: 500;
}
.ai-body p {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant);
  line-height: 1.6;
}
.ai-body p :deep(strong) {
  color: var(--primary);
  font-weight: 700;
}
.ai-cta {
  width: 100%;
  background: var(--tertiary);
  color: var(--on-tertiary);
  padding: 10px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  position: relative;
  z-index: 1;
  box-shadow: var(--shadow);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.ai-cta:hover {
  background: var(--tertiary-container);
}

.alerts-panel {
  padding: 24px;
}
.alerts-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.alerts-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.link {
  border: 0;
  background: transparent;
  color: var(--primary);
  font-size: 13px;
  cursor: pointer;
}
.alert-item {
  border-radius: 8px;
  padding: 16px;
  border: 1px solid rgba(193, 198, 214, 0.5);
  border-left: 4px solid;
  margin-bottom: 12px;
  cursor: pointer;
  transition: box-shadow 0.15s;
}
.alert-item:hover {
  box-shadow: var(--shadow);
}
/* 原型：border-orange-200 bg-orange-50/50 border-l-orange-500 */
.alert-item.orange {
  background: rgba(255, 247, 237, 0.5);
  border-color: #fed7aa;
  border-left-color: #f97316;
}
/* 原型：border-yellow-200 bg-yellow-50/50 border-l-yellow-400 */
.alert-item.yellow {
  background: rgba(254, 252, 232, 0.5);
  border-color: #fef08a;
  border-left-color: #facc15;
}
.alert-item.primary {
  background: var(--surface-container-lowest);
  border-color: rgba(193, 198, 214, 0.5);
  border-left-color: rgba(0, 91, 191, 0.5);
  opacity: 0.7;
}
.alert-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.room {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--surface-container);
  color: var(--on-surface-variant);
}
/* 原型：bg-orange-100 text-orange-800 / bg-yellow-100 text-yellow-800 */
.alert-item.orange .room {
  background: #ffedd5;
  color: #9a3412;
}
.alert-item.yellow .room {
  background: #fef9c3;
  color: #854d0e;
}
.ttl {
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface);
}
.alert-item p {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.alert-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
/* 原型：text-on-surface-variant border-outline-variant */
.btn-ignore {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid var(--outline-variant);
  background: transparent;
  cursor: pointer;
  color: var(--on-surface-variant);
  font-weight: 500;
}
.btn-ignore:hover {
  color: var(--primary);
}
.btn-act {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-weight: 500;
}
/* 原型：bg-orange-100 text-orange-700 */
.btn-act.orange {
  background: #ffedd5;
  color: #c2410c;
}
.btn-act.orange:hover {
  background: #fed7aa;
}
/* 原型：bg-primary-container text-on-primary-container */
.btn-act.primary {
  background: var(--primary-container);
  color: var(--on-primary-container);
}
.btn-act.primary:hover {
  background: var(--primary);
  color: var(--on-primary);
}
.rca-banner {
  margin-top: 16px;
  padding: 14px;
  border-radius: 10px;
  border: 1px solid rgba(140, 51, 179, 0.35);
  background: linear-gradient(135deg, rgba(248, 216, 255, 0.45), rgba(255, 255, 255, 0.9));
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rca-copy {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.rca-copy .material-symbols-outlined {
  color: var(--tertiary);
  font-size: 22px;
  flex-shrink: 0;
}
.rca-copy strong {
  display: block;
  font-size: 14px;
  color: var(--on-surface);
  margin-bottom: 2px;
}
.rca-copy p {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.btn-rca {
  align-self: stretch;
  border: none;
  border-radius: 8px;
  padding: 10px 14px;
  background: var(--tertiary);
  color: var(--on-tertiary, #fff);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-rca:hover {
  opacity: 0.92;
}
.empty-hint {
  font-size: 13px;
  color: var(--on-surface-variant);
  margin: 0;
  padding: 12px 0;
}

@media (max-width: 1100px) {
  .kpi-row {
    grid-template-columns: 1fr 1fr;
  }
  .kpi-pending-panel {
    grid-column: 1 / -1;
  }
  .main-grid,
  .charts-top {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .kpi-row {
    grid-template-columns: 1fr;
  }
}
</style>
