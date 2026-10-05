<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 临时用工与抢单池 —— 任务/零工优先 board.tasks + board.staff；其余页内兜底。
 */
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import HousekeepingFlowNav from '../../components/HousekeepingFlowNav.vue'

const router = useRouter()

const FALLBACK = {
  marketNote: t(
    '根据当前本地市场数据，周末深度清洁服务供需紧张，建议将基础报价上调 15% 以提高抢单率。预计最佳单价为 ¥180/单。',
  ),
  tasks: [
    {
      urgent: true,
      title: t('8201 套房深度清洁'),
      desc: t('贵宾退房 · 需 VIP SOP 复检与拍照上传'),
      price: 220,
      aiPrice: 198,
      eta: '2.5h',
      loc: t('8F 东区'),
    },
    {
      urgent: false,
      title: t('0509 续住深度整理'),
      desc: t('住客外出窗口 · 标准深度清洁'),
      price: 160,
      aiPrice: 168,
      eta: '2h',
      loc: '5F',
    },
    {
      urgent: false,
      title: t('B 翼公区地毯护理'),
      desc: t('周末加单 · 需自带设备'),
      price: 280,
      aiPrice: 252,
      eta: '3h',
      loc: t('B 翼走廊'),
    },
  ],
  pool: [
    { name: t('陈大姐'), role: t('深度保洁 · 4.9★'), status: 'progress' },
    { name: t('刘师傅'), role: t('申请抢单 · 0509'), status: 'pending' },
    { name: t('周姐'), role: t('布草协助 · 4.7★'), status: 'progress' },
  ],
  settle: { verified: 12, pending: '¥1,850' },
}

const data = ref<any>({ ...FALLBACK })

function taskTag(row: any) {
  if (row.urgent)
    return { bg: 'var(--error-container, #ffe3e1)', color: 'var(--error)', label: t('加急') }
  return {
    bg: 'var(--secondary-container)',
    color: 'var(--on-secondary-container)',
    label: t('常规'),
  }
}
function poolPill(s: string) {
  if (s === 'progress')
    return {
      bg: 'var(--tertiary-container)',
      color: 'var(--on-tertiary-container)',
      label: t('进行中'),
    }
  return { bg: 'rgba(186,26,26,0.1)', color: 'var(--error)', label: t('待审核') }
}

function mapOpenTask(task: any, i: number) {
  const urgent = task.priority || (task.priority_rank || 5) <= 2
  const base = urgent ? 200 : 150
  return {
    urgent,
    title: `${task.room_no || task.room || '—'} · ${task.title || t('深度清洁')}`,
    desc: task.tip || `${task.assignee ? `当前 ${task.assignee}` : t('待发布至抢单池')}`,
    price: base + i * 15,
    aiPrice: base + i * 10 - 12,
    eta: task.elapsed ? task.elapsed.replace(t('分钟'), 'h').replace(' ', '') : `${2 + (i % 2)}h`,
    loc: task.floor ? `${task.floor}F` : t('东区三楼'),
  }
}

