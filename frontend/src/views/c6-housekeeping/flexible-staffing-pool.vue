<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 弹性用工池 —— 对照原型：地图零工分布 + 卡片请求 + 薪酬分发 + 质检
 * 数据：房务 board 员工名优先，其余用种子数据 / 页内兜底。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import HousekeepingFlowNav from '../../components/HousekeepingFlowNav.vue'

const router = useRouter()
const MAP_SRC = '' // 占位：实际 URL 应来自后端接口或资源上传，源码里不 hardcode

const FALLBACK_WORKERS = [
  {
    id: 1,
    name: t('陈大姐'),
    rating: '4.9',
    orders: 128,
    rate: 38,
    skill: t('客房清洁'),
    status: 'clean',
    top: '38%',
    left: '32%',
  },
  {
    id: 2,
    name: t('刘师傅'),
    rating: '4.8',
    orders: 96,
    rate: 42,
    skill: t('深度保洁'),
    status: 'clean',
    top: '52%',
    left: '48%',
  },
  {
    id: 3,
    name: t('周姐'),
    rating: '4.7',
    orders: 74,
    rate: 36,
    skill: t('布草协助'),
    status: 'idle',
    top: '28%',
    left: '58%',
  },
  {
    id: 4,
    name: t('马哥'),
    rating: '4.6',
    orders: 61,
    rate: 45,
    skill: t('工程协助'),
    status: 'maintain',
    top: '62%',
    left: '36%',
  },
  {
    id: 5,
    name: t('小林'),
    rating: '5.0',
    orders: 42,
    rate: 40,
    skill: t('VIP 清扫'),
    status: 'idle',
    top: '44%',
    left: '68%',
  },
]

const FALLBACK = {
  nearby: 12,
  aiNote: t('预测下周六入住率 95%。已基于历史效率数据自动预订 3 名外部保洁。'),
  settlement: { today: '¥1,250.00', pending: t('2 个任务') },
  qc: [
    { task: t('0509 退房清扫复检'), worker: t('陈大姐'), status: 'pass', note: '', ai: false },
    {
      task: t('0512 视觉质检异常'),
      worker: t('刘师傅'),
      status: 'ai',
      note: t('毛巾套装缺失 · AI 建议复核'),
      ai: true,
    },
    { task: t('0601 深度清洁'), worker: t('周姐'), status: 'review', note: '', ai: false },
  ],
  workers: FALLBACK_WORKERS,
}

const data = ref<any>({ ...FALLBACK })
const selectedId = ref<number | null>(FALLBACK_WORKERS[0].id)

const selected = computed(() => {
  const list = data.value.workers || []
  return list.find((w: any) => w.id === selectedId.value) || list[0] || null
})

function qcPill(s: string) {
  if (s === 'pass') return { bg: '#e6f4ea', color: '#137333', label: t('已通过') }
  if (s === 'ai')
    return {
      bg: 'var(--secondary-container)',
      color: 'var(--on-secondary-container)',
      label: t('AI 复核'),
    }
  return { bg: '#fce8e6', color: '#c5221f', label: t('复核') }
}

function pinClass(status: string) {
  if (status === 'maintain') return 'pin maintain'
  if (status === 'clean') return 'pin clean'
  return 'pin idle'
}

function selectWorker(w: any) {
  selectedId.value = w.id
}

