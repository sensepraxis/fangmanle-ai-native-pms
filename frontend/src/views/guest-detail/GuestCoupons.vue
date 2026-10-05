<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ORDER_ST_CN } from '../../lib/ui'

defineProps<{
  coupons: any[]
  g: any
  orders: any[]
  redeemCode: string
  redeemCodeBusy: boolean
  redeemHint: string
  redeemErr: string
  redeemModal: { coupon: any; orderId: number | null } | null
  redeemBusyId: number | null
  couponStCn: Record<string, string>
  redeemCn: Record<string, string>
}>()

const emit = defineEmits<{
  'update:redeemCode': [string]
  'redeem-by-code': []
  'open-redeem': [any]
  'confirm-redeem': []
  'close-redeem': []
}>()
</script>

<template>
  <section class="card orders-card coupon-card">
    <h3 class="card-h !mb-0 px-4 pt-4 pb-3 flex items-center gap-2 flex-wrap">
      <span class="material-symbols-outlined text-primary text-[20px]">local_offer</span>
      {{ t('优惠券') }}
      <span v-if="coupons.length" class="text-xs font-normal text-on-surface-variant">{{
        t('共 {n} 张', { n: coupons.length })
      }}</span>
    </h3>
    <div class="px-4 pb-3 flex flex-wrap items-center gap-2">
      <input
        class="redeem-input"
        :value="redeemCode"
        :placeholder="t('输入/粘贴客人出示的券码')"
        @input="emit('update:redeemCode', ($event.target as HTMLInputElement).value)"
        @keyup.enter="emit('redeem-by-code')"
      />
      <button
        type="button"
        class="btn-hero"
        :disabled="redeemCodeBusy || !redeemCode.trim()"
        @click="emit('redeem-by-code')"
      >
        {{ redeemCodeBusy ? t('核销中…') : t('输券码核销') }}
      </button>
    </div>
    <p v-if="redeemHint" class="px-4 pb-2 text-sm text-green-700">{{ redeemHint }}</p>
    <p v-if="redeemErr && !redeemModal" class="px-4 pb-2 text-sm text-red-600">{{ redeemErr }}</p>
    <div class="overflow-auto">
      <table class="data w-full">
        <thead>
          <tr>
            <th class="text-left p-3">{{ t('领券人') }}</th>
            <th class="text-left p-3">{{ t('券码') }}</th>
            <th class="text-left p-3">{{ t('有效期') }}</th>
            <th class="text-left p-3">{{ t('券状态') }}</th>
            <th class="text-left p-3">{{ t('核销') }}</th>
            <th class="text-left p-3">{{ t('来源') }}</th>
            <th class="text-center p-3">{{ t('操作') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in coupons" :key="c.id || c.code" class="border-t border-outline-variant">
            <td class="p-3 text-sm">{{ c.recipient_name || g.name || '—' }}</td>
            <td class="p-3 font-mono text-sm">{{ c.code }}</td>
            <td class="p-3 text-sm text-on-surface-variant">
              {{ (c.valid_from || '—').slice(0, 10) }} ~ {{ (c.valid_until || '—').slice(0, 10) }}
            </td>
            <td class="p-3 text-sm">{{ couponStCn[c.status] || c.status || '—' }}</td>
            <td class="p-3 text-sm">
              {{ redeemCn[c.redeem_status] || c.redeem_status || '—' }}
              <span v-if="c.used_at" class="block text-xs text-on-surface-variant">{{
                String(c.used_at).slice(0, 16)
              }}</span>
            </td>
            <td class="p-3 text-sm">
              <span class="src-tag" :class="c.source || 'wecom'">{{
                c.source_label || c.channel || '—'
              }}</span>
            </td>
            <td class="p-3 text-center">
              <button
                v-if="c.can_redeem"
                type="button"
                class="text-primary text-sm font-semibold"
                :disabled="redeemBusyId === c.id"
                @click="emit('open-redeem', c)"
              >
                {{ t('核销') }}
              </button>
              <span v-else-if="c.redeem_blocked_reason" class="text-xs text-on-surface-variant">{{
                c.redeem_blocked_reason
              }}</span>
              <span v-else class="text-xs text-on-surface-variant">—</span>
            </td>
          </tr>
          <tr v-if="!coupons.length">
            <td colspan="7" class="p-6 text-center text-on-surface-variant">
              {{ t('暂无优惠券') }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <div v-if="redeemModal" class="care-overlay" @click.self="emit('close-redeem')">
    <div class="care-modal" role="dialog">
      <div class="care-head">
        <div>
          <h2 class="care-title">{{ t('核销优惠券') }}</h2>
          <p class="care-sub">{{ redeemModal.coupon.name }} · {{ redeemModal.coupon.code }}</p>
        </div>
        <button
          type="button"
          class="care-close"
          :aria-label="t('关闭')"
          @click="emit('close-redeem')"
        >
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
      <label class="care-label">{{ t('关联订单（可选，建议选在住/待入住）') }}</label>
      <select
        v-model="redeemModal.orderId"
        class="care-textarea"
        style="min-height: auto; height: 42px; padding: 8px 10px"
      >
        <option :value="null">{{ t('不关联订单') }}</option>
        <option v-for="o in orders" :key="o.id" :value="o.id">
          {{ o.order_no }} · {{ o.check_in }} · {{ ORDER_ST_CN[o.status] || o.status }}
        </option>
      </select>
      <p v-if="redeemErr" class="care-err">{{ redeemErr }}</p>
      <div class="care-actions">
        <button type="button" class="btn-hero" @click="emit('close-redeem')">
          {{ t('取消') }}
        </button>
        <button
          type="button"
          class="btn-hero primary"
          :disabled="!!redeemBusyId"
          @click="emit('confirm-redeem')"
        >
          {{ redeemBusyId ? t('核销中…') : t('确认核销') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './guest-detail-shared.css';
</style>
