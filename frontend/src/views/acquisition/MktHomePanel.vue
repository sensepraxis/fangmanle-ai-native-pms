<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 私域总览 · 健康度 + 触发式 AI（格式化文案 + 可写操作，不展示 JSON）
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import NarrativeInsightPanel from '../../components/NarrativeInsightPanel.vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'

const router = useRouter()
const loading = ref(false)
const data = ref<any>(null)

type AiKind = 'diagnosis' | 'week_plan' | 'radar'

const KIND_UI = computed(() => ({
  diagnosis: {
    title: t('AI 健康度诊断'),
    idle: '',
    run: t('开始诊断'),
    rerun: t('重新诊断'),
    wait: t('正在分析私域健康度与看板指标…'),
  },
  week_plan: {
    title: t('AI 本周养客作战计划'),
    idle: '',
    run: t('生成本周计划'),
    rerun: t('重新生成'),
    wait: t('正在生成本周养客作战计划…'),
  },
  radar: {
    title: t('AI 异常与机会雷达'),
    idle: '',
    run: t('扫描雷达'),
    rerun: t('重新扫描'),
    wait: t('正在扫描异常与机会信号…'),
  },
}))

const KPI_META: Record<string, { emoji: string; ico: string; stroke: string; fill: string }> = {
  private_cust: { emoji: '🏠', ico: '👥', stroke: '#005bbf', fill: 'rgba(0,91,191,.12)' },
  link_rate: { emoji: '🤝', ico: '🤝', stroke: '#16a34a', fill: 'rgba(22,163,74,.12)' },
  month_active: { emoji: '🔥', ico: '📈', stroke: '#d97706', fill: 'rgba(217,119,6,.12)' },
  mkt_revenue: { emoji: '💰', ico: '💰', stroke: '#0284c7', fill: 'rgba(2,132,199,.12)' },
}

