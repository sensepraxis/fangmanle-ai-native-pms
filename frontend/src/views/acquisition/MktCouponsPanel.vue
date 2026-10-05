<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 优惠券中心 · 三入口：建券 / 发放 / 核销流水（只读；操作核销在客户 360）
 * 壳层：路由 tab/sub + KPI + 组合 composable / 子面板
 */
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { hotelStore } from '../../store/hotel'
import { TAB_ALIAS } from './coupons/constants'
import type { GrantSub, TabKey } from './coupons/types'
import { useCouponCatalog } from './coupons/useCouponCatalog'
import { useCouponAi } from './coupons/useCouponAi'
import { useCouponWizard } from './coupons/useCouponWizard'
import CouponWizard from './coupons/CouponWizard.vue'
import CouponBuildPane from './coupons/CouponBuildPane.vue'
import CouponGrantPane from './coupons/CouponGrantPane.vue'
import CouponRedeemPane from './coupons/CouponRedeemPane.vue'

const router = useRouter()
const route = useRoute()

function tabFromQuery(): TabKey {
  const q = String(route.query.tab || 'build')
  return TAB_ALIAS[q] || 'build'
}

function grantSubFromQuery(): GrantSub {
  const s = String(route.query.sub || '')
  if (s === 'records' || s === 'grants') return 'records'
  if (s === 'rules' || s === 'auto') return 'rules'
  if (s === 'segment') return 'segment'
  if (s === 'guest' || s === 'push' || s === 'do' || s === 'claim') return 'guest'
  const t = String(route.query.tab || '')
  if (t === 'grants') return 'records'
  if (t === 'rules') return 'rules'
  return 'guest'
}

const tab = ref<TabKey>(tabFromQuery())
const grantSub = ref<GrantSub>(grantSubFromQuery())

function syncQuery() {
  const query: Record<string, string> = { tab: tab.value }
  if (tab.value === 'grant' && grantSub.value !== 'guest') query.sub = grantSub.value
  router.replace({ path: '/acquisition/coupons', query })
}

function setTab(t: TabKey) {
  tab.value = t
  if (t === 'grant') {
    grantSub.value = 'guest'
    grantForm.mode = 'guest'
  }
  syncQuery()
}

function setGrantSub(s: GrantSub) {
  tab.value = 'grant'
  grantSub.value = s
  if (s === 'segment' || s === 'guest') {
    grantForm.mode = s
    if (s === 'segment') refreshSegmentPreview()
  }
  syncQuery()
}

const catalog = useCouponCatalog({ grantSub, setGrantSub })
const {
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
  activeCoupons,
  h5Guests,
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
} = catalog

const wizard = useCouponWizard({
  rows,
  roomTypeOpts,
  busy,
  setTab,
  load,
})
const { showWizard, step, form, openWizard, closeWizard, copyBatch, create, genBno } = wizard

const { aiGoal, aiTargetRedeem, aiTargetRoi, makeFetcher, narrativeExecutor } = useCouponAi({
  router,
  setTab,
  setGrantSub,
  openWizard,
  form,
  grantForm,
  load,
  refreshSegmentPreview,
  rulesPanelKey,
})

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(
  () => [route.query.tab, route.query.sub],
  () => {
    tab.value = tabFromQuery()
    grantSub.value = grantSubFromQuery()
  },
)
watch(
  () => [grantForm.segment, grantSub.value],
  () => {
    if (grantSub.value === 'segment') refreshSegmentPreview()
  },
)
watch(
  () => [grantForm.coupon_id, grantSub.value, guests.value.length],
  () => {
    if (grantSub.value === 'guest' || grantSub.value === 'segment') refreshOwnership()
  },
)
watch(
  () => grantForm.allow_over_limit,
  (on) => {
    if (!on) {
      grantForm.guest_ids = grantForm.guest_ids.filter((id) => !ownershipOf(id)?.at_limit)
      grantForm.over_limit_reason = ''
    }
  },
)
watch(step, (n) => {
  if (n === 2 && !form.batch_no) genBno()
})

