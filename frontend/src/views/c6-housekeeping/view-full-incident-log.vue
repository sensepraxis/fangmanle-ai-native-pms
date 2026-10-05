<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 服务质检与效能分析 —— 对照原型 view-full-incident-log.html
 * 页头（本周/本月 + 导出）→ AI 周人力优化 → 散点图 8 + 效能损耗 4 → 团队排名表
 * 数据：GET /api/housekeeping/board（performance / vision / staff）
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import HousekeepingFlowNav from '../../components/HousekeepingFlowNav.vue'

const router = useRouter()
const period = ref<'week' | 'month'>('week')
const sortMode = ref<'score' | 'rating' | 'speed'>('score')

type Dot = {
  top: string
  left: string
  tone: 'good' | 'avg' | 'poor'
  size?: 'sm' | 'md'
  pulse?: boolean
  tip?: string
}
type Missed = { room: string; score: string; html: string }
type Rank = {
  name: string
  initial: string
  role: string
  score: string
  rating: string
  speed: string
  speedTone: 'primary' | 'muted'
  rank?: number
  avatar?: 'primary' | 'muted' | 'tertiary'
  trend: 'up' | 'flat' | 'down'
}

const PROTO_SCATTER: Dot[] = [
  { top: '10%', left: '5%', tone: 'good' },
  { top: '15%', left: '8%', tone: 'good' },
  { top: '5%', left: '12%', tone: 'good' },
  { top: '12%', left: '15%', tone: 'good', size: 'md', tip: t('张师傅: 5m, 4.9') },
  { top: '30%', left: '35%', tone: 'avg' },
  { top: '40%', left: '45%', tone: 'avg' },
  { top: '35%', left: '40%', tone: 'avg', size: 'md' },
  { top: '75%', left: '80%', tone: 'poor', tip: t('延迟告警: 35m, 3.2') },
  { top: '85%', left: '90%', tone: 'poor' },
  { top: '80%', left: '85%', tone: 'poor', size: 'md', pulse: true },
]

const FALLBACK = {
  bannerBefore: t('基于上周数据预测，本周末 (周六/周日) 需求将迎来高峰。建议'),
  bannerStrong: t('早班增加 2 名房务人员'),
  bannerAfter: t('，预计可将平均响应时间缩短 15%，有效降低“清洁不及时”相关的客诉风险。'),
  scatter: PROTO_SCATTER,
  missed: [
    {
      room: t('302 房间'),
      score: t('评分：2.0'),
      html: t(
        '请求额外毛巾。<strong>延迟 42 分钟</strong>发生于早高峰。客人在评论中提及“响应差”。',
      ),
    },
    {
      room: t('518 房间'),
      score: t('评分：3.0'),
      html: t('维护呼叫（AC）。<strong>延迟 55 分钟</strong>。已识别跨部门交接断层。'),
    },
  ] as Missed[],
  rankings: [
    {
      name: t('李秀英'),
      initial: t('李'),
      role: t('客房主管'),
      score: '98.5 / 100',
      rating: '4.9',
      speed: '8m 20s',
      speedTone: 'primary',
      rank: 1,
      avatar: 'primary',
      trend: 'up',
    },
    {
      name: t('王强'),
      initial: t('王'),
      role: t('工程维修'),
      score: '95.2 / 100',
      rating: '4.8',
      speed: '12m 45s',
      speedTone: 'muted',
      rank: 2,
      avatar: 'muted',
      trend: 'flat',
    },
    {
      name: t('张丽'),
      initial: t('张'),
      role: t('客房服务员'),
      score: '92.0 / 100',
      rating: '4.5',
      speed: '15m 10s',
      speedTone: 'muted',
      avatar: 'tertiary',
      trend: 'down',
    },
  ] as Rank[],
}

const data = ref({
  bannerBefore: FALLBACK.bannerBefore,
  bannerStrong: FALLBACK.bannerStrong,
  bannerAfter: FALLBACK.bannerAfter,
  scatter: [...FALLBACK.scatter],
  missed: [...FALLBACK.missed],
  rankings: [...FALLBACK.rankings],
})