async function load() {
  loading.value = true
  try {
    data.value = await api.mktDashboard(hotelStore.hotelId)
  } catch (e: any) {
    toast(e?.message || t('加载失败'), false)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)

const health = computed(() => data.value?.health || null)
const heroKpis = computed(() => data.value?.hero_kpis || [])
const flow = computed(() => data.value?.flow || [])
const activities = computed(() => data.value?.activities || [])
const aiResetKey = computed(() => hotelStore.hotelId)

const dimList = computed(() => {
  const d = health.value?.dims || {}
  return [
    { name: t('接入'), v: Number(d.access ?? 0), warn: false },
    { name: t('引流'), v: Number(d.attract ?? d[t('引流')] ?? 0), warn: false },
    { name: t('活跃'), v: Number(d.active ?? d[t('活跃')] ?? 0), warn: false },
    {
      name: t('转化'),
      v: Number(d.convert ?? d[t('转化')] ?? 0),
      warn: Number(d.convert ?? d[t('转化')] ?? 0) < 60,
    },
  ]
})

const healthLvlText = computed(() => {
  const h = health.value
  if (!h) return '—'
  const delta = Number(h.week_delta || 0)
  const lvl = t(String(h.level || ''))
  const emoji = h.level === t('健康') ? '🟢' : h.level === t('一般') ? '🟡' : '🔴'
  if (delta > 0) return `${emoji} ${lvl} · ${t('较上周')} +${delta}`
  if (delta < 0) return `${emoji} ${lvl} · ${t('较上周')} ${delta}`
  return `${emoji} ${lvl}`
})

function go(path?: string) {
  if (path) router.push(path)
}

function fmtVal(k: any) {
  const v = Number(k?.value || 0)
  if (k?.unit === '¥') {
    if (v >= 1000) return `¥${(v / 1000).toFixed(v % 1000 === 0 || v >= 10000 ? 0 : 1)}K`
    return `¥${v.toLocaleString()}`
  }
  if (k?.unit === '%') return `${v}%`
  return v.toLocaleString()
}

function deltaText(k: any) {
  const pct = Number(k?.delta_pct)
  if (Number.isFinite(pct) && pct !== 0) {
    const arrow = pct > 0 ? '▲' : '▼'
    const unit = k?.unit === '%' ? 'pt' : '%'
    return `${arrow} ${Math.abs(pct)}${unit} ${k.delta_label ? '' : t('较上周')}`.trim()
  }
  // API 常返回「本月新建联 N」整句：尽量按前缀翻译
  const raw = String(k?.delta_label || '')
  if (!raw) return '—'
  return tDeltaLabel(raw)
}

function tDeltaLabel(raw: string): string {
  const m1 = raw.match(/^本月新建联\s*(\d+)$/)
  if (m1) return `${t('本月新建联')} ${m1[1]}`
  const m2 = raw.match(/^本月核销\s*(\d+)\s*张估$/)
  if (m2) return `${t('本月核销')} ${m2[1]} ${t('张估')}`
  const m3 = raw.match(/^私域\s*(\d+)\s*\/\s*客户\s*(\d+)$/)
  if (m3) return `${t('私域')} ${m3[1]} / ${t('客户')} ${m3[2]}`
  const m4 = raw.match(/^占私域\s*([\d.]+)%$/)
  if (m4) return `${t('占私域')} ${m4[1]}%`
  return t(raw)
}

function tFlowBadge(raw: string): string {
  const s = String(raw || '')
  let m = s.match(/^已发布\s*(\d+)\s*·\s*本月建联\s*(\d+)$/)
  if (m) return `${t('已发布')} ${m[1]} · ${t('本月建联')} ${m[2]}`
  m = s.match(/^已发布\s*(\d+)\s*\/\s*草稿\s*(\d+)$/)
  if (m) return `${t('已发布')} ${m[1]} / ${t('草稿')} ${m[2]}`
  m = s.match(/^私域客户\s*(\d+)$/)
  if (m) return `${t('私域客户')} ${m[1]}`
  m = s.match(/^在跑\s*(\d+)\s*条规则$/)
  if (m) return `${t('在跑')} ${m[1]} ${t('条规则')}`
  return t(s)
}

function sparkLine(ys: number[], w = 120, h = 28) {
  const arr = ys?.length ? ys : [18, 16, 14, 12, 10, 8, 6]
  const n = arr.length
  return arr.map((y, i) => `${(i / Math.max(n - 1, 1)) * w},${y}`).join(' ')
}

function sparkArea(ys: number[], w = 120, h = 28) {
  return `${sparkLine(ys, w, h)} ${w},${h} 0,${h}`
}

function meta(k: any) {
  return KPI_META[k.key] || KPI_META.private_cust
}

function makeFetcher(kind: AiKind) {
  return () => api.mktAiNarrate(hotelStore.hotelId, kind)
}

function executor(action: Record<string, any>) {
  return api.mktAiExecute(hotelStore.hotelId, action)
}
</script>

<template>
  <div class="wrap">
    <div v-if="loading && !data" class="loading">{{ t('加载中…') }}</div>

    <template v-else-if="data">
      <section class="hero">
        <div class="health">
          <div class="row">
            <div>
              <div class="title">{{ t('私域健康度') }}</div>
              <div class="score">{{ health?.score ?? '—' }} <small>/100</small></div>
              <div class="lvl">{{ healthLvlText }}</div>
            </div>
            <div style="flex: 1; min-width: 0">
              <div style="font-size: 12px; opacity: 0.8; margin-bottom: 6px">
                {{ t('四维评分') }}
              </div>
              <div class="bars">
                <div v-for="d in dimList" :key="d.name" class="bar">
                  <span class="name">{{ d.name }}</span>
                  <div class="track">
                    <div
                      class="fill"
                      :style="{
                        width: d.v + '%',
                        background: d.warn ? 'linear-gradient(90deg,#fbbf24,#fff)' : undefined,
                      }"
                    />
                  </div>
                  <span class="v">{{ d.v }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="hero-kpis">
          <div v-for="(k, i) in heroKpis" :key="k.key" class="hkpi" :class="'k' + (i + 1)">
            <div class="lbl">{{ meta(k).emoji }} {{ t(k.label) }}</div>
            <div class="val">{{ fmtVal(k) }}</div>
            <div class="delta" :class="{ down: k.down || Number(k.delta_pct) < 0 }">
              {{ deltaText(k) }}
            </div>
            <div class="ico">{{ meta(k).ico }}</div>
            <svg class="spark" viewBox="0 0 120 28" preserveAspectRatio="none">
              <polyline
                fill="none"
                :stroke="meta(k).stroke"
                stroke-width="2"
                :points="sparkLine(k.spark_y)"
              />
              <polyline :fill="meta(k).fill" stroke="none" :points="sparkArea(k.spark_y)" />
            </svg>
          </div>
        </div>
      </section>

      <NarrativeInsightPanel
        :title="KIND_UI.diagnosis.title"
        :idle="KIND_UI.diagnosis.idle"
        :run-label="KIND_UI.diagnosis.run"
        :rerun-label="KIND_UI.diagnosis.rerun"
        :wait-label="KIND_UI.diagnosis.wait"
        :reset-key="`diagnosis:${aiResetKey}`"
        :fetcher="makeFetcher('diagnosis')"
        :executor="executor"
      />

      <section class="ai-grid">
        <NarrativeInsightPanel
          v-for="kind in ['week_plan', 'radar'] as AiKind[]"
          :key="kind"
          :title="KIND_UI[kind as AiKind].title"
          :idle="KIND_UI[kind as AiKind].idle"
          :run-label="KIND_UI[kind as AiKind].run"
          :rerun-label="KIND_UI[kind as AiKind].rerun"
          :wait-label="KIND_UI[kind as AiKind].wait"
          :reset-key="`${kind}:${aiResetKey}`"
          :fetcher="makeFetcher(kind)"
          :executor="executor"
        />
      </section>

      <section class="flow">
        <div class="flow-head">
          <h3>{{ t('私域闭环进度') }}</h3>
        </div>
        <div class="flow-steps">
          <button
            v-for="s in flow"
            :key="s.step"
            type="button"
            class="step"
            :class="s.status"
            @click="go(s.path)"
          >
            <div class="num">{{ s.step }}</div>
            <div class="body">
              <div class="t">{{ t(s.name) }}</div>
              <div
                class="num-k"
                :style="
                  s.status === 'warn'
                    ? { background: 'var(--warn-soft)', color: 'var(--warn)' }
                    : undefined
                "
              >
                {{ tFlowBadge(s.badge) }}
              </div>
            </div>
          </button>
        </div>
      </section>

      <section class="panel">
        <h3>{{ t('最近动态') }}</h3>
        <ul v-if="activities.length" class="tl">
          <li v-for="(a, i) in activities" :key="i">
            <div class="ts">{{ a.ts }}</div>
            <div class="ct">
              {{ a.text }}
              <span class="tag" :class="'t-' + (a.tag_kind || 'grant')">{{ a.tag }}</span>
            </div>
          </li>
        </ul>
        <div v-else class="empty">{{ t('暂无动态') }}</div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.wrap {
  --brand: #005bbf;
  --soft: #eef5ff;
  --line: #c1c6d6;
  --ink2: #475569;
  --ink3: #7b8794;
  --ok: #16a34a;
  --ok-soft: #ecfdf5;
  --warn: #d97706;
  --warn-soft: #fff7ed;
  --bad: #dc2626;
  --bad-soft: #fef2f2;
  padding-bottom: 24px;
  color: #1e293b;
}
.loading,
.empty {
  color: var(--ink3);
  font-size: 13px;
  padding: 12px 0;
}

.hero {
  display: grid;
  grid-template-columns: 1.4fr 2fr;
  gap: 12px;
  margin-bottom: 12px;
}
.health {
  background: linear-gradient(135deg, #003d82 0%, #005bbf 55%, #3b82f6 100%);
  border-radius: 12px;
  padding: 18px 20px;
  color: #fff;
  position: relative;
  overflow: hidden;
}
.health::before {
  content: '';
  position: absolute;
  right: -40px;
  top: -40px;
  width: 180px;
  height: 180px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.14), transparent 70%);
  border-radius: 50%;
}
.health .row {
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
}
.health .score {
  font-size: 42px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -1px;
}
.health .score small {
  font-size: 13px;
  font-weight: 500;
  opacity: 0.7;
  margin-left: 4px;
}
.health .lvl {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 12px;
  margin-top: 6px;
}
.health .title {
  font-size: 13px;
  opacity: 0.9;
  font-weight: 600;
}
.health .bars {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}
.health .bar {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}
.health .bar .name {
  width: 40px;
  opacity: 0.9;
}
.health .bar .track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 3px;
  overflow: hidden;
}
.health .bar .fill {
  height: 100%;
  background: linear-gradient(90deg, #93c5fd, #fff);
  border-radius: 3px;
}
.health .bar .v {
  width: 28px;
  text-align: right;
  opacity: 0.9;
  font-variant-numeric: tabular-nums;
}

.hero-kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.hkpi {
  background: #fff;
  border-radius: 12px;
  padding: 12px 14px;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--line);
}
.hkpi .lbl {
  color: var(--ink3);
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}
.hkpi .val {
  font-size: 22px;
  font-weight: 800;
  margin: 6px 0 4px;
  font-variant-numeric: tabular-nums;
}
.hkpi .delta {
  font-size: 12px;
  color: var(--ok);
}
.hkpi .delta.down {
  color: var(--bad);
}
.hkpi .ico {
  position: absolute;
  right: 12px;
  top: 12px;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  background: var(--soft);
  color: var(--brand);
}
.hkpi.k2 .ico {
  background: var(--ok-soft);
  color: var(--ok);
}
.hkpi.k3 .ico {
  background: var(--warn-soft);
  color: var(--warn);
}
.hkpi.k4 .ico {
  background: #e0f2fe;
  color: #0284c7;
}
.hkpi .spark {
  margin-top: 6px;
  height: 28px;
  width: 100%;
  display: block;
}