async function load() {
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId)
    const staff = board?.staff || []
    const positions = [
      { top: '38%', left: '32%' },
      { top: '52%', left: '48%' },
      { top: '28%', left: '58%' },
      { top: '62%', left: '36%' },
      { top: '44%', left: '68%' },
      { top: '55%', left: '72%' },
    ]
    let workers = FALLBACK_WORKERS.map((w) => ({ ...w }))
    if (staff.length) {
      workers = staff.slice(0, 6).map((s: any, i: number) => {
        const base = FALLBACK_WORKERS[i % FALLBACK_WORKERS.length]
        const busy = s.busy || Number(s.open || 0) > 0
        return {
          id: s.id || base.id + i,
          name: s.name || base.name,
          rating: base.rating,
          orders: Number(s.done || 0) * 12 + base.orders,
          rate: base.rate,
          skill: busy ? t('客房清洁 · 在岗') : s.area || base.skill,
          status: busy ? 'clean' : i % 4 === 3 ? 'maintain' : 'idle',
          top: positions[i % positions.length].top,
          left: positions[i % positions.length].left,
        }
      })
    }

    // 质检：用 vision history / pending 拼几条
    const vision = board?.vision || {}
    const hist = vision.history || []
    const qc = hist.slice(0, 3).map((h: any, i: number) => ({
      task: `${h.room || '—'} 查房${h.result === 'fail' ? t('返工') : t('通过')}`,
      worker: h.inspector || workers[i % workers.length]?.name || t('零工'),
      status: h.result === 'fail' ? 'ai' : 'pass',
      note: h.result === 'fail' ? t('AI 标注异常项，建议复核后结算') : '',
      ai: h.result === 'fail',
    }))

    const openTasks = (board?.tasks || board?.queue || []).filter(
      (t: any) => t.status !== 'done',
    ).length
    const done = Number(board?.counts?.done_tasks || 0)
    const pendingQc = qc.filter((q: any) => q.status !== 'pass').length
    const settleAmt = done * 95 + workers.filter((w: any) => w.status === 'clean').length * 38
    data.value = {
      nearby: Math.max(workers.length, openTasks),
      aiNote: openTasks
        ? `当前开放清扫 ${openTasks} 单；在岗/可调度 ${workers.length} 人。AI 已按楼层压力预留兼职运力。`
        : `今日已闭环 ${done} 单；附近可调度 ${workers.length} 人。`,
      settlement: {
        today: `¥${settleAmt.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        pending: pendingQc ? `${pendingQc} 个任务` : `${Math.max(0, openTasks)} 个待结`,
      },
      qc: qc.length
        ? qc
        : (board?.vision?.rooms || []).slice(0, 3).map((v: any, i: number) => ({
            task: `${v.room} ${v.type || t('查房')}`,
            worker: v.note || workers[i % Math.max(workers.length, 1)]?.name || t('零工'),
            status: v.needAction ? 'ai' : 'review',
            note: v.needAction ? t('待 AI/人工复核') : '',
            ai: !!v.needAction,
          })),
      workers,
    }
    selectedId.value = workers[0]?.id ?? null
  } catch {
    data.value = { ...FALLBACK, workers: FALLBACK_WORKERS.map((w) => ({ ...w })) }
    selectedId.value = FALLBACK_WORKERS[0].id
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)

function goDispatch() {
  router.push('/c6-housekeeping/dispatch')
}
</script>

<template>
  <div class="page">
    <div class="page-head head-row">
      <div>
        <h1>{{ t('弹性用工池') }}</h1>
        <p>{{ t('管理兼职人力、零工集成与自动排程。') }}</p>
      </div>
      <div class="head-actions">
        <HousekeepingFlowNav
          mode="labor"
          :hint="t('人力支线：排班 · 用工池 · 零工抢单 · 临时用工')"
        />
      </div>
    </div>

    <div class="ai-card ai-banner">
      <div class="ai-left">
        <div class="ai-badge"><span class="material-symbols-outlined">auto_awesome</span></div>
        <div>
          <h3>{{ t('AI 排程优化已启用') }}</h3>
          <p>{{ data.aiNote }}</p>
        </div>
      </div>
      <button class="btn btn-ghost" type="button" @click="goDispatch">{{ t('复核排程') }}</button>
    </div>

    <div class="grid main-grid">
      <!-- 地图 + 零工 -->
      <div class="card-clean map-card">
        <div class="card-head map-head">
          <span class="head-title">{{ t('本地零工') }}</span>
          <span class="pill pill-blue"
            >{{ t('附近') }} {{ data.nearby || (data.workers || []).length }} {{ t('人')
            }}{{ t('可接') }}</span
          >
        </div>
        <div class="map-stage">
          <img class="map-img" :src="MAP_SRC" :alt="t('周边零工分布地图')" />
          <div class="map-veil"></div>

          <!-- 地图钉点 -->
          <button
            v-for="w in data.workers || []"
            :key="'pin-' + w.id"
            type="button"
            :class="[pinClass(w.status), { active: selected && selected.id === w.id }]"
            :style="{ top: w.top, left: w.left }"
            :title="w.name"
            @click="selectWorker(w)"
          >
            <span class="pin-dot"></span>
            <span class="pin-label">{{ w.name }}</span>
          </button>

          <!-- 顶部可横滑工人卡 -->
          <div class="worker-rail">
            <div
              v-for="w in data.workers || []"
              :key="w.id"
              class="worker"
              :class="{ active: selected && selected.id === w.id }"
              @click="selectWorker(w)"
            >
              <div class="worker-top">
                <div class="avatar-sm">{{ (w.name || t('工')).charAt(0) }}</div>
                <div class="worker-meta">
                  <div class="worker-name">{{ w.name }}</div>
                  <div class="worker-sub">
                    <span class="num">{{ w.rating }}</span>
                    <span class="muted">（{{ w.orders }} {{ t('单）') }}</span>
                  </div>
                  <div class="worker-skill">{{ w.skill }}</div>
                </div>
              </div>
              <div class="worker-bot">
                <span class="num rate">¥{{ w.rate }}/{{ t('小时') }}</span>
                <button class="btn btn-primary req-btn" type="button" @click.stop>
                  {{ t('请求') }}
                </button>
              </div>
            </div>
          </div>

          <div class="legend-bar">
            <span><i class="dot clean"></i>{{ t('清洁中') }}</span>
            <span><i class="dot maintain"></i>{{ t('维护') }}</span>
            <span><i class="dot idle"></i>{{ t('可接单') }}</span>
          </div>
        </div>
      </div>

      <!-- 右栏 -->
      <div class="side-col">
        <div class="card-clean">
          <div class="card-pad">
            <div class="side-title-row">
              <h3 class="side-title">{{ t('薪酬分发') }}</h3>
              <div class="toggle" :title="t('自动日结')"><div class="knob"></div></div>
            </div>
            <div class="status-box">
              <p class="label">{{ t('状态') }}</p>
              <p class="status-on">{{ t('自动日结薪酬已启用') }}</p>
            </div>
            <div class="kv">
              <div>
                <span class="muted">{{ t('今日预计发放') }}</span
                ><span class="num bold">{{ data.settlement?.today }}</span>
              </div>
              <div>
                <span class="muted">{{ t('待审批') }}</span
                ><span class="num pending">{{ data.settlement?.pending }}</span>
              </div>
            </div>
            <button class="btn btn-ghost full" type="button">{{ t('查看台账') }}</button>
          </div>
        </div>

        <div class="card-clean side-qc">
          <div class="card-pad">
            <h3 class="side-title">{{ t('结算前质检') }}</h3>
            <div class="qc-list">
              <div v-for="(q, i) in data.qc || []" :key="i" class="qc" :class="{ ai: q.ai }">
                <div class="qc-top">
                  <span class="qc-task">{{ q.task }}</span>
                  <span
                    class="badge"
                    :style="{ background: qcPill(q.status).bg, color: qcPill(q.status).color }"
                  >
                    {{ qcPill(q.status).label }}</span
                  >
                </div>
                <p v-if="q.note" class="qc-note">{{ q.note }}</p>
                <div class="qc-bot">
                  <span class="muted">{{ q.worker }}</span>
                  <button v-if="q.ai" class="btn btn-ghost mini" type="button">
                    {{ t('审计任务') }}
                  </button>
                </div>
              </div>
              <div v-if="!(data.qc || []).length" class="empty">{{ t('暂无质检任务') }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 12px;
}
.head-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.ai-banner {
  margin-bottom: 16px;
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
}
.ai-left {
  display: flex;
  gap: 16px;
  align-items: center;
}
.ai-badge {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--tertiary-container);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ai-badge .material-symbols-outlined {
  font-size: 18px;
}
.ai-left h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}
.ai-left p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--on-surface-variant);
  max-width: 640px;
}
.main-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 16px;
}
.map-card {
  grid-column: span 8;
  display: flex;
  flex-direction: column;
  min-height: 520px;
}
.map-head .head-title {
  font-size: 16px;
  font-weight: 700;
}
.map-stage {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-height: 460px;
  background: #d9e2ec;
}
.map-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.map-veil {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(15, 23, 42, 0.12));
  pointer-events: none;
}
.pin {
  position: absolute;
  transform: translate(-50%, -100%);
  border: none;
  background: transparent;
  cursor: pointer;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 0;
}
.pin-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.35);
}
.pin.clean .pin-dot {
  background: var(--primary);
}
.pin.maintain .pin-dot {
  background: var(--tertiary);
}
.pin.idle .pin-dot {
  background: #059669;
}
.pin-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--on-surface);
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--outline-variant);
  border-radius: 999px;
  padding: 2px 8px;
  white-space: nowrap;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.12);
}
.pin.active .pin-label {
  border-color: var(--primary);
  color: var(--primary);
}
.pin.active .pin-dot {
  transform: scale(1.2);
}
.worker-rail {
  position: absolute;
  top: 16px;
  left: 16px;
  right: 16px;
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
  z-index: 4;
}
.worker {
  width: 220px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid var(--outline-variant);
  border-radius: 10px;
  padding: 12px;
  backdrop-filter: blur(6px);
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.worker:hover,
.worker.active {
  border-color: var(--primary);
  box-shadow: 0 6px 18px rgba(0, 91, 191, 0.16);
}
.worker-top {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.avatar-sm {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--secondary-container);
  color: var(--on-secondary-container);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}
.worker-name {
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
}
.worker-sub {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.worker-skill {
  margin-top: 4px;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.worker-bot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}
.rate {
  color: var(--primary);
  font-size: 14px;
  font-weight: 700;
}
.req-btn {
  padding: 4px 12px;
  font-size: 12px;
}
.legend-bar {
  position: absolute;
  right: 16px;
  bottom: 16px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  gap: 12px;
  z-index: 4;
}
.legend-bar .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 4px;
}
.legend-bar .dot.clean {
  background: var(--primary);
}
.legend-bar .dot.maintain {
  background: var(--tertiary);
}
.legend-bar .dot.idle {
  background: #059669;
}
.side-col {
  grid-column: span 4;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.side-qc {
  flex: 1;
}
.side-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.side-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 16px;
}
.side-title-row .side-title {
  margin: 0;
}
.status-box {
  background: var(--surface-low);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.status-box .label {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin: 0 0 4px;
}
.status-on {
  margin: 0;
  color: var(--primary);
  font-weight: 700;
}
.kv {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.kv > div {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.muted {
  color: var(--on-surface-variant);
}
.bold {
  font-weight: 700;
}
.pending {
  color: var(--error);
  font-weight: 700;
}
.full {
  width: 100%;
  margin-top: 20px;
}
.toggle {
  width: 40px;
  height: 24px;
  border-radius: 999px;
  background: var(--primary-container);
  display: flex;
  align-items: center;
  padding: 2px;
  cursor: pointer;
}
.knob {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--on-primary-container);
  transform: translateX(16px);
}
.qc-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.qc {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--outline-variant);
}
.qc:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}
.qc.ai {
  border-left: 2px solid var(--tertiary);
  padding-left: 8px;
}
.qc-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}
.qc-task {
  font-size: 14px;
  font-weight: 700;
}
.qc-note {
  font-size: 12px;
  color: var(--tertiary);
  font-weight: 600;
  margin: 0 0 6px;
}
.qc-bot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 12px;
}
.badge {
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 4px;
  font-weight: 700;
  white-space: nowrap;
}
.mini {
  padding: 2px 8px;
  font-size: 11px;
}
.empty {
  text-align: center;
  color: var(--on-surface-variant);
  padding: 16px;
  font-size: 13px;
}
@media (max-width: 960px) {
  .map-card,
  .side-col {
    grid-column: span 12 !important;
  }
}
</style>
