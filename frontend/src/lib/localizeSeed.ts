// SPDX-License-Identifier: Apache-2.0
import { getLocale, t } from './i18n'

/** 资产/工单种子里常见的中文片段（展示时按 Locale 替换；长词优先） */
const FRAGMENTS = [
  '智能门锁电池',
  '花洒水压与密封圈例行检查',
  '花洒水压与密封例行检查',
  '滤网与排水需季节性保养',
  '门锁电池与固件需纳入巡检',
  '门锁电池与固件巡检',
  '执行电池与固件巡检',
  '监控巡检结果并更新健康分',
  '客诉/巡检后已修复归档',
  '智能门锁',
  '分体空调',
  '淋浴套件',
  'TOTO 淋浴',
  '带淋浴间',
  '中央空调',
  '门锁安防',
  '空调暖通',
  '卫浴设备',
  '卫浴/管道',
  '五金件',
  '家具',
  '客房设备',
  '弱电',
  '去资产清单',
  '核对报损与告警',
  '佣金',
  '店长',
  '平台抬头',
  '开具发票',
  '散客直订',
  '其他预订渠道',
  '协议挂账早餐',
  '协议挂账',
  '协议单位',
  '已结清',
  '影响当日营收',
  '房费',
  '迷你吧消费',
  '迷你吧',
  '人工改价未审批',
  '账单未平',
  '在店',
  '即到',
  '到店',
  '客诉',
  '常住客',
  '逾期应收',
  'OTA结算',
  '长包房',
  '企业挂账',
  '佣金',
  'AI 配对',
  '待 AI 分析',
  '待人复核',
  '壁挂吹风机',
  '客房遥控器',
  '淋浴喷头',
  '空调滤网',
  '公共区',
  '公区',
  '综合维保',
  '计划维保',
  '历史维修',
  '应急维修',
  '预防性维保',
  '纠正性维修',
  '更换报废评估',
  '持续监测',
  '【行动判定】',
  '【结论】',
  '【执行建议】',
  '【风险与依据】',
  '【风险与衔接】',
  '优先级 高',
  '优先级 中',
  '优先级 低',
  '工程维保部',
  '工程维保',
  '工程外包',
  '工程总包',
  '前台报修',
  '张师傅',
  '李工',
  '王工',
  '宁工',
  '上越外包',
  '健康分',
  '修换指数',
  '开放告警',
  '无开放告警',
  '万能房卡',
  '丢失须换整层锁芯',
  '丢失须缴费赔偿',
  '携程客',
  '明早预离',
  '接收确认中',
  '交班人已签',
  '接班人签字接收',
  '（你 · 待完成）',
  '（有阻断时）',
  '保存 3 年',
  '库存单位',
  '安全库存',
]

/** DB/API 中文种子文案 → 当前 Locale；保留房号等数字前缀 */
export function localizeSeedText(raw: string | null | undefined): string {
  if (raw == null || raw === '') return ''
  const s = String(raw)
  const full = t(s)
  if (full !== s) return full

  let out = s.replace(/(\d+)\s*房/g, (_m, n) => t('{n} 房', { n }))
  out = out.replace(/（房\s*(\d+)）/g, (_m, n) => t('（房 {n}）', { n }))
  out = out.replace(/(\d+)\s*单/g, (_m, n) => t('{n} 单', { n }))
  out = out.replace(/(\d+)\s*笔订单/g, (_m, n) => t('{n} 笔订单', { n }))
  out = out.replace(/(\d+)\s*月/g, (_m, n) => t('{n} 月', { n }))
  out = out.replace(/逾期\s*(\d+)\s*天/g, (_m, n) => t('逾期 {n} 天', { n }))
  out = out.replace(/账期\s*([0-9\-—]+)/g, (_m, d) => t('账期 {d}', { d }))
  out = out.replace(/连住\s*(\d+)\s*晚/g, (_m, n) => t('连住 {n} 晚', { n }))
  out = out.replace(/库存单位\s+/g, `${t('库存单位')} `)
  out = out.replace(/安全库存\s+/g, `${t('安全库存')} `)
  out = out.replace(/到店\s*·\s*预计/g, t('到店 · 预计'))
  out = out.replace(/(\d+)\s*班/g, (_m, n) => t('{n} 班', { n }))
  for (const zh of FRAGMENTS) {
    if (!out.includes(zh)) continue
    const en = t(zh)
    if (en === zh) continue
    // 房号紧贴中文名时补空格：0105智能门锁 → 0105 Smart door lock
    out = out.replaceAll(zh, (match, offset, whole) => {
      const prev = offset > 0 ? whole[offset - 1] : ''
      return /\d/.test(prev) ? ` ${en}` : en
    })
  }
  return out
}

/** 资产 AI 叙事：片段替换 + 常见模板正则（EN 下尽量消掉残留中文） */
export function localizeAssetAiText(raw: string | null | undefined): string {
  if (raw == null || raw === '') return ''
  let out = localizeSeedText(raw)
  if (!getLocale().startsWith('en')) return out

  out = out
    .replace(/置信度\s*(\d+)\s*%/g, 'Confidence $1%')
    .replace(/优先级\s*高/g, 'priority high')
    .replace(/优先级\s*中/g, 'priority medium')
    .replace(/优先级\s*低/g, 'priority low')
    .replace(/(\d{4}-\d{2}-\d{2})\s*前完成/g, 'complete by $1')
    .replace(/前完成/g, 'complete before due date')
    .replace(/工程维保部/g, 'Engineering / maintenance')
    .replace(/工程维护部/g, 'Engineering / maintenance')
    .replace(/维修成本占比\s*(\d+(?:\.\d+)?)%/g, 'repair cost $1% of original')
    .replace(/修换指数\s*(\d+)/g, 'replace index $1')
    .replace(/健康分\s*(\d+)/g, 'health $1')
    .replace(/无开放告警/g, 'no open alerts')
    .replace(/开放告警/g, 'open alerts')
    .replace(/保障运营连续性/g, 'protect operational continuity')
    .replace(/保障客房可售与宾客体验/g, 'protect sellable rooms and guest experience')
    .replace(/建议执行/g, 'Recommend ')
    .replace(/以保障/g, 'to ensure ')
    .replace(/部\s*·/g, ' ·')
    .replace(/接近阈值/g, 'near threshold')
    .replace(/需确保电池与固件正常/g, 'ensure battery and firmware are healthy')

  return out
}