.panel {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid var(--line);
  margin-bottom: 12px;
}
.panel h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-mark {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--brand);
  background: var(--soft);
  border: 1px solid #bfd4f5;
  border-radius: 4px;
  padding: 1px 6px;
}
.run-btn {
  border: none;
  background: var(--brand);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 14px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}
.run-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.run-btn:hover:not(:disabled) {
  filter: brightness(1.06);
}

.dx-wait {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--ink3);
}
.dx-meta {
  font-size: 11px;
  color: var(--ink3);
  margin: 0 0 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.conf-pill {
  background: #e2e8f0;
  border-radius: 4px;
  padding: 1px 6px;
  font-weight: 700;
  color: #475569;
}
.ai-err {
  font-size: 12px;
  color: var(--bad);
  background: var(--bad-soft);
  border-radius: 6px;
  padding: 8px 10px;
  margin-top: 10px;
}
.dx-soft-err {
  font-size: 12px;
  color: var(--ink3);
  margin: 8px 0 0;
}

.ai-insight-body {
  margin-bottom: 12px;
}
.ai-insight-body :deep(.ai-insight) {
  display: grid;
  gap: 10px;
}
@media (min-width: 720px) {
  .ai-insight-body :deep(.ai-insight) {
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
}
.ai-insight-body :deep(.ai-insight-sec) {
  border-radius: 10px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  background: #f8fafc;
}
.ai-insight-body :deep(.ai-insight-sec.fact) {
  border-left: 3px solid var(--brand);
}
.ai-insight-body :deep(.ai-insight-sec.sug) {
  border-left: 3px solid #0284c7;
  background: #f0f9ff;
}
.ai-insight-body :deep(.ai-insight-h) {
  font-size: 12px;
  font-weight: 800;
  color: var(--ink2);
  margin-bottom: 8px;
}
.ai-insight-body :deep(.ai-insight-sec.fact .ai-insight-h) {
  color: var(--brand);
}
.ai-insight-body :deep(.ai-insight-sec.sug .ai-insight-h) {
  color: #0369a1;
}
.ai-insight-body :deep(ul) {
  margin: 0;
  padding: 0 0 0 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-insight-body :deep(li) {
  font-size: 13px;
  line-height: 1.5;
  color: var(--ink2);
}
.ai-insight-body :deep(li strong) {
  color: #0f172a;
  font-weight: 700;
}

.dx-actions {
  margin-top: 4px;
}
.dx-actions-h {
  font-size: 12px;
  font-weight: 800;
  color: var(--ink2);
  margin-bottom: 8px;
}
.dx-action-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.dx-action-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px 14px;
  background: #fff;
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
  color: var(--ink2);
  line-height: 1.45;
  flex: 1;
}
.dx-act {
  align-self: flex-start;
  margin-top: 4px;
  border: none;
  background: var(--brand);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  white-space: normal;
  text-align: left;
  line-height: 1.3;
  max-width: 100%;
}
.dx-act:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.ai-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 0;
}
.ai-grid > .panel {
  margin-bottom: 12px;
}

.flow {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 12px;
  border: 1px solid var(--line);
}
.flow-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 8px;
  flex-wrap: wrap;
}
.flow-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
}
.flow-steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  align-items: stretch;
}
.step {
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid var(--line);
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-right: 12px;
  position: relative;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
  width: calc(100% - 12px);
}
.step:last-child {
  margin-right: 0;
  width: 100%;
}
.step::after {
  content: '';
  position: absolute;
  right: -10px;
  top: 50%;
  width: 8px;
  height: 8px;
  border-top: 2px solid #cbd5e1;
  border-right: 2px solid #cbd5e1;
  transform: translateY(-50%) rotate(45deg);
  z-index: 1;
}
.step:last-child::after {
  display: none;
}
.step .num {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--brand);
  color: var(--brand);
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 26px;
  font-size: 12px;
}
.step .body {
  flex: 1;
  min-width: 0;
}
.step .body .t {
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 6px;
}
.step .body .num-k {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--soft);
  color: var(--brand);
  border-radius: 99px;
  font-weight: 600;
  display: inline-block;
}
.step.done {
  background: var(--ok-soft);
  border-style: solid;
  border-color: #bbf7d0;
}
.step.done .num {
  background: var(--ok);
  border-color: var(--ok);
  color: #fff;
}
.step.warn {
  background: var(--warn-soft);
  border-style: solid;
  border-color: #fed7aa;
}
.step.warn .num {
  background: var(--warn);
  border-color: var(--warn);
  color: #fff;
}
.step.bad {
  background: var(--bad-soft);
  border-style: solid;
  border-color: #fecaca;
}
.step.bad .num {
  background: var(--bad);
  border-color: var(--bad);
  color: #fff;
}

