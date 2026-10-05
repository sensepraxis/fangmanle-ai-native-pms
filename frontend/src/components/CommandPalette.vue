<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { commercialEnabled, packUiRev } from '../lib/branding'
import { pageManifest } from '../pages.manifest'

const router = useRouter()
const open = ref(false)
const query = ref('')
const selected = ref(0)
const hotels = ref<any[]>([])
const recentOrders = ref<any[]>([])
const recentGuests = ref<any[]>([])
const recentRooms = ref<any[]>([])

const NAV_COMMANDS = [
  { id: 'go:dashboard', label: t('进入 经营看板'), icon: 'dashboard', group: '页面跳转' },
  { id: 'go:pricing', label: t('进入 价格助手'), icon: 'auto_graph', group: '页面跳转' },
  { id: 'go:revenue-forecast', label: t('进入 营收预测'), icon: 'trending_up', group: '页面跳转' },
  { id: 'go:orders', label: t('进入 订单管理'), icon: 'receipt_long', group: '页面跳转' },
  { id: 'go:analytics', label: t('进入 数据洞察'), icon: 'monitoring', group: '页面跳转' },
  {
    id: 'go:room-board',
    label: t('进入 房务与房态'),
    icon: 'calendar_view_day',
    group: '页面跳转',
  },
  {
    id: 'go:housekeeping',
    label: t('进入 房务任务'),
    icon: 'cleaning_services',
    group: '页面跳转',
  },
  {
    id: 'go:assets',
    label: t('进入 设备设施（房务与房态）'),
    icon: 'precision_manufacturing',
    group: '页面跳转',
  },
  { id: 'go:finance', label: t('进入 财务管理'), icon: 'payments', group: '页面跳转' },
  { id: 'go:crm', label: t('进入 客户会员'), icon: 'share_reviews', group: '页面跳转' },
  { id: 'go:acquisition', label: t('进入 私域运营'), icon: 'groups', group: '页面跳转' },
  { id: 'go:ai', label: t('进入 AI 问数（数据洞察）'), icon: 'smart_toy', group: '页面跳转' },
]
const AI_ACTIONS = [
  { id: 'ai:audit', label: t('AI 执行今日夜审'), icon: 'auto_awesome', group: 'AI 任务' },
  { id: 'ai:new-order', label: t('AI 给散客开新订单'), icon: 'auto_awesome', group: 'AI 任务' },
  {
    id: 'ai:accept-pricing',
    label: t('AI 采纳所有非拦截改价'),
    icon: 'auto_awesome',
    group: 'AI 任务',
  },
  { id: 'ai:dispatch-hk', label: t('AI 给脏房自动派工'), icon: 'auto_awesome', group: 'AI 任务' },
]

function navCommands() {
  void packUiRev.value
  if (commercialEnabled()) return NAV_COMMANDS
  return NAV_COMMANDS.filter((c) => c.id !== 'go:ai')
}

function aiActionCommands() {
  void packUiRev.value
  return commercialEnabled() ? AI_ACTIONS : []
}

function groupBy(arr: any[], key: string) {
  const out: Record<string, any[]> = {}
  arr.forEach((it) => {
    const k = it[key] || '其他'
    if (!out[k]) out[k] = []
    out[k].push(it)
  })
  return Object.entries(out).map(([k, items]) => ({ k, items }))
}

