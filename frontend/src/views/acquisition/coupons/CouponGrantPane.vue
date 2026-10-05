<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

import { computed } from 'vue'
import NarrativeInsightPanel from '../../../components/NarrativeInsightPanel.vue'
import MktGrantRulesPanel from '../MktAutomationPanel.vue'
import { AI_UI, CHANNEL_CN, GRANT_ST, fmtDt } from './constants'
import type { CouponAiKind, GrantForm, GrantSub, SegmentPreview } from './types'
import { hotelStore } from '../../../store/hotel'

const props = defineProps<{
  grantSub: GrantSub
  grantForm: GrantForm
  activeCoupons: any[]
  segments: any[]
  segmentPreview: SegmentPreview | null
  h5Guests: any[]
  guestQ: string
  grants: any[]
  rulesPanelKey: number
  busy: boolean
  aiGoal: string
  makeFetcher: (kind: CouponAiKind) => () => Promise<any>
  narrativeExecutor: (a: Record<string, any>) => Promise<any>
  setGrantSub: (s: GrantSub) => void
  ownershipOf: (guestId: number) => any
  toggleGuest: (id: number) => void
  toggleAllH5Guests: () => void
  doGrant: () => void | Promise<void>
}>()

const emit = defineEmits<{
  (e: 'update:guestQ', v: string): void
  (e: 'update:aiGoal', v: string): void
}>()

const aiResetKey = computed(() => hotelStore.hotelId)
</script>

