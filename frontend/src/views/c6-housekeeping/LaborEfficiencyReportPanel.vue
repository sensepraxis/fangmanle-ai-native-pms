<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * 今日运营 — 信息分层：房态 → 任务 → 决策 → 追踪 → 热力
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import HkAiPlanDrawer, { type HkAiScene } from '../../components/HkAiPlanDrawer.vue'

const router = useRouter()
const slots = [
  '08:00',
  '09:00',
  '10:00',
  '11:00',
  '12:00',
  '13:00',
  '14:00',
  '15:00',
  '16:00',
  '17:00',
  '18:00',
  '19:00',
]

const LEVEL: Record<number, { bg: string; border: string; label: string }> = {
  0: { bg: '#e8eaed', border: '#c1c6d6', label: t('无任务') },
  1: { bg: '#dcfce7', border: '#86efac', label: t('正常≤80%') },
  2: { bg: '#fef3c7', border: '#f9ab00', label: t('紧张80–120%') },
  3: { bg: '#fee2e2', border: '#ba1a1a', label: t('告警>120%') },
}

const REFRESH_OPTS = [
  { sec: 30, label: '30s' },
  { sec: 60, label: '1min' },
  { sec: 300, label: '5min' },
] as const

function nowSlotIndex() {
  const h = new Date().getHours()
  return Math.max(0, Math.min(11, h - 8))
}

const autoRefresh = ref(true)
const refreshSec = ref(30)
const lastUpdated = ref<Date | null>(null)
const loading = ref(false)
const routeOpen = ref(false)
const tip = ref<{ row: string; hour: string; lv: number; count?: number; ratio?: number } | null>(
  null,
)
const aiOpen = ref(false)
const aiScene = ref<HkAiScene>('floor_rebalance')

const data = ref<any>({
  completionProgress: null as number | null,
  targetFulfill: 90,
  wowFulfill: null as number | null,
  doneToday: 0,
  toClean: 0,
  waiting: 0,
  progress: 0,
  inspect: 0,
  avgDisplay: null as number | null,
  avgNote: '',
  routes: 0,
  routeNote: '',
  routeExcluded: [] as any[],
  decisionText: '',
  peakLabel: '',
  peakKind: '',
  capacityOk: null as boolean | null,
  onDuty: 0,
  onDutyLabel: t('在岗'),
  scheduledOn: 0,
  roomsTotal: 0,
  dirty: 0,
  vacant: 0,
  occupiedOoo: 0,
  heatmapFormula: '',
  dispatchSuggest: null as any,
  heatmap: [] as { dept: string; slots: number[]; counts?: number[]; ratios?: number[] }[],
  routeItems: [] as any[],
})

