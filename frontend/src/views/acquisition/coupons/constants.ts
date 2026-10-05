// SPDX-License-Identifier: Apache-2.0
import type { CouponAiKind, CouponTypeMeta, TabKey } from './types'
import { t } from '../../../lib/i18n'
import { confidenceLabel } from '../../../lib/aiConfidence'

export const TAB_ALIAS: Record<string, TabKey> = {
  build: 'build',
  list: 'build',
  tpl: 'build',
  rules: 'grant',
  grant: 'grant',
  grants: 'grant',
  redeem: 'redeem',
}

/** 内部 msgid；展示请用 typeMeta() / t(nm) */
const TYPES_RAW: Record<string, CouponTypeMeta> = {
  CASH_ROOM: {
    nm: '指定房型代金券',
    ico: '💰',
    ds: '豪华房立减 ¥120（满 500）',
    lbl: '减免金额（元）*',
    hint: '指定房型可用',
    ph: '120',
    thrHide: false,
  },
  CASH_ALL: {
    nm: '无门槛代金券',
    ico: '🪙',
    ds: '通用立减 ¥50',
    lbl: '减免金额（元）*',
    hint: '全房型无门槛',
    ph: '50',
    thrHide: true,
  },
  DISCOUNT: {
    nm: '折价券',
    ico: '💸',
    ds: '房价 7 折',
    lbl: '折扣率（0.01~1.00）*',
    hint: '填 0.70 即七折',
    ph: '0.70',
    thrHide: true,
    isDiscount: true,
  },
  BENEFIT: {
    nm: '权益券',
    ico: '🎁',
    ds: '免费双早 / 延迟退房',
    lbl: '权益说明',
    hint: '如 免费双早',
    ph: '免费双早',
    thrHide: true,
    isText: true,
    isBenefit: true,
  },
}

export function typeMeta(code: string): CouponTypeMeta {
  const raw = TYPES_RAW[code] || TYPES_RAW.DISCOUNT
  return {
    ...raw,
    nm: t(raw.nm),
    ds: t(raw.ds),
    lbl: t(raw.lbl),
    hint: t(raw.hint),
    ph: t(raw.ph),
  }
}

/** 供模板 v-for；每次调用按当前 locale 翻译 */
export function listTypeMetas(): { key: string; meta: CouponTypeMeta }[] {
  return Object.keys(TYPES_RAW).map((key) => ({ key, meta: typeMeta(key) }))
}

/** 兼容旧 import：Proxy 按 key 返回已翻译 meta */
export const TYPES: Record<string, CouponTypeMeta> = new Proxy(
  {} as Record<string, CouponTypeMeta>,
  {
    get(_t, prop: string) {
      if (prop in TYPES_RAW) return typeMeta(prop)
      return undefined
    },
    ownKeys() {
      return Object.keys(TYPES_RAW)
    },
    getOwnPropertyDescriptor(_t, prop) {
      if (prop in TYPES_RAW)
        return { enumerable: true, configurable: true, value: typeMeta(String(prop)) }
      return undefined
    },
  },
)

const ST_RAW: Record<string, string> = {
  draft: '草稿',
  active: '进行中',
  paused: '已暂停',
  expired: '已结束',
}

export const ST_CN: Record<string, string> = new Proxy({} as Record<string, string>, {
  get(_t, prop: string) {
    const m = ST_RAW[prop]
    return m != null ? t(m) : prop
  },
})

const GRANT_RAW: Record<string, string> = {
  CLAIMABLE: '待领取',
  AVAILABLE: '可用',
  USED: '已核销',
  EXPIRED: '已过期',
  VOID: '已作废',
  unused: '可用',
  used: '已核销',
  expired: '已过期',
  void: '已作废',
}

export const GRANT_ST: Record<string, string> = new Proxy({} as Record<string, string>, {
  get(_t, prop: string) {
    const m = GRANT_RAW[prop]
    return m != null ? t(m) : prop
  },
})

const CHANNEL_RAW: Record<string, string> = {
  all: '全员推送',
  tag: '按客户标签',
  segment: '自定义客群',
  level: '会员等级',
  guest: '指定客人',
  claim: '自助领取',
}

export const CHANNEL_CN: Record<string, string> = new Proxy({} as Record<string, string>, {
  get(_t, prop: string) {
    const m = CHANNEL_RAW[prop]
    return m != null ? t(m) : prop
  },
})

export const LEVEL_OPTS = [t('普通会员'), t('银卡'), t('金卡'), t('钻石卡')]

// Note: LEVEL_OPTS is evaluated at module load; panels that need live locale
// should map via t() when rendering. For wizard options we keep Chinese msgids:
export const LEVEL_OPTS_MSGID = ['普通会员', '银卡', '金卡', '钻石卡'] as const

const AI_UI_RAW: Record<
  CouponAiKind,
  { title: string; idle: string; run: string; rerun: string; wait: string }
> = {
  smart_create: {
    title: '智能建券助手',
    idle: '',
    run: '生成建券方案',
    rerun: '重新生成',
    wait: '正在根据目标生成建券参数…',
  },
  audience: {
    title: '发券对象智能圈选',
    idle: '点击后推荐客群，并说明「为何这些人」',
    run: '推荐客群',
    rerun: '重新推荐',
    wait: '正在匹配目标与客群…',
  },
  rule_recommend: {
    title: '自动发券规则推荐',
    idle: '',
    run: '推荐规则',
    rerun: '重新推荐',
    wait: '正在分析历史触发与核销…',
  },
  budget: {
    title: '发券预算与面额建议',
    idle: '',
    run: '生成预算建议',
    rerun: '重新测算',
    wait: '正在测算面额与发放上限…',
  },
  redeem_insight: {
    title: '核销归因解读',
    idle: '',
    run: '解读核销',
    rerun: '重新解读',
    wait: '正在解读核销流水…',
  },
}

export const AI_UI: Record<
  CouponAiKind,
  { title: string; idle: string; run: string; rerun: string; wait: string }
> = new Proxy({} as any, {
  get(_t, prop: string) {
    const raw = AI_UI_RAW[prop as CouponAiKind]
    if (!raw) return undefined
    return {
      title: t(raw.title),
      idle: raw.idle ? t(raw.idle) : '',
      run: t(raw.run),
      rerun: t(raw.rerun),
      wait: t(raw.wait),
    }
  },
})

export const confText: Record<string, string> = new Proxy({} as Record<string, string>, {
  get(_t, prop: string) {
    return confidenceLabel(String(prop))
  },
})

export function fmtDt(v?: string) {
  if (!v) return '—'
  return String(v).slice(0, 16).replace('T', ' ')
}

export function shortRange(from?: string, to?: string) {
  const a = from ? String(from).slice(5, 10).replace('-', '.') : '—'
  const b = to ? String(to).slice(5, 10).replace('-', '.') : '—'
  return `${a} ~ ${b}`
}

export function aiSourceLabel(insight: any) {
  const s = insight?.source
  if (s === 'llm') return t('AI 解读')
  if (s === 'unavailable' || s === 'fallback') return t('AI 暂不可用')
  if (s === 'rules_disabled') return t('AI 未启用')
  return ''
}
