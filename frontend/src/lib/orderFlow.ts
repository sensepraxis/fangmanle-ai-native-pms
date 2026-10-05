// SPDX-License-Identifier: Apache-2.0
/** 订单中心：工作视图、结账模式、行内主操作文案（前后端一致） */
import { t } from './i18n'
import { ORDER_ST_CN, PAY_CN } from './ui'
export type CheckoutKind = 'prepaid' | 'collect' | 'corp'
export type OrderWorkView =
  'all' | 'arrivals' | 'departures' | 'created_today' | 'unassigned' | 'pending' | 'inhouse'

export const SOURCE_LABEL: Record<string, string> = {
  all: '全部来源',
  ota: '预订平台',
  booking: '预订平台',
  voucher: '团购核销',
  direct: '散客直订',
  group: '团体订单',
  map: '地图预订',
  geo: 'GEO推荐',
  longstay: '常住客',
  agreement: '协议客',
  wechat: '企微私域',
  xiaohongshu: '小红书',
}

export function resolveCheckoutKind(o: {
  source_group?: string
  channel_type?: string
  payment_status?: string
}): CheckoutKind {
  const sg = String(o?.source_group || o?.channel_type || 'direct')
  const pay = String(o?.payment_status || '')
  if (sg === 'agreement' || pay === 'on_account') return 'corp'
  if (sg === 'ota' || sg === 'voucher' || pay === 'paid') return 'prepaid'
  return 'collect'
}

export function checkoutBtnLabel(o: Parameters<typeof resolveCheckoutKind>[0]): string {
  const kind = resolveCheckoutKind(o)
  if (kind === 'corp') return t('挂账退房')
  if (kind === 'prepaid') return t('核对退房')
  return t('收银退房')
}

export function primaryOrderAction(o: {
  status?: string
  assign_status?: string
  pre_room_no?: string | null
  room_no?: string | null
}): 'checkin' | 'checkout' | 'view' | null {
  const st = String(o?.status || '')
  if (st === 'pending' || st === 'confirmed') return 'checkin'
  if (st === 'checked_in') return 'checkout'
  return 'view'
}

export function isUnassignedOrder(o: {
  assign_status?: string
  pre_room_id?: number | null
  pre_room_no?: string | null
  room_no?: string | null
}): boolean {
  if (o.assign_status) return o.assign_status === 'unassigned'
  return !o.pre_room_id && !o.pre_room_no && !o.room_no
}

export function primaryOrderActionLabel(o: {
  status?: string
  assign_status?: string
  pre_room_no?: string | null
  room_no?: string | null
}): string {
  const act = primaryOrderAction(o)
  if (act === 'checkin') return isUnassignedOrder(o) ? t('待分房') : t('办理入住')
  if (act === 'checkout') return t('退房结账')
  return t('查看详情')
}

/** 分房生命周期（列表展示，非房间号） */
export const ASSIGN_ST_CN: Record<string, string> = {
  unassigned: '未排房',
  pre_assigned: '已预分',
  in_house: '在住分房',
  checked_out: '已退房',
  no_show: '未到店',
  cancelled: '已取消',
}

export const ASSIGN_ST_PILL: Record<string, string> = {
  unassigned: 'pill pill-amber',
  pre_assigned: 'pill pill-blue',
  in_house: 'pill pill-green',
  checked_out: 'pill pill-slate',
  no_show: 'pill pill-rose',
  cancelled: 'pill pill-slate',
}

export function assignStatusOf(o: {
  assign_status?: string
  status?: string
  pre_room_no?: string | null
  pre_room_id?: number | null
}): string {
  if (o.assign_status) return o.assign_status
  const st = String(o.status || '')
  if (st === 'checked_in') return 'in_house'
  if (st === 'checked_out') return 'checked_out'
  if (st === 'no_show') return 'no_show'
  if (st === 'cancelled') return 'cancelled'
  if (st === 'pending' || st === 'confirmed') {
    return o.pre_room_id || o.pre_room_no ? 'pre_assigned' : 'unassigned'
  }
  return 'unassigned'
}