const combined = computed(() => {
  const q = query.value.trim().toLowerCase()
  const all: any[] = []
  if (!q) {
    navCommands()
      .slice(0, 5)
      .forEach((c) => all.push(c))
    all.push({
      id: 'go:map',
      label: t('浏览全部页面地图（') + pageManifest.length + ' 页）',
      icon: 'map',
      group: '页面跳转',
    })
    if (hotels.value.length) {
      hotels.value.forEach((h) =>
        all.push({
          id: 'hotel:' + h.id,
          label: t('切换门店：') + h.name,
          icon: 'storefront',
          group: '门店切换',
          meta: h,
        }),
      )
    }
    if (recentOrders.value.length) {
      recentOrders.value.slice(0, 5).forEach((o) =>
        all.push({
          id: 'order:' + o.id,
          label: `订单 ${o.order_no} · ${o.guest_name || '散客'}`,
          icon: 'receipt_long',
          group: '近期订单',
          meta: o,
        }),
      )
    }
    if (recentGuests.value.length) {
      recentGuests.value.slice(0, 5).forEach((g) =>
        all.push({
          id: 'guest:' + g.id,
          label: `${g.name || '客人'} · ${g.phone || '—'}`,
          icon: 'person',
          group: '近期客户',
          meta: g,
        }),
      )
    }
    if (recentRooms.value.length) {
      recentRooms.value.slice(0, 5).forEach((r) =>
        all.push({
          id: 'room:' + r.id,
          label: `房间 ${r.room_no} · ${r.room_type_name || ''}`,
          icon: 'bed',
          group: '近期房间',
          meta: r,
        }),
      )
    }
    return all
  }
  navCommands().forEach((c) => {
    if (c.label.toLowerCase().includes(q) || c.id.toLowerCase().includes(q)) all.push(c)
  })
  aiActionCommands().forEach((c) => {
    if (c.label.toLowerCase().includes(q)) all.push(c)
  })
  hotels.value.forEach((h) => {
    if (('切换 ' + h.name).toLowerCase().includes(q) || h.name.toLowerCase().includes(q))
      all.push({
        id: 'hotel:' + h.id,
        label: t('切换门店：') + h.name,
        icon: 'storefront',
        group: '门店切换',
        meta: h,
      })
  })
  recentOrders.value.forEach((o) => {
    const t = (o.order_no + ' ' + (o.guest_name || '')).toLowerCase()
    if (t.includes(q))
      all.push({
        id: 'order:' + o.id,
        label: `订单 ${o.order_no} · ${o.guest_name || '散客'}`,
        icon: 'receipt_long',
        group: '订单',
        meta: o,
      })
  })
  recentGuests.value.forEach((g) => {
    const t = ((g.name || '') + ' ' + (g.phone || '') + ' ' + (g.one_id || '')).toLowerCase()
    if (t.includes(q))
      all.push({
        id: 'guest:' + g.id,
        label: `${g.name || '客人'} · ${g.phone || '—'}`,
        icon: 'person',
        group: '客户',
        meta: g,
      })
  })
  recentRooms.value.forEach((r) => {
    const t = (r.room_no + ' ' + (r.room_type_name || '')).toLowerCase()
    if (t.includes(q))
      all.push({
        id: 'room:' + r.id,
        label: `房间 ${r.room_no} · ${r.room_type_name || ''}`,
        icon: 'bed',
        group: '房间',
        meta: r,
      })
  })
  // 全站页面（按标题/域/路由匹配，限 40 条）
  let pc = 0
  for (const p of pageManifest) {
    if (pc >= 40) break
    const t = (p.title + ' ' + p.domain + ' ' + p.route).toLowerCase()
    if (t.includes(q)) {
      all.push({
        id: 'page:' + p.route,
        label: p.title + ' · ' + p.domain,
        icon: 'description',
        group: '全部页面',
        meta: p.route,
      })
      pc++
    }
  }
  return all
})

const grouped = computed(() => groupBy(combined.value, 'group'))

function show() {
  open.value = true
  selected.value = 0
  query.value = ''
  loadHotels()
}
function hide() {
  open.value = false
}
function toggle() {
  open.value ? hide() : show()
}
async function loadHotels() {
  hotels.value = await api.listHotels()
  recentOrders.value = await api.listOrders(hotelStore.hotelId)
  recentGuests.value = await api.listGuests(hotelStore.hotelId).catch(() => [])
  recentRooms.value = await api.listRooms(hotelStore.hotelId)
}

async function run(item: any) {
  hide()
  if (item.id.startsWith('go:')) {
    const GO: Record<string, string> = {
      'go:dashboard': '/',
      'go:crm': '/b-data/global-guest-directory',
      'go:pricing': '/pricing',
      'go:revenue-forecast': '/c9-finance/revenue-forecast',
      'go:orders': '/orders',
      'go:analytics': '/analytics?tab=insights',
      'go:acquisition': '/acquisition',
      'go:ai': '/ai',
      'go:housekeeping': '/c6-housekeeping/housekeeping',
      'go:assets': '/c8-assets/inventory-2',
      'go:finance': '/c9-finance/daily-operations',
      'go:room-board': '/room-board',
    }
    router.push(GO[item.id] || '/' + item.id.replace('go:', ''))
  } else if (item.id.startsWith('guest:')) {
    router.push('/guests/' + item.meta.id)
  } else if (item.id.startsWith('hotel:')) {
    hotelStore.hotelId = Number(item.id.split(':')[1])
    router.push('/dashboard')
  } else if (item.id.startsWith('order:')) {
    router.push('/orders/' + item.meta.id)
  } else if (item.id.startsWith('room:')) {
    router.push('/rooms/' + item.meta.id)
  } else if (item.id.startsWith('page:')) {
    router.push(item.meta)
  } else if (item.id === 'ai:audit') {
    const d = new Date().toISOString().slice(0, 10)
    const r = await api.runAudit({ hotel_id: hotelStore.hotelId, biz_date: d })
    alert(t('夜审已完成：营收 ¥') + Number(r.revenue).toFixed(0) + ' · 间夜 ' + r.room_nights)
    router.push('/finance')
  } else if (item.id === 'ai:new-order') {
    router.push('/orders')
  } else if (item.id === 'ai:accept-pricing') {
    router.push('/pricing')
  } else if (item.id === 'ai:dispatch-hk') {
    router.push('/housekeeping')
  }
}