async function load() {
  loading.value = true
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId)
    const labor = board?.labor_today || {}
    const snap = board?.status_snapshot || {}
    const alertObj = board?.dispatch_alert || {}

    const heatRows = (board?.floor_hour_heatmap || labor.floor_hour_heatmap || []).map(
      (f: any) => ({
        dept: f.label || `${f.floor}F`,
        slots: Array.isArray(f.slots) ? f.slots : Array(12).fill(0),
        counts: Array.isArray(f.counts) ? f.counts : Array(12).fill(0),
        ratios: Array.isArray(f.ratios) ? f.ratios : [],
      }),
    )

    const routeItems = (board?.route || [])
      .filter((t: any) => t && Number(t.id) > 0)
      .map((t: any) => ({
        id: t.id,
        room_no: t.room_no,
        assignee: t.assignee || t('待分配'),
        floor: t.floor,
        tag: t.tag,
        eta: t.eta,
      }))

    const occOoo = (labor.occupied ?? snap.occupied ?? 0) + (labor.ooo ?? snap.ooo ?? 0)
    const suggest =
      labor.dispatch_suggest || snap.dispatch_suggest || alertObj.dispatch_suggest || null
    const capOk = snap.capacity_ok ?? alertObj.capacity_ok
    const decision = labor.decision_text || snap.decision_text || alertObj.decision_text || ''

    data.value = {
      completionProgress: labor.completion_progress ?? labor.fulfillment ?? null,
      targetFulfill: labor.target_fulfill ?? 90,
      wowFulfill: labor.wow_fulfill ?? null,
      doneToday: labor.done_today ?? 0,
      toClean: labor.to_clean ?? (labor.waiting ?? 0) + (labor.progress ?? 0),
      waiting: labor.waiting ?? snap.waiting ?? 0,
      progress: labor.progress ?? snap.progress ?? 0,
      inspect: labor.inspect ?? snap.inspect ?? 0,
      avgDisplay: labor.avg_min_display ?? labor.avg_min_today ?? null,
      avgNote: labor.avg_note || '',
      routes: labor.route_count ?? routeItems.length,
      routeNote: labor.route_note || '',
      routeExcluded: labor.route_excluded || [],
      decisionText: decision,
      peakLabel: labor.peak_label || snap.peak_label || alertObj.peak_label || '',
      peakKind: labor.peak_kind || snap.peak_kind || '',
      capacityOk:
        typeof capOk === 'boolean'
          ? capOk
          : decision.includes('→ 够')
            ? true
            : decision.includes('不够')
              ? false
              : null,
      onDuty: labor.on_duty ?? snap.on_duty ?? 0,
      onDutyLabel: labor.on_duty_label || snap.on_duty_label || t('在岗'),
      scheduledOn: labor.scheduled_on ?? snap.scheduled_on ?? 0,
      roomsTotal: labor.rooms_total ?? snap.rooms_total ?? board?.room_status?.total ?? 0,
      dirty: labor.dirty ?? snap.dirty ?? 0,
      vacant: labor.vacant ?? snap.vacant ?? 0,
      occupiedOoo: alertObj.occupied_ooo ?? snap.occupied_ooo ?? occOoo,
      heatmapFormula:
        labor.heatmap_formula || t('该时段新增任务数 ÷ 该楼层当前产能（在岗×2间/时）'),
      dispatchSuggest: suggest,
      heatmap: heatRows,
      routeItems,
    }
    lastUpdated.value = new Date()
  } catch {
    lastUpdated.value = new Date()
  } finally {
    loading.value = false
  }
}

const updatedText = computed(() => {
  if (!lastUpdated.value) return t('尚未更新')
  const sec = Math.max(0, Math.round((Date.now() - lastUpdated.value.getTime()) / 1000))
  if (sec < 10) return t('刚刚更新')
  if (sec < 60) return t('{n} 秒前更新', { n: sec })
  return t('{n} 分钟前更新', { n: Math.floor(sec / 60) })
})

const wowText = computed(() => {
  const v = data.value.wowFulfill
  if (v == null) return '—'
  return `${v > 0 ? '+' : ''}${v}%`
})

const verdict = computed(() => {
  if (data.value.capacityOk === true) return { ok: true, text: t('产能够'), tone: 'ok' }
  if (data.value.capacityOk === false) return { ok: false, text: t('产能不够'), tone: 'bad' }
  return { ok: null, text: t('待评估'), tone: 'flat' }
})

/** 决策一句话：去掉与上方重复的房态/任务罗列 */
const decisionBrief = computed(() => {
  const raw = String(data.value.decisionText || '')
  // 取「窗口产能…→ 够/不够」一段；没有则压缩原文
  const m = raw.match(/(\d{2}:00 前[^。]*?(?:够|不够))/)
  if (m) return m[1]
  if (raw.length <= 72) return raw
  return raw.slice(0, 70) + '…'
})

const suggestOneLiner = computed(() => data.value.dispatchSuggest?.message || '')

let timer: number | undefined
let tick: number | undefined
const tickNow = ref(0)

function resetTimer() {
  if (timer) clearInterval(timer)
  timer = undefined
  if (!autoRefresh.value) return
  timer = window.setInterval(() => load(), refreshSec.value * 1000)
}

onMounted(() => {
  load()
  tick = window.setInterval(() => {
    tickNow.value += 1
  }, 15000)
  resetTimer()
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (tick) clearInterval(tick)
})
watch(() => hotelStore.hotelId, load)
watch([autoRefresh, refreshSec], resetTimer)

const NOW = computed(() => {
  void tickNow.value
  return nowSlotIndex()
})

function cellTip(row: any, ci: number, lv: number) {
  tip.value = {
    row: row.dept,
    hour: slots[ci],
    lv,
    count: row.counts?.[ci],
    ratio: row.ratios?.[ci],
  }
}

function goDispatch() {
  router.push('/c6-housekeeping/housekeeping')
}
function goDispatchFromRoute() {
  goDispatch()
  routeOpen.value = false
}
function goStaffing() {
  router.push('/c6-housekeeping/staffing')
}
function openAi(scene: HkAiScene) {
  aiScene.value = scene
  aiOpen.value = true
}
function onAiConfirmed() {
  load()
  toast(t('安排已生效'))
}
function fmtPct(v: number | null | undefined) {
  return v == null || Number.isNaN(Number(v)) ? '—' : String(v)
}
</script>