function openGrantTab() {
  openGrant()
}
</script>

<template>
  <div class="page">
    <div class="head">
      <div>
        <h1>{{ t('优惠券') }}</h1>
      </div>
      <div class="head-actions">
        <button type="button" class="btn pri" @click="openWizard()">{{ t('新建优惠券') }}</button>
      </div>
    </div>

    <div class="kpis">
      <div class="kpi">
        <span class="kpi-ico material-symbols-outlined">confirmation_number</span>
        <div>
          <div class="lbl">{{ t('活跃批次') }}</div>
          <div class="val">{{ kpi.active }}</div>
          <div class="delta">{{ t('可发放 / 可领取') }}</div>
        </div>
      </div>
      <div class="kpi">
        <span class="kpi-ico material-symbols-outlined">send</span>
        <div>
          <div class="lbl">{{ t('已发放') }}</div>
          <div class="val">{{ kpi.granted }}</div>
          <div class="delta">{{ t('券实例合计') }}</div>
        </div>
      </div>
      <div class="kpi">
        <span class="kpi-ico material-symbols-outlined">verified</span>
        <div>
          <div class="lbl">{{ t('已核销') }}</div>
          <div class="val">{{ kpi.used }}</div>
          <div class="delta">{{ t('到店使用') }}</div>
        </div>
      </div>
      <div class="kpi">
        <span class="kpi-ico material-symbols-outlined">percent</span>
        <div>
          <div class="lbl">{{ t('核销率') }}</div>
          <div class="val">{{ kpi.rate }}%</div>
          <div class="delta">{{ t('已核销 / 已发放') }}</div>
        </div>
      </div>
    </div>

    <div class="tabs" role="tablist">
      <button type="button" class="tab" :class="{ on: tab === 'build' }" @click="setTab('build')">
        {{ t('建券') }}
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'grant' }" @click="openGrantTab()">
        {{ t('发放') }}
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'redeem' }" @click="setTab('redeem')">
        {{ t('核销流水') }}
      </button>
    </div>

    <CouponWizard
      v-if="showWizard"
      :form="form"
      :step="step"
      :busy="busy"
      :room-type-opts="roomTypeOpts"
      @update:step="step = $event"
      @close="closeWizard"
      @create="create"
    />

    <CouponBuildPane
      v-if="tab === 'build'"
      :rows="rows"
      v-model:ai-goal="aiGoal"
      v-model:ai-target-redeem="aiTargetRedeem"
      v-model:ai-target-roi="aiTargetRoi"
      :make-fetcher="makeFetcher"
      :narrative-executor="narrativeExecutor"
      :set-status="setStatus"
      :open-grant="openGrant"
      :copy-batch="copyBatch"
    />

    <CouponGrantPane
      v-else-if="tab === 'grant'"
      :grant-sub="grantSub"
      :grant-form="grantForm"
      :active-coupons="activeCoupons"
      :segments="segments"
      :segment-preview="segmentPreview"
      :h5-guests="h5Guests"
      v-model:guest-q="guestQ"
      :grants="grants"
      :rules-panel-key="rulesPanelKey"
      :busy="busy"
      v-model:ai-goal="aiGoal"
      :make-fetcher="makeFetcher"
      :narrative-executor="narrativeExecutor"
      :set-grant-sub="setGrantSub"
      :ownership-of="ownershipOf"
      :toggle-guest="toggleGuest"
      :toggle-all-h5-guests="toggleAllH5Guests"
      :do-grant="doGrant"
    />

    <CouponRedeemPane
      v-else-if="tab === 'redeem'"
      :redeem-ledger="redeemLedger"
      :make-fetcher="makeFetcher"
      :narrative-executor="narrativeExecutor"
    />
  </div>
</template>

<style scoped>
@import './coupons/coupons-shared.css';
</style>
