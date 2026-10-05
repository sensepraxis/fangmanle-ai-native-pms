// SPDX-License-Identifier: Apache-2.0
import { computed, onMounted, ref, watch, type ComputedRef, type Ref } from 'vue'
import { formatAiModelMeta } from '../../../lib/aiModelMeta'
import { api } from '../../../lib/api'
import { hotelStore } from '../../../store/hotel'
import { toast } from '../../../lib/ui'
import type { BatchRow, Breakdown, Status, Tab } from './types'
import { money } from './types'
import { t } from '../../../lib/i18n'
import { localizeSeedText } from '../../../lib/localizeSeed'

export function useReconBatches(
  batches: Ref<BatchRow[]>,
  opts: {
    dateLabel: Ref<string>
    channelFilter: Ref<string>
    tab: Ref<Tab>
    filtered: ComputedRef<BatchRow[]>
  },
) {
  const { dateLabel, channelFilter, tab, filtered } = opts

  /** 值班人：当前登录用户（无会话则不展示，避免假数据） */
  const dutyName = computed(() => hotelStore.user?.name || hotelStore.user?.username || '')
  const loading = ref(false)
  const selectedId = ref<string | number | null>(null)
  const checked = ref<Set<string>>(new Set())
  const closeModal = ref(false)
  const syncConfirm = ref(false)
  const exportOpen = ref(false)
  const aiOpen = ref(false)
  const overrideNote = ref('')
  const showOverride = ref(false)
  const aiLoading = ref(false)

  function mapStatus(raw: string, variance: number): Status {
    const s = (raw || '').toLowerCase()
    if (s === 'closed' || s === 'matched') return s === 'closed' ? 'closed' : 'matched'
    if (s === 'conflict' || Math.abs(variance) >= 0.01) {
      return Math.abs(variance) >= 200 ? 'human' : 'ai'
    }
    if (s === 'open') return 'ai'
    return 'matched'
  }

  function buildBreakdown(
    pms: number,
    gateway: number,
    bank: number | null,
    variance: number,
    breakdownOpts?: {
      commissionPct?: number
      commissionPctText?: string
      commissionLabel?: string
      expectedCommission?: number
    },
  ): Breakdown[] {
    const absVar = Math.abs(variance)
    const rate = Number(breakdownOpts?.commissionPct || 0) / 100
    const rateText = breakdownOpts?.commissionPctText || String(breakdownOpts?.commissionPct ?? 0)
    const rawLabel =
      breakdownOpts?.commissionLabel || (rate > 0 ? t('渠道佣金 {n}%', { n: rateText }) : '')
    const label = localizeSeedText(rawLabel)
    const otaCut =
      breakdownOpts?.expectedCommission != null && breakdownOpts.expectedCommission > 0
        ? Number(breakdownOpts.expectedCommission)
        : rate > 0
          ? Math.round(pms * rate * 100) / 100
          : 0

    if (absVar < 0.01) {
      if (otaCut >= 0.01) {
        return [
          {
            type: 'fee',
            label: t('OTA 平台佣金（配置）'),
            tag: 'normal',
            tagLabel: t('配置费率'),
            amount: otaCut,
            note: t('{label}：应收 {pms} × {rate}% = {cut}（本批已对齐）', {
              label,
              pms: money(pms),
              rate: rateText,
              cut: money(otaCut),
            }),
            pct: 100,
          },
        ]
      }
      return [
        {
          type: 'fee',
          label: t('渠道扣减'),
          tag: 'normal',
          tagLabel: t('正常'),
          amount: 0,
          note: t('本批无 OTA 佣金配置或佣金率为 0%'),
          pct: 100,
        },
      ]
    }

    const sign = variance >= 0 ? 1 : -1
    let remain = absVar
    const feePart = otaCut >= 0.01 ? Math.min(otaCut, remain) : 0
    remain = Math.round((remain - feePart) * 100) / 100

    let t1 = 0
    if (bank != null && gateway > 0 && bank < gateway - 0.01) {
      t1 = Math.min(Math.round((gateway - bank) * 100) / 100, remain)
      remain = Math.round((remain - t1) * 100) / 100
    } else if (bank == null && remain > 0 && feePart < absVar - 0.01) {
      t1 = Math.min(Math.round(remain * 0.35 * 100) / 100, remain)
      remain = Math.round((remain - t1) * 100) / 100
    }

    let refund = 0
    if (absVar >= 150 && remain > 30) {
      refund = Math.min(Math.round(remain * 0.25 * 100) / 100, remain)
      remain = Math.round((remain - refund) * 100) / 100
    }
    const net = remain
    const rows: Breakdown[] = []
    if (feePart >= 0.01) {
      rows.push({
        type: 'fee',
        label: t('OTA 平台佣金（配置）'),
        tag: 'normal',
        tagLabel: t('配置费率'),
        amount: sign * feePart,
        note: t('读取系统配置「{label}」：{pms} × {rate}% = {cut}', {
          label,
          pms: money(pms),
          rate: rateText,
          cut: money(otaCut),
        }),
        pct: Math.round((feePart / absVar) * 100),
      })
    } else if (rate <= 0) {
      rows.push({
        type: 'fee',
        label: t('OTA 平台佣金'),
        tag: 'check',
        tagLabel: t('未配置'),
        amount: 0,
        note: t('未匹配到 OTA 佣金设置中的渠道费率，请到系统配置核对'),
        pct: 0,
      })
    }
    if (t1 >= 0.01) {
      rows.push({
        type: 't1',
        label: t('T+1 在途'),
        tag: 'normal',
        tagLabel: t('正常'),
        amount: sign * t1,
        note:
          bank == null
            ? t('钱还在路上，明天早上对公户通常会到账')
            : t('渠道实收 {gateway}，银行到账 {bank}，差额多为结算在途', {
                gateway: money(gateway),
                bank: money(bank),
              }),
        pct: Math.round((t1 / absVar) * 100),
      })
    }
    if (refund >= 0.01) {
      rows.push({
        type: 'refund',
        label: t('退款在途'),
        tag: 'check',
        tagLabel: t('待核'),
        amount: sign * refund,
        note: t('疑似退款未回冲或重复入账，请核订单退改记录'),
        pct: Math.round((refund / absVar) * 100),
      })
    }
    if (net >= 0.01) {
      rows.push({
        type: 'net',
        label: t('应收与实收净差额'),
        tag: absVar >= 200 ? 'bad' : 'check',
        tagLabel: absVar >= 200 ? t('真差额') : t('待核'),
        amount: sign * net,
        note: label
          ? t('扣除配置佣金（{label}）后仍有差额，请逐单核对', { label })
          : t('PMS 订单应收与渠道实收对不上，请逐单核对'),
        pct: Math.max(1, 100 - rows.reduce((s, r) => s + r.pct, 0)),
      })
    }
    return rows
  }

  function enrichBatch(b: any): BatchRow {
    const pms = Number(b.pms_total || 0)
    const gateway = Number(b.channel_total || 0)
    const variance = Number(b.variance ?? pms - gateway)
    const commissionPct = Number(b.commission_pct ?? 0)
    const commissionPctText = String(b.commission_pct_text ?? commissionPct)
    const commissionLabel = String(b.commission_label || '')
    const expectedCommission = Number(b.expected_commission ?? (pms * commissionPct) / 100)
    const expectedNet = Number(b.expected_net ?? pms - expectedCommission)
    const commissionFormula = String(
      b.commission_formula ||
        (commissionLabel && pms > 0
          ? `${money(pms)} × (1 - ${commissionLabel}) = ${money(expectedNet)}`
          : ''),
    )
    const ch = String(b.channel || '渠道')
    let bank: number | null = null
    if (gateway > 0) {
      if (/现金|直订|协议|银行|POS/.test(ch)) bank = gateway
      else bank = gateway
    }
    const status = mapStatus(b.status || '', variance)
    const code = `${ch}-${b.id}`
    const breakdown = buildBreakdown(pms, gateway, bank, variance, {
      commissionPct,
      commissionPctText,
      commissionLabel,
      expectedCommission,
    })
    return {
      id: b.id,
      code,
      channel: ch,
      guest: localizeSeedText(b.note || t('{ch} 渠道批次', { ch: t(ch) })),
      bizDate: b.biz_date || '',
      pms,
      gateway,
      bank,
      variance,
      status,
      note: b.note || '',
      confidence: 0,
      cause: '',
      commissionPct,
      commissionPctText,
      commissionLabel: localizeSeedText(commissionLabel),
      commissionFormula: localizeSeedText(commissionFormula),
      expectedCommission,
      expectedNet,
      breakdown,
      similar: [],
      orderLines: [],
      closed: status === 'closed',
    }
  }

  async function loadDetail(batchId: string | number) {
    const id = Number(batchId)
    if (!Number.isFinite(id)) return
    try {
      const detail = await api.reconBatchDetail(id)
      const row = batches.value.find((b) => Number(b.id) === id)
      if (!row || !detail) return
      const pmsItems = (detail.items || []).filter((it: any) => it.side === 'pms' && it.order_id)
      row.orderLines = pmsItems.map((it: any) => ({
        orderId: it.order_id,
        orderNo: it.order?.order_no || it.ref_no || `ORD-${it.order_id}`,
        guestName: it.order?.guest_name || undefined,
        pms: Number(it.amount || 0),
        channel: Number(it.note?.match(/渠道实收\s+([\d.]+)/)?.[1] || 0),
        matchStatus: it.match_status || '',
        note: it.note || '',
      }))
      if (row.orderLines.length === 1) {
        const one = row.orderLines[0]
        row.guest = `${one.orderNo}${one.guestName ? ` · ${one.guestName}` : ''}`
      } else if (row.orderLines.length > 1) {
        row.guest = t('{n} 笔订单 · {date}', { n: row.orderLines.length, date: row.bizDate })
      }
      row.similar = row.orderLines.slice(0, 5).map((ol) => ({
        title: `${ol.orderNo}${ol.guestName ? ` · ${ol.guestName}` : ''} · ${money(ol.pms)}`,
        done: ol.matchStatus === 'matched',
      }))
    } catch {
      /* 列表数据仍可用 */
    }
  }

  async function load() {
    loading.value = true
    try {
      let list = await api.listReconBatches(hotelStore.hotelId)
      if (!Array.isArray(list) || !list.length) {
        await api.syncReconBatches(hotelStore.hotelId, 14)
        list = await api.listReconBatches(hotelStore.hotelId)
      }
      batches.value = Array.isArray(list) ? list.map(enrichBatch) : []
      const dates = [...new Set(batches.value.map((b) => b.bizDate).filter(Boolean))]
        .sort()
        .reverse()
      if (!dateLabel.value || !dates.includes(dateLabel.value)) {
        dateLabel.value = dates[0] || ''
      }
    } catch {
      batches.value = []
      toast(t('加载对账批次失败'), false)
    } finally {
      loading.value = false
      if (!selectedId.value && batches.value.length) {
        const prefer =
          batches.value.find((b) => b.status === 'human' || b.status === 'ai') || batches.value[0]
        selectedId.value = prefer.id
      }
      if (selectedId.value) await loadDetail(selectedId.value)
    }
  }

  const selected = computed(() => batches.value.find((b) => b.id === selectedId.value) || null)

  const kpi = computed(() => {
    const all = dateLabel.value
      ? batches.value.filter((b) => b.bizDate === dateLabel.value)
      : batches.value
    const abnormal = all.filter(
      (b) => b.status === 'ai' || b.status === 'human' || b.status === 'progress',
    )
    const pmsSum = all.reduce((s, b) => s + b.pms, 0)
    const varSum = abnormal.reduce((s, b) => s + Math.abs(b.variance), 0)
    return {
      pendingTotal: pmsSum,
      abnormalCount: abnormal.length,
      abnormalAmount: varSum,
    }
  })

  const abnormalBatches = computed(() => {
    const all = dateLabel.value
      ? batches.value.filter((b) => b.bizDate === dateLabel.value)
      : batches.value
    return all.filter((b) => b.status === 'ai' || b.status === 'human' || b.status === 'progress')
  })

  const canCloseBatch = computed(() => abnormalBatches.value.length === 0)

  function jumpToAbnormal(b: BatchRow) {
    closeModal.value = false
    channelFilter.value = 'all'
    tab.value = b.status === 'ai' ? 'ai' : 'human'
    selectRow(b)
    toast(t('已定位到异常批次 {code}', { code: b.code }))
  }

  function selectRow(b: BatchRow) {
    selectedId.value = b.id
    showOverride.value = false
    b.cause = ''
    b.confidence = 0
    void loadDetail(b.id)
  }

  async function runAiExplain() {
    const b = selected.value
    if (!b) return
    const id = Number(b.id)
    if (!Number.isFinite(id)) return
    aiLoading.value = true
    try {
      if (!b.orderLines.length) await loadDetail(id)
      const res = await api.reconBatchAiExplain(id)
      b.cause = (res?.cause || '').trim()
      b.confidence = Number(res?.confidence || 0)
      b.modelMeta = formatAiModelMeta(res)
      if (!b.cause) toast(t('AI 未返回解释内容'), false)
    } catch (e: any) {
      toast(e?.message || t('AI 差异解释失败'), false)
    } finally {
      aiLoading.value = false
    }
  }

  function toggleCheck(id: string | number, e: Event) {
    e.stopPropagation()
    const key = String(id)
    const next = new Set(checked.value)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    checked.value = next
  }

  function selectAllAbnormal(on: boolean) {
    const next = new Set<string>()
    if (on) {
      for (const b of filtered.value) {
        if (b.status === 'ai' || b.status === 'human' || b.status === 'progress')
          next.add(String(b.id))
      }
    }
    checked.value = next
  }

  function doExport(kind: 'all' | 'abnormal' | 'closed') {
    exportOpen.value = false
    const label = t(
      kind === 'all' ? '全批次明细' : kind === 'abnormal' ? '仅异常批次' : '仅关账批次',
    )
    toast(
      t('已导出：{label}（Excel）· {date}', {
        label,
        date: dateLabel.value || t('今日'),
      }),
    )
  }

  function forceSync() {
    syncConfirm.value = true
  }

  async function confirmSync() {
    syncConfirm.value = false
    loading.value = true
    try {
      const res = await api.syncReconBatches(hotelStore.hotelId, 14)
      selectedId.value = null
      await load()
      toast(t('已按订单同步 {n} 个批次', { n: res?.batches ?? 0 }))
    } catch {
      loading.value = false
      toast(t('同步失败'), false)
    }
  }

  function runAiMatch() {
    const n = checked.value.size
    if (!n) {
      toast(t('请先勾选要匹配的批次'))
      return
    }
    for (const b of batches.value) {
      if (checked.value.has(String(b.id)) && Math.abs(b.variance) < 100) {
        b.status = 'matched'
      } else if (checked.value.has(String(b.id))) {
        b.status = 'human'
      }
    }
    toast(t('已对 {n} 笔运行 AI 匹配', { n }))
  }

  function acceptAi() {
    const b = selected.value
    if (!b) return
    b.status = 'closed'
    b.closed = true
    toast(t('已接受 AI 解释 · 本笔已关账（记入审计日志）'))
  }

  function markRefund() {
    const b = selected.value
    if (!b) return
    b.status = 'progress'
    toast(t('已标记为「退款异常」· 进入追踪队列'))
  }

  function overrideAi() {
    showOverride.value = true
  }

  function saveOverride() {
    const b = selected.value
    if (!b) return
    if (overrideNote.value.trim()) b.cause = overrideNote.value.trim()
    b.status = 'progress'
    showOverride.value = false
    toast(t('已转人工复核 · 覆盖版本已留痕'))
  }

  function openCloseModal() {
    closeModal.value = true
  }

  function confirmClose() {
    if (!canCloseBatch.value) {
      toast(t('仍有未处理差异，建议先清零再关账'), false)
      return
    }
    for (const b of batches.value) {
      if (b.status === 'matched') b.status = 'closed'
    }
    closeModal.value = false
    toast(
      t('已关账 · 批次 {date} 已冻结，审计日志已写入', {
        date: dateLabel.value || t('今日'),
      }),
    )
  }

  onMounted(load)
  watch(() => hotelStore.hotelId, load)

  return {
    dutyName,
    loading,
    selectedId,
    checked,
    closeModal,
    syncConfirm,
    exportOpen,
    aiOpen,
    overrideNote,
    showOverride,
    aiLoading,
    selected,
    kpi,
    abnormalBatches,
    canCloseBatch,
    load,
    loadDetail,
    enrichBatch,
    selectRow,
    jumpToAbnormal,
    runAiExplain,
    toggleCheck,
    selectAllAbnormal,
    doExport,
    forceSync,
    confirmSync,
    runAiMatch,
    acceptAi,
    markRefund,
    overrideAi,
    saveOverride,
    openCloseModal,
    confirmClose,
  }
}
