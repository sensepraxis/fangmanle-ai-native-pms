// SPDX-License-Identifier: Apache-2.0
/**
 * 客户 360：加载、派生指标、雷达/指纹/LTV/轨迹、优惠券核销
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, type RouteLocationNormalizedLoaded } from 'vue-router'
import { api } from '../../lib/api'
import { fmt, VIP_CN, ORDER_ST_CN } from '../../lib/ui'
import { t, getLocale } from '../../lib/i18n'

export type TrailEvt = {
  title: string
  sub: string
  when: string
  time: string
  body: string
  mood?: string
  ai?: string
  tone: 'primary' | 'ai' | 'ok'
  sortAt?: string
}

export function useGuest360(route?: RouteLocationNormalizedLoaded) {
  const r = route || useRoute()
  const d = ref<any>(null)
  const loading = ref(true)
  const oneidExpanded = ref(false)

  const COUPON_ST_CN = computed<Record<string, string>>(() => ({
    active: t('有效'),
    used: t('已使用'),
    expired: t('已过期'),
  }))
  const REDEEM_CN = computed<Record<string, string>>(() => ({
    unused: t('未核销'),
    redeemed: t('已核销'),
  }))
  const redeemBusyId = ref<number | null>(null)
  const redeemCode = ref('')
  const redeemCodeBusy = ref(false)
  const redeemHint = ref('')
  const redeemErr = ref('')
  const redeemModal = ref<{ coupon: any; orderId: number | null } | null>(null)

  function identitySourceLabel(i: any) {
    const raw = i?.source_cn || i?.source
    return t(String(raw || '其他'))
  }

  async function load() {
    loading.value = true
    try {
      d.value = await api.guest360(Number(r.params.id))
    } finally {
      loading.value = false
    }
  }
  onMounted(load)
  watch(() => r.params.id, load)
  watch(
    () => r.query.oneid,
    (v) => {
      if (v === 'open') oneidExpanded.value = true
    },
    { immediate: true },
  )

  function toggleOneidAudit() {
    oneidExpanded.value = !oneidExpanded.value
  }

  const g = computed(() => d.value?.guest || {})
  const h5Membership = computed(() => d.value?.h5_membership || null)
  const orders = computed(() => d.value?.orders || [])
  const tags = computed(() => d.value?.tags || [])
  const identities = computed(() => d.value?.identities || [])
  const reviews = computed(() => d.value?.reviews || [])
  const wecom = computed(() => d.value?.private_channel || d.value?.wecom || null)
  const wecomBound = computed(
    () =>
      !!wecom.value?.bound ||
      !!wecom.value?.channel_reachable ||
      !!d.value?.channel_reachable ||
      !!d.value?.in_wecom_private,
  )
  const inWecomPrivate = computed(() => wecomBound.value)
  const channelReachable = inWecomPrivate
  const coupons = computed(() => d.value?.coupons || wecom.value?.coupons || [])
  const wecomExternalId = computed(() => wecom.value?.external_userid || '')
  const phoneDisplay = computed(() => {
    const p = String(g.value.phone || '').replace(/\D/g, '')
    if (!p) return '—'
    if (
      wecomBound.value ||
      identities.value.some((i: any) => (i.source || '').toLowerCase() === 'wecom')
    ) {
      return p.length === 11 ? `${p.slice(0, 3)} ${p.slice(3, 7)} ${p.slice(7)}` : p
    }
    if (p.length >= 7) return `+86 ${p.slice(0, 3)} **** ${p.slice(-4)}`
    return g.value.phone || '—'
  })

  const vipLabel = computed(() => VIP_CN[g.value.vip_level] || g.value.vip_level || t('普通'))
  const stayCount = computed(() => orders.value.length)
  const avgTicket = computed(() => {
    if (!orders.value.length) return 0
    const sum = orders.value.reduce((s: number, o: any) => s + Number(o.total_amount || 0), 0)
    return sum / orders.value.length
  })
  const ltvScore = computed(() => {
    const ltv = Number(g.value.ltv || 0)
    const score = Math.min(10, Math.max(4, 4 + ltv / 3000))
    return score.toFixed(1)
  })
  const churnPct = computed(() => Math.round(Number(g.value.churn_risk || 0) * 100))
  const channelCount = computed(() => Math.max(1, identities.value.length || 1))
  const mergeConfidence = computed(() => {
    const list = identities.value
    if (!list.length) return 98
    const avg = list.reduce((s: number, i: any) => s + Number(i.confidence || 0.9), 0) / list.length
    return Math.round(avg * 100)
  })
  const oneIdLabel = computed(
    () => g.value.one_id || `ONE${String(g.value.id || 0).padStart(6, '0')}`,
  )
  const channelChips = computed(() => {
    const names = identities.value.map((i: any) => identitySourceLabel(i))
    const uniq = [...new Set(names.filter(Boolean))]
    return uniq.length ? uniq : [t('本店直客')]
  })
  const sourceBars = computed(() => {
    const list = identities.value
    const palette = [
      { box: 'bg-blue-100 text-blue-600' },
      { box: 'bg-green-100 text-green-600' },
      { box: 'bg-orange-100 text-orange-600' },
      { box: 'bg-purple-100 text-purple-600' },
    ]
    if (!list.length) {
      return [{ name: t('私域流量（直订）'), pct: 100, ...palette[2] }]
    }
    const bag: Record<string, number> = {}
    for (const i of list) {
      const n = identitySourceLabel(i)
      bag[n] = (bag[n] || 0) + 1
    }
    const total = Object.values(bag).reduce((a, b) => a + b, 0) || 1
    return Object.entries(bag).map(([name, c], i) => ({
      name,
      pct: Math.round((c / total) * 100),
      ...palette[i % palette.length],
    }))
  })
  const nextStay = computed(() => {
    const upcoming = orders.value.find((o: any) =>
      ['pending', 'confirmed', 'checked_in'].includes(o.status),
    )
    return upcoming || orders.value[0] || null
  })
  const nextStayNights = computed(() => {
    const o = nextStay.value
    if (!o?.check_in || !o?.check_out) return 0
    const a = new Date(o.check_in).getTime()
    const b = new Date(o.check_out).getTime()
    if (!Number.isFinite(a) || !Number.isFinite(b) || b <= a) return 1
    return Math.max(1, Math.round((b - a) / 86400000))
  })
  const sentiment = computed(() => {
    if (!reviews.value.length) {
      return {
        label: t('暂无点评'),
        tip: t('尚无历史评价记录'),
        cls: 'text-on-surface-variant',
        ring: 'bg-surface-container-high border-outline-variant',
      }
    }
    const avg =
      reviews.value.reduce((s: number, rev: any) => s + Number(rev.rating || 0), 0) /
      reviews.value.length
    if (avg >= 4) {
      return {
        label: t('正面 / 感激'),
        tip: t('基于 {n} 条历史评论与互动。', { n: reviews.value.length }),
        cls: 'text-green-700',
        ring: 'bg-green-50 border-green-100',
      }
    }
    if (avg >= 3) {
      return {
        label: t('中性'),
        tip: t('基于 {n} 条历史评论。', { n: reviews.value.length }),
        cls: 'text-amber-700',
        ring: 'bg-amber-50 border-amber-100',
      }
    }
    return {
      label: t('需关怀'),
      tip: t('基于 {n} 条历史评论。', { n: reviews.value.length }),
      cls: 'text-red-700',
      ring: 'bg-red-50 border-red-100',
    }
  })

  const ROOM_PREF_RE =
    /安静|静音|无烟|高楼|高层|低楼|低层|景观|山景|江景|海景|枕头|乳胶|硬枕|软枕|荞麦|矿泉水|夜床|开夜床|管家|亲子|家庭|儿童|加床|无障碍|quiet|high.?floor|pillow|water|turndown/i
  const roomPrefs = computed(() => {
    const names = tags.value.map((tg: any) => String(tg.name || ''))
    const hit = names.filter((n) => ROOM_PREF_RE.test(n))
    if (hit.length) return hit.slice(0, 5).map((n) => t(n))
    return [t('中高楼层优先'), t('远离电梯/制冰机'), t('标准枕 + 备用荞麦枕'), t('额外矿泉水')]
  })
  const prefs = roomPrefs
  const motiveTags = computed(() => {
    const names = tags.value.map((x: any) => x.name)
    return {
      primary: names[0] ? t(String(names[0])) : t('商务旅客'),
      secondary: names[1] ? t(String(names[1])) : t('周末休闲'),
    }
  })

  const nextAction = computed(() => {
    const name = g.value.name || t('该客人')
    const honor = g.value.gender === 'F' ? t('女士') : t('先生')
    const conf = Math.min(
      96,
      Math.max(78, 80 + stayCount.value * 2 + Math.round(mergeConfidence.value / 10)),
    )
    const b = String(g.value.birthday || '')
    const m = b.match(/^\d{4}-(\d{2})-(\d{2})/)
    if (m) {
      const month = Number(m[1])
      const day = Number(m[2])
      return {
        conf,
        text: t(
          '预测{name}{honor}将在 {month} 月 {day} 日前后迎来生日到访窗口。建议在入住前 3 天推送「专属礼遇套餐」，结合偏好「{pref}」安排欢迎礼与延迟退房预授权。',
          { name, honor, month, day, pref: prefs.value[0] || t('安静客房') },
        ),
      }
    }
    if (nextStay.value) {
      return {
        conf,
        text: t(
          '预测{name}{honor}即将入住（{checkIn}）。建议提前同步偏好「{prefs}」，并推送与 LTV {ltv} 匹配的升单方案。',
          {
            name,
            honor,
            checkIn: nextStay.value.check_in,
            prefs:
              prefs.value.slice(0, 2).join(getLocale() === 'en' ? ', ' : '、') || t('标准化服务'),
            ltv: fmt(g.value.ltv),
          },
        ),
      }
    }
    return {
      conf,
      text: t(
        '基于 {n} 次入住与标签「{tag}」，建议在下次触达时推送个性化关怀，降低流失风险（当前 {pct}%）。',
        { n: stayCount.value, tag: prefs.value[0] || t('高价值'), pct: churnPct.value },
      ),
    }
  })

  const psychRadar = computed(() => {
    const names = tags.value.map((tg: any) => String(tg.name || ''))
    const hit = (re: RegExp) => names.some((n) => re.test(n))
    const base = 55 + ((g.value.id || 0) % 12)
    const quiet = Math.min(
      95,
      base + (hit(/安静|静音|无烟/) ? 28 : 8) + Math.min(10, stayCount.value),
    )
    const highFloor = Math.min(95, base + (hit(/高楼|高层|景观|山景|江景/) ? 30 : 12))
    const turndown = Math.min(
      90,
      48 + (hit(/夜床|开夜床|管家/) ? 25 : 10) + Math.round(Number(g.value.ltv || 0) / 2000),
    )
    const spicy = Math.min(92, 50 + (hit(/餐饮|美食|辣|口味/) ? 28 : 15))
    const express = Math.min(
      90,
      52 + (hit(/效率|快速|商务/) ? 22 : 8) + Math.min(15, stayCount.value * 2),
    )
    const pillow = Math.min(88, 50 + (hit(/枕头|乳胶|硬枕|软枕/) ? 26 : 12))
    const axes = [
      { label: t('静音要求极高'), score: quiet, angle: -90 },
      { label: t('偏好高楼层'), score: highFloor, angle: -30 },
      { label: t('夜床服务'), score: turndown, angle: 30 },
      { label: t('重口味/餐饮'), score: spicy, angle: 90 },
      { label: t('快速退房'), score: express, angle: 150 },
      { label: t('枕具偏好'), score: pillow, angle: 210 },
    ]
    const pts = axes.map((a, i) => {
      const ang = (-90 + i * 60) * (Math.PI / 180)
      const rad = (a.score / 100) * 40
      return { x: 50 + rad * Math.cos(ang), y: 50 + rad * Math.sin(ang), ...a }
    })
    const poly = pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
    return { axes, pts, poly }
  })

  const fingerprint = computed(() => {
    const ttv = Math.max(0, Number(g.value.ltv || 0))
    const tagBoost = tags.value.some((tg: any) => /餐饮|美食|SPA|康体/.test(String(tg.name || '')))
      ? 0.05
      : 0
    const roomR = Math.max(0.42, 0.55 - tagBoost)
    const fbR = 0.22 + tagBoost + Math.min(0.08, stayCount.value * 0.008)
    const spaR = 0.12 + (['gold', 'platinum'].includes(String(g.value.vip_level || '')) ? 0.04 : 0)
    const room = Math.round(ttv * roomR)
    const fb = Math.round(ttv * fbR)
    const spa = Math.round(ttv * spaR)
    const other = Math.max(0, Math.round(ttv - room - fb - spa))
    const anc = fb + spa + other
    const ancPct = ttv ? Math.round((anc / ttv) * 100) : 0
    const fbPct = ttv ? Math.round((fb / ttv) * 100) : 0
    const fbPrefs = prefs.value
      .filter((p) => /餐|食|水|酒|吧|Room|dining|water|bar/i.test(p))
      .slice(0, 2)
    return {
      ttv,
      ancPct,
      rows: [
        {
          name: t('客房消费 (Room)'),
          amount: room,
          pct: ttv ? Math.round((room / ttv) * 100) : 0,
          color: 'bg-primary',
          tip: '',
        },
        {
          name: t('餐饮 (F&B)'),
          amount: fb,
          pct: fbPct,
          color: 'bg-tertiary-container',
          tip: prefs.value.find((p) => /餐|食|水|酒|Room|dining|water/i.test(p))
            ? t('主要偏好：{prefs}', {
                prefs: fbPrefs.join(getLocale() === 'en' ? ', ' : '、') || t('客房送餐'),
              })
            : t('主要偏好：客房送餐、大堂吧'),
        },
        {
          name: t('水疗与康体 (Spa)'),
          amount: spa,
          pct: ttv ? Math.round((spa / ttv) * 100) : 0,
          color: 'bg-secondary',
          tip: '',
        },
        {
          name: t('其他 (交通/洗衣等)'),
          amount: other,
          pct: ttv ? Math.round((other / ttv) * 100) : 0,
          color: 'bg-outline',
          tip: '',
        },
      ],
      insightTitle: fbPct >= 25 ? t('高净值餐饮转化客户') : t('均衡消费结构客户'),
      insightBody:
        fbPct >= 25
          ? t(
              '该客人的 F&B 占比约 {pct}%，高于同级别会员均值。建议下次预订优先推荐含餐饮抵扣的房价计划。',
              { pct: fbPct },
            )
          : t('客房占比主导，ANC 约 {ancPct}%。可结合偏好标签「{tag}」轻推附加体验。', {
              ancPct,
              tag: prefs.value[0] || t('升单'),
            }),
    }
  })

  function fmtInt(n: number) {
    return `¥${Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
  }

  const estLtv = computed(
    () => Math.round(Number(g.value.ltv || 0) * 1.12) || Math.round(Number(g.value.ltv || 0) * 1.1),
  )
  const riskLabel = computed(() => {
    const p = churnPct.value
    const factorTip = (g.value.churn_factors || [])
      .slice(0, 2)
      .map((x: string) => t(String(x)))
      .join(getLocale() === 'en' ? '; ' : '；')
    if (p >= 50) {
      return {
        text: t('高风险'),
        cls: 'text-red-600',
        tip: factorTip || t('近期活跃下降，建议立即召回。'),
        badge: 'bg-red-50 border-red-200',
      }
    }
    if (p >= 30) {
      return {
        text: t('中等风险'),
        cls: 'text-amber-600',
        tip: factorTip || t('已出现流失苗头，可发送个性化优惠。'),
        badge: 'bg-amber-50 border-amber-200',
      }
    }
    return {
      text: t('低风险 · 活跃'),
      cls: 'text-emerald-600',
      tip: factorTip || t('客户近期活跃度较好，粘性较高。'),
      badge: 'bg-emerald-50 border-emerald-200',
    }
  })
  const needleDeg = computed(() => -90 + (churnPct.value / 100) * 180)

  const ltvChart = computed(() => {
    const sorted = [...orders.value].sort((a, b) =>
      String(a.check_in || '').localeCompare(String(b.check_in || '')),
    )
    let cum = 0
    const series = sorted.map((o) => {
      cum += Number(o.total_amount || 0)
      return { cum, date: o.check_in }
    })
    const ltvNum = Number(g.value.ltv || 0)
    const finalCum = Math.max(ltvNum, cum, 1)
    const yMax = Math.max(10000, Math.ceil((finalCum * 1.35) / 10000) * 10000)
    const labels = [5, 4, 3, 2, 1, 0].map((i) => {
      const v = Math.round((yMax / 5) * i)
      return v >= 1000 ? `${Math.round(v / 1000)}k` : String(v)
    })
    const toY = (v: number) => 95 - (Math.min(v, yMax) / yMax) * 90
    const n = Math.max(series.length, 1)
    const hist: { x: number; y: number; cum: number }[] = []
    if (!series.length) {
      hist.push({ x: 0, y: toY(0), cum: 0 })
      hist.push({ x: 35, y: toY(finalCum * 0.45), cum: finalCum * 0.45 })
      hist.push({ x: 70, y: toY(finalCum), cum: finalCum })
    } else {
      const take =
        series.length <= 4
          ? series
          : [series[0], series[Math.floor(n / 3)], series[Math.floor((2 * n) / 3)], series[n - 1]]
      take.forEach((p, i) => {
        const x = take.length === 1 ? 70 : (i / Math.max(take.length - 1, 1)) * 70
        hist.push({ x, y: toY(p.cum), cum: p.cum })
      })
    }
    const last = hist[hist.length - 1]
    const projY = toY(Math.min(yMax, estLtv.value))
    const guestPath = hist
      .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
      .join(' ')
    return {
      labels,
      guestPath,
      areaPath: `${guestPath} L70,100 L0,100 Z`,
      cohortPath: `M0,90 Q25,72 50,55 T100,28`,
      projPath: `M${last.x.toFixed(1)},${last.y.toFixed(1)} Q85,${((last.y + projY) / 2).toFixed(1)} 100,${projY.toFixed(1)}`,
      points: hist,
      last,
      tipX: Math.min(78, Math.max(18, last.x)),
      tipY: Math.max(8, last.y - 2),
    }
  })

  function splitWhen(raw: string) {
    const s = String(raw || '').replace('T', ' ')
    const m = s.match(/(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/)
    if (!m) return { when: '—', time: '' }
    const date = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
    const when =
      getLocale() === 'en'
        ? date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        : t('{m}月{d}日', { m: Number(m[2]), d: Number(m[3]) })
    return { when, time: m[4] ? `${m[4]}:${m[5]}` : '' }
  }

  const channelTrail = computed<TrailEvt[]>(() => {
    const evts: TrailEvt[] = []

    if (wecomBound.value) {
      const c0 = coupons.value[0]
      const ts = String(c0?.valid_from || wecom.value?.linked_at || '')
      const book = splitWhen(ts)
      evts.push({
        title: t('企业微信互动'),
        sub: t('加好友领券 · 跟进人 {user}', { user: wecom.value?.follow_userid || '—' }),
        when: book.when,
        time: book.time || '—',
        body: c0
          ? t('扫码添加管家，已领取 {name}（{discount} · 券码 {code}）', {
              name: c0.name || t('房费券'),
              discount: c0.discount_label || '',
              code: c0.code,
            })
          : t('扫码添加专属管家，完成私域建联'),
        mood: c0 ? t('已领券') : t('已建联'),
        tone: 'ai',
        ai: wecom.value?.merge_method
          ? t('OneID 归集 · {method}', { method: wecom.value.merge_method })
          : t('企微身份已写入 OneID'),
        sortAt: ts || '9999',
      })
    }

    const channelRaw =
      channelChips.value.find((c) =>
        /携程|美团|飞猪|OTA|抖音|小红书|Ctrip|Meituan|Fliggy|Douyin/i.test(c),
      ) ||
      channelChips.value[0] ||
      t('直客')
    const channel = t(String(channelRaw))
    const sorted = [...orders.value].sort((a, b) =>
      String(a.check_in || '').localeCompare(String(b.check_in || '')),
    )
    const take = sorted.slice(-3)

    for (const o of take) {
      const book = splitWhen(o.created_at || o.check_in)
      evts.push({
        title: t('{channel} 平台预订', { channel }),
        sub: t('渠道: {channel} · 订单号: {no}', { channel, no: o.order_no }),
        when: book.when,
        time: book.time || '',
        body: t('预订入住 {ci} – {co} · {amt}', {
          ci: o.check_in,
          co: o.check_out,
          amt: fmt(o.total_amount),
        }),
        mood: t('已预订'),
        tone: 'primary',
        sortAt: String(o.created_at || o.check_in || ''),
      })

      if (['checked_in', 'checked_out', 'confirmed'].includes(o.status)) {
        const cin = splitWhen(o.check_in)
        const st = t(ORDER_ST_CN[o.status] || o.status)
        evts.push({
          title: o.status === 'checked_out' ? t('完成入住离店') : t('前台办理入住'),
          sub: t('订单 {no} · {status}', { no: o.order_no, status: st }),
          when: cin.when,
          time: cin.time || '',
          body:
            o.status === 'checked_out'
              ? t('已完成 {n} 晚入住，营收计入 LTV。', { n: o.nights || 1 })
              : t('订单状态：{status}', { status: st }),
          mood: o.status === 'checked_out' ? t('已离店') : t('在店/确认'),
          tone: 'ok',
          sortAt: String(o.check_out || o.check_in || ''),
        })
      }
    }

    if (!evts.length) {
      evts.push({
        title: t('档案接入 OneID'),
        sub: t('身份 {id}', { id: oneIdLabel.value }),
        when: '—',
        time: '',
        body: t('暂无订单或企微触点记录。'),
        tone: 'ai',
        sortAt: '',
      })
    }
    return evts.sort((a, b) => String(b.sortAt || '').localeCompare(String(a.sortAt || '')))
  })

  const sentimentScore = computed(() => {
    if (!reviews.value.length) return { score: 88, label: t('良好') }
    const avg =
      reviews.value.reduce((s: number, rev: any) => s + Number(rev.rating || 0), 0) /
      reviews.value.length
    const score = Math.round(Math.min(98, Math.max(55, avg * 18 + stayCount.value)))
    return {
      score,
      label: score >= 90 ? t('极度满意') : score >= 75 ? t('满意') : t('需关怀'),
    }
  })

  const lowScoreReview = computed(() =>
    reviews.value.find(
      (rev: any) => Number(rev.rating) > 0 && Number(rev.rating) <= 2 && !rev.replied,
    ),
  )

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  watch([() => r.query.focus, () => loading.value, () => d.value], () => {
    if (loading.value || !d.value) return
    const f = String(r.query.focus || '')
    if (f === 'ltv' || f === 'trail') {
      requestAnimationFrame(() => scrollTo(f === 'ltv' ? 'section-ltv' : 'section-trail'))
    }
  })

  function openRedeemModal(c: any) {
    if (!c?.can_redeem) return
    const upcoming = orders.value.find((o: any) =>
      ['pending', 'confirmed', 'checked_in'].includes(o.status),
    )
    redeemModal.value = {
      coupon: c,
      orderId: upcoming?.id || orders.value[0]?.id || null,
    }
    redeemErr.value = ''
    redeemHint.value = ''
  }

  async function confirmRedeem() {
    const m = redeemModal.value
    if (!m?.coupon?.id || redeemBusyId.value) return
    redeemBusyId.value = m.coupon.id
    redeemErr.value = ''
    try {
      const res = await api.couponRedeem({
        coupon_id: m.coupon.id,
        order_id: m.orderId || undefined,
        remark: t('客户360前台核销'),
      })
      redeemHint.value = res.message || t('核销成功')
      redeemModal.value = null
      await load()
    } catch (e: any) {
      redeemErr.value = e?.message || t('核销失败')
    } finally {
      redeemBusyId.value = null
    }
  }

  async function redeemByCode() {
    const code = redeemCode.value.trim()
    if (!code || redeemCodeBusy.value) return
    redeemCodeBusy.value = true
    redeemErr.value = ''
    redeemHint.value = ''
    try {
      const looked = await api.couponLookup(code)
      if (looked.guest_id && looked.guest_id !== g.value.id) {
        redeemErr.value = t('该券属于客人 #{id} {name}，请打开对应客户页核销', {
          id: looked.guest_id,
          name: looked.guest_name || '',
        })
        return
      }
      if (!looked.can_redeem) {
        redeemErr.value = t('券不可核销（状态：{status} / {redeem}）', {
          status: looked.status,
          redeem: looked.redeem_status,
        })
        return
      }
      const upcoming = orders.value.find((o: any) =>
        ['pending', 'confirmed', 'checked_in'].includes(o.status),
      )
      const res = await api.couponRedeem({
        code,
        order_id: upcoming?.id,
        remark: t('客户360输券码核销'),
      })
      redeemHint.value = res.message || t('核销成功')
      redeemCode.value = ''
      await load()
    } catch (e: any) {
      redeemErr.value = e?.message || t('核销失败')
    } finally {
      redeemCodeBusy.value = false
    }
  }

  return {
    d,
    loading,
    load,
    oneidExpanded,
    toggleOneidAudit,
    g,
    h5Membership,
    orders,
    tags,
    identities,
    reviews,
    wecom,
    wecomBound,
    inWecomPrivate,
    coupons,
    wecomExternalId,
    phoneDisplay,
    vipLabel,
    stayCount,
    avgTicket,
    ltvScore,
    churnPct,
    channelCount,
    mergeConfidence,
    oneIdLabel,
    channelChips,
    sourceBars,
    nextStay,
    nextStayNights,
    sentiment,
    roomPrefs,
    motiveTags,
    nextAction,
    psychRadar,
    fingerprint,
    fmtInt,
    estLtv,
    riskLabel,
    needleDeg,
    ltvChart,
    channelTrail,
    sentimentScore,
    lowScoreReview,
    scrollTo,
    COUPON_ST_CN,
    REDEEM_CN,
    redeemBusyId,
    redeemCode,
    redeemCodeBusy,
    redeemHint,
    redeemErr,
    redeemModal,
    openRedeemModal,
    confirmRedeem,
    redeemByCode,
  }
}
