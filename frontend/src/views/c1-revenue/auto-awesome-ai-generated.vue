<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 价格推导详情 (AI Generated)：推导时间线 + 渠道净价对比 + AI 决策摘要
// 核心域：api.listChannels 渲染渠道净价对比（建议售价 - 佣金 = 预估净价）
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import { fmt } from '../../lib/ui'

const channels = ref<any[]>([])
const basePrice = ref(318)
onMounted(async () => {
  channels.value = await api.listChannels()
})
// 建议售价（直销为基准，OTA 上浮）
function listPrice(c: any) {
  return c.code === 'direct'
    ? basePrice.value
    : Math.round(basePrice.value * (c.code === 'ota' ? 1.02 : 1.01))
}
// 预估净价 = 建议售价 × (1 - 佣金)
function net(c: any) {
  return Math.round(listPrice(c) * (1 - Number(c.commission_rate || 0)))
}
function subsidy(c: any) {
  return Math.round(listPrice(c) * Number(c.commission_rate || 0))
}
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto">
      <!-- 页头 -->
      <div class="mb-8 flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2 mb-2">
            <button
              class="text-on-surface-variant hover:text-primary transition-colors flex items-center"
            >
              <span class="material-symbols-outlined text-sm mr-1">arrow_back</span>
              <span class="font-label-lg text-label-lg">Back to Price Assistant</span>
            </button>
          </div>
          <h1 class="font-display-lg text-display-lg text-on-background flex items-center gap-3">
            {{ t('价格推导详情') }}
            <span
              class="bg-tertiary/10 text-tertiary text-sm px-2 py-1 rounded-md font-label-lg flex items-center gap-1 border border-tertiary/20"
            >
              <span
                class="material-symbols-outlined text-sm"
                style="font-variation-settings: 'FILL' 1"
                >auto_awesome</span
              >
              AI Generated
            </span>
          </h1>
          <p class="text-on-surface-variant mt-1">Oct 24, 2023 · Deluxe King Room (201)</p>
        </div>
        <div
          class="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant shadow-sm flex flex-col items-end min-w-[280px]"
        >
          <span class="text-on-surface-variant font-label-lg text-label-lg mb-1">{{
            t('建议优化价')
          }}</span>
          <div class="flex items-baseline gap-1 mb-4 text-primary">
            <span class="text-xl font-bold">¥</span
            ><span class="font-num-xl text-display-lg font-bold">{{ basePrice }}</span>
          </div>
          <button
            class="w-full bg-primary text-on-primary py-2.5 px-4 rounded-lg font-label-lg text-label-lg hover:bg-on-primary-fixed-variant transition-colors flex items-center justify-center gap-2 shadow-sm"
          >
            <span class="material-symbols-outlined text-sm">sync</span>
            {{ t('采纳并写回 PMS') }}
          </button>
        </div>
      </div>
      <!-- Bento 布局 -->
      <div class="grid grid-cols-12 gap-gutter relative">
        <!-- 推导时间线 -->
        <div
          class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6"
        >
          <h2
            class="font-headline-md text-headline-md text-on-background mb-6 flex items-center gap-2 border-b border-outline-variant pb-4"
          >
            <span class="material-symbols-outlined text-primary">timeline</span>
            {{ t('推导时间线') }}
          </h2>
          <div class="relative pl-2">
            <div class="relative pb-8">
              <div class="stepper-line"></div>
              <div class="flex gap-4 relative z-10">
                <div class="step-node bg-primary text-on-primary mt-1 shadow-sm">
                  <span class="material-symbols-outlined text-[14px]">database</span>
                </div>
                <div class="flex-1">
                  <h3 class="font-headline-md text-base text-on-background font-semibold">
                    {{ t('1. 数据输入 (Data Inputs)') }}
                  </h3>
                  <p class="text-sm text-on-surface-variant mb-3 mt-1">
                    {{ t('综合内外部因子进行初步基线评估。') }}
                  </p>
                  <div class="grid grid-cols-2 gap-3">
                    <div
                      class="bg-surface-container-low p-3 rounded-lg border border-outline-variant/50"
                    >
                      <span class="text-xs text-on-surface-variant block mb-1">{{
                        t('内部数据 (Internal)')
                      }}</span>
                      <div class="flex items-center gap-2">
                        <span class="font-num-md text-num-md font-medium"
                          >{{ t('入住率 68%') }}}</span
                        ><span
                          class="material-symbols-outlined text-success text-[16px] text-green-600"
                          >trending_up</span
                        >
                      </div>
                    </div>
                    <div class="ai-tinge-bg p-3 rounded-lg border border-tertiary/20">
                      <span
                        class="text-xs text-tertiary block mb-1 font-medium flex items-center gap-1"
                        ><span class="material-symbols-outlined text-[12px]">public</span
                        >{{ t('外部因子 (External)') }}</span
                      >
                      <div class="flex justify-between items-center">
                        <span class="font-label-lg text-sm">{{ t('本地音乐节') }}}</span
                        ><span class="text-tertiary font-bold font-num-md">{{
                          t('+12% 权重')
                        }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="relative pb-8">
              <div class="stepper-line"></div>
              <div class="flex gap-4 relative z-10">
                <div class="step-node bg-primary text-on-primary mt-1 shadow-sm">
                  <span class="material-symbols-outlined text-[14px]">insights</span>
                </div>
                <div class="flex-1">
                  <h3 class="font-headline-md text-base text-on-background font-semibold">
                    {{ t('2. 需求预测 (Demand Forecasting)') }}
                  </h3>
                  <p class="text-sm text-on-surface-variant mb-3 mt-1">
                    {{ t('基于当前数据预估未来需求曲线。') }}
                  </p>
                  <div
                    class="bg-surface-bright border border-outline-variant rounded-lg p-4 h-32 flex items-center justify-center text-on-surface-variant relative overflow-hidden group"
                  >
                    <div
                      class="absolute inset-0 opacity-20 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-tertiary to-transparent"
                    ></div>
                    <span class="relative z-10 text-sm flex items-center gap-2"
                      ><span class="material-symbols-outlined">monitoring</span>
                      {{ t('[预测曲线图占位 - 显示因子的需求抬升]') }}</span
                    >
                  </div>
                </div>
              </div>
            </div>
            <div class="relative pb-8">
              <div class="stepper-line bg-tertiary/30"></div>
              <div class="flex gap-4 relative z-10">
                <div class="step-node bg-tertiary text-on-tertiary mt-1 shadow-md">
                  <span
                    class="material-symbols-outlined text-[14px]"
                    style="font-variation-settings: 'FILL' 1"
                    >auto_awesome</span
                  >
                </div>
                <div
                  class="flex-1 ai-tinge p-4 rounded-r-lg rounded-bl-lg bg-surface-container-lowest"
                >
                  <h3
                    class="font-headline-md text-base text-tertiary font-semibold flex items-center gap-2"
                  >
                    {{ t('3. 价格弹性估计 (Price Elasticity)') }}
                  </h3>
                  <p class="text-sm text-on-surface-variant mb-3 mt-1">
                    {{ t('AI 测算提价对需求的抑制作用。') }}
                  </p>
                  <div
                    class="bg-surface-bright border border-tertiary/20 rounded-lg p-4 h-32 flex flex-col items-center justify-center text-on-surface-variant"
                  >
                    <span class="text-sm flex items-center gap-2 mb-2"
                      ><span class="material-symbols-outlined text-tertiary">query_stats</span>
                      {{ t('[弹性曲线图占位]') }}</span
                    >
                    <div class="text-xs text-center text-on-surface-variant/80">
                      {{ t('提价 ¥30 预计损失 2% 转化率，整体收益仍为正。') }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="relative pb-8">
              <div class="stepper-line"></div>
              <div class="flex gap-4 relative z-10">
                <div class="step-node bg-primary text-on-primary mt-1 shadow-sm">
                  <span class="material-symbols-outlined text-[14px]">track_changes</span>
                </div>
                <div class="flex-1">
                  <h3 class="font-headline-md text-base text-on-background font-semibold">
                    {{ t('4. 优化目标 (Optimization Goal)') }}
                  </h3>
                  <p class="text-sm text-on-surface-variant mb-3 mt-1">
                    {{ t('RevPAR (每间可售房收入) 最大化方案对比。') }}
                  </p>
                  <!-- 渠道净价对比（数据驱动：listChannels） -->
                  <div
                    class="bg-surface-container-low border border-outline-variant rounded-lg p-0 overflow-hidden"
                  >
                    <table class="w-full text-left text-sm">
                      <thead class="bg-surface-variant/50 border-b border-outline-variant">
                        <tr>
                          <th class="py-2 px-4 font-medium text-on-surface-variant">
                            {{ t('渠道 (Channel)') }}
                          </th>
                          <th class="py-2 px-4 font-medium text-on-surface-variant">
                            {{ t('P_guest (挂牌价)') }}
                          </th>
                          <th class="py-2 px-4 font-medium text-on-surface-variant">
                            {{ t('平台补贴') }}
                          </th>
                          <th class="py-2 px-4 font-medium text-on-surface-variant">
                            {{ t('N (预估净价)') }}
                          </th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-outline-variant/50">
                        <tr v-for="c in channels" :key="c.id">
                          <td class="py-2 px-4 text-on-surface flex items-center gap-2">
                            <span class="w-2 h-2 rounded-full bg-[#FFC300]"></span> {{ c.name }}
                          </td>
                          <td class="py-2 px-4 font-num-md">{{ fmt(listPrice(c)) }}</td>
                          <td class="py-2 px-4 font-num-md text-tertiary">
                            -{{ fmt(subsidy(c)) }}
                          </td>
                          <td class="py-2 px-4 font-num-md text-success text-green-700">
                            {{ fmt(net(c)) }}
                          </td>
                        </tr>
                        <tr v-if="!channels.length">
                          <td colspan="4" class="py-2 px-4 text-on-surface-variant">
                            {{ t('加载渠道中…') }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
            <div class="relative">
              <div class="flex gap-4 relative z-10">
                <div class="step-node bg-green-600 text-white mt-1 shadow-sm">
                  <span
                    class="material-symbols-outlined text-[14px]"
                    style="font-variation-settings: 'FILL' 1"
                    >check_circle</span
                  >
                </div>
                <div class="flex-1 bg-surface-bright border border-green-200 rounded-lg p-4">
                  <h3
                    class="font-headline-md text-base text-green-800 font-semibold flex items-center gap-2"
                  >
                    {{ t('5. 护栏检查通过 (Guardrail Checks Passed)') }}
                  </h3>
                  <ul class="mt-3 space-y-2 text-sm text-on-surface-variant">
                    <li
                      class="flex items-center justify-between border-b border-outline-variant/30 pb-2 mb-2"
                    >
                      <span class="flex items-center gap-2 font-medium text-primary"
                        ><span class="material-symbols-outlined text-[16px]">filter_alt</span>
                        {{ t('N_floor 净价底线过滤') }}</span
                      ><span class="font-num-md text-xs bg-primary/10 px-2 py-0.5 rounded"
                        >Active</span
                      >
                    </li>
                    <li class="flex items-center justify-between">
                      <span class="flex items-center gap-2"
                        ><span class="material-symbols-outlined text-green-600 text-[16px]"
                          >done</span
                        >
                        {{ t('最低价保护 (Min Price: ¥200)') }}</span
                      ><span class="font-num-md text-xs">Pass</span>
                    </li>
                    <li class="flex items-center justify-between">
                      <span class="flex items-center gap-2"
                        ><span class="material-symbols-outlined text-green-600 text-[16px]"
                          >done</span
                        >
                        {{ t('单次变动上限 (&lt; 15%)') }}</span
                      ><span class="font-num-md text-xs">Pass (+8%)</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- 右栏：AI 决策摘要 -->
        <div class="col-span-12 lg:col-span-4 flex flex-col gap-gutter">
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-5 h-full"
          >
            <h3 class="font-headline-md text-md text-on-background mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-tertiary">psychology</span>
              {{ t('AI 决策摘要') }}
            </h3>
            <div class="text-sm text-on-surface-variant leading-relaxed space-y-4">
              <p>
                {{ t('系统检测到') }} <strong>Oct 24</strong> {{ t('期间受')
                }}<span class="bg-tertiary/10 text-tertiary px-1 rounded">{{
                  t('本地音乐节')
                }}</span
                >{{ t('影响，区域搜索热度环比上升 34%。') }}
              </p>
              <p>
                {{
                  t(
                    '结合本酒店历史该房型在类似热度下的转化表现，AI 模型判断当前定价 (¥298) 存在溢价空间。',
                  )
                }}
              </p>
              <div class="p-3 bg-surface-variant/30 rounded-lg border-l-2 border-primary text-xs">
                {{ t('建议将基准价上调至') }} ¥{{ basePrice }}，{{ t('预计能在保持') }} 85%
                {{ t('预定达成率的前提下，最大化') }} RevPAR {{ t('收益。') }}
              </div>
              <div class="mt-4 pt-4 border-t border-outline-variant/50">
                <h4 class="text-xs font-bold text-on-surface mb-2 flex items-center gap-1">
                  <span class="material-symbols-outlined text-xs">analytics</span>
                  {{ t('模拟推演依据 (Simulation Reasoning)') }}
                </h4>
                <ul class="grid grid-cols-2 gap-2 text-[11px]">
                  <li class="bg-surface-container p-2 rounded">
                    {{ t('Pace (进度):') }} <span class="text-success">+5%</span>
                  </li>
                  <li class="bg-surface-container p-2 rounded">
                    {{ t('Occ (出租率):') }} <span class="text-on-surface">68%</span>
                  </li>
                  <li class="bg-surface-container p-2 rounded">
                    Price Gap: <span class="text-tertiary">-¥15</span>
                  </li>
                  <li class="bg-surface-container p-2 rounded">
                    {{ t('竞对均价:') }} <span class="text-on-surface">¥335</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
