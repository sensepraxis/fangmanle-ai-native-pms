// SPDX-License-Identifier: Apache-2.0
/** 价格助手界面文案：渠道 / 数据源 / 模式等（msgid 中文，展示时 t()） */
import { t, getLocale } from '../../lib/i18n'

/** 渠道编码 → 展示名（英文品牌名保留原文，如 Agoda） */
export const CHANNEL_LABEL: Record<string, string> = {
  // 本店 / 直销
  direct: '官网直订',
  member: '小程序/会员',
  corp: '协议/团队',
  agreement: '协议客户',
  longstay: '长租',
  walkin: '散客上门',
  wechat: '微信',
  wecom: '企微',

  // OTA 档案码
  ota_ctrip: '携程',
  ota_meituan: '美团',
  ota_fliggy: '飞猪',
  ota_douyin: '抖音来客',
  ota_tongcheng: '同程/去哪儿',
  ota_elong: '艺龙',
  ota_agoda: 'Agoda',
  ota_booking: 'Booking',
  ota_expedia: 'Expedia',
  jd: '京东',

  // 运营别名（与档案码同义；展示时优先用档案码，此处兜底）
  ctrip: '携程',
  meituan: '美团',
  fliggy: '飞猪',
  douyin: '抖音来客',
  tongcheng: '同程/去哪儿',
  elong: '艺龙',
  qunar: '去哪儿',
  booking: 'Booking',
  expedia: 'Expedia',
  agoda: 'Agoda',

  // 获客 / 地图 / 券包等
  meituan_voucher: '美团券',
  xiaohongshu: '小红书',
  map_baidu: '百度地图',
  map_amap: '高德地图',
  geo_doubao: '豆包地理',
  meta_google: '谷歌比价',
  douyin_life: '抖音生活服务',
}

/** 不应作为「销售渠道」chip 展示的编码（笼统桶 / 纯别名） */
export const CHANNEL_CHIP_HIDE = new Set([
  'ota', // 笼统桶，不是具体渠道
])

/** 运营别名 → 档案主码（有主码时 chip 去重） */
export const CHANNEL_ALIAS_TO_PRIMARY: Record<string, string> = {
  ctrip: 'ota_ctrip',
  meituan: 'ota_meituan',
  fliggy: 'ota_fliggy',
  douyin: 'ota_douyin',
  tongcheng: 'ota_tongcheng',
  elong: 'ota_elong',
  agoda: 'ota_agoda',
  booking: 'ota_booking',
  expedia: 'ota_expedia',
}

export const SOURCE_LABEL: Record<string, string> = {
  manual: '手工录入',
  rate_shopping: '比价工具',
  public_scrape: '公开页采集',
  ai_candidate_confirmed: 'AI 候选已确认',
  manual_entry: '手工录入',
  amap: '高德周边',
  amap_demo: '高德',
  tianditu: '天地图周边',
  tianditu_demo: '天地图',
}

export const AGG_LABEL: Record<string, string> = {
  conservative: '保守',
  balanced: '均衡',
  aggressive: '激进',
}

export function channelLabel(code: string | null | undefined): string {
  if (!code) return '—'
  const key = String(code).trim()
  if (CHANNEL_LABEL[key]) return t(CHANNEL_LABEL[key])
  const low = key.toLowerCase()
  if (CHANNEL_LABEL[low]) return t(CHANNEL_LABEL[low])
  // 未知 snake_case：尽量可读，但不伪造「ota」渠道名
  if (low === 'ota') return t('线上渠道（未指定）')
  return key
}

/** 价格日历等 chip 列表：去笼统桶、去与档案码重复的别名 */
export function filterChannelChipKeys(keys: string[]): string[] {
  const set = new Set(keys.map(String))
  return keys.filter((raw) => {
    const k = String(raw)
    if (CHANNEL_CHIP_HIDE.has(k) || CHANNEL_CHIP_HIDE.has(k.toLowerCase())) return false
    const primary = CHANNEL_ALIAS_TO_PRIMARY[k] || CHANNEL_ALIAS_TO_PRIMARY[k.toLowerCase()]
    if (primary && set.has(primary)) return false
    return true
  })
}

export function sourceLabel(code: string | null | undefined): string {
  if (!code) return '—'
  return SOURCE_LABEL[code] ? t(SOURCE_LABEL[code]) : code
}

export function aggLabel(code: string | null | undefined): string {
  if (!code) return '—'
  return AGG_LABEL[code] ? t(AGG_LABEL[code]) : code
}

