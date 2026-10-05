<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 价格助手：AI 价格建议列表（收益管理 C1）
// 真实接口：api.listPricing 取房型的当前价/建议价/置信度/状态/护栏
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { PRICE_ST_PILL, fmt } from '../../lib/ui'

const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.listPricing(hotelStore.hotelId)
})

// 计算建议价相对当前价的差值（正=溢价，负=降价）
function delta(r: any) {
  const c = Number(r.current_price || 0)
  const s = Number(r.suggested_price || 0)
  return Math.round((s - c) * 100) / 100
}
// 置信度 pill：高=紫、中=蓝、低=灰
function confClass(c: string) {
  if (c === '高') return 'text-tertiary bg-tertiary-fixed'
  if (c === '中') return 'text-primary bg-primary-fixed'
  return 'text-on-surface-variant bg-surface-variant'
}
function statusLabel(st: string) {
  const m: Record<string, string> = {
    pending: t('待确认'),
    accepted: t('已采纳'),
    rejected: t('已驳回'),
    blocked: t('已拦截'),
  }
  return m[st] || st || '—'
}
</script>

<template>
  <div class="page">
    <!-- 页头 + 工具条（原型：7天/30天、自动巡航、采纳全部合规项） -->
    <div class="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
      <div>
        <h1 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
          {{ t('价格助手') }}
        </h1>
        <p class="text-on-surface-variant text-sm mt-1">
          {{ t('AI 驱动的价格建议，实现最优营收。') }}
        </p>
      </div>
      <div
        class="flex flex-wrap items-center gap-4 bg-surface-container-lowest p-2 rounded-xl shadow-sm border border-outline-variant"
      >
        <div class="flex items-center bg-surface-container-low rounded-lg p-1">
          <button
            class="px-3 py-1.5 text-sm font-medium rounded-md bg-surface-container-lowest shadow-sm text-on-surface"
          >
            {{ t('7 天') }}
          </button>
          <button
            class="px-3 py-1.5 text-sm font-medium rounded-md text-on-surface-variant hover:text-on-surface"
          >
            {{ t('30 天') }}
          </button>
        </div>
        <div class="w-px h-6 bg-outline-variant mx-2"></div>
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-on-surface-variant">{{ t('自动巡航') }}</span>
          <button
            aria-checked="false"
            class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent bg-surface-variant transition-colors"
            role="switch"
          >
            <span
              class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-on-secondary shadow ring-0 transition translate-x-0"
            ></span>
          </button>
        </div>
        <div class="w-px h-6 bg-outline-variant mx-2"></div>
        <button
          class="flex items-center gap-2 bg-primary text-on-primary px-4 py-2 rounded-lg font-medium hover:bg-on-primary-fixed-variant transition-colors shadow-sm"
        >
          {{ t('采纳全部合规项') }}
        </button>
      </div>
    </div>

    <!-- 价格建议表（v-for 绑定 api.listPricing） -->
    <div
      class="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant overflow-hidden"
    >
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-outline-variant bg-surface-container-low">
              <th class="py-3 px-4 font-label-lg text-on-surface-variant">{{ t('产品场景') }}</th>
              <th class="py-3 px-4 font-label-lg text-on-surface-variant">{{ t('日期') }}</th>
              <th class="py-3 px-4 font-label-lg text-on-surface-variant">{{ t('当前价') }}</th>
              <th class="py-3 px-4 font-label-lg text-on-surface-variant">{{ t('建议价') }}</th>
              <th class="py-3 px-4 font-label-lg text-on-surface-variant">{{ t('置信度') }}</th>
              <th class="py-3 px-4 font-label-lg text-on-surface-variant">{{ t('状态') }}</th>
              <th class="py-3 px-4 font-label-lg text-on-surface-variant text-right">
                {{ t('操作') }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant">
            <tr
              v-for="r in rows"
              :key="r.id"
              class="hover:bg-surface-bright transition-colors"
              :class="{ 'border-l-4 border-l-error': r.status === 'blocked' }"
            >
              <td class="py-4 px-4">
                <div class="flex items-center gap-3">
                  <div
                    class="w-8 h-8 rounded-lg bg-primary-container flex items-center justify-center text-on-primary-container"
                  ></div>
                  <div>
                    <p class="font-medium text-on-surface">{{ r.room_type_name || t('房型') }}</p>
                    <p class="text-xs text-on-surface-variant">{{ r.channel || t('全渠道') }}</p>
                  </div>
                </div>
              </td>
              <td class="py-4 px-4 text-sm text-on-surface">{{ r.biz_date || '—' }}</td>
              <td class="py-4 px-4 font-num-md text-on-surface">{{ fmt(r.current_price) }}</td>
              <td class="py-4 px-4">
                <div class="flex items-center gap-2">
                  <span class="font-num-md text-primary font-bold">{{
                    fmt(r.suggested_price)
                  }}</span>
                  <span
                    v-if="delta(r) !== 0"
                    class="flex items-center text-xs font-medium px-1.5 py-0.5 rounded"
                    :class="
                      delta(r) > 0 ? 'text-green-600 bg-green-50' : 'text-error bg-error-container'
                    "
                    >{{ delta(r) > 0 ? '+' : '-' }}¥{{ Math.abs(delta(r)) }}</span
                  >
                  <span
                    v-else
                    class="flex items-center text-xs font-medium text-on-surface-variant bg-surface-variant px-1.5 py-0.5 rounded"
                    >-</span
                  >
                </div>
              </td>
              <td class="py-4 px-4">
                <span
                  class="inline-flex items-center gap-1 text-xs font-medium rounded-full px-2 py-1"
                  :class="confClass(r.confidence)"
                  >{{ r.confidence || '—' }}</span
                >
              </td>
              <td class="py-4 px-4">
                <div class="flex flex-col gap-1">
                  <span
                    class="inline-flex w-max items-center gap-1 text-xs font-medium rounded-md px-2 py-1"
                    :class="PRICE_ST_PILL[r.status] || 'pill pill-slate'"
                    >{{ statusLabel(r.status) }}</span
                  >
                  <span
                    v-if="r.status === 'blocked' && r.guardrail_msg"
                    class="text-[11px] text-error"
                    >低于最低价地板 ({{ r.guardrail_msg }})</span
                  >
                </div>
              </td>
              <td class="py-4 px-4 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    class="text-primary hover:bg-primary-fixed p-1.5 rounded-md transition-colors"
                  >
                    {{ t('查看推导') }}
                  </button>
                  <button
                    v-if="r.status !== 'blocked'"
                    class="bg-primary-container text-on-primary-container hover:bg-primary px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
                  >
                    {{ t('采纳') }}
                  </button>
                  <button
                    v-else
                    class="bg-surface-variant text-on-surface-variant opacity-50 cursor-not-allowed px-3 py-1.5 rounded-md text-sm font-medium"
                    disabled
                  >
                    {{ t('采纳') }}
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="7" class="py-8 text-center text-on-surface-variant">
                {{ t('暂无价格建议') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
