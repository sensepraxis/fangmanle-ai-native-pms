// SPDX-License-Identifier: Apache-2.0
/** 前端 RBAC：菜单/操作权限（以后端 /me 为准，改权限后即时刷新） */
import { reactive } from 'vue'
import { t } from '../lib/i18n'
import { isMenuHiddenByPack } from '../lib/branding'

/** 路径前缀 → 二级菜单 code（更长前缀优先） */
export const MENU_PATH_RULES: { prefix: string; menu: string }[] = [
  { prefix: '/a-ai-core/users', menu: 'menu.system.users' },
  { prefix: '/a-ai-core/rbac', menu: 'menu.system.rbac' },
  { prefix: '/a-ai-core/private-channel', menu: 'menu.system.wecom' },
  { prefix: '/a-ai-core/wecom-integration', menu: 'menu.system.wecom' },
  { prefix: '/a-ai-core/ai-system-configuration', menu: 'menu.system.llm' },
  { prefix: '/a-ai-core/map-config', menu: 'menu.system.map' },
  { prefix: '/a-ai-core/finance-params-float-carry', menu: 'menu.system.finance_params' },
  { prefix: '/a-ai-core/ota-commission', menu: 'menu.system.finance_params' },
  { prefix: '/a-ai-core/room-type-management', menu: 'menu.system.room_types' },
  { prefix: '/a-ai-core/room-master', menu: 'menu.system.room_master' },
  { prefix: '/pricing', menu: 'menu.overview.pricing' },
  { prefix: '/c9-finance/revenue-forecast', menu: 'menu.overview.forecast' },
  { prefix: '/c5-frontdesk/pending-assignment', menu: 'menu.orders.assign' },
  { prefix: '/c5-frontdesk/cashiering-checkout', menu: 'menu.orders.checkout' },
  { prefix: '/c5-frontdesk/voucher-verification', menu: 'menu.orders.checkout' },
  { prefix: '/c5-frontdesk/walk-in-quick-check-in', menu: 'menu.orders.booking' },
  { prefix: '/c5-frontdesk/front-desk-booking', menu: 'menu.orders.booking' },
  { prefix: '/c5-frontdesk/group-booking', menu: 'menu.orders.booking' },
  { prefix: '/c5-frontdesk/agreement-corp', menu: 'menu.orders.booking' },
  { prefix: '/c5-frontdesk/engine', menu: 'menu.orders.booking' },
  { prefix: '/orders', menu: 'menu.orders.center' },
  { prefix: '/c5-frontdesk/orders', menu: 'menu.orders.center' },
  { prefix: '/room-board', menu: 'menu.rooms.board' },
  { prefix: '/c6-housekeeping/reports', menu: 'menu.rooms.hk_reports' },
  { prefix: '/c6-housekeeping', menu: 'menu.rooms.hk' },
  { prefix: '/c5-frontdesk/smart-inventory', menu: 'menu.rooms.inventory' },
  { prefix: '/c8-assets', menu: 'menu.rooms.assets' },
  { prefix: '/b-data/global-guest-directory', menu: 'menu.crm.directory' },
  { prefix: '/guests', menu: 'menu.crm.directory' },
  { prefix: '/b-data/cohort-list', menu: 'menu.crm.cohort' },
  { prefix: '/b-data/one-id', menu: 'menu.crm.oneid' },
  { prefix: '/b-data/ai-high-confidence', menu: 'menu.crm.oneid' },
  { prefix: '/b-data/consolidated-asset', menu: 'menu.crm.oneid' },
  { prefix: '/b-data/tag-management', menu: 'menu.crm.tags' },
  { prefix: '/b-data/master-tag', menu: 'menu.crm.tags' },
  { prefix: '/b-data/semantic-tag', menu: 'menu.crm.tags' },
  { prefix: '/analytics', menu: 'menu.analytics.insights' },
  { prefix: '/ai', menu: 'menu.analytics.ai' },
  { prefix: '/c9-finance/deposit-management', menu: 'menu.finance.deposit' },
  { prefix: '/c9-finance/refund-adjustment', menu: 'menu.finance.refund' },
  { prefix: '/c9-finance/shift-handover', menu: 'menu.finance.shift' },
  { prefix: '/c9-finance/night-audit', menu: 'menu.finance.night_audit' },
  { prefix: '/c9-finance/smart-reconciliation', menu: 'menu.finance.recon' },
  { prefix: '/c9-finance/happy-house', menu: 'menu.finance.invoice' },
  { prefix: '/c9-finance/ar-ap', menu: 'menu.finance.ar_ap' },
  { prefix: '/c9-finance/daily-operations', menu: 'menu.finance.reports' },
  { prefix: '/acquisition/coupons', menu: 'menu.mkt.coupons' },
  { prefix: '/acquisition/landing-pages', menu: 'menu.mkt.landing' },
  { prefix: '/acquisition/members', menu: 'menu.mkt.members' },
  { prefix: '/acquisition/points', menu: 'menu.mkt.points' },
  { prefix: '/acquisition', menu: 'menu.mkt.overview' },
  { prefix: '/overview', menu: 'menu.overview.dashboard' },
]

