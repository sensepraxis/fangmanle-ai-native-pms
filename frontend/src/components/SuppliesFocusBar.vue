<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 物资页「聚焦条」：根据路由 query 提示当前处理的个案
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps<{
  /** 当前页高亮的记录文案 */
  summary?: string
}>()

const route = useRoute()
const router = useRouter()

const active = computed(() => {
  const id =
    route.query.focus_id ||
    route.query.alert_id ||
    route.query.insight_id ||
    route.query.requisition_id
  return !!id || !!props.summary
})

const label = computed(() => {
  if (props.summary) return props.summary
  const t = String(route.query.focus_type || '')
  const id =
    route.query.focus_id ||
    route.query.alert_id ||
    route.query.insight_id ||
    route.query.requisition_id
  const kind =
    t === 'alert' || route.query.alert_id
      ? '告警'
      : t === 'insight' || route.query.insight_id
        ? '洞察'
        : t === 'requisition' || route.query.requisition_id
          ? '领用单'
          : '个案'
  return `正在聚焦：${kind} #${id}`
})

function clearFocus() {
  const q = { ...route.query }
  delete q.focus_type
  delete q.focus_id
  delete q.alert_id
  delete q.insight_id
  delete q.requisition_id
  delete q.room
  delete q.supply
  router.replace({ path: route.path, query: q })
}

function backCase() {
  const type = String(route.query.focus_type || '')
  const id = String(
    route.query.focus_id ||
      route.query.alert_id ||
      route.query.insight_id ||
      route.query.requisition_id ||
      '',
  )
  if (type && id) {
    router.push({ path: '/c7-supplies/case', query: { type, id } })
  } else if (route.query.alert_id) {
    router.push({
      path: '/c7-supplies/case',
      query: { type: 'alert', id: String(route.query.alert_id) },
    })
  } else if (route.query.insight_id) {
    router.push({
      path: '/c7-supplies/case',
      query: { type: 'insight', id: String(route.query.insight_id) },
    })
  } else if (route.query.requisition_id) {
    router.push({
      path: '/c7-supplies/case',
      query: { type: 'requisition', id: String(route.query.requisition_id) },
    })
  }
}
</script>

<template>
  <div v-if="active" class="focus-bar">
    <div class="left">
      <span class="tag">{{ t('聚焦') }}</span>
      <span class="text">{{ label }}</span>
    </div>
    <div class="right">
      <button type="button" class="link" @click="backCase">{{ t('回个案') }}</button>
      <button type="button" class="link muted" @click="clearFocus">{{ t('清除聚焦') }}</button>
    </div>
  </div>
</template>

<style scoped>
.focus-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.25);
  background: rgba(37, 99, 235, 0.06);
}
.left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.tag {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: var(--primary, #2563eb);
  border-radius: 6px;
  padding: 2px 8px;
}
.text {
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface);
}
.right {
  display: flex;
  gap: 10px;
}
.link {
  border: none;
  background: none;
  color: var(--primary);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
.link.muted {
  color: var(--on-surface-variant);
}
</style>
