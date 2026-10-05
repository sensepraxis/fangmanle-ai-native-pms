// SPDX-License-Identifier: Apache-2.0
import { createRouter, createWebHashHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Rooms from './views/Rooms.vue'
import Orders from './views/Orders.vue'
import Pricing from './views/Pricing.vue'
import RoomBoard from './views/RoomBoard.vue'
import Acquisition from './views/Acquisition.vue'
import Ai from './views/Ai.vue'
import OrderDetail from './views/OrderDetail.vue'
import RoomDetail from './views/RoomDetail.vue'
import GuestDetail from './views/GuestDetail.vue'
import PricingDetail from './views/PricingDetail.vue'
import AuditDetail from './views/AuditDetail.vue'
import Login from './views/Login.vue'
import Landing from './views/Landing.vue'
import PageMap from './views/PageMap.vue'
import { generatedRoutes } from './routes.generated'
import { canAccessPath, domainHome, firstAllowedHome, rbacStore } from './store/rbac'
import { clearSession, ensureSession } from './store/hotel'
import { t } from './lib/i18n'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'landing', component: Landing, meta: { public: true } },
    { path: '/login', name: 'login', component: Login, meta: { public: true } },
    {
      path: '/wecom/care-sidebar',
      name: 'wecom-care-sidebar',
      component: () => import('./views/wecom/CareSidebar.vue'),
      meta: { public: true },
    },
    { path: '/overview', name: 'dashboard', component: Dashboard },
    { path: '/map', name: 'map', component: PageMap },
    { path: '/pricing', name: 'pricing', component: Pricing },
    { path: '/pricing/:id', name: 'pricing-detail', component: PricingDetail },
    { path: '/rooms', name: 'rooms', component: Rooms },
    { path: '/rooms/:id', name: 'room-detail', component: RoomDetail },
    { path: '/room-board', name: 'room-board', component: RoomBoard },
    { path: '/orders', name: 'orders', component: Orders },
    { path: '/orders/:id', name: 'order-detail', component: OrderDetail },
    {
      path: '/compliance',
      name: 'compliance',
      component: () => import('./views/Compliance.vue'),
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: () => import('./views/analytics/hub.vue'),
    },
    // 经营分析 IA：旧独立页 → Tab + query
    {
      path: '/analytics/order-health',
      redirect: { path: '/analytics', query: { tab: 'insights', section: 'health' } },
    },
    {
      path: '/analytics/order-health/churn-warning',
      redirect: { path: '/analytics', query: { tab: 'insights', section: 'health' } },
    },
    {
      path: '/analytics/channel-insight',
      redirect: { path: '/analytics', query: { tab: 'insights', section: 'channel' } },
    },
    {
      path: '/analytics/channel-insight/omni',
      redirect: { path: '/analytics', query: { tab: 'insights', section: 'channel' } },
    },
    {
      path: '/analytics/marketing-attribution',
      redirect: { path: '/analytics', query: { tab: 'insights', section: 'attribution' } },
    },
    {
      path: '/analytics/marketing-attribution/path',
      redirect: { path: '/analytics', query: { tab: 'insights', section: 'attribution' } },
    },
    {
      path: '/analytics/yield',
      redirect: '/analytics/yield/overview',
    },
    {
      path: '/analytics/room-status-history',
      redirect: '/room-board',
    },
    {
      path: '/analytics/yield/overview',
      name: 'analytics-yield-overview',
      component: () => import('./views/analytics/yield-overview.vue'),
    },
    // 旧路径 → 经营分析树（须在 generatedRoutes 之前）
    {
      path: '/c5-frontdesk/order-monitor',
      redirect: { path: '/analytics', query: { tab: 'insights', section: 'health' } },
    },
    {
      path: '/c5-frontdesk/order-monitor-2',
      redirect: { path: '/analytics', query: { tab: 'insights', section: 'health' } },
    },
    {
      path: '/c5-frontdesk/ai-new',
      redirect: { path: '/analytics', query: { tab: 'insights', section: 'channel' } },
    },
    {
      path: '/c5-frontdesk/order-attribution',
      redirect: { path: '/analytics', query: { tab: 'insights', section: 'attribution' } },
    },
    { path: '/c5-frontdesk/order-ops', redirect: '/analytics' },
    {
      path: '/c9-finance/profit-optimization-ai',
      redirect: { path: '/analytics', query: { tab: 'profit' } },
    },
    // 废弃：财务工作台 / 财务侧「经营分析」诊断页 / 收银台占位页
    { path: '/c9-finance/finance-dashboard', redirect: '/c9-finance/daily-operations' },
    {
      path: '/c9-finance/room-board',
      redirect: { path: '/analytics', query: { tab: 'insights' } },
    },
    { path: '/c9-finance/cash-register', redirect: '/c9-finance/deposit-management' },
    { path: '/finance', redirect: '/c9-finance/daily-operations' },
    { path: '/finance/audit/:biz_date', name: 'audit-detail', component: AuditDetail },
    { path: '/night-audit', redirect: '/c9-finance/night-audit' },
    {
      path: '/c9-finance/night-audit-cruise-control',
      redirect: '/c9-finance/night-audit',
    },
    // 夜审自动修复已并入夜间审计页下方
    {
      path: '/c9-finance/night-audit-auto-fix',
      redirect: { path: '/c9-finance/night-audit', query: { section: 'autofix' } },
    },
    { path: '/guests', redirect: '/b-data/global-guest-directory' },
    { path: '/guests/:id', name: 'guest-detail', component: GuestDetail },
    {
      path: '/b-data/one-id-audit',
      name: 'one-id-audit',
      component: () => import('./views/b-data/one-id-audit.vue'),
    },
    { path: '/crm', redirect: '/b-data/global-guest-directory' },
    {
      path: '/b-data/cohort-list',
      name: 'cohort-list',
      component: () => import('./views/b-data/cohort-list.vue'),
    },
    // 标签管理（库 + 打标规则）
    {
      path: '/b-data/tag-management',
      name: 'tag-management',
      component: () => import('./views/b-data/tag-management.vue'),
    },
    { path: '/b-data/tag-ecosystem-overview', redirect: '/b-data/tag-management' },
    { path: '/b-data/master-tag-library', redirect: '/b-data/tag-management' },
    { path: '/b-data/semantic-tag-rules', redirect: '/b-data/tag-management' },
    { path: '/b-data/guest-segmentation', redirect: '/b-data/tag-management' },
    // 客群数据漂移独立页已下线 → 客群列表（卡片「比对客群」抽屉）
    { path: '/b-data/comparison', redirect: '/b-data/cohort-list' },
    // 动态人群分群已下线 → 客群列表（AI 找人保存分群）
    { path: '/b-data/dynamic-customer-segmentation', redirect: '/b-data/cohort-list' },
    // 旧「动态分群」列表入口兼容：看客户侧统一到客群列表
    { path: '/b-data/guest-segments', redirect: '/b-data/cohort-list' },
    { path: '/b-data/guest-360-workspace', redirect: '/b-data/global-guest-directory' },
    { path: '/c4-reputation/ms-lin-vip', redirect: '/b-data/global-guest-directory' },
    { path: '/c4-reputation/in-stay-proactive-care', redirect: '/b-data/global-guest-directory' },
    {
      path: '/c3-acquisition/ota-reputation-management',
      redirect: '/b-data/global-guest-directory',
    },
    // 房态图统一主入口；其余同名 room-board 多为误命名原型页，勿再挂第二套房态
    { path: '/c5-frontdesk/room-board', redirect: '/room-board' },
    { path: '/c6-housekeeping/room-board-2', redirect: '/room-board' },
    // 房态控制台已下线 → 统一房态看板
    { path: '/c5-frontdesk/5.4.1_ai', redirect: '/room-board' },
    // 状态登记已下线 → 系统配置 · 房间档案
    { path: '/c5-frontdesk/ooo', redirect: '/a-ai-core/room-master' },
    // 房型配置迁至系统配置 · 房型管理
    { path: '/c5-frontdesk/room-asset-configuration', redirect: '/a-ai-core/room-type-management' },
    { path: '/rooms', redirect: '/a-ai-core/room-master' },
    // 营销获客新 IA：私域 / 公域投放 / AI种草 / 分群 / 活动（不再以小红书/抖音双频道入口）
    { path: '/c3-acquisition/room-board', redirect: '/acquisition/ai-seeding' },
    { path: '/c3-acquisition/room-board-2', redirect: '/acquisition/ai-seeding' },
    { path: '/c3-acquisition/ai-xiaohongshu-analytics', redirect: '/acquisition' },
    { path: '/c3-acquisition/xiaohongshu-native-analytics', redirect: '/acquisition' },
    { path: '/c3-acquisition/one-id', redirect: '/acquisition' },
    {
      path: '/c3-acquisition/content-ai',
      redirect: { path: '/acquisition', query: { tab: 'funnel' } },
    },
    { path: '/c3-acquisition/flow', redirect: { path: '/acquisition', query: { tab: 'funnel' } } },
    { path: '/c3-acquisition/douyin-acquisition', redirect: '/acquisition' },
    { path: '/c3-acquisition/poi', redirect: '/acquisition/ads' },
    { path: '/c3-acquisition/filter-list', redirect: '/acquisition/ads' },
    { path: '/c3-acquisition/auto-awesome-ai-active', redirect: '/acquisition/ads' },
    { path: '/c3-acquisition/geofencing', redirect: '/acquisition/ads' },
    { path: '/c3-acquisition/wecom-mini-program-direct-sales', redirect: '/acquisition' },
    {
      path: '/c4-reputation/roi',
      redirect: { path: '/acquisition', query: { tab: 'attribution' } },
    },
    { path: '/housekeeping', redirect: '/c6-housekeeping/housekeeping' },
    { path: '/dispatch', redirect: '/c6-housekeeping/housekeeping' },
    { path: '/campaigns', redirect: '/acquisition/coupons' },
    { path: '/acquisition', name: 'acquisition', component: Acquisition },
    { path: '/acquisition/ads', redirect: '/acquisition' },
    { path: '/acquisition/ai-seeding', redirect: '/acquisition' },
    { path: '/acquisition/segments', redirect: '/acquisition' },
    { path: '/acquisition/campaigns', redirect: '/acquisition/coupons' },
    { path: '/acquisition/coupons', name: 'acquisition-coupons', component: Acquisition },
    { path: '/acquisition/landing-pages', name: 'acquisition-landing', component: Acquisition },
    { path: '/acquisition/customers', redirect: '/acquisition' },
    { path: '/acquisition/members', name: 'acquisition-members', component: Acquisition },
    { path: '/acquisition/points', name: 'acquisition-points', component: Acquisition },
    {
      path: '/acquisition/automation',
      redirect: { path: '/acquisition/coupons', query: { tab: 'grant', sub: 'rules' } },
    },
    { path: '/acquisition/mini-program', redirect: '/acquisition' },
    { path: '/ai', name: 'ai', component: Ai },
    // 自然语言客史搜索 / 客群查询，统一并入客群运营工作台
    { path: '/b-data/search', redirect: '/b-data/cohort-list' },
    { path: '/b-data/top-50', redirect: '/b-data/cohort-list' },
    // 深度偏好关联已下线
    { path: '/b-data/top-5', redirect: '/b-data/cohort-list' },
    // 即时客情预测已废弃，回流配置客群
    { path: '/b-data/prediction', redirect: '/b-data/tag-management' },
    // OTA 口碑监测已下线（generated 路由会被上面的 redirect 抢先）
    {
      path: '/c9-finance/shift-handover/handover',
      name: 'c9-finance-shift-handover-handover',
      component: () => import('./views/c9-finance/shift-handover.vue'),
    },
    {
      path: '/c9-finance/shift-handover/takeover',
      name: 'c9-finance-shift-handover-takeover',
      component: () => import('./views/c9-finance/shift-takeover.vue'),
    },
    {
      path: '/c9-finance/shift-handover',
      redirect: (to) => {
        if (String(to.query.view || '') === 'bench') {
          return { path: '/c9-finance/shift-handover/takeover' }
        }
        return { path: '/c9-finance/shift-handover/handover' }
      },
    },
    // OTA 佣金已并入财务参数三级 Tab
    {
      path: '/a-ai-core/ota-commission',
      redirect: { path: '/a-ai-core/finance-params-float-carry', query: { tab: 'ota' } },
    },
    // 已下线悬空页：旧书签回流可达页
    {
      path: '/c6-housekeeping/ai-vision-analysis',
      redirect: '/c6-housekeeping/view-full-incident-log',
    },
    {
      path: '/c6-housekeeping/8201-vip',
      redirect: '/c6-housekeeping/in-stay-guest-request-management',
    },
    { path: '/c7-supplies/ai-rca', redirect: '/overview' },
    ...generatedRoutes,
    // 物资耗材已下线：旧路径统一回首页
    { path: '/c7-supplies/:pathMatch(.*)*', redirect: '/overview' },
    // 资产价值页：从房务路径迁至设备设施（直达现用页）
    {
      path: '/c6-housekeeping/asset-value-replacement',
      redirect: '/c8-assets/loss-analysis-replacement-strategy',
    },
    { path: '/c6-housekeeping/b-wing-b', redirect: '/c8-assets/inventory-2' },
    // 预防性维护页已废弃，旧链回流设备总览
    { path: '/c6-housekeeping/inventory-2', redirect: '/c8-assets/inventory-2' },
    {
      path: '/c8-assets/damage-registration',
      name: 'c8-assets-damage-registration',
      component: () => import('./views/c7-supplies/damage-registration.vue'),
    },
    {
      path: '/c8-assets/asset-procurement',
      redirect: (to) => ({
        path: '/c8-assets/inventory-2',
        query: {
          action: 'register',
          ...(to.query.replace_asset_id ? { replace_asset_id: to.query.replace_asset_id } : {}),
        },
      }),
    },
    {
      path: '/c8-assets/assets/:id',
      name: 'c8-assets-profile',
      component: () => import('./views/c8-assets/asset-profile.vue'),
    },
    // 旧履历页 → 资产画像
    {
      path: '/c8-assets/lifecycle',
      redirect: (to) => {
        const id = to.query.asset_id
        return id ? `/c8-assets/assets/${id}` : '/c8-assets/inventory-2'
      },
    },
    { path: '/c8-assets/lifecycle-2', redirect: '/c8-assets/inventory-2' },
    { path: '/c8-assets/asset-profile', redirect: '/c8-assets/inventory-2' },
    // 易耗库存水位随物资耗材下线
    { path: '/c8-assets/inventory-2-stock-levels', redirect: '/overview' },
    // 旧设备设施页面收敛到资产清单 / 报损分析
    { path: '/c8-assets/asset-health-overview', redirect: '/c8-assets/inventory-2' },
    { path: '/c8-assets/repair-replace', redirect: '/c8-assets/inventory-2' },
    {
      path: '/c8-assets/asset-value-replacement',
      redirect: '/c8-assets/loss-analysis-replacement-strategy',
    },
    { path: '/c8-assets/b-wing-b', redirect: '/c8-assets/inventory-2' },
    { path: '/c8-assets/key-assets', redirect: '/c8-assets/inventory-2' },
    { path: '/c8-assets/inventory-overview', redirect: '/c8-assets/inventory-2' },
    { path: '/c8-assets/audit', redirect: '/c8-assets/inventory-2' },
    {
      path: '/c6-housekeeping/long-term-maintenance-schedule-oct-2023',
      redirect: { path: '/c8-assets/tracking', query: { view: 'calendar' } },
    },
    { path: '/c6-housekeeping/arrow-forward-2', redirect: '/c8-assets/inventory-2' },
    { path: '/:pathMatch(.*)*', redirect: '/overview' },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true

  if (!localStorage.getItem('fml_token')) {
    clearSession()
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // 首次进入或会话未校验：请求 /auth/me；失败则回登录页
  if (!rbacStore.loaded) {
    const ok = await ensureSession()
    if (!ok) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }

  const path = to.path || '/'
  if (!canAccessPath(path)) {
    if (path.startsWith('/a-ai-core/')) {
      for (const g of ['system', 'extensions'] as const) {
        const alt = (domainHome(g) || '/').split('?')[0]
        if (alt && alt !== path && canAccessPath(alt)) return alt
      }
    }
    return firstAllowedHome()
  }
  return true
})

export default router
