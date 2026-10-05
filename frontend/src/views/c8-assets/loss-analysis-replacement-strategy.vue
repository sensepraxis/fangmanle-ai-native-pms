<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * 报损分析 & 更新策略 —— 设备设施专属（与布草耗材解耦）
 * 数据：assetsBoard + 非布草 damage_tickets
 */
import { ref, computed, onMounted, watch } from 'vue'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { ASSETS_EMPTY } from '../../lib/assetsEmpty'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import WorkOrderDrawer, { type WorkOrderTask } from '../../components/WorkOrderDrawer.vue'
import { buildWorkOrderIndex, resolveWorkOrderRef } from '../../lib/workOrderFromBoard'
import { localizeSeedText } from '../../lib/localizeSeed'
import RoomOpsNav from '../../components/RoomOpsNav.vue'

const router = useRouter()
const period = ref('12')

const fin = ref<{
  total: string
  delta: string
  items: { name: string; value: string; pct: number; colorCls: string }[]
}>({
  total: '¥0',
  delta: '',
  items: [],
})
const causes = ref<Cause[]>([])
const attributionLoading = ref(false)
const attributionSource = ref<'llm' | 'fallback' | 'unavailable' | 'empty' | 'cache' | null>(null)
const attributionError = ref('')
const attributionHtml = ref('')
const attributionActions = ref<any[]>([])
const attributionModelMeta = ref<any | null>(null)
const attributionExecuting = ref<string | null>(null)
const woDrawerOpen = ref(false)
const selectedWo = ref<WorkOrderTask | null>(null)
const attributionInputStats = ref({ damage: 0, alert: 0, maintenance: 0 })

const suggestions = ref<any[]>([])
type PriorityAsset = {
  rank: number
  assetId: number
  title: string
  badge: string
  category: string
  name: string
  tier: 'high' | 'mid'
}
const priorityAssets = ref<PriorityAsset[]>([])
const emptyHint = ref('')

const INSIGHT_CATEGORY_LABELS: Record<string, string> = {
  replace: t('建议更换'),
  roi: t('置换经济性'),
  health: t('健康风险'),
  maintain: t('维保建议'),
  audit: t('盘点差异'),
}

function insightCategoryLabel(cat?: string) {
  return INSIGHT_CATEGORY_LABELS[String(cat || '').toLowerCase()] || t('设备洞察')
}

function insightCategoryTier(cat?: string): 'high' | 'mid' {
  const c = String(cat || '').toLowerCase()
  return c === 'replace' || c === 'roi' ? 'high' : 'mid'
}

function insightCategoryWeight(cat?: string) {
  return insightCategoryTier(cat) === 'high' ? 2 : 1
}

const BAR_COLORS = ['bg-tertiary', 'bg-secondary', 'bg-primary', 'bg-outline', 'bg-error-container']
const ICON_CLS = ['bg-error-container', 'bg-secondary-container', 'bg-surface-container-highest']
const SUPPLY_CATS = /布草|消耗|易耗|耗材|linen|amenity/i

type RefLink = {
  label: string
  task: WorkOrderTask | null
}

type Cause = {
  iconCls: string
  count: string
  title: string
  desc: string
  rootCause: string
  mechanism: string
  evidence: string[]
  refLinks: RefLink[]
  actionHint: string
  priority?: string
}

type Sug = {
  title: string
  badge: string
  badgeCls: string
  glow: boolean
  insight: string
  strategy: string
  actions: { t: string; primary: boolean; to?: string }[]
}

const raw = ref<{
  damages: any[]
  assets: any[]
  alerts: any[]
  assetInsights: any[]
  maintenance: any[]
}>({
  damages: [],
  assets: [],
  alerts: [],
  assetInsights: [],
  maintenance: [],
})