/** 前台任务视图 Tab（对齐行业 PMS：订单来了 / 住宿订单） */
export const ORDER_WORK_TABS = [
  { key: 'all', label: '全部', icon: 'apps', summaryKey: 'all' as const },
  { key: 'arrivals', label: '今日预抵', icon: 'login', summaryKey: 'arrivals' as const },
  { key: 'departures', label: '今日预离', icon: 'logout', summaryKey: 'departures' as const },
  {
    key: 'created_today',
    label: '今日新办',
    icon: 'add_circle',
    summaryKey: 'created_today' as const,
  },
  { key: 'unassigned', label: '未排房', icon: 'meeting_room', summaryKey: 'unassigned' as const },
  { key: 'pending', label: '待处理', icon: 'pending_actions', summaryKey: 'pending' as const },
  { key: 'inhouse', label: '在住', icon: 'hotel', summaryKey: 'inhouse' as const },
] as const

/** 入住类型（列表展示，由来源 + 晚数推导） */
export const STAY_TYPE_CN: Record<string, string> = {
  daily: '日租',
  longstay: '长住',
  agreement: '协议',
  voucher: '团购',
  ota: 'OTA',
  group: '团体',
  direct: '直订',
  wechat: '私域',
}

export function stayTypeLabel(o: { source_group?: string; nights?: number }): string {
  const sg = String(o?.source_group || 'direct')
  const nights = Number(o?.nights || 0)
  let msgid = STAY_TYPE_CN.daily
  if (sg === 'group') msgid = STAY_TYPE_CN.group
  else if (sg === 'longstay' || nights >= 28) msgid = STAY_TYPE_CN.longstay
  else if (sg === 'agreement') msgid = STAY_TYPE_CN.agreement
  else if (sg === 'voucher') msgid = STAY_TYPE_CN.voucher
  else if (sg === 'ota') msgid = STAY_TYPE_CN.ota
  else if (sg === 'wechat') msgid = STAY_TYPE_CN.wechat
  return t(msgid)
}

export function formatOrderDateTime(iso?: string | null, fallbackDate?: string): string {
  if (iso) {
    const d = new Date(iso)
    if (!Number.isNaN(d.getTime())) {
      const p = (n: number) => String(n).padStart(2, '0')
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
    }
  }
  return fallbackDate || '—'
}

/** @deprecated 改用 ORDER_WORK_TABS */
export const ORDER_STATUS_TABS = ORDER_WORK_TABS

/** 来源筛选（分组展示，与 SOURCE_META / 库内渠道对齐） */
export const ORDER_SOURCE_GROUPS = [
  {
    label: '全部',
    items: [{ key: 'all', label: '全部来源' }],
  },
  {
    label: 'OTA 分销',
    items: [
      { key: 'ota', label: '预订平台（全部）' },
      { key: 'ctrip', label: '携程' },
      { key: 'meituan', label: '美团' },
      { key: 'fliggy', label: '飞猪' },
    ],
  },
  {
    label: '到店办单',
    items: [
      { key: 'voucher', label: '团购核销' },
      { key: 'direct', label: '前台直订' },
      { key: 'group', label: '团体订单' },
      { key: 'wechat', label: '企微私域' },
    ],
  },
  {
    label: '其他预订',
    items: [
      { key: 'map', label: '地图预订' },
      { key: 'geo', label: 'GEO 推荐' },
      { key: 'xiaohongshu', label: '小红书' },
    ],
  },
  {
    label: '特殊客群',
    items: [
      { key: 'longstay', label: '常住客' },
      { key: 'agreement', label: '协议客' },
    ],
  },
] as const

export const ORDER_SOURCE_FILTER = ORDER_SOURCE_GROUPS.flatMap((g) => [...g.items])

export const OTA_CHANNEL_CODES = ['ota', 'ctrip', 'meituan', 'fliggy'] as const
export const WECHAT_CHANNEL_CODES = ['wechat', 'wecom', 'xiaohongshu'] as const

/** 选中某来源时，订单中心内展示的上下文办单引导（链到支线页） */
export const ORDER_SOURCE_BRANCH: Record<
  string,
  { label: string; path: string; hint: string; icon: string } | null
