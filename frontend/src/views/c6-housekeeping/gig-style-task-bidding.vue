<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 任务市场 —— 可接任务优先 board.tasks/queue（开放房间）；其余页内兜底。
 */
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import HousekeepingFlowNav from '../../components/HousekeepingFlowNav.vue'

const router = useRouter()

const FALLBACK = {
  todayEarn: '145.00',
  aiHint: t('你在深度清洁评分较高；当前有 3 个 贵宾 退房清洁匹配你的技能。'),
  tasks: [
    {
      tag: 'vip',
      title: t('8201 套房 · 贵宾退房深度清洁'),
      desc: t('预计 45 分钟 · 需按 VIP SOP 复检'),
      eta: t('45 分钟'),
      reward: 68,
      ai: true,
    },
    {
      tag: 'quick',
      title: t('0509 · 快捷续住整理'),
      desc: t('住客外出 2 小时窗口'),
      eta: t('25 分钟'),
      reward: 28,
    },
    {
      tag: 'normal',
      title: t('0412 · 退房标准清扫'),
      desc: t('常规退房 · 按楼层动线'),
      eta: t('35 分钟'),
      reward: 35,
    },
  ],
  badge: {
    title: t('准时连击：5 天'),
    desc: t('今日再完成 2 个任务即可维持你的奖励倍率（1.2 倍）！'),
  },
  leaderboard: [
    { rank: 1, name: t('陈大姐'), rating: '★ 4.9', earning: '892.00', me: false },
    { rank: 2, name: t('刘师傅'), rating: '★ 4.8', earning: '756.00', me: false },
    { rank: 3, name: t('我'), rating: '★ 4.7', earning: '145.00', me: true },
  ],
}

const data = ref<any>({ ...FALLBACK })

function tagPill(kind: string) {
  if (kind === 'vip')
    return { bg: 'var(--error-container, #ffe3e1)', color: 'var(--error)', label: t('贵宾退房') }
  if (kind === 'quick')
    return { bg: 'var(--surface-high)', color: 'var(--on-surface)', label: t('快捷') }
  return {
    bg: 'var(--secondary-container)',
    color: 'var(--on-secondary-container)',
    label: t('常规'),
  }
}

function mapTask(task: any, i: number) {
  const vip = task.priority || task.task_type === 'turn'
  const tag = vip ? 'vip' : task.type === 'inspect' ? 'quick' : 'normal'
  return {
    tag,
    title: `${task.room_no || task.room || '—'} · ${task.title || t('客房任务')}`,
    desc: task.tip || task.note || `${task.assignee ? `指派 ${task.assignee}` : t('开放抢单')}`,
    eta: task.elapsed || task.eta || `${30 + i * 5} 分钟`,
    reward: vip ? 55 + i * 5 : 28 + i * 3,
    ai: vip && i === 0,
  }
}

