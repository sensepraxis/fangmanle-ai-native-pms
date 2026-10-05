<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 智能会议室与宴会预订 · MICE 智能仪表盘（C10 多形态）
// AI 动态定价卡片 / 套餐转化预测 / 场地资源时间轴为原型静态结构；
// 底部「近期 MICE 活动」绑定 api.demo('mice') 渲染真实事件列表。
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import { fmt } from '../../lib/ui'

const events = ref<any[]>([])
onMounted(async () => {
  events.value = await api.demo('mice')
})
function statusPill(s: string) {
  if (s === t('已确认')) return 'text-green-700 bg-green-50'
  if (s === t('洽谈中')) return 'text-primary bg-primary-fixed'
  if (s === t('待排期')) return 'text-on-surface-variant bg-surface-variant'
  return 'text-tertiary bg-tertiary-fixed'
}
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto">
      <!-- 页头 -->
      <div class="flex justify-between items-center mb-8">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-background">
            {{ t('智能会议室与宴会预订') }}
          </h1>
          <p class="font-body-lg text-body-lg text-on-surface-variant mt-2">
            {{ t('MICE 智能仪表盘') }}
          </p>
        </div>
        <div class="flex gap-4">
          <button
            class="bg-surface-container-highest text-on-surface px-4 py-2 rounded-lg font-label-lg text-label-lg border border-outline-variant hover:bg-surface-variant transition-colors flex items-center gap-2"
          >
            {{ t('选择日期') }}
          </button>
          <button
            class="bg-primary text-on-primary px-6 py-2 rounded-lg font-label-lg text-label-lg hover:bg-on-primary-fixed-variant transition-colors tonal-shadow flex items-center gap-2"
          >
            {{ t('新建预订') }}
          </button>
        </div>
      </div>
      <!-- 网格布局 -->
      <div class="grid grid-cols-12 gap-gutter">
        <!-- AI 动态定价引擎 -->
        <div
          class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 tonal-shadow flex flex-col gap-6"
        >
          <div class="flex justify-between items-center">
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('AI 动态定价引擎') }}
            </h2>
            <div
              class="bg-primary-fixed text-on-primary-fixed px-3 py-1 rounded-full font-label-lg text-label-lg flex items-center gap-1"
            >
              {{ t('需求旺季: 建议上调') }}
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              class="border border-outline-variant rounded-lg p-4 bg-surface hover:border-primary transition-colors cursor-pointer group"
            >
              <div class="flex justify-between items-start mb-4">
                <div>
                  <h3 class="font-headline-lg text-headline-lg text-on-surface">
                    {{ t('大宴会厅 A') }}
                  </h3>
                  <p class="font-body-md text-body-md text-on-surface-variant">
                    {{ t('容量: 500人 | 设备: 全套') }}
                  </p>
                </div>
              </div>
              <div class="flex items-end justify-between">
                <div>
                  <div class="font-num-md text-num-md text-on-surface-variant line-through">
                    {{ t('¥ 15,000 / 天') }}
                  </div>
                  <div class="font-num-xl text-num-xl text-primary font-bold">
                    {{ t('¥ 18,500 / 天') }}
                  </div>
                </div>
                <div class="text-right">
                  <span
                    class="bg-error-container text-on-error-container text-xs px-2 py-1 rounded-md font-label-lg"
                    >{{ t('+23% 周末溢价') }}</span
                  >
                </div>
              </div>
              <div class="mt-4 text-sm text-on-surface-variant flex items-center gap-1">
                {{ t('AI 建议: 本周末行业峰会较多，需求强劲。') }}
              </div>
            </div>
            <div
              class="border border-outline-variant rounded-lg p-4 bg-surface hover:border-primary transition-colors cursor-pointer group"
            >
              <div class="flex justify-between items-start mb-4">
                <div>
                  <h3 class="font-headline-lg text-headline-lg text-on-surface">
                    {{ t('高管会议室 1') }}
                  </h3>
                  <p class="font-body-md text-body-md text-on-surface-variant">
                    {{ t('容量: 20人 | 设备: 视频会议') }}
                  </p>
                </div>
              </div>
              <div class="flex items-end justify-between">
                <div>
                  <div class="font-num-md text-num-md text-on-surface-variant line-through">
                    {{ t('¥ 3,000 / 半天') }}
                  </div>
                  <div class="font-num-xl text-num-xl text-primary font-bold">
                    {{ t('¥ 2,800 / 半天') }}
                  </div>
                </div>
                <div class="text-right">
                  <span
                    class="bg-primary-fixed text-on-primary-fixed text-xs px-2 py-1 rounded-md font-label-lg"
                    >{{ t('-6% 闲时特惠') }}</span
                  >
                </div>
              </div>
              <div class="mt-4 text-sm text-on-surface-variant flex items-center gap-1">
                {{ t('AI 建议: 下周二上午存在档期空隙，建议小幅降价促销。') }}
              </div>
            </div>
          </div>
        </div>
        <!-- 套餐转化预测 -->
        <div
          class="col-span-12 lg:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 tonal-shadow flex flex-col gap-4"
        >
          <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
            {{ t('MICE 套餐转化预测') }}
          </h2>
          <div class="bg-surface border border-outline-variant rounded-lg p-4 ai-glow">
            <div class="flex items-center gap-3 mb-2">
              <div
                class="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center"
              ></div>
              <div>
                <div class="font-label-lg text-label-lg text-on-surface">
                  {{ t('张伟 (科技公司 HR)') }}
                </div>
                <div class="text-sm text-on-surface-variant">{{ t('仅预订客房 (20间)') }}</div>
              </div>
            </div>
            <div class="my-4">
              <div class="flex justify-between text-sm mb-1">
                <span class="text-on-surface-variant">{{ t('转化 MICE 套餐概率') }}</span
                ><span class="text-primary font-bold">85%</span>
              </div>
              <div class="w-full bg-surface-container-high rounded-full h-2">
                <div class="bg-primary h-2 rounded-full" style="width: 85%"></div>
              </div>
            </div>
            <div class="bg-surface-container-low p-3 rounded text-sm text-on-surface-variant mb-4">
              {{
                t(
                  'AI 分析: 该企业用户近期在寻觅团建场地，建议推送包含会议室与茶歇的"企业精英套餐"。',
                )
              }}
            </div>
            <button
              class="w-full bg-surface-container-highest text-on-surface py-2 rounded-lg font-label-lg text-label-lg border border-outline-variant hover:bg-surface-variant transition-colors"
            >
              {{ t('一键生成个性化报价方案') }}
            </button>
          </div>
        </div>
        <!-- 场地资源看板（时间轴） -->
        <div
          class="col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 tonal-shadow"
        >
          <div class="flex justify-between items-center mb-6">
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('场地资源看板 (10月24日)') }}
            </h2>
            <div class="flex gap-2">
              <span class="flex items-center gap-1 text-sm text-on-surface-variant"
                ><div class="w-3 h-3 bg-primary rounded-sm"></div>
                {{ t('已预订') }}</span
              >
              <span class="flex items-center gap-1 text-sm text-on-surface-variant"
                ><div
                  class="w-3 h-3 bg-surface-container-highest border border-outline-variant rounded-sm"
                ></div>
                {{ t('空闲') }}</span
              >
              <span class="flex items-center gap-1 text-sm text-on-surface-variant"
                ><div class="w-3 h-3 bg-error border border-error rounded-sm"></div>
                {{ t('维护') }}</span
              >
            </div>
          </div>
          <div class="overflow-x-auto">
            <div class="min-w-[800px]">
              <div
                class="flex border-b border-outline-variant pb-2 mb-2 font-num-md text-num-md text-on-surface-variant"
              >
                <div class="w-48 flex-shrink-0 pl-2">{{ t('场地名称') }}</div>
                <div class="flex-1 flex justify-between px-2">
                  <span>08:00</span><span>10:00</span><span>12:00</span><span>14:00</span
                  ><span>16:00</span><span>18:00</span>
                </div>
              </div>
              <div
                class="flex items-center py-3 border-b border-surface-container-high hover:bg-surface-container-low transition-colors"
              >
                <div class="w-48 flex-shrink-0 pl-2 font-label-lg text-label-lg text-on-surface">
                  {{ t('大宴会厅 A') }}
                </div>
                <div
                  class="flex-1 relative h-8 bg-surface-container-highest rounded-md mx-2 border border-outline-variant/30"
                >
                  <div
                    class="absolute left-[10%] w-[40%] h-full bg-primary rounded-md flex items-center px-2 text-on-primary text-xs overflow-hidden text-ellipsis whitespace-nowrap cursor-pointer hover:bg-primary-fixed-variant shadow-sm"
                  >
                    {{ t('万科年度峰会 (500人)') }}
                  </div>
                  <div
                    class="absolute left-[60%] w-[30%] h-full bg-primary rounded-md flex items-center px-2 text-on-primary text-xs overflow-hidden text-ellipsis whitespace-nowrap cursor-pointer hover:bg-primary-fixed-variant shadow-sm"
                  >
                    {{ t('晚宴筹备') }}
                  </div>
                </div>
              </div>
              <div
                class="flex items-center py-3 border-b border-surface-container-high hover:bg-surface-container-low transition-colors"
              >
                <div class="w-48 flex-shrink-0 pl-2 font-label-lg text-label-lg text-on-surface">
                  {{ t('高管会议室 1') }}
                </div>
                <div
                  class="flex-1 relative h-8 bg-surface-container-highest rounded-md mx-2 border border-outline-variant/30"
                >
                  <div
                    class="absolute left-0 w-[20%] h-full bg-primary rounded-md flex items-center px-2 text-on-primary text-xs overflow-hidden text-ellipsis whitespace-nowrap cursor-pointer hover:bg-primary-fixed-variant shadow-sm"
                  >
                    {{ t('内部高管会') }}
                  </div>
                  <div
                    class="absolute left-[50%] w-[50%] h-full bg-error/80 rounded-md flex items-center px-2 text-on-error text-xs overflow-hidden text-ellipsis whitespace-nowrap cursor-not-allowed shadow-sm"
                  >
                    {{ t('设备维护 (投影仪更换)') }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 近期 MICE 活动（绑定 api.demo('mice')） -->
      <div
        class="mt-8 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden"
      >
        <div
          class="px-6 py-4 border-b border-outline-variant bg-surface-bright flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-primary">event_available</span>
          <h2 class="font-headline-md text-headline-md text-on-surface">
            {{ t('近期 MICE 活动排期') }}
          </h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr
                class="border-b border-outline-variant bg-surface-container-low font-label-lg text-label-lg text-on-surface-variant"
              >
                <th class="py-3 px-4">{{ t('活动') }}</th>
                <th class="py-3 px-4">{{ t('场地') }}</th>
                <th class="py-3 px-4 text-right">{{ t('人数') }}</th>
                <th class="py-3 px-4">{{ t('日期') }}</th>
                <th class="py-3 px-4">{{ t('状态') }}</th>
                <th class="py-3 px-4 text-right">{{ t('预计收入') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant">
              <tr v-for="e in events" :key="e.id" class="hover:bg-surface-bright transition-colors">
                <td class="py-3 px-4 font-medium text-on-surface">{{ e.event }}</td>
                <td class="py-3 px-4 text-sm text-on-surface">{{ e.space }}</td>
                <td class="py-3 px-4 text-right font-num-md text-on-surface">{{ e.pax }}</td>
                <td class="py-3 px-4 text-sm text-on-surface">{{ e.date }}</td>
                <td class="py-3 px-4">
                  <span
                    class="inline-flex text-xs font-medium rounded-full px-2 py-1"
                    :class="statusPill(e.status)"
                    >{{ e.status }}</span
                  >
                </td>
                <td class="py-3 px-4 text-right font-num-md text-primary font-bold">
                  {{ fmt(e.revenue) }}
                </td>
              </tr>
              <tr v-if="!events.length">
                <td colspan="6" class="py-8 text-center text-on-surface-variant">
                  {{ t('暂无活动') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