.tl {
  padding-left: 0;
  list-style: none;
  margin: 0;
  max-height: 340px;
  overflow: auto;
}
.tl li {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
}
.tl li:last-child {
  border-bottom: none;
}
.tl .ts {
  color: var(--ink3);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  padding-top: 2px;
}
.tl .ct {
  font-size: 13px;
  line-height: 1.5;
}
.tl .ct .tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  margin-left: 4px;
}
.tl .ct .tag.t-grant {
  background: var(--soft);
  color: var(--brand);
}
.tl .ct .tag.t-active {
  background: #e0f2fe;
  color: #0284c7;
}
.tl .ct .tag.t-issue {
  background: var(--bad-soft);
  color: var(--bad);
}
.tl .ct .tag.t-use {
  background: var(--ok-soft);
  color: var(--ok);
}

@media (max-width: 1180px) {
  .hero {
    grid-template-columns: 1fr;
  }
  .hero-kpis {
    grid-template-columns: repeat(2, 1fr);
  }
  .ai-grid {
    grid-template-columns: 1fr;
  }
  .flow-steps {
    grid-template-columns: 1fr 1fr;
  }
  .step {
    width: 100%;
    margin-right: 0;
  }
  .step::after {
    display: none;
  }
}
@media (max-width: 720px) {
  .hero-kpis,
  .flow-steps {
    grid-template-columns: 1fr;
  }
}
</style>