<template>
  <div class="tab-pane">
    <div class="subtabs" role="tablist">
      <button
        type="button"
        class="subtab"
        :class="{ on: grantSub === 'segment' }"
        @click="setGrantSub('segment')"
      >
        {{ t('按客群发放') }}
      </button>
      <button
        type="button"
        class="subtab"
        :class="{ on: grantSub === 'guest' }"
        @click="setGrantSub('guest')"
      >
        {{ t('指定客人发放') }}
      </button>
      <button
        type="button"
        class="subtab"
        :class="{ on: grantSub === 'rules' }"
        @click="setGrantSub('rules')"
      >
        {{ t('基于规则自动发放') }}
      </button>
      <button
        type="button"
        class="subtab"
        :class="{ on: grantSub === 'records' }"
        @click="setGrantSub('records')"
      >
        {{ t('发放记录') }}
      </button>
    </div>

    <div v-if="grantSub === 'rules'" class="rules-embed">
      <div class="panel-box" style="margin-bottom: 12px; padding: 14px 16px">
        <NarrativeInsightPanel
          :title="AI_UI.rule_recommend.title"
          :idle="AI_UI.rule_recommend.idle"
          :run-label="AI_UI.rule_recommend.run"
          :rerun-label="AI_UI.rule_recommend.rerun"
          :wait-label="AI_UI.rule_recommend.wait"
          :reset-key="`rule_recommend:${aiResetKey}`"
          :fetcher="makeFetcher('rule_recommend')"
          :executor="narrativeExecutor"
        />
      </div>
      <MktGrantRulesPanel :key="rulesPanelKey" embedded />
    </div>

    <div v-else-if="grantSub === 'records'" class="table-wrap panel-box">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ t('客户') }}</th>
            <th>{{ t('手机号') }}</th>
            <th>{{ t('券批次') }}</th>
            <th>{{ t('领取渠道') }}</th>
            <th>{{ t('领取时间') }}</th>
            <th>{{ t('状态') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in grants" :key="g.id">
            <td>{{ g.guest_name || g.guest_id }}</td>
            <td>{{ g.guest_phone || '—' }}</td>
            <td class="bno">{{ g.batch_no || g.coupon_name }}</td>
            <td>{{ g.grant_channel_label || CHANNEL_CN[g.grant_channel] || g.grant_channel }}</td>
            <td>{{ fmtDt(g.grant_at) }}</td>
            <td>
              <span
                class="status"
                :class="
                  ['USED', 'used'].includes(g.status)
                    ? 'active'
                    : ['EXPIRED', 'expired'].includes(g.status)
                      ? 'expired'
                      : 'draft'
                "
              >
                {{ GRANT_ST[g.status] || g.status }}</span
              >
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!grants.length" class="empty">{{ t('暂无发放记录') }}</p>
    </div>

    <div v-else-if="grantSub === 'segment'" class="panel grant-panel panel-box">
      <div class="ai-with-inputs" style="margin-bottom: 16px">
        <div class="ai-inputs">
          <label>{{ t('发券目标（可选）') }}</label>
          <input
            :value="aiGoal"
            type="text"
            :placeholder="t('如：唤醒沉默客户')"
            @input="emit('update:aiGoal', ($event.target as HTMLInputElement).value)"
          />
        </div>
        <NarrativeInsightPanel
          :title="AI_UI.audience.title"
          :idle="AI_UI.audience.idle"
          :run-label="AI_UI.audience.run"
          :rerun-label="AI_UI.audience.rerun"
          :wait-label="AI_UI.audience.wait"
          :reset-key="`audience:${aiResetKey}`"
          :fetcher="makeFetcher('audience')"
          :executor="narrativeExecutor"
        />
      </div>

      <h3>{{ t('按客群发放') }}</h3>
      <p class="grant-lead">
        {{ t('先选要发的券，再选客群；实际推送 = 全局分群 ∩ 企微私域可达客人。') }}
      </p>

      <section class="grant-step">
        <div class="step-head">
          <span class="step-n">1</span>
          <div>
            <div class="step-t">{{ t('选择券批次') }}</div>
          </div>
        </div>
        <select v-model="grantForm.coupon_id" class="batch-select">
          <option value="">{{ t('请选择批次') }}</option>
          <option v-for="r in activeCoupons" :key="r.id" :value="r.id">
            {{ r.name }}（{{ r.batch_no }}）
          </option>
        </select>
      </section>

      <section class="grant-step">
        <div class="step-head">
          <span class="step-n">2</span>
          <div>
            <div class="step-t">{{ t('选择客群') }}</div>
          </div>
        </div>
        <div class="seg-list">
          <button
            v-for="s in segments"
            :key="s.key || s.segment_id"
            type="button"
            class="seg-card"
            :class="{ on: String(grantForm.segment) === String(s.key || s.segment_id) }"
            @click="grantForm.segment = s.key || s.segment_id"
          >
            <div class="mt">{{ s.label || s.name }}</div>
            <div class="md">{{ s.desc }}</div>
          </button>
        </div>
        <p v-if="!segments.length" class="empty-inline">
          {{ t('暂无全局客群，请先到「客群运营」创建分群') }}
        </p>
        <div v-if="segmentPreview" class="preview-box">
          <template v-if="segmentPreview.segment_count != null">
            {{ t('该客群共') }} <b>{{ segmentPreview.segment_count }}</b>
            {{ t('人，企微私域可达') }}
            <b>{{ segmentPreview.reachable_count ?? segmentPreview.count }}</b> {{ t('人') }}
            <span v-if="segmentPreview.unreachable_count">
              （{{ t('另') }} {{ segmentPreview.unreachable_count }} {{ t('人')
              }}{{ t('未进私域，建议短信/前台引导加企微）') }}
            </span>
          </template>
          <template v-else
            >{{ t('预计命中') }} <b>{{ segmentPreview.count }}</b> {{ t('人') }}</template
          >
          <span v-if="segmentPreview.samples?.length">
            · {{ t('示例') }}：{{ segmentPreview.samples.map((x: any) => x.name).join('、') }}</span
          >
        </div>
      </section>

      <div class="grant-foot">
        <button
          type="button"
          class="btn pri"
          :disabled="busy || !grantForm.coupon_id || !grantForm.segment"
          @click="doGrant"
        >
          {{ t('确认按客群发放') }}
        </button>
      </div>
    </div>

    <div v-else class="panel grant-panel panel-box">
      <h3>{{ t('指定客人发放') }}</h3>

      <section class="grant-step">
        <div class="step-head">
          <span class="step-n">1</span>
          <div>
            <div class="step-t">{{ t('选择券批次') }}</div>
          </div>
        </div>
        <select v-model="grantForm.coupon_id" class="batch-select">
          <option value="">{{ t('请选择批次') }}</option>
          <option v-for="r in activeCoupons" :key="r.id" :value="r.id">
            {{ r.name }}（{{ r.batch_no }}）
          </option>
        </select>
      </section>

      <section class="grant-step">
        <div class="step-head">
          <span class="step-n">2</span>
          <div>
            <div class="step-t">{{ t('选择发放对象') }}</div>
          </div>
        </div>
        <div class="guest-toolbar">
          <input
            :value="guestQ"
            :placeholder="t('搜索姓名 / 手机号')"
            @input="emit('update:guestQ', ($event.target as HTMLInputElement).value)"
          />
          <button type="button" class="btn sm" @click="toggleAllH5Guests">
            {{ t('全选可发客人') }}
          </button>
        </div>
        <div class="guest-list">
          <label
            v-for="g in h5Guests"
            :key="g.guest_id"
            class="gchk"
            :class="{ blocked: ownershipOf(g.guest_id)?.at_limit && !grantForm.allow_over_limit }"
          >
            <input
              type="checkbox"
              :checked="grantForm.guest_ids.includes(g.guest_id)"
              :disabled="!!ownershipOf(g.guest_id)?.at_limit && !grantForm.allow_over_limit"
              @change="toggleGuest(g.guest_id)"
            />
            <span>{{ g.name }} · {{ g.phone || '—' }}</span>
            <span class="mini">{{ t('私域') }}</span>
            <span v-if="ownershipOf(g.guest_id)?.at_limit" class="mini hold">{{
              t('已持有')
            }}</span>
            <span v-else-if="ownershipOf(g.guest_id)?.used" class="mini used">{{
              t('曾核销')
            }}</span>
          </label>
          <p v-if="!h5Guests.length" class="empty-inline">{{ t('暂无企微私域客人') }}</p>
        </div>
        <div class="compensate-box">
          <label class="chk">
            <input v-model="grantForm.allow_over_limit" type="checkbox" />{{
              t('补偿强制发放（允许对已持有客人再发一张）')
            }}</label
          >
          <input
            v-if="grantForm.allow_over_limit"
            v-model="grantForm.over_limit_reason"
            class="batch-select"
            :placeholder="t('必填：补偿原因，如「差评安抚」「上门体验补偿」')"
          />
        </div>
      </section>

      <div class="grant-foot">
        <button
          type="button"
          class="btn pri"
          :disabled="busy || !grantForm.coupon_id"
          @click="doGrant"
        >
          {{ t('确认发放给选中客人') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './coupons-shared.css';

.ai-with-inputs :deep(.narrative-ai) {
  margin: 0;
  border: none;
  padding: 0;
  background: transparent;
}
</style>
