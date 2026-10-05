<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 智能收益预测看板 (365天)：RevPAR 预测图 + 高需求预警 + 事件日历 + AI 对比
// 长尾域：api.demo('yield') 渲染 365 天 RevPAR 预测柱状图（predicted_occ 高度）
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
    <!-- 页头 -->
    <div class="flex justify-between items-end mb-6">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background mb-1">
          {{ t('智能收益预测看板') }}
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          Future-Cast BI: AI-driven insights for the next 365 days.
        </p>
      </div>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 bg-surface-container-lowest border border-outline-variant rounded flex items-center gap-2 font-label-lg text-label-lg text-on-surface hover:bg-surface-container-low transition-colors shadow-sm"
        >
          <span class="material-symbols-outlined text-[18px]">calendar_month</span>
          {{ t('选择日期范围') }}
        </button>
        <button
          class="px-4 py-2 bg-primary text-on-primary rounded flex items-center gap-2 font-label-lg text-label-lg hover:bg-primary/90 transition-colors shadow-sm"
        >
          <span
            class="material-symbols-outlined text-[18px]"
            style="font-variation-settings: 'FILL' 1"
            >auto_awesome</span
          >
          {{ t('一键采纳AI建议') }}
        </button>
      </div>
    </div>
    <!-- Bento 布局 -->
    <div class="grid grid-cols-12 gap-gutter">
      <!-- 主预测图 (Col 8) -->
      <div
        class="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm flex flex-col h-[420px]"
      >
        <div class="flex justify-between items-center mb-4">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-tertiary">monitoring</span>
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('365天 RevPAR &amp; 出租率预测') }}
            </h2>
          </div>
          <div class="flex items-center gap-4 text-sm">
            <div class="flex items-center gap-1">
              <div class="w-3 h-3 rounded-full bg-primary"></div>
              <span>{{ t('RevPAR (预测)') }}</span>
            </div>
            <div class="flex items-center gap-1">
              <div class="w-3 h-3 rounded-full bg-tertiary/30"></div>
              <span>{{ t('AI 置信区间') }}</span>
            </div>
          </div>
        </div>
        <!-- 预测柱状图（数据驱动：demo('yield') 首 8 天占位 365 视图） -->
        <div
          class="flex-1 relative w-full h-full flex items-end gap-2 px-2 border-b border-l border-outline-variant pt-4"
        >
          <div
            v-for="y in yields"
            :key="y.id"
            class="flex-1 flex flex-col items-center justify-end h-full"
          >
            <span class="text-[10px] text-on-surface-variant mb-1">{{ y.lift }}</span>
            <div class="w-full bg-primary rounded-t" :style="{ height: occNum(y) + '%' }"></div>
          </div>
          <div
            v-if="!yields.length"
            class="absolute inset-0 flex items-center justify-center text-on-surface-variant"
          >
            {{ t('加载中…') }}
          </div>
        </div>
        <div class="flex justify-around text-outline font-num-md text-[12px] mt-2">
          <span>{{ t('第1周') }}</span
          ><span>{{ t('第4周') }}</span
          ><span>{{ t('第12周') }}</span
          ><span>{{ t('第26周') }}</span
          ><span>{{ t('第52周') }}</span>
        </div>
      </div>
      <!-- 高需求预警 (Col 4) -->
      <div class="col-span-12 lg:col-span-4 flex flex-col gap-gutter">
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm flex-1"
        >
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-[#d97706]">warning</span>
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('高需求预警 (Sell-out Alerts)') }}
            </h2>
          </div>
          <div class="flex flex-col gap-3">
            <div
              class="p-3 border border-[#f59e0b] bg-[#fffbeb] rounded-lg relative overflow-hidden"
            >
              <div class="absolute left-0 top-0 bottom-0 w-1 bg-[#f59e0b]"></div>
              <div class="flex justify-between items-start mb-1">
                <span class="font-label-lg text-label-lg text-[#92400e]">{{
                  t('10月1日 - 10月7日 (国庆节)')
                }}</span>
                <span class="text-xs font-bold text-[#b45309] bg-[#fde68a] px-2 py-0.5 rounded">{{
                  t('建议审核')
                }}</span>
              </div>
              <div class="flex items-end justify-between mt-2">
                <div>
                  <p class="text-xs text-on-surface-variant">{{ t('预测出租率') }}</p>
                  <p class="font-num-md text-num-md text-on-surface">
                    98%
                    <span class="material-symbols-outlined text-[14px] text-error align-middle"
                      >trending_up</span
                    >
                  </p>
                </div>
                <button class="text-sm text-primary font-medium hover:underline">
                  {{ t('查看调价建议') }}
                </button>
              </div>
            </div>
            <div
              class="p-3 border border-outline-variant bg-surface-container-lowest rounded-lg ai-border-glow ai-gradient-bg"
            >
              <div class="flex justify-between items-start mb-1">
                <span class="font-label-lg text-label-lg text-on-surface">{{
                  t('11月11日 - 11月12日 (本地会展)')
                }}</span>
                <span class="material-symbols-outlined text-tertiary text-[18px]"
                  >auto_awesome</span
                >
              </div>
              <div class="flex items-end justify-between mt-2">
                <div>
                  <p class="text-xs text-on-surface-variant">{{ t('当前定价低于市场均值 15%') }}</p>
                  <p class="font-body-md text-body-md text-on-surface">
                    {{ t('建议上调基准价至') }} <span class="font-num-md">¥680</span>
                  </p>
                </div>
                <button
                  class="text-sm bg-tertiary/10 text-tertiary px-2 py-1 rounded font-medium hover:bg-tertiary/20"
                >
                  {{ t('一键应用') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- 市场事件日历 (Col 6) -->
      <div
        class="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm"
      >
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-secondary">event</span>
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('市场事件日历') }}
            </h2>
          </div>
          <select
            class="text-sm border-none bg-surface-container-low rounded py-1 pl-2 pr-8 focus:ring-0"
          >
            <option>{{ t('本月 (9月)') }}</option>
            <option>{{ t('下月 (10月)') }}</option>
          </select>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-outline-variant text-sm text-on-surface-variant">
                <th class="pb-2 font-medium w-1/4">{{ t('日期') }}</th>
                <th class="pb-2 font-medium w-2/4">{{ t('事件名称') }}</th>
                <th class="pb-2 font-medium w-1/4 text-right">{{ t('需求影响评估') }}</th>
              </tr>
            </thead>
            <tbody class="text-sm">
              <tr class="border-b border-surface-container-highest">
                <td class="py-3 font-num-md text-on-surface">09.15 - 09.17</td>
                <td class="py-3">
                  <span class="bg-primary/10 text-primary px-2 py-0.5 rounded text-xs mr-2">{{
                    t('法定假日')
                  }}</span
                  >{{ t('中秋节假期') }}
                </td>
                <td class="py-3 text-right">
                  <div class="flex items-center justify-end gap-1">
                    <div class="w-16 h-2 bg-surface-container-highest rounded-full overflow-hidden">
                      <div class="w-[80%] h-full bg-primary"></div>
                    </div>
                    <span class="font-num text-[#d97706]">+45%</span>
                  </div>
                </td>
              </tr>
              <tr class="border-b border-surface-container-highest">
                <td class="py-3 font-num-md text-on-surface">09.28</td>
                <td class="py-3">
                  <span class="bg-tertiary/10 text-tertiary px-2 py-0.5 rounded text-xs mr-2">{{
                    t('演唱会')
                  }}</span
                  >{{ t('周杰伦巡回演唱会') }}
                </td>
                <td class="py-3 text-right">
                  <div class="flex items-center justify-end gap-1">
                    <div class="w-16 h-2 bg-surface-container-highest rounded-full overflow-hidden">
                      <div class="w-[100%] h-full bg-error"></div>
                    </div>
                    <span class="font-num text-error">+120%</span>
                  </div>
                </td>
              </tr>
              <tr>
                <td class="py-3 font-num-md text-on-surface">10.12 - 10.15</td>
                <td class="py-3">
                  <span class="bg-secondary/10 text-secondary px-2 py-0.5 rounded text-xs mr-2">{{
                    t('展会')
                  }}</span
                  >{{ t('国际汽车工业博览会') }}
                </td>
                <td class="py-3 text-right">
                  <div class="flex items-center justify-end gap-1">
                    <div class="w-16 h-2 bg-surface-container-highest rounded-full overflow-hidden">
                      <div class="w-[60%] h-full bg-primary"></div>
                    </div>
                    <span class="font-num text-primary">+25%</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <!-- AI 对比 (Col 6) -->
      <div
        class="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm flex flex-col"
      >
        <div class="flex items-center gap-2 mb-4">
          <span class="material-symbols-outlined text-primary">history_edu</span>
          <h2 class="font-headline-md text-headline-md text-on-surface">
            {{ t('AI预测与历史表现对比') }}
          </h2>
        </div>
        <div class="grid grid-cols-2 gap-4 mb-4">
          <div class="p-4 bg-surface rounded-lg border border-outline-variant">
            <p class="text-sm text-on-surface-variant mb-1">{{ t('去年同期 RevPAR') }}</p>
            <p class="font-display-lg text-display-lg font-num text-on-surface">¥342</p>
          </div>
          <div class="p-4 ai-gradient-bg rounded-lg border border-tertiary/30 ai-border-glow">
            <p class="text-sm text-tertiary mb-1 flex items-center gap-1">
              <span class="material-symbols-outlined text-[14px]">auto_awesome</span>
              {{ t('预测下月同期 RevPAR') }}
            </p>
            <p class="font-display-lg text-display-lg font-num text-on-surface">
              ¥385 <span class="text-sm text-[#16a34a] font-normal align-middle">+12.5%</span>
            </p>
          </div>
        </div>
        <div
          class="flex-1 text-sm text-on-surface-variant bg-surface-container-low p-3 rounded flex items-start gap-2"
        >
          <span class="material-symbols-outlined text-[18px] mt-0.5">info</span>
          <p>
            {{
              t(
                'AI模型指出，由于本年度新增了三个大型商业展会，加上优化后的动态定价策略，预计第四季度的整体收益将有显著提升。建议在展会前45天提前锁定远期早鸟价格策略。',
              )
            }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
