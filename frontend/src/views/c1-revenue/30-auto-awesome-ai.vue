<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 未来30天收益预测（价格助手详情）：总收益趋势 + 置信度 + 影响因子 + 各房型 Occ%
// 长尾域：api.demo('yield') 渲染 30 天预测柱状图（predicted_occ 高度）
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

const yields = ref<any[]>([])
onMounted(async () => {
  yields.value = await api.demo('yield')
})
function occNum(y: any) {
  return Number(String(y.predicted_occ || '0').replace('%', ''))
}
</script>

<template>
  <div class="page">
    <div class="pt-[88px] pb-12 px-container-padding max-w-[1440px] mx-auto min-h-screen">
      <!-- 页头 -->
      <div class="mb-8 flex justify-between items-end">
        <div>
          <div class="flex items-center gap-2 text-on-surface-variant mb-2">
            <span class="font-label-lg text-label-lg">{{ t('价格助手') }}</span>
            <span class="material-symbols-outlined text-sm">chevron_right</span>
            <span class="font-label-lg text-label-lg text-primary font-medium">{{
              t('收益预测模型详情')
            }}</span>
          </div>
          <h1 class="font-display-lg text-display-lg text-on-surface flex items-center gap-3">
            {{ t('未来30天收益预测') }}
            <span
              class="inline-flex items-center gap-1 bg-tertiary-container/10 text-tertiary px-3 py-1 rounded-full text-label-lg font-label-lg border border-tertiary-container/20"
            >
              <span class="material-symbols-outlined text-sm">auto_awesome</span>
              {{ t('AI 生成') }}</span
            >
          </h1>
        </div>
        <div class="flex gap-3">
          <button
            class="px-4 py-2 border border-outline-variant text-on-surface rounded-lg font-label-lg text-label-lg hover:bg-surface-container-low transition-colors"
          >
            {{ t('导出报告') }}
          </button>
          <button
            class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg text-label-lg shadow-sm hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-sm">edit_calendar</span>
            {{ t('调整策略') }}
          </button>
        </div>
      </div>
      <!-- 网格 -->
      <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        <!-- 主图：收益预测 -->
        <div
          class="md:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-[0_4px_12px_rgba(0,0,0,0.02)] relative overflow-hidden flex flex-col"
        >
          <div class="flex justify-between items-start mb-6 z-10">
            <div>
              <h2 class="font-headline-md text-headline-md mb-1">{{ t('总收益预测趋势') }}</h2>
              <p class="font-body-md text-body-md text-on-surface-variant">
                {{ t('实际收益 vs AI 预测 (未来30天)') }}
              </p>
            </div>
            <div class="flex gap-4">
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full bg-secondary-container"></div>
                <span class="font-label-lg text-label-lg text-on-surface-variant">{{
                  t('实际收益')
                }}</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full bg-tertiary"></div>
                <span class="font-label-lg text-label-lg text-on-surface-variant">{{
                  t('AI 预测')
                }}</span>
              </div>
            </div>
          </div>
          <!-- 预测柱状图（数据驱动：demo('yield')） -->
          <div class="flex-grow flex items-end relative min-h-[300px] z-10">
            <div class="w-full h-full flex items-end gap-1 px-2">
              <div
                v-for="y in yields"
                :key="y.id"
                class="flex-1 flex flex-col items-center justify-end h-full group relative"
              >
                <div
                  class="w-full bg-tertiary rounded-t"
                  :style="{ height: occNum(y) + '%' }"
                ></div>
                <span
                  class="text-[10px] text-on-surface-variant mt-1 opacity-0 group-hover:opacity-100 absolute -top-5"
                  >{{ y.lift }}</span
                >
              </div>
              <div
                v-if="!yields.length"
                class="absolute inset-0 flex items-center justify-center text-on-surface-variant"
              >
                <span class="material-symbols-outlined text-6xl">monitoring</span>
              </div>
            </div>
            <div
              class="absolute -bottom-6 left-8 right-0 flex justify-between text-xs text-on-surface-variant font-num-md"
            >
              <span>{{ t('今日') }}}</span><span>{{ t('+7天') }}</span
              ><span>{{ t('+14天') }}</span
              ><span>{{ t('+21天') }}</span
              ><span>{{ t('+30天') }}</span>
            </div>
          </div>
        </div>
        <!-- 侧栏：置信度 + 因子 -->
        <div class="md:col-span-4 flex flex-col gap-gutter">
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex items-center gap-6"
          >
            <div class="relative w-24 h-24 flex-shrink-0">
              <svg class="w-full h-full transform -rotate-90" viewbox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  fill="transparent"
                  r="40"
                  stroke="#f2f4f5"
                  stroke-width="8"
                ></circle>
                <circle
                  cx="50"
                  cy="50"
                  fill="transparent"
                  r="40"
                  stroke="#1a73e8"
                  stroke-dasharray="251.2"
                  stroke-dashoffset="15.07"
                  stroke-linecap="round"
                  stroke-width="8"
                ></circle>
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="font-num-xl text-num-xl text-primary">94%</span>
              </div>
            </div>
            <div>
              <h3 class="font-headline-md text-headline-md mb-1">{{ t('AI 预测置信度') }}</h3>
              <p class="font-body-md text-body-md text-on-surface-variant mb-2">
                {{ t('基于历史数据与多维实时因子计算的高可靠性预测。') }}
              </p>
              <div class="flex items-center gap-1 text-primary font-label-lg text-label-lg">
                <span class="material-symbols-outlined text-sm">trending_up</span>
                {{ t('较上周提升 2%') }}
              </div>
            </div>
          </div>
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex-grow"
          >
            <h3 class="font-headline-md text-headline-md mb-4 flex items-center justify-between">
              {{ t('预测影响因子权重') }}
              <span class="material-symbols-outlined text-outline cursor-help text-sm">info</span>
            </h3>
            <div class="space-y-4">
              <div>
                <div class="flex justify-between font-label-lg text-label-lg mb-1">
                  <span class="flex items-center gap-2"
                    ><span class="material-symbols-outlined text-sm text-tertiary"
                      >local_activity</span
                    >{{ t('周边事件 (演唱会/展会)') }}</span
                  >
                  <span class="font-num-md text-num-md">45%</span>
                </div>
                <div class="w-full bg-surface-container rounded-full h-2">
                  <div class="bg-tertiary h-2 rounded-full" style="width: 45%"></div>
                </div>
              </div>
              <div>
                <div class="flex justify-between font-label-lg text-label-lg mb-1">
                  <span class="flex items-center gap-2"
                    ><span class="material-symbols-outlined text-sm text-primary">storefront</span
                    >{{ t('竞对动态定价') }}</span
                  >
                  <span class="font-num-md text-num-md">30%</span>
                </div>
                <div class="w-full bg-surface-container rounded-full h-2">
                  <div class="bg-primary h-2 rounded-full" style="width: 30%"></div>
                </div>
              </div>
              <div>
                <div class="flex justify-between font-label-lg text-label-lg mb-1">
                  <span class="flex items-center gap-2"
                    ><span class="material-symbols-outlined text-sm text-outline"
                      >calendar_month</span
                    >{{ t('历史季节性') }}</span
                  >
                  <span class="font-num-md text-num-md">15%</span>
                </div>
                <div class="w-full bg-surface-container rounded-full h-2">
                  <div class="bg-outline h-2 rounded-full" style="width: 15%"></div>
                </div>
              </div>
              <div>
                <div class="flex justify-between font-label-lg text-label-lg mb-1">
                  <span class="flex items-center gap-2"
                    ><span class="material-symbols-outlined text-sm text-outline"
                      >partly_cloudy_day</span
                    >{{ t('天气预报') }}</span
                  >
                  <span class="font-num-md text-num-md">10%</span>
                </div>
                <div class="w-full bg-surface-container rounded-full h-2">
                  <div class="bg-outline-variant h-2 rounded-full" style="width: 10%"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- 建议横幅 -->
        <div
          class="md:col-span-12 bg-[#fff8eb] border border-[#ffdb99] rounded-xl p-5 shadow-sm flex items-start gap-4"
        >
          <div
            class="w-10 h-10 rounded-full bg-[#ffeed1] flex items-center justify-center flex-shrink-0 text-[#b26b00]"
          >
            <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
              >lightbulb</span
            >
          </div>
          <div class="flex-grow">
            <h4 class="font-headline-md text-headline-md text-[#8c5400] mb-1">
              {{ t('AI 策略建议：审核推荐') }}
            </h4>
            <p class="font-body-md text-body-md text-[#593600] mb-3">
              {{
                t(
                  '预测显示下周末（11月24日-25日）因附近举办大型体育赛事，需求激增。AI 建议将豪华大床房及以上房型的基础价上调',
                )
              }}
              <strong>15%</strong>。
            </p>
            <div class="flex gap-3">
              <button
                class="px-4 py-2 bg-[#d98200] text-white rounded-lg font-label-lg text-label-lg hover:bg-[#b26b00] transition-colors"
              >
                {{ t('一键应用价格建议') }}
              </button>
              <button
                class="px-4 py-2 border border-[#d98200] text-[#8c5400] rounded-lg font-label-lg text-label-lg hover:bg-[#ffeed1] transition-colors"
              >
                {{ t('查看详细推演过程') }}
              </button>
            </div>
          </div>
        </div>
        <!-- 各房型 Occ% -->
        <div
          class="md:col-span-12 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
        >
          <div class="flex justify-between items-center mb-6">
            <h2 class="font-headline-md text-headline-md">{{ t('各房型预计入住率 (Occ%)') }}</h2>
            <select
              class="bg-surface border border-outline-variant rounded-lg px-3 py-1.5 text-label-lg font-label-lg text-on-surface focus:ring-primary focus:border-primary"
            >
              <option>{{ t('未来 7 天平均') }}</option>
              <option>{{ t('未来 14 天平均') }}</option>
              <option>{{ t('未来 30 天平均') }}</option>
            </select>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div class="flex flex-col gap-2">
              <div class="flex justify-between font-label-lg text-label-lg text-on-surface-variant">
                <span>{{ t('标准大床房') }}</span
                ><span class="font-num-md text-num-md text-primary font-bold">88%</span>
              </div>
              <div class="w-full bg-surface-container h-4 rounded-sm overflow-hidden">
                <div class="bg-primary h-full rounded-sm" style="width: 88%"></div>
              </div>
              <div class="text-xs text-outline font-num-md">{{ t('预估剩余: 5 间') }}</div>
            </div>
            <div class="flex flex-col gap-2">
              <div class="flex justify-between font-label-lg text-label-lg text-on-surface-variant">
                <span>{{ t('豪华双床房') }}</span
                ><span class="font-num-md text-num-md text-primary font-bold">75%</span>
              </div>
              <div class="w-full bg-surface-container h-4 rounded-sm overflow-hidden">
                <div class="bg-primary h-full rounded-sm" style="width: 75%"></div>
              </div>
              <div class="text-xs text-outline font-num-md">{{ t('预估剩余: 12 间') }}</div>
            </div>
            <div class="flex flex-col gap-2">
              <div class="flex justify-between font-label-lg text-label-lg text-on-surface-variant">
                <span>{{ t('行政套房') }}</span
                ><span class="font-num-md text-num-md text-tertiary font-bold">92%</span>
              </div>
              <div class="w-full bg-surface-container h-4 rounded-sm overflow-hidden relative">
                <div
                  class="absolute top-0 left-0 h-full bg-primary/20 w-[10%] z-10"
                  style="left: 82%"
                ></div>
                <div class="bg-tertiary h-full rounded-sm" style="width: 92%"></div>
              </div>
              <div class="text-xs text-outline font-num-md flex justify-between">
                <span>{{ t('预估剩余: 1 间') }}</span
                ><span class="text-tertiary flex items-center"
                  ><span class="material-symbols-outlined text-[10px] mr-0.5">trending_up</span
                  >{{ t('AI 提拉') }}</span
                >
              </div>
            </div>
            <div class="flex flex-col gap-2">
              <div class="flex justify-between font-label-lg text-label-lg text-on-surface-variant">
                <span>{{ t('亲子家庭房') }}}</span
                ><span class="font-num-md text-num-md text-on-surface font-bold">45%</span>
              </div>
              <div class="w-full bg-surface-container h-4 rounded-sm overflow-hidden">
                <div class="bg-secondary-fixed-dim h-full rounded-sm" style="width: 45%"></div>
              </div>
              <div class="text-xs text-outline font-num-md">{{ t('预估剩余: 8 间') }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