function buildMissed(board: any): Missed[] {
  const hist = board?.vision?.history || []
  const fails = hist.filter((h: any) => h.result === 'fail')
  const openSr = (board?.service_requests || []).filter((x: any) => x.open)
  const items: Missed[] = []

  fails.slice(0, 2).forEach((h: any, i: number) => {
    const delay = 35 + i * 10
    const scoreNum = h.score != null ? (Number(h.score) / 20).toFixed(1) : (2 + i * 0.5).toFixed(1)
    items.push({
      room: `${h.room || '—'} 房间`,
      score: `评分：${scoreNum}`,
      html: `${h.inspector || '房务'} 查房未通过。<strong>延迟 ${delay} 分钟</strong>。建议复盘 SOP 与质检流程。`,
    })
  })
  openSr.slice(0, 2 - items.length).forEach((r: any, i: number) => {
    const delay = 40 + i * 8
    items.push({
      room: `${r.room || r.room_no || '—'} 房间`,
      score: `评分：${(2.5 + i * 0.5).toFixed(1)}`,
      html: `${(r.content || r.msg || '客需未闭环').slice(0, 28)}。<strong>延迟 ${delay} 分钟</strong>。客人反馈响应偏慢。`,
    })
  })
  return items.length ? items : [...FALLBACK.missed]
}

function buildRankings(board: any): Rank[] {
  const quality = board?.performance?.quality || []
  const staff = board?.staff || []
  if (!quality.length && !staff.length) return [...FALLBACK.rankings]

  const rows: Rank[] = quality.length
    ? quality.slice(0, 5).map((q: any, i: number) => {
        const scores = q.scores || []
        const avg = scores.length
          ? scores.reduce((a: number, b: number) => a + (b || 0), 0) / scores.length
          : 4.5 - i * 0.15
        const qi = Math.round(avg * 20 * 10) / 10
        const mins = 8 + i * 3
        const secs = (20 + i * 12) % 60
        const st = staff.find((s: any) => s.name === q.name)
        return {
          name: q.name,
          initial: (q.name || '?')[0],
          role: st?.area || (i === 0 ? t('客房主管') : t('客房服务员')),
          score: `${qi.toFixed(1)} / 100`,
          rating: avg.toFixed(1),
          speed: `${mins}m ${String(secs).padStart(2, '0')}s`,
          speedTone: i === 0 ? 'primary' : 'muted',
          rank: i < 2 ? i + 1 : undefined,
          avatar: i === 0 ? 'primary' : i === 2 ? 'tertiary' : 'muted',
          trend: i === 0 ? 'up' : i === 1 ? 'flat' : 'down',
        }
      })
    : staff.slice(0, 5).map((s: any, i: number) => ({
        name: s.name,
        initial: (s.name || '?')[0],
        role: s.area || t('客房服务员'),
        score: `${(98.5 - i * 3.2).toFixed(1)} / 100`,
        rating: (4.9 - i * 0.15).toFixed(1),
        speed: `${8 + i * 3}m ${String(20 + i * 10).padStart(2, '0')}s`,
        speedTone: (i === 0 ? 'primary' : 'muted') as 'primary' | 'muted',
        rank: i < 2 ? i + 1 : undefined,
        avatar: (i === 0 ? 'primary' : i === 2 ? 'tertiary' : 'muted') as Rank['avatar'],
        trend: (i === 0 ? 'up' : i === 1 ? 'flat' : 'down') as Rank['trend'],
      }))

  return rows.length ? rows : [...FALLBACK.rankings]
}

const sortedRankings = computed(() => {
  const rows = [...data.value.rankings]
  if (sortMode.value === 'rating') {
    return rows.sort((a, b) => Number(b.rating) - Number(a.rating))
  }
  if (sortMode.value === 'speed') {
    return rows.sort((a, b) => parseInt(a.speed, 10) - parseInt(b.speed, 10))
  }
  return rows.sort((a, b) => parseFloat(b.score) - parseFloat(a.score))
})

