<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 经营总览 · 营收预测
 * 数据来自夜审 / 订单 / 房型；「智能问数」从候选异常中选题生成建议；本页不改价。
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { api } from '../../lib/api'
import { loadAskDataCache, pricingQueryFromIssue, saveAskDataCache } from '../../lib/askDataBridge'
import { hotelStore } from '../../store/hotel'
import { commercialEnabled } from '../../lib/branding'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const error = ref('')
const board = ref<any>(null)
const dismissed = ref<Set<string>>(new Set())
const hoverDay = ref<any>(null)

const findings = ref<any[]>([])
const askLoading = ref(false)
const askError = ref('')
const askStream = ref('')
const askThinking = ref('')
const askThinkOpen = ref(true)
const askMeta = ref<any>(null)
const askWarning = ref('')
const askSource = ref('')
const askGeneratedAt = ref('')
const askModelMeta = ref('')
let askAbort: AbortController | null = null

function resetAskState() {
  findings.value = []
  askStream.value = ''
  askThinking.value = ''
  askThinkOpen.value = true
  askError.value = ''
  askWarning.value = ''
  askSource.value = ''
  askGeneratedAt.value = ''
  askModelMeta.value = ''
  askMeta.value = null
  dismissed.value = new Set()
  askAbort?.abort()
  askAbort = null
}

function persistAskState() {
  saveAskDataCache({
    hotelId: hotelStore.hotelId,
    findings: findings.value,
    askSource: askSource.value,
    askGeneratedAt: askGeneratedAt.value,
    askWarning: askWarning.value,
    askStream: askStream.value,
    askThinking: askThinking.value,
    askModelMeta: askModelMeta.value,
    dismissed: Array.from(dismissed.value),
    savedAt: Date.now(),
  })
}

function tryRestoreAskState() {
  const cached = loadAskDataCache(hotelStore.hotelId)
  if (!cached) return false
  findings.value = Array.isArray(cached.findings) ? cached.findings : []
  askSource.value = cached.askSource || ''
  askGeneratedAt.value = cached.askGeneratedAt || ''
  askWarning.value = cached.askWarning || ''
  askStream.value = cached.askStream || ''
  askThinking.value = cached.askThinking || ''
  askThinkOpen.value = !askStream.value && !!askThinking.value
  askModelMeta.value = cached.askModelMeta || ''
  dismissed.value = new Set(cached.dismissed || [])
  return findings.value.length > 0 || !!askGeneratedAt.value
}

