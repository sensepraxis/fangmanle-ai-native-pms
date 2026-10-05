<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 周期性维保计划看板（2026年10月）—— 优先 assetsBoard.maintenance + assets.next_maintain_date
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import AssetsFlowNav from '../../components/AssetsFlowNav.vue'

const router = useRouter()

const FALLBACK = {
  rows: [
    {
      area: t('暖通系统'),
      sub: t('空调 / 新风 / 热泵'),
      tasks: [
        { label: t('402 空调滤网'), start: 4, span: 5, status: 'scheduled', row: 0 },
        { label: t('新风滤网更换'), start: 12, span: 4, status: 'ai-optimized', row: 1 },
      ],
    },
    {
      area: t('客房设备'),
      sub: t('卫浴 / 电视 / 床垫'),
      tasks: [
        { label: t('305 马桶检修'), start: 2, span: 3, status: 'overdue', row: 0 },
        { label: t('302 床垫评估'), start: 18, span: 6, status: 'scheduled', row: 0 },
      ],
    },
    {
      area: t('弱电门锁'),
      sub: t('5F 批量电池'),
      tasks: [{ label: t('510 门锁电池'), start: 8, span: 4, status: 'scheduled', row: 0 }],
    },
  ],
  workload: [
    { week: 'W1', original: 72, current: 58, optimized: true },
    { week: 'W2', original: 85, current: 70, optimized: true },
    { week: 'W3', original: 68, current: 65, optimized: false },
    { week: 'W4', original: 55, current: 52, optimized: false },
  ],
  critical: [
    {
      title: t('305 TOTO 智能马桶'),
      due: t('已逾期'),
      desc: t('水压异常波动，建议立即检查水阀'),
      tone: 'error',
      action: t('立即派工'),
    },
    {
      title: t('402 大金中央空调'),
      due: t('今日'),
      desc: t('运行功率偏高 20%，建议清洗滤网'),
      tone: 'warn',
      action: t('确认排程'),
    },
    {
      title: t('5F 智能门锁集群'),
      due: t('本周'),
      desc: t('多把门锁电量告警，建议批量更换电池'),
      tone: '',
      action: t('生成工单'),
    },
  ],
}

const data = ref<any>({ ...FALLBACK })

function parseDay(d?: string) {
  if (!d) return 1
  const n = parseInt(String(d).slice(8, 10), 10)
  return Number.isFinite(n) ? Math.min(28, Math.max(1, n)) : 1
}

function mapStatus(st?: string) {
  if (st === 'done') return 'completed'
  if (st === 'overdue') return 'overdue'
  if (st === 'doing') return 'scheduled'
  return 'scheduled'
}

function buildRows(maint: any[], assets: any[]) {
  const assetById = Object.fromEntries(assets.map((a) => [a.id, a]))
  const groups: Record<string, { m: any; asset: any }[]> = {}

  for (const m of maint) {
    const asset = assetById[m.asset_id]
    const area = asset?.category || t('综合维保')
    if (!groups[area]) groups[area] = []
    groups[area].push({ m, asset })
  }

  for (const a of assets.filter((x) => x.next_maintain_date).slice(0, 8)) {
    const area = a.category || t('计划维保')
    if (!groups[area]) groups[area] = []
    const exists = groups[area].some((x) => x.asset?.id === a.id)
    if (!exists) {
      groups[area].push({
        m: {
          due_date: a.next_maintain_date,
          status: 'scheduled',
          task_type: t('预防性保养'),
          note: a.insight,
        },
        asset: a,
      })
    }
  }

  return Object.entries(groups)
    .slice(0, 6)
    .map(([area, items]) => ({
      area,
      sub: `${items.length} 项任务 · ${items[0]?.asset?.location || t('全店')}`,
      tasks: items.slice(0, 3).map(({ m, asset }, idx) => ({
        label:
          (asset?.room_no ? `${asset.room_no} ` : '') +
          (asset?.name || m.task_type || t('维保')).slice(0, 14),
        start: Math.max(0, parseDay(m.due_date) - 2),
        span: Math.min(8, Math.max(3, 4 + (idx % 2))),
        status: mapStatus(m.status),
        row: idx > 0 ? 1 : 0,
      })),
    }))
}

function buildWorkload(maint: any[]) {
  const weeks = [0, 0, 0, 0]
  for (const m of maint) {
    const day = parseDay(m.due_date)
    weeks[Math.min(3, Math.floor((day - 1) / 7))] += 1
  }
  if (!weeks.some(Boolean)) return FALLBACK.workload
  const max = Math.max(...weeks, 1)
  return weeks.map((c, i) => ({
    week: `W${i + 1}`,
    original: Math.min(100, Math.round(((c * 1.15) / max) * 100)),
    current: Math.min(100, Math.round((c / max) * 100)),
    optimized: i === 1 && c > 0,
  }))
}