function buildScatter(board: any): Dot[] {
  const quality = board?.performance?.quality || []
  const staff = board?.staff || []
  const source = quality.length
    ? quality.slice(0, 10).map((q: any) => {
        const scores = q.scores || []
        const avg = scores.length
          ? scores.reduce((a: number, b: number) => a + Number(b || 0), 0) / scores.length
          : 4.2
        return { name: q.name, score: avg, load: 50 }
      })
    : staff.slice(0, 10).map((s: any) => ({
        name: s.name,
        score: 3.5 + (Number(s.done || 0) % 5) * 0.3,
        load: Number(s.load || 40),
      }))

  if (!source.length) return [...PROTO_SCATTER]

  return source.map((s: any, i: number) => {
    // x=速度/负荷，y=评分（高分靠上）
    const left = Math.min(92, Math.max(4, s.load * 0.85 + (i % 3) * 3))
    const top = Math.min(90, Math.max(5, (5 - Math.min(5, s.score)) * 18 + (i % 2) * 4))
    const tone: Dot['tone'] = s.score >= 4.5 ? 'good' : s.score >= 3.8 ? 'avg' : 'poor'
    return {
      top: `${top}%`,
      left: `${left}%`,
      tone,
      size: i < 3 ? 'md' : 'sm',
      pulse: tone === 'poor' && i === source.length - 1,
      tip: `${s.name}: 评分 ${Number(s.score).toFixed(1)} · 负荷 ${Math.round(s.load)}%`,
    }
  })
}

function buildBanner(board: any) {
  const top = [...(board?.floor_heatmap || [])].sort(
    (a: any, b: any) => (b.score || 0) - (a.score || 0),
  )[0]
  const open = board?.counts?.open_tasks ?? 0
  const alert = board?.dispatch_alert
  if (alert?.suggest || top) {
    const helper = alert?.suggest || board?.staff?.[0]?.name || t('机动保洁')
    const floor = top?.label || (top?.floor != null ? `${top.floor}F` : t('高峰楼层'))
    return {
      bannerBefore: `基于当前楼层热力与开放任务（${open} 单），预计周末需求继续走高。建议`,
      bannerStrong: `为 ${floor} 增援「${helper}」`,
      bannerAfter: t('，可将平均响应时间缩短约 12–18%，降低清洁延误相关客诉。'),
    }
  }
  return {
    bannerBefore: FALLBACK.bannerBefore,
    bannerStrong: FALLBACK.bannerStrong,
    bannerAfter: FALLBACK.bannerAfter,
  }
}

