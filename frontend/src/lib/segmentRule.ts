// SPDX-License-Identifier: Apache-2.0
import { t } from './i18n'
/**
 * 分群 filter_rule → 确定性 SQL / 语义（与后端 segment_sql.rule_to_sql 对齐，无 LLM）
 */
export type RuleExplain = {
  source: 'nl' | 'dsl' | 'snapshot' | 'unknown' | 'tag' | 'plain' | 'empty'
  sourceLabel: string
  expression: string
  meaning: string
  bullets: string[]
  sql?: string
}

const TAG_CN: Record<string, string> = {
  business: '商务常旅客',
  family: '亲子家庭',
  repeat: '复购/回头客',
  vip: 'VIP',
  high_value: '高价值',
  cancelled: '已取消',
  no_show: '未到店',
}

type NlSpec = {
  query?: string
  window_days?: number
  order_status?: string[]
  tag_codes_any?: string[]
  min_stays?: number | null
  require_children_orders?: boolean
  prefer_high_floor?: boolean
  quiet_pref?: boolean
  sql?: string
}

const HOTEL_SCOPE = (hotel: string) =>
  `EXISTS (\n` +
  `  SELECT 1 FROM orders o0\n` +
  `  WHERE o0.guest_id = g.id AND o0.hotel_id = ${hotel}\n` +
  `)`

const TAG_EXISTS = (codes: string[], alias = 'gt') => {
  const lit = codes.map((v) => `'${String(v).replace(/'/g, "''")}'`).join(', ')
  return (
    `EXISTS (\n` +
    `  SELECT 1 FROM guest_tags ${alias}\n` +
    `  JOIN tag_definitions td ON td.id = ${alias}.tag_id\n` +
    `  WHERE ${alias}.guest_id = g.id AND td.code IN (${lit})\n` +
    `)`
  )
}

/** FilterSpec → SQL（与后端 filter_spec_to_sql 对齐） */
export function filterSpecToSql(spec: NlSpec, hotel = ':hotel_id'): string {
  if (spec.sql) return spec.sql
  const days = Number(spec.window_days || 90)
  const statuses = spec.order_status || []
  const tags = spec.tag_codes_any || []
  const lit = (vals: string[]) => vals.map((v) => `'${String(v).replace(/'/g, "''")}'`).join(', ')

  if (statuses.length) {
    const where = [
      `o.hotel_id = ${hotel}`,
      'o.guest_id IS NOT NULL',
      `o.status IN (${lit(statuses)})`,
      `DATE(COALESCE(o.created_at, o.check_in)) >= DATE('now', '-${days} days')`,
    ]
    let sql =
      'SELECT DISTINCT g.id, g.name, g.one_id, g.ltv\n' +
      'FROM guests g\n' +
      'INNER JOIN orders o ON o.guest_id = g.id\n' +
      'WHERE ' +
      where.join('\n  AND ')
    if (tags.length) {
      sql +=
        '\n  AND EXISTS (\n' +
        '    SELECT 1 FROM guest_tags gt\n' +
        '    JOIN tag_definitions td ON td.id = gt.tag_id\n' +
        `    WHERE gt.guest_id = g.id AND td.code IN (${lit(tags)})\n` +
        '  )'
    }
    if (spec.min_stays) {
      sql +=
        `\n  AND (\n` +
        `    SELECT COUNT(*) FROM orders s\n` +
        `    WHERE s.guest_id = g.id AND s.hotel_id = ${hotel}\n` +
        `      AND s.status IN ('checked_out', 'checked_in')\n` +
        `      AND DATE(COALESCE(s.created_at, s.check_in)) >= DATE('now', '-${days} days')\n` +
        `  ) >= ${Number(spec.min_stays)}`
    }
    if (spec.require_children_orders) {
      sql +=
        `\n  AND (\n` +
        `    EXISTS (SELECT 1 FROM orders c WHERE c.guest_id = g.id AND c.hotel_id = ${hotel} AND IFNULL(c.children,0) > 0)\n` +
        `    OR EXISTS (\n` +
        `      SELECT 1 FROM guest_tags gt2 JOIN tag_definitions td2 ON td2.id = gt2.tag_id\n` +
        `      WHERE gt2.guest_id = g.id AND td2.code = 'family'\n` +
        `    )\n` +
        '  )'
    }
    return sql
  }

  const where = [HOTEL_SCOPE(hotel)]
  if (tags.length) where.push(TAG_EXISTS(tags))
  if (spec.min_stays) {
    where.push(
      `(\n` +
        `  SELECT COUNT(*) FROM orders s\n` +
        `  WHERE s.guest_id = g.id AND s.hotel_id = ${hotel}\n` +
        `    AND s.status IN ('checked_out', 'checked_in')\n` +
        `    AND DATE(COALESCE(s.created_at, s.check_in)) >= DATE('now', '-${days} days')\n` +
        `) >= ${Number(spec.min_stays)}`,
    )
  }
  if (spec.require_children_orders) {
    where.push(
      `(\n` +
        `  EXISTS (SELECT 1 FROM orders c WHERE c.guest_id = g.id AND c.hotel_id = ${hotel} AND IFNULL(c.children,0) > 0)\n` +
        `  OR ${TAG_EXISTS(['family'], 'gt_fam')}\n` +
        `)`,
    )
  }
  return (
    'SELECT g.id, g.name, g.one_id, g.ltv\n' + 'FROM guests g\n' + 'WHERE ' + where.join('\n  AND ')
  )
}

