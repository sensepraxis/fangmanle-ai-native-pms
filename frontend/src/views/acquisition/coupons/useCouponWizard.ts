// SPDX-License-Identifier: Apache-2.0
import { reactive, ref, type Ref } from 'vue'
import { api } from '../../../lib/api'
import { hotelStore } from '../../../store/hotel'
import { toast } from '../../../lib/ui'
import { TYPES } from './constants'
import type { CouponForm, TabKey } from './types'
import { t } from '../../../lib/i18n'

export function useCouponWizard(opts: {
  rows: Ref<any[]>
  roomTypeOpts: Ref<string[]>
  busy: Ref<boolean>
  setTab: (t: TabKey) => void
  load: () => Promise<void>
}) {
  const { rows, roomTypeOpts, busy, setTab, load } = opts

  const showWizard = ref(false)
  const step = ref(1)
  const form = reactive<CouponForm>({
    type: 'DISCOUNT',
    batch_no: '',
    name: '',
    face_raw: TYPES.DISCOUNT.ph,
    threshold: 0,
    max_discount: '',
    benefit_key: 'BREAKFAST',
    validity_mode: 'FIXED',
    validity_days: 365,
    total_qty: 500,
    per_user_qty: 1,
    valid_from: '',
    valid_to: '',
    rooms: [],
    levels: [],
  })

  function genBno() {
    const d = new Date()
    const ymd = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
    const n = String(rows.value.length + 1).padStart(3, '0')
    form.batch_no = `COUPON-${ymd}-${n}`
  }

  function openWizard(prefill?: any) {
    showWizard.value = true
    step.value = 1
    form.type = prefill?.coupon_type || prefill?.type || 'DISCOUNT'
    form.name = prefill?.name || ''
    const d = prefill?.defaults || {}
    if (TYPES[form.type]?.isText)
      form.face_raw = String(d.face_text || d.benefit_value || TYPES[form.type].ph)
    else
      form.face_raw = String(
        d.discount_rate ?? d.reduce_amount ?? d.face_value ?? TYPES[form.type].ph,
      )
    form.threshold = Number(d.threshold || 0)
    form.max_discount = d.max_discount != null ? String(d.max_discount) : ''
    form.benefit_key = String(d.benefit_key || 'BREAKFAST')
    form.validity_mode = (d.validity_mode || 'FIXED') as 'FIXED' | 'RELATIVE'
    form.validity_days = Number(d.validity_days || 365)
    form.total_qty = Number(d.total_qty || 500)
    form.per_user_qty = Number(d.per_user_qty || 1)
    const prefRooms = (d.scope_rooms || d.rooms || prefill?.scope_rooms || []) as string[]
    const names = Array.isArray(prefRooms) ? prefRooms.map(String) : []
    form.rooms = names.filter((n) => roomTypeOpts.value.includes(n))
    form.levels = []
    genBno()
    const now = new Date()
    const to = new Date(now.getTime() + 30 * 86400000)
    const fmt = (x: Date) =>
      `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}T00:00`
    form.valid_from = fmt(now)
    form.valid_to = fmt(to).replace('T00:00', 'T23:59')
  }

  function closeWizard() {
    showWizard.value = false
  }

  function copyBatch(r: any) {
    openWizard({
      type: r.coupon_type || r.type,
      coupon_type: r.coupon_type || r.type,
      name: `${r.name}（副本）`,
      defaults: {
        face_value: r.face_value,
        discount_rate: r.discount_rate,
        reduce_amount: r.reduce_amount,
        face_text: r.face_text,
        benefit_key: r.benefit_key,
        benefit_value: r.benefit_value,
        threshold: r.threshold,
        max_discount: r.max_discount,
        total_qty: r.total_qty,
        per_user_qty: r.per_user_qty,
        validity_mode: r.validity_mode || 'FIXED',
        validity_days: r.validity_days || 365,
        scope_rooms: r.scope_rooms || r.scope?.rooms || [],
      },
    })
    step.value = 2
  }

  function buildPayload(status: 'draft' | 'active') {
    const raw = String(form.face_raw ?? '').trim()
    const payload: any = {
      name: form.name.trim() || '未命名券',
      coupon_type: form.type,
      type: form.type,
      batch_no: form.batch_no || undefined,
      threshold: form.type === 'CASH_ALL' ? 0 : form.threshold,
      total_qty: form.total_qty,
      per_user_qty: form.per_user_qty,
      validity_mode: form.validity_mode,
      validity_days: form.validity_mode === 'RELATIVE' ? form.validity_days : undefined,
      valid_from: form.validity_mode === 'FIXED' ? form.valid_from || undefined : undefined,
      valid_to: form.validity_mode === 'FIXED' ? form.valid_to || undefined : undefined,
      scope_type: form.type === 'CASH_ROOM' ? 'ROOM_SPECIFIED' : 'ALL',
      scope_rooms: form.type === 'CASH_ROOM' ? [...form.rooms] : [],
      status,
      scope: {
        rooms: [...form.rooms],
        member_levels: [...form.levels],
      },
    }
    if (form.type === 'DISCOUNT') {
      payload.discount_rate = Number(raw) || 0
      payload.face_value = payload.discount_rate
      if (form.max_discount) payload.max_discount = Number(form.max_discount)
    } else if (form.type === 'CASH_ROOM' || form.type === 'CASH_ALL') {
      payload.reduce_amount = Number(raw) || 0
      payload.face_value = payload.reduce_amount
    } else {
      payload.benefit_key = form.benefit_key || 'CUSTOM'
      payload.benefit_value = raw
      payload.face_text = raw
      payload.face_value = 0
    }
    return payload
  }

  async function create(publish: boolean) {
    if (!form.name.trim()) {
      toast(t('请填写券名称'), false)
      step.value = 2
      return
    }
    if (!String(form.face_raw ?? '').trim()) {
      toast(t('请填写面值/参数'), false)
      step.value = 2
      return
    }
    busy.value = true
    try {
      const r = await api.mktCreateCoupon(
        hotelStore.hotelId,
        buildPayload(publish ? 'active' : 'draft'),
      )
      toast(publish ? `已创建并投放：${r.batch_no}` : '已存为草稿')
      closeWizard()
      setTab('build')
      await load()
    } catch (e: any) {
      toast(e?.message || t('创建失败'), false)
    } finally {
      busy.value = false
    }
  }

  return {
    showWizard,
    step,
    form,
    genBno,
    openWizard,
    closeWizard,
    copyBatch,
    create,
  }
}