async function load() {
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId)
    const open = (board?.tasks || board?.queue || []).filter((t: any) => t.status !== 'done')
    const tasks = open.slice(0, 6).map(mapTask)
    const staff = board?.staff || []
    const vipCount = tasks.filter((t: any) => t.tag === 'vip').length

    const leaderboard = staff.slice(0, 3).map((s: any, i: number) => ({
      rank: i + 1,
      name: s.name,
      rating: `★ ${(4.9 - i * 0.1).toFixed(1)}`,
      earning: ((Number(s.done || 0) + 1) * 45 + i * 120).toFixed(2),
      me: i === 2,
    }))

    const done = board?.counts?.done_tasks ?? 0
    const me = staff[0]
    const todayEarn = (
      (Number(me?.done || 0) + open.filter((t: any) => t.priority).length) * 45 +
      20
    ).toFixed(2)
    data.value = {
      todayEarn,
      aiHint: vipCount
        ? `你在深度清洁评分较高；当前有 ${vipCount} 个高优任务匹配你的技能。`
        : open.length
          ? `当前开放 ${open.length} 个可接任务，建议优先抢高优退房清扫。`
          : t('暂无可接任务，可先查看排班或支援其他楼层。'),
      tasks: tasks.length ? tasks : FALLBACK.tasks,
      badge: {
        title: `今日已完成：${done} 单`,
        desc: open.length
          ? `再完成 ${Math.min(2, open.length)} 个开放任务可维持奖励倍率（1.2 倍）。`
          : t('保持连击可提升周末加价抢单权重。'),
      },
      leaderboard: leaderboard.length
        ? leaderboard.map((row: any, i: number) => ({
            ...row,
            me: i === Math.min(2, leaderboard.length - 1),
            name: i === Math.min(2, leaderboard.length - 1) ? t('我') : row.name,
            earning: i === Math.min(2, leaderboard.length - 1) ? todayEarn : row.earning,
          }))
        : FALLBACK.leaderboard,
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
    <div class="page-head head-row">
      <div>
        <h1>{{ t('任务市场') }}</h1>
        <p>{{ t('抢接今日可接任务赚取额外奖励。') }}</p>
      </div>
      <div class="head-actions">
        <div
          style="
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--surface-low);
            border: 1px solid var(--outline-variant);
            border-radius: 999px;
            padding: 8px 16px;
          "
        >
          <span style="font-weight: 600; font-size: 13px">{{ t('今日收益：') }}</span>
          <span class="num" style="color: #f9ab00; font-weight: 700"
            >￥{{ data.todayEarn || '145.00' }}</span
          >
        </div>
        <HousekeepingFlowNav mode="labor" />
      </div>
    </div>

    <div class="grid" style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px">
      <!-- 左 8：可接任务 -->
      <div style="grid-column: span 8; display: flex; flex-direction: column; gap: 24px">
        <div class="ai-card" style="border-left: 2px solid var(--tertiary)">
          <h3
            style="
              margin: 0 0 4px;
              font-size: 14px;
              font-weight: 600;
              color: var(--on-tertiary-container, #320047);
            "
          >
            {{ t('为你推荐') }}
          </h3>
          <p style="margin: 0; font-size: 13px; color: var(--on-surface-variant)">
            {{ data.aiHint }}
          </p>
        </div>
        <div>
          <h2
            style="
              font-size: 16px;
              font-weight: 600;
              display: flex;
              align-items: center;
              gap: 8px;
              margin-bottom: 16px;
            "
          >
            {{ t('可接任务') }}
          </h2>
          <div style="display: flex; flex-direction: column; gap: 16px">
            <div
              v-for="(item, i) in data.tasks || []"
              :key="i"
              class="task"
              :class="{ aimatch: item.ai }"
            >
              <div style="display: flex; justify-content: space-between; align-items: flex-start">
                <div>
                  <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
                    <span
                      class="badge"
                      :style="{ background: tagPill(item.tag).bg, color: tagPill(item.tag).color }"
                      >{{ tagPill(item.tag).label }}</span
                    >
                    <span
                      style="
                        font-size: 13px;
                        color: var(--on-surface-variant);
                        display: flex;
                        align-items: center;
                        gap: 4px;
                      "
                      ><span class="material-symbols-outlined" style="font-size: 14px"
                        >schedule</span
                      >{{ t('预计') }} {{ item.eta || '45 分钟' }}</span
                    >
                  </div>
                  <h3 style="font-size: 16px; font-weight: 600; margin: 0 0 4px">
                    {{ item.title }}
                  </h3>
                  <p style="font-size: 13px; color: var(--on-surface-variant); margin: 0">
                    {{ item.desc }}
                  </p>
                </div>
                <div style="text-align: right">
                  <div class="num reward">+￥{{ item.reward || 35 }}</div>
                  <button class="btn btn-primary" style="margin-top: 8px">{{ t('抢单') }}</button>
                </div>
              </div>
            </div>
            <div v-if="!(data.tasks || []).length" class="empty">{{ t('暂无可接任务') }}</div>
          </div>
        </div>
      </div>

      <!-- 右 4：徽章 + 排行榜 -->
      <div style="grid-column: span 4; display: flex; flex-direction: column; gap: 24px">
        <div
          class="card-clean"
          style="
            background: linear-gradient(135deg, var(--surface-lowest), var(--surface-high));
            text-align: center;
          "
        >
          <div class="badge-ico">
            <span class="material-symbols-outlined">local_fire_department</span>
          </div>
          <h3 style="font-size: 16px; font-weight: 600; margin: 0 0 4px">
            {{ (data.badge || {}).title || t('准时连击：5 天') }}
          </h3>
          <p style="font-size: 12px; color: var(--on-surface-variant); margin: 0">
            {{
              (data.badge || {}).desc || t('今日再完成 2 个任务即可维持你的奖励倍率（1.2 倍）！')
            }}
          </p>
        </div>
        <div class="card-clean">
          <div class="card-pad">
            <h2
              style="
                font-size: 16px;
                font-weight: 600;
                margin: 0 0 16px;
                display: flex;
                align-items: center;
                gap: 8px;
              "
            >
              {{ t('周度收益榜') }}
            </h2>
            <div style="display: flex; flex-direction: column; gap: 8px">
              <div
                v-for="(r, i) in data.leaderboard || []"
                :key="i"
                class="rank"
                :class="{ me: r.me }"
              >
                <div style="display: flex; align-items: center; gap: 12px">
                  <span
                    class="num"
                    :style="{
                      color: r.me
                        ? 'var(--primary)'
                        : i === 0
                          ? '#f9ab00'
                          : 'var(--on-surface-variant)',
                      width: '14px',
                      textAlign: 'center',
                    }"
                    >{{ r.rank }}</span
                  >
                  <div class="avatar-sm">{{ (r.name || '?')[0] }}</div>
                  <span style="font-size: 13px">{{ r.name }}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px">
                  <span
                    style="
                      color: #f9ab00;
                      font-size: 13px;
                      display: flex;
                      align-items: center;
                      gap: 2px;
                    "
                    >{{ r.rating }}</span
                  >
                  <span
                    class="num"
                    :style="{
                      color: r.me ? 'var(--primary)' : 'var(--on-surface)',
                      fontWeight: r.me ? 700 : 400,
                    }"
                    >￥{{ r.earning }}</span
                  >
                </div>
              </div>
              <div v-if="!(data.leaderboard || []).length" class="empty">
                {{ t('暂无排行数据') }}
              </div>
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
.task {
  background: var(--surface-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 20px;
  position: relative;
  overflow: hidden;
}
.task.aimatch {
  border-left: 3px solid var(--tertiary);
}
.reward {
  font-size: 22px;
  font-weight: 700;
  color: #f97316;
  margin-bottom: 8px;
}
.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 700;
  text-transform: uppercase;
}
.badge-ico {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #fffbeb;
  color: #f9ab00;
  border: 2px solid #fcd34d;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}
.badge-ico .material-symbols-outlined {
  font-size: 32px;
}
.avatar-sm {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary-container);
  color: var(--on-primary-container);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.rank {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  border-radius: 8px;
}
.rank.me {
  border: 1px solid rgba(0, 91, 191, 0.3);
  background: rgba(0, 91, 191, 0.05);
}
.empty {
  text-align: center;
  color: var(--on-surface-variant);
  padding: 16px;
  font-size: 13px;
}
@media (max-width: 900px) {
  .grid > div[style*='span 8'],
  .grid > div[style*='span 4'] {
    grid-column: span 12 !important;
  }
}
</style>