export function parseNlToSpec(query: string): NlSpec {
  const text = (query || '').trim()
  let window_days = 90
  if (/近\s*一\s*年|去年|过去一年/.test(text)) window_days = 365
  else if (/近\s*半\s*年|六个月/.test(text)) window_days = 180
  else if (/近\s*三\s*个?\s*月|近\s*90\s*天|三个月/.test(text)) window_days = 90
  else if (/近\s*一\s*个?\s*月|近\s*30\s*天/.test(text)) window_days = 30

  const order_status: string[] = []
  if (text.includes('取消')) order_status.push('cancelled')
  if (/未到|no[\s\-]?show|noshow/i.test(text)) order_status.push('no_show')

  const tag_codes_any: string[] = []
  if (/商务|商旅/.test(text)) tag_codes_any.push('business')
  if (/亲子|孩子|儿童|家庭|带娃/.test(text)) tag_codes_any.push('family')
  if (/回头|复购|常客/.test(text)) tag_codes_any.push('repeat')
  if (/VIP|贵宾/i.test(text)) tag_codes_any.push('vip')

  const m = text.match(/(\d+)\s*次\s*以上/)
  const min_stays = m ? Number(m[1]) : /三次以上|3次以上/.test(text) ? 3 : null
  return {
    query: text,
    window_days,
    order_status,
    tag_codes_any,
    min_stays,
    require_children_orders: /孩子|儿童|亲子|带娃/.test(text),
    prefer_high_floor: /高层|高楼层/.test(text),
    quiet_pref: /安静/.test(text),
  }
}

function looksLikeNl(text: string) {
  return /取消|近三|商务|亲子|回头|房客|住过|带孩|高层|安静|周末|近三个月|近3个月|商务客/.test(text)
}

