<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'

const roiData = ref<any>(null)
// seed 保留原型示例卡片，保证 1:1 视觉；onMounted 后由真实接口数据覆盖
const seed: any[] = [
  {
    id: 0,
    cls: 'w-full border-t border-outline-variant/30 h-0 flex items-center',
    raw: '<span class="bg-surface pr-2 text-on-surface-variant text-[12px] font-num-md -mt-3">100k</span>',
  },
  {
    id: 1,
    cls: 'w-full border-t border-outline-variant/30 h-0 flex items-center',
    raw: '<span class="bg-surface pr-2 text-on-surface-variant text-[12px] font-num-md -mt-3">75k</span>',
  },
  {
    id: 2,
    cls: 'w-full border-t border-outline-variant/30 h-0 flex items-center',
    raw: '<span class="bg-surface pr-2 text-on-surface-variant text-[12px] font-num-md -mt-3">50k</span>',
  },
  {
    id: 3,
    cls: 'w-full border-t border-outline-variant/30 h-0 flex items-center',
    raw: '<span class="bg-surface pr-2 text-on-surface-variant text-[12px] font-num-md -mt-3">25k</span>',
  },
]
const rows = ref<any[]>(seed)
onMounted(loadRoi)
watch(() => hotelStore.hotelId, loadRoi)