function buildCritical(maint: any[], alerts: any[], assets: any[]) {
  const assetById = Object.fromEntries(assets.map((a) => [a.id, a]))
  const items = [
    ...maint
      .filter((m) => m.status === 'overdue')
      .slice(0, 3)
      .map((m) => {
        const asset = assetById[m.asset_id]
        return {
          title: asset
            ? `${asset.room_no || ''} ${asset.name}`.trim()
            : m.task_type || t('逾期维保'),
          due: t('已逾期'),
          desc: m.note || asset?.insight || t('请尽快安排工程人员处理'),
          tone: 'error',
          action: t('立即派工'),
        }
      }),
    ...alerts
      .filter((a) => a.severity === 'high')
      .slice(0, 3)
      .map((a) => ({
        title: [a.room_no, a.asset_name].filter(Boolean).join(' ') || t('设备告警'),
        due: t('今日'),
        desc: a.message || '',
        tone: 'warn',
        action: t('确认排程'),
      })),
  ]
  // 去重标题
  const seen = new Set<string>()
  const unique = items.filter((x) => {
    if (seen.has(x.title)) return false
    seen.add(x.title)
    return true
  })
  return unique.length ? unique.slice(0, 4) : FALLBACK.critical
}

function goTracking() {
  router.push('/c8-assets/tracking')
}

async function load() {
  try {
    const board = await api.assetsBoard(hotelStore.hotelId)
    const assets = board?.assets || []
    const maint = board?.maintenance || []
    const alerts = board?.alerts || []

    const rows = buildRows(maint, assets)
    const workload = buildWorkload(maint)
    const critical = buildCritical(maint, alerts, assets)

    data.value = {
      rows: rows.length ? rows : FALLBACK.rows,
      workload: maint.length ? workload : FALLBACK.workload,
      critical,
    }
  } catch {
    data.value = { ...FALLBACK }
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page">
    <!-- 页头：标题左 / 操作右 -->
    <header class="page-head">
      <div class="head-copy">
        <h1>{{ t('周期性维保计划看板') }}</h1>
        <p>{{ t('2026年10月 · 长期维护排期') }}</p>
      </div>
      <div class="head-actions">
        <button class="btn-primary" type="button">
          <span class="material-symbols-outlined">auto_awesome</span>
          {{ t('AI 自动优化排程') }}
        </button>
        <button class="btn-ghost" type="button">
          <span class="material-symbols-outlined">calendar_month</span>
          {{ t('班次排程') }}
        </button>
      </div>
    </header>

    <!-- 图例（对齐原型：操作行旁） -->
    <div class="legend-row">
      <span class="legend-item"><i class="dot scheduled"></i>{{ t('已排程') }}</span>
      <span class="legend-item"><i class="dot completed"></i>{{ t('已完成') }}</span>
      <span class="legend-item"><i class="dot overdue"></i>{{ t('逾期') }}</span>
      <span class="legend-item"><i class="dot ai"></i>{{ t('AI 已重排') }}</span>
    </div>

    <!-- AI 洞察横幅 -->
    <div class="ai-banner">
      <span class="material-symbols-outlined ai-ico">psychology</span>
      <div>
        <h4>{{ t('工作量均衡已启用') }}</h4>
        <p>
          {{
            t(
              'AI 已将 3 项深度清洁从本周末移至下周二，以避开 95% 预测入住高峰。员工工作量现已均衡。',
            )
          }}
        </p>
      </div>
    </div>

    <div class="main-grid">
      <!-- 甘特 -->
      <section class="gantt-card">
        <div class="gantt-head">
          <h2>{{ t('长期维护排期（2026年10月）') }}</h2>
          <span class="week-label">{{ t('第 1–4 周') }}</span>
        </div>
        <div class="gantt-scroll">
          <div class="gantt-row gantt-header">
            <div class="gantt-label">{{ t('区域 / 任务组') }}</div>
            <div class="gantt-grid days">
              <div v-for="d in 30" :key="d" class="gantt-day">{{ d }}</div>
            </div>
          </div>
          <div v-for="row in data.rows" :key="row.area" class="gantt-row">
            <div class="gantt-label">
              <span class="area-name">{{ row.area }}</span>
              <span class="area-sub">{{ row.sub }}</span>
            </div>
            <div class="gantt-grid gantt-track">
              <div
                v-for="t in row.tasks"
                :key="t.label + t.start"
                class="task-bar"
                :class="'status-' + t.status"
                :style="{
                  left: (t.start / 30) * 100 + '%',
                  width: (t.span / 30) * 100 + '%',
                  top: (t.row ? 44 : 8) + 'px',
                }"
              >
                {{ t.label }}
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右侧栏 -->
      <aside class="side-col">
        <div class="side-card">
          <h3 class="side-title">{{ t('员工工作量预测') }}</h3>
          <div class="workload-chart">
            <div v-for="(w, i) in data.workload" :key="i" class="wl-col">
              <div class="wl-bars">
                <div class="wl-bar-bg" :style="{ height: w.original + '%' }"></div>
                <div
                  class="wl-bar"
                  :class="w.optimized ? 'opt' : 'base'"
                  :style="{ height: w.current + '%' }"
                ></div>
              </div>
              <span class="wl-week">{{ w.week }}</span>
            </div>
          </div>
          <div class="wl-legend">
            <span><i class="lg-dot muted"></i>{{ t('原方案') }}</span>
            <span><i class="lg-dot tertiary"></i>{{ t('已优化') }}</span>
          </div>
        </div>

        <div class="side-card attention-card">
          <h3 class="side-title">{{ t('需关注') }}</h3>
          <div class="crit-list">
            <article
              v-for="c in data.critical"
              :key="c.title"
              class="crit-item"
              :class="{
                'is-error': c.tone === 'error',
                'is-warn': c.tone === 'warn',
              }"
            >
              <div class="crit-top">
                <h4 class="crit-title">{{ c.title }}</h4>
                <span class="crit-badge">{{ c.due }}</span>
              </div>
              <p class="crit-desc">{{ c.desc }}</p>
              <button v-if="c.action" class="crit-btn" type="button" @click="goTracking">
                {{ c.action }}
              </button>
            </article>
          </div>
        </div>
      </aside>
    </div>

    <AssetsFlowNav />
  </div>
