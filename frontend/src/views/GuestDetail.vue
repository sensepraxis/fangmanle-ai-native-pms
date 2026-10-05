<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 客户 360 画像 —— 薄壳：组合 guest-detail 子模块
 * 数据：GET /api/guests/:id
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { fmt, ORDER_ST_CN, ORDER_ST_PILL } from '../lib/ui'
import { useGuest360 } from './guest-detail/useGuest360'
import { useGuestCare } from './guest-detail/useGuestCare'
import GuestIdentity from './guest-detail/GuestIdentity.vue'
import GuestPrefRadar from './guest-detail/GuestPrefRadar.vue'
import GuestLtv from './guest-detail/GuestLtv.vue'
import GuestCoupons from './guest-detail/GuestCoupons.vue'
import GuestTrail from './guest-detail/GuestTrail.vue'
import GuestCareModal from './guest-detail/GuestCareModal.vue'

const router = useRouter()
const g360 = useGuest360()
const {
  d,
  loading,
  oneidExpanded,
  toggleOneidAudit,
  g,
  h5Membership,
  orders,
  tags,
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
} = g360

const guestId = computed(() => g.value?.id as number | undefined)
const care = useGuestCare({
  guestId,
  wecomBound,
  wecomExternalId,
})
const {
  careOpen,
  careMaterial,
  careDraft,
  careGenerated,
  careGenerating,
  careSending,
  careHint,
  careError,
  careSource,
  careCopied,
  careSent,
  wecomInChat,
  openCareModal,
  closeCareModal,
  copyCareDraft,
  generateCareDraft,
  sendCareMessage,
} = care

function goOrder(id: number) {
  router.push(`/orders/${id}`)
}
function goCare() {
  void openCareModal()
}
function goVip() {
  void openCareModal()
}
</script>

