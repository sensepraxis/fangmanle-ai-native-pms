<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * AI 智能排班控制台 —— 对照原型 room-board-3.html
 * 页头（周区间 + 自动调整开关）→ 峰值预警 → 甘特周排班
 * 数据：GET /api/housekeeping/staffing
 */
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import HousekeepingFlowNav from '../../components/HousekeepingFlowNav.vue'

type DayCol = { name: string; dateLabel: string; hot: boolean; isToday: boolean }
type Cell = {
  kind: 'morning' | 'mid' | 'night' | 'rest' | 'empty' | 'suggest'
  text: string
  note?: string
}
type StaffRow = {
  id: number | string
  name: string
  role: string
  initial: string
  score: number
  warn?: string
  temp?: boolean
  cells: Cell[]
}

const WEEK_CN = [t('周一'), t('周二'), t('周三'), t('周四'), t('周五'), t('周六'), t('周日')]

const SHIFT_TIME: Record<string, { kind: Cell['kind']; text: string }> = {
  morning: { kind: 'morning', text: '08:00 - 16:00' },
  afternoon: { kind: 'mid', text: '14:00 - 22:00' },
  night: { kind: 'night', text: '16:00 - 24:00' },
  hourly: { kind: 'mid', text: '10:00 - 14:00' },
  off: { kind: 'rest', text: t('休息') },
}

const FALLBACK_DAYS: DayCol[] = WEEK_CN.map((name, i) => ({
  name,
  dateLabel: `10/${23 + i}`,
  hot: i === 4 || i === 6,
  isToday: false,
}))

const FALLBACK_ROWS: StaffRow[] = [
  {
    id: 1,
    name: t('张阿姨'),
    role: t('保洁主管'),
    initial: t('张'),
    score: 92,
    cells: [
      { kind: 'morning', text: '08:00 - 16:00' },
      { kind: 'morning', text: '08:00 - 16:00' },
      { kind: 'rest', text: t('休息') },
      { kind: 'morning', text: '08:00 - 16:00' },
      { kind: 'mid', text: '14:00 - 22:00', note: t('AI 建议调班') },
      { kind: 'morning', text: '08:00 - 16:00' },
      { kind: 'morning', text: '08:00 - 16:00' },
    ],
  },
  {
    id: 2,
    name: t('李大姐'),
    role: t('资深保洁'),
    initial: t('李'),
    score: 65,
    warn: t('连续工作预警'),
    cells: [
      { kind: 'mid', text: '14:00 - 22:00' },
      { kind: 'mid', text: '14:00 - 22:00' },
      { kind: 'mid', text: '14:00 - 22:00' },
      { kind: 'mid', text: '14:00 - 22:00' },
      { kind: 'morning', text: '08:00 - 16:00' },
      { kind: 'mid', text: '14:00 - 22:00' },
      { kind: 'mid', text: '14:00 - 22:00', note: t('缺口增援') },
    ],
  },
]

const weekLabel = ref(t('本周'))
const days = ref<DayCol[]>([...FALLBACK_DAYS])
const rows = ref<StaffRow[]>([...FALLBACK_ROWS])
const alert = ref({
  title: t('峰值工作量预警'),
  desc: t(
    'AI 分析历史入住数据与当前预订情况显示，本周周五与周日将出现集中退房潮，现有排班运力缺口达 15%。',
  ),
  suggest: t('建议动作：为保洁团队增加 1 名临时员工 (外包或调休人员)。'),
  hotFri: t('周五'),
  hotSun: t('周日'),
})
const autoAdjust = ref(true)
const dept = ref<'hk' | 'fd'>('hk')

const tempRow = computed<StaffRow>(() => ({
  id: 'temp',
  name: t('临时员工'),
  role: t('AI 建议增补'),
  initial: '+',
  score: 0,
  temp: true,
  cells: days.value.map((d, i) => {
    if (d.hot && i === 4) return { kind: 'suggest', text: t('待安排 (早班)') }
    if (d.hot && i === 6) return { kind: 'suggest', text: t('待安排 (中班)') }
    return { kind: 'empty', text: '' }
  }),
}))

function scoreColor(s: number) {
  return s >= 85 ? '#1e8e3e' : '#d93025'
}