</template>

<style scoped>
.page {
  max-width: 1400px;
}

/* —— 页头 —— */
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.head-copy h1 {
  margin: 0 0 6px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--on-surface, #1f2329);
  line-height: 1.25;
}
.head-copy p {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant, #5b616e);
}
.head-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.btn-primary,
.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  line-height: 1.2;
}
.btn-primary {
  background: var(--primary, #2563eb);
  color: #fff;
}
.btn-primary:hover {
  opacity: 0.92;
}
.btn-ghost {
  background: var(--surface-container-lowest, #fff);
  color: var(--on-surface, #1f2329);
  border: 1px solid var(--outline-variant, #c9ced8);
}
.btn-ghost:hover {
  background: var(--surface-container-low, #f3f4f6);
}
.btn-primary .material-symbols-outlined,
.btn-ghost .material-symbols-outlined {
  font-size: 18px;
}

/* —— 图例 —— */
.legend-row {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--on-surface-variant, #5b616e);
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  display: inline-block;
}
.dot.scheduled {
  background: var(--primary, #2563eb);
}
.dot.completed {
  background: #1e8e3e;
}
.dot.overdue {
  background: var(--error, #ba1a1a);
}
.dot.ai {
  background: var(--tertiary, #8c33b3);
}

/* —— AI 横幅 —— */
.ai-banner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 18px;
  margin-bottom: 20px;
  border-radius: 12px;
  background: var(--tertiary-fixed, #f8d8ff);
  color: var(--on-tertiary-fixed, #2e004e);
  border-left: 4px solid var(--tertiary, #8c33b3);
}
.ai-ico {
  font-size: 22px;
  color: var(--tertiary, #8c33b3);
  margin-top: 1px;
  flex-shrink: 0;
}
.ai-banner h4 {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.3;
}
.ai-banner p {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  opacity: 0.9;
}

/* —— 主栅格 —— */
.main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
}

/* —— 甘特 —— */
.gantt-card {
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant, #c9ced8);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.gantt-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid var(--outline-variant, #e2e5eb);
  background: var(--surface-container-lowest, #fff);
}
.gantt-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
}
.week-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--on-surface-variant, #5b616e);
}
.gantt-scroll {
  overflow-x: auto;
}
.gantt-row {
  display: grid;
  grid-template-columns: 168px 1fr;
  border-bottom: 1px solid var(--outline-variant, #e2e5eb);
  min-height: 84px;
}
.gantt-header {
  min-height: 0;
  background: var(--surface-container-low, #f3f4f6);
  position: sticky;
  top: 0;
  z-index: 10;
}
.gantt-label {
  padding: 12px 14px;
  border-right: 1px solid var(--outline-variant, #e2e5eb);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
}
.area-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface, #1f2329);
  line-height: 1.3;
}
.area-sub {
  font-size: 11px;
  color: var(--on-surface-variant, #5b616e);
  line-height: 1.35;
  font-weight: 400;
}
.gantt-grid {
  display: grid;
  grid-template-columns: repeat(30, minmax(26px, 1fr));
  min-width: 780px;
}
.gantt-grid.days {
  background: var(--surface-container-low, #f3f4f6);
}
.gantt-day {
  text-align: center;
  padding: 8px 0;
  font-size: 11px;
  color: var(--on-surface-variant, #5b616e);
  border-right: 1px solid rgba(193, 198, 214, 0.35);
}
.gantt-track {
  position: relative;
  background: var(--surface, #fff);
  min-height: 84px;
}
.task-bar {
  position: absolute;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  padding: 0 10px;
  color: #fff;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}
.status-scheduled {
  background: var(--primary, #2563eb);
}
.status-completed {
  background: #1e8e3e;
}
.status-overdue {
  background: var(--error, #ba1a1a);
}
.status-ai-optimized {
  background: var(--tertiary, #8c33b3);
  box-shadow: 0 0 8px rgba(140, 51, 179, 0.45);
}

/* —— 右侧栏 —— */
.side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.side-card {
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant, #c9ced8);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.attention-card {
  flex: 1;
}
.side-title {
  margin: 0 0 14px;
  font-size: 14px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
  letter-spacing: -0.01em;
}

/* 工作量柱图 */
.workload-chart {
  display: flex;
  align-items: stretch;
  gap: 8px;
  height: 132px;
  border-bottom: 1px solid var(--outline-variant, #e2e5eb);
  padding-bottom: 6px;
  margin-bottom: 10px;
}
.wl-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
}
.wl-bars {
  position: relative;
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
}
.wl-bar-bg {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--surface-variant, #e1e3ea);
  opacity: 0.55;
  border-radius: 3px 3px 0 0;
}
.wl-bar {
  position: relative;
  z-index: 1;
  width: 100%;
  border-radius: 3px 3px 0 0;
  min-height: 4px;
}
.wl-bar.base {
  background: var(--primary, #2563eb);
}
.wl-bar.opt {
  background: var(--tertiary, #8c33b3);
}
.wl-week {
  margin-top: 6px;
  font-size: 10px;
  color: var(--on-surface-variant, #5b616e);
}
.wl-legend {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--on-surface-variant, #5b616e);
}
.wl-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.lg-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  display: inline-block;
}
.lg-dot.muted {
  background: var(--surface-variant, #e1e3ea);
  opacity: 0.8;
}
.lg-dot.tertiary {
  background: var(--tertiary, #8c33b3);
}

/* —— 需关注（重点美化） —— */
.crit-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.crit-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant, #d5d9e2);
  background: var(--surface-container-lowest, #fff);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}
.crit-item:hover {
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}
.crit-item.is-error {
  border-color: rgba(186, 26, 26, 0.35);
  background: rgba(255, 218, 214, 0.35);
}
.crit-item.is-warn {
  border-color: rgba(186, 26, 26, 0.22);
  background: rgba(255, 218, 214, 0.18);
}
.crit-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.crit-title {
  margin: 0;
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 650;
  line-height: 1.4;
  color: var(--on-surface, #1f2329);
  word-break: break-word;
}
.crit-item.is-error .crit-title,
.crit-item.is-warn .crit-title {
  color: var(--error, #ba1a1a);
}
.crit-badge {
  flex-shrink: 0;
  margin-top: 1px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: 0.01em;
  white-space: nowrap;
  color: var(--on-surface-variant, #5b616e);
  background: var(--surface-container-low, #f0f1f4);
}
.crit-item.is-error .crit-badge,
.crit-item.is-warn .crit-badge {
  color: var(--error, #ba1a1a);
  background: rgba(186, 26, 26, 0.1);
}
.crit-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.55;
  color: var(--on-surface-variant, #5b616e);
}
.crit-btn {
  align-self: flex-start;
  margin-top: 2px;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant, #c9ced8);
  background: #fff;
  color: var(--on-surface, #1f2329);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  line-height: 1.2;
}
.crit-btn:hover {
  border-color: var(--primary, #2563eb);
  color: var(--primary, #2563eb);
  background: rgba(37, 99, 235, 0.04);
}
.crit-item.is-error .crit-btn:hover {
  border-color: var(--error, #ba1a1a);
  color: var(--error, #ba1a1a);
  background: rgba(186, 26, 26, 0.04);
}

@media (max-width: 1100px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
  .side-col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
}
@media (max-width: 720px) {
  .side-col {
    grid-template-columns: 1fr;
  }
}
</style>