/**
 * 推导/理由文案：兼容已落库的中文快照 + 术语归一。
 * 可重复调用；已本地化的串再过一遍也安全。
 */
export function localizePricingCopy(text: string | null | undefined): string {
  let s = String(text || '').trim()
  if (!s) return ''

  const once = (needle: RegExp, labeled: string) => {
    if (s.includes(labeled)) return
    s = s.replace(needle, labeled)
  }

  once(/competitor_rate_snapshot/gi, '竞品房价快照 (competitor_rate_snapshot)')
  once(/inventory_snapshot/gi, '库存快照 (inventory_snapshot)')
  once(/pace_snapshot/gi, t('预订进度快照'))
  once(/event_calendar/gi, '活动日历 (event_calendar)')
  once(/room_type_base_rate/gi, '房型基础价表 (room_type_base_rate)')
  once(/orders_derived/gi, '订单推算 (orders_derived)')
  once(/\bbase_rate\b/gi, '基准价 (base_rate)')

  const pace = t('预订进度')
  s = s.replace(/销售预订进度\s*[（(]Pace[)）]/gi, pace)
  s = s.replace(/预订进度\s*[（(]Pace[)）]/gi, pace)
  s = s.replace(/销售预订进度 \(Pace\)/gi, pace)
  s = s.replace(/预订进度 \(Pace\)/gi, pace)
  s = s.replace(/销售\s*Pace\b/gi, pace)
  if (getLocale() !== 'en') {
    s = s.replace(/\bPace\b/g, pace)
  } else {
    s = s.replace(/销售预订进度/g, pace)
    s = s.replace(/预订进度快照/g, t('预订进度快照'))
    s = s.replace(/预订进度/g, pace)
  }
  if (!/紧张度\s*\(Tightness\)/i.test(s) && !/Tightness\s*\(Tightness\)/i.test(s)) {
    s = s.replace(/\bTightness\b/gi, '紧张度 (Tightness)')
  }
  if (!/价差\s*\(Gap\)/i.test(s)) {
    s = s.replace(/\bGap\b/g, '价差 (Gap)')
  }
  if (!/入住率\s*\(OCC\)/i.test(s)) {
    s = s.replace(/\bOCC\b/g, '入住率 (OCC)')
  }
  if (!/每间可售房收入\s*\(RevPAR\)/i.test(s)) {
    s = s.replace(/\bRevPAR\b/g, '每间可售房收入 (RevPAR)')
  }

  s = s.replace(/^活动[:：]/, '活动：')
  // 清理「（活动日历 (event_calendar)）」双层括号感 / 重复
  s = s.replace(/（活动日历\s*活动日历 \(event_calendar\)）/g, '（活动日历 event_calendar）')
  s = s.replace(/（活动日历 \(event_calendar\)）/g, '（活动日历 event_calendar）')

  // —— 已落库中文快照 → 按 msgid 翻译（库内活动名保留）——
  s = s.replace(/销售预订进度 \(Pace\) ([+\-]?\d+)%/g, (_m, pct) => t('预订进度 {pct}%', { pct }))
  s = s.replace(/预订进度 \(Pace\) ([+\-]?\d+)%/g, (_m, pct) => t('预订进度 {pct}%', { pct }))
  s = s.replace(/预订进度 \(Pace\) 平稳 ([\d.]+)/g, (_m, ratio) =>
    t('预订进度 平稳 {ratio}', { ratio }),
  )
  s = s.replace(/紧张度 \(Tightness\) ([\d.]+)/g, (_m, n) => t('紧张度 (Tightness) {n}', { n }))
  s = s.replace(/库存偏紧（剩 (\d+) 间）/g, (_m, n) => t('库存偏紧（剩 {n} 间）', { n }))
  s = s.replace(/库存偏松（剩 (\d+) 间）/g, (_m, n) => t('库存偏松（剩 {n} 间）', { n }))
  s = s.replace(/^活动：(.+?)\+?([+\-]?\d+)%$/, (_m, name, pct) =>
    t('活动：{name}+{pct}%', { name, pct }),
  )
  s = s.replace(/^活动 \+([+\-]?\d+)%$/, (_m, pct) => t('活动 +{pct}%', { pct }))
  s = s.replace(/竞品中位 ¥([\d.]+) vs 本店/g, (_m, price) =>
    t('竞品中位 ¥{price} vs 本店', { price }),
  )
  s = s.replace(/(.+?)（活动日历 event_calendar）/g, (_m, name) =>
    t('{name}（活动日历 event_calendar）', { name }),
  )
  s = s.replace(
    /活动日历 · 热度 ([\d.]+) · 距本店 ([\d.]+)km → 系数 \+?([+\-]?[\d.]+)%（档位锚点不封顶，受硬上限 \+?([+\-]?[\d.]+)% 约束）/g,
    (_m, heat, dist, coef, cap) =>
      t(
        '活动日历 · 热度 {heat} · 距本店 {dist}km → 系数 +{coef}%（档位锚点不封顶，受硬上限 +{cap}% 约束）',
        { heat, dist, coef, cap },
      ),
  )
  s = s.replace(
    /节假日系数 · 假期长度基准 \+?([+\-]?[\d.]+)% × 形状 ([\d.]+)（受活动因子硬上限 \+?([+\-]?[\d.]+)% 约束）/g,
    (_m, base, shape, cap) =>
      t('节假日系数 · 假期长度基准 +{base}% × 形状 {shape}（受活动因子硬上限 +{cap}% 约束）', {
        base,
        shape,
        cap,
      }),
  )
  s = s.replace(
    /预订进度快照(?:\s*\(pace_snapshot\))? · 阈值 >([\d.]+) 涨 \/ <([\d.]+) 降/g,
    (_m, up, down) => t('预订进度快照 · 阈值 >{up} 涨 / <{down} 降', { up, down }),
  )
  s = s.replace(/库存快照 \(inventory_snapshot\) · 紧张度 \(Tightness\) ([\d.]+)/g, (_m, n) =>
    t('库存快照 (inventory_snapshot) · 紧张度 (Tightness) {n}', { n }),
  )
  s = s.replace(
    /竞品房价快照 · 加权中位（距离半径 ([\d.]+)km · 模式 (\w+) · w([\d.]+)）/g,
    (_m, km, mode, w) =>
      t('竞品房价快照 · 加权中位（距离半径 {km}km · 模式 {mode} · w{w}）', { km, mode, w }),
  )
  s = s.replace(/活动日历 · 实际系数 \+?([+\-]?[\d.]+)%（受活动因子硬上限约束）/g, (_m, pct) =>
    t('活动日历 · 实际系数 +{pct}%（受活动因子硬上限约束）', { pct }),
  )

  const staticFrags = [
    '竞品对比未开启',
    '仅基于本店房态 / 库存 / 销售信号，竞品因子不参与',
    '竞品对比已开启 · 当日无可用竞品价',
    '开关已开，但该入住日缺少可比竞品客付价快照（需录价且日期匹配；有房型映射时须 like-for-like），故竞品因子贡献为 0',
    '公平价带暂不可用',
    '公平价带不可用',
    '竞品对比未开启：公平价带不计算。',
    '竞品对比已开启，但该日无可用竞品中位价，公平价带不计算。请为建议入住日补录竞品客付价后重新生成建议。',
    '未含竞品信号（内部基准模式）',
    '竞品对齐',
    '涨幅封顶、成本底线与净到手下限均已通过。',
    '以上仅为建议，须店长确认后改价，系统不会自动跟价。',
  ]
  for (const frag of staticFrags) {
    if (s.includes(frag)) s = s.split(frag).join(t(frag))
  }

  // 整句 msgid 兜底（精确命中才有英文；否则原样）
  return t(s)
}

/** KPI / 图例等后端可能仍返回中文 msgid 时的展示 */
export function localizeKpiHint(raw: string | null | undefined): string {
  const s = String(raw || '').trim()
  if (!s) return ''
  const hol = s.match(/^含\s*(\d+)\s*个节假日日期$/)
  if (hol) return t('含 {n} 个节假日日期', { n: hol[1] })
  const fut = s.match(/^未来\s*(\d+)\s*天$/)
  if (fut) return t('未来 {n} 天', { n: fut[1] })
  const cap = s.match(/^活动因子硬上限\s*\+(\d+)%（日环比涨幅\s*\+(\d+)%\s*为独立闸门）$/)
  if (cap)
    return t('活动因子硬上限 +{ev}%（日环比涨幅 +{cap}% 为独立闸门）', { ev: cap[1], cap: cap[2] })
  const cap2 = s.match(/^活动因子硬上限\s*\+(\d+)%$/)
  if (cap2) return t('活动因子硬上限 +{ev}%', { ev: cap2[1] })
  return t(s)
}