function mapCell(sh: any, dayIdx: number, hot: boolean): Cell {
  const raw = (sh?.shift || '').toLowerCase()
  const meta = SHIFT_TIME[raw] || (sh?.type === 'off' ? SHIFT_TIME.off : SHIFT_TIME.morning)
  const cell: Cell = { kind: meta.kind, text: meta.text }
  // 高峰日给中班加 AI 提示
  if (hot && meta.kind === 'mid' && dayIdx === 4) cell.note = t('AI 建议调班')
  if (hot && meta.kind === 'mid' && dayIdx === 6) cell.note = t('缺口增援')
  if (raw === 'off' || sh?.type === 'off') return { kind: 'rest', text: t('休息') }
  return cell
}

function buildScore(name: string, idx: number, cells: Cell[]) {
  const work = cells.filter((c) => c.kind !== 'rest' && c.kind !== 'empty').length
  let score = 100 - Math.max(0, work - 5) * 12 - (idx % 3) * 5
  score = Math.max(55, Math.min(98, score))
  const warn = work >= 6 && score < 75 ? t('连续工作预警') : undefined
  return { score, warn }
}

async function load() {
  try {
    const raw = await api.housekeepingStaffing(hotelStore.hotelId)
    weekLabel.value = raw.week_label || t('本周')

    const dayCols: DayCol[] = (raw.days || []).map((d: any, i: number) => {
      const iso = d.date || ''
      const md =
        iso.length >= 10
          ? `${Number(iso.slice(5, 7))}/${Number(iso.slice(8, 10))}`
          : FALLBACK_DAYS[i]?.dateLabel
      const wd = new Date(iso + 'T12:00:00').getDay() // 0 Sun
      const hot = wd === 5 || wd === 0 // Fri / Sun
      return {
        name: WEEK_CN[i] || (d.label || '').split(' ')[0],
        dateLabel: md,
        hot,
        isToday: !!d.is_today,
      }
    })
    days.value = dayCols.length === 7 ? dayCols : [...FALLBACK_DAYS]

    const hotIdx = days.value.map((d, i) => (d.hot ? i : -1)).filter((i) => i >= 0)
    const fri = days.value.find((d) => d.name === '周五')
    const sun = days.value.find((d) => d.name === '周日')
    if (raw.alert) {
      alert.value = {
        title: t('峰值工作量预警'),
        desc:
          raw.alert.desc ||
          `AI 分析历史入住数据与当前预订情况显示，本周${fri ? `周五 (${fri.dateLabel})` : t('周五')}与${sun ? `周日 (${sun.dateLabel})` : t('周日')}将出现集中退房潮，现有排班运力缺口达 15%。`,
        suggest: `建议动作：为保洁团队增加 ${raw.alert.suggest_hourly || 1} 名临时员工 (外包或调休人员)。`,
        hotFri: fri ? `周五 (${fri.dateLabel})` : t('周五'),
        hotSun: sun ? `周日 (${sun.dateLabel})` : t('周日'),
      }
    }

    const staff = raw.staff || []
    if (!staff.length) {
      rows.value = [...FALLBACK_ROWS]
      return
    }

    rows.value = staff.slice(0, 6).map((s: any, idx: number) => {
      const cells = (s.shifts || [])
        .slice(0, 7)
        .map((sh: any, di: number) => mapCell(sh, di, !!days.value[di]?.hot))
      while (cells.length < 7) cells.push({ kind: 'rest', text: t('休息') })
      const { score, warn } = buildScore(s.name || t('员工'), idx, cells)
      // 高峰日强化 AI 调班提示（首行周五）
      if (idx === 0 && hotIdx.includes(4) && cells[4]?.kind !== 'rest') {
        cells[4] = {
          ...cells[4],
          kind: 'mid',
          text: cells[4].text.includes(':') ? cells[4].text : '14:00 - 22:00',
          note: t('AI 建议调班'),
        }
      }
      return {
        id: s.id || idx,
        name: s.name || `员工${idx + 1}`,
        role: s.type === 'hourly' ? t('小时工保洁') : idx === 0 ? t('保洁主管') : t('资深保洁'),
        initial: s.initial || (s.name || t('员'))[0],
        score,
        warn,
        cells,
      }
    })
  } catch {
    weekLabel.value = t('本周')
    days.value = [...FALLBACK_DAYS]
    rows.value = [...FALLBACK_ROWS]
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page rb3">
    <!-- 页头 -->
    <div class="page-top">
      <div>
        <h1>{{ t('AI 智能排班控制台') }}</h1>
        <p class="sub">{{ weekLabel }}</p>
      </div>
      <div class="top-actions">
        <div class="auto-box">
          <span>{{ t('自动调整突发退房排班') }}</span>
          <label class="switch">
            <input v-model="autoAdjust" type="checkbox" />
            <span class="slider"></span>
          </label>
        </div>
        <div class="week-nav">
          <button type="button" class="nav-ico" :aria-label="t('上一周')">
            <span class="material-symbols-outlined">chevron_left</span>
          </button>
          <span class="week-lbl">{{ t('本周') }}</span>
          <button type="button" class="nav-ico" :aria-label="t('下一周')">
            <span class="material-symbols-outlined">chevron_right</span>
          </button>
        </div>
        <HousekeepingFlowNav mode="labor" />
      </div>
    </div>

    <!-- AI 峰值预警 -->
    <div class="ai-panel">
      <div class="glow"></div>
      <div class="ai-ico">
        <span class="material-symbols-outlined">auto_awesome</span>
      </div>
      <div class="ai-body">
        <h3>
          {{ alert.title }}
          <span class="risk">{{ t('高风险') }}</span>
        </h3>
        <p>
          {{ t('AI 分析历史入住数据与当前预订情况显示，本周') }} <strong>{{ alert.hotFri }}</strong>
          {{ t('与') }} <strong>{{ alert.hotSun }}</strong>
          {{ t('将出现集中退房潮，现有排班运力缺口达 15%。') }}
        </p>
        <div class="suggest">
          <span>{{ alert.suggest }}</span>
          <button type="button" class="btn-gen">{{ t('一键生成临时排班') }}</button>
        </div>
      </div>
    </div>

    <!-- 甘特 -->
    <div class="gantt">
      <div class="toolbar">
        <div class="depts">
          <button type="button" class="dept" :class="{ on: dept === 'hk' }" @click="dept = 'hk'">
            {{ t('客房部') }}
          </button>
          <button type="button" class="dept" :class="{ on: dept === 'fd' }" @click="dept = 'fd'">
            {{ t('前厅部') }}
          </button>
        </div>
        <div class="legend">
          <span><i class="lg-m"></i>{{ t('早班') }}</span>
          <span><i class="lg-a"></i>{{ t('中班') }}</span>
          <span><i class="lg-n"></i>{{ t('晚班') }}</span>
          <span><i class="lg-r"></i>{{ t('休息') }}</span>
        </div>
      </div>

      <div class="gantt-scroll">
        <div class="gantt-inner">
          <div class="g-head">
            <div class="col-info">{{ t('员工信息') }}</div>
            <div v-for="(d, i) in days" :key="i" class="col-day" :class="{ hot: d.hot }">
              <div class="day-name" :class="{ error: d.hot }">{{ d.name }}</div>
              <div class="day-date">{{ d.dateLabel }}</div>
            </div>
          </div>

          <div class="g-body">
            <div v-for="r in rows" :key="r.id" class="g-row">
              <div class="col-info staff">
                <div class="who">
                  <div class="avatar">{{ r.initial }}</div>
                  <div>
                    <div class="name">{{ r.name }}</div>
                    <div class="role">{{ r.role }}</div>
                  </div>
                </div>
                <div class="score-box">
                  <div class="score-top">
                    <span>{{ t('工作量平衡分') }}</span>
                    <span class="num" :style="{ color: scoreColor(r.score) }"
                      >{{ r.score }}/100</span
                    >
                  </div>
                  <div class="bar">
                    <div
                      class="fill"
                      :style="{ width: r.score + '%', background: scoreColor(r.score) }"
                    ></div>
                  </div>
                  <div v-if="r.warn" class="warn-txt">{{ r.warn }}</div>
                </div>
              </div>
              <div
                v-for="(c, ci) in r.cells"
                :key="ci"
                class="col-cell"
                :class="{ hot: days[ci]?.hot }"
              >
                <div class="chip" :class="[c.kind, { noted: !!c.note }]">
                  <span>{{ c.text }}</span>
                  <span v-if="c.note" class="note">({{ c.note }})</span>
                </div>
              </div>
            </div>

            <!-- 临时员工行 -->
            <div class="g-row temp">
              <div class="col-info staff">
                <div class="who">
                  <div class="avatar dash">+</div>
                  <div>
                    <div class="name tertiary">{{ t('临时员工') }}</div>
                    <div class="role">{{ t('AI 建议增补') }}</div>
                  </div>
                </div>
              </div>
              <div
                v-for="(c, ci) in tempRow.cells"
                :key="'t' + ci"
                class="col-cell"
                :class="{ hot: days[ci]?.hot, 'temp-slot': c.kind === 'suggest' }"
              >
                <div v-if="c.kind === 'suggest'" class="chip suggest">{{ c.text }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rb3 {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-top {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.page-top h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  color: var(--on-surface, #191c1d);
  line-height: 32px;
}
.sub {
  margin: 4px 0 0;
  font-size: 16px;
  color: var(--on-surface-variant, #414754);
}
.top-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  justify-content: flex-end;
}
.auto-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  background: var(--surface, #f8fafb);
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  font-size: 14px;
  color: var(--on-surface);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.switch {
  position: relative;
  width: 40px;
  height: 20px;
  display: inline-block;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  inset: 0;
  background: var(--surface-container, #eceeef);
  border-radius: 999px;
  cursor: pointer;
  transition: 0.2s;
}
.slider::before {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  left: 2px;
  top: 2px;
  background: #fff;
  border-radius: 50%;
  border: 2px solid var(--surface-container);
  transition: 0.2s;
  box-sizing: border-box;
}
.switch input:checked + .slider {
  background: #1a73e8;
}
.switch input:checked + .slider::before {
  transform: translateX(20px);
  border-color: #1a73e8;
}
.week-nav {
  display: flex;
  align-items: center;
  background: var(--surface, #f8fafb);
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.nav-ico {
  border: none;
  background: transparent;
  padding: 8px;
  color: var(--on-surface-variant);
  cursor: pointer;
  display: flex;
}
.nav-ico:hover {
  background: var(--surface-container);
}
.nav-ico .material-symbols-outlined {
  font-size: 20px;
}
.week-lbl {
  padding: 0 16px;
  font-size: 14px;
  border-left: 1px solid var(--outline-variant);
  border-right: 1px solid var(--outline-variant);
  color: var(--on-surface);
  line-height: 36px;
}

/* AI panel */
.ai-panel {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: var(--surface, #f8fafb);
  border: 1px solid var(--outline-variant);
  border-left: 4px solid var(--tertiary, #8c33b3);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}
.glow {
  position: absolute;
  left: -40px;
  top: -40px;
  width: 128px;
  height: 128px;
  background: var(--tertiary, #8c33b3);
  border-radius: 50%;
  opacity: 0.05;
  filter: blur(24px);
  pointer-events: none;
}
.ai-ico {
  flex-shrink: 0;
  margin-top: 4px;
  padding: 8px;
  border-radius: 999px;
  background: rgba(168, 79, 206, 0.1);
  color: var(--tertiary, #8c33b3);
  display: flex;
}
.ai-ico .material-symbols-outlined {
  font-size: 22px;
}
.ai-body {
  flex: 1;
  min-width: 0;
  position: relative;
  z-index: 1;
}
.ai-body h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: var(--on-surface);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.risk {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--error-container, #ffdad6);
  color: var(--on-error-container, #93000a);
  border: 1px solid rgba(186, 26, 26, 0.2);
}
.ai-body p {
  margin: 8px 0 0;
  font-size: 16px;
  line-height: 24px;
  color: var(--on-surface-variant);
  max-width: 48rem;
}
.ai-body strong {
  color: var(--on-surface);
  font-weight: 700;
}
.suggest {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 12px;
  background: var(--surface-bright, #f8fafb);
  border: 1px solid rgba(193, 198, 214, 0.5);
  border-radius: 8px;
  font-size: 16px;
  color: var(--on-surface);
}
.btn-gen {
  margin-left: auto;
  border: none;
  padding: 6px 16px;
  border-radius: 6px;
  background: #1a73e8;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.btn-gen:hover {
  opacity: 0.9;
}

/* Gantt */
.gantt {
  background: var(--surface, #f8fafb);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.toolbar {
  padding: 16px;
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface-bright, #f8fafb);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.depts {
  display: flex;
  gap: 8px;
}
.dept {
  padding: 6px 12px;
  border: 1px solid var(--outline-variant);
  background: var(--surface, #fff);
  border-radius: 6px;
  font-size: 14px;
  color: var(--on-surface);
  cursor: pointer;
}
.dept.on,
.dept:hover {
  background: var(--surface-container, #eceeef);
}
.legend {
  display: flex;
  align-items: center;
  gap: 4px 16px;
  flex-wrap: wrap;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.legend i {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  border: 1px solid;
  display: inline-block;
}
.lg-m {
  background: #e8f0fe;
  border-color: #1a73e8;
}
.lg-a {
  background: #fce8e6;
  border-color: #d93025;
}
.lg-n {
  background: #e6f4ea;
  border-color: #1e8e3e;
}
.lg-r {
  background: var(--surface-variant, #e1e3e4);
  border-color: var(--outline-variant);
}

.gantt-scroll {
  overflow-x: auto;
}
.gantt-inner {
  min-width: 900px;
}

.g-head,
.g-row {
  display: grid;
  grid-template-columns: 240px repeat(7, 1fr);
}
.g-head {
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest, #fff);
}
.col-info {
  padding: 12px;
  border-right: 1px solid var(--outline-variant);
  font-size: 14px;
  color: var(--on-surface-variant);
}
.col-day {
  padding: 12px;
  text-align: center;
  border-right: 1px solid var(--outline-variant);
}
.col-day:last-child {
  border-right: none;
}
.col-day.hot {
  background: rgba(255, 218, 214, 0.35);
}
.day-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--on-surface);
}
.day-name.error {
  color: var(--error, #ba1a1a);
}
.day-date {
  font-family: 'Roboto Mono', monospace;
  font-size: 13px;
  color: var(--on-surface-variant);
  margin-top: 2px;
}

.g-body {
  display: flex;
  flex-direction: column;
}
.g-row {
  border-bottom: 1px solid var(--outline-variant);
  transition: background 0.15s;
}
.g-row:hover {
  background: var(--surface-bright, #f8fafb);
}
.g-row.temp {
  opacity: 0.9;
  background: var(--surface-container-lowest, #fff);
  border-left: 2px solid var(--tertiary, #8c33b3);
}

.col-info.staff {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}
.who {
  display: flex;
  align-items: center;
  gap: 12px;
}
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--surface-container-high, #e6e8e9);
  border: 1px solid var(--outline-variant);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: var(--on-surface);
  flex-shrink: 0;
}
.avatar.dash {
  background: var(--surface, #fff);
  border-style: dashed;
  border-color: var(--tertiary, #8c33b3);
  color: var(--tertiary, #8c33b3);
}
.name {
  font-size: 14px;
  font-weight: 700;
  color: var(--on-surface);
}
.name.tertiary {
  color: var(--tertiary, #8c33b3);
}
.role {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-top: 2px;
}
.score-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 4px;
}
.score-top {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.score-top .num {
  font-family: 'Roboto Mono', monospace;
  font-weight: 600;
}
.bar {
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: var(--surface-variant, #e1e3e4);
  overflow: hidden;
}
.fill {
  height: 100%;
  border-radius: 999px;
}
.warn-txt {
  font-size: 10px;
  color: #d93025;
}

.col-cell {
  padding: 8px;
  border-right: 1px solid var(--outline-variant);
  min-height: 72px;
  position: relative;
}
.col-cell:last-child {
  border-right: none;
}
.col-cell.hot {
  background: rgba(255, 218, 214, 0.12);
}
.col-cell.temp-slot {
  background: rgba(140, 51, 179, 0.05);
}

.chip {
  height: 100%;
  min-height: 56px;
  width: 100%;
  border-radius: 6px;
  border: 1px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  box-sizing: border-box;
  padding: 4px;
  text-align: center;
  transition: box-shadow 0.15s;
}
.chip:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}
.chip.morning {
  background: #e8f0fe;
  border-color: rgba(26, 115, 232, 0.3);
  color: #1a73e8;
}
.chip.mid {
  background: #fce8e6;
  border-color: rgba(217, 48, 37, 0.3);
  color: #d93025;
}
.chip.night {
  background: #e6f4ea;
  border-color: rgba(30, 142, 62, 0.3);
  color: #1e8e3e;
}
.chip.rest {
  background: var(--surface-variant, #e1e3e4);
  border-color: var(--outline-variant);
  color: var(--on-surface-variant);
  cursor: default;
}
.chip.noted {
  box-shadow: inset 0 0 0 1px #d93025;
}
.chip .note {
  font-size: 10px;
  opacity: 0.85;
  font-weight: 500;
  margin-top: 2px;
}
.chip.suggest {
  border: 2px dashed rgba(140, 51, 179, 0.4);
  background: transparent;
  color: var(--tertiary, #8c33b3);
  min-height: 56px;
}
.chip.suggest:hover {
  background: rgba(140, 51, 179, 0.08);
}
.chip.empty {
  border: none;
  background: transparent;
  cursor: default;
  min-height: 0;
}

@media (max-width: 900px) {
  .suggest {
    flex-direction: column;
    align-items: stretch;
  }
  .btn-gen {
    margin-left: 0;
    width: 100%;
  }
}
</style>