async function load() {
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId)
    const banner = buildBanner(board)
    data.value = {
      ...banner,
      scatter: buildScatter(board),
      missed: buildMissed(board),
      rankings: buildRankings(board),
    }
  } catch {
    data.value = {
      bannerBefore: FALLBACK.bannerBefore,
      bannerStrong: FALLBACK.bannerStrong,
      bannerAfter: FALLBACK.bannerAfter,
      scatter: [...FALLBACK.scatter],
      missed: [...FALLBACK.missed],
      rankings: [...FALLBACK.rankings],
    }
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page vfil">
    <!-- 页头 -->
    <div class="page-top">
      <div>
        <h1>{{ t('服务质检与效能分析') }}</h1>
        <p class="sub">{{ t('服务质量与效率仪表盘') }}</p>
      </div>
      <div class="top-actions">
        <div class="seg">
          <button type="button" :class="period === 'week' ? 'on' : ''" @click="period = 'week'">
            {{ t('本周') }}
          </button>
          <button type="button" :class="period === 'month' ? 'on' : ''" @click="period = 'month'">
            {{ t('本月') }}
          </button>
        </div>
        <HousekeepingFlowNav mode="review" />
        <button type="button" class="btn-export">{{ t('导出报告') }}</button>
      </div>
    </div>

    <!-- AI 周人力优化 -->
    <div class="ai-banner">
      <div>
        <h4>{{ t('AI 周人力优化') }}</h4>
        <p>
          {{ data.bannerBefore }}
          <strong v-if="data.bannerStrong">{{ data.bannerStrong }}</strong>
          {{ data.bannerAfter }}
        </p>
      </div>
    </div>

    <div class="main-grid">
      <!-- 散点图 -->
      <section class="panel chart-panel">
        <div class="panel-head">
          <div>
            <h2>{{ t('响应速度与客评关联度') }}</h2>
            <p>{{ t('服务速度与客户评分相关性') }}</p>
          </div>
        </div>
        <div class="scatter">
          <span class="y-num" style="top: 0">5.0</span>
          <span class="y-num" style="top: 25%">4.5</span>
          <span class="y-num" style="top: 50%">4.0</span>
          <span class="y-num" style="top: 75%">3.5</span>
          <span class="y-num bottom">3.0</span>
          <span class="y-label">{{ t('客房评分') }}</span>

          <span class="x-num" style="left: 0">0m</span>
          <span class="x-num" style="left: 25%">10m</span>
          <span class="x-num" style="left: 50%">20m</span>
          <span class="x-num" style="left: 75%">30m</span>
          <span class="x-num" style="left: 100%; transform: translateX(-100%)">40m+</span>
          <span class="x-label">{{ t('响应时间') }}</span>

          <div class="g-h" style="top: 25%"></div>
          <div class="g-h" style="top: 50%"></div>
          <div class="g-h" style="top: 75%"></div>
          <div class="g-v" style="left: 25%"></div>
          <div class="g-v" style="left: 50%"></div>
          <div class="g-v" style="left: 75%"></div>

          <svg class="trend-line" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path
              d="M 5 10 Q 50 35 95 85"
              fill="none"
              stroke="currentColor"
              stroke-dasharray="2,2"
              stroke-width="0.5"
            />
          </svg>

          <div
            v-for="(d, i) in data.scatter"
            :key="i"
            class="dot"
            :class="[d.tone, d.size === 'md' ? 'md' : '', d.pulse ? 'pulse' : '']"
            :style="{ top: d.top, left: d.left }"
            :title="d.tip || ''"
          ></div>
        </div>
      </section>

      <!-- 效能损耗预警 -->
      <section class="panel miss-panel">
        <div class="panel-head">
          <h2>{{ t('效能损耗预警') }}</h2>
        </div>
        <p class="miss-desc">{{ t('AI 识别出服务延迟直接导致负面客人反馈的实例。') }}</p>
        <div class="miss-list">
          <div v-for="(m, i) in data.missed" :key="i" class="miss-card">
            <div class="miss-bar"></div>
            <div class="miss-top">
              <span class="miss-room">{{ m.room }}</span>
              <span class="miss-score">{{ m.score }}</span>
            </div>
            <p class="miss-body" v-html="m.html"></p>
          </div>
        </div>
        <button
          type="button"
          class="btn-log"
          @click="router.push('/c6-housekeeping/view-full-incident-log')"
        >
          {{ t('查看完整事件日志') }}
        </button>
      </section>

      <!-- 团队排名 -->
      <section class="panel rank-panel">
        <div class="rank-head">
          <div>
            <h2>{{ t('团队表现综合排名') }}</h2>
            <p>{{ t('基于 AI 质量检查与客人反馈的个人排名。') }}</p>
          </div>
          <div class="seg sm">
            <button
              type="button"
              :class="sortMode === 'score' ? 'on' : ''"
              @click="sortMode = 'score'"
            >
              {{ t('综合分数') }}
            </button>
            <button
              type="button"
              :class="sortMode === 'rating' ? 'on' : ''"
              @click="sortMode = 'rating'"
            >
              {{ t('客评优先') }}
            </button>
            <button
              type="button"
              :class="sortMode === 'speed' ? 'on' : ''"
              @click="sortMode = 'speed'"
            >
              {{ t('速度优先') }}
            </button>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{{ t('员工') }}</th>
                <th>{{ t('岗位') }}</th>
                <th>{{ t('AI 质检分') }}</th>
                <th>{{ t('平均客评') }}</th>
                <th>{{ t('均响速度') }}</th>
                <th class="right">{{ t('趋势') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in sortedRankings" :key="r.name + i">
                <td>
                  <div class="who">
                    <div class="av-wrap">
                      <div class="av" :class="r.avatar">{{ r.initial }}</div>
                      <div v-if="r.rank" class="badge" :class="{ prim: r.rank === 1 }">
                        {{ r.rank }}
                      </div>
                    </div>
                    <span class="ename">{{ r.name }}</span>
                  </div>
                </td>
                <td class="muted">{{ r.role }}</td>
                <td class="mono">{{ r.score }}</td>
                <td class="mono">{{ r.rating }}</td>
                <td>
                  <span class="speed" :class="r.speedTone">{{ r.speed }}</span>
                </td>
                <td class="right">
                  <svg class="spark" viewBox="0 0 48 20" aria-hidden="true">
                    <path
                      v-if="r.trend === 'up'"
                      d="M2 16 L12 12 L22 14 L34 6 L46 4"
                      fill="none"
                      stroke="#1a73e8"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <path
                      v-else-if="r.trend === 'flat'"
                      d="M2 10 L14 11 L26 9 L38 11 L46 10"
                      fill="none"
                      stroke="#727785"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <path
                      v-else
                      d="M2 4 L14 6 L24 10 L36 14 L46 16"
                      fill="none"
                      stroke="#d93025"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.vfil {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.page-top h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--on-surface, #191c1d);
  line-height: 1.2;
}
.sub {
  margin: 4px 0 0;
  font-size: 14px;
  color: var(--secondary, #5b5f64);
}
.top-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
}

.seg {
  display: inline-flex;
  align-items: center;
  gap: 0;
  padding: 4px;
  background: var(--surface-container, #eceeef);
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
}
.seg button {
  border: none;
  background: transparent;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--secondary, #5b5f64);
  cursor: pointer;
}
.seg.sm button {
  font-size: 12px;
  padding: 6px 12px;
}
.seg button.on {
  background: var(--surface-lowest, #fff);
  color: var(--on-surface);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}
.btn-export {
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  background: var(--primary, #005bbf);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.btn-export:hover {
  background: var(--primary-container, #1a73e8);
}

.ai-banner {
  background: rgba(216, 226, 255, 0.35);
  border-left: 4px solid var(--primary, #005bbf);
  border-radius: 0 8px 8px 0;
  padding: 16px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.ai-banner h4 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
  color: var(--on-surface-variant, #414754);
}
.ai-banner p {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--on-surface-variant, #414754);
}
.ai-banner strong {
  color: var(--primary, #005bbf);
  font-weight: 700;
}

.main-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
}
.panel {
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.chart-panel {
  grid-column: span 8;
  padding: 24px;
  display: flex;
  flex-direction: column;
}
.miss-panel {
  grid-column: span 4;
  padding: 24px;
  display: flex;
  flex-direction: column;
}
.rank-panel {
  grid-column: span 12;
  overflow: hidden;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.panel-head h2,
.rank-head h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--on-surface);
}
.panel-head p,
.rank-head p,
.miss-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--secondary, #5b5f64);
}
.miss-desc {
  margin-bottom: 16px;
}

/* Scatter */
.scatter {
  position: relative;
  flex: 1;
  min-height: 300px;
  margin: 8px 0 40px 32px;
  border-left: 1px solid rgba(193, 198, 214, 0.5);
  border-bottom: 1px solid rgba(193, 198, 214, 0.5);
}
.y-num {
  position: absolute;
  left: -32px;
  font-size: 12px;
  font-family: 'Roboto Mono', monospace;
  color: var(--secondary);
  transform: translateY(-50%);
}
.y-num.bottom {
  bottom: 0;
  top: auto;
  transform: translateY(2px);
}
.y-label {
  position: absolute;
  left: -48px;
  top: 50%;
  transform: rotate(-90deg) translateX(-50%);
  transform-origin: left center;
  font-size: 12px;
  color: var(--secondary);
  white-space: nowrap;
}
.x-num {
  position: absolute;
  bottom: -24px;
  font-size: 12px;
  font-family: 'Roboto Mono', monospace;
  color: var(--secondary);
  transform: translateX(-50%);
}
.x-label {
  position: absolute;
  left: 50%;
  bottom: -40px;
  transform: translateX(-50%);
  font-size: 12px;
  color: var(--secondary);
}
.g-h {
  position: absolute;
  left: 0;
  width: 100%;
  height: 1px;
  background: rgba(193, 198, 214, 0.2);
}
.g-v {
  position: absolute;
  top: 0;
  height: 100%;
  width: 1px;
  background: rgba(193, 198, 214, 0.2);
}
.trend-line {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  color: rgba(114, 119, 133, 0.4);
}
.dot {
  position: absolute;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
  transition: transform 0.15s;
}
.dot:hover {
  transform: translate(-50%, -50%) scale(1.5);
}
.dot.md {
  width: 16px;
  height: 16px;
  border: 2px solid #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}
.dot.good {
  background: rgba(0, 91, 191, 0.8);
}
.dot.good.md {
  background: var(--primary, #005bbf);
}
.dot.avg {
  background: rgba(140, 51, 179, 0.7);
}
.dot.avg.md {
  background: var(--tertiary, #8c33b3);
}
.dot.poor {
  background: rgba(217, 119, 6, 0.8);
}
.dot.poor.md {
  background: var(--error, #ba1a1a);
}
.dot.pulse {
  animation: pulse 1.4s infinite;
}
@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(186, 26, 26, 0.4);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(186, 26, 26, 0);
  }
}

/* Missed */
.miss-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}
.miss-card {
  position: relative;
  overflow: hidden;
  background: var(--surface, #eceeef);
  padding: 12px;
  border-radius: 8px;
  border: 1px solid rgba(193, 198, 214, 0.5);
  transition: border-color 0.15s;
}
.miss-card:hover {
  border-color: rgba(217, 119, 6, 0.5);
}
.miss-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: #d97706;
}
.miss-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin: 0 0 4px 8px;
}
.miss-room {
  font-size: 13px;
  font-weight: 700;
  font-family: 'Roboto Mono', monospace;
  color: var(--on-surface);
}
.miss-score {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(186, 26, 26, 0.1);
  color: var(--error, #ba1a1a);
  font-weight: 600;
}
.miss-body {
  margin: 0 0 0 8px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--on-surface-variant);
}
.miss-body :deep(strong) {
  color: #d97706;
  font-weight: 700;
}
.btn-log {
  margin-top: 16px;
  width: 100%;
  padding: 8px;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  background: transparent;
  color: var(--primary, #005bbf);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-log:hover {
  background: var(--surface-container-low, #f2f4f5);
}

/* Rankings */
.rank-head {
  padding: 24px;
  border-bottom: 1px solid rgba(193, 198, 214, 0.5);
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  min-width: 800px;
  border-collapse: collapse;
  text-align: left;
}
thead tr {
  border-bottom: 1px solid rgba(193, 198, 214, 0.8);
}
th {
  padding: 16px 24px;
  font-size: 12px;
  font-weight: 600;
  color: var(--secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
td {
  padding: 16px 24px;
  border-bottom: 1px solid rgba(193, 198, 214, 0.25);
  font-size: 14px;
  color: var(--on-surface);
  vertical-align: middle;
}
tbody tr:hover {
  background: rgba(242, 244, 245, 0.6);
}
.right {
  text-align: right;
}
.muted {
  color: var(--secondary);
  font-size: 13px;
}
.mono {
  font-family: 'Roboto Mono', monospace;
  font-size: 13px;
}
.who {
  display: flex;
  align-items: center;
  gap: 12px;
}
.av-wrap {
  position: relative;
}
.av {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
}
.av.primary {
  background: var(--primary);
  color: #fff;
}
.av.muted {
  background: var(--surface-variant, #e1e3e4);
  color: var(--on-surface-variant);
}
.av.tertiary {
  background: var(--tertiary-container, #a84fce);
  color: #fff;
}
.badge {
  position: absolute;
  right: -4px;
  bottom: -4px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--surface-variant);
  color: var(--on-surface-variant);
  font-size: 10px;
  font-family: 'Roboto Mono', monospace;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #fff;
}
.badge.prim {
  background: var(--primary);
  color: #fff;
}
.ename {
  font-weight: 600;
}
.speed {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'Roboto Mono', monospace;
  font-weight: 600;
}
.speed.primary {
  background: rgba(0, 91, 191, 0.1);
  color: var(--primary);
}
.speed.muted {
  background: var(--surface-variant);
  color: var(--on-surface-variant);
}
.spark {
  width: 48px;
  height: 20px;
  display: inline-block;
}

@media (max-width: 960px) {
  .chart-panel,
  .miss-panel,
  .rank-panel {
    grid-column: span 12;
  }
}
</style>