export const SIDEBAR_GROUPS: Record<string, string[]> = {
  overview: ['menu.overview.dashboard', 'menu.overview.pricing', 'menu.overview.forecast'],
  orders: [
    'menu.orders.center',
    'menu.orders.booking',
    'menu.orders.assign',
    'menu.orders.checkout',
  ],
  rooms: [
    'menu.rooms.board',
    'menu.rooms.hk',
    'menu.rooms.inventory',
    'menu.rooms.assets',
    'menu.rooms.hk_reports',
  ],
  crm: ['menu.crm.directory', 'menu.crm.cohort', 'menu.crm.oneid', 'menu.crm.tags'],
  analytics: ['menu.analytics.insights', 'menu.analytics.profit', 'menu.analytics.ai'],
  finance: [
    'menu.finance.deposit',
    'menu.finance.refund',
    'menu.finance.shift',
    'menu.finance.night_audit',
    'menu.finance.recon',
    'menu.finance.invoice',
    'menu.finance.ar_ap',
    'menu.finance.reports',
  ],
  mkt: [
    'menu.mkt.overview',
    'menu.mkt.coupons',
    'menu.mkt.landing',
    'menu.mkt.members',
    'menu.mkt.points',
  ],
  system: [
    'menu.system.finance_params',
    'menu.system.room_types',
    'menu.system.room_master',
    'menu.system.users',
    'menu.system.rbac',
  ],
  extensions: ['menu.system.llm', 'menu.system.map', 'menu.system.wecom'],
}

/** 一级域默认落地页 */
export const DOMAIN_HOME: Record<string, string> = {
  overview: '/overview',
  orders: '/orders',
  rooms: '/room-board',
  crm: '/b-data/global-guest-directory',
  analytics: '/analytics?tab=insights',
  finance: '/c9-finance/daily-operations',
  mkt: '/acquisition',
  system: '/a-ai-core/finance-params-float-carry',
  extensions: '/a-ai-core/ai-system-configuration',
}

const SYSTEM_LANDING: { menu: string; path: string }[] = [
  { menu: 'menu.system.finance_params', path: '/a-ai-core/finance-params-float-carry' },
  { menu: 'menu.system.room_types', path: '/a-ai-core/room-type-management' },
  { menu: 'menu.system.room_master', path: '/a-ai-core/room-master' },
  { menu: 'menu.system.users', path: '/a-ai-core/users' },
  { menu: 'menu.system.rbac', path: '/a-ai-core/rbac' },
]

const EXTENSIONS_LANDING: { menu: string; path: string }[] = [
  { menu: 'menu.system.llm', path: '/a-ai-core/ai-system-configuration' },
  { menu: 'menu.system.map', path: '/a-ai-core/map-config' },
  { menu: 'menu.system.wecom', path: '/a-ai-core/private-channel' },
]

export const rbacStore = reactive({
  role: '' as string,
  menus: [] as string[],
  scopes: [] as string[],
  loaded: false,
})

export function applyRbac(data: { role?: string; menus?: string[]; scopes?: string[] }) {
  rbacStore.role = data.role || ''
  rbacStore.menus = Array.isArray(data.menus) ? [...data.menus] : []
  rbacStore.scopes = Array.isArray(data.scopes) ? [...data.scopes] : []
  rbacStore.loaded = true
}

export function clearRbac() {
  rbacStore.role = ''
  rbacStore.menus = []
  rbacStore.scopes = []
  rbacStore.loaded = false
}

export function hasMenu(code: string): boolean {
  if (isMenuHiddenByPack(code)) return false
  if (rbacStore.role === 'admin') return true
  if (!rbacStore.loaded) return true // 未加载前不误伤（登录页）
  return rbacStore.menus.includes(code)
}

export function hasScope(code: string): boolean {
  if (rbacStore.role === 'admin') return true
  if (!rbacStore.loaded) return true
  return rbacStore.scopes.includes(code) || rbacStore.menus.includes(code)
}

export function hasAnyMenu(codes: string[]): boolean {
  const vis = codes.filter((c) => !isMenuHiddenByPack(c))
  if (!vis.length) return false
  if (rbacStore.role === 'admin') return true
  if (!rbacStore.loaded) return true
  return vis.some((c) => rbacStore.menus.includes(c))
}

export function canAccessPath(path: string): boolean {
  const p = (path || '/').split('?')[0].replace(/\/+$/, '') || '/'
  for (const rule of MENU_PATH_RULES) {
    const pref = rule.prefix.replace(/\/+$/, '') || '/'
    let hit = false
    if (pref === '/') {
      hit = p === '/'
    } else {
      hit = p === pref || p.startsWith(pref + '/')
    }
    if (!hit) continue
    if (isMenuHiddenByPack(rule.menu)) return false
    if (rbacStore.role === 'admin') return true
    if (!rbacStore.loaded) return true
    return hasMenu(rule.menu)
  }
  return true
}

export function domainHome(group: string): string {
  const landing =
    group === 'system' ? SYSTEM_LANDING : group === 'extensions' ? EXTENSIONS_LANDING : null
  if (landing) {
    for (const row of landing) {
      if (hasMenu(row.menu)) return row.path
    }
  }
  return DOMAIN_HOME[group] || '/overview'
}

export function firstAllowedHome(): string {
  const order = [
    'overview',
    'orders',
    'rooms',
    'crm',
    'analytics',
    'finance',
    'mkt',
    'system',
    'extensions',
  ]
  for (const d of order) {
    if (hasAnyMenu(SIDEBAR_GROUPS[d] || [])) return domainHome(d)
  }
  return '/login'
}

/** 二级入口：按 menu code 过滤 */
export function filterByMenu<T extends { menu?: string }>(items: T[]): T[] {
  return items.filter((i) => !i.menu || hasMenu(i.menu))
}