> = {
  all: null,
  ota: null,
  ctrip: null,
  meituan: null,
  fliggy: null,
  voucher: {
    label: '去团购核销',
    path: '/c5-frontdesk/voucher-verification',
    hint: '团购券需先核销成单；下列表为已入库订单',
    icon: 'confirmation_number',
  },
  group: {
    label: '新建团体单',
    path: '/c5-frontdesk/group-booking',
    hint: '会议/旅游团等多间主单；下列表为已入库团体订单',
    icon: 'groups',
  },
  direct: {
    label: '新建前台预订',
    path: '/c5-frontdesk/front-desk-booking',
    hint: '电话 / 企微等先建预订单；无预订到店请走散客即时入住',
    icon: 'edit_calendar',
  },
  wechat: null,
  map: null,
  geo: null,
  xiaohongshu: null,
  longstay: {
    label: '常住订单中心',
    path: '/c5-frontdesk/filter',
    hint: '长住合同、续约提醒与账务催收',
    icon: 'calendar_month',
  },
  agreement: {
    label: '协议企业管理',
    path: '/c5-frontdesk/agreement-corp',
    hint: '企业协议价、挂账与量价阶梯',
    icon: 'corporate_fare',
  },
}

/** 订单中心模块结构（L1 工作台 + L2 专项页） */
export const ORDER_HUB_SUBTITLE = '前台工作台 · 按任务与来源浏览订单 · 行内办理入住与退房'

export const ORDER_OPS_PATH = '/analytics'
export const ORDER_FULFILL_PATH = '/c5-frontdesk/pending-assignment'

/** 顶栏「办单」菜单（与到店办单卡片同一组动作，不重复其它入口） */
export const ORDER_CHECKIN_ACTIONS = [
  {
    key: 'voucher',
    label: '团购核销',
    desc: '券到店成单',
    path: '/c5-frontdesk/voucher-verification',
    icon: 'confirmation_number',
    sourceKey: 'voucher',
  },
  {
    key: 'booking',
    label: '前台预订',
    desc: '电话 / 企微预订单',
    path: '/c5-frontdesk/front-desk-booking',
    icon: 'edit_calendar',
    sourceKey: 'direct',
  },
  {
    key: 'group',
    label: '团体订单',
    desc: '会议 / 旅游团多间',
    path: '/c5-frontdesk/group-booking',
    icon: 'groups',
    sourceKey: 'group',
  },
] as const

/** @deprecated L1 已改为 ORDER_CHECKIN_ACTIONS + 待分房徽章 */
export const ORDER_QUICK_LINKS = [] as const

/** 到店办单 · 三大场景（L1 卡片，与办单菜单一致） */
export const ORDER_BASE_FLOWS = [
  {
    key: 'voucher',
    title: '团购核销',
    desc: '美团 / 抖音券到店核销成单',
    path: '/c5-frontdesk/voucher-verification',
    icon: 'confirmation_number',
    sourceKey: 'voucher',
  },
  {
    key: 'booking',
    title: '前台预订',
    desc: '电话 / 企微 · 先建预订单',
    path: '/c5-frontdesk/front-desk-booking',
    icon: 'edit_calendar',
    sourceKey: 'direct',
  },
  {
    key: 'group',
    title: '团体订单',
    desc: '会议 / 旅游团 · 多间主单',
    path: '/c5-frontdesk/group-booking',
    icon: 'groups',
    sourceKey: 'group',
  },
] as const

/** @deprecated 已迁至经营分析树；保留兼容旧引用 */
export const ORDER_ENHANCE_CARDS = [
  {
    key: 'monitor',
    title: '异常与流失预警',
    desc: '取消风险 / 转化走低',
    path: '/analytics/order-health/churn-warning',
    icon: 'warning',
  },
  {
    key: 'insight',
    title: '全渠道订单洞察',
    desc: '渠道表现复盘',
    path: '/analytics/channel-insight/omni',
    icon: 'insights',
  },
  {
    key: 'attribution',
    title: '订单渠道归因分析',
    desc: '多触点 · ROI · 高价值单溯源',
    path: '/analytics/marketing-attribution/path',
    icon: 'route',
  },
] as const

/** @deprecated 改用 /analytics 经营分析枢纽 */
export const ORDER_ENHANCE_MENU = [
  {
    label: '异常预警',
    path: '/analytics/order-health/churn-warning',
    icon: 'warning',
    hint: '取消 / 流失趋势',
  },
  {
    label: '渠道洞察',
    path: '/analytics/channel-insight/omni',
    icon: 'insights',
    hint: '价格弹性 · 渠道质量',
  },
  {
    label: '渠道归因',
    path: '/analytics/marketing-attribution/path',
    icon: 'route',
    hint: '多触点 ROI 溯源',
  },
] as const

/** 订单分组 pill 顺序（与后端 SOURCE_META 一致，不含 OTA 子渠道） */
export const ORDER_GROUP_KEYS = [
  'all',
  'ota',
  'voucher',
  'direct',
  'group',
  'wechat',
  'map',
  'geo',
  'longstay',
  'agreement',
] as const

