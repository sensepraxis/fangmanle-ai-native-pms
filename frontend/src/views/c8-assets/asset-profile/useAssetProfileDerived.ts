// SPDX-License-Identifier: Apache-2.0
import { computed, type Ref } from 'vue'
import { t } from '../../../lib/i18n'
import { localizeSeedText } from '../../../lib/localizeSeed'

export function fmtDate(raw?: string | null) {
  if (!raw) return '—'
  return String(raw).slice(0, 10)
}

export function fmtDateTime(raw?: string | null) {
  if (!raw) return '—'
  return String(raw).replace('T', ' ').slice(0, 16)
}

export function fmtMoney(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return '—'
  return `¥${Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
}

export function fmtInt(n: number) {
  return `¥${Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

export function statusLabelMaint(s?: string) {
  if (s === 'done') return t('已完成')
  if (s === 'overdue') return t('逾期')
  if (s === 'doing') return t('处理中')
  return t('计划中')
}

export function statusClsMaint(s?: string) {
  if (s === 'done') return 'var(--primary)'
  if (s === 'overdue') return 'var(--error)'
  if (s === 'doing') return '#0d9488'
  return 'var(--on-surface-variant)'
}

/** 按品类估算使用年限（年），用于预估报废节点 */
function usefulLifeYears(category?: string) {
  const c = (category || '').toLowerCase()
  if (c.includes('电梯')) return 15
  if (c.includes('暖通') || c.includes('空调')) return 10
  if (c.includes('电视') || c.includes('电器')) return 8
  if (c.includes('弱电') || c.includes('监控')) return 8
  if (c.includes('客房')) return 6
  return 8
}

const DAY_MS = 86400000

function pad2(n: number) {
  return String(n).padStart(2, '0')
}

function chartYearMonth(d: Date) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}`
}

function addCalendarYears(base: Date, years: number) {
  const d = new Date(base.getTime())
  d.setFullYear(d.getFullYear() + years)
  return d
}

export function useAssetProfileDerived(opts: {
  raw: Ref<any>
  alerts: Ref<any[]>
  assetEvents: Ref<any[]>
  workOrders: Ref<any[]>
}) {
  const { raw, alerts, assetEvents, workOrders } = opts

  const a = computed(() => raw.value || {})

  const assetNo = computed(
    () => a.value.asset_no || a.value.sn || `EQ-${String(a.value.id || 0).padStart(5, '0')}`,
  )

  const statusLabel = computed(() => {
    const s = a.value.status
    if (s === 'active') return t('在用')
    if (s === 'maintenance') return t('维保中')
    if (s === 'retired') return t('已报废')
    if (s === 'abnormal') return t('故障')
    return localizeSeedText(a.value.health_label) || t('在用')
  })

  const location = computed(() => {
    if (a.value.room_no) return t('{n} 房', { n: a.value.room_no })
    return localizeSeedText(a.value.location) || '—'
  })

  const assetInfo = computed(() => ({
    location: location.value,
    inbound: a.value.purchase_date || '—',
    supplier: localizeSeedText(a.value.supplier) || '—',
    dept: localizeSeedText(a.value.dept) || t('工程维保部'),
  }))

  const iotMetrics = computed(() => {
    const stability =
      a.value.health_score != null
        ? `${Number(a.value.health_score).toFixed(a.value.health_score % 1 ? 1 : 0)}%`
        : '—'
    return [
      {
        label: t('累计工作时长'),
        value: a.value.runtime_hours != null ? Number(a.value.runtime_hours).toLocaleString() : '—',
        unit: 'h',
        iconBg: 'var(--primary-container)',
        iconFg: 'var(--on-primary-container)',
        icon: 'schedule',
        primary: false,
      },
      {
        label: t('平均功耗'),
        value: a.value.avg_power_w != null ? String(a.value.avg_power_w) : '—',
        unit: 'W/h',
        iconBg: 'var(--secondary-container)',
        iconFg: 'var(--on-secondary-container)',
        icon: 'bolt',
        primary: false,
      },
      {
        label: t('连接稳定性'),
        value: stability,
        unit: '',
        iconBg: 'var(--surface-container-high)',
        iconFg: 'var(--primary)',
        icon: 'wifi',
        primary: true,
      },
    ]
  })

  const metrics = computed(() => {
    const pv = Number(a.value.purchase_value || 0)
    const cv = Number(a.value.current_value ?? pv)
    const rc = Number(a.value.repair_cost_total || 0)
    const health = Number(a.value.health_score || 0)
    const ratio = pv > 0 ? Math.round((rc / pv) * 100) : 0
    const years = a.value.purchase_date
      ? Math.max(
          0,
          Math.round(
            (Date.now() - new Date(a.value.purchase_date).getTime()) / (365.25 * 86400000),
          ),
        )
      : null
    const residual = pv > 0 ? Math.round((cv / pv) * 100) : 0
    return { pv, cv, rc, health, ratio, years, residual }
  })

  const failureRiskBreakdown = computed(() => {
    const m = metrics.value
    const repairPart = m.ratio * 0.5
    const healthGap = Math.max(0, 70 - m.health)
    const healthPart = healthGap * 0.4
    const ageApplied = m.years != null && m.years >= 8
    const ageBonus = ageApplied ? 12 : 0
    const residualApplied = m.residual < 30
    const residualBonus = residualApplied ? 10 : 0
    const subtotal = repairPart + healthPart + ageBonus + residualBonus
    const replaceIdx = Math.min(99, Math.round(subtotal))
    const displayPct = Math.min(95, Math.max(5, replaceIdx))

    const round1 = (n: number) => Math.round(n * 10) / 10

    return {
      inputs: {
        purchaseValue: m.pv,
        repairCost: m.rc,
        repairRatio: m.ratio,
        healthScore: m.health,
        yearsServed: m.years,
        residualPct: m.residual,
        currentValue: m.cv,
      },
      steps: [
        {
          label: t('维修成本因子'),
          formula: t('维修占原值比例 × 0.5'),
          calc: `${m.ratio}% × 0.5`,
          points: round1(repairPart),
        },
        {
          label: t('健康分因子'),
          formula: t('max(0, 70 − 健康分) × 0.4'),
          calc: `max(0, 70 − ${m.health}) × 0.4`,
          points: round1(healthPart),
        },
        {
          label: t('服役年限加成'),
          formula: t('服役 ≥ 8 年时 +12'),
          calc: ageApplied
            ? t('已服役 {n} 年，触发 +12', { n: m.years ?? '—' })
            : t('已服役 {n} 年，未触发', { n: m.years ?? '—' }),
          points: ageBonus,
          inactive: !ageApplied,
        },
        {
          label: t('残值率加成'),
          formula: t('净值残值率 < 30% 时 +10'),
          calc: residualApplied
            ? t('残值率 {n}% < 30%，触发 +10', { n: m.residual })
            : t('残值率 {n}%，未触发', { n: m.residual }),
          points: residualBonus,
          inactive: !residualApplied,
        },
      ],
      subtotal: round1(subtotal),
      replaceIndex: replaceIdx,
      displayPct,
      clampNote:
        replaceIdx < 5
          ? t('修换指数低于 5，仪表盘显示下限 5%')
          : replaceIdx > 95
            ? t('修换指数高于 95，仪表盘显示上限 95%')
            : t('仪表盘显示值与修换指数一致'),
    }
  })

  const replaceIndex = computed(() => failureRiskBreakdown.value.replaceIndex)

  const verdict = computed(() => {
    const i = replaceIndex.value
    if (i >= 75) return { label: t('建议报废 / 更换'), tone: 'replace' as const }
    if (i >= 50) return { label: t('建议评估后决策'), tone: 'quote' as const }
    return { label: t('建议继续使用'), tone: 'ok' as const }
  })

  const needsRepair = computed(
    () =>
      a.value.status === 'abnormal' ||
      Number(a.value.health_score || 100) < 55 ||
      alerts.value.some((al) => al.severity === 'high'),
  )

  const aiConf = computed(() =>
    Math.min(96, Math.max(78, 82 + Math.round(metrics.value.health / 8))),
  )

  const fallbackNextAction = computed(() => {
    const m = metrics.value
    const name = localizeSeedText(a.value.name) || t('该设备')
    if (verdict.value.tone === 'replace') {
      return {
        conf: aiConf.value,
        text: t(
          '{name}（{loc}）：累计维修 ¥{rc}，占原值 {ratio}%，健康分 {health}。AI 建议走采购更换或报废流程，避免继续投入无效维修成本。',
          {
            name,
            loc: location.value,
            rc: m.rc.toLocaleString(),
            ratio: m.ratio,
            health: m.health,
          },
        ),
      }
    }
    if (needsRepair.value) {
      return {
        conf: aiConf.value,
        text: t('{name} 当前状态为「{status}」。建议生成维修工单并指派工程部，优先处理 {issue}。', {
          name,
          status: statusLabel.value,
          issue: localizeSeedText(alerts.value[0]?.message) || t('设备异常'),
        }),
      }
    }
    if (a.value.insight) {
      return { conf: aiConf.value, text: localizeSeedText(a.value.insight) }
    }
    return {
      conf: aiConf.value,
      text: t('{name} 运行平稳，健康分 {health}。建议按计划在 {date} 完成预防性维保。', {
        name,
        health: m.health,
        date: a.value.next_maintain_date || t('下月'),
      }),
    }
  })

  const openWorkOrders = computed(() =>
    workOrders.value.filter(
      (w) => (w.rawStatus || w.status) !== 'done' && w.status !== t('已完成'),
    ),
  )

  const maintCount = computed(() => workOrders.value.length)

  /** 运行性能雷达 */
  const perfRadar = computed(() => {
    const h = metrics.value.health || 70
    const id = a.value.id || 1
    const base = 50 + (id % 10)
    const axes = [
      { label: t('运行效率'), score: Math.min(95, base + Math.round(h * 0.35)), angle: -90 },
      {
        label: t('能耗表现'),
        score: Math.min(92, base + Math.round(100 - Number(a.value.avg_power_w || 120) / 3)),
        angle: -30,
      },
      { label: t('稳定性'), score: Math.min(95, h), angle: 30 },
      { label: t('振动/噪音'), score: Math.min(90, base + Math.round(h * 0.3)), angle: 90 },
      { label: t('温控精度'), score: Math.min(88, base + Math.round(h * 0.28)), angle: 150 },
      { label: t('IoT 在线'), score: Math.min(93, base + Math.round(h * 0.32)), angle: 210 },
    ]
    const pts = axes.map((ax, i) => {
      const ang = (-90 + i * 60) * (Math.PI / 180)
      const r = (ax.score / 100) * 40
      return { x: 50 + r * Math.cos(ang), y: 50 + r * Math.sin(ang), ...ax }
    })
    const poly = pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
    return { axes, pts, poly }
  })

  /** 成本指纹 */
  const costFingerprint = computed(() => {
    const pv = metrics.value.pv
    const rc = metrics.value.rc
    const dep = Math.max(0, pv - metrics.value.cv)
    const labor = Math.round(rc * 0.45)
    const parts = Math.round(rc * 0.4)
    const outsource = Math.max(0, rc - labor - parts)
    const total = Math.max(pv, dep + rc, 1)
    const rows = [
      {
        name: t('采购原值'),
        amount: pv,
        pct: Math.round((pv / total) * 100),
        color: 'bg-primary',
        tip: '',
      },
      {
        name: t('累计折旧'),
        amount: dep,
        pct: Math.round((dep / total) * 100),
        color: 'bg-secondary',
        tip: t('净值残值 {n}%', { n: metrics.value.residual }),
      },
      {
        name: t('维修人工'),
        amount: labor,
        pct: Math.round((labor / total) * 100),
        color: 'bg-tertiary-container',
        tip: '',
      },
      {
        name: t('备件 / 外协'),
        amount: parts + outsource,
        pct: Math.round(((parts + outsource) / total) * 100),
        color: 'bg-outline',
        tip: maintCount.value ? t('关联工单 {n} 条', { n: maintCount.value }) : '',
      },
    ]
    return {
      total: pv,
      repairPct: metrics.value.ratio,
      rows,
      insightTitle: metrics.value.ratio >= 50 ? t('高维修成本设备') : t('成本结构均衡'),
      insightBody:
        metrics.value.ratio >= 50
          ? t('维修费已占原值 {n}%，高于同类设备均值。建议进入修换评估。', {
              n: metrics.value.ratio,
            })
          : t('折旧与维修成本可控，当前修换指数 {n}，可继续服役并关注预防性维保。', {
              n: replaceIndex.value,
            }),
    }
  })

  /** 价值折旧曲线：采购日 → 今日净值 → 预估报废（公历时间轴） */
  const depChart = computed(() => {
    const pv = metrics.value.pv
    const cv = metrics.value.cv
    const rc = metrics.value.rc
    const lifeYears = usefulLifeYears(a.value.category)

    const nowDate = new Date()
    const purchaseDate = a.value.purchase_date
      ? new Date(a.value.purchase_date)
      : new Date(nowDate.getTime() - Math.max(metrics.value.years ?? 3, 1) * 365.25 * DAY_MS)

    const purchaseTime = purchaseDate.getTime()
    const nowTime = nowDate.getTime()
    const scrapDate = addCalendarYears(purchaseDate, lifeYears)
    const scrapTime = scrapDate.getTime()
    const spanMs = Math.max(scrapTime - purchaseTime, DAY_MS)

    const daysSincePurchase = Math.max(0, (nowTime - purchaseTime) / DAY_MS)
    const salvage = Math.max(pv * 0.05, Math.min(cv, pv * 0.1))

    const valueAtTime = (t: number) => {
      if (t <= purchaseTime) return pv
      if (t <= nowTime) {
        const span = Math.max(nowTime - purchaseTime, DAY_MS)
        const ratio = (t - purchaseTime) / span
        return pv + (cv - pv) * ratio
      }
      const remain = Math.max(scrapTime - nowTime, DAY_MS)
      const ratio = (t - nowTime) / remain
      return cv + (salvage - cv) * Math.min(1, ratio)
    }

    const toX = (t: number) => ((t - purchaseTime) / spanMs) * 70

    const curveTimes: number[] = [purchaseTime]
    if (nowTime - purchaseTime >= DAY_MS) curveTimes.push(nowTime)
    curveTimes.push(scrapTime)

    const valuePts = curveTimes.map((t) => ({
      x: toX(t),
      y: 0,
      v: valueAtTime(t),
      time: t,
    }))

    const yMax = Math.max(pv * 1.08, rc * 1.15, cv * 1.05, 1)
    const toY = (v: number) => 95 - (Math.min(Math.max(v, 0), yMax) / yMax) * 90
    for (const p of valuePts) p.y = toY(p.v)

    const path = valuePts
      .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
      .join(' ')
    const lastPt = valuePts[valuePts.length - 1]
    const currentIdx = valuePts.findIndex((p) => p.time === nowTime)
    const currentPt = currentIdx >= 0 ? valuePts[currentIdx] : valuePts[0]

    const sameMonthPurchase =
      purchaseDate.getFullYear() === nowDate.getFullYear() &&
      purchaseDate.getMonth() === nowDate.getMonth()
    const mergePurchaseCurrent = daysSincePurchase < 45 && sameMonthPurchase

    const xLabels: { year: string; hint: string; x: number }[] = []
    if (mergePurchaseCurrent) {
      xLabels.push({
        year: chartYearMonth(purchaseDate),
        hint: t('采购·当前'),
        x: toX(nowTime),
      })
    } else {
      xLabels.push({
        year:
          daysSincePurchase < 730
            ? chartYearMonth(purchaseDate)
            : String(purchaseDate.getFullYear()),
        hint: t('采购'),
        x: toX(purchaseTime),
      })
      if (nowTime > purchaseTime + DAY_MS) {
        const currentYear = nowDate.getFullYear()
        const purchaseYear = purchaseDate.getFullYear()
        xLabels.push({
          year: currentYear === purchaseYear ? chartYearMonth(nowDate) : String(currentYear),
          hint: t('当前'),
          x: toX(nowTime),
        })
      }
    }
    xLabels.push({
      year: String(scrapDate.getFullYear()),
      hint: t('预估报废'),
      x: toX(scrapTime),
    })

    if (daysSincePurchase > 400) {
      const usedYears = new Set(xLabels.map((lb) => lb.year.slice(0, 4)))
      for (let y = purchaseDate.getFullYear() + 1; y < scrapDate.getFullYear(); y += 1) {
        if (usedYears.has(String(y))) continue
        const t = new Date(purchaseDate)
        t.setFullYear(y)
        if (
          t.getTime() >= purchaseTime &&
          t.getTime() <= scrapTime &&
          t.getTime() < nowTime - 180 * DAY_MS
        ) {
          xLabels.push({ year: String(y), hint: '', x: toX(t.getTime()) })
          usedYears.add(String(y))
        }
      }
      xLabels.sort((a, b) => a.x - b.x)
    }

    const repairByYear: Record<number, number> = {}
    for (const e of assetEvents.value) {
      if (!['repair', 'maintain'].includes(e.event_type)) continue
      const cost = Number(e.cost || 0)
      if (!cost || !e.happened_at) continue
      const yr = Math.max(
        0,
        Math.floor((new Date(e.happened_at).getTime() - purchaseTime) / (365.25 * DAY_MS)),
      )
      repairByYear[yr] = (repairByYear[yr] || 0) + cost
    }
    let cumRepair = 0
    const repairPts: { x: number; y: number; v: number }[] = [
      { x: toX(purchaseTime), y: toY(0), v: 0 },
    ]
    const maxRepairYear = Math.ceil((nowTime - purchaseTime) / (365.25 * DAY_MS))
    for (let yr = 0; yr <= maxRepairYear; yr += 1) {
      cumRepair += repairByYear[yr] || 0
      const t = purchaseTime + yr * 365.25 * DAY_MS
      if (t <= nowTime) repairPts.push({ x: toX(t), y: toY(cumRepair), v: cumRepair })
    }
    if (rc > 0 && cumRepair < rc * 0.5) {
      repairPts.push({ x: toX(nowTime), y: toY(rc), v: rc })
    }
    const repairPath =
      repairPts.length > 1
        ? repairPts
            .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
            .join(' ')
        : `M0,${toY(0)} L${toX(nowTime).toFixed(1)},${toY(0)}`

    const labels = [5, 4, 3, 2, 1, 0].map((i) => {
      const v = Math.round((yMax / 5) * i)
      return v >= 1000 ? `${Math.round(v / 1000)}k` : String(v)
    })

    const purchaseCalYear = purchaseDate.getFullYear()

    return {
      labels,
      path,
      areaPath: `${path} L${lastPt.x.toFixed(1)},100 L0,100 Z`,
      repairPath,
      points: valuePts,
      tipX: currentPt.x,
      tipY: currentPt.y,
      estValue: cv,
      xLabels,
      salvageLine: toY(salvage),
      currentPointIndex: currentIdx >= 0 ? currentIdx : 0,
      lifeYears,
      purchaseCalYear,
      daysSincePurchase: Math.round(daysSincePurchase),
    }
  })

  const failurePct = computed(() => failureRiskBreakdown.value.displayPct)
  const failureLabel = computed(() => {
    const p = failurePct.value
    if (p >= 70)
      return {
        text: t('高故障风险'),
        cls: 'text-red-600',
        tip: t('建议尽快更换或报废。'),
        badge: 'bg-red-50 border-red-200',
      }
    if (p >= 45)
      return {
        text: t('中等风险'),
        cls: 'text-amber-600',
        tip: t('需加强巡检与维保。'),
        badge: 'bg-amber-50 border-amber-200',
      }
    return {
      text: t('低风险 · 稳定'),
      cls: 'text-emerald-600',
      tip: t('设备运行平稳。'),
      badge: 'bg-emerald-50 border-emerald-200',
    }
  })
  const needleDeg = computed(() => -90 + (failurePct.value / 100) * 180)

  return {
    a,
    assetNo,
    statusLabel,
    location,
    assetInfo,
    iotMetrics,
    metrics,
    failureRiskBreakdown,
    replaceIndex,
    verdict,
    needsRepair,
    aiConf,
    fallbackNextAction,
    openWorkOrders,
    maintCount,
    perfRadar,
    costFingerprint,
    depChart,
    failurePct,
    failureLabel,
    needleDeg,
    fmtDate,
    fmtDateTime,
    fmtMoney,
    fmtInt,
    statusLabelMaint,
    statusClsMaint,
  }
}
