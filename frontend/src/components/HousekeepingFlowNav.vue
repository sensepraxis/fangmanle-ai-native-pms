<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 房务动线页头 CTA
 * hub   = 作业台：A 清扫主链 + 灵活用工(支) + 客需(B) + 班末交接
 * chain = A 主链精简（作业台/派工/任务板/质检/效能）
 * labor = A′ 人力支线（排班/用工池/抢单/临时用工/人效）
 * guest = B 客需（客需看板/流转/SLA/AI助理/多语言）
 * review= A 复盘（效能/人效/质检日志/SOP）
 * shift = 班末交接（交接班 / 换班场景）
 * 注：房态看板支线走 RoomBoardFlowNav，不挂本组件
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = withDefaults(
  defineProps<{
    mode?: 'hub' | 'chain' | 'labor' | 'guest' | 'review' | 'shift'
    hint?: string
  }>(),
  { mode: 'hub', hint: '' },
)

const route = useRoute()
const router = useRouter()

type FlowBtn = {
  label: string
  icon: string
  path: string
  accent?: boolean
  ghost?: boolean
}

const hubBtns: FlowBtn[] = [
  { label: t('派工'), icon: 'assignment_ind', path: '/c6-housekeeping/housekeeping' },
  { label: t('任务板'), icon: 'view_kanban', path: '/c6-housekeeping/housekeeping' },
  { label: t('质检日志'), icon: 'visibility', path: '/c6-housekeeping/view-full-incident-log' },
  { label: t('复盘'), icon: 'monitoring', path: '/c6-housekeeping/reports?tab=perf' },
  {
    label: t('灵活用工'),
    icon: 'groups',
    path: '/c6-housekeeping/flexible-staffing-pool',
    ghost: true,
  },
  {
    label: t('客需'),
    icon: 'room_service',
    path: '/c6-housekeeping/in-stay-guest-request-management',
    accent: true,
  },
  {
    label: t('交接班'),
    icon: 'swap_horiz',
    path: '/c9-finance/shift-handover/handover',
    ghost: true,
  },
  { label: t('换班'), icon: 'nightlife', path: '/c9-finance/shift-handover/takeover', ghost: true },
]

const chainBtns: FlowBtn[] = [
  { label: t('作业台'), icon: 'home', path: '/c6-housekeeping/housekeeping' },
  { label: t('派工'), icon: 'assignment_ind', path: '/c6-housekeeping/housekeeping' },
  { label: t('任务板'), icon: 'view_kanban', path: '/c6-housekeeping/housekeeping' },
  { label: t('质检日志'), icon: 'visibility', path: '/c6-housekeeping/view-full-incident-log' },
  { label: t('复盘'), icon: 'monitoring', path: '/c6-housekeeping/reports?tab=perf' },
]

const laborBtns: FlowBtn[] = [
  { label: t('作业台'), icon: 'home', path: '/c6-housekeeping/housekeeping', ghost: true },
  { label: t('排班'), icon: 'calendar_month', path: '/c6-housekeeping/staffing' },
  {
    label: t('排班深讲'),
    icon: 'view_timeline',
    path: '/c6-housekeeping/room-board-3',
    ghost: true,
  },
  {
    label: t('用工池'),
    icon: 'groups',
    path: '/c6-housekeeping/flexible-staffing-pool',
    accent: true,
  },
  { label: t('零工抢单'), icon: 'handshake', path: '/c6-housekeeping/gig-style-task-bidding' },
  {
    label: t('临时用工'),
    icon: 'engineering',
    path: '/c6-housekeeping/on-demand-labor',
    ghost: true,
  },
  { label: t('今日运营'), icon: 'speed', path: '/c6-housekeeping/reports?tab=labor', ghost: true },
]