export const ORDER_GROUP_HINT = '按来源分块浏览；组内列表再按具体渠道展示 · 退房须点在住单行内操作'

/** 组合搜索：多字段表单，点「搜索」时 AND 叠加 */
export type OrderComboSearch = {
  order_no: string
  external_order_no: string
  reception_no: string
  room_no: string
  guest_name: string
  phone: string
  note: string
  channel_id: number
  room_type_id: number
  status: string
  payment_status: string
}

export const ORDER_COMBO_SEARCH_FIELDS = [
  { key: 'order_no', label: '订单号', placeholder: '系统内部单号' },
  { key: 'external_order_no', label: '渠道订单号', placeholder: '携程 / 美团等平台单号' },
  { key: 'reception_no', label: '预分房单号', placeholder: 'JDD 开头或数字' },
  { key: 'room_no', label: '房号（预分/在住）', placeholder: '如 0704' },
  { key: 'guest_name', label: '联系人', placeholder: '客人姓名' },
  { key: 'phone', label: '手机号', placeholder: '完整或后四位' },
  { key: 'note', label: '备注', placeholder: '订单备注关键词' },
] as const

export function emptyComboSearch(): OrderComboSearch {
  return {
    order_no: '',
    external_order_no: '',
    reception_no: '',
    room_no: '',
    guest_name: '',
    phone: '',
    note: '',
    channel_id: 0,
    room_type_id: 0,
    status: '',
    payment_status: '',
  }
}

export function hasComboSearch(f: OrderComboSearch): boolean {
  return (
    ORDER_COMBO_SEARCH_FIELDS.some((x) =>
      String(f[x.key as keyof OrderComboSearch] || '').trim(),
    ) ||
    !!f.channel_id ||
    !!f.room_type_id ||
    !!f.status ||
    !!f.payment_status
  )
}

export function comboSearchSummary(f: OrderComboSearch): string[] {
  const parts: string[] = []
  for (const field of ORDER_COMBO_SEARCH_FIELDS) {
    const v = String(f[field.key as keyof OrderComboSearch] || '').trim()
    if (v) parts.push(`${t(field.label)}=${v}`)
  }
  if (f.channel_id) parts.push(t('渠道已选'))
  if (f.room_type_id) parts.push(t('房型已选'))
  if (f.status) parts.push(`${t('入住')}=${ORDER_ST_CN[f.status] || f.status}`)
  if (f.payment_status) parts.push(`${t('结账')}=${PAY_CN[f.payment_status] || f.payment_status}`)
  return parts
}

/** @deprecated 顶栏已改为 ORDER_QUICK_LINKS */
export const ORDER_CHECKIN_MENU = [
  {
    label: '前台预订',
    path: '/c5-frontdesk/front-desk-booking',
    icon: 'edit_calendar',
    key: 'booking',
  },
  {
    label: '团购核销',
    path: '/c5-frontdesk/voucher-verification',
    icon: 'confirmation_number',
    key: 'voucher',
  },
  { label: '待分房', path: '/c5-frontdesk/pending-assignment', icon: 'door_front', key: 'assign' },
] as const

/** @deprecated 改用 ORDER_CHECKIN_MENU */
export const ORDER_CREATE_ACTIONS = ORDER_CHECKIN_MENU.filter((x) => x.label !== '待分房')
export const ORDER_FULFILL_LINKS = ORDER_CHECKIN_MENU.filter((x) => x.label === '待分房')

export const ORDER_SOURCE_TABS = ORDER_SOURCE_FILTER

/** 仅前台直订；地图 / GEO 独立筛选项 */
export const DIRECT_LIKE_GROUPS = ['direct'] as const

export type OrderWorkSummary = {
  date: string
  all: number
  arrivals: number
  departures: number
  created_today: number
  unassigned: number
  pending: number
  inhouse: number
}

export function emptyWorkSummary(onDate?: string): OrderWorkSummary {
  const d = (onDate || new Date().toISOString()).slice(0, 10)
  return {
    date: d,
    all: 0,
    arrivals: 0,
    departures: 0,
    created_today: 0,
    unassigned: 0,
    pending: 0,
    inhouse: 0,
  }
}

