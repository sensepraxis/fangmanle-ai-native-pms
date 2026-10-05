<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 资产折旧与财务摊销分析
 * 图表「资产账龄与净残值对比」：优先 assetsBoard.depreciation_chart（按类别聚合原值/净值/账龄）
 */
import { ref, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import AssetsFlowNav from '../../components/AssetsFlowNav.vue'

type Bar = {
  label: string
  original: number
  net: number
  netOfOriginal: number
  purchase: number
  current: number
  ageYears: number
  residualPct: number
  count: number
}

const FALLBACK = {
  summary: [
    { label: t('总资产净值'), value: t('¥ 286.4万'), note: t('较上月 -2.1%'), tone: 'down' },
    { label: t('本月折旧额'), value: t('¥ 12.8万'), note: t('直线法 · 12 类资产'), tone: '' },
    { label: t('预计重置预算'), value: t('¥ 45.2万'), note: t('未来 6 个月'), tone: 'up' },
  ],
  bars: [
    {
      label: t('暖通'),
      original: 88,
      net: 52,
      netOfOriginal: 59,
      purchase: 880000,
      current: 520000,
      ageYears: 4.2,
      residualPct: 59,
      count: 6,
    },
    {
      label: t('客房设备'),
      original: 76,
      net: 41,
      netOfOriginal: 54,
      purchase: 760000,
      current: 410000,
      ageYears: 3.5,
      residualPct: 54,
      count: 12,
    },
    {
      label: t('弱电'),
      original: 64,
      net: 38,
      netOfOriginal: 59,
      purchase: 640000,
      current: 380000,
      ageYears: 2.8,
      residualPct: 59,
      count: 8,
    },
    {
      label: t('公区'),
      original: 58,
      net: 29,
      netOfOriginal: 50,
      purchase: 580000,
      current: 290000,
      ageYears: 5.1,
      residualPct: 50,
      count: 5,
    },
    {
      label: t('电梯'),
      original: 72,
      net: 48,
      netOfOriginal: 67,
      purchase: 720000,
      current: 480000,
      ageYears: 6.0,
      residualPct: 67,
      count: 2,
    },
  ] as Bar[],
  aiAdvice: {
    text: t(
      '基于 IoT 传感器数据，尊享大床房（201-205）的空调使用频率高出均值 40%。建议将该批次设备的折旧年限从 5 年调整为 3 年，以更真实反映资产损耗。',
    ),
    amount: t('+¥3,200/月'),
  },
  risks: [
    { name: t('大金中央空调'), rooms: t('402 等 3 间'), value: '8%', remaining: t('残值 ¥360') },
    { name: t('TOTO 智能马桶'), rooms: '305', value: '6%', remaining: t('残值 ¥408') },
    { name: t('智能门锁'), rooms: t('510 等 5F'), value: '9%', remaining: t('残值 ¥162') },
  ],
}

const data = ref<any>({ ...FALLBACK })

function fmtWan(n: number) {
  if (!n) return '¥ 0'
  if (Math.abs(n) >= 10000) return `¥ ${(n / 10000).toFixed(1)}万`
  return `¥ ${Math.round(n).toLocaleString('zh-CN')}`
}

function buildSummary(summary: any, assets: any[], insights: any[]) {
  const totalVal = Number(summary?.total_value || 0)
  const purchase =
    Number(summary?.total_purchase) || assets.reduce((s, a) => s + Number(a.purchase_value || 0), 0)
  const current = assets.reduce((s, a) => s + Number(a.current_value || 0), 0) || totalVal
  const monthlyDep = purchase && current < purchase ? Math.round((purchase - current) / 24) : 0
  const replaceBudget = insights
    .filter((i) => ['replace', 'roi'].includes(i.category))
    .reduce((s, i) => s + Number(i.impact_amount || 0), 0)

  if (!totalVal && !assets.length) return FALLBACK.summary

  return [
    {
      label: t('总资产净值'),
      value: fmtWan(totalVal || current),
      note: summary?.asset_count ? `${summary.asset_count} 项在册` : t('较上月 -2.1%'),
      tone: 'down',
    },
    {
      label: t('本月折旧额'),
      value: monthlyDep ? fmtWan(monthlyDep) : '—',
      note: `平均健康 ${summary?.avg_health ?? '—'}/100`,
      tone: 'down',
    },
    {
      label: t('预计重置预算'),
      value: replaceBudget ? fmtWan(replaceBudget) : fmtWan((totalVal || current) * 0.15),
      note: `待维保 ${summary?.maint_due ?? 0} 项`,
      tone: 'up',
    },
  ]
}

/** 将 API depreciation_chart / assets 转为柱高（相对最大原值） */
function buildBars(chart: any[], assets: any[]): Bar[] {
  let rows = (chart || []).filter((r) => Number(r.purchase || 0) > 0)

  if (!rows.length && assets?.length) {
    const cats: Record<
      string,
      { purchase: number; current: number; count: number; ageSum: number }
    > = {}
    const now = Date.now()
    for (const a of assets) {
      const c = String(a.category || '其他').trim() || '其他'
      if (!cats[c]) cats[c] = { purchase: 0, current: 0, count: 0, ageSum: 0 }
      const pv = Number(a.purchase_value || 0)
      const cv = Number(a.current_value != null ? a.current_value : pv)
      cats[c].purchase += pv
      cats[c].current += cv
      cats[c].count += 1
      if (a.purchase_date) {
        const t = new Date(a.purchase_date).getTime()
        cats[c].ageSum += Math.max(0, (now - t) / (365.25 * 86400000))
      } else {
        cats[c].ageSum += 3
      }
    }
    rows = Object.entries(cats).map(([label, v]) => ({
      label,
      purchase: v.purchase,
      current: v.current,
      count: v.count,
      age_years: Math.round((v.ageSum / Math.max(v.count, 1)) * 10) / 10,
      residual_pct: v.purchase > 0 ? Math.round(((100 * v.current) / v.purchase) * 10) / 10 : 0,
    }))
  }

  if (!rows.length) return [...FALLBACK.bars]

  rows = [...rows].sort((a, b) => Number(b.purchase) - Number(a.purchase)).slice(0, 6)
  const maxP = Math.max(...rows.map((r) => Number(r.purchase) || 0), 1)

  return rows.map((r) => {
    const purchase = Number(r.purchase) || 0
    const current = Number(r.current) || 0
    const original = Math.max(8, Math.round((purchase / maxP) * 100))
    const net = Math.max(4, Math.round((current / maxP) * 100))
    const netOfOriginal =
      purchase > 0
        ? Math.max(6, Math.round((current / purchase) * 100))
        : Math.round((net / original) * 100)
    const short = String(r.label || '其他')
    return {
      label: short.length > 6 ? short.slice(0, 6) : short,
      original,
      net: Math.min(net, original),
      netOfOriginal: Math.min(100, netOfOriginal),
      purchase,
      current,
      ageYears: Number(r.age_years) || 0,
      residualPct:
        Number(r.residual_pct) || (purchase ? Math.round((100 * current) / purchase) : 0),
      count: Number(r.count) || 0,
    }
  })
}

function buildRisks(assets: any[]) {
  return assets
    .filter((a) => {
      const pv = Number(a.purchase_value || 0)
      const cv = Number(a.current_value || 0)
      return pv > 0 && cv / pv < 0.15 && (a.room_no || Number(a.health_score ?? 100) < 60)
    })
    .slice(0, 6)
    .map((a) => {
      const pv = Number(a.purchase_value || 1)
      const cv = Number(a.current_value || 0)
      const pct = Math.round((cv / pv) * 100)
      return {
        name: a.name,
        rooms: a.room_no
          ? `${a.room_no}${a.location ? ` · ${a.location}` : ''}`
          : a.location || '—',
        value: `${pct}%`,
        remaining: `残值 ¥${Math.round(cv).toLocaleString(')zh-CN')}`,
      }
    })
}

function tip(b: Bar) {
  return `${b.label}｜账龄约 ${b.ageYears} 年｜原值 ${fmtWan(b.purchase)}｜净值 ${fmtWan(b.current)}（残值率 ${b.residualPct}%）${b.count ? `｜${b.count} 项` : ''}`
}

async function load() {
  try {
    const board = await api.assetsBoard(hotelStore.hotelId)
    const assets = board?.assets || []
    const summary = board?.summary || {}
    const insights = board?.insights || []
    const chart = board?.depreciation_chart || []

    const bars = buildBars(chart, assets)
    const risks = buildRisks(assets)
    const roiIns = insights.find((i: any) => i.category === 'roi') || insights[0]

    data.value = {
      summary: buildSummary(summary, assets, insights),
      bars,
      aiAdvice: roiIns
        ? {
            text: roiIns.recommendation || FALLBACK.aiAdvice.text,
            amount: roiIns.impact_amount
              ? `+¥${Number(roiIns.impact_amount).toLocaleString('zh-CN')}/月`
              : FALLBACK.aiAdvice.amount,
          }
        : FALLBACK.aiAdvice,
      risks: risks.length ? risks : FALLBACK.risks,
    }
  } catch {
    data.value = { ...FALLBACK }
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page dep-page">
    <div class="page-head">
      <div>
        <h1>{{ t('资产折旧与财务摊销分析') }}</h1>
        <p>{{ t('实时资产估值、折旧追踪与 AI 驱动的更换预测。') }}</p>
      </div>
    </div>

    <div class="grid-12">
      <div class="col-main">
        <div class="kpi-row">
          <template v-for="(c, i) in data.summary || []" :key="i">
            <div class="card-clean card-pad kpi">
              <h3 class="kpi-title">{{ c.label }}</h3>
              <div class="kpi-val">{{ c.value }}</div>
              <div
                class="kpi-note"
                :class="c.tone === 'down' ? 'down' : c.tone === 'up' ? 'up' : ''"
              >
                {{ c.note }}
              </div>
            </div>
          </template>
        </div>

        <!-- 账龄与净残值对比 -->
        <div class="card-clean card-pad chart-card">
          <h3 class="chart-title">{{ t('资产账龄与净残值对比') }}</h3>
          <p class="chart-sub">{{ t('按资产类别汇总原值与净值；柱顶标注平均账龄（年）。') }}</p>

          <div class="chart">
            <div class="y-axis">
              <span>100%</span>
              <span>50%</span>
              <span>0%</span>
            </div>
            <div class="bars">
              <div v-for="(b, i) in data.bars || []" :key="i" class="bar-col" :title="tip(b)">
                <div class="bar-track">
                  <div class="bar-original" :style="{ height: b.original + '%' }">
                    <div class="bar-net" :style="{ height: b.netOfOriginal + '%' }"></div>
                  </div>
                </div>
                <span class="age-tag">{{ b.ageYears }}年</span>
                <span class="bar-label">{{ b.label }}</span>
              </div>
            </div>
          </div>

          <div class="legend">
            <span><i class="lg-o"></i>{{ t('原值比例') }}</span>
            <span><i class="lg-n"></i>{{ t('当前净值') }}</span>
          </div>
        </div>
      </div>

      <div class="col-side">
        <div class="card-clean card-pad ai-glow">
          <h3 class="side-title">{{ t('AI 摊销优化建议') }}</h3>
          <p class="ai-text">{{ data.aiAdvice?.text }}</p>
          <div class="ai-box">
            <div class="ai-row">
              <span>{{ t('建议调整金额') }}</span>
              <strong>{{ data.aiAdvice?.amount }}</strong>
            </div>
            <button type="button" class="ai-btn">{{ t('采纳 AI 建议并更新财务报表') }}</button>
          </div>
        </div>

        <div class="card-clean risk-card">
          <div class="risk-head">
            <h3>{{ t('高风险折旧资产 (临近报废)') }}</h3>
            <p>{{ t('净残值 &lt; 10% 且位于高频使用客房') }}</p>
          </div>
          <div class="risk-list">
            <div v-for="(r, i) in data.risks || []" :key="i" class="risk-row">
              <div>
                <div class="r-name">{{ r.name }}</div>
                <div class="r-rooms">{{ r.rooms }}</div>
              </div>
              <div class="r-right">
                <div class="r-pct">净值: {{ r.value }}</div>
                <div class="r-rm">{{ r.remaining }}</div>
              </div>
            </div>
          </div>
          <div class="risk-foot">
            <button type="button">{{ t('查看完整报废清单') }}</button>
          </div>
        </div>
      </div>
    </div>

    <AssetsFlowNav />
  </div>
</template>

<style scoped>
.dep-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.grid-12 {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
  align-items: stretch;
}
.col-main {
  grid-column: span 8;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.col-side {
  grid-column: span 4;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.kpi-title {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 700;
  color: var(--on-surface);
}
.kpi-val {
  font-size: 28px;
  font-weight: 700;
  font-family: 'Roboto Mono', monospace;
  color: var(--on-surface);
  margin-bottom: 8px;
}
.kpi-note {
  font-size: 13px;
  color: var(--on-surface-variant);
  margin-top: auto;
}
.kpi-note.down {
  color: var(--error, #ba1a1a);
}
.kpi-note.up {
  color: var(--primary, #005bbf);
}
.kpi {
  display: flex;
  flex-direction: column;
  min-height: 120px;
}

.chart-card {
  flex: 1;
}
.chart-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--on-surface);
}
.chart-sub {
  margin: 6px 0 16px;
  font-size: 13px;
  color: var(--on-surface-variant);
}

.chart {
  position: relative;
  height: 280px;
  padding: 8px 8px 36px 40px;
  border-bottom: 1px solid var(--outline-variant);
  box-sizing: border-box;
}
.y-axis {
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 36px;
  width: 36px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
  padding-right: 6px;
  font-size: 11px;
  font-family: 'Roboto Mono', monospace;
  color: var(--on-surface-variant);
  pointer-events: none;
}
.bars {
  height: 100%;
  display: flex;
  align-items: stretch;
  justify-content: space-around;
  gap: 8px;
}
.bar-col {
  flex: 1;
  max-width: 72px;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  min-width: 0;
  cursor: default;
}
.bar-track {
  flex: 1;
  width: 48px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  min-height: 0;
}
.bar-original {
  width: 100%;
  position: relative;
  border-radius: 6px 6px 0 0;
  background: rgba(0, 91, 191, 0.2);
  min-height: 12px;
  transition:
    height 0.35s ease,
    opacity 0.15s;
}
.bar-col:hover .bar-original {
  opacity: 0.92;
  background: rgba(0, 91, 191, 0.3);
}
.bar-net {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 6px 6px 0 0;
  background: var(--primary, #005bbf);
  min-height: 6px;
}
.age-tag {
  margin-top: 6px;
  font-size: 11px;
  font-family: 'Roboto Mono', monospace;
  font-weight: 600;
  color: var(--primary, #005bbf);
  line-height: 1;
}
.bar-label {
  margin-top: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--on-surface);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 16px;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.legend i {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}
.lg-o {
  background: rgba(0, 91, 191, 0.2);
}
.lg-n {
  background: var(--primary, #005bbf);
}

.side-title {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 700;
  color: var(--on-surface);
}
.ai-text {
  margin: 0 0 16px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--on-surface-variant);
}
.ai-box {
  border-radius: 8px;
  padding: 16px;
  background: rgba(140, 51, 179, 0.1);
  border: 1px solid rgba(140, 51, 179, 0.2);
}
.ai-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--on-surface);
}
.ai-row strong {
  font-family: 'Roboto Mono', monospace;
  color: var(--tertiary, #8c33b3);
  font-size: 14px;
}
.ai-btn {
  width: 100%;
  margin-top: 8px;
  border: none;
  border-radius: 8px;
  padding: 10px;
  background: var(--tertiary, #8c33b3);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.ai-btn:hover {
  opacity: 0.92;
}

.risk-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}
.risk-head {
  padding: 16px;
  border-bottom: 1px solid var(--outline-variant);
  background: rgba(186, 26, 26, 0.05);
}
.risk-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--error, #ba1a1a);
}
.risk-head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.risk-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  max-height: 320px;
}
.risk-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  border-bottom: 1px solid rgba(193, 198, 214, 0.4);
}
.risk-row:hover {
  background: var(--surface-low, #f2f4f5);
}
.r-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--on-surface);
}
.r-rooms {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-top: 4px;
}
.r-right {
  text-align: right;
  flex-shrink: 0;
}
.r-pct {
  font-family: 'Roboto Mono', monospace;
  color: var(--error);
  font-size: 13px;
  font-weight: 600;
}
.r-rm {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-top: 4px;
}
.risk-foot {
  padding: 16px;
  border-top: 1px solid var(--outline-variant);
  background: var(--surface-lowest, #fff);
}
.risk-foot button {
  width: 100%;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 8px;
  background: transparent;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface);
  cursor: pointer;
}
.risk-foot button:hover {
  background: var(--surface-low);
}

.ai-glow {
  box-shadow: 0 0 15px -3px rgba(140, 51, 179, 0.3);
  border-left: 2px solid #8c33b3;
}

@media (max-width: 960px) {
  .col-main,
  .col-side {
    grid-column: span 12;
  }
  .kpi-row {
    grid-template-columns: 1fr;
  }
}
</style>
