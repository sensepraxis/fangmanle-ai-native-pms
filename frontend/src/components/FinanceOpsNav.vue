<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 财务管理 · 四个一级（固定顺序靠左）+ 二级（下划线 Tab）
 * 日常收银 / 班次交接 / 对账与结算 / 财务报表
 */
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { hasMenu } from '../store/rbac'

const route = useRoute()
const router = useRouter()
const localeTick = ref(0)
function onLocale() {
  localeTick.value++
}
onMounted(() => window.addEventListener('fml:locale', onLocale))
onUnmounted(() => window.removeEventListener('fml:locale', onLocale))

type Leaf = {
  label: string
  icon: string
  path: string
  query?: Record<string, string>
  menu?: string
}

type Section = {
  key: string
  label: string
  icon: string
  defaultPath: string
  defaultQuery?: Record<string, string>
  children: Leaf[]
  matchPaths: string[]
  menu?: string
}

const SECTIONS_ALL: Section[] = [
  {
    key: 'cashier',
    label: '日常收银',
    icon: 'point_of_sale',
    defaultPath: '/c9-finance/deposit-management',
    matchPaths: ['/c9-finance/deposit-management', '/c9-finance/refund-adjustment'],
    children: [
      {
        label: '押金管理',
        icon: 'savings',
        path: '/c9-finance/deposit-management',
        menu: 'menu.finance.deposit',
      },
      {
        label: '退改与反结账',
        icon: 'undo',
        path: '/c9-finance/refund-adjustment',
        menu: 'menu.finance.refund',
      },
    ],
  },
  {
    key: 'shift',
    label: '班次交接',
    icon: 'swap_horiz',
    defaultPath: '/c9-finance/shift-handover/handover',
    menu: 'menu.finance.shift',
    matchPaths: [
      '/c9-finance/shift-handover/handover',
      '/c9-finance/shift-handover/takeover',
      '/c9-finance/shift-handover',
      '/c5-frontdesk/float',
      '/c5-frontdesk/5.5.3.1',
    ],
    children: [
      {
        label: '交班',
        icon: 'logout',
        path: '/c9-finance/shift-handover/handover',
        menu: 'menu.finance.shift',
      },
      {
        label: '接班',
        icon: 'login',
        path: '/c9-finance/shift-handover/takeover',
        menu: 'menu.finance.shift',
      },
    ],
  },
  {
    key: 'settle',
    label: '对账与结算',
    icon: 'account_balance',
    defaultPath: '/c9-finance/night-audit',
    matchPaths: [
      '/c9-finance/night-audit',
      '/c9-finance/night-audit-auto-fix',
      '/c9-finance/smart-reconciliation',
      '/c9-finance/pms',
      '/c9-finance/happy-house',
      '/c9-finance/ar-ap',
    ],
    children: [
      {
        label: '夜间审计',
        icon: 'nightlight',
        path: '/c9-finance/night-audit',
        menu: 'menu.finance.night_audit',
      },
      {
        label: '财务对账',
        icon: 'sync_alt',
        path: '/c9-finance/smart-reconciliation',
        menu: 'menu.finance.recon',
      },
      {
        label: '发票管理',
        icon: 'receipt_long',
        path: '/c9-finance/happy-house',
        menu: 'menu.finance.invoice',
      },
      {
        label: '应收应付',
        icon: 'request_quote',
        path: '/c9-finance/ar-ap',
        menu: 'menu.finance.ar_ap',
      },
    ],
  },
  {
    key: 'reports',
    label: '财务报表',
    icon: 'description',
    defaultPath: '/c9-finance/daily-operations',
    menu: 'menu.finance.reports',
    matchPaths: ['/c9-finance/daily-operations'],
    children: [],
  },
]

const SECTIONS = computed(() => {
  localeTick.value
  return SECTIONS_ALL.map((s) => {
    const children = s.children.filter((c) => !c.menu || hasMenu(c.menu))
    if (s.menu && !hasMenu(s.menu) && !children.length) return null
    if (s.children.length && !children.length && !s.menu) return null
    if (s.menu && !hasMenu(s.menu) && s.children.length === 0) return null
    return {
      ...s,
      children,
      defaultPath: children[0]?.path || s.defaultPath,
    }
  }).filter(Boolean) as Section[]
})

function normalize(p: string) {
  return (p || '').replace(/\/+$/, '') || '/'
}

function sectionMatch(s: Section, cur: string) {
  return s.matchPaths.some((p) => cur === normalize(p) || cur.startsWith(normalize(p) + '/'))
}

const reportsSection = computed(
  () => SECTIONS.value.find((s) => s.key === 'reports') || SECTIONS.value[0],
)

const activeSection = computed(() => {
  const cur = normalize(route.path)
  return SECTIONS.value.find((s) => sectionMatch(s, cur)) || reportsSection.value
})

function leafActive(leaf: Leaf) {
  return normalize(route.path) === normalize(leaf.path)
}

function goSection(s: Section) {
  if (s.defaultQuery) router.push({ path: s.defaultPath, query: s.defaultQuery })
  else router.push(s.defaultPath)
}

function goLeaf(leaf: Leaf) {
  if (leaf.query) router.push({ path: leaf.path, query: leaf.query })
  else router.push(leaf.path)
}
</script>

<template>
  <nav
    class="fin-ops-nav"
    :class="{ 'has-sub': activeSection.children.length }"
    :aria-label="t('财务管理')"
  >
    <button
      v-for="s in SECTIONS"
      :key="s.key"
      type="button"
      class="tab"
      :class="{ on: activeSection.key === s.key }"
      @click="goSection(s)"
    >
      <span class="material-symbols-outlined">{{ s.icon }}</span>
      {{ t(s.label) }}
    </button>
  </nav>
  <nav v-if="activeSection.children.length" class="fin-subnav" :aria-label="t('财务管理二级')">
    <button
      v-for="c in activeSection.children"
      :key="c.label"
      type="button"
      class="subtab"
      :class="{ on: leafActive(c) }"
      @click="goLeaf(c)"
    >
      {{ t(c.label) }}
    </button>
  </nav>
</template>

<style scoped>
.fin-ops-nav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 4px;
  background: #f3f4f6;
  border-radius: 12px;
  margin-bottom: 24px;
  box-sizing: border-box;
}
.fin-ops-nav.has-sub {
  margin-bottom: 4px;
}
.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  border-radius: 9px;
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #5b616e;
  cursor: pointer;
}
.tab .material-symbols-outlined {
  font-size: 18px;
}
.tab:hover {
  background: #fff;
  color: #1f2329;
}
.tab.on {
  background: #1f2329;
  color: #fff;
}

.fin-subnav {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin-bottom: 24px;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 2px;
}
.subtab {
  border: none;
  background: transparent;
  padding: 10px 14px 11px;
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  border-radius: 0;
}
.subtab:hover {
  color: #1f2329;
}
.subtab.on {
  color: #1f2329;
  border-bottom-color: #1f2329;
  background: transparent;
}
</style>