<template>
  <div class="labor-panel">
    <div class="page-head head-row">
      <div>
        <h2 class="panel-title">{{ t('今日运营') }}</h2>
      </div>
      <div class="head-actions">
        <label class="refresh-tog">
          <input v-model="autoRefresh" type="checkbox" />
          {{ t('自动刷新') }}</label
        >
        <select
          v-model.number="refreshSec"
          class="refresh-sel"
          :disabled="!autoRefresh"
          :aria-label="t('刷新间隔')"
        >
          <option v-for="o in REFRESH_OPTS" :key="o.sec" :value="o.sec">{{ o.label }}</option>
        </select>
        <button class="btn btn-ghost" type="button" :disabled="loading" @click="load">
          {{ loading ? t('刷新中…') : t('刷新') }}
        </button>
        <span class="live-pill">
          <span class="dot"></span>{{ updatedText }} · {{ refreshSec }}s
        </span>
      </div>
    </div>

    <!-- ① 房态：一眼四格 -->
    <section class="block" :aria-label="t('房态总览')">
      <div class="block-label">{{ t('房态') }}</div>
      <div class="room-status-strip">
        <div class="rs-item">
          <span class="rs-label">{{ t('总房') }}</span>
          <strong class="rs-val">{{ data.roomsTotal }}</strong
          ><em>{{ t('间') }}</em>
        </div>
        <div class="rs-item dirty">
          <span class="rs-label">{{ t('脏房') }}</span>
          <strong class="rs-val">{{ data.dirty }}</strong
          ><em>{{ t('间') }}</em>
        </div>
        <div class="rs-item clean">
          <span class="rs-label">{{ t('净房') }}</span>
          <strong class="rs-val">{{ data.vacant }}</strong
          ><em>{{ t('间') }}</em>
        </div>
        <div class="rs-item ooo">
          <span class="rs-label">{{ t('占用 / 维修锁房') }}</span>
          <strong class="rs-val">{{ data.occupiedOoo }}</strong
          ><em>{{ t('间') }}</em>
        </div>
      </div>
    </section>

    <!-- ② 任务：待清洁拆开 -->
    <section class="block" :aria-label="t('清洁任务')">
      <div class="block-label">{{ t('清洁任务') }}</div>
      <div class="task-strip">
        <div class="ts-item primary">
          <span class="ts-label">{{ t('待清洁') }}</span>
          <strong>{{ data.toClean }}</strong>
          <em>{{ t('= 待分配 + 进行中') }}</em>
        </div>
        <div class="ts-item">
          <span class="ts-label">{{ t('待分配') }}</span>
          <strong>{{ data.waiting }}</strong>
        </div>
        <div class="ts-item">
          <span class="ts-label">{{ t('进行中') }}</span>
          <strong>{{ data.progress }}</strong>
        </div>
        <div class="ts-item">
          <span class="ts-label">{{ t('待验收') }}</span>
          <strong>{{ data.inspect }}</strong>
        </div>
        <div class="ts-item">
          <span class="ts-label">{{ data.onDutyLabel }}</span>
          <strong>{{ data.onDuty }}</strong>
          <em v-if="data.scheduledOn">{{ t('应到 {n}', { n: data.scheduledOn }) }}</em>
        </div>
      </div>
    </section>

    <!-- ③ 决策：只留够不够 + 一句话 + 行动 -->
    <section class="decision-banner" :class="verdict.tone" :aria-label="t('产能决策')">
      <div class="dec-left">
        <div class="verdict-pill" :class="verdict.tone">{{ verdict.text }}</div>
        <div class="dec-body">
          <h3>{{ t('下一步') }}</h3>
          <p class="dec-main">{{ decisionBrief || t('暂无产能判断') }}</p>
          <p v-if="suggestOneLiner" class="dec-sub">
            {{ t('调拨建议：{msg}', { msg: suggestOneLiner }) }}
          </p>
          <p v-else-if="data.peakLabel" class="dec-sub">{{ data.peakLabel }}</p>
        </div>
      </div>
      <div class="dec-acts">
        <button class="btn btn-ghost" type="button" @click="goStaffing">{{ t('去排班') }}</button>
        <button
          v-if="commercialEnabled()"
          class="btn btn-ghost"
          type="button"
          @click="openAi('cleaning_plan')"
        >
          {{ t('AI清扫安排') }}
        </button>
        <button
          v-if="commercialEnabled()"
          class="btn btn-primary"
          type="button"
          @click="openAi('floor_rebalance')"
        >
          {{ t('AI一键调拨') }}
        </button>
      </div>
    </section>

    <HkAiPlanDrawer v-model:open="aiOpen" :scene="aiScene" @confirmed="onAiConfirmed" />

    <div class="grid">
      <div class="card-clean gauge-card">
        <h2>{{ t('今日完成进度') }}</h2>
        <div class="gauge">
          <svg viewBox="0 0 100 100" class="gauge-svg">
            <circle
              cx="50"
              cy="50"
              r="40"
              fill="none"
              stroke="var(--surface-high)"
              stroke-width="8"
            />
            <circle
              v-if="data.completionProgress != null"
              cx="50"
              cy="50"
              r="40"
              fill="none"
              :stroke="
                data.completionProgress >= data.targetFulfill
                  ? '#16a34a'
                  : data.completionProgress >= 50
                    ? '#f9ab00'
                    : '#ba1a1a'
              "
              stroke-width="8"
              stroke-linecap="round"
              :stroke-dasharray="251.2"
              :stroke-dashoffset="251.2 * (1 - (data.completionProgress || 0) / 100)"
            />
          </svg>
          <div class="gauge-num">
            <span class="num"
              >{{ fmtPct(data.completionProgress)
              }}<small v-if="data.completionProgress != null">%</small></span
            >
            <span class="bench">{{ t('目标') }} {{ data.targetFulfill }}%</span>
          </div>
        </div>
        <p class="hint">
          {{ t('已完成') }} {{ data.doneToday }} / {{ t('待清洁') }} {{ data.toClean }}（{{
            t('环比')
          }}
          {{ wowText }}）
        </p>
        <button class="btn btn-ghost sm" type="button" @click="goDispatch">
          {{ t('去派单') }}
        </button>
      </div>

      <div class="card-clean metrics-card">
        <div class="metrics-head">
          <h2>{{ t('今日作业追踪') }}</h2>
          <span class="pill">{{ t('实时') }}</span>
        </div>
        <div class="metrics">
          <div class="metric">
            <span class="m-label">{{ t('今日已完成') }}</span>
            <div class="m-val">
              <strong>{{ data.doneToday }}</strong
              ><em>{{ t('单') }}</em>
            </div>
            <div class="bench">{{ t('仅统计今日闭环任务') }}</div>
          </div>
          <button type="button" class="metric clickable" @click="routeOpen = true">
            <span class="m-label"
              >{{ t('建议路径') }} <span class="linkish">{{ t('明细 →') }}</span></span
            >
            <div class="m-val">
              <strong>{{ data.routes }}</strong
              ><em>{{ t('间') }}</em>
            </div>
            <div class="bench">{{ t('对应待分配') }} {{ data.waiting }} {{ t('间') }}</div>
          </button>
          <div class="metric">
            <span class="m-label">{{ t('平均清扫时长') }}</span>
            <div class="m-val">
              <strong>{{ data.avgDisplay != null ? data.avgDisplay : '—' }}</strong>
              <em v-if="data.avgDisplay != null">min</em>
            </div>
            <div class="bench">{{ data.avgNote || t('暂无样本') }}</div>
          </div>
        </div>
      </div>

      <div class="card-clean heat-card">
        <div class="heat-head">
          <div>
            <h2>{{ t('楼层 × 时段负荷') }}</h2>
            <p>{{ data.heatmapFormula }}</p>
          </div>
          <div class="heat-legend">
            <span v-for="(lv, k) in LEVEL" :key="k"
              ><i :style="{ background: lv.bg, borderColor: lv.border }"></i>{{ lv.label }}</span
            >
          </div>
        </div>
        <div v-if="data.heatmap.length" class="heat-scroll">
          <div class="hm-head">
            <div></div>
            <div v-for="(s, i) in slots" :key="s" :class="{ now: i === NOW }">{{ s }}</div>
          </div>
          <div v-for="(row, ri) in data.heatmap" :key="ri" class="hm-row">
            <div class="hm-label">{{ row.dept }}</div>
            <div
              v-for="(lv, ci) in row.slots"
              :key="ci"
              class="hm-cell"
              :class="{ now: ci === NOW }"
              :style="{ background: LEVEL[lv]?.bg, borderColor: LEVEL[lv]?.border }"
              @mouseenter="cellTip(row, ci, lv)"
              @mouseleave="tip = null"
              @click="lv >= 2 ? goDispatch() : null"
            >
              <span v-if="lv >= 2" class="cell-tag" :class="{ alert: lv === 3 }">{{
                lv === 3 ? t('告警') : t('紧')
              }}</span>
            </div>
          </div>
        </div>
        <p v-else class="empty-hint">{{ t('今日暂无按楼层落点的新建任务。') }}</p>
        <p v-if="tip" class="tip-line">
          {{ tip.row }} · {{ tip.hour }} · {{ LEVEL[tip.lv]?.label }}
          <template v-if="tip.count != null"> · {{ tip.count }} {{ t('任务') }}</template>
          <template v-if="tip.ratio != null && tip.ratio > 0">
            · {{ t('负荷') }} {{ Math.round(tip.ratio * 100) }}%</template
          >
        </p>
      </div>
    </div>

    <div v-if="routeOpen" class="mask" @click.self="routeOpen = false">
      <div class="panel" role="dialog" :aria-label="t('建议路径明细')">
        <header>
          <h3>{{ t('建议路径明细') }}</h3>
          <button type="button" class="x" @click="routeOpen = false">×</button>
        </header>
        <p class="panel-sub">{{ data.routeNote || t('待分配 {n} 间', { n: data.waiting }) }}</p>
        <ul v-if="data.routeItems.length" class="route-list">
          <li v-for="(r, i) in data.routeItems" :key="r.id">
            <strong>{{ i + 1 }}. {{ r.room_no }}</strong>
            <span
              >{{ r.floor ? r.floor + 'F · ' : '' }}{{ r.assignee
              }}{{ r.tag ? ' · ' + r.tag : '' }}</span
            >
          </li>
        </ul>
        <p v-else class="empty-hint">{{ t('当前无待分配任务。') }}</p>
        <div v-if="data.routeExcluded?.length" class="excl">
          <strong>{{ t('已排除') }}</strong>
          <span v-for="e in data.routeExcluded" :key="e.id || e.room_no"
            >{{ e.room_no }}（{{ e.reason }}）</span
          >
        </div>
        <footer>
          <button type="button" class="btn btn-ghost" @click="routeOpen = false">
            {{ t('关闭') }}
          </button>
          <button type="button" class="btn btn-primary" @click="goDispatchFromRoute">
            {{ t('去派单') }}
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel-title {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 800;
}
.labor-panel .page-head p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.head-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.refresh-tog {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--on-surface-variant);
}
.refresh-sel {
  height: 32px;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 0 8px;
  font-size: 12px;
  font-weight: 700;
  font-family: inherit;
  background: #fff;
}
.live-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--secondary);
  background: var(--surface-low);
  border: 1px solid var(--outline-variant);
  padding: 6px 12px;
  border-radius: 999px;
}
.live-pill .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #16a34a;
}