/** DSL → SQL（与后端 dsl_to_sql 对齐） */
export function dslToSql(rule: string, hotel = ':hotel_id'): RuleExplain | null {
  const raw = (rule || '').trim()
  if (!raw) return null
  const r = raw.toLowerCase().replace(/\s+/g, '')
  const where: string[] = [HOTEL_SCOPE(hotel)]
  let meaning = ''
  let bullets: string[] = ['范围：本店有过订单的客人（orders.hotel_id）']

  if (r.includes('ltv>5000') && r.includes('repeat')) {
    where.push('IFNULL(g.ltv, 0) > 5000')
    where.push(TAG_EXISTS(['repeat', 'high_value']))
    bullets = [
      'LTV（终身价值）> ¥5,000',
      '且标签含「复购/回头」或「高价值」',
      '范围：本店有过订单的客人',
    ]
    meaning = '高价值复购客：LTV>5000 且带复购/高价值标签'
  } else if (r === 'family' || (r.startsWith('family') && !r.includes('and'))) {
    where.push(TAG_EXISTS(['family']))
    bullets = ['标签：亲子家庭（family）', '范围：本店有过订单的客人']
    meaning = '亲子家庭客：带有 family 标签'
  } else if (r.includes('churn')) {
    where.push('IFNULL(g.churn_risk, 0) >= 0.7')
    bullets = ['流失风险 churn_risk ≥ 0.7', '范围：本店有过订单的客人']
    meaning = '高流失风险：churn_risk ≥ 0.7'
  } else if (
    r === 'business' ||
    (r.includes('business') && !r.includes('ltv') && !r.includes('cancel'))
  ) {
    where.push(TAG_EXISTS(['business']))
    bullets = ['标签：商务常旅客（business）', '范围：本店有过订单的客人']
    meaning = '商务常旅客：带有 business 标签'
  } else if (r === 'vip') {
    where.push(
      `(` +
        `LOWER(IFNULL(g.vip_level,'')) IN ('silver','gold','platinum','diamond')` +
        ` OR ${TAG_EXISTS(['vip'])}` +
        `)`,
    )
    bullets = ['会员等级 ∈ 银/金/白金/钻石，或带 VIP 标签', '范围：本店有过订单的客人']
    meaning = 'VIP 会员：等级或 vip 标签'
  } else if (r === 'new_guest' || r.includes('new_guest')) {
    where.push('IFNULL(g.ltv, 0) < 800')
    where.push(`LOWER(IFNULL(g.vip_level,'')) IN ('', 'normal')`)
    bullets = ['近似本月新客：LTV < 800 且非 VIP', '范围：本店有过订单的客人']
    meaning = '本月新客（近似规则）'
  } else if (r.includes('high_intent')) {
    where.push('IFNULL(g.ltv, 0) > 2000')
    where.push('IFNULL(g.churn_risk, 1) < 0.55')
    bullets = ['LTV > 2000 且流失风险 < 0.55', '范围：本店有过订单的客人']
    meaning = '高意向未转化'
  } else if (r.includes('repeat')) {
    where.push(TAG_EXISTS(['repeat']))
    bullets = ['标签：复购客（repeat）', '范围：本店有过订单的客人']
    meaning = '复购客'
  } else {
    return null
  }

  const sql =
    'SELECT g.id, g.name, g.one_id, g.ltv, g.vip_level, g.churn_risk\n' +
    'FROM guests g\n' +
    'WHERE ' +
    where.join('\n  AND ')

  return {
    source: 'dsl',
    sourceLabel: '过滤条件（SQL）',
    expression: sql,
    sql,
    meaning,
    bullets,
  }
}

const SNAPSHOT_SQL =
  'SELECT g.id, g.name, g.one_id, g.ltv\n' +
  'FROM guests g\n' +
  'JOIN segment_members sm ON sm.guest_id = g.id\n' +
  'WHERE sm.segment_id = :segment_id'

