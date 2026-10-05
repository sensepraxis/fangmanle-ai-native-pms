<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../../lib/i18n'

import { computed } from 'vue'
import NarrativeInsightPanel from '../../../components/NarrativeInsightPanel.vue'
import { AI_UI, TYPES, ST_CN, shortRange } from './constants'
import type { CouponAiKind } from './types'
import { hotelStore } from '../../../store/hotel'

const props = defineProps<{
  rows: any[]
  aiGoal: string
  aiTargetRedeem: number
  aiTargetRoi: string
  makeFetcher: (kind: CouponAiKind) => () => Promise<any>
  narrativeExecutor: (a: Record<string, any>) => Promise<any>
  setStatus: (id: number, status: string) => void | Promise<void>
  openGrant: (couponId?: number | string) => void
  copyBatch: (r: any) => void
}>()

const emit = defineEmits<{
  (e: 'update:aiGoal', v: string): void
  (e: 'update:aiTargetRedeem', v: number): void
  (e: 'update:aiTargetRoi', v: string): void
}>()

const aiResetKey = computed(() => hotelStore.hotelId)
</script>

<template>
  <div class="tab-pane">
    <div class="ai-grid">
      <div class="ai-with-inputs panel-box">
        <div class="ai-inputs">
          <label>{{ t('经营目标') }}</label>
          <input
            :value="aiGoal"
            type="text"
            :placeholder="t('如：唤醒沉默客户、周中冲量、拉新办会员')"
            @input="emit('update:aiGoal', ($event.target as HTMLInputElement).value)"
          />
        </div>
        <NarrativeInsightPanel
          :title="AI_UI.smart_create.title"
          :idle="AI_UI.smart_create.idle"
          :run-label="AI_UI.smart_create.run"
          :rerun-label="AI_UI.smart_create.rerun"
          :wait-label="AI_UI.smart_create.wait"
          :reset-key="`smart_create:${aiResetKey}`"
          :fetcher="makeFetcher('smart_create')"
          :executor="narrativeExecutor"
        />
      </div>

      <div class="ai-with-inputs panel-box">
        <div class="ai-inputs row2">
          <div>
            <label>{{ t('目标核销率 %') }}</label>
            <input
              :value="aiTargetRedeem"
              type="number"
              min="5"
              max="80"
              @input="
                emit('update:aiTargetRedeem', Number(($event.target as HTMLInputElement).value))
              "
            />
          </div>
          <div>
            <label>{{ t('目标投产比') }}</label>
            <input
              :value="aiTargetRoi"
              type="text"
              :placeholder="t('如 1:3')"
              @input="emit('update:aiTargetRoi', ($event.target as HTMLInputElement).value)"
            />
          </div>
        </div>
        <NarrativeInsightPanel
          :title="AI_UI.budget.title"
          :idle="AI_UI.budget.idle"
          :run-label="AI_UI.budget.run"
          :rerun-label="AI_UI.budget.rerun"
          :wait-label="AI_UI.budget.wait"
          :reset-key="`budget:${aiResetKey}`"
          :fetcher="makeFetcher('budget')"
          :executor="narrativeExecutor"
        />
      </div>
    </div>

    <div class="table-wrap panel-box">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ t('批次号') }}</th>
            <th>{{ t('名称') }}</th>
            <th>{{ t('类型') }}</th>
            <th>{{ t('面值') }}</th>
            <th>{{ t('剩余/总量') }}</th>
            <th>{{ t('已核销') }}</th>
            <th>{{ t('有效期') }}</th>
            <th>{{ t('状态') }}</th>
            <th>{{ t('操作') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>
              <span class="bno">{{ r.batch_no }}</span>
            </td>
            <td class="name">{{ r.name }}</td>
            <td>
              <span class="type" :class="'type-' + (r.coupon_type || r.type)">
                {{ TYPES[r.coupon_type || r.type]?.nm || r.coupon_type || r.type }}</span
              >
            </td>
            <td>{{ r.face_text || r.discount_label }}</td>
            <td>
              {{ r.remaining ?? Math.max(0, (r.total_qty || 0) - (r.granted || 0)) }} /
              {{ r.total_qty }}
            </td>
            <td>{{ r.used }}</td>
            <td>{{ shortRange(r.valid_from, r.valid_to) }}</td>
            <td>
              <span class="status" :class="r.status">{{ ST_CN[r.status] || r.status }}</span>
            </td>
            <td class="ops">
              <button
                v-if="r.status === 'draft'"
                type="button"
                class="more"
                @click="setStatus(r.id, 'active')"
              >
                {{ t('投放') }}
              </button>
              <button
                v-if="r.status === 'active'"
                type="button"
                class="more"
                @click="setStatus(r.id, 'paused')"
              >
                {{ t('停发') }}
              </button>
              <button
                v-if="r.status === 'paused'"
                type="button"
                class="more"
                @click="setStatus(r.id, 'active')"
              >
                {{ t('恢复') }}
              </button>
              <button
                v-if="r.status === 'active'"
                type="button"
                class="more"
                @click="openGrant(r.id)"
              >
                {{ t('去发放') }}
              </button>
              <button type="button" class="more" @click="copyBatch(r)">{{ t('复制') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="pager">
        <span>{{ t('共') }} {{ rows.length }} {{ t('条') }}</span>
      </div>
      <p v-if="!rows.length" class="empty">{{ t('暂无批次，点击「新建优惠券」开始') }}</p>
    </div>
  </div>
</template>

<style scoped>
@import './coupons-shared.css';

.ai-with-inputs {
  padding: 14px 16px;
}
.ai-with-inputs :deep(.narrative-ai) {
  margin: 0;
  border: none;
  padding: 0;
  background: transparent;
}
</style>