function money(n: number) {
  return `¥${Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function assetProfilePath(id?: number | string | null) {
  return id ? `/c8-assets/assets/${id}` : '/c8-assets/inventory-2'
}

function isLinenDamage(d: any) {
  const blob = `${d.asset_category || ''} ${d.item_name || ''} ${d.line || ''}`
  return d.line === 'linen' || /布草|床单|浴巾|枕套|面巾/.test(blob)
}

function isEquipmentAsset(a: any) {
  const cat = String(a.category || '').trim()
  return !!cat && !SUPPLY_CATS.test(cat)
}

/** 使用库内品类字段，不做正则重映射；展示按 Locale */
function normalizeCategory(raw?: string) {
  const s = String(raw || '').trim()
  if (!s) return t('未分类')
  const base = s.split('(')[0].split('（')[0].trim() || t('未分类')
  return localizeSeedText(base) || t(base) || base
}

function parseDate(raw?: string | null) {
  if (!raw) return null
  const d = new Date(String(raw).slice(0, 10))
  return Number.isNaN(d.getTime()) ? null : d
}

function inDateRange(raw: string | null | undefined, start: Date | null, end: Date | null) {
  if (!start && !end) return true
  const d = parseDate(raw)
  if (!d) return false
  if (start && d < start) return false
  if (end && d > end) return false
  return true
}

function periodRanges(p: string) {
  const end = new Date()
  end.setHours(23, 59, 59, 999)
  if (p === 'all') {
    return {
      start: null as Date | null,
      end,
      prevStart: null as Date | null,
      prevEnd: null as Date | null,
    }
  }
  const months = p === '6' ? 6 : 12
  const start = new Date()
  start.setHours(0, 0, 0, 0)
  start.setMonth(start.getMonth() - months)
  const prevEnd = new Date(start)
  prevEnd.setMilliseconds(prevEnd.getMilliseconds() - 1)
  const prevStart = new Date(start)
  prevStart.setMonth(prevStart.getMonth() - months)
  return { start, end, prevStart, prevEnd }
}

function maintRecordDate(m: any) {
  return m.completed_at || m.due_date || m.created_at || ''
}

type FinBuckets = { total: number; buckets: Record<string, number> }

function sumFinancial(
  damages: any[],
  maintenance: any[],
  assetById: Record<number, any>,
  start: Date | null,
  end: Date | null,
): FinBuckets {
  const buckets: Record<string, number> = {}
  let total = 0
  const add = (cat: string, amt: number) => {
    if (amt <= 0) return
    total += amt
    buckets[cat] = (buckets[cat] || 0) + amt
  }
  for (const d of damages) {
    if (!inDateRange(d.created_at, start, end)) continue
    add(normalizeCategory(d.asset_category), Number(d.fee || 0))
  }
  for (const m of maintenance) {
    if (m.status !== 'done') continue
    const asset = assetById[Number(m.asset_id)]
    if (!asset || !isEquipmentAsset(asset)) continue
    if (!inDateRange(maintRecordDate(m), start, end)) continue
    add(normalizeCategory(asset.category), Number(m.cost || 0))
  }
  return { total, buckets }
}

function rebuild() {
  const { damages, assets, alerts, assetInsights, maintenance } = raw.value
  const assetDamages = damages.filter((d) => !isLinenDamage(d))
  const assetById = Object.fromEntries(assets.map((a) => [a.id, a]))
  const { start, end, prevStart, prevEnd } = periodRanges(period.value)

  const current = sumFinancial(assetDamages, maintenance, assetById, start, end)
  const previous =
    period.value === 'all'
      ? { total: 0, buckets: {} as Record<string, number> }
      : sumFinancial(assetDamages, maintenance, assetById, prevStart, prevEnd)

  const items = Object.entries(current.buckets)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
  const totalNum = current.total
  const denom = Math.max(1, totalNum)

  let delta = ''
  if (period.value !== 'all' && previous.total > 0) {
    const pct = Math.round(((totalNum - previous.total) / previous.total) * 100)
    delta = `${pct >= 0 ? '+' : ''}${pct}% ${t('较上期')}`
  }

  fin.value = {
    total: money(totalNum),
    delta,
    items: items.map((it, i) => ({
      name: it.name,
      value: money(it.value),
      pct: Math.round((it.value / denom) * 100),
      colorCls: BAR_COLORS[i % BAR_COLORS.length],
    })),
  }

  const periodDamages = assetDamages.filter((d) => inDateRange(d.created_at, start, end))
  const openAlerts = alerts.filter((a) => a.status === 'open')
  const periodMaint = maintenance.filter((m) => {
    if (m.status !== 'done') return false
    const asset = assetById[Number(m.asset_id)]
    return asset && isEquipmentAsset(asset) && inDateRange(maintRecordDate(m), start, end)
  })
  attributionInputStats.value = {
    damage: periodDamages.length,
    alert: openAlerts.length,
    maintenance: periodMaint.length,
  }

  const assetMap = Object.fromEntries(assets.map((a) => [a.id, a.name || t('设备')]))
  priorityAssets.value = assetInsights
    .filter((x) => x.asset_id && x.status === 'open')
    .sort((a, b) => {
      const w = (c: string) => insightCategoryWeight(c)
      return (
        w(String(b.category)) - w(String(a.category)) ||
        String(a.biz_date || '').localeCompare(String(b.biz_date || ''))
      )
    })
    .slice(0, 8)
    .map((x, idx) => ({
      rank: idx + 1,
      assetId: Number(x.asset_id),
      title: localizeSeedText(String(x.title || '')),
      category: String(x.category || 'insight'),
      badge: insightCategoryLabel(x.category),
      tier: insightCategoryTier(x.category),
      name: localizeSeedText(assetMap[x.asset_id] || String(x.title || t('设备'))),
    }))

  const sug: Sug[] = []
  const openMaint = maintenance.filter((m) => m.status !== 'done').length
  const highAlerts = alerts.filter((a) => a.severity === 'high').length
  if (openMaint || highAlerts || priorityAssets.value.length) {
    sug.push({
      title: t('低入住时段集中预防性维保'),
      badge: t('维保优化'),
      badgeCls: 'bg-secondary-container text-on-secondary-container border-secondary/20',
      glow: false,
      insight: highAlerts
        ? t('当前有 {n} 项高优告警、{m} 项待办维保，建议优先消化高风险项。', {
            n: highAlerts,
            m: openMaint,
          })
        : t('当前有 {n} 项待办维保，可结合排期日历统筹安排。', { n: openMaint }),
      strategy: t(
        '建议在入住低谷时段（11:00–14:00）安排工程巡查与预防性维护，减少对客干扰并降低紧急抢修概率。',
      ),
      actions: [
        { t: t('查看排期日历'), primary: true, to: '/c8-assets/tracking?view=calendar' },
        { t: t('工单列表'), primary: false, to: '/c8-assets/tracking' },
      ],
    })
  }
  for (const x of assetInsights.filter(
    (i) => !i.asset_id && ['replace', 'roi', 'maintain'].includes(i.category),
  )) {
    const high = x.category === 'replace' || x.category === 'roi'
    sug.push({
      title: localizeSeedText(x.title),
      badge: high ? t('品类策略') : t('维保优化'),
      badgeCls: high
        ? 'bg-error-container text-on-error-container border-error/20'
        : 'bg-secondary-container text-on-secondary-container border-secondary/20',
      glow: high,
      insight: localizeSeedText(x.recommendation || ''),
      strategy: x.impact_amount
        ? t('预计相关成本约 {amt}；建议从资产清单按品类下钻评估。', {
            amt: money(Number(x.impact_amount)),
          })
        : t('建议结合健康分与维保履历评估置换窗口。'),
      actions: [
        { t: t('资产清单'), primary: true, to: '/c8-assets/inventory-2' },
        { t: t('维修追踪'), primary: false, to: '/c8-assets/tracking' },
      ],
    })
  }
  if (sug[0]) sug[0].glow = true
  suggestions.value = sug.slice(0, 6)

  emptyHint.value = totalNum <= 0 ? ASSETS_EMPTY : ''
}

function priorityIconCls(priority?: string) {
  if (priority === 'high') return ICON_CLS[0]
  if (priority === 'low') return ICON_CLS[2]
  return ICON_CLS[1]
}

function mapAttributionItems(items: any[]): Cause[] {
  const index = buildWorkOrderIndex(raw.value)
  return (items || []).map((it) => {
    const evidence = Array.isArray(it.evidence)
      ? it.evidence
          .map((x: unknown) => String(x).trim())
          .filter(Boolean)
          .slice(0, 3)
      : []
    const refsRaw = Array.isArray(it.data_refs)
      ? it.data_refs
      : Array.isArray(it.refs)
        ? it.refs
        : Array.isArray(it.related_items)
          ? it.related_items
          : []
    const refLinks: RefLink[] = refsRaw.slice(0, 4).map((r: unknown) => {
      const label =
        typeof r === 'object' && r !== null
          ? String((r as { label?: string }).label || '').trim()
          : String(r).trim()
      const task = resolveWorkOrderRef(r as any, index)
      return {
        label: label || task?.title || '—',
        task,
      }
    })
    return {
      iconCls: priorityIconCls(it.priority),
      count: localizeSeedText(String(it.count || t('1 起'))),
      title: localizeSeedText(String(it.title || '—')),
      rootCause: localizeSeedText(String(it.root_cause || '')),
      mechanism: localizeSeedText(String(it.mechanism || '')),
      evidence: (evidence.length
        ? evidence
        : it.description
          ? [String(it.description).slice(0, 80)]
          : []
      ).map((e) => localizeSeedText(e)),
      refLinks: refLinks.map((r) => ({ ...r, label: localizeSeedText(r.label) })),
      actionHint: localizeSeedText(String(it.action_hint || '')),
      desc: localizeSeedText(String(it.description || it.root_cause || '').slice(0, 120)),
      priority: it.priority,
    }
  })
}

function openRefDrawer(link: RefLink) {
  if (!link.task) return
  selectedWo.value = link.task
  woDrawerOpen.value = true
}

function closeWoDrawer() {
  woDrawerOpen.value = false
  selectedWo.value = null
}

function localizeInsightHtml(raw: string) {
  // 仅替换区块标题节点，避免把正文里的「建议…」误替换
  let html = String(raw || '')
  html = html.replace(/>事实</g, `>${t('事实')}<`).replace(/>建议</g, `>${t('建议')}<`)
  return html
}

function applyAttributionResult(data: any) {
  attributionSource.value = data.source || 'llm'
  attributionHtml.value = localizeInsightHtml(String(data.narrative_html || ''))
  attributionActions.value = (Array.isArray(data.actions) ? data.actions : []).map((a: any) => ({
    ...a,
    title: localizeSeedText(a?.title),
    body: localizeSeedText(a?.body),
    action_label: t(String(a?.action_label || '')) || a?.action_label,
  }))
  attributionModelMeta.value = {
    provider: data.provider,
    provider_label: data.provider_label,
    model: data.model,
  }
  if (data.source === 'unavailable' || data.source === 'fallback') {
    attributionError.value = t('未能调用大模型生成归因。下列如有条目，来自报损数据，不是 AI 结论。')
    causes.value = []
    return
  }
  if (data.source === 'empty' || !data.items?.length) {
    attributionError.value = t('当前周期内数据不足，未生成归因结论')
    causes.value = []
    return
  }
  causes.value = mapAttributionItems(data.items)
  attributionError.value = ''
}

function resetAttribution() {
  causes.value = []
  attributionSource.value = null
  attributionError.value = ''
  attributionHtml.value = ''
  attributionActions.value = []
  attributionModelMeta.value = null
  attributionLoading.value = false
  attributionExecuting.value = null
}

async function triggerAttributionAnalysis(force = false) {
  if (attributionLoading.value) return
  const stats = attributionInputStats.value
  if (!stats.damage && !stats.alert) {
    attributionError.value = t('当前周期内无报损单或开放告警，无法归因分析')
    toast(attributionError.value, false)
    return
  }

  attributionLoading.value = true
  attributionError.value = ''
  attributionHtml.value = ''
  attributionActions.value = []
  causes.value = []
  attributionSource.value = null

  try {
    const data = await api.lossAttributionAnalyze(hotelStore.hotelId, period.value, force)
    applyAttributionResult(data || {})
  } catch (e: any) {
    attributionError.value = e?.message || t('归因分析失败')
    toast(attributionError.value, false)
  } finally {
    attributionLoading.value = false
  }
}

async function runAttributionAction(a: any) {
  if (!a || attributionExecuting.value) return
  attributionExecuting.value = String(a.id || a.action_type || 'act')
  try {
    if (a.action_type === 'open_path' && a.path) {
      router.push(String(a.path))
      toast(a.action_label || t('已打开'), true)
      return
    }
    toast(a.action_label || t('已记录'), true)
  } finally {
    attributionExecuting.value = null
  }
}

const attributionSourceLabel = computed(() => {
  if (attributionSource.value === 'cache') return t('AI 解读')
  if (attributionSource.value === 'llm') return t('AI 解读')
  if (attributionSource.value === 'unavailable' || attributionSource.value === 'fallback')
    return t('AI 暂不可用')
  return ''
})

const FLOW_STEPS = [
  { n: '01', title: t('损耗总览'), desc: t('花了多少钱') },
  { n: '02', title: t('财务结构'), desc: t('品类分布') },
  { n: '03', title: t('原因分析'), desc: t('为何反复损坏') },
  { n: '04', title: t('行动决策'), desc: t('修换与排期') },
]

function goList() {
  router.push('/c8-assets/tracking')
}

function goBack() {
  router.push('/c8-assets/inventory-2')
}

function onAction(to?: string) {
  if (to) router.push(to)
}

async function load() {
  resetAttribution()
  try {
    const [assetBoard, supplyBoard] = await Promise.all([
      api.assetsBoard(hotelStore.hotelId),
      api.suppliesBoard(hotelStore.hotelId).catch(() => null),
    ])
    const damages = (supplyBoard?.damages || []).filter((d: any) => !isLinenDamage(d))
    raw.value = {
      damages,
      assets: assetBoard?.assets || [],
      alerts: assetBoard?.alerts || [],
      assetInsights: assetBoard?.insights || [],
      maintenance: assetBoard?.maintenance || [],
    }
    rebuild()
  } catch {
    raw.value = { damages: [], assets: [], alerts: [], assetInsights: [], maintenance: [] }
    rebuild()
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(period, () => {
  resetAttribution()
  rebuild()
})
</script>

<template>
  <div class="page loss-page">
    <RoomOpsNav />
    <!-- 页头 -->
    <header class="loss-header">
      <div class="loss-header-main">
        <h1 class="loss-title">{{ t('报损情况') }}</h1>
      </div>
      <div class="loss-toolbar">
        <label class="period-label">
          <span>{{ t('统计周期') }}</span>
          <select v-model="period" class="period-select">
            <option value="6">{{ t('过去 6 个月') }}</option>
            <option value="12">{{ t('过去 12 个月') }}</option>
            <option value="all">{{ t('全部历史') }}</option>
          </select>
        </label>
        <button type="button" class="back-btn" @click="goBack">{{ t('返回资产清单') }}</button>
      </div>
    </header>

    <!-- 流程导引 -->
    <nav class="loss-flow" :aria-label="t('分析步骤')">
      <div v-for="(step, i) in FLOW_STEPS" :key="step.n" class="flow-item">
        <span class="flow-n">{{ step.n }}</span>
        <div class="flow-text">
          <strong>{{ step.title }}</strong>
          <span>{{ step.desc }}</span>
        </div>
        <span v-if="i < FLOW_STEPS.length - 1" class="flow-arrow material-symbols-outlined"
          >chevron_right</span
        >
      </div>
    </nav>

    <!-- 01 损耗总览 -->
    <section class="loss-section">
      <div class="section-head">
        <span class="section-step">01</span>
        <div>
          <h2 class="section-title">{{ t('损耗总览') }}</h2>
        </div>
      </div>
      <div class="kpi-strip">
        <div class="kpi-main">
          <p class="kpi-label">{{ t('损耗总额') }}</p>
          <div class="kpi-val-row">
            <span class="kpi-val">{{ fin.total }}</span>
            <span
              v-if="fin.delta"
              class="kpi-delta"
              :class="fin.delta.startsWith('+') ? 'up' : 'down'"
              >{{ fin.delta }}</span
            >
          </div>
        </div>
        <div class="kpi-stat">
          <p class="kpi-label">{{ t('设备报损') }}</p>
          <p class="kpi-num">
            {{ attributionInputStats.damage }} <small>{{ t('条') }}</small>
          </p>
        </div>
        <div class="kpi-stat">
          <p class="kpi-label">{{ t('开放告警') }}</p>
          <p class="kpi-num">
            {{ attributionInputStats.alert }} <small>{{ t('条') }}</small>
          </p>
        </div>
        <div class="kpi-stat">
          <p class="kpi-label">{{ t('已完成维保') }}</p>
          <p class="kpi-num">
            {{ attributionInputStats.maintenance }} <small>{{ t('条') }}</small>
          </p>
        </div>
      </div>
    </section>

    <!-- 02 财务结构 -->
    <section class="loss-section">
      <div class="section-head">
        <span class="section-step">02</span>
        <div>
          <h2 class="section-title">{{ t('财务结构') }}</h2>
        </div>
      </div>
      <div class="panel">
        <p v-if="!fin.items.length" class="empty-hint">{{ emptyHint || ASSETS_EMPTY }}</p>
        <div v-else class="fin-bars">
          <div v-for="(it, i) in fin.items" :key="i" class="fin-bar-row">
            <div class="fin-bar-meta">
              <span class="fin-bar-name">{{ it.name }}</span>
              <span class="fin-bar-val">{{ it.value }} · {{ it.pct }}%</span>
            </div>
            <div class="fin-bar-track">
              <div class="fin-bar-fill" :class="it.colorCls" :style="{ width: it.pct + '%' }" />
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 03 原因分析 · 触发式 AI（对齐积分倍率智能建议） -->
    <section class="loss-section">
      <div class="section-head section-head-actions">
        <div class="section-head-left">
          <span class="section-step">03</span>
          <div>
            <h2 class="section-title">{{ t('高频损坏归因') }}</h2>
          </div>
        </div>
        <div class="section-actions">
          <button type="button" class="link-btn" @click="goList">{{ t('维修追踪') }}</button>
        </div>
      </div>

      <section v-if="commercialEnabled()" class="ai-block panel">
        <div class="ai-head">
          <div class="ai-head-l">
            <h3>{{ t('损坏归因智能建议') }}</h3>
            <span class="ai-mark">AI</span>
          </div>
          <button
            type="button"
            class="ai-run"
            :disabled="attributionLoading"
            @click="triggerAttributionAnalysis(!!(attributionHtml || causes.length))"
          >
            {{
              attributionLoading
                ? t('生成中…')
                : attributionHtml || causes.length
                  ? t('重新归因')
                  : t('生成归因建议')
            }}
          </button>
        </div>

        <template v-if="attributionLoading">
          <p class="ai-wait">{{ t('正在归纳报损与告警中的重复故障模式…') }}</p>
        </template>
        <template v-else-if="attributionHtml || causes.length">
          <p class="ai-meta">
            <span>{{ attributionSourceLabel || t('AI 解读') }}</span>
            <span v-if="formatAiModelMeta(attributionModelMeta)" class="conf-pill">{{
              formatAiModelMeta(attributionModelMeta)
            }}</span>
            <span
              v-if="attributionSource === 'fallback' || attributionSource === 'unavailable'"
              class="conf-pill"
              >{{ t('AI 暂不可用') }}</span
            >
          </p>
          <div v-if="attributionHtml" class="ai-insight-body" v-html="attributionHtml" />
          <div v-if="attributionActions.length" class="dx-actions">
            <div class="dx-actions-h">{{ t('可执行操作') }}</div>
            <div class="dx-action-list">
              <article v-for="a in attributionActions" :key="a.id" class="dx-action-card">
                <div class="dx-action-title">{{ a.title }}</div>
                <div v-if="a.body" class="dx-action-body">{{ a.body }}</div>
                <button
                  type="button"
                  class="dx-act"
                  :disabled="!!attributionExecuting"
                  @click="runAttributionAction(a)"
                >
                  {{ attributionExecuting === a.id ? t('执行中…') : a.action_label || t('执行') }}
                </button>
              </article>
            </div>
          </div>
          <div v-if="causes.length" class="attr-grid">
            <div
              v-for="(c, i) in causes"
              :key="i"
              class="attr-card"
              :class="'pri-' + (c.priority || 'mid')"
            >
              <div class="attr-card-header">
                <h3 class="attr-card-title">{{ c.title }}</h3>
                <span class="attr-card-count">{{ c.count }}</span>
              </div>
              <div class="attr-mini-card">
                <div class="attr-mini-card-head">{{ t('根因') }}</div>
                <div class="attr-mini-card-body">
                  <template v-if="c.rootCause">
                    <p class="attr-block-lead">{{ c.rootCause }}</p>
                    <p v-if="c.mechanism" class="attr-block-sub">{{ c.mechanism }}</p>
                  </template>
                  <p v-else class="attr-mini-empty">{{ t('暂无') }}</p>
                </div>
              </div>
              <div class="attr-mini-card">
                <div class="attr-mini-card-head">{{ t('数据依据') }}</div>
                <div class="attr-mini-card-body">
                  <ul v-if="c.evidence.length" class="attr-evidence-list">
                    <li v-for="(e, j) in c.evidence" :key="j">{{ e }}</li>
                  </ul>
                  <p v-else class="attr-mini-empty">{{ t('暂无') }}</p>
                </div>
              </div>
              <div class="attr-mini-card">
                <div class="attr-mini-card-head">{{ t('涉及记录') }}</div>
                <div class="attr-mini-card-body">
                  <div v-if="c.refLinks.length" class="attr-ref-chips">
                    <button
                      v-for="(r, j) in c.refLinks"
                      :key="j"
                      type="button"
                      class="attr-ref-chip"
                      :class="{ clickable: !!r.task }"
                      :disabled="!r.task"
                      @click="openRefDrawer(r)"
                    >
                      {{ r.label }}
                    </button>
                  </div>
                  <p v-else class="attr-mini-empty">{{ t('暂无') }}</p>
                </div>
              </div>
              <p v-if="c.actionHint" class="attr-action-hint">
                <span class="material-symbols-outlined">tips_and_updates</span>
                {{ c.actionHint }}
              </p>
            </div>
          </div>
          <p v-if="attributionError" class="ai-soft-err">{{ attributionError }}</p>
        </template>
        <p
          v-if="attributionError && !attributionLoading && !(attributionHtml || causes.length)"
          class="ai-err"
        >
          {{ attributionError }}
        </p>
      </section>
      <WorkOrderDrawer :open="woDrawerOpen" :task="selectedWo" @close="closeWoDrawer" />
    </section>

    <!-- 04 行动决策 -->
    <section class="loss-section">
      <div class="section-head">
        <span class="section-step">04</span>
        <div>
          <h2 class="section-title">{{ t('行动决策') }}</h2>
        </div>
      </div>
      <div class="action-grid">
        <!-- 左：单台优先队列 -->
        <div class="panel action-col">
          <div class="action-col-head">
            <h3 class="action-col-title">{{ t('设备优先评估') }}</h3>
          </div>
          <div class="priority-algo-box">
            <p class="priority-algo-title">
              <span class="material-symbols-outlined">info</span>
              {{ t('优先排序规则') }}
            </p>
            <ol class="priority-algo-list">
              <li>
                <strong>{{ t('入选') }}</strong
                >{{ t('：仅「开放中」且已绑定单台设备的洞察记录') }}
              </li>
              <li>
                <strong>{{ t('类型权重') }}</strong
                >{{ t('：建议更换、置换经济性 → 高优先；健康风险、维保建议、盘点差异 → 次优先') }}
              </li>
              <li>
                <strong>{{ t('次序') }}</strong
                >{{ t('：先按类型权重，再按洞察日期；列表仅展示前 8 台，自上而下优先级递减') }}
              </li>
            </ol>
          </div>
          <div v-if="priorityAssets.length" class="priority-list">
            <button
              v-for="p in priorityAssets"
              :key="`${p.assetId}-${p.rank}`"
              type="button"
              class="priority-row"
              @click="router.push(assetProfilePath(p.assetId))"
            >
              <span class="priority-rank" :class="'tier-' + p.tier">P{{ p.rank }}</span>
              <div class="priority-row-main">
                <span class="priority-name">{{ p.name }}</span>
                <span class="priority-insight">{{ p.title }}</span>
              </div>
              <span class="priority-badge" :class="'cat-' + p.category">{{ p.badge }}</span>
              <span class="material-symbols-outlined priority-arrow">chevron_right</span>
            </button>
          </div>
          <p v-else class="action-empty">{{ t('当前无开放中的单台评估洞察') }}</p>
        </div>

        <!-- 右：策略建议 -->
        <div class="panel action-col action-col-wide">
          <div class="action-col-head">
            <h3 class="action-col-title ai-text-gradient">{{ t('更新与维保策略') }}</h3>
          </div>
          <p v-if="!suggestions.length" class="action-empty">{{ emptyHint || ASSETS_EMPTY }}</p>
          <div v-else class="sug-list">
            <div v-for="(s, i) in suggestions" :key="i" class="sug-item" :class="{ glow: s.glow }">
              <div class="sug-head">
                <h4 class="sug-title">{{ s.title }}</h4>
                <span class="sug-badge" :class="s.badgeCls">{{ s.badge }}</span>
              </div>
              <p class="sug-insight">{{ s.insight }}</p>
              <p class="sug-strategy">{{ s.strategy }}</p>
              <div class="sug-actions">
                <button
                  v-for="(a, ai) in s.actions"
                  :key="ai"
                  type="button"
                  class="sug-btn"
                  :class="{ primary: a.primary }"
                  @click="onAction(a.to)"
                >
                  {{ a.t }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.loss-page {
  width: 100%;
  max-width: none;
}

/* ── 页头 ── */
.loss-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
.loss-title {
  margin: 0 0 6px;
  font-size: 28px;
  font-weight: 700;
  color: var(--on-surface);
}
.loss-title-sub {
  font-size: 20px;
  font-weight: 500;
  color: var(--outline);
}
.loss-desc {
  margin: 0;
  font-size: 14px;
  color: var(--on-surface-variant);
}
.loss-toolbar {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}
.period-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--on-surface-variant);
}
.period-select {
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  background: var(--surface);
  color: var(--on-surface);
  min-width: 140px;
}
.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  letter-spacing: 0.04em;
}
.back-btn {
  border: 1px solid var(--primary);
  background: var(--primary);
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-primary, #fff);
  cursor: pointer;
  height: 36px;
}
.back-btn:hover {
  filter: brightness(0.95);
  background: var(--primary);
  color: var(--on-primary, #fff);
}

/* ── 流程导引 ── */
.loss-flow {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 28px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
}
.flow-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  position: relative;
}
.flow-n {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--primary-container);
  color: var(--on-primary-container);
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.flow-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.flow-text strong {
  font-size: 13px;
  color: var(--on-surface);
}
.flow-text span {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.flow-arrow {
  display: none;
}

/* ── 分区通用 ── */
.loss-section {
  margin-bottom: 28px;
}
.section-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.section-head-actions {
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.section-head-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.section-step {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--surface-container-high);
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}
.section-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--on-surface);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.section-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.section-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.link-btn {
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 8px 4px;
  font-family: inherit;
}
.panel {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 20px;
}

/* ── 01 KPI 条 ── */
.kpi-strip {
  display: grid;
  grid-template-columns: 1.4fr repeat(3, 1fr);
  gap: 12px;
}
.kpi-main,
.kpi-stat {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 16px 18px;
}
.kpi-main {
  border-left: 4px solid var(--primary);
  background: linear-gradient(105deg, rgba(216, 226, 255, 0.5), rgba(255, 255, 255, 0.98));
}
.kpi-label {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--on-surface-variant);
}
.kpi-val-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}
.kpi-val {
  font-size: 32px;
  font-weight: 700;
  color: var(--on-surface);
  font-variant-numeric: tabular-nums;
}
.kpi-delta {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
}
.kpi-delta.up {
  background: var(--error-container);
  color: var(--on-error-container);
}
.kpi-delta.down {
  background: var(--primary-container);
  color: var(--on-primary-container);
}
.kpi-num {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: var(--on-surface);
  font-variant-numeric: tabular-nums;
}
.kpi-num small {
  font-size: 13px;
  font-weight: 500;
  color: var(--on-surface-variant);
  margin-left: 2px;
}

/* ── 02 财务条 ── */
.fin-bars {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.fin-bar-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
  font-size: 13px;
}
.fin-bar-name {
  color: var(--on-surface);
  font-weight: 600;
}
.fin-bar-val {
  color: var(--on-surface-variant);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.fin-bar-track {
  height: 8px;
  background: var(--surface-container-highest);
  border-radius: 999px;
  overflow: hidden;
}
.fin-bar-fill {
  height: 100%;
  border-radius: 999px;
  min-width: 2px;
}

/* ── 03 归因 AI（对齐积分倍率智能建议） ── */
.ai-block {
  --ai-brand: var(--primary);
  --ai-soft: color-mix(in srgb, var(--primary) 8%, var(--surface));
  --ai-line: var(--outline-variant);
  --ai-ink2: var(--on-surface-variant);
  --ai-ink3: var(--outline);
  margin-bottom: 0;
}
.ai-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}
.ai-head h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 800;
  color: var(--on-surface);
}
.ai-head-l {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-mark {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--ai-brand);
  background: var(--ai-soft);
  border: 1px solid color-mix(in srgb, var(--primary) 28%, var(--outline-variant));
  border-radius: 4px;
  padding: 1px 6px;
}
.ai-run {
  border: none;
  background: var(--ai-brand);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
  font-family: inherit;
}
.ai-run:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.ai-wait,
.ai-idle {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--ai-ink3);
  line-height: 1.55;
}
.ai-meta {
  font-size: 11px;
  color: var(--ai-ink3);
  margin: 0 0 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.conf-pill {
  background: var(--surface-container-highest);
  border-radius: 4px;
  padding: 1px 6px;
  font-weight: 700;
  color: var(--ai-ink2);
}
.ai-err {
  font-size: 12px;
  color: var(--error);
  background: color-mix(in srgb, var(--error) 8%, var(--surface));
  border-radius: 6px;
  padding: 8px 10px;
  margin-top: 8px;
}
.ai-soft-err {
  font-size: 12px;
  color: var(--ai-ink3);
  margin: 8px 0 0;
}
.ai-insight-body {
  margin-bottom: 10px;
}
.ai-insight-body :deep(.ai-insight) {
  display: grid;
  gap: 8px;
}
.ai-insight-body :deep(.ai-insight-sec) {
  border-radius: 10px;
  padding: 10px 12px;
  border: 1px solid var(--ai-line);
  background: var(--surface-container-low, #f8fafc);
}
.ai-insight-body :deep(.ai-insight-h) {
  font-size: 12px;
  font-weight: 800;
  color: var(--ai-brand);
  margin-bottom: 6px;
}
.ai-insight-body :deep(ul) {
  margin: 0;
  padding-left: 18px;
}
.ai-insight-body :deep(li) {
  font-size: 12px;
  line-height: 1.45;
  color: var(--on-surface);
  margin-bottom: 3px;
}
.dx-actions {
  margin-top: 4px;
}
.dx-actions-h {
  font-size: 12px;
  font-weight: 800;
  color: var(--ai-ink2);
  margin-bottom: 8px;
}
.dx-action-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}
.dx-action-card {
  border: 1px solid var(--ai-line);
  border-radius: 10px;
  padding: 10px;
  background: var(--surface);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dx-action-title {
  font-size: 13px;
  font-weight: 700;
}
.dx-action-body {
  font-size: 12px;
  color: var(--ai-ink2);
  line-height: 1.45;
  flex: 1;
}
.dx-act {
  align-self: flex-start;
  margin-top: 2px;
  border: 1px solid color-mix(in srgb, var(--primary) 28%, var(--outline-variant));
  background: var(--ai-soft);
  color: var(--ai-brand);
  font-size: 12px;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-family: inherit;
}
.dx-act:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
@media (min-width: 900px) {
  .ai-insight-body :deep(.ai-insight) {
    grid-template-columns: 1fr 1fr;
  }
  .dx-action-list {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }
}
.attr-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 14px;
  align-items: start;
}
.attr-card {
  display: grid;
  grid-template-rows: subgrid;
  grid-row: span 5;
  gap: 8px;
  background: var(--surface);
  padding: 14px;
  border-radius: 10px;
  border: 1px solid rgba(193, 198, 214, 0.55);
  text-align: left;
  font-family: inherit;
}
.attr-card.pri-high {
  border-left: 3px solid #ef4444;
}
.attr-card.pri-mid {
  border-left: 3px solid #f59e0b;
}
.attr-card.pri-low {
  border-left: 3px solid #94a3b8;
}
.attr-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  min-height: 40px;
}
.attr-card-count {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface-variant);
  line-height: 1.35;
  padding-top: 2px;
}
.attr-card-title {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--on-surface);
  line-height: 1.35;
  min-height: calc(1.35em * 2);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}
.attr-mini-card {
  display: flex;
  flex-direction: column;
  background: var(--surface-container-lowest, #f8f9fc);
  border: 1px solid rgba(193, 198, 214, 0.5);
  border-radius: 8px;
  overflow: hidden;
  min-height: 0;
}
.attr-mini-card-head {
  height: 28px;
  min-height: 28px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  font-size: 11px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0.04em;
  background: #e8f4fc;
  border-bottom: 1px solid #c5e4f8;
  flex-shrink: 0;
}
.attr-mini-card-body {
  padding: 8px 10px 10px;
  flex: 1;
  min-height: 52px;
}
.attr-mini-empty {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.attr-block-lead {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--on-surface);
  line-height: 1.5;
}
.attr-block-sub {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.attr-evidence-list {
  margin: 0;
  padding: 0 0 0 14px;
  font-size: 11px;
  color: var(--on-surface);
  line-height: 1.5;
}
.attr-evidence-list li + li {
  margin-top: 4px;
}
.attr-ref-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.attr-ref-chip {
  display: inline-block;
  padding: 3px 8px;
  font-size: 10px;
  line-height: 1.35;
  color: var(--on-surface);
  background: var(--surface);
  border: 1px solid rgba(193, 198, 214, 0.55);
  border-radius: 5px;
  font-family: inherit;
}
.attr-ref-chip.clickable {
  cursor: pointer;
  color: var(--primary);
  border-color: color-mix(in srgb, var(--primary) 35%, var(--outline-variant));
  background: color-mix(in srgb, var(--primary) 6%, var(--surface));
}
.attr-ref-chip.clickable:hover {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, var(--surface));
}
.attr-ref-chip:disabled {
  cursor: default;
  opacity: 0.75;
}
.attr-action-hint {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  margin: 0;
  padding: 8px 10px;
  font-size: 11px;
  line-height: 1.45;
  color: var(--on-surface-variant);
  background: color-mix(in srgb, var(--tertiary) 6%, var(--surface));
  border-radius: 6px;
  border: 1px dashed color-mix(in srgb, var(--tertiary) 25%, transparent);
}
.attr-action-hint .material-symbols-outlined {
  font-size: 14px;
  color: var(--tertiary);
  flex-shrink: 0;
  margin-top: 1px;
}
.attr-action-hint.is-placeholder {
  visibility: hidden;
  pointer-events: none;
  border-color: transparent;
  background: transparent;
}
.attr-root {
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--on-surface);
  line-height: 1.45;
}
.attr-root strong {
  display: block;
  font-size: 10px;
  font-weight: 700;
  color: var(--tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 2px;
}
.attr-card-desc {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}

/* ── 04 行动决策 ── */
.action-grid {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(320px, 1.6fr);
  gap: 16px;
  align-items: start;
}
.action-col-head {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--outline-variant);
}
.action-col-title {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 700;
  color: var(--on-surface);
}
.action-col-sub {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.action-empty {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant);
  text-align: center;
  padding: 24px 12px;
}
.priority-algo-box {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--primary) 5%, var(--surface));
  border: 1px solid color-mix(in srgb, var(--primary) 18%, var(--outline-variant));
}
.priority-algo-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface);
}
.priority-algo-title .material-symbols-outlined {
  font-size: 16px;
  color: var(--primary);
}
.priority-algo-list {
  margin: 0;
  padding-left: 18px;
  font-size: 11px;
  line-height: 1.55;
  color: var(--on-surface-variant);
}
.priority-algo-list li + li {
  margin-top: 4px;
}
.priority-algo-list strong {
  color: var(--on-surface);
  font-weight: 600;
}
.priority-algo-list code {
  font-size: 10px;
  padding: 0 4px;
  border-radius: 4px;
  background: var(--surface-container-low);
}
.priority-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.priority-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--outline-variant);
  border-radius: 10px;
  background: var(--surface);
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: border-color 0.15s;
}
.priority-row:hover {
  border-color: var(--primary);
}
.priority-rank {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 800;
  font-family: 'Roboto Mono', monospace;
}
.priority-rank.tier-high {
  background: #fee2e2;
  color: #b91c1c;
}
.priority-rank.tier-mid {
  background: #e0f2fe;
  color: #0369a1;
}
.priority-row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.priority-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--on-surface);
}
.priority-insight {
  font-size: 11px;
  color: var(--on-surface-variant);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.priority-badge {
  flex-shrink: 0;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
}
.priority-badge.cat-replace,
.priority-badge.cat-roi {
  background: #fee2e2;
  color: #b91c1c;
}
.priority-badge.cat-health {
  background: #dbeafe;
  color: #1d4ed8;
}
.priority-badge.cat-maintain {
  background: #e0e7ff;
  color: #4338ca;
}
.priority-badge.cat-audit {
  background: #f1f5f9;
  color: #475569;
}
.priority-badge.cat-insight {
  background: var(--surface-container-high);
  color: var(--on-surface-variant);
}
.priority-arrow {
  font-size: 18px;
  color: var(--on-surface-variant);
  flex-shrink: 0;
}
.sug-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sug-item {
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface);
}
.sug-item.glow {
  border-left: 3px solid var(--tertiary);
  background: linear-gradient(105deg, rgba(248, 216, 255, 0.25), rgba(255, 255, 255, 0.98));
}
.sug-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}
.sug-title {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--on-surface);
  line-height: 1.35;
}
.sug-badge {
  flex-shrink: 0;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid transparent;
  font-weight: 600;
}
.sug-insight {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--on-surface-variant);
  line-height: 1.5;
}
.sug-strategy {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--on-surface);
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--surface-container);
  line-height: 1.45;
}
.sug-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.sug-btn {
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--outline-variant);
  background: var(--surface);
  color: var(--on-surface-variant);
  font-family: inherit;
}
.sug-btn.primary {
  border-color: var(--primary);
  color: var(--primary);
}
.sug-btn:hover {
  background: var(--surface-container);
}
.ai-text-gradient {
  background: linear-gradient(90deg, #005bbf, #a84fce);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.empty-hint {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant);
  text-align: center;
  padding: 16px 0;
}

@media (max-width: 900px) {
  .loss-flow {
    grid-template-columns: 1fr 1fr;
  }
  .kpi-strip {
    grid-template-columns: 1fr 1fr;
  }
  .kpi-main {
    grid-column: 1 / -1;
  }
  .attr-grid {
    grid-template-columns: 1fr;
  }
  .attr-card {
    display: flex;
    flex-direction: column;
    grid-row: auto;
    gap: 8px;
  }
  .action-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 520px) {
  .loss-flow {
    grid-template-columns: 1fr;
  }
  .kpi-strip {
    grid-template-columns: 1fr;
  }
}
</style>