<template>
  <div class="page gp">
    <div v-if="loading" class="text-on-surface-variant text-sm">{{ t('加载中…') }}</div>
    <template v-else-if="d">
      <div v-if="lowScoreReview" class="alert-low">
        <span class="material-symbols-outlined">warning</span>
        <span>{{ t('低分评价待处理（{n} 星）', { n: lowScoreReview.rating }) }}</span>
        <div class="alert-actions">
          <button type="button" class="alert-btn" @click="goVip">{{ t('发送关怀') }}</button>
          <button type="button" class="alert-btn ghost" @click="goCare">{{ t('住中关怀') }}</button>
        </div>
      </div>

      <GuestIdentity
        :g="g"
        :vip-label="vipLabel"
        :churn-pct="churnPct"
        :in-wecom-private="inWecomPrivate"
        :wecom-bound="wecomBound"
        :wecom-external-id="wecomExternalId"
        :wecom="wecom"
        :phone-display="phoneDisplay"
        :stay-count="stayCount"
        :tags="tags"
        :h5-membership="h5Membership"
        :oneid-expanded="oneidExpanded"
        :one-id-label="oneIdLabel"
        :channel-count="channelCount"
        :merge-confidence="mergeConfidence"
        :channel-chips="channelChips"
        :avg-ticket="avgTicket"
        :ltv-score="ltvScore"
        :next-stay="nextStay"
        :next-stay-nights="nextStayNights"
        @care="goCare"
        @toggle-oneid="toggleOneidAudit"
      />

      <GuestPrefRadar
        :next-action="nextAction"
        :psych-radar="psychRadar"
        :fingerprint="fingerprint"
        :fmt-int="fmtInt"
        @care="goCare"
      />

      <GuestLtv
        :est-ltv="estLtv"
        :ltv-chart="ltvChart"
        :g="g"
        :stay-count="stayCount"
        :churn-pct="churnPct"
        :needle-deg="needleDeg"
        :risk-label="riskLabel"
        :fmt-int="fmtInt"
      />

      <GuestCoupons
        :coupons="coupons"
        :g="g"
        :orders="orders"
        :redeem-code="redeemCode"
        :redeem-code-busy="redeemCodeBusy"
        :redeem-hint="redeemHint"
        :redeem-err="redeemErr"
        :redeem-modal="redeemModal"
        :redeem-busy-id="redeemBusyId"
        :coupon-st-cn="COUPON_ST_CN"
        :redeem-cn="REDEEM_CN"
        @update:redeem-code="redeemCode = $event"
        @redeem-by-code="redeemByCode"
        @open-redeem="openRedeemModal"
        @confirm-redeem="confirmRedeem"
        @close-redeem="redeemModal = null"
      />

      <GuestTrail
        :channel-trail="channelTrail"
        :sentiment-score="sentimentScore"
        :stay-count="stayCount"
      />

      <div class="layout insight-row">
        <aside class="col">
          <div class="card">
            <h3 class="card-h">{{ t('客房偏好') }}</h3>
            <ul class="pref-list">
              <li v-for="p in roomPrefs" :key="p">
                <span class="material-symbols-outlined text-[16px] text-tertiary"
                  >check_circle</span
                >
                {{ p }}
              </li>
            </ul>
          </div>
          <div class="card">
            <h3 class="card-h">{{ t('数据源综合') }}</h3>
            <div class="space-y-1">
              <div v-for="s in sourceBars" :key="s.name" class="src-row">
                <div class="flex items-center gap-2 min-w-0">
                  <div
                    class="w-7 h-7 rounded flex items-center justify-center shrink-0"
                    :class="s.box"
                  >
                    <span class="material-symbols-outlined text-[14px]">source</span>
                  </div>
                  <span class="text-sm truncate">{{ s.name }}</span>
                </div>
                <span class="text-sm text-on-surface-variant font-mono">{{ s.pct }}%</span>
              </div>
            </div>
          </div>
        </aside>

        <main class="col col-mid">
          <div class="card">
            <div class="flex items-start justify-between gap-2 mb-1">
              <h3 class="card-h !mb-0">{{ t('已识别画像标签') }}</h3>
              <button
                type="button"
                class="tag-cfg-link"
                @click="router.push('/b-data/tag-ecosystem-overview')"
              >
                {{ t('标签如何配置') }}
              </button>
            </div>
            <div class="flex flex-wrap gap-2 mb-3">
              <button
                v-for="tag in tags.slice(0, 6)"
                :key="tag.name"
                type="button"
                class="px-3 py-1.5 bg-primary-container text-on-primary-container rounded-lg text-sm font-semibold border-0 cursor-pointer"
                @click="router.push('/b-data/master-tag-library')"
              >
                {{ tag.name }}
              </button>
              <span
                v-if="!tags.length"
                class="px-3 py-1.5 bg-primary-container text-on-primary-container rounded-lg text-sm font-semibold"
                >{{ motiveTags.primary }}</span
              >
            </div>
            <div class="card !shadow-none !border !p-3 bg-surface-container-low">
              <h3 class="card-h !mb-2">{{ t('情感与概率') }}</h3>
              <div class="flex items-center gap-3 mb-3">
                <div
                  class="w-12 h-12 rounded-full flex items-center justify-center border-4 shrink-0"
                  :class="sentiment.ring"
                >
                  <span class="material-symbols-outlined text-[22px]" :class="sentiment.cls"
                    >sentiment_satisfied</span
                  >
                </div>
                <div>
                  <p class="m-0 font-bold text-sm" :class="sentiment.cls">{{ sentiment.label }}</p>
                  <p class="m-0 text-xs text-on-surface-variant">{{ sentiment.tip }}</p>
                </div>
              </div>
              <div class="rfm">
                <div>
                  <div class="flex justify-between text-sm mb-1">
                    <span>{{ t('最近消费') }}</span
                    ><span class="font-medium">{{ orders[0]?.check_in || '—' }}</span>
                  </div>
                  <div class="bar"><div style="width: 70%" /></div>
                </div>
                <div>
                  <div class="flex justify-between text-sm mb-1">
                    <span>{{ t('消费频率') }}</span
                    ><span class="font-medium">{{ stayCount }} {{ t('次') }}</span>
                  </div>
                  <div class="bar">
                    <div :style="{ width: Math.min(100, stayCount * 8) + '%' }" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>

        <aside class="col">
          <div class="card ai-side">
            <div class="ai-side-h">
              <h3 class="m-0 font-bold text-sm">{{ t('AI 客户洞察') }}</h3>
              <span class="live">{{ t('实时') }}</span>
            </div>
            <div class="p-4 flex flex-col gap-3">
              <button type="button" class="suggest" @click="goCare">{{ t('发送召回优惠') }}</button>
              <button type="button" class="suggest" @click="scrollTo('section-ltv')">
                {{ t('查看价值曲线') }}
              </button>
              <button type="button" class="suggest" @click="goCare">{{ t('记录互动') }}</button>
            </div>
          </div>
          <div class="alert-warm">
            <h4 class="m-0 text-sm font-bold text-[#e65100] mb-1">{{ t('建议复核：生日礼遇') }}</h4>
            <p class="m-0 text-sm text-[#e65100] opacity-90">
              {{ t('系统检测到临近生日。是否自动安排欢迎果盘配送与延迟退房预授权？') }}
            </p>
            <div class="mt-3 flex gap-2">
              <button type="button" class="btn-warm" @click="goCare">{{ t('审批并排程') }}</button>
              <button type="button" class="btn-warm-ghost">{{ t('忽略') }}</button>
            </div>
          </div>
        </aside>
      </div>

      <section class="card orders-card">
        <h3 class="card-h !mb-0 px-4 pt-4 pb-3">{{ t('订单明细') }}</h3>
        <div class="overflow-auto">
          <table class="data w-full">
            <thead>
              <tr>
                <th class="text-left p-3">{{ t('订单号') }}</th>
                <th class="text-left p-3">{{ t('入住区间') }}</th>
                <th class="text-right p-3">{{ t('金额') }}</th>
                <th class="text-left p-3">{{ t('状态') }}</th>
                <th class="text-left p-3">{{ t('归属档案') }}</th>
                <th class="text-center p-3">{{ t('操作') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="o in orders.slice(0, 12)"
                :key="o.id"
                class="border-t border-outline-variant hover:bg-surface-container-low cursor-pointer"
                @click="goOrder(o.id)"
              >
                <td class="p-3 font-mono text-sm">{{ o.order_no }}</td>
                <td class="p-3 text-sm text-on-surface-variant">
                  {{ o.check_in }} ~ {{ o.check_out }}
                </td>
                <td class="p-3 text-right font-medium">{{ fmt(o.total_amount) }}</td>
                <td class="p-3">
                  <span class="pill" :class="ORDER_ST_PILL[o.status] || 'pill-slate'">
                    {{ ORDER_ST_CN[o.status] || o.status }}</span
                  >
                </td>
                <td class="p-3 text-xs text-on-surface-variant">
                  <span v-if="o.record_guest_name"
                    >{{ o.record_guest_name }} · #{{ o.record_guest_id }}</span
                  >
                  <span v-else>{{ t('本档案') }}</span>
                </td>
                <td class="p-3 text-center text-primary text-sm font-semibold">{{ t('查看') }}</td>
              </tr>
              <tr v-if="!orders.length">
                <td colspan="6" class="p-6 text-center text-on-surface-variant">
                  {{ t('暂无订单') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>

    <GuestCareModal
      :open="careOpen"
      :guest-name="g.name"
      :care-material="careMaterial"
      :care-draft="careDraft"
      :care-source="careSource"
      :care-hint="careHint"
      :care-error="careError"
      :care-sent="careSent"
      :care-copied="careCopied"
      :care-generating="careGenerating"
      :care-generated="careGenerated"
      :care-sending="careSending"
      :wecom-bound="wecomBound"
      :wecom-in-chat="wecomInChat"
      :wecom="wecom"
      @close="closeCareModal"
      @update:care-material="careMaterial = $event"
      @update:care-draft="careDraft = $event"
      @generate="generateCareDraft"
      @send="sendCareMessage"
      @copy="copyCareDraft"
    />
  </div>
</template>

<style scoped>
@import './guest-detail/guest-detail-shared.css';
</style>