function flatIndex(groupK: string, withinGroup: number, items: any[]) {
  let idx = 0
  for (const g of grouped.value) {
    if (g.k === groupK) return idx + withinGroup
    idx += g.items.length
  }
  return idx
}

function onKey(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    toggle()
  }
  if (open.value && e.key === 'Escape') hide()
}
onMounted(() => {
  document.addEventListener('keydown', onKey)
})

function onBackdrop(e: MouseEvent) {
  if (e.target === e.currentTarget) hide()
}

watch(query, () => {
  selected.value = 0
})

function onKeyNav(e: KeyboardEvent) {
  if (!open.value) return
  const list = combined.value
  if (e.key === 'ArrowDown') {
    selected.value = Math.min(selected.value + 1, list.length - 1)
  } else if (e.key === 'ArrowUp') {
    selected.value = Math.max(selected.value - 1, 0)
  } else if (e.key === 'Enter') {
    if (list[selected.value]) run(list[selected.value])
  }
}

defineExpose({ show, hide, toggle })
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        @click="onBackdrop"
        @keydown="onKeyNav"
        class="palette-backdrop"
        tabindex="-1"
      >
        <div class="palette" @click.stop>
          <div class="palette-search">
            <span class="ms" style="color: var(--tertiary)">auto_awesome</span>
            <input
              v-model="query"
              autofocus
              :placeholder="t('搜索页面、执行命令、或用一句话告诉 AI……')"
            />
            <span class="kbd">ESC</span>
          </div>
          <div class="palette-list">
            <template v-if="!combined.length">
              <div class="palette-empty">
                <span class="ms">search</span>
                <p>{{ t('没有匹配的命令。试试 “夜审”、“切店到北京” 或 “OTA 订单”') }}</p>
              </div>
            </template>
            <template v-else>
              <div v-for="g in grouped" :key="g.k">
                <div class="palette-group">{{ g.k }}</div>
                <div
                  v-for="(it, i) in g.items"
                  :key="it.id"
                  class="palette-item"
                  :class="{ active: flatIndex(g.k, i, g.items) === selected }"
                  @mouseenter="selected = flatIndex(g.k, i, g.items)"
                  @click="run(it)"
                >
                  <span class="ms">{{ it.icon }}</span>
                  <span style="flex: 1">{{ it.label }}</span>
                  <span class="kbd" style="position: static">↵</span>
                </div>
              </div>
            </template>
          </div>
          <div class="palette-foot">
            <span><span class="kbd">↑↓</span> {{ t('选择') }}</span>
            <span><span class="kbd">↵</span> {{ t('执行') }}</span>
            <span><span class="kbd">ESC</span> {{ t('关闭') }}</span>
            <span style="margin-left: auto; color: var(--tertiary)">
              <span class="ms" style="font-size: 14px; vertical-align: -2px">auto_awesome</span
              >{{ t('AI 能力需配置大模型') }}</span
            >
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.palette-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.32);
  z-index: 9999;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 12vh;
}
.palette {
  width: min(640px, 92vw);
  background: var(--surface-container-lowest, #fff);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.22);
  overflow: hidden;
  border: 1px solid var(--outline-variant);
}
.palette-search {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--outline-variant);
}
.palette-search .ms {
  font-family: 'Material Symbols Outlined';
  font-size: 22px;
  font-variation-settings:
    'FILL' 1,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
.palette-search input {
  flex: 1;
  border: 0;
  outline: 0;
  font-size: 16px;
  background: transparent;
  color: var(--on-surface);
  font-family: 'Source Sans 3', sans-serif;
}
.kbd {
  font-family: 'Roboto Mono', monospace;
  font-size: 11px;
  padding: 2px 6px;
  border: 1px solid var(--outline-variant);
  border-radius: 4px;
  color: var(--on-surface-variant);
}
.palette-list {
  max-height: 50vh;
  overflow-y: auto;
  padding: 8px 0;
}
.palette-empty {
  padding: 40px 24px;
  text-align: center;
  color: var(--on-surface-variant);
  font-size: 13px;
}
.palette-empty .ms {
  font-family: 'Material Symbols Outlined';
  font-size: 48px;
  display: block;
  margin: 0 auto 8px;
  opacity: 0.5;
}
.palette-group {
  padding: 8px 20px 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--on-surface-variant);
  letter-spacing: 0.5px;
}
.palette-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  cursor: pointer;
  font-size: 14px;
  color: var(--on-surface);
}
.palette-item .ms {
  font-family: 'Material Symbols Outlined';
  font-size: 18px;
  color: var(--on-surface-variant);
}
.palette-item.active {
  background: rgba(0, 91, 191, 0.08);
}
.palette-item.active .ms {
  color: var(--primary);
}
.palette-foot {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 16px;
  font-size: 11px;
  color: var(--on-surface-variant);
  border-top: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
}
.palette-foot .ms {
  font-family: 'Material Symbols Outlined';
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
