<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 全渠道库存与收益预测：实时渠道分配矩阵 + 收益预测 + 超售风险
// 核心域：api.listChannels 渲染渠道列；api.demo('yield') 渲染逐日预测
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

const channels = ref<any[]>([])
const yields = ref<any[]>([])
onMounted(async () => {
  channels.value = await api.listChannels()
  yields.value = await api.demo('yield')
})
// 渠道短名（取前 4 个）
function shortName(c: any, i: number) {
  const map = ['Ctrip', 'Meituan', 'Direct', 'Social']
  return map[i] || c.name || '渠道'
}
function cnName(c: any, i: number) {
  const map = ['携程', '美团', '官网直客', '小红书']
  return map[i] || c.name || '渠道'
}
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto flex flex-col gap-6">
      <!-- 顶部控制条 -->
      <div
        class="glass-panel rounded-xl p-4 flex flex-col md:flex-row justify-between items-center gap-4"
      >
        <div class="flex items-center gap-3">
          <div
            class="h-10 w-10 rounded-full bg-primary-container flex items-center justify-center text-on-primary-container"
          >
            <span class="material-symbols-outlined">hub</span>
          </div>
          <div>
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('全渠道库存概览') }}
            </h2>
            <p class="font-body-md text-body-md text-on-surface-variant">Today, Oct 24 - Oct 25</p>
          </div>
        </div>
        <div
          class="flex items-center gap-4 bg-surface-container-low rounded-lg p-2 border border-outline-variant"
        >
          <span class="font-label-lg text-label-lg text-on-surface font-semibold">{{
            t('AI Auto-Rebalance (AI 自动均衡)')
          }}</span>
          <label class="relative inline-flex items-center cursor-pointer">
            <input checked class="sr-only peer" type="checkbox" value="" />
            <div
              class="w-11 h-6 bg-outline-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"
            ></div>
          </label>
          <span class="material-symbols-outlined text-tertiary" title="Active"
            >arrow_back_ios_new</span
          >
        </div>
      </div>
      <!-- Bento 布局 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- 左列：渠道矩阵 -->
        <div class="lg:col-span-2 flex flex-col gap-6">
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col h-full"
          >
            <div
              class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-bright"
            >
              <h3 class="font-headline-md text-headline-md text-on-surface">
                {{ t('实时渠道分配矩阵') }}
              </h3>
              <button
                class="text-primary font-label-lg text-label-lg hover:underline flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-sm">tune</span> Adjust
              </button>
            </div>
            <div class="p-4 overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr
                    class="text-on-surface-variant font-label-lg text-label-lg border-b border-surface-variant"
                  >
                    <th class="py-3 px-2 font-medium">Room Type</th>
                    <th class="py-3 px-2 font-medium">Total Avail</th>
                    <th
                      v-for="(c, i) in channels.slice(0, 4)"
                      :key="c.id"
                      class="py-3 px-2 font-medium text-center"
                    >
                      {{ shortName(c, i) }} ({{ cnName(c, i) }})
                    </th>
                  </tr>
                </thead>
                <tbody class="font-body-md text-body-md">
                  <tr
                    class="border-b border-surface-variant hover:bg-surface-container-low transition-colors"
                  >
                    <td class="py-3 px-2 font-semibold">{{ t('Deluxe King (豪华大床)') }}</td>
                    <td class="py-3 px-2 font-num-md text-num-md">12</td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-surface-container px-2 py-1 rounded"
                      >
                        <span class="font-num-md">4</span>
                      </div>
                    </td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-surface-container px-2 py-1 rounded"
                      >
                        <span class="font-num-md">3</span>
                      </div>
                    </td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-primary-container text-on-primary-container px-2 py-1 rounded border border-primary"
                      >
                        <span class="font-num-md">3</span
                        ><span
                          class="material-symbols-outlined text-[14px] text-tertiary"
                          title="AI Increased"
                          >trending_up</span
                        >
                      </div>
                    </td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-surface-container px-2 py-1 rounded"
                      >
                        <span class="font-num-md">2</span>
                      </div>
                    </td>
                  </tr>
                  <tr
                    class="border-b border-surface-variant hover:bg-surface-container-low transition-colors"
                  >
                    <td class="py-3 px-2 font-semibold">{{ t('Standard Twin (标准双床)') }}</td>
                    <td class="py-3 px-2 font-num-md text-num-md">8</td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-surface-container px-2 py-1 rounded"
                      >
                        <span class="font-num-md">5</span>
                      </div>
                    </td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-surface-container px-2 py-1 rounded"
                      >
                        <span class="font-num-md">2</span>
                      </div>
                    </td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-error-container text-on-error-container px-2 py-1 rounded"
                      >
                        <span class="font-num-md">1</span
                        ><span class="material-symbols-outlined text-[14px]" title="Low Demand"
                          >trending_down</span
                        >
                      </div>
                    </td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-surface-container px-2 py-1 rounded"
                      >
                        <span class="font-num-md">0</span>
                      </div>
                    </td>
                  </tr>
                  <tr class="hover:bg-surface-container-low transition-colors">
                    <td class="py-3 px-2 font-semibold">{{ t('Executive Suite (行政套房)') }}</td>
                    <td class="py-3 px-2 font-num-md text-num-md">3</td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-surface-container px-2 py-1 rounded"
                      >
                        <span class="font-num-md">1</span>
                      </div>
                    </td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-surface-container px-2 py-1 rounded"
                      >
                        <span class="font-num-md">0</span>
                      </div>
                    </td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-surface-container px-2 py-1 rounded"
                      >
                        <span class="font-num-md">2</span>
                      </div>
                    </td>
                    <td class="py-3 px-2 text-center">
                      <div
                        class="inline-flex items-center gap-1 bg-surface-container px-2 py-1 rounded"
                      >
                        <span class="font-num-md">0</span>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div
              class="p-3 bg-surface-container-low mt-auto border-t border-outline-variant text-sm text-on-surface-variant flex items-center gap-2"
            >
              <span class="material-symbols-outlined text-tertiary text-sm">info</span>
              <span
                >AI shifted 2 Deluxe Kings from Meituan to Direct Web due to surging local search
                traffic.</span
              >
            </div>
          </div>
        </div>
        <!-- 右列：收益与风险 -->
        <div class="flex flex-col gap-6">
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-4 relative overflow-hidden"
          >
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary"></div>
            <h3
              class="font-headline-md text-headline-md text-on-surface mb-2 flex items-center gap-2"
            >
              <span class="material-symbols-outlined text-tertiary">monitoring</span>
              {{ t('收益预测 (Yield Prediction)') }}
            </h3>
            <div class="mt-4 flex flex-col gap-4">
              <div>
                <p class="font-label-lg text-label-lg text-on-surface-variant">
                  Current Strategy Est.
                </p>
                <div class="font-num-xl text-num-xl text-primary mt-1">¥ 18,450</div>
              </div>
              <!-- 逐日预测（数据驱动：demo('yield')） -->
              <div class="bg-surface-container p-3 rounded-lg border border-surface-variant">
                <p class="font-label-lg text-label-lg text-on-surface-variant mb-2">
                  {{ t('逐日预测 (Predicted Occ)') }}
                </p>
                <div
                  v-for="y in yields.slice(0, 3)"
                  :key="y.id"
                  class="flex justify-between items-center mb-1 text-sm"
                >
                  <span>{{ y.date }}</span>
                  <span class="font-num-md text-tertiary">{{ y.predicted_occ }}</span>
                </div>
                <div v-if="!yields.length" class="text-sm text-on-surface-variant">
                  {{ t('加载中…') }}
                </div>
              </div>
            </div>
          </div>
          <div class="bg-[#fff9e6] rounded-xl border border-[#ffeb99] shadow-sm p-4">
            <h3
              class="font-headline-md text-headline-md text-[#997300] mb-2 flex items-center gap-2"
            >
              <span class="material-symbols-outlined">warning</span>
              {{ t('超售风险 (Overbooking Risk)') }}
            </h3>
            <p class="font-body-md text-body-md text-on-surface-variant mb-4">
              Moderate risk detected on Standard Twins across OTA channels.
            </p>
            <div class="flex items-center justify-between bg-white/60 p-3 rounded-lg mb-3">
              <span class="font-label-lg text-label-lg">Auto Safety Stop</span>
              <label class="relative inline-flex items-center cursor-pointer">
                <input checked class="sr-only peer" type="checkbox" value="" />
                <div
                  class="w-9 h-5 bg-outline-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"
                ></div>
              </label>
            </div>
            <div class="text-sm text-on-surface-variant flex gap-2">
              <span class="material-symbols-outlined text-sm">shield</span>
              System will halt OTA sales when global inventory hits 1.
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
