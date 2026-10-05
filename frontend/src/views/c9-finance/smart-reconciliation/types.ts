// SPDX-License-Identifier: Apache-2.0
import { t } from '../../../lib/i18n'
export type Dim = 'batch' | 'accrual' | 'settle'
export type Tab = 'all' | 'ai' | 'human' | 'closed'
export type Status = 'ai' | 'human' | 'progress' | 'matched' | 'closed'

export type Breakdown = {
  type: 'fee' | 't1' | 'refund' | 'net'
  label: string
  tag: 'normal' | 'check' | 'bad'
  tagLabel: string
  amount: number
  note: string
  pct: number
}

export type OrderLine = {
  orderId: number
  orderNo: string
  guestName?: string
  pms: number
  channel: number
  matchStatus: string
  note?: string
}

export type BatchRow = {
  id: number | string
  code: string
  channel: string
  guest: string
  bizDate: string
  pms: number
  gateway: number
  bank: number | null
  variance: number
  status: Status
  note: string
  confidence: number
  cause: string
  modelMeta?: string
  commissionPct: number
  commissionPctText: string
  commissionLabel: string
  commissionFormula: string
  expectedCommission: number
  expectedNet: number
  breakdown: Breakdown[]
  similar: { title: string; done: boolean }[]
  orderLines: OrderLine[]
  closed?: boolean
}

export const STATUS_META: Record<Status, { label: string; cls: string }> = {
  ai: { label: '待 AI 分析', cls: 'info' },
  human: { label: '待人复核', cls: 'warn' },
  progress: { label: '处理中', cls: 'purple' },
  matched: { label: 'AI 配对', cls: 'ok' },
  closed: { label: '已关账', cls: 'ok' },
}

/** 状态徽章文案跟 Locale（STATUS_META.label 存 msgid） */
export function statusLabel(st: Status) {
  return t(STATUS_META[st]?.label || st)
}

const CHAN_CLS: Record<string, string> = {
  支付宝: 'alipay',
  微信支付: 'wechat',
  企微私域: 'wechat',
  企业微信: 'wechat',
  散客直订: 'bank',
  协议客户: 'bank',
  现金: 'bank',
  POS: 'bank',
  银行转账: 'bank',
  携程: 'ctrip',
  美团酒店: 'meituan',
  美团团购: 'meituan',
  飞猪: 'fliggy',
  抖音团购: 'douyin',
  小红书: 'xhs',
}

export function chanClass(name: string) {
  if (CHAN_CLS[name]) return CHAN_CLS[name]
  if (/美团/.test(name)) return 'meituan'
  if (/携程/.test(name)) return 'ctrip'
  if (/飞猪/.test(name)) return 'fliggy'
  if (/抖音/.test(name)) return 'douyin'
  if (/微信|企微/.test(name)) return 'wechat'
  if (/支付宝/.test(name)) return 'alipay'
  return 'booking'
}

export function money(n: number | null | undefined, digits = 2) {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return `¥${Number(n).toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`
}