export function explainSegmentRule(
  raw: string | null | undefined,
  segmentName?: string,
): RuleExplain {
  const expression = (raw || '').trim()
  if (!expression || expression === '—') {
    return {
      source: 'snapshot',
      sourceLabel: '过滤条件（SQL）',
      expression: SNAPSHOT_SQL,
      sql: SNAPSHOT_SQL,
      meaning: segmentName
        ? `无规则表达式：列表成员来自「${segmentName}」已保存名单（segment_members）`
        : '无规则表达式：仅按分群已保存成员名单展示',
      bullets: [
        '下方列表 = 保存时写入的 guest_id，不是现场重算全库',
        '关联：segment_members.guest_id = guests.id',
      ],
    }
  }

  // FilterSpec JSON
  if (expression.startsWith('{')) {
    try {
      const spec = JSON.parse(expression) as NlSpec
      const sql = filterSpecToSql(spec)
      const bullets: string[] = []
      if (spec.window_days && spec.order_status?.length)
        bullets.push(`时间窗：近 ${spec.window_days} 天`)
      if (spec.order_status?.length) {
        bullets.push(`订单状态：${spec.order_status.map((s) => TAG_CN[s] || s).join(' / ')}`)
      }
      if (spec.tag_codes_any?.length) {
        bullets.push(`须同时具备标签：${spec.tag_codes_any.map((t) => TAG_CN[t] || t).join(' + ')}`)
      } else if (spec.order_status?.includes('cancelled')) {
        bullets.push('不限标签：凡本店近窗内有取消单的房客（guest_id 非空）')
      }
      if (spec.min_stays) bullets.push(`实住次数 ≥ ${spec.min_stays}`)
      if (spec.require_children_orders) bullets.push('须有带儿童订单或亲子标签')
      if (spec.query) bullets.push(`原始描述：「${spec.query}」`)
      bullets.push('关联：orders.guest_id = guests.id')
      return {
        source: 'nl',
        sourceLabel: '过滤条件（SQL）',
        expression: sql,
        sql,
        meaning: bullets.slice(0, 3).join('；') || '自然语言条件已编译为 SQL',
        bullets,
      }
    } catch {
      /* fall through */
    }
  }

  const dsl = dslToSql(expression)
  if (dsl) return dsl

  if (looksLikeNl(expression)) {
    const spec = parseNlToSpec(expression)
    const sql = filterSpecToSql(spec)
    const bullets: string[] = []
    if (spec.order_status?.length) {
      bullets.push(`时间窗：近 ${spec.window_days} 天`)
      bullets.push(`订单状态：${spec.order_status.map((s) => TAG_CN[s] || s).join(' / ')}`)
    }
    if (spec.tag_codes_any?.length) {
      bullets.push(`标签：${spec.tag_codes_any.map((t) => TAG_CN[t] || t).join(' + ')}`)
    }
    if (!bullets.length) bullets.push(`按短语解析：${expression}`)
    bullets.push('关联：orders.guest_id = guests.id')
    return {
      source: 'nl',
      sourceLabel: '过滤条件（SQL）',
      expression: sql,
      sql,
      meaning: bullets.slice(0, 3).join('；'),
      bullets,
    }
  }

  const unknownSql = SNAPSHOT_SQL + `\n-- 未能将规则编译为可复算条件：${expression.slice(0, 80)}`
  return {
    source: 'unknown',
    sourceLabel: '过滤条件（SQL）',
    expression: unknownSql,
    sql: unknownSql,
    meaning: `规则「${expression}」暂无专用编译器，列表按已保存成员展示`,
    bullets: [`原始规则：${expression}`, '展示名单来自 segment_members，非现场重算'],
  }
}

/** 行级「为何在此分群」简要说明 */
export function guestHitHint(guest: any, expression: string): string {
  const bits: string[] = []
  const ltv = Number(guest.ltv || guest.spend || 0)
  const tags = (guest.tags || []).map((t: string) => String(t))
  const churn = Number(guest.churn_risk || 0)
  const expr = (expression || '').trim()

  const nl = looksLikeNl(expr) || expr.startsWith('{') || /cancelled|status IN/i.test(expr)
  if (nl) bits.push('命中近窗取消/订单条件（名单已按 SQL 锁定）')
  if (/ltv\s*>\s*5000/i.test(expr) || expr.includes('ltv>5000')) {
    bits.push(`LTV ¥${ltv.toLocaleString('zh-CN')}`)
  }
  if (/churn/i.test(expr) && churn >= 0.5) {
    bits.push(`流失风险 ${(churn * 100).toFixed(0)}%`)
  }
  const hitTags = tags
    .filter((t: string) => /商务|亲子|复购|回头|常客|VIP|高价值|家庭/.test(t))
    .slice(0, 2)
  if (hitTags.length) bits.push(`标签：${hitTags.join('、')}`)
  if (!bits.length && tags.length) bits.push(`标签：${tags.slice(0, 2).join('、')}`)
  if (!bits.length) bits.push('分群已保存成员')
  return bits.join(' · ')
}