async function loadRoi() {
  try {
    roiData.value = await api.acquisitionRoiAttribution(hotelStore.hotelId)
  } catch {
    roiData.value = null
  }
  try {
    const r = await api.demo('reputation')
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch {
    /* 保留原型 */
  }
}
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="main" /></div>
    <div class="max-w-max-content-width mx-auto">
      <!-- Page Header -->
      <div class="flex justify-between items-end mb-8">
        <div>
          <div class="flex items-center gap-2 text-on-surface-variant mb-1">
            <span class="material-symbols-outlined text-[18px]">payments</span>
            <span class="text-label-lg font-label-lg">{{ t('财务分析 / 营销效率') }}</span>
          </div>
          <h1 class="text-display-lg font-display-lg text-on-surface">
            {{ t('获客渠道 ROI 实时复盘') }}
          </h1>
          <p v-if="roiData?.summary" class="text-body-md text-on-surface-variant mt-2">
            {{ t('小红书线索') }} {{ roiData.summary.leads }} {{ t('条 · 成交') }}
            {{ roiData.summary.booked }} {{ t('条 ·') }} {{ t('投流') }} ¥{{
              roiData.summary.spend
            }}
            · ROI {{ roiData.summary.roi != null ? roiData.summary.roi + 'x' : '—' }}
          </p>
        </div>
        <div class="flex gap-3">
          <button
            class="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-lg bg-surface text-on-surface-variant hover:bg-surface-container-low transition-colors text-label-lg font-label-lg"
          >
            <span class="material-symbols-outlined text-[20px]">calendar_today</span>
            {{ t('近 30 天') }}
            <span class="material-symbols-outlined text-[20px]">arrow_drop_down</span>
          </button>
          <button
            class="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg hover:bg-primary-fixed-variant transition-colors text-label-lg font-label-lg shadow-sm"
          >
            <span class="material-symbols-outlined text-[20px]">download</span>
            {{ t('导出报告') }}
          </button>
        </div>
      </div>
      <!-- 小红书计划/笔记归因（真实 API） -->
      <div v-if="roiData" class="mb-8 grid grid-cols-12 gap-gutter">
        <section
          class="col-span-12 lg:col-span-6 bg-surface border border-outline-variant rounded-xl p-6 shadow-sm"
        >
          <h2 class="text-headline-md font-headline-md text-on-surface mb-4">
            {{ t('按广告计划归因') }}
          </h2>
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-on-surface-variant border-b">
                <th class="pb-2">{{ t('计划') }}</th>
                <th>{{ t('线索') }}</th>
                <th>{{ t('成交') }}</th>
                <th>ROI</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="p in roiData.by_plan"
                :key="p.plan_id"
                class="border-b border-outline-variant/30"
              >
                <td class="py-2">{{ p.campaign_name || p.plan_id }}</td>
                <td>{{ p.leads }}</td>
                <td>{{ p.booked }}</td>
                <td>{{ p.roi != null ? p.roi + 'x' : '—' }}</td>
              </tr>
              <tr v-if="!roiData.by_plan?.length">
                <td colspan="4" class="py-3 text-on-surface-variant">
                  {{ t('暂无计划归因数据') }}
                </td>
              </tr>
            </tbody>
          </table>
        </section>
        <section
          class="col-span-12 lg:col-span-6 bg-surface border border-outline-variant rounded-xl p-6 shadow-sm"
        >
          <h2 class="text-headline-md font-headline-md text-on-surface mb-4">
            {{ t('按种草笔记归因') }}
          </h2>
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-on-surface-variant border-b">
                <th class="pb-2">{{ t('笔记') }}</th>
                <th>{{ t('线索') }}</th>
                <th>{{ t('成交') }}</th>
                <th>{{ t('收入') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="n in roiData.by_note"
                :key="n.key"
                class="border-b border-outline-variant/30"
              >
                <td class="py-2 max-w-[200px] truncate">{{ n.key }}</td>
                <td>{{ n.leads }}</td>
                <td>{{ n.booked }}</td>
                <td>¥{{ n.rev }}</td>
              </tr>
              <tr v-if="!roiData.by_note?.length">
                <td colspan="4" class="py-3 text-on-surface-variant">
                  {{ t('暂无笔记归因数据') }}
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
      <!-- AI Insight Banner (Guardrail R0 style + AI Tinge) -->
      <div
        class="mb-8 border border-tertiary-fixed-dim bg-gradient-to-r from-tertiary-container/10 to-surface rounded-xl p-5 shadow-sm relative overflow-hidden flex items-start gap-4"
      >
        <div class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary"></div>
        <div class="p-2 bg-surface rounded-full shadow-sm text-tertiary shrink-0">
          <span class="material-symbols-outlined icon-fill">auto_awesome</span>
        </div>
        <div class="flex-1">
          <h3
            class="text-headline-md font-headline-md text-on-surface mb-1 flex items-center gap-2"
          >
            {{ t('AI 洞察建议') }}
            <span
              class="px-2 py-0.5 rounded-full bg-tertiary text-on-tertiary text-[12px] font-bold tracking-wide uppercase"
              >{{ t('高置信度') }}</span
            >
          </h3>
          <p class="text-body-lg font-body-lg text-on-surface-variant">
            {{ t('建议：根据当前搜索热度预测，将下周末') }}
            <strong class="text-on-surface font-semibold">{{ t('抖音') }}</strong> {{ t('预算的') }}
            <strong class="text-tertiary font-semibold">15%</strong> {{ t('重新分配给') }}
            <strong>{{ t('GEO搜索广告') }}</strong
            >{{ t('，预计可提升整体 ROI 约 8.5%。') }}
          </p>
        </div>
        <div class="shrink-0 flex items-center">
          <button
            class="px-6 py-2.5 bg-tertiary text-on-tertiary rounded-lg hover:bg-tertiary-container hover:text-on-tertiary-container transition-colors text-label-lg font-label-lg shadow-sm font-semibold flex items-center gap-2"
          >
            {{ t('一键分配') }}
            <span class="material-symbols-outlined text-[18px]">arrow_forward</span>
          </button>
        </div>
      </div>
      <!-- Dashboard Grid -->
      <div class="grid grid-cols-12 gap-gutter mb-8">
        <!-- Main Chart: Spent vs Revenue (Col Span 8) -->
        <div
          class="col-span-12 lg:col-span-8 bg-surface border border-outline-variant rounded-xl p-6 shadow-[0_4px_12px_rgba(0,0,0,0.02)] flex flex-col"
        >
          <div class="flex justify-between items-center mb-6">
            <h2 class="text-headline-md font-headline-md text-on-surface">
              {{ t('各渠道支出与收益对比') }}
            </h2>
            <div class="flex items-center gap-4 text-label-lg font-label-lg">
              <div class="flex items-center gap-1.5 text-on-surface-variant">
                <div class="w-3 h-3 rounded-full bg-primary/30"></div>
                {{ t('营销支出 (¥)') }}
              </div>
              <div class="flex items-center gap-1.5 text-on-surface-variant">
                <div class="w-3 h-3 rounded-full bg-primary"></div>
                {{ t('净收益 (¥)') }}
              </div>
            </div>
          </div>
          <!-- CSS Bar Chart Canvas -->
          <div
            class="flex-1 relative min-h-[300px] mt-4 flex items-end justify-around border-b border-outline-variant pb-2"
          >
            <!-- Y-Axis Ticks (Decorative) -->
            <div
              class="absolute left-0 top-0 bottom-0 w-full flex flex-col justify-between pointer-events-none z-0"
            >
              <template v-for="(item, i) in rows" :key="i"
                ><div :class="item.cls" v-html="item.raw"></div
              ></template>
            </div>
            <!-- Data Group: Ctrip -->
            <div class="relative z-10 flex flex-col items-center gap-2 group w-1/5">
              <div class="flex items-end gap-1.5 h-[260px] w-full justify-center">
                <div
                  class="w-6 bg-primary/30 rounded-t-sm h-[35%] transition-all duration-300 hover:opacity-80"
                  :title="t('支出: ¥35,000')"
                ></div>
                <div
                  class="w-6 bg-primary rounded-t-sm h-[85%] transition-all duration-300 hover:opacity-80 relative"
                  :title="t('收益: ¥85,000')"
                >
                  <div
                    class="absolute -top-6 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-inverse-surface text-inverse-on-surface text-[11px] py-1 px-2 rounded font-num-md whitespace-nowrap shadow-md z-20 pointer-events-none"
                  >
                    ROI: 2.4x
                  </div>
                </div>
              </div>
              <span class="text-label-lg font-label-lg text-on-surface mt-2">{{
                t('携程 (Ctrip)')
              }}</span>
            </div>
            <!-- Data Group: Meituan -->
            <div class="relative z-10 flex flex-col items-center gap-2 group w-1/5">
              <div class="flex items-end gap-1.5 h-[260px] w-full justify-center">
                <div
                  class="w-6 bg-primary/30 rounded-t-sm h-[40%] transition-all duration-300 hover:opacity-80"
                  :title="t('支出: ¥40,000')"
                ></div>
                <div
                  class="w-6 bg-primary rounded-t-sm h-[70%] transition-all duration-300 hover:opacity-80 relative"
                  :title="t('收益: ¥70,000')"
                >
                  <div
                    class="absolute -top-6 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-inverse-surface text-inverse-on-surface text-[11px] py-1 px-2 rounded font-num-md whitespace-nowrap shadow-md z-20 pointer-events-none"
                  >
                    ROI: 1.75x
                  </div>
                </div>
              </div>
              <span class="text-label-lg font-label-lg text-on-surface mt-2">{{
                t('美团 (Meituan)')
              }}</span>
            </div>
            <!-- Data Group: Douyin -->
            <div class="relative z-10 flex flex-col items-center gap-2 group w-1/5">
              <div class="flex items-end gap-1.5 h-[260px] w-full justify-center relative">
                <!-- Warning indicator for Douyin -->
                <div
                  class="absolute top-0 right-4 flex items-center justify-center w-6 h-6 rounded-full bg-error-container text-on-error-container shadow-sm animate-bounce"
                  :title="t('效率下滑，需调整')"
                >
                  <span class="material-symbols-outlined text-[14px]">warning</span>
                </div>
                <div
                  class="w-6 bg-primary/30 rounded-t-sm h-[60%] transition-all duration-300 hover:opacity-80"
                  :title="t('支出: ¥60,000')"
                ></div>
                <div
                  class="w-6 bg-primary rounded-t-sm h-[65%] transition-all duration-300 hover:opacity-80 relative"
                  :title="t('收益: ¥65,000')"
                >
                  <div
                    class="absolute -top-6 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-inverse-surface text-inverse-on-surface text-[11px] py-1 px-2 rounded font-num-md whitespace-nowrap shadow-md z-20 pointer-events-none"
                  >
                    ROI: 1.08x
                  </div>
                </div>
              </div>
              <span class="text-label-lg font-label-lg text-on-surface mt-2">{{
                t('抖音 (Douyin)')
              }}</span>
            </div>
            <!-- Data Group: WeChat -->
            <div class="relative z-10 flex flex-col items-center gap-2 group w-1/5">
              <div class="flex items-end gap-1.5 h-[260px] w-full justify-center">
                <div
                  class="w-6 bg-primary/30 rounded-t-sm h-[15%] transition-all duration-300 hover:opacity-80"
                  :title="t('支出: ¥15,000')"
                ></div>
                <div
                  class="w-6 bg-primary rounded-t-sm h-[45%] transition-all duration-300 hover:opacity-80 relative"
                  :title="t('收益: ¥45,000')"
                >
                  <div
                    class="absolute -top-6 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-inverse-surface text-inverse-on-surface text-[11px] py-1 px-2 rounded font-num-md whitespace-nowrap shadow-md z-20 pointer-events-none"
                  >
                    ROI: 3.0x
                  </div>
                </div>
              </div>
              <span class="text-label-lg font-label-lg text-on-surface mt-2">{{
                t('微信 (WeChat)')
              }}</span>
            </div>
          </div>
        </div>
        <!-- Efficiency Rank Leaderboard (Col Span 4) -->
        <div
          class="col-span-12 lg:col-span-4 bg-surface border border-outline-variant rounded-xl p-6 shadow-[0_4px_12px_rgba(0,0,0,0.02)] flex flex-col"
        >
          <div class="flex justify-between items-center mb-6">
            <h2 class="text-headline-md font-headline-md text-on-surface">
              {{ t('渠道效率排行 (Efficiency Rank)') }}
            </h2>
            <span
              class="material-symbols-outlined text-on-surface-variant cursor-help"
              :title="t('按扣除佣金和营销支出后的净利润率排序')"
              >info</span
            >
          </div>
          <div class="flex-1 flex flex-col gap-3">
            <!-- Rank 1 -->
            <div
              class="flex items-center p-3 rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors group"
            >
              <div
                class="w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center font-num-md font-bold shrink-0 shadow-sm"
              >
                1
              </div>
              <div class="ml-3 flex-1">
                <div class="text-label-lg font-label-lg text-on-surface font-bold">
                  {{ t('微信私域 (WeChat)') }}
                </div>
                <div class="text-[12px] text-on-surface-variant">{{ t('高复购, 低佣金') }}</div>
              </div>
              <div class="text-right">
                <div class="text-num-xl font-num-xl text-primary text-[20px]">42.5%</div>
                <div class="text-[11px] text-[#006837] flex items-center justify-end gap-0.5">
                  <span class="material-symbols-outlined text-[12px]">trending_up</span> +2.1%
                </div>
              </div>
            </div>
            <!-- Rank 2 -->
            <div
              class="flex items-center p-3 rounded-lg border border-outline-variant/50 hover:bg-surface-container-lowest transition-colors"
            >
              <div
                class="w-8 h-8 rounded-full border-2 border-outline-variant text-on-surface-variant flex items-center justify-center font-num-md font-bold shrink-0"
              >
                2
              </div>
              <div class="ml-3 flex-1">
                <div class="text-label-lg font-label-lg text-on-surface font-bold">
                  {{ t('携程 (Ctrip)') }}
                </div>
                <div class="text-[12px] text-on-surface-variant">{{ t('稳定流量基盘') }}</div>
              </div>
              <div class="text-right">
                <div class="text-num-md font-num-md text-on-surface text-[18px] font-bold">
                  28.0%
                </div>
                <div
                  class="text-[11px] text-on-surface-variant flex items-center justify-end gap-0.5"
                >
                  <span class="material-symbols-outlined text-[12px]">horizontal_rule</span>
                  {{ t('持平') }}
                </div>
              </div>
            </div>
            <!-- Rank 3 -->
            <div
              class="flex items-center p-3 rounded-lg border border-outline-variant/50 hover:bg-surface-container-lowest transition-colors"
            >
              <div
                class="w-8 h-8 rounded-full border-2 border-outline-variant text-on-surface-variant flex items-center justify-center font-num-md font-bold shrink-0"
              >
                3
              </div>
              <div class="ml-3 flex-1">
                <div class="text-label-lg font-label-lg text-on-surface font-bold">
                  {{ t('美团 (Meituan)') }}
                </div>
                <div class="text-[12px] text-on-surface-variant">{{ t('周末效应显著') }}</div>
              </div>
              <div class="text-right">
                <div class="text-num-md font-num-md text-on-surface text-[18px] font-bold">
                  22.4%
                </div>
                <div class="text-[11px] text-error flex items-center justify-end gap-0.5">
                  <span class="material-symbols-outlined text-[12px]">trending_down</span> -1.5%
                </div>
              </div>
            </div>
            <!-- Rank 4 -->
            <div
              class="flex items-center p-3 rounded-lg border border-error/30 bg-error-container/10 hover:bg-error-container/20 transition-colors mt-auto"
            >
              <div
                class="w-8 h-8 rounded-full border-2 border-error/50 text-error flex items-center justify-center font-num-md font-bold shrink-0"
              >
                4
              </div>
              <div class="ml-3 flex-1">
                <div class="text-label-lg font-label-lg text-on-surface font-bold">
                  {{ t('抖音 (Douyin)') }}
                </div>
                <div class="text-[12px] text-error flex items-center gap-1">
                  <span class="material-symbols-outlined text-[12px]">warning</span>
                  {{ t('转化成本攀升') }}
                </div>
              </div>
              <div class="text-right">
                <div class="text-num-md font-num-md text-error text-[18px] font-bold">8.2%</div>
                <div class="text-[11px] text-error flex items-center justify-end gap-0.5">
                  <span class="material-symbols-outlined text-[12px]">trending_down</span> -5.4%
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- ROI Trend Line Chart (Full Width) -->
      <div
        class="bg-surface border border-outline-variant rounded-xl p-6 shadow-[0_4px_12px_rgba(0,0,0,0.02)]"
      >
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-headline-md font-headline-md text-on-surface">
            {{ t('历史营销效率趋势 (ROI Trend)') }}
          </h2>
          <div class="bg-surface-container-low rounded-lg p-1 flex">
            <button
              class="px-3 py-1 text-label-sm rounded bg-surface shadow-sm text-on-surface font-semibold"
            >
              {{ t('日') }}
            </button>
            <button
              class="px-3 py-1 text-label-sm rounded text-on-surface-variant hover:text-on-surface"
            >
              {{ t('周') }}
            </button>
            <button
              class="px-3 py-1 text-label-sm rounded text-on-surface-variant hover:text-on-surface"
            >
              {{ t('月') }}
            </button>
          </div>
        </div>
        <!-- Mock Line Chart via SVG -->
        <div class="w-full h-[240px] relative">
          <!-- Grid Lines -->
          <svg class="absolute inset-0 w-full h-full" preserveaspectratio="none">
            <line
              stroke="#e1e3e4"
              stroke-dasharray="4"
              stroke-width="1"
              x1="0"
              x2="100%"
              y1="20%"
              y2="20%"
            ></line>
            <line
              stroke="#e1e3e4"
              stroke-dasharray="4"
              stroke-width="1"
              x1="0"
              x2="100%"
              y1="50%"
              y2="50%"
            ></line>
            <line
              stroke="#e1e3e4"
              stroke-dasharray="4"
              stroke-width="1"
              x1="0"
              x2="100%"
              y1="80%"
              y2="80%"
            ></line>
            <!-- Area Gradient -->
            <defs>
              <lineargradient id="areaGradient" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#005bbf" stop-opacity="0.2"></stop>
                <stop offset="100%" stop-color="#005bbf" stop-opacity="0"></stop>
              </lineargradient>
            </defs>
            <!-- Smooth Trend Line with Area -->
            <path
              d="M0,200 C100,180 200,120 300,140 C400,160 500,80 600,90 C700,100 800,40 900,50 C1000,60 1100,120 1200,100 L1200,240 L0,240 Z"
              fill="url(#areaGradient)"
            ></path>
            <path
              d="M0,200 C100,180 200,120 300,140 C400,160 500,80 600,90 C700,100 800,40 900,50 C1000,60 1100,120 1200,100"
              fill="none"
              stroke="#005bbf"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="3"
            ></path>
            <!-- Data Points -->
            <circle
              class="hover:r-6 transition-all cursor-pointer"
              cx="300"
              cy="140"
              fill="#ffffff"
              r="4"
              stroke="#005bbf"
              stroke-width="2"
            ></circle>
            <circle
              class="hover:r-6 transition-all cursor-pointer"
              cx="600"
              cy="90"
              fill="#ffffff"
              r="4"
              stroke="#005bbf"
              stroke-width="2"
            ></circle>
            <circle
              class="animate-pulse cursor-pointer"
              cx="900"
              cy="50"
              fill="#ffffff"
              r="6"
              stroke="#8c33b3"
              stroke-width="3"
            ></circle>
            <!-- Highlighted point -->
          </svg>
          <!-- X-Axis Labels (Mock) -->
          <div
            class="absolute bottom-[-24px] left-0 w-full flex justify-between text-on-surface-variant text-[12px] font-num-md px-2"
          >
            <span>10/01</span>
            <span>10/08</span>
            <span>10/15</span>
            <span>10/22</span>
            <span>{{ t('今日') }}</span>
          </div>
          <!-- Tooltip Simulation for Highlighted Point -->
          <div
            class="absolute top-[20px] right-[25%] bg-inverse-surface text-inverse-on-surface p-3 rounded-lg shadow-lg pointer-events-none border border-outline-variant/20"
          >
            <div class="text-[12px] opacity-80 mb-1">{{ t('10月22日') }}</div>
            <div class="font-num-md font-bold text-[16px]">{{ t('综合 ROI: 2.1x') }}</div>
            <div class="text-[11px] text-tertiary-fixed-dim mt-1 flex items-center gap-1">
              <span class="material-symbols-outlined text-[14px]">auto_awesome</span>
              {{ t('AI 调价介入点') }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 原型自定义工具类（v-html 内联卡片的根节点由 Vue 渲染，可命中） */
.ai-glow {
  box-shadow: 0 0 15px rgba(140, 51, 179, 0.15);
  border-left: 2px solid #8c33b3;
}
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
