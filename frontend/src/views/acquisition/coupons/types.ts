// SPDX-License-Identifier: Apache-2.0
export type TabKey = 'build' | 'grant' | 'redeem'
export type GrantSub = 'segment' | 'guest' | 'rules' | 'records'
export type GrantMode = 'segment' | 'guest'

export type CouponAiKind =
  'smart_create' | 'audience' | 'rule_recommend' | 'budget' | 'redeem_insight'

export type NarrativeSlot = { loading: boolean; insight: any | null; error: string }

export type CouponTypeMeta = {
  nm: string
  ico: string
  ds: string
  lbl: string
  hint: string
  ph: string
  thrHide: boolean
  isText?: boolean
  isBenefit?: boolean
  isDiscount?: boolean
}

export type CouponForm = {
  type: string
  batch_no: string
  name: string
  face_raw: string
  threshold: number
  max_discount: string
  benefit_key: string
  validity_mode: 'FIXED' | 'RELATIVE'
  validity_days: number
  total_qty: number
  per_user_qty: number
  valid_from: string
  valid_to: string
  rooms: string[]
  levels: string[]
}

export type GrantForm = {
  coupon_id: string | number
  mode: GrantMode
  segment: string | number
  guest_ids: number[]
  allow_over_limit: boolean
  over_limit_reason: string
}

export type SegmentPreview = {
  count: number
  samples: any[]
  segment_count?: number
  reachable_count?: number
  unreachable_count?: number
}
