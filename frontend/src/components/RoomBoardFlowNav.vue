<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 房态看板支线（侧栏「房态看板」入口）
 * hub   = 看板首页
 * ops   = 房态运营页精简链（看板 / 库存）
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = withDefaults(
  defineProps<{
    mode?: 'hub' | 'ops' | 'iot'
    hint?: string
    hideBack?: boolean
    hideLinks?: boolean
  }>(),
  { mode: 'hub', hint: '', hideBack: false, hideLinks: false },
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
  { label: '房态库存', icon: 'inventory_2', path: '/c5-frontdesk/smart-inventory' },
]

const opsBtns: FlowBtn[] = [
  { label: '房态看板', icon: 'calendar_view_day', path: '/room-board', accent: true },
  { label: '房态库存', icon: 'inventory_2', path: '/c5-frontdesk/smart-inventory' },
]

const iotBtns: FlowBtn[] = [
  { label: '房态看板', icon: 'calendar_view_day', path: '/room-board', ghost: true },
  { label: '房态库存', icon: 'inventory_2', path: '/c5-frontdesk/smart-inventory' },
]

const PATH_ALIASES: Record<string, string[]> = {
  '/room-board': ['/room-board'],
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
  ops: opsBtns,
  iot: iotBtns,
}

const visible = computed(() => {
  const list = modeBtns[props.mode] || hubBtns
  return list.filter((b) => !isCurrent(b.path))
})

const showLinks = computed(() => !props.hideLinks)
</script>

<template>
  <div class="rb-flow">
    <div v-if="showLinks" class="btns">
      <button
        v-for="b in visible"
        :key="b.path"
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
.rb-flow {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
.flow-btn.ghost {
  opacity: 0.85;
  border-style: dashed;
}
</style>