async function load() {
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId)
    const unassigned = (board?.tasks || board?.queue || []).filter(
      (t: any) => t.status !== 'done' && (t.assignee === t('待分配') || !t.assignee_id),
    )
    const openAll = (board?.tasks || []).filter((t: any) => t.status !== 'done')
    const tasks = (unassigned.length ? unassigned : openAll).slice(0, 5).map(mapOpenTask)

    const staff = board?.staff || []
    const pool = staff.slice(0, 5).map((s: any, i: number) => ({
      name: s.name,
      role: s.area || (s.busy ? t('客房清洁 · 在岗') : t('零工')),
      status: s.busy ? 'progress' : i === 1 ? 'pending' : 'progress',
    }))

    const done = board?.counts?.done_tasks ?? 0
    const openN = openAll.length
    data.value = {
      marketNote:
        openN >= 4
          ? `当前开放 ${openN} 单清扫任务，供需偏紧。AI 建议基础报价上调 12–18%，最佳单价约 ¥${160 + openN * 8}/单。`
          : openN
            ? `市场平稳：开放 ${openN} 单。建议报价维持 ¥${150 + openN * 5}–${180 + openN * 6}/单以兼顾抢单率。`
            : t('今日开放任务较少，可发布深度清洁加单吸引高评分零工。'),
      tasks: tasks.length ? tasks : FALLBACK.tasks,
      pool: pool.length ? pool : FALLBACK.pool,
      settle: {
        verified: done || pool.filter((p: any) => p.status === 'progress').length,
        pending: `¥${(done * 120 + openN * 85 + 200).toLocaleString()}`,
      },
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
        <h1>{{ t('临时用工与抢单池') }}</h1>
        <p>{{ t('按需发布深度清洁任务，由认证零工抢单完成并结算。') }}</p>
      </div>
      <div class="head-actions">
        <HousekeepingFlowNav mode="labor" />
      </div>
    </div>

    <!-- AI 劳动力市场分析 -->
    <div
      class="ai-card"
      style="
        margin-bottom: 16px;
        display: flex;
        gap: 16px;
        align-items: flex-start;
        flex-wrap: wrap;
        justify-content: space-between;
      "
    >
      <div>
        <h3
          style="
            margin: 0 0 4px;
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
          "
        >
          <span class="material-symbols-outlined" style="color: var(--tertiary)">auto_awesome</span
          >{{ t('AI 劳动力市场分析') }}
        </h3>
        <p style="margin: 0; font-size: 13px; color: var(--on-surface-variant)">
          {{ data.marketNote }}
        </p>
      </div>
      <button class="btn btn-primary">{{ t('一键应用建议价') }}</button>
    </div>

    <div class="grid" style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px">
      <!-- 左 8：待分配任务 -->
      <div style="grid-column: span 8">
        <h3 style="font-size: 16px; font-weight: 600; margin: 0 0 16px">
          {{ t('待分配深度清洁任务 (Unassigned Tasks)') }}
        </h3>
        <div style="display: flex; flex-direction: column; gap: 16px">
          <div v-for="(item, i) in data.tasks || []" :key="i" class="task">
            <div
              style="
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 16px;
              "
            >
              <div>
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px">
                  <span
                    class="badge"
                    :style="{ background: taskTag(item).bg, color: taskTag(item).color }"
                    >{{ taskTag(item).label }}</span
                  >
                  <h4 style="font-size: 16px; font-weight: 600; margin: 0">{{ item.title }}</h4>
                </div>
                <p style="font-size: 13px; color: var(--on-surface-variant); margin: 0">
                  {{ item.desc }}
                </p>
              </div>
              <div style="text-align: right">
                <div class="num" style="font-size: 24px; font-weight: 700; color: var(--primary)">
                  ¥{{ item.price }}
                </div>
                <div style="font-size: 11px; color: var(--on-surface-variant)">
                  AI {{ t('建议:') }} ¥{{ item.aiPrice }}
                </div>
              </div>
            </div>
            <div
              style="
                display: flex;
                align-items: center;
                gap: 16px;
                font-size: 13px;
                color: var(--on-surface-variant);
                margin-bottom: 20px;
              "
            >
              <span style="display: inline-flex; align-items: center; gap: 4px"
                ><span class="material-symbols-outlined" style="font-size: 14px">schedule</span
                >{{ t('预计用时:') }} {{ item.eta || '2h' }}</span
              >
              <span style="display: inline-flex; align-items: center; gap: 4px"
                ><span class="material-symbols-outlined" style="font-size: 14px">location_on</span
                >{{ item.loc || t('东区三楼') }}</span
              >
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 12px">
              <button class="btn btn-ghost">{{ t('编辑任务') }}</button>
              <button class="btn btn-primary">{{ t('发布至抢单池') }}</button>
            </div>
          </div>
          <div v-if="!(data.tasks || []).length" class="empty">{{ t('暂无待分配任务') }}</div>
        </div>
      </div>

      <!-- 右 4：抢单池动态 + 结算 -->
      <div style="grid-column: span 4; display: flex; flex-direction: column; gap: 16px">
        <div class="card-clean">
          <div class="card-pad">
            <h3 style="font-size: 16px; font-weight: 600; margin: 0 0 16px">
              {{ t('抢单池动态') }}
            </h3>
            <div style="display: flex; flex-direction: column; gap: 12px">
              <div
                v-for="(p, i) in data.pool || []"
                :key="i"
                class="pool"
                :class="{ err: p.status !== 'progress' }"
              >
                <div style="display: flex; align-items: center; gap: 12px">
                  <div class="avatar-sm">
                    <span class="material-symbols-outlined" style="font-size: 18px">{{
                      p.status === 'progress' ? 'person' : 'history'
                    }}</span>
                  </div>
                  <div>
                    <div style="font-size: 13px; font-weight: 500">{{ p.name }}</div>
                    <div style="font-size: 11px; color: var(--on-surface-variant)">
                      {{ p.role }}
                    </div>
                  </div>
                </div>
                <span
                  v-if="p.status === 'progress'"
                  class="badge"
                  :style="{ background: poolPill(p.status).bg, color: poolPill(p.status).color }"
                  >{{ poolPill(p.status).label }}</span
                >
                <button v-else class="btn btn-primary" style="padding: 4px 10px; font-size: 11px">
                  {{ t('去审核') }}
                </button>
              </div>
              <div v-if="!(data.pool || []).length" class="empty">{{ t('暂无动态') }}</div>
            </div>
          </div>
        </div>
        <div class="card-clean">
          <div class="card-pad">
            <h3 style="font-size: 16px; font-weight: 600; margin: 0 0 16px">
              {{ t('今日结算状态') }}
            </h3>
            <div
              style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px"
            >
              <div
                style="
                  background: var(--surface);
                  border-radius: 8px;
                  padding: 16px;
                  text-align: center;
                "
              >
                <div style="font-size: 12px; color: var(--on-surface-variant); margin-bottom: 4px">
                  {{ t('已验收单量') }}
                </div>
                <div class="num" style="font-size: 24px; font-weight: 700">
                  {{ data.settle?.verified || 12 }}
                </div>
              </div>
              <div
                style="
                  background: var(--surface);
                  border-radius: 8px;
                  padding: 16px;
                  text-align: center;
                "
              >
                <div style="font-size: 12px; color: var(--on-surface-variant); margin-bottom: 4px">
                  {{ t('待支付总额') }}
                </div>
                <div class="num" style="font-size: 24px; font-weight: 700; color: var(--primary)">
                  {{ data.settle?.pending || '¥1,850' }}
                </div>
              </div>
            </div>
            <button
              class="btn btn-ghost"
              style="
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
              "
            >
              <span class="material-symbols-outlined" style="font-size: 18px"
                >account_balance_wallet</span
              >{{ t('查看财务结算详情') }}
            </button>
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
  flex-wrap: wrap;
  justify-content: flex-end;
}
.task {
  background: var(--surface-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 24px;
}
.badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  font-weight: 700;
}
.avatar-sm {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--primary-container);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.pool {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: var(--surface);
  border-radius: 8px;
}
.pool.err {
  border-left: 2px solid var(--error);
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