/** 合并后端 summary，补齐新增 Tab 计数字段（兼容旧 API） */
export function normalizeWorkSummary(
  raw: Partial<OrderWorkSummary> | null | undefined,
  onDate?: string,
): OrderWorkSummary {
  const base = emptyWorkSummary(onDate || raw?.date)
  if (!raw) return base
  return {
    date: raw.date || base.date,
    all: Number(raw.all ?? base.all),
    arrivals: Number(raw.arrivals ?? base.arrivals),
    departures: Number(raw.departures ?? base.departures),
    created_today: Number(raw.created_today ?? base.created_today),
    unassigned: Number(raw.unassigned ?? base.unassigned),
    pending: Number(raw.pending ?? base.pending),
    inhouse: Number(raw.inhouse ?? base.inhouse),
  }
}

export type OrderListPage = {
  items: any[]
  total: number
  page: number
  page_size: number
  summary: OrderWorkSummary
}

export function computeWorkSummary(orders: any[], onDate: string): OrderWorkSummary {
  const d = onDate.slice(0, 10)
  const active = orders.filter((o) => o.status !== 'cancelled')
  const unassigned = active.filter(
    (o) => (o.status === 'pending' || o.status === 'confirmed') && !o.room_no && !o.room_id,
  )
  return {
    date: d,
    all: active.length,
    arrivals: active.filter(
      (o) => o.check_in === d && (o.status === 'pending' || o.status === 'confirmed'),
    ).length,
    departures: active.filter((o) => o.check_out === d && o.status === 'checked_in').length,
    created_today: active.filter((o) => String(o.created_at || '').slice(0, 10) === d).length,
    unassigned: unassigned.length,
    pending: active.filter((o) => o.status === 'pending').length,
    inhouse: active.filter((o) => o.status === 'checked_in').length,
  }
}

function matchSearch(o: any, q: string): boolean {
  const term = q.trim().toLowerCase()
  if (!term) return true
  const hay = [o.order_no, o.guest_name, o.phone, o.room_no, o.external_order_no, o.voucher_code]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return hay.includes(term)
}

export function filterOrdersForView(
  orders: any[],
  opts: {
    view?: string
    source?: string
    q?: string
    onDate?: string
  },
): any[] {
  const onDate = (opts.onDate || new Date().toISOString().slice(0, 10)).slice(0, 10)
  let list = orders.filter((o) => {
    if (opts.view === 'arrivals') {
      return o.check_in === onDate && (o.status === 'pending' || o.status === 'confirmed')
    }
    if (opts.view === 'inhouse') return o.status === 'checked_in'
    if (opts.view === 'departures') {
      return o.check_out === onDate && o.status === 'checked_in'
    }
    if (opts.view === 'created_today') {
      return String(o.created_at || '').slice(0, 10) === onDate && o.status !== 'cancelled'
    }
    if (opts.view === 'unassigned') {
      return (o.status === 'pending' || o.status === 'confirmed') && !o.room_no && !o.room_id
    }
    if (opts.view === 'pending') return o.status === 'pending'
    if (opts.view === 'all') return o.status !== 'cancelled'
    return true
  })
  if (opts.source && opts.source !== 'all') {
    list = list.filter((o) =>
      matchSourceTab(opts.source!, o.source_group || 'wechat', o.channel_code),
    )
  }
  if (opts.q?.trim()) {
    list = list.filter((o) => matchSearch(o, opts.q!))
  }
  return list
}

/** 兼容旧版 API 返回数组 */
export function normalizeOrdersPage(
  raw: any,
  opts: {
    view?: string
    source?: string
    q?: string
    onDate?: string
    page?: number
    pageSize?: number
  },
): OrderListPage {
  const page = opts.page ?? 1
  const pageSize = opts.pageSize ?? 20
  const onDate = opts.onDate || new Date().toISOString().slice(0, 10)

  if (raw && !Array.isArray(raw) && Array.isArray(raw.items)) {
    return {
      items: raw.items,
      total: raw.total ?? raw.items.length,
      page: raw.page ?? page,
      page_size: raw.page_size ?? pageSize,
      summary: normalizeWorkSummary(raw.summary, onDate),
    }
  }

  const all = Array.isArray(raw) ? raw : []
  const summary = computeWorkSummary(all, onDate)
  const filtered = filterOrdersForView(all, opts)
  const start = (page - 1) * pageSize
  return {
    items: filtered.slice(start, start + pageSize),
    total: filtered.length,
    page,
    page_size: pageSize,
    summary,
  }
}