async function scrollToAskData() {
  await nextTick()
  document.getElementById('ask-data')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function load(opts?: { keepAsk?: boolean }) {
  loading.value = true
  error.value = ''
  try {
    board.value = await api.revenueForecast(hotelStore.hotelId)
    if (!opts?.keepAsk) resetAskState()
  } catch (e: any) {
    error.value = e?.message || t('加载失败')
    board.value = null
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const wantRestore = route.query.restore === '1' || route.hash === '#ask-data'
  await load({ keepAsk: wantRestore })
  if (wantRestore && tryRestoreAskState()) {
    await scrollToAskData()
    if (route.query.restore === '1') {
      const { restore: _, ...rest } = route.query
      router.replace({ path: route.path, query: rest, hash: '#ask-data' })
    }
  } else if (wantRestore) {
    // 无缓存时仍滚到问数区，方便重新生成
    await scrollToAskData()
  }
})
watch(
  () => hotelStore.hotelId,
  () => load(),
)

const kpis = computed(() => board.value?.kpis || [])
const daily = computed(() => board.value?.daily || [])
const trend = computed(() => board.value?.trend || [])
const pickup = computed(() => board.value?.pickup || [])
const candidates = computed(() => board.value?.candidates || [])
const visibleFindings = computed(() =>
  findings.value.filter((r: any) => !dismissed.value.has(r.id)),
)

function fmtMoney(n: number | null | undefined) {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return `¥${Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function fmtChg(k: any) {
  if (k.tone === 'warn') return `⚠ ${t(k.chg_label || '需补量')}`
  if (k.tone === 'muted' || k.chg == null) return t(k.chg_label || '') || ''
  const arrow = k.tone === 'down' ? '↓' : '↑'
  const unit = k.chg_unit === 'pt' ? 'pt' : '%'
  return `${arrow} ${Math.abs(Number(k.chg)).toFixed(1)}${unit} ${t(k.chg_label || '同比')}`
}

function fmtKpiVal(k: any) {
  if (k.unit === '¥') return fmtMoney(k.value)
  if (k.unit === '%') return `${Number(k.value).toFixed(0)}%`
  return String(k.value ?? '—')
}

/** 收入柱图 SVG */
const revChartSvg = computed(() => {
  const rows = daily.value
  if (!rows.length) return ''
  const W = 720
  const H = 270
  const padL = 44
  const padR = 14
  const padT = 18
  const padB = 26
  const cw = W - padL - padR
  const ch = H - padT - padB
  const vals = rows.map((d: any) => {
    if (d.is_past && d.revenue_actual != null) return Number(d.revenue_actual)
    return Number(d.revenue_forecast) || 0
  })
  const spVals = rows
    .map((d: any) => d.revenue_same_period)
    .filter((v: any) => v != null)
    .map(Number)
  const maxV = Math.max(...vals, ...(spVals.length ? spVals : [0]), 1) * 1.08
  const n = rows.length
  const slot = cw / n
  const bw = slot * 0.62
  const gap = slot * 0.38
  const x0 = padL + gap / 2
  let todayIdx = rows.findIndex((d: any) => d.is_today)
  if (todayIdx < 0) todayIdx = rows.filter((d: any) => d.is_past).length - 1

  const parts: string[] = [`<svg viewBox="0 0 ${W} ${H}" width="100%" style="display:block">`]
  for (let g = 0; g <= 4; g++) {
    const yy = padT + ch * (g / 4)
    const val = Math.round((maxV * (1 - g / 4)) / 1000)
    parts.push(`<line x1="${padL}" y1="${yy}" x2="${W - padR}" y2="${yy}" stroke="#eef2f7"/>`)
    parts.push(
      `<text x="${padL - 6}" y="${yy + 3}" font-size="9" fill="#9ca3af" text-anchor="end">${val}k</text>`,
    )
  }

  const poly: string[] = []
  for (let i = 0; i < n; i++) {
    const d = rows[i]
    const x = x0 + i * (bw + gap)
    const isPast = !!d.is_past && d.revenue_actual != null
    const v = isPast ? Number(d.revenue_actual) : Number(d.revenue_forecast) || 0
    const bh = ch * (v / maxV)
    const y = padT + ch - bh
    const fill = isPast ? '#2563eb' : 'rgba(37,99,235,0.32)'
    const stroke = isPast ? 'none' : '#2563eb'
    const dash = isPast ? '0' : '3,2'
    parts.push(
      `<rect x="${x}" y="${y}" width="${bw}" height="${Math.max(1, bh)}" rx="2" fill="${fill}" stroke="${stroke}" stroke-dasharray="${dash}"/>`,
    )
    if (d.revenue_same_period != null) {
      const sp = Number(d.revenue_same_period) || 0
      const sy = padT + ch - ch * (sp / maxV)
      const cx = x + bw / 2
      poly.push(`${cx},${sy}`)
      parts.push(`<circle cx="${cx}" cy="${sy}" r="2" fill="#f59e0b"/>`)
    }
    if ((i + 1) % 5 === 0 || i === 0) {
      parts.push(
        `<text x="${x + bw / 2}" y="${H - 8}" font-size="9" fill="#9ca3af" text-anchor="middle">${d.day}${t('日')}</text>`,
      )
    }
  }
  if (poly.length >= 2) {
    parts.push(
      `<polyline points="${poly.join(' ')}" fill="none" stroke="#f59e0b" stroke-width="1.4" stroke-dasharray="4,3" opacity="0.85"/>`,
    )
  }
  if (todayIdx >= 0) {
    const tx = x0 + todayIdx * (bw + gap) + bw / 2
    parts.push(
      `<line x1="${tx}" y1="${padT}" x2="${tx}" y2="${padT + ch}" stroke="#94a3b8" stroke-dasharray="3,3"/>`,
    )
    parts.push(
      `<text x="${tx}" y="${padT - 4}" font-size="9" fill="#64748b" text-anchor="middle">${t('今天')}</text>`,
    )
  }
  parts.push('</svg>')
  return parts.join('')
})

/** 带坐标轴的迷你趋势图 */
function axisLine(
  data: { v: number; sp: number | null; label: string }[],
  color: string,
  yUnit: string,
) {
  if (!data.length) return ''
  const W = 280
  const H = 120
  const padL = 36
  const padR = 8
  const padT = 10
  const padB = 22
  const cw = W - padL - padR
  const ch = H - padT - padB
  const vals = data.flatMap((d) => [d.v, d.sp].filter((x): x is number => x != null))
  let max = Math.max(...vals)
  let min = Math.min(...vals)
  if (max === min) {
    max += 1
    min = Math.max(0, min - 1)
  }
  const span = max - min
  const xAt = (i: number) => padL + cw * (i / Math.max(1, data.length - 1))
  const yAt = (v: number) => padT + ch * (1 - (v - min) / span)

  const parts: string[] = [`<svg viewBox="0 0 ${W} ${H}" width="100%" style="display:block">`]
  // Y 网格 + 刻度
  for (let g = 0; g <= 3; g++) {
    const yy = padT + ch * (g / 3)
    const val = max - (span * g) / 3
    const label =
      yUnit === '%' ? `${val.toFixed(0)}%` : yUnit === '¥' ? `${Math.round(val)}` : val.toFixed(0)
    parts.push(`<line x1="${padL}" y1="${yy}" x2="${W - padR}" y2="${yy}" stroke="#eef2f7"/>`)
    parts.push(
      `<text x="${padL - 4}" y="${yy + 3}" font-size="8" fill="#9ca3af" text-anchor="end">${label}</text>`,
    )
  }
  // 主线
  const main = data.map((d, i) => `${xAt(i)},${yAt(d.v)}`).join(' ')
  parts.push(`<polyline points="${main}" fill="none" stroke="${color}" stroke-width="1.8"/>`)
  // 同期线（有数据才画）
  const spPts = data
    .map((d, i) => (d.sp == null ? null : `${xAt(i)},${yAt(d.sp)}`))
    .filter(Boolean) as string[]
  if (spPts.length >= 2) {
    parts.push(
      `<polyline points="${spPts.join(' ')}" fill="none" stroke="#cbd5e1" stroke-width="1.3" stroke-dasharray="3,2"/>`,
    )
  }
  // X 轴日期（首、中、尾）
  const ticks = [0, Math.floor((data.length - 1) / 2), data.length - 1]
  for (const i of ticks) {
    parts.push(
      `<text x="${xAt(i)}" y="${H - 6}" font-size="8" fill="#9ca3af" text-anchor="middle">${data[i].label}</text>`,
    )
  }
  parts.push('</svg>')
  return parts.join('')
}

const occLine = computed(() =>
  axisLine(
    trend.value.map((d: any) => ({
      v: Number(d.occ),
      sp: d.occ_sp == null ? null : Number(d.occ_sp),
      label: d.label,
    })),
    '#2563eb',
    '%',
  ),
)
const adrLine = computed(() =>
  axisLine(
    trend.value.map((d: any) => ({
      v: Number(d.adr),
      sp: d.adr_sp == null ? null : Number(d.adr_sp),
      label: d.label,
    })),
    '#16a34a',
    '¥',
  ),
)
const revLine = computed(() =>
  axisLine(
    trend.value.map((d: any) => ({
      v: Number(d.revpar),
      sp: d.revpar_sp == null ? null : Number(d.revpar_sp),
      label: d.label,
    })),
    '#f59e0b',
    '¥',
  ),
)

const trendSummary = computed(() => {
  const t = trend.value
  if (!t.length) return { occ: '—', adr: '—', revpar: '—' }
  const last = t[t.length - 1]
  return {
    occ: `${Number(last.occ).toFixed(0)}%`,
    adr: fmtMoney(last.adr),
    revpar: fmtMoney(last.revpar),
  }
})

function goPricing(issue?: any) {
  persistAskState()
  if (issue && typeof issue === 'object') {
    router.push({ path: '/pricing', query: pricingQueryFromIssue(issue) })
    return
  }
  if (typeof issue === 'string' && issue) {
    router.push({ path: '/pricing', query: { from: 'forecast', action: issue } })
    return
  }
  router.push({ path: '/pricing', query: { from: 'forecast' } })
}

function dismissReco(id: string) {
  const next = new Set(dismissed.value)
  next.add(id)
  dismissed.value = next
  persistAskState()
}

async function runAskData() {
  if (askLoading.value) return
  askAbort?.abort()
  const ac = new AbortController()
  askAbort = ac
  askLoading.value = true
  askError.value = ''
  askWarning.value = ''
  askStream.value = ''
  askThinking.value = ''
  askThinkOpen.value = true
  findings.value = []
  askMeta.value = null
  try {
    await api.revenueForecastAiAdviceStream(
      hotelStore.hotelId,
      (evt) => {
        if (evt.type === 'meta') {
          askMeta.value = evt.data || null
        } else if (evt.type === 'thinking' && evt.content) {
          askThinking.value += evt.content
        } else if (evt.type === 'token' && evt.content) {
          askStream.value += evt.content
          // 开始出正文后默认收起思考区，突出结论
          if (askThinkOpen.value && askThinking.value) askThinkOpen.value = false
        } else if (evt.type === 'done' && evt.data) {
          const list = evt.data.issues || evt.data.findings || []
          findings.value = list
          askSource.value = evt.data.ai_source || ''
          askGeneratedAt.value = evt.data.generated_at || ''
          askWarning.value = evt.data.ai_warning || ''
          askModelMeta.value = formatAiModelMeta(evt.data)
          persistAskState()
        } else if (evt.type === 'error') {
          askError.value = evt.message || t('问数失败')
        }
      },
      1,
      ac.signal,
    )
  } catch (e: any) {
    if (e?.name === 'AbortError') return
    askError.value = e?.message || t('智能问数失败，请稍后重试')
  } finally {
    askLoading.value = false
    if (askAbort === ac) askAbort = null
  }
}

function onBarHover(d: any) {
  hoverDay.value = d
}

function onBarLeave() {
  hoverDay.value = null
}
</script>

<template>
  <div class="page rf-page">
    <OverviewOpsNav />

    <div class="rf-head">
      <h1 class="font-display-lg text-display-lg text-on-background">{{ t('营收预测') }}</h1>
    </div>

    <div v-if="loading" class="rf-empty">{{ t('加载中…') }}</div>
    <div v-else-if="error" class="rf-empty err">{{ error }}</div>
    <template v-else-if="board">
      <div class="kpi-row">
        <div v-for="k in kpis" :key="k.key" class="kpi" :class="{ warn: k.tone === 'warn' }">
          <div class="lbl">{{ t(k.label) }}</div>
          <div class="val" :class="{ warn: k.tone === 'warn' }">{{ fmtKpiVal(k) }}</div>
          <div class="chg" :class="k.tone">{{ fmtChg(k) }}</div>
        </div>
      </div>

      <div class="card arch">
        <h3>{{ t('预测怎么用') }}</h3>
        <div class="arch-flow">
          <div class="arch-box">
            <b>{{ t('收益预测') }}</b>
            <span>{{ t(board.formula) }}</span>
          </div>
          <span class="arch-arrow">→</span>
          <div class="arch-box on">
            <b>{{ t('营收预测') }}</b>
            <span>{{ t('看未来营收 / 缺口') }}</span>
          </div>
          <span class="arch-arrow">→</span>
          <div class="arch-box">
            <b>{{ t('价格助手') }}</b>
            <span>{{ t('确认后调价') }}</span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-top">
          <div>
            <h3>{{ t('收入预测（实际 vs 预测）') }}</h3>
          </div>
          <div v-if="hoverDay" class="hover-tip">
            {{ hoverDay.biz_date }} · {{ t('实际') }} {{ fmtMoney(hoverDay.revenue_actual) }} ·
            {{ t('预测') }} {{ fmtMoney(hoverDay.revenue_forecast) }} · {{ t('同期') }}
            {{ fmtMoney(hoverDay.revenue_same_period) }}
          </div>
        </div>
        <div class="chart-wrap" @mouseleave="onBarLeave" v-html="revChartSvg" />
        <div class="day-hits">
          <button
            v-for="d in daily"
            :key="d.biz_date"
            type="button"
            class="day-hit"
            :title="d.biz_date"
            @mouseenter="onBarHover(d)"
            @click="!d.is_past && goPricing()"
          />
        </div>
        <div class="legend">
          <span><i class="lg-a" />{{ t('实际营收（夜审）') }}</span>
          <span><i class="lg-f" />{{ t('预测') }}</span>
          <span><i class="lg-s" />{{ t('去年同期夜审') }}</span>
          <span class="legend-right">{{ t('竖虚线 = 今天') }}</span>
        </div>
      </div>

      <div class="card">
        <h3>{{ t('核心指标趋势（未来 30 天）') }}</h3>
        <div class="trend-row">
          <div class="trend-card">
            <div class="t">{{ t('OCC 预测（出租率 %）') }}</div>
            <div class="v">{{ trendSummary.occ }}</div>
            <div v-html="occLine" />
          </div>
          <div class="trend-card">
            <div class="t">{{ t('ADR 预测（平均房价 ¥）') }}</div>
            <div class="v">{{ trendSummary.adr }}</div>
            <div v-html="adrLine" />
          </div>
          <div class="trend-card">
            <div class="t">{{ t('RevPAR 预测（单房收益 ¥）') }}</div>
            <div class="v">{{ trendSummary.revpar }}</div>
            <div v-html="revLine" />
          </div>
        </div>
      </div>

      <div class="card">
        <h3>{{ t('未来订房进度（还差多少间）') }}</h3>
        <div v-for="p in pickup" :key="p.window_days" class="pk">
          <div class="pk-hd">
            <span>{{ t(p.label) }}（{{ p.range_label }}）</span>
            <span
              >{{ t('已订') }} <b>{{ p.booked.toLocaleString() }}</b> / {{ t('目标') }}
              {{ p.expected.toLocaleString() }} {{ t('间') }}{{ t('夜') }}</span
            >
          </div>
          <div class="bar">
            <div class="exp" />
            <div class="fill" :style="{ width: Math.min(100, p.fill_pct) + '%' }" />
          </div>
          <div class="gap">
            {{ t('还差') }} {{ p.gap.toLocaleString() }} {{ t('间') }}{{ t('夜（')
            }}{{ p.gap_pct }}%）· {{ t(p.verdict) }}
          </div>
        </div>
      </div>

      <div id="ask-data" class="card">
        <h3>{{ t('AI 行动建议 · 智能问数') }}</h3>

        <div v-if="candidates.length" class="cand-box">
          <div class="cand-hd">{{ t('待关注') }}（{{ candidates.length }}）</div>
          <ul class="cand-list">
            <li v-for="c in candidates" :key="c.id">
              <span class="sev" :class="c.severity">{{ t(c.severity_label || '中') }}</span>
              <span>{{ t(c.summary) }}</span>
            </li>
          </ul>
        </div>
        <div v-else class="rf-empty soft">{{ t('当前未发现明显异常，数据整体健康。') }}</div>

        <div class="ask-bar" v-if="commercialEnabled()">
          <button
            type="button"
            class="btn btn-primary ask-btn"
            :disabled="askLoading"
            @click="runAskData"
          >
            {{ askLoading ? t('正在智能问数…') : findings.length ? t('重新问数') : t('智能问数') }}
          </button>
          <span v-if="askGeneratedAt" class="ask-meta">
            {{ t('生成于') }} {{ askGeneratedAt
            }}{{
              askSource === 'llm'
                ? ' · ' + t('智能诊断')
                : askSource === 'unavailable' || askSource === 'rules_fallback'
                  ? ' · ' + t('AI 暂不可用')
                  : ''
            }}{{ askModelMeta ? ` · ${askModelMeta}` : '' }}</span
          >
        </div>

        <div v-if="askLoading || askStream || askThinking" class="ask-stream">
          <details
            v-if="askThinking"
            class="ask-think"
            :open="askThinkOpen"
            @toggle="askThinkOpen = ($event.target as HTMLDetailsElement).open"
          >
            <summary class="ask-stream-hd">
              <span>{{ t('思考过程') }}</span>
              <span v-if="askLoading && !askStream" class="live">{{ t('思考中') }}</span>
            </summary>
            <pre
              class="ask-stream-pre think">{{ askThinking }}<span v-if="askLoading && !askStream" class="cursor" /></pre>
          </details>
          <div v-if="askLoading || askStream" class="ask-out">
            <div class="ask-stream-hd">
              <span>{{ t('模型输出') }}</span>
              <span v-if="askLoading && askStream" class="live">{{ t('生成中') }}</span>
            </div>
            <pre
              class="ask-stream-pre">{{ askStream || (askLoading ? t('等待模型输出…') : '') }}<span v-if="askLoading && askStream" class="cursor" /></pre>
          </div>
        </div>
        <div v-if="askError" class="rw">{{ askError }}</div>
        <div v-if="askWarning" class="rw">{{ t(askWarning) }}</div>

        <div v-if="!askLoading && askGeneratedAt && !visibleFindings.length" class="rf-empty soft">
          {{ t('数据健康，暂无行动建议。') }}
        </div>

        <div v-if="visibleFindings.length" class="reco">
          <div v-for="r in visibleFindings" :key="r.id" class="rc">
            <span class="badge">{{ r.confidence ? `可信度${r.confidence}` : 'AI 建议' }}</span>
            <div class="rt">{{ r.dimension || r.reco_title }}</div>
            <div v-if="r.severity" class="ri">
              严重度 {{ r.severity }} · 影响 {{ r.revenue_impact || r.est_impact || '—' }}
            </div>
            <div class="meta">{{ t('依据：') }}{{ r.evidence || r.trigger }}</div>
            <div class="rd">
              {{ r.reco_detail || `建议动作：${r.suggested_action || t('暂不动作')}` }}
            </div>
            <div class="rc-actions">
              <button
                type="button"
                class="btn btn-primary"
                @click="goPricing(r)"
                :disabled="r.suggested_action === '暂不动作'"
              >
                {{
                  r.suggested_action === '暂不动作'
                    ? t('暂不动作')
                    : `去价格助手 · ${r.suggested_action || t('调整')}`
                }}
              </button>
              <button type="button" class="btn btn-ghost" @click="dismissReco(r.id)">
                {{ t('忽略') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.rf-page {
  padding-bottom: 2rem;
}
#ask-data {
  scroll-margin-top: 16px;
}
.rf-head {
  margin-bottom: 16px;
}
.rf-empty {
  padding: 28px;
  text-align: center;
  color: #79747e;
  font-size: 14px;
}
.rf-empty.soft {
  padding: 18px;
  background: #f8fafc;
  border-radius: 8px;
}
.rf-empty.err {
  color: #ba1a1a;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.kpi {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 13px 14px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.06);
}
.kpi .lbl {
  font-size: 11.5px;
  font-weight: 700;
  color: #9ca3af;
  margin-bottom: 7px;
}
.kpi .val {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #1f2937;
}
.kpi .val.warn,
.kpi.warn .val {
  color: #dc2626;
}
.kpi .chg {
  font-size: 11.5px;
  margin-top: 5px;
  font-variant-numeric: tabular-nums;
}
.kpi .chg.up {
  color: #16a34a;
}
.kpi .chg.down,
.kpi .chg.warn {
  color: #dc2626;
  font-weight: 600;
}
.kpi .chg.muted {
  color: #9ca3af;
}

.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.06);
  margin-bottom: 16px;
}
.card h3 {
  font-size: 14px;
  font-weight: 700;
  margin: 0 0 4px;
  color: #1f2937;
}
.card .ch {
  font-size: 11.5px;
  color: #9ca3af;
  margin: 0 0 12px;
  line-height: 1.5;
}
.card.arch {
  background: linear-gradient(180deg, #f8faff, #fff);
}
.arch-flow {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-top: 4px;
}
.arch-box {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 12px;
  background: #fff;
  min-width: 128px;
  font-size: 12px;
}
.arch-box b {
  display: block;
  margin-bottom: 2px;
}
.arch-box span {
  color: #9ca3af;
  font-size: 11px;
}
.arch-box.on {
  border-color: #2563eb;
  background: #eff4ff;
}
.arch-arrow {
  color: #2563eb;
  font-weight: 700;
  font-size: 12px;
}
.note {
  font-size: 11px;
  color: #9ca3af;
  margin: 10px 0 0;
  line-height: 1.5;
}

.card-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
}
.hover-tip {
  font-size: 11.5px;
  color: #4b5563;
  background: #f3f4f6;
  padding: 6px 10px;
  border-radius: 8px;
}
.chart-wrap {
  width: 100%;
}
.day-hits {
  display: flex;
  margin-top: -8px;
  margin-bottom: 4px;
}
.day-hit {
  flex: 1;
  height: 18px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 11.5px;
  color: #4b5563;
  margin-top: 8px;
  align-items: center;
}
.legend i {
  display: inline-block;
  width: 11px;
  height: 11px;
  border-radius: 3px;
  margin-right: 5px;
  vertical-align: -1px;
}
.lg-a {
  background: #2563eb;
}
.lg-f {
  background: rgba(37, 99, 235, 0.35);
  border: 1px dashed #2563eb;
  box-sizing: border-box;
}
.lg-s {
  background: #f59e0b;
}
.legend-right {
  margin-left: auto;
  color: #9ca3af;
}

.trend-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.trend-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px 14px;
}
.trend-card .t {
  font-size: 12px;
  color: #4b5563;
  margin-bottom: 2px;
}
.trend-card .v {
  font-size: 17px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  margin-bottom: 2px;
}

.pk {
  margin-bottom: 14px;
}
.pk:last-child {
  margin-bottom: 0;
}
.pk-hd {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
  margin-bottom: 6px;
  gap: 8px;
  flex-wrap: wrap;
}
.pk-hd b {
  font-variant-numeric: tabular-nums;
}
.bar {
  height: 11px;
  background: #eef2f7;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}
.bar .exp {
  height: 100%;
  width: 100%;
  background: repeating-linear-gradient(45deg, #cbd5e1, #cbd5e1 4px, #e2e8f0 4px, #e2e8f0 8px);
  position: absolute;
  inset: 0;
  border-radius: 6px;
}
.bar .fill {
  height: 100%;
  background: #2563eb;
  border-radius: 6px;
  position: relative;
  z-index: 1;
}
.gap {
  font-size: 11.5px;
  color: #dc2626;
  margin-top: 4px;
}

.reco {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.rc {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px;
  position: relative;
  background: linear-gradient(180deg, #fff, #fcfdff);
}
.rc .badge {
  position: absolute;
  top: 12px;
  right: 12px;
  font-size: 10px;
  background: #eff4ff;
  color: #1d4ed8;
  padding: 2px 7px;
  border-radius: 20px;
  font-weight: 600;
}
.rc .rt {
  font-size: 12.5px;
  font-weight: 600;
  margin-bottom: 7px;
  padding-right: 54px;
  color: #1f2937;
}
.rc .rd {
  font-size: 12px;
  color: #4b5563;
  line-height: 1.6;
  margin-bottom: 9px;
  white-space: pre-wrap;
}
.rc .rd.muted {
  color: #9ca3af;
  white-space: normal;
}
.cand-box {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f8fafc;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.cand-hd {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 6px;
}
.cand-list {
  margin: 0;
  padding-left: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cand-list li {
  font-size: 12px;
  color: #4b5563;
  line-height: 1.45;
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.sev {
  flex: none;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 1px 6px;
  border-radius: 4px;
  background: #e5e7eb;
  color: #4b5563;
}
.sev.high {
  background: #fee2e2;
  color: #b91c1c;
}
.sev.medium {
  background: #ffedd5;
  color: #c2410c;
}
.sev.low {
  background: #e0e7ff;
  color: #4338ca;
}
.ask-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.ask-btn {
  width: auto;
  min-width: 140px;
}
.ask-meta {
  font-size: 11px;
  color: #9ca3af;
}
.ask-stream {
  border: 1px solid #dbeafe;
  background: #f8fbff;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ask-think {
  border-bottom: 1px dashed #dbeafe;
  padding-bottom: 8px;
}
.ask-think summary {
  cursor: pointer;
  list-style: none;
}
.ask-think summary::-webkit-details-marker {
  display: none;
}
.ask-think summary::before {
  content: '▸ ';
  color: #94a3b8;
}
.ask-think[open] summary::before {
  content: '▾ ';
}
.ask-stream-hd {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
  margin-bottom: 6px;
}
.ask-stream-hd .live {
  color: #2563eb;
}
.ask-stream-pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.55;
  color: #1f2937;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  max-height: 220px;
  overflow: auto;
}
.ask-stream-pre.think {
  color: #64748b;
  max-height: 160px;
  background: #f1f5f9;
  border-radius: 6px;
  padding: 8px;
}
.cursor {
  display: inline-block;
  width: 7px;
  height: 12px;
  margin-left: 2px;
  vertical-align: -1px;
  background: #2563eb;
  animation: rf-blink 1s step-end infinite;
}
@keyframes rf-blink {
  50% {
    opacity: 0;
  }
}
.rc .ri {
  font-size: 11.5px;
  color: #16a34a;
  margin-bottom: 6px;
}
.rc .rw {
  font-size: 11px;
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 6px 8px;
  margin-bottom: 8px;
  line-height: 1.45;
}
.rc .meta {
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 10px;
  line-height: 1.4;
}
.rc-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.rc-actions .btn,
.ask-bar .btn {
  width: 100%;
  justify-content: center;
}
.ask-bar .ask-btn {
  width: auto;
  min-width: 140px;
}
.rc-actions .btn:disabled,
.ask-bar .btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

@media (max-width: 1100px) {
  .kpi-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .trend-row,
  .reco {
    grid-template-columns: 1fr;
  }
}
</style>