const guestBtns: FlowBtn[] = [
  {
    label: t('客需看板'),
    icon: 'list_alt',
    path: '/c6-housekeeping/in-stay-guest-request-management',
    accent: true,
  },
  { label: t('常住服务'), icon: 'room_service', path: '/c5-frontdesk/housekeeping', ghost: true },
  { label: t('客需流转'), icon: 'account_tree', path: '/c6-housekeeping/workflow' },
  { label: t('SLA质量'), icon: 'verified', path: '/c6-housekeeping/arrow-forward' },
  {
    label: t('多语言'),
    icon: 'translate',
    path: '/c6-housekeeping/room-302-john-doe',
    ghost: true,
  },
]

const reviewBtns: FlowBtn[] = [
  { label: t('作业台'), icon: 'home', path: '/c6-housekeeping/housekeeping', ghost: true },
  { label: t('复盘'), icon: 'monitoring', path: '/c6-housekeeping/reports?tab=perf', accent: true },
  { label: t('今日运营'), icon: 'speed', path: '/c6-housekeeping/reports?tab=labor' },
  { label: t('质检日志'), icon: 'analytics', path: '/c6-housekeeping/view-full-incident-log' },
  { label: t('SOP库'), icon: 'menu_book', path: '/c6-housekeeping/sop', ghost: true },
]

/** 班末：挂在房务作业台下 */
const shiftBtns: FlowBtn[] = [
  { label: t('作业台'), icon: 'home', path: '/c6-housekeeping/housekeeping', ghost: true },
  {
    label: t('交接班'),
    icon: 'swap_horiz',
    path: '/c9-finance/shift-handover/handover',
    accent: true,
  },
  { label: t('换班场景'), icon: 'nightlife', path: '/c9-finance/shift-handover/takeover' },
  { label: t('排班'), icon: 'calendar_month', path: '/c6-housekeeping/staffing', ghost: true },
]

const PATH_ALIASES: Record<string, string[]> = {
  '/c6-housekeeping/housekeeping': ['/c6-housekeeping/housekeeping', '/housekeeping'],
  '/c6-housekeeping/room-board': ['/c6-housekeeping/room-board'],
}

function normalize(p: string) {
  return (p || '').replace(/\/+$/, '') || '/'
}

function isCurrent(path: string) {
  const cur = normalize(route.path)
  const aliases = PATH_ALIASES[path] || [path]
  return aliases.some((p) => cur === normalize(p))
}

const modeBtns: Record<string, FlowBtn[]> = {
  hub: hubBtns,
  chain: chainBtns,
  labor: laborBtns,
  guest: guestBtns,
  review: reviewBtns,
  shift: shiftBtns,
}

const visibleBtns = computed(() => {
  const list = modeBtns[props.mode] || hubBtns
  return list.filter((b) => !isCurrent(b.path))
})
</script>

<template>
  <div class="hk-flow">
    <p v-if="hint" class="hint">{{ hint }}</p>
    <div class="btns">
      <button
        v-for="b in visibleBtns"
        :key="b.path + b.label"
        type="button"
        class="flow-btn"
        :class="{ accent: b.accent, ghost: b.ghost }"
        @click="router.push(b.path)"
      >
        <span class="material-symbols-outlined">{{ b.icon }}</span>
        {{ t(b.label) }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.hk-flow {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}
.hint {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  text-align: right;
}
.btns {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.flow-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant, #c9ced8);
  background: var(--surface-container-lowest, #fff);
  color: var(--on-surface, #1f2329);
  font-size: 13px;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s,
    color 0.15s;
}
.flow-btn .material-symbols-outlined {
  font-size: 16px;
}
.flow-btn:hover {
  background: var(--surface-container-low, #f3f4f6);
}
.flow-btn.accent {
  border-color: #1f2329;
  background: #1f2329;
  color: #fff;
  font-weight: 600;
}
.flow-btn.accent:hover {
  background: #333943;
  border-color: #333943;
  color: #fff;
}
.flow-btn.ghost {
  color: var(--on-surface-variant, #5b616e);
}
</style>