export function matchSourceTab(
  sourceTab: string,
  sourceGroup: string,
  channelCode?: string,
): boolean {
  if (sourceTab === 'all') return true
  if (sourceTab === 'group') return sourceGroup === 'group'
  if (sourceTab === 'ota') return sourceGroup === 'ota'
  if ((OTA_CHANNEL_CODES as readonly string[]).includes(sourceTab)) {
    return channelCode === sourceTab
  }
  if (sourceTab === 'voucher') return sourceGroup === 'voucher'
  if (sourceTab === 'wechat') {
    return (WECHAT_CHANNEL_CODES as readonly string[]).includes(channelCode || '')
  }
  if (sourceTab === 'direct') return sourceGroup === 'direct'
  if (sourceTab === 'map') return sourceGroup === 'map'
  if (sourceTab === 'geo') return sourceGroup === 'geo'
  if (sourceTab === 'longstay') return sourceGroup === 'longstay'
  if (sourceTab === 'agreement') return sourceGroup === 'agreement'
  if (sourceTab === 'xiaohongshu') return channelCode === 'xiaohongshu'
  return sourceGroup === sourceTab
}

export function channelDisplayLabel(o: {
  channel_name?: string
  channel_code?: string
  source_group?: string
}): string {
  // 渠道名按当前 Locale 翻译（DB 可能仍是中文种子名）
  if (o.channel_name && o.channel_name !== '散客') return t(o.channel_name)
  const msgid = SOURCE_LABEL[o.source_group || '']
  return msgid ? t(msgid) : o.source_group || '—'
}

/** 行项目摘要：把「×N晚×M间」等单位按 Locale 展示 */
export function localizeLineDesc(desc: string | null | undefined): string {
  if (!desc) return ''
  let s = String(desc)
  s = s.replace(/×(\d+)晚×(\d+)间/g, (_m, n, r) =>
    t('×{nights}晚×{rooms}间', { nights: n, rooms: r }),
  )
  s = s.replace(/×(\d+)晚/g, (_m, n) => t('×{nights}晚', { nights: n }))
  s = s.replace(/×(\d+)间/g, (_m, r) => t('×{rooms}间', { rooms: r }))
  s = s.replace(/续住房费/g, () => t('续住房费'))
  s = s.replace(/^房费$/, () => t('房费'))
  s = s.replace(/^收款$/, () => t('收款'))
  s = s.replace(/房费（/g, () => `${t('房费')}（`)
  s = s.replace(/已预付$/g, () => t('已预付'))
  s = s.replace(/迷你吧\/杂费/g, () => t('迷你吧/杂费'))
  s = s.replace(/杂费/g, () => t('杂费'))
  return s
}

export function workTabCount(summary: OrderWorkSummary | null, tabKey: string): number {
  if (!summary) return 0
  const s = normalizeWorkSummary(summary, summary.date)
  const k = tabKey as keyof OrderWorkSummary
  if (k === 'date') return 0
  return Number(s[k]) || 0
}

export function sourcePillClass(sg: string): string {
  const m: Record<string, string> = {
    ota: 'src-ota',
    voucher: 'src-voucher',
    direct: 'src-direct',
    group: 'src-group',
    map: 'src-map',
    geo: 'src-geo',
    longstay: 'src-longstay',
    agreement: 'src-agreement',
    wechat: 'src-wechat',
  }
  return m[sg] || 'src-wechat'
}

/** @deprecated */
export function statusTabCount(orders: { status?: string }[], tabKey: string): number {
  if (!tabKey) return orders.length
  if (tabKey === 'pending') {
    return orders.filter((o) => o.status === 'pending' || o.status === 'confirmed').length
  }
  return orders.filter((o) => o.status === tabKey).length
}

export function tabCount(sources: { key: string; count?: number }[], tabKey: string): number {
  if (tabKey === 'all') return sources.find((s) => s.key === 'all')?.count ?? 0
  if (tabKey === 'ota') return sources.find((s) => s.key === 'ota')?.count ?? 0
  if (tabKey === 'voucher') return sources.find((s) => s.key === 'voucher')?.count ?? 0
  if (tabKey === 'wechat') return sources.find((s) => s.key === 'wechat')?.count ?? 0
  if (tabKey === 'direct') {
    return (DIRECT_LIKE_GROUPS as readonly string[]).reduce(
      (n, k) => n + (sources.find((s) => s.key === k)?.count ?? 0),
      0,
    )
  }
  return 0
}
