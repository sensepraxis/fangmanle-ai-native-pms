<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { hasAnyMenu, SIDEBAR_GROUPS, domainHome } from '../store/rbac'
import { t } from '../lib/i18n'
import { packUiRev } from '../lib/branding'

const OVERVIEW_PATHS = ['/pricing', '/c9-finance/revenue-forecast']

const NAV_KEYS = [
  {
    to: '/overview',
    match: '/overview',
    labelKey: 'nav.overview',
    labelZh: '经营总览',
    icon: 'dashboard',
    group: 'overview',
  },
  {
    to: '/orders',
    labelKey: 'nav.orders',
    labelZh: '订单管理',
    icon: 'receipt_long',
    group: 'orders',
  },
  {
    to: '/room-board',
    match: '/room-board',
    labelKey: 'nav.rooms',
    labelZh: '房务与房态',
    icon: 'calendar_view_day',
    group: 'rooms',
  },
  {
    to: '/b-data/global-guest-directory',
    match: '/member-crm',
    labelKey: 'nav.crm',
    labelZh: '客户会员',
    icon: 'share_reviews',
    group: 'crm',
  },
  {
    to: '/analytics?tab=insights',
    match: '/analytics',
    labelKey: 'nav.analytics',
    labelZh: '数据洞察',
    icon: 'monitoring',
    group: 'analytics',
  },
  {
    to: '/c9-finance/daily-operations',
    match: '/c9-finance',
    labelKey: 'nav.finance',
    labelZh: '财务管理',
    icon: 'payments',
    group: 'finance',
  },
  {
    to: '/acquisition',
    match: '/acquisition',
    labelKey: 'nav.mkt',
    labelZh: '私域运营',
    icon: 'groups',
    group: 'mkt',
  },
  {
    to: '/a-ai-core/finance-params-float-carry',
    match: '/a-ai-core/finance-params-float-carry',
    labelKey: 'nav.system',
    labelZh: '系统配置',
    icon: 'tune',
    iconTone: 'danger' as const,
    group: 'system',
  },
  {
    to: '/a-ai-core/ai-system-configuration',
    match: '/a-ai-core/ai-system-configuration',
    labelKey: 'nav.extensions',
    labelZh: '扩展能力',
    icon: 'extension',
    iconTone: 'primary' as const,
    group: 'extensions',
  },
]

const tick = ref(0)
function onLocale() {
  tick.value++
}
onMounted(() => window.addEventListener('fml:locale', onLocale))
onUnmounted(() => window.removeEventListener('fml:locale', onLocale))

const NAV = computed(() => {
  tick.value
  packUiRev.value
  return NAV_KEYS.filter((n) => hasAnyMenu(SIDEBAR_GROUPS[n.group] || [])).map((n) => {
    const byKey = t(n.labelKey)
    return {
      ...n,
      // 稳定 key 优先；缺失时再走中文 msgid，避免 EN 下误显中文 labelZh 原文
      label: byKey && byKey !== n.labelKey ? byKey : t(n.labelZh),
      to: domainHome(n.group) || n.to,
    }
  })
})

const route = useRoute()
const current = computed(() => route.path)

const ROOM_BOARD_FROM_HK: string[] = []
const ROOM_OPS_EXTRA = [
  '/c5-frontdesk/smart-inventory',
  '/c6-housekeeping',
  '/housekeeping',
  '/c8-assets',
]
const ORDERS_EXTRA = [
  '/c5-frontdesk/orders',
  '/c5-frontdesk/voucher-verification',
  '/c5-frontdesk/walk-in-quick-check-in',
  '/c5-frontdesk/front-desk-booking',
  '/c5-frontdesk/group-booking',
  '/c5-frontdesk/filter',
  '/c5-frontdesk/agreement-corp',
  '/c5-frontdesk/engine',
  '/c5-frontdesk/pending-assignment',
  '/c5-frontdesk/cashiering-checkout',
  '/c5-frontdesk/zhang-san',
]
const ANALYTICS_EXTRA = ['/analytics', '/c2-risk', '/ai']
const ACQUISITION_ATTR = [
  '/c4-reputation/roi',
  '/c4-reputation/download',
  '/c4-reputation/one-id-tracing-path-to-purchase',
  '/campaigns',
]
const MEMBER_BDATA = [
  '/b-data/one-id-resolution',
  '/b-data/one-id',
  '/b-data/ai-high-confidence-94',
  '/b-data/consolidated-asset-confirmation',
  '/b-data/data-source-lineage',
  '/b-data/global-guest-directory',
  '/b-data/cohort-list',
  '/b-data/guest-360-workspace',
  '/b-data/life-time-value',
  '/b-data/ltv',
  '/b-data/f-ngm-nl-pms',
  '/b-data/ota',
  '/b-data/master-tag-library',
  '/b-data/tag-ecosystem-overview',
  '/b-data/tag-management',
  '/b-data/semantic-tag-rules',
  '/b-data/guest-segmentation',
  '/b-data/top-50',
  '/b-data/top-50-2',
  '/b-data/ai-auto-awesome',
  '/guests',
]

