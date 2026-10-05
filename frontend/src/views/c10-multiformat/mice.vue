<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// MICE 交叉收益优化看板（C10 多形态）
// 顶部 KPI / 团队 vs 散客图 / 各类型 ROI 表为原型静态结构（忠实还原），
// 底部「近期 MICE 活动」绑定 api.demo('mice') 渲染真实事件列表。
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import { fmt } from '../../lib/ui'

const events = ref<any[]>([])
onMounted(async () => {
  events.value = await api.demo('mice')
})
// 状态 pill 样式：已确认=绿、洽谈中=蓝、待排期=灰、观察=橙
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
      <div class="mb-6 flex justify-between items-end">
        <div>
          <h1 class="font-headline-lg text-headline-lg font-bold text-on-surface">
            {{ t('MICE 交叉收益优化看板') }}
          </h1>
          <p class="font-body-md text-body-md text-on-surface-variant mt-1">
            {{ t('会议与活动(MICE)的“光环效应”对客房及餐饮收入的全面分析') }}
          </p>
        </div>
        <div class="flex gap-2">
          <button
            class="px-4 py-2 bg-surface-container-high hover:bg-secondary-container text-on-surface rounded-lg font-label-lg text-label-lg transition-colors border border-outline-variant flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-sm">calendar_month</span> {{ t('本月') }}
          </button>
          <button
            class="px-4 py-2 bg-primary text-on-primary hover:bg-primary-container rounded-lg font-label-lg text-label-lg transition-colors flex items-center gap-2 shadow-sm"
          >
            <span class="material-symbols-outlined text-sm">download</span> {{ t('导出报告') }}
          </button>
        </div>
      </div>
      <!-- AI 优化建议 banner -->
      <div
        class="bg-[#f0f4fb] border-l-4 border-primary rounded-r-xl p-4 mb-8 flex items-start gap-4 shadow-sm relative overflow-hidden"
      >
        <div
          class="absolute -right-20 -top-20 w-64 h-64 bg-tertiary-fixed-dim/20 rounded-full blur-3xl pointer-events-none"
        ></div>
        <div class="bg-primary-container text-on-primary-container p-2 rounded-lg shrink-0">
          <span class="material-symbols-outlined icon-fill">neurology</span>
        </div>
        <div class="flex-1">
          <h3 class="font-headline-md text-[18px] font-semibold text-primary mb-1">
            {{ t('AI 优化建议') }}
          </h3>
          <p class="font-body-md text-body-md text-on-surface">
            {{ t('10月15日的200人婚礼活动预计将占用40%的基础房型。AI建议：')
            }}<strong class="text-on-surface">{{ t('适度提高非团队散客的高级套房价格') }}</strong
            >{{ t('，以最大化剩余库存收益，同时通过餐饮加购包提升转化率。') }}
          </p>
        </div>
        <div class="shrink-0 flex gap-2">
          <button
            class="px-4 py-1.5 border border-primary text-primary rounded-lg font-label-lg hover:bg-primary-fixed transition-colors"
          >
            {{ t('忽略') }}
          </button>
          <button
            class="px-4 py-1.5 bg-primary text-on-primary rounded-lg font-label-lg hover:bg-primary-container transition-colors shadow-sm"
          >
            {{ t('一键应用策略') }}
          </button>
        </div>
      </div>
      <!-- KPI Bento -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-gutter mb-8">
        <div
          class="bg-surface-container-lowest border border-surface-variant rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group"
        >
          <div
            class="absolute top-0 right-0 w-32 h-32 bg-primary-fixed/30 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"
          ></div>
          <div class="flex justify-between items-start mb-4">
            <h3 class="font-label-lg text-label-lg text-on-surface-variant">
              {{ t('团队客房占用 (Pickup)') }}
            </h3>
            <span class="material-symbols-outlined text-primary bg-primary-fixed p-1.5 rounded-md"
              >bed</span
            >
          </div>
          <div class="font-num-xl text-[36px] font-bold text-on-surface mb-2">
            1,240
            <span class="font-body-md text-body-md text-on-surface-variant font-normal">{{
              t('间夜')
            }}</span>
          </div>
          <div class="flex items-center text-sm">
            <span class="material-symbols-outlined text-[16px] text-green-600 mr-1"
              >trending_up</span
            >
            <span class="text-green-600 font-medium mr-2">+12%</span>
            <span class="text-on-surface-variant">{{ t('较上月同期') }}</span>
          </div>
        </div>
        <div
          class="bg-surface-container-lowest border border-surface-variant rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group"
        >
          <div
            class="absolute top-0 right-0 w-32 h-32 bg-tertiary-fixed/30 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"
          ></div>
          <div class="flex justify-between items-start mb-4">
            <h3 class="font-label-lg text-label-lg text-on-surface-variant">
              {{ t('参会代表平均消费') }}
            </h3>
            <span class="material-symbols-outlined text-tertiary bg-tertiary-fixed p-1.5 rounded-md"
              >local_dining</span
            >
          </div>
          <div class="font-num-xl text-[36px] font-bold text-on-surface mb-2">
            ¥850
            <span class="font-body-md text-body-md text-on-surface-variant font-normal">{{
              t('/人')
            }}</span>
          </div>
          <div class="flex items-center text-sm">
            <span class="material-symbols-outlined text-[16px] text-green-600 mr-1"
              >trending_up</span
            >
            <span class="text-green-600 font-medium mr-2">+5.4%</span>
            <span class="text-on-surface-variant">{{ t('受高端餐饮拉动') }}</span>
          </div>
        </div>
        <div
          class="bg-surface-container-lowest border border-surface-variant rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group"
        >
          <div
            class="absolute top-0 right-0 w-32 h-32 bg-secondary-fixed/30 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"
          ></div>
          <div class="flex justify-between items-start mb-4">
            <h3 class="font-label-lg text-label-lg text-on-surface-variant">
              {{ t('MICE 留宿转化率') }}
            </h3>
            <span
              class="material-symbols-outlined text-secondary bg-secondary-fixed p-1.5 rounded-md"
              >swap_calls</span
            >
          </div>
          <div class="font-num-xl text-[36px] font-bold text-on-surface mb-2">32.8%</div>
          <div class="flex items-center text-sm">
            <span class="material-symbols-outlined text-[16px] text-red-500 mr-1"
              >trending_down</span
            >
            <span class="text-red-500 font-medium mr-2">-2.1%</span>
            <span class="text-on-surface-variant">{{ t('低于行业基准 35%') }}</span>
          </div>
        </div>
      </div>
      <!-- 图表 + ROI 表 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-gutter">
        <div
          class="lg:col-span-2 bg-surface-container-lowest border border-surface-variant rounded-xl shadow-sm p-6 flex flex-col h-[400px]"
        >
          <div class="flex justify-between items-center mb-6">
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('活动期间收益对比：团队 vs. 散客') }}
            </h2>
            <div class="flex gap-4">
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full bg-primary"></div>
                <span class="font-label-lg text-xs text-on-surface-variant">{{
                  t('企业团队 (MICE)')
                }}</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full bg-tertiary"></div>
                <span class="font-label-lg text-xs text-on-surface-variant">{{
                  t('散客 (Retail)')
                }}</span>
              </div>
            </div>
          </div>
          <div class="flex-1 relative flex items-end gap-4 pb-8 pl-8 pt-4">
            <div
              class="absolute left-0 top-4 bottom-8 flex flex-col justify-between text-xs text-on-surface-variant font-num-md items-end pr-2"
            >
              <span>¥50w</span><span>¥30w</span><span>¥10w</span><span>¥0</span>
            </div>
            <div class="absolute left-8 right-0 top-4 bottom-8 flex flex-col justify-between z-0">
              <div class="w-full border-b border-surface-variant border-dashed"></div>
              <div class="w-full border-b border-surface-variant border-dashed"></div>
              <div class="w-full border-b border-surface-variant border-dashed"></div>
              <div class="w-full border-b border-surface-variant border-dashed"></div>
            </div>
            <div class="flex-1 flex justify-center items-end gap-2 group z-10 h-full relative">
              <div
                class="w-8 md:w-12 bg-primary rounded-t-sm h-[60%] hover:opacity-80 transition-opacity"
              ></div>
              <div
                class="w-8 md:w-12 bg-tertiary rounded-t-sm h-[40%] hover:opacity-80 transition-opacity"
              ></div>
              <div
                class="absolute -bottom-6 w-full text-center text-xs font-label-lg text-on-surface-variant truncate"
              >
                {{ t('Q1 峰会') }}
              </div>
            </div>
            <div class="flex-1 flex justify-center items-end gap-2 group z-10 h-full relative">
              <div
                class="w-8 md:w-12 bg-primary rounded-t-sm h-[45%] hover:opacity-80 transition-opacity"
              ></div>
              <div
                class="w-8 md:w-12 bg-tertiary rounded-t-sm h-[70%] hover:opacity-80 transition-opacity"
              ></div>
              <div
                class="absolute -bottom-6 w-full text-center text-xs font-label-lg text-on-surface-variant truncate"
              >
                {{ t('行业展会') }}
              </div>
            </div>
            <div class="flex-1 flex justify-center items-end gap-2 group z-10 h-full relative">
              <div
                class="w-8 md:w-12 bg-primary rounded-t-sm h-[80%] hover:opacity-80 transition-opacity"
              ></div>
              <div
                class="w-8 md:w-12 bg-tertiary rounded-t-sm h-[30%] hover:opacity-80 transition-opacity"
              ></div>
              <div
                class="absolute -bottom-6 w-full text-center text-xs font-label-lg text-on-surface-variant truncate"
              >
                {{ t('年终答谢') }}
              </div>
            </div>
            <div
              class="flex-1 flex justify-center items-end gap-2 group z-10 h-full relative bg-surface-container/30 rounded-lg"
            >
              <div class="absolute top-2 left-0 right-0 text-center text-xs text-primary font-bold">
                {{ t('10月15日') }}
              </div>
              <div
                class="w-8 md:w-12 bg-primary rounded-t-sm h-[55%] hover:opacity-80 transition-opacity border-2 border-primary-fixed shadow-[0_0_10px_rgba(26,115,232,0.3)]"
              ></div>
              <div
                class="w-8 md:w-12 bg-tertiary rounded-t-sm h-[65%] hover:opacity-80 transition-opacity"
              ></div>
              <div
                class="absolute -bottom-6 w-full text-center text-xs font-label-lg text-on-surface-variant truncate"
              >
                {{ t('大型婚礼(预测)') }}
              </div>
            </div>
          </div>
        </div>
        <div
          class="lg:col-span-1 bg-surface-container-lowest border border-surface-variant rounded-xl shadow-sm overflow-hidden flex flex-col h-[400px]"
        >
          <div class="p-6 border-b border-surface-variant pb-4 bg-surface-bright">
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('各类型活动历史 ROI') }}
            </h2>
          </div>
          <div class="flex-1 overflow-y-auto">
            <table class="w-full text-left">
              <thead
                class="bg-surface-container-low font-label-lg text-label-lg text-on-surface-variant sticky top-0"
              >
                <tr>
                  <th class="p-3 font-medium">{{ t('活动类型') }}</th>
                  <th class="p-3 font-medium text-right">{{ t('综合利润率') }}</th>
                  <th class="p-3 font-medium text-right">{{ t('餐饮贡献') }}</th>
                </tr>
              </thead>
              <tbody
                class="font-body-md text-body-md text-on-surface divide-y divide-surface-variant"
              >
                <tr class="hover:bg-surface-bright transition-colors group">
                  <td class="p-3">
                    <div class="flex items-center gap-2">
                      <span class="material-symbols-outlined text-primary text-[18px]"
                        >business_center</span
                      >{{ t('大型企业会议') }}
                    </div>
                  </td>
                  <td class="p-3 text-right font-num-md text-green-600 font-medium">35%</td>
                  <td class="p-3 text-right">
                    <div class="w-full bg-surface-variant rounded-full h-1.5 mt-2 overflow-hidden">
                      <div class="bg-tertiary h-1.5 rounded-full" style="width: 45%"></div>
                    </div>
                    <span class="text-xs text-on-surface-variant mt-1 block">45%</span>
                  </td>
                </tr>
                <tr class="hover:bg-surface-bright transition-colors group">
                  <td class="p-3">
                    <div class="flex items-center gap-2">
                      <span class="material-symbols-outlined text-secondary text-[18px]"
                        >celebration</span
                      >{{ t('婚宴/私人派对') }}
                    </div>
                  </td>
                  <td class="p-3 text-right font-num-md text-green-600 font-medium">42%</td>
                  <td class="p-3 text-right">
                    <div class="w-full bg-surface-variant rounded-full h-1.5 mt-2 overflow-hidden">
                      <div class="bg-tertiary h-1.5 rounded-full" style="width: 70%"></div>
                    </div>
                    <span class="text-xs text-on-surface-variant mt-1 block">70%</span>
                  </td>
                </tr>
                <tr class="hover:bg-surface-bright transition-colors group">
                  <td class="p-3">
                    <div class="flex items-center gap-2">
                      <span class="material-symbols-outlined text-outline text-[18px]"
                        >co_present</span
                      >{{ t('行业展会/论坛') }}
                    </div>
                  </td>
                  <td class="p-3 text-right font-num-md text-on-surface font-medium">28%</td>
                  <td class="p-3 text-right">
                    <div class="w-full bg-surface-variant rounded-full h-1.5 mt-2 overflow-hidden">
                      <div class="bg-tertiary h-1.5 rounded-full" style="width: 25%"></div>
                    </div>
                    <span class="text-xs text-on-surface-variant mt-1 block">25%</span>
                  </td>
                </tr>
                <tr class="hover:bg-surface-bright transition-colors group">
                  <td class="p-3">
                    <div class="flex items-center gap-2">
                      <span class="material-symbols-outlined text-outline text-[18px]"
                        >sports_martial_arts</span
                      >{{ t('团建拓展') }}
                    </div>
                  </td>
                  <td class="p-3 text-right font-num-md text-on-surface font-medium">22%</td>
                  <td class="p-3 text-right">
                    <div class="w-full bg-surface-variant rounded-full h-1.5 mt-2 overflow-hidden">
                      <div class="bg-tertiary h-1.5 rounded-full" style="width: 30%"></div>
                    </div>
                    <span class="text-xs text-on-surface-variant mt-1 block">30%</span>
                  </td>
                </tr>
              </tbody>
            </table>
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
            {{ t('近期 MICE 活动') }}
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
