// SPDX-License-Identifier: Apache-2.0
import { computed, reactive, ref, type Ref } from 'vue'
import { t } from '../../../lib/i18n'
import { api } from '../../../lib/api'
import { hotelStore } from '../../../store/hotel'
import { toast } from '../../../lib/ui'
import { NATIVE_WALLET_SOURCE, labelForWalletSource } from '../../../lib/branding'
import type { GrantForm, GrantMode, GrantSub, SegmentPreview } from './types'

export function useCouponCatalog(opts: {
  grantSub: Ref<GrantSub>
  setGrantSub: (s: GrantSub) => void
}) {
  const { grantSub, setGrantSub } = opts

  const rows = ref<any[]>([])
  const grants = ref<any[]>([])
  const redeemLedger = ref<any[]>([])
  const guests = ref<any[]>([])
  const segments = ref<any[]>([])
  const roomTypeOpts = ref<string[]>([])
  const segmentPreview = ref<SegmentPreview | null>(null)
  const busy = ref(false)
  const guestQ = ref('')
  const rulesPanelKey = ref(0)

  const grantForm = reactive<GrantForm>({
    coupon_id: '',
    mode: (grantSub.value === 'segment' ? 'segment' : 'guest') as GrantMode,
    segment: '',
    guest_ids: [],
    allow_over_limit: false,
    over_limit_reason: '',
  })

  /** guest_id → ownership info for selected batch */
  const ownershipByGuest = ref<Record<number, any>>({})
  const ownershipMeta = ref<{
    per_user_qty: number
    at_limit_count: number
    grantable_count: number
  } | null>(null)

  const activeCoupons = computed(() => rows.value.filter((x) => x.status === 'active'))

  const h5Guests = computed(() => {
    const q = guestQ.value.trim().toLowerCase()
    return guests.value.filter((g) => {
      if (!g.channel_bound && !g.channel_reachable && !g.wecom_bound && !g.in_wecom_private)
        return false
      if (!q) return true
      return (
        String(g.name || '')
          .toLowerCase()
          .includes(q) || String(g.phone || '').includes(q)
      )
    })
  })

  function ownershipOf(guestId: number) {
    return ownershipByGuest.value[Number(guestId)] || null
  }

  const selectedGrantStats = computed(() => {
    const ids = grantForm.guest_ids
    let grantable = 0
    let blocked = 0
    for (const id of ids) {
      const o = ownershipOf(id)
      if (o?.at_limit) blocked += 1
      else grantable += 1
    }
    return { total: ids.length, grantable, blocked }
  })

  const kpi = computed(() => {
    const active = rows.value.filter((r) => r.status === 'active').length
    const granted = rows.value.reduce((s, r) => s + (r.granted || 0), 0)
    const used = rows.value.reduce((s, r) => s + (r.used || 0), 0)
    return {
      active,
      granted,
      used,
      rate: granted ? Math.round((used / granted) * 1000) / 10 : 0,
    }
  })

  function enrichRedeemLedger(ledger: any[], grantRows: any[], couponRows: any[]) {
    const grantByCode = new Map<string, any>()
    for (const g of grantRows || []) {
      const code = String(g.coupon_code || g.code || '')
        .trim()
        .toUpperCase()
      if (code) grantByCode.set(code, g)
    }
    const couponById = new Map<number, any>()
    for (const c of couponRows || []) {
      if (c?.id != null) couponById.set(Number(c.id), c)
    }

    const base =
      ledger && ledger.length
        ? ledger
        : (grantRows || [])
            .filter((g) => g.used_at || ['USED', 'used'].includes(String(g.status || '')))
            .map((g) => ({
              id: `g-${g.id}`,
              coupon_code: g.coupon_code || g.code,
              used_at: g.used_at,
              used_amount: g.used_amount,
              guest_name: g.guest_name,
              batch_no: g.batch_no,
              coupon_name: g.coupon_name,
              used_order_id: g.used_order_id,
              source: NATIVE_WALLET_SOURCE,
              wallet_source: NATIVE_WALLET_SOURCE,
              source_label: labelForWalletSource(NATIVE_WALLET_SOURCE),
              status: 'USED',
            }))

    return base.map((row) => {
      const code = String(row.coupon_code || row.code || '')
        .trim()
        .toUpperCase()
      const g = code ? grantByCode.get(code) : null
      const coupon = g?.coupon_id != null ? couponById.get(Number(g.coupon_id)) : null
      const src = row.source_label || row.wallet_source || row.source
      return {
        ...row,
        coupon_code: row.coupon_code || row.code || g?.code || g?.coupon_code,
        used_at: row.used_at || row.redeemed_at || g?.used_at || null,
        used_amount:
          row.used_amount != null
            ? row.used_amount
            : row.amount_saved != null
              ? row.amount_saved
              : (g?.used_amount ?? null),
        guest_name: row.guest_name || row.customer_name || g?.guest_name || null,
        recipient_name: row.recipient_name || null,
        batch_no: row.batch_no || g?.batch_no || coupon?.batch_no || null,
        coupon_name: row.coupon_name || row.name || g?.coupon_name || coupon?.name || null,
        used_order_id: row.used_order_id ?? row.order_id ?? g?.used_order_id ?? null,
        source:
          row.source ||
          row.wallet_source ||
          (g ? NATIVE_WALLET_SOURCE : src) ||
          NATIVE_WALLET_SOURCE,
        wallet_source: row.wallet_source || row.source || (g ? NATIVE_WALLET_SOURCE : null),
        source_label:
          row.source_label ||
          labelForWalletSource(
            row.wallet_source || row.source || (g ? NATIVE_WALLET_SOURCE : ''),
          ) ||
          (g ? labelForWalletSource(NATIVE_WALLET_SOURCE) : '—'),
      }
    })
  }

  async function load() {
    const hid = hotelStore.hotelId
    const [couponRows, grantRows, guestRows, segRows, rtRows, ledgerRows] = await Promise.all([
      api.mktCoupons(hid),
      api.mktGrants(hid),
      api.mktCustomers(hid, undefined, true),
      api.mktGrantSegments(hid).catch(() => []),
      api.listRoomTypes(hid).catch(() => []),
      api.mktCouponRedeemLog(hid).catch(() => []),
    ])
    rows.value = couponRows
    grants.value = grantRows
    guests.value = guestRows
    segments.value = segRows
    redeemLedger.value = enrichRedeemLedger(ledgerRows || [], grantRows || [], couponRows || [])
    if (!grantForm.segment && segments.value[0]) {
      grantForm.segment = segments.value[0].key || segments.value[0].segment_id
    }
    roomTypeOpts.value = (rtRows || []).map((r: any) => String(r.name || '').trim()).filter(Boolean)
  }

  async function refreshSegmentPreview() {
    if (grantSub.value !== 'segment' || !grantForm.segment) {
      segmentPreview.value = null
      return
    }
    try {
      const r = await api.mktGrantPreview(hotelStore.hotelId, {
        mode: 'segment',
        segment: grantForm.segment,
      })
      segmentPreview.value = {
        count: r.count || 0,
        samples: r.samples || [],
        segment_count: r.segment_count,
        reachable_count: r.reachable_count ?? r.count,
        unreachable_count: r.unreachable_count,
      }
    } catch {
      segmentPreview.value = null
    }
  }

  async function refreshOwnership() {
    ownershipByGuest.value = {}
    ownershipMeta.value = null
    const cid = Number(grantForm.coupon_id)
    if (!cid) return
    try {
      const ids = h5Guests.value.map((g) => Number(g.guest_id)).filter(Boolean)
      const r = await api.mktCouponOwnership(hotelStore.hotelId, cid, ids.length ? ids : undefined)
      const map: Record<number, any> = {}
      for (const it of r.items || []) {
        map[Number(it.guest_id)] = it
      }
      ownershipByGuest.value = map
      ownershipMeta.value = {
        per_user_qty: Number(r.per_user_qty || 1),
        at_limit_count: Number(r.at_limit_count || 0),
        grantable_count: Number(r.grantable_count || 0),
      }
    } catch {
      ownershipByGuest.value = {}
      ownershipMeta.value = null
    }
  }

  function openGrant(couponId?: number | string, mode?: GrantMode) {
    if (couponId != null) grantForm.coupon_id = couponId
    else if (!grantForm.coupon_id && activeCoupons.value[0])
      grantForm.coupon_id = activeCoupons.value[0].id
    if (mode === 'segment') {
      grantForm.guest_ids = []
      setGrantSub('segment')
    } else {
      grantForm.guest_ids = []
      setGrantSub('guest')
    }
  }

  async function setStatus(id: number, status: string) {
    try {
      await api.mktCouponStatus(hotelStore.hotelId, id, status)
      toast(t('状态已更新'))
      await load()
    } catch (e: any) {
      toast(e?.message || t('失败'), false)
    }
  }

  function toggleGuest(id: number) {
    const own = ownershipOf(id)
    if (own?.at_limit && !grantForm.allow_over_limit) {
      toast(t('该客人已持有本批次（达限领），可勾选「补偿强制发放」后再选'), false)
      return
    }
    const i = grantForm.guest_ids.indexOf(id)
    if (i >= 0) grantForm.guest_ids.splice(i, 1)
    else grantForm.guest_ids.push(id)
  }

  function toggleAllH5Guests() {
    const ids = h5Guests.value
      .map((g) => g.guest_id)
      .filter((id) => grantForm.allow_over_limit || !ownershipOf(id)?.at_limit)
    if (ids.every((id) => grantForm.guest_ids.includes(id))) {
      grantForm.guest_ids = grantForm.guest_ids.filter((id) => !ids.includes(id))
    } else {
      const set = new Set([...grantForm.guest_ids, ...ids])
      grantForm.guest_ids = [...set]
    }
  }

  async function doGrant() {
    if (!grantForm.coupon_id) {
      toast(t('请选择券批次'), false)
      return
    }
    const mode: GrantMode = grantSub.value === 'segment' ? 'segment' : 'guest'
    grantForm.mode = mode
    if (mode === 'guest' && !grantForm.guest_ids.length) {
      toast(t('请勾选企微私域客人'), false)
      return
    }
    if (mode === 'segment' && !grantForm.segment) {
      toast(t('请选择客群'), false)
      return
    }
    if (
      mode === 'guest' &&
      grantForm.allow_over_limit &&
      !String(grantForm.over_limit_reason || '').trim()
    ) {
      toast(t('补偿强制发放须填写原因'), false)
      return
    }

    const coupon = rows.value.find((r) => Number(r.id) === Number(grantForm.coupon_id))
    const couponLabel = coupon
      ? `${coupon.name}（${coupon.batch_no || coupon.id}）`
      : `批次 #${grantForm.coupon_id}`
    const per = ownershipMeta.value?.per_user_qty || coupon?.per_user_qty || 1

    let confirmTip = ''
    if (mode === 'segment') {
      const seg = segments.value.find(
        (s) => String(s.key || s.segment_id) === String(grantForm.segment),
      )
      const segName = seg?.label || seg?.name || grantForm.segment
      const reach = segmentPreview.value?.reachable_count ?? segmentPreview.value?.count
      let skipHint = ''
      try {
        const prev = await api.mktGrantPreview(hotelStore.hotelId, {
          mode: 'segment',
          segment: grantForm.segment,
        })
        const gids = (prev.guest_ids || []) as number[]
        if (gids.length) {
          const own = await api.mktCouponOwnership(
            hotelStore.hotelId,
            Number(grantForm.coupon_id),
            gids,
          )
          const blocked = Number(own.at_limit_count || 0)
          const grantable = Number(own.grantable_count || 0)
          skipHint =
            '\n' +
            t('预计新发约 {grantable} 人 · 已持有将跳过 {blocked} 人（每人限领 {per}）', {
              grantable,
              blocked,
              per: own.per_user_qty || per,
            })
        }
      } catch {
        /* ignore preview failure */
      }
      const reachText =
        reach != null ? t('企微私域可达 {n} 人', { n: reach }) : t('将按客群 ∩ 企微私域实际发放')
      confirmTip =
        t('确认向客群「{seg}」发放「{coupon}」？', { seg: segName, coupon: couponLabel }) +
        '\n' +
        reachText +
        '。' +
        skipHint +
        '\n' +
        t('发放后不可撤回。')
    } else {
      const { total, grantable, blocked } = selectedGrantStats.value
      if (!grantForm.allow_over_limit && grantable === 0) {
        toast(t('所选客人均已持有本批次，请换人、换券，或开启补偿强制发放'), false)
        return
      }
      if (grantForm.allow_over_limit) {
        confirmTip =
          t('确认补偿强制发放「{coupon}」给已选 {total} 人？', { coupon: couponLabel, total }) +
          '\n' +
          t('其中约 {blocked} 人已达限领，将额外再发；原因：{reason}', {
            blocked,
            reason: grantForm.over_limit_reason.trim(),
          }) +
          '\n' +
          t('发放后不可撤回。')
      } else {
        confirmTip =
          t('确认向已选 {total} 人发放「{coupon}」？', { total, coupon: couponLabel }) +
          '\n' +
          t('预计新发 {grantable} · 已持有跳过 {blocked}（每人限领 {per}）', {
            grantable,
            blocked,
            per,
          }) +
          '\n' +
          t('发放后不可撤回。')
      }
    }
    if (!window.confirm(confirmTip)) return

    busy.value = true
    try {
      const r = await api.mktGrantCoupon(hotelStore.hotelId, Number(grantForm.coupon_id), {
        mode,
        segment: mode === 'segment' ? grantForm.segment : undefined,
        guest_ids: mode === 'guest' ? grantForm.guest_ids : [],
        channel: mode,
        require_h5: true,
        allow_over_limit: mode === 'guest' ? !!grantForm.allow_over_limit : false,
        over_limit_reason:
          mode === 'guest' && grantForm.allow_over_limit
            ? grantForm.over_limit_reason.trim()
            : undefined,
      })
      const parts = [t('发放 {n}', { n: r.granted })]
      if (r.skipped_already) parts.push(t('已持有跳过 {n}', { n: r.skipped_already }))
      else if (r.skipped) parts.push(t('跳过 {n}', { n: r.skipped }))
      if (r.skipped_no_h5) parts.push(t('无H5跳过 {n}', { n: r.skipped_no_h5 }))
      if (r.compensated) parts.push(t('补偿加发 {n}', { n: r.compensated }))
      toast(parts.join(' · '))
      grantForm.guest_ids = []
      grantForm.allow_over_limit = false
      grantForm.over_limit_reason = ''
      await load()
      await refreshOwnership()
      setGrantSub('records')
    } catch (e: any) {
      toast(e?.message || t('发放失败'), false)
    } finally {
      busy.value = false
    }
  }

  function pruneOverLimitGuests() {
    grantForm.guest_ids = grantForm.guest_ids.filter((id) => !ownershipOf(id)?.at_limit)
    grantForm.over_limit_reason = ''
  }

  return {
    rows,
    grants,
    redeemLedger,
    guests,
    segments,
    roomTypeOpts,
    segmentPreview,
    busy,
    guestQ,
    rulesPanelKey,
    grantForm,
    ownershipByGuest,
    ownershipMeta,
    activeCoupons,
    h5Guests,
    selectedGrantStats,
    kpi,
    ownershipOf,
    load,
    refreshSegmentPreview,
    refreshOwnership,
    openGrant,
    setStatus,
    toggleGuest,
    toggleAllH5Guests,
    doGrant,
    pruneOverLimitGuests,
  }
}