function pathHit(list: string[]) {
  return list.some(
    (p) => current.value === p || current.value.startsWith(p + '/') || current.value.startsWith(p),
  )
}

function isActive(n: { to: string; match?: string; label?: string; group?: string }) {
  if (n.match === '/c9-finance' && current.value === '/c9-finance/revenue-forecast') return false
  if (n.match === '/c9-finance') {
    if (current.value === '/finance' || current.value.startsWith('/finance/')) return true
    if (current.value === '/c5-frontdesk/float' || current.value === '/c5-frontdesk/5.5.3.1')
      return true
  }
  if (n.group === 'orders' || n.to === '/orders') {
    if (current.value === '/orders' || current.value.startsWith('/orders/')) return true
    if (ORDERS_EXTRA.some((p) => current.value === p || current.value.startsWith(p))) return true
  }
  if (n.to === '/analytics' || n.match === '/analytics' || n.group === 'analytics') {
    if (ANALYTICS_EXTRA.some((p) => current.value === p || current.value.startsWith(p))) return true
  }
  if (n.group === 'rooms' || n.to === '/room-board' || n.match === '/room-board') {
    if (current.value === '/room-board' || current.value.startsWith('/room-board/')) return true
    if (ROOM_OPS_EXTRA.some((p) => current.value === p || current.value.startsWith(p))) return true
    if (ROOM_BOARD_FROM_HK.some((p) => current.value === p || current.value.startsWith(p)))
      return true
  }
  if (n.group === 'system') {
    const SYS = [
      '/a-ai-core/finance-params-float-carry',
      '/a-ai-core/ota-commission',
      '/a-ai-core/room-type-management',
      '/a-ai-core/room-master',
      '/a-ai-core/users',
      '/a-ai-core/rbac',
      '/c5-frontdesk/room-asset-configuration',
    ]
    if (SYS.some((p) => current.value === p || current.value.startsWith(p))) return true
  }
  if (n.group === 'extensions') {
    const EXT = [
      '/a-ai-core/private-channel',
      '/a-ai-core/wecom-integration',
      '/a-ai-core/ai-system-configuration',
      '/a-ai-core/map-config',
    ]
    if (EXT.some((p) => current.value === p || current.value.startsWith(p))) return true
  }
  if (n.group === 'mkt' || n.to === '/acquisition') {
    if (current.value === '/acquisition' || current.value.startsWith('/acquisition/')) return true
    if (current.value === '/campaigns' || current.value.startsWith('/campaigns/')) return true
    if (current.value.startsWith('/c3-acquisition')) return true
    return false
  }
  if (n.group === 'crm' || n.match === '/member-crm') {
    if (current.value === '/crm' || current.value.startsWith('/crm/')) return true
    if (current.value === '/guests' || current.value.startsWith('/guests/')) return true
    if (pathHit(MEMBER_BDATA)) return true
    if (current.value.startsWith('/c4-reputation')) {
      if (pathHit(ACQUISITION_ATTR)) return false
      return true
    }
  }
  if (n.group === 'overview' || n.match === '/overview' || n.to === '/overview') {
    if (current.value === '/overview') return true
    if (OVERVIEW_PATHS.some((p) => current.value === p || current.value.startsWith(p + '/')))
      return true
    return false
  }
  const prefix = n.match || n.to
  return (
    current.value === n.to || current.value === prefix || current.value.startsWith(prefix + '/')
  )
}
</script>

<template>
  <aside class="rail">
    <nav class="nav">
      <RouterLink
        v-for="n in NAV"
        :key="n.group || n.to"
        :to="n.to"
        class="nav-item"
        :class="{ active: isActive(n) }"
      >
        <span
          class="nav-ico material-symbols-outlined"
          :class="{
            'nav-ico-danger': n.iconTone === 'danger',
            'nav-ico-primary': n.iconTone === 'primary',
          }"
          >{{ n.icon }}</span
        >
        <span class="nav-label">{{ n.label }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>