.block {
  margin-bottom: 12px;
}
.block-label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--on-surface-variant);
  margin-bottom: 8px;
  text-transform: uppercase;
}

.room-status-strip,
.task-strip {
  display: grid;
  gap: 10px;
}
.room-status-strip {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.task-strip {
  grid-template-columns: 1.4fr repeat(4, minmax(0, 1fr));
}
@media (max-width: 900px) {
  .room-status-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .task-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.rs-item,
.ts-item {
  background: #fff;
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}
.rs-item.dirty {
  border-color: #f9ab00;
  background: #fffbf0;
}
.rs-item.clean {
  border-color: #86efac;
  background: #f0fdf4;
}
.rs-item.ooo {
  border-color: #c1c6d6;
  background: #f8f9fb;
}
.ts-item.primary {
  border-color: var(--primary);
  background: #eef4ff;
}
.rs-label,
.ts-label {
  width: 100%;
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface-variant);
  margin-bottom: 2px;
}
.rs-val,
.ts-item strong {
  font-size: 28px;
  font-weight: 800;
  color: var(--on-surface);
  line-height: 1;
}
.rs-item em,
.ts-item em {
  font-style: normal;
  font-size: 12px;
  color: var(--on-surface-variant);
  font-weight: 600;
}

.decision-banner {
  margin: 14px 0 16px;
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  border-radius: 14px;
  padding: 14px 16px;
  border: 1px solid var(--outline-variant);
  background: #fff;
}
.decision-banner.bad {
  border-color: #f9ab00;
  background: #fff8e8;
}
.decision-banner.ok {
  border-color: #86efac;
  background: #f0fdf4;
}
.dec-left {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  min-width: 0;
  flex: 1;
}
.verdict-pill {
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 800;
  padding: 10px 14px;
  border-radius: 10px;
  background: var(--surface-high);
  color: var(--on-surface);
}
.verdict-pill.bad {
  background: #ba1a1a;
  color: #fff;
}
.verdict-pill.ok {
  background: #16a34a;
  color: #fff;
}
.dec-body h3 {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 800;
}
.dec-main {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 600;
  color: var(--on-surface);
  line-height: 1.45;
}
.dec-sub {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}
.dec-acts {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.grid {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 14px;
}
@media (max-width: 1100px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
.card-clean {
  background: #fff;
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 16px;
}
.gauge-card h2,
.metrics-head h2,
.heat-head h2 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 800;
}
.gauge {
  position: relative;
  width: 160px;
  height: 160px;
  margin: 8px auto;
}
.gauge-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.gauge-num {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.gauge-num .num {
  font-size: 28px;
  font-weight: 800;
}
.gauge-num small {
  font-size: 14px;
  margin-left: 2px;
}
.bench {
  font-size: 11px;
  color: var(--on-surface-variant);
  margin-top: 4px;
  text-align: center;
}
.hint {
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}
.metrics-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.pill {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary);
  background: var(--surface-low);
  padding: 4px 10px;
  border-radius: 999px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
@media (max-width: 800px) {
  .metrics {
    grid-template-columns: 1fr;
  }
}
.metric {
  border: 1px solid var(--outline-variant);
  border-radius: 10px;
  padding: 12px;
  background: var(--surface-low);
  text-align: left;
  font-family: inherit;
}
.metric.clickable {
  cursor: pointer;
}
.metric.clickable:hover {
  border-color: var(--primary);
}
.m-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface-variant);
  display: block;
  margin-bottom: 6px;
}
.linkish {
  color: var(--primary);
  font-weight: 700;
}
.m-val {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.m-val strong {
  font-size: 26px;
  font-weight: 800;
  color: var(--on-surface);
}
.m-val em {
  font-style: normal;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.heat-card {
  grid-column: 1 / -1;
}
.heat-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.heat-head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  max-width: 560px;
}
.heat-legend {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.heat-legend i {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 3px;
  border: 1px solid;
  margin-right: 4px;
  vertical-align: -2px;
}
.heat-scroll {
  overflow-x: auto;
}
.hm-head,
.hm-row {
  display: grid;
  grid-template-columns: 48px repeat(12, minmax(36px, 1fr));
  gap: 4px;
  align-items: center;
  margin-bottom: 4px;
}
.hm-head {
  font-size: 11px;
  font-weight: 700;
  color: var(--on-surface-variant);
  text-align: center;
}
.hm-head .now,
.hm-cell.now {
  outline: 2px solid var(--primary);
  outline-offset: -1px;
}
.hm-label {
  font-size: 12px;
  font-weight: 800;
}
.hm-cell {
  height: 36px;
  border-radius: 6px;
  border: 1px solid;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: default;
}
.cell-tag {
  font-size: 9px;
  font-weight: 800;
  color: #855e00;
}
.cell-tag.alert {
  color: #ba1a1a;
}
.tip-line,
.empty-hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 40;
  padding: 16px;
}
.panel {
  background: #fff;
  border-radius: 14px;
  width: min(480px, 100%);
  padding: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}
.panel header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel h3 {
  margin: 0;
  font-size: 16px;
}
.panel .x {
  border: none;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
}
.panel-sub,
.suggest-body {
  font-size: 13px;
  color: var(--on-surface);
  line-height: 1.5;
}
.route-list,
.drill-list {
  list-style: none;
  padding: 0;
  margin: 12px 0;
  max-height: 320px;
  overflow: auto;
}
.drill-list {
  padding-left: 18px;
  list-style: disc;
  font-size: 13px;
  line-height: 1.6;
}
.route-list li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--outline-variant);
  font-size: 13px;
}
.excl {
  font-size: 12px;
  color: var(--on-surface-variant);
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.panel footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
.btn.sm {
  height: 32px;
  padding: 0 12px;
  font-size: 12px;
}
</style>
