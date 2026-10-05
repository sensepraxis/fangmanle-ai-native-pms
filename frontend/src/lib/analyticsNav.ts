// SPDX-License-Identifier: Apache-2.0
/**
 * 数据洞察信息架构
 *
 * 一级「数据洞察」（/analytics）
 * ├── 专题洞察 — 渠道洞察 / 订单健康 / 营销归因
 * ├── 利润优化
 * └── AI 问数（/ai）
 *
 * 财务管理入口 = 财务报表（/c9-finance/daily-operations）
 */
export const ANALYTICS_PATH = '/analytics'

export type AnalyticsLeaf = {
  key: string
  title: string
  path: string
  /** 实际页面组件路由（可能与 path 相同） */
  pagePath: string
  icon: string
  /** 价值标签 */
  badge?: string
  /** 后置 / 规划中 */
  muted?: boolean
  /** 一句话价值（文档要点） */
  valueNote?: string
}

export type AnalyticsBranch = {
  key: string
  /** 一级栏目名，如「订单健康」 */
  title: string
  /** 副标题，如「风险预警」 */
  subtitle: string
  path: string
  icon: string
  hint: string
  leaves: AnalyticsLeaf[]
}

export const ANALYTICS_TREE: AnalyticsBranch[] = [
  {
    key: 'health',
    title: '订单健康',
    subtitle: '风险预警',
    path: '/analytics/order-health',
    icon: 'health_and_safety',
    hint: '内部数据闭环 · 催款 / 跟进 / 调政策 · 优先落地',
    leaves: [
      {
        key: 'churn-warning',
        title: '异常与流失预警',
        path: '/analytics/order-health/churn-warning',
        pagePath: '/analytics/order-health/churn-warning',
        icon: 'warning',
        badge: '优先',
        valueNote: '取消/支付/No-show 全在 PMS 内；可联动企微生成前台跟进任务',
      },
    ],
  },
  {
    key: 'channel',
    title: '渠道洞察',
    subtitle: '收益策略',
    path: '/analytics/channel-insight',
    icon: 'insights',
    hint: '价格弹性 · ADR vs 取消 · 依赖价格历史与渠道标签',
    leaves: [
      {
        key: 'omni-insight',
        title: '全渠道订单洞察',
        path: '/analytics/channel-insight/omni',
        pagePath: '/analytics/channel-insight/omni',
        icon: 'analytics',
        badge: '高价值',
        valueNote: '收益管理/渠道策略工具；数据质量不足会成样子货',
      },
    ],
  },
  {
    key: 'attribution',
    title: '营销归因',
    subtitle: '触点 ROI',
    path: '/analytics/marketing-attribution',
    icon: 'route',
    hint: '需小红书/抖音/OTA 流量数据 · MVP 后置',
    leaves: [
      {
        key: 'path-attr',
        title: '订单渠道归因分析',
        path: '/analytics/marketing-attribution/path',
        pagePath: '/analytics/marketing-attribution/path',
        icon: 'account_tree',
        badge: '后置',
        muted: true,
        valueNote: '缺广告/流量接入时占比多为估算，慎作决策依据',
      },
    ],
  },
  {
    key: 'yield',
    title: '收益概览',
    subtitle: '收益指标',
    path: '/analytics/yield',
    icon: 'monitoring',
    hint: 'RevPAR / ADR / OCC',
    leaves: [
      {
        key: 'revpar',
        title: 'RevPAR · ADR · OCC 趋势',
        path: '/analytics/yield/overview',
        pagePath: '/analytics/yield/overview',
        icon: 'show_chart',
        badge: '规划中',
        muted: true,
        valueNote: '与价格助手、智能定价打通后上线',
      },
    ],
  },
]

export const ANALYTICS_LEAVES: AnalyticsLeaf[] = ANALYTICS_TREE.flatMap((b) => b.leaves)

/** @deprecated 兼容旧卡片列表 */
export const ANALYTICS_SECTIONS = ANALYTICS_TREE.map((b) => ({
  key: b.key,
  title: b.title,
  hint: b.hint,
  cards: b.leaves.map((l) => ({
    key: l.key,
    title: l.title,
    desc: l.valueNote || b.hint,
    path: l.path,
    icon: l.icon,
    badge: l.badge,
    muted: l.muted,
  })),
}))

export const ANALYTICS_CARDS = ANALYTICS_LEAVES.map((l) => ({
  key: l.key,
  title: l.title,
  desc: l.valueNote || '',
  path: l.path,
  icon: l.icon,
  badge: l.badge,
  muted: l.muted,
}))

export function findAnalyticsBranch(path: string): AnalyticsBranch | null {
  return (
    ANALYTICS_TREE.find(
      (b) =>
        path === b.path || path.startsWith(b.path + '/') || b.leaves.some((l) => l.path === path),
    ) || null
  )
}

export function findAnalyticsLeaf(path: string): AnalyticsLeaf | null {
  return ANALYTICS_LEAVES.find((l) => l.path === path) || null
}

export function isAnalyticsDomain(path: string): boolean {
  if (path === ANALYTICS_PATH || path.startsWith(ANALYTICS_PATH + '/')) return true
  if (path === '/ai' || path.startsWith('/ai/')) return true
  // 旧路径兼容高亮
  return [
    '/c5-frontdesk/order-monitor',
    '/c5-frontdesk/order-monitor-2',
    '/c5-frontdesk/ai-new',
    '/c5-frontdesk/order-attribution',
    '/c5-frontdesk/order-ops',
  ].some((p) => path === p || path.startsWith(p + '/'))
}

export const ANALYTICS_EXTRA = [ANALYTICS_PATH, '/c2-risk']
