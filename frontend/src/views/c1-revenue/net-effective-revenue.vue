<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 渠道成本与协议价 / 净有效收益（收益管理 C1）：分销渠道净收益表 + 价格护栏
// 数据：api.listChannels 取渠道名与佣金率，计算净收；基础价来自 demo('rate')
import { ref, onMounted, computed } from 'vue'
import { api } from '../../lib/api'

const channels = ref<any[]>([])
const basePrice = ref(500)
onMounted(async () => {
  channels.value = await api.listChannels()
  const rate = await api.demo('rate')
  if (rate && rate.length) basePrice.value = Number(rate[0].current_price) || 500
})
const fee = 12
function net(c: any) {
  const comm = Number(c.commission_rate || 0)
  return Math.round(basePrice.value * (1 - comm) - fee)
}
</script>

<template>
  <div class="page">
    <div
      class="p-container-padding max-w-max-content-width mx-auto w-full flex-1 flex flex-col gap-6"
    >
      <div class="flex justify-between items-end mb-2">
        <div>
          <h2 class="font-display-lg text-display-lg text-on-surface mb-1">
            {{ t('渠道成本与协议价') }}
          </h2>
          <p class="font-body-md text-body-md text-on-surface-variant">
            {{ t('管理分销渠道盈利能力与企业协议价净有效营收。') }}
          </p>
        </div>
        <div class="flex gap-3">
          <button
            class="px-4 py-2 border border-outline rounded-lg text-primary font-label-lg hover:bg-surface-container transition-colors flex items-center gap-2"
          >
            {{ t('导出报表') }}
          </button>
          <button
            class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg shadow-sm hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            {{ t('新增协议价') }}
          </button>
        </div>
      </div>

      <div class="grid grid-cols-12 gap-gutter">
        <!-- 分销渠道净收益（v-for 绑定 listChannels） -->
        <div
          class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col"
        >
          <div
            class="p-5 border-b border-outline-variant flex justify-between items-center bg-surface-bright"
          >
            <h3 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('分销渠道净收益') }}
            </h3>
            <span
              class="text-xs font-label-lg bg-surface-container-high px-2 py-1 rounded text-on-surface-variant"
              >{{ t('基于当前基础价:') }} ¥{{ basePrice }}</span
            >
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr
                  class="border-b border-surface-container-highest bg-surface/50 text-on-surface-variant font-label-lg"
                >
                  <th class="p-4 font-medium">{{ t('渠道名称') }}</th>
                  <th class="p-4 font-medium text-right">{{ t('基础售价') }}</th>
                  <th class="p-4 font-medium text-right">{{ t('佣金率') }}</th>
                  <th class="p-4 font-medium text-right">{{ t('税费/杂费') }}</th>
                  <th class="p-4 font-medium text-right">{{ t('净收') }}</th>
                  <th class="p-4 font-medium text-center">{{ t('盈利状态') }}</th>
                  <th class="p-4 font-medium text-center">{{ t('操作') }}</th>
                </tr>
              </thead>
              <tbody class="font-body-md divide-y divide-surface-container-highest">
                <tr
                  v-for="c in channels"
                  :key="c.id"
                  class="hover:bg-surface-container-lowest/50 transition-colors"
                >
                  <td class="p-4 flex items-center gap-3">
                    <div
                      class="w-8 h-8 rounded bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs"
                    >
                      {{ (c.name || t('渠')).charAt(0) }}
                    </div>
                    <span class="font-medium text-on-surface">{{ c.name || t('渠道') }}</span>
                  </td>
                  <td class="p-4 text-right font-num-md text-on-surface-variant">
                    ¥{{ basePrice }}.00
                  </td>
                  <td class="p-4 text-right font-num-md text-on-surface-variant">
                    {{ ((c.commission_rate || 0) * 100).toFixed(0) }}%
                  </td>
                  <td class="p-4 text-right font-num-md text-on-surface-variant">¥{{ fee }}.00</td>
                  <td class="p-4 text-right font-num-md font-bold text-on-surface">
                    ¥{{ net(c) }}.00
                  </td>
                  <td class="p-4 text-center">
                    <span
                      class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 text-green-800 text-xs font-medium"
                      ><span class="w-1.5 h-1.5 rounded-full bg-green-600"></span
                      >{{ t('良好') }}</span
                    >
                  </td>
                  <td class="p-4 text-center">
                    <button
                      class="text-primary hover:bg-primary-container/10 p-1 rounded transition-colors"
                    >
                      <span class="material-symbols-outlined text-sm">more_vert</span>
                    </button>
                  </td>
                </tr>
                <tr class="hover:bg-surface-container-lowest/50 transition-colors">
                  <td class="p-4 flex items-center gap-3">
                    <div
                      class="w-8 h-8 rounded bg-primary-container text-on-primary-container flex items-center justify-center font-bold text-xs"
                    >
                      {{ t('自') }}
                    </div>
                    <span class="font-medium text-on-surface">{{ t('自有渠道 (小程序)') }}</span>
                  </td>
                  <td class="p-4 text-right font-num-md text-on-surface-variant">
                    ¥{{ basePrice }}.00
                  </td>
                  <td class="p-4 text-right font-num-md text-on-surface-variant">0%</td>
                  <td class="p-4 text-right font-num-md text-on-surface-variant">¥0.00</td>
                  <td class="p-4 text-right font-num-md font-bold text-on-surface">
                    ¥{{ basePrice }}.00
                  </td>
                  <td class="p-4 text-center">
                    <span
                      class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 text-green-800 text-xs font-medium"
                      ><span class="w-1.5 h-1.5 rounded-full bg-green-600"></span
                      >{{ t('最优') }}</span
                    >
                  </td>
                  <td class="p-4 text-center">
                    <button
                      class="text-primary hover:bg-primary-container/10 p-1 rounded transition-colors"
                    >
                      <span class="material-symbols-outlined text-sm">more_vert</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 价格护栏 -->
        <div class="col-span-12 lg:col-span-4 flex flex-col gap-4">
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-5 relative overflow-hidden group"
          >
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary"></div>
            <div class="flex justify-between items-start mb-4">
              <h3 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
                {{ t('价格护栏') }}
              </h3>
              <button class="text-primary hover:bg-surface-container p-1 rounded-full">
                <span class="material-symbols-outlined text-sm">settings</span>
              </button>
            </div>
            <p class="text-sm text-on-surface-variant mb-4">
              {{ t('AI 自动调价的边界控制，防止异常低价损失利润。') }}
            </p>
            <div class="space-y-4">
              <div class="bg-surface p-3 rounded-lg border border-outline-variant/50">
                <div class="flex justify-between items-center mb-1">
                  <span class="font-label-lg text-on-surface">{{ t('绝对底价') }}</span
                  ><span class="font-num-md text-on-surface font-bold">¥280.00</span>
                </div>
                <div class="w-full bg-surface-container-highest rounded-full h-1.5 mt-2">
                  <div class="bg-error h-1.5 rounded-full w-[30%]"></div>
                </div>
                <p class="text-xs text-on-surface-variant mt-2">
                  {{ t('系统任何情况下均不可低于此价格') }}
                </p>
              </div>
              <div class="bg-surface p-3 rounded-lg border border-outline-variant/50">
                <div class="flex justify-between items-center mb-1">
                  <span class="font-label-lg text-on-surface">{{ t('目标净收') }}</span
                  ><span class="font-num-md text-on-surface font-bold">¥350.00</span>
                </div>
                <div class="w-full bg-surface-container-highest rounded-full h-1.5 mt-2">
                  <div class="bg-primary h-1.5 rounded-full w-[60%]"></div>
                </div>
                <p class="text-xs text-on-surface-variant mt-2">
                  {{ t('扣除佣金后的期望最低收益') }}
                </p>
              </div>
            </div>
            <div
              class="mt-4 bg-primary-fixed/30 border border-primary/20 p-3 rounded-lg flex gap-3 items-start"
            >
              <div class="text-xs text-on-primary-fixed">
                <strong>{{ t('AI 提示:') }}</strong
                >{{ t('检测到周末预订热度上升，建议将目标净收上调 10% 以匹配市场需求。') }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
