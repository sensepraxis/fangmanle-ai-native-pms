<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

import { computed } from 'vue'
import NarrativeInsightPanel from '../../../components/NarrativeInsightPanel.vue'
import { AI_UI, fmtDt } from './constants'
import type { CouponAiKind } from './types'
import { hotelStore } from '../../../store/hotel'

defineProps<{
  redeemLedger: any[]
  makeFetcher: (kind: CouponAiKind) => () => Promise<any>
  narrativeExecutor: (a: Record<string, any>) => Promise<any>
}>()

const aiResetKey = computed(() => hotelStore.hotelId)
</script>

<template>
  <div class="tab-pane">
    <div class="panel-box" style="margin-bottom: 12px; padding: 14px 16px">
      <NarrativeInsightPanel
        :title="AI_UI.redeem_insight.title"
        :idle="AI_UI.redeem_insight.idle"
        :run-label="AI_UI.redeem_insight.run"
        :rerun-label="AI_UI.redeem_insight.rerun"
        :wait-label="AI_UI.redeem_insight.wait"
        :reset-key="`redeem_insight:${aiResetKey}`"
        :fetcher="makeFetcher('redeem_insight')"
        :executor="narrativeExecutor"
      />
    </div>

    <div class="table-wrap panel-box">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ t('核销时间') }}</th>
            <th>{{ t('来源') }}</th>
            <th>{{ t('订单号') }}</th>
            <th>{{ t('券批次 / 券名') }}</th>
            <th>{{ t('券码') }}</th>
            <th>{{ t('抵扣') }}</th>
            <th>{{ t('客户') }}</th>
            <th>{{ t('状态') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in redeemLedger" :key="g.id">
            <td>{{ fmtDt(g.used_at || g.redeemed_at) }}</td>
            <td>
              <span class="src-pill">{{
                g.source_label || g.wallet_source || g.source || '—'
              }}</span>
            </td>
            <td>
              {{ g.used_order_id || g.order_id ? `ORD-${g.used_order_id || g.order_id}` : '—' }}
            </td>
            <td class="bno">{{ g.batch_no || g.coupon_name || g.name || '—' }}</td>
            <td class="bno">{{ g.coupon_code || g.code || '—' }}</td>
            <td>
              {{
                g.used_amount != null
                  ? `¥${g.used_amount}`
                  : g.amount_saved != null
                    ? `¥${g.amount_saved}`
                    : g.discount_label || '—'
              }}
            </td>
            <td>
              {{ g.guest_name || g.customer_name || '—' }}
              <span
                v-if="g.recipient_name && g.recipient_name !== (g.guest_name || g.customer_name)"
                class="muted-sub"
              >
                · {{ t('领券人') }} {{ g.recipient_name }}</span
              >
            </td>
            <td>
              <span class="status active">{{ t('成功') }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!redeemLedger.length" class="empty">{{ t('暂无核销流水') }}</p>
    </div>
  </div>
</template>

<style scoped>
@import './coupons-shared.css';
</style>
