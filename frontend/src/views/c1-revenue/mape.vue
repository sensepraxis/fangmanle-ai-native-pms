<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 历史预测偏差与复盘：MAPE + 显著偏差复盘 + 模型进化 + 关键房型复盘
// 长尾域：api.demo('rate') 渲染关键房型复盘表（建议价/当前价/准确度派生）
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import { fmt } from '../../lib/ui'

const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('rate')
})
// 预测准确度：以 |建议-当前|/当前 反推估算值
function accuracy(r: any) {
  const cur = Number(r.current_price || 0)
  const sug = Number(r.suggested_price || 0)
  if (!cur) return 90
  const diff = Math.abs(cur - sug) / cur
  return Math.max(80, Math.round((1 - diff) * 100))
}
</script>

<template>
  <div class="page">
    <!-- 页头与成就徽章 -->
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-4">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface">
          {{ t('历史预测偏差与复盘') }}
        </h1>
        <p class="font-body-md text-on-surface-variant mt-1">
          {{ t('评估 AI 定价模型的准确性及学习轨迹') }}
        </p>
      </div>
      <div
        class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 flex items-center gap-4 ai-glow relative overflow-hidden"
      >
        <div
          class="absolute right-0 top-0 w-32 h-32 bg-primary opacity-5 rounded-full blur-2xl transform translate-x-1/2 -translate-y-1/2 pointer-events-none"
        ></div>
        <div
          class="w-12 h-12 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center shrink-0"
        >
          <span class="material-symbols-outlined text-3xl">savings</span>
        </div>
        <div>
          <div class="font-label-lg text-on-surface-variant">
            {{ t('本月通过防止低价出售，AI 为您挽回收益') }}
          </div>
          <div class="font-num-xl text-num-xl text-primary mt-1">¥12,000</div>
        </div>
      </div>
    </div>
    <!-- 主网格 -->
    <div class="grid grid-cols-12 gap-gutter">
      <!-- 回测图 (Col 8) -->
      <div
        class="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col shadow-sm"
      >
        <div class="flex justify-between items-center mb-6">
          <h2 class="font-headline-md text-headline-md text-on-surface">
            {{ t('预测与实际成交对比 (近30天)') }}
          </h2>
          <div class="flex gap-4">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-tertiary"></div>
              <span class="font-label-lg text-on-surface-variant">{{ t('AI 预测均价') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-primary"></div>
              <span class="font-label-lg text-on-surface-variant">{{ t('实际成交均价') }}</span>
            </div>
          </div>
        </div>
        <div
          class="flex-grow min-h-[300px] relative flex items-end justify-between pt-10 border-b border-l border-outline-variant pb-2 pl-2"
        >
          <div
            class="absolute left-[-40px] top-0 bottom-0 flex flex-col justify-between text-xs text-on-surface-variant font-num-md py-2"
          >
            <span>¥600</span><span>¥500</span><span>¥400</span><span>¥300</span><span>¥200</span>
          </div>
          <div class="w-[8%] flex gap-1 items-end h-full group relative">
            <div
              class="w-full bg-tertiary/80 rounded-t h-[60%] group-hover:bg-tertiary transition-colors"
            ></div>
            <div
              class="w-full bg-primary/80 rounded-t h-[58%] group-hover:bg-primary transition-colors"
            ></div>
          </div>
          <div class="w-[8%] flex gap-1 items-end h-full group relative">
            <div
              class="w-full bg-tertiary/80 rounded-t h-[65%] group-hover:bg-tertiary transition-colors"
            ></div>
            <div
              class="w-full bg-primary/80 rounded-t h-[62%] group-hover:bg-primary transition-colors"
            ></div>
          </div>
          <div class="w-[8%] flex gap-1 items-end h-full group relative">
            <div
              class="w-full bg-tertiary/80 rounded-t h-[80%] group-hover:bg-tertiary transition-colors"
            ></div>
            <div
              class="w-full bg-primary/80 rounded-t h-[75%] group-hover:bg-primary transition-colors"
            ></div>
            <div
              class="absolute top-[-30px] left-1/2 transform -translate-x-1/2 bg-error-container text-on-error-container text-xs px-2 py-1 rounded shadow-sm whitespace-nowrap"
            >
              {{ t('偏差较大') }}
            </div>
          </div>
          <div class="w-[8%] flex gap-1 items-end h-full group relative">
            <div
              class="w-full bg-tertiary/80 rounded-t h-[50%] group-hover:bg-tertiary transition-colors"
            ></div>
            <div
              class="w-full bg-primary/80 rounded-t h-[55%] group-hover:bg-primary transition-colors"
            ></div>
          </div>
          <div class="w-[8%] flex gap-1 items-end h-full group relative">
            <div
              class="w-full bg-tertiary/80 rounded-t h-[70%] group-hover:bg-tertiary transition-colors"
            ></div>
            <div
              class="w-full bg-primary/80 rounded-t h-[72%] group-hover:bg-primary transition-colors"
            ></div>
          </div>
          <div class="w-[8%] flex gap-1 items-end h-full group relative">
            <div
              class="w-full bg-tertiary/80 rounded-t h-[90%] group-hover:bg-tertiary transition-colors"
            ></div>
            <div
              class="w-full bg-primary/80 rounded-t h-[88%] group-hover:bg-primary transition-colors"
            ></div>
          </div>
          <div
            class="absolute bottom-[-24px] left-0 right-0 flex justify-between text-xs text-on-surface-variant font-num-md pl-2"
          >
            <span class="w-[8%] text-center">10/01</span
            ><span class="w-[8%] text-center">10/06</span
            ><span class="w-[8%] text-center">10/12</span
            ><span class="w-[8%] text-center">10/18</span
            ><span class="w-[8%] text-center">10/24</span
            ><span class="w-[8%] text-center">10/30</span>
          </div>
        </div>
      </div>
      <!-- 误差分析 (Col 4) -->
      <div class="col-span-12 lg:col-span-4 flex flex-col gap-gutter">
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col justify-center"
        >
          <h3 class="font-headline-md text-headline-md text-on-surface mb-2">
            {{ t('平均绝对百分比误差 (MAPE)') }}
          </h3>
          <div class="flex items-baseline gap-2">
            <span class="font-display-lg text-display-lg font-bold text-primary">4.2%</span>
            <span class="font-label-lg text-error flex items-center"
              ><span class="material-symbols-outlined text-sm">arrow_downward</span>
              {{ t('0.8% (较上月)') }}</span
            >
          </div>
          <p class="font-body-md text-on-surface-variant mt-2">
            {{ t('模型预测精度极高，误差保持在5%的行业优秀线以内。') }}
          </p>
        </div>
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex-grow"
        >
          <h3
            class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-error">warning</span>
            {{ t('近期显著偏差复盘') }}
          </h3>
          <ul class="flex flex-col gap-4">
            <li
              class="flex gap-3 items-start pb-4 border-b border-outline-variant/50 last:border-0"
            >
              <div
                class="w-8 h-8 rounded-full bg-error-container text-on-error-container flex items-center justify-center shrink-0 mt-1"
              >
                <span class="material-symbols-outlined text-sm">rainy</span>
              </div>
              <div>
                <div class="font-label-lg text-on-surface">{{ t('10月12日 (高估需求)') }}</div>
                <div class="font-body-md text-on-surface-variant text-sm mt-1">
                  {{
                    t(
                      '突发特大暴雨，导致预期内的 Walk-in 客源急剧减少，AI 未能提前获取极端天气预警。',
                    )
                  }}
                </div>
              </div>
            </li>
            <li class="flex gap-3 items-start">
              <div
                class="w-8 h-8 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center shrink-0 mt-1"
              >
                <span class="material-symbols-outlined text-sm">festival</span>
              </div>
              <div>
                <div class="font-label-lg text-on-surface">{{ t('9月28日 (低估需求)') }}</div>
                <div class="font-body-md text-on-surface-variant text-sm mt-1">
                  {{ t('周边场馆临时新增一场未在公共日历上的演唱会，导致实际需求激增。') }}
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>
      <!-- 模型进化轨迹 (Col 6) -->
      <div
        class="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
      >
        <h3 class="font-headline-md text-headline-md text-on-surface mb-6 flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">model_training</span>
          {{ t('AI 模型进化轨迹') }}
        </h3>
        <div class="relative border-l-2 border-outline-variant ml-4 pl-6 pb-2">
          <div class="mb-8 relative">
            <div
              class="absolute w-4 h-4 rounded-full bg-primary border-4 border-surface-container-lowest left-[-31px] top-1"
            ></div>
            <div class="font-num-md text-primary mb-1">{{ t('2023年11月1日 (v2.4)') }}</div>
            <div class="font-headline-md text-base text-on-surface">
              {{ t('整合全新地理交通因子') }}
            </div>
            <p class="font-body-md text-sm text-on-surface-variant mt-1">
              {{ t('引入高铁站及机场实时拥堵数据，优化对商旅客人延迟到达的预测准确率。') }}
            </p>
          </div>
          <div class="mb-8 relative">
            <div
              class="absolute w-4 h-4 rounded-full bg-outline-variant border-4 border-surface-container-lowest left-[-31px] top-1"
            ></div>
            <div class="font-num-md text-on-surface-variant mb-1">
              {{ t('2023年10月15日 (v2.3.5)') }}
            </div>
            <div class="font-headline-md text-base text-on-surface">
              {{ t('长假节后需求衰减算法修正') }}
            </div>
            <p class="font-body-md text-sm text-on-surface-variant mt-1">
              {{ t('针对十一黄金周后迅速回落的需求曲线进行平滑处理，减少节后首周的过度降价。') }}
            </p>
          </div>
          <div class="relative">
            <div
              class="absolute w-4 h-4 rounded-full bg-outline-variant border-4 border-surface-container-lowest left-[-31px] top-1"
            ></div>
            <div class="font-num-md text-on-surface-variant mb-1">
              {{ t('2023年9月10日 (v2.3)') }}
            </div>
            <div class="font-headline-md text-base text-on-surface">
              {{ t('引入竞对动态感知模块') }}
            </div>
            <p class="font-body-md text-sm text-on-surface-variant mt-1">
              {{ t('增加对周边3公里内同级竞品满房状态的实时监控，动态上调基准价。') }}
            </p>
          </div>
        </div>
      </div>
      <!-- 关键房型复盘 (Col 6) -->
      <div
        class="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-0 shadow-sm overflow-hidden flex flex-col"
      >
        <div class="p-6 border-b border-outline-variant flex justify-between items-center">
          <h3 class="font-headline-md text-headline-md text-on-surface">
            {{ t('关键房型复盘概览') }}
          </h3>
          <button class="text-primary font-label-lg hover:underline">
            {{ t('查看完整报告') }}
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr
                class="bg-surface text-on-surface-variant font-label-lg border-b border-outline-variant"
              >
                <th class="p-4 font-medium">{{ t('房型') }}</th>
                <th class="p-4 font-medium">{{ t('预测均价') }}</th>
                <th class="p-4 font-medium">{{ t('实际均价') }}</th>
                <th class="p-4 font-medium">{{ t('预测准确度') }}</th>
              </tr>
            </thead>
            <tbody class="font-body-md text-on-surface divide-y divide-outline-variant/50">
              <tr
                v-for="r in rows"
                :key="r.id"
                class="hover:bg-surface-container-lowest transition-colors"
              >
                <td class="p-4 flex items-center gap-2">
                  <span class="material-symbols-outlined text-outline">bed</span>{{ r.room_type }}
                </td>
                <td class="p-4 font-num-md">{{ fmt(r.suggested_price) }}</td>
                <td class="p-4 font-num-md">{{ fmt(r.current_price) }}</td>
                <td class="p-4">
                  <div class="flex items-center gap-2">
                    <div class="w-16 h-2 bg-surface-container-high rounded-full overflow-hidden">
                      <div class="bg-primary h-full" :style="{ width: accuracy(r) + '%' }"></div>
                    </div>
                    <span class="text-sm">{{ accuracy(r) }}%</span>
                  </div>
                </td>
              </tr>
              <tr v-if="!rows.length">
                <td colspan="4" class="p-4 text-center text-on-surface-variant">
                  {{ t('加载中…') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
