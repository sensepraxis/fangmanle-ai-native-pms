<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'

// 酒店上下文（固定为 1 号店）
const hotelId = 1
// seed 保留原型示例卡片，保证 1:1 视觉；onMounted 后由真实接口数据覆盖
const seed: any[] = [
  {
    id: 0,
    cls: 'bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm flex flex-col justify-between',
    raw: '\n<div class="flex justify-between items-center mb-2">\n<span class="font-label-lg text-label-lg text-on-surface-variant">实际投资回报率 (Actual ROI)</span>\n<span class="material-symbols-outlined text-outline">show_chart</span>\n</div>\n<div class="flex items-baseline gap-2">\n<span class="font-num-xl text-display-lg text-on-surface tracking-tight">4.2x</span>\n<span class="text-sm font-medium text-green-700 bg-green-50 px-1.5 py-0.5 rounded border border-green-200">+12% vs 上周</span>\n</div>\n<p class="text-xs text-on-surface-variant mt-3">总消耗: ¥3,500 | 归因营收: ¥14,700</p>\n',
  },
  {
    id: 1,
    cls: 'bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm flex flex-col justify-between',
    raw: '\n<div class="flex justify-between items-center mb-2">\n<span class="font-label-lg text-label-lg text-on-surface-variant">预期投资回报率 (Forecast ROI)</span>\n<span class="material-symbols-outlined text-outline">monitoring</span>\n</div>\n<div class="flex items-baseline gap-2">\n<span class="font-num-xl text-display-lg text-on-surface-variant tracking-tight">3.8x</span>\n</div>\n<div class="w-full bg-surface-container-high h-1.5 rounded-full mt-4 overflow-hidden">\n<div class="bg-tertiary h-full rounded-full" style="width: 110%;"></div>\n</div>\n<p class="text-xs text-tertiary mt-2">实际表现超出 AI 预测 10.5%</p>\n',
  },
  {
    id: 2,
    cls: 'bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm flex flex-col justify-between',
    raw: '\n<div class="flex justify-between items-center mb-2">\n<span class="font-label-lg text-label-lg text-on-surface-variant">GEO 归因订单量 (Bookings)</span>\n<span class="material-symbols-outlined text-outline">book_online</span>\n</div>\n<div class="flex items-baseline gap-2">\n<span class="font-num-xl text-display-lg text-on-surface tracking-tight">86</span>\n<span class="text-sm font-medium text-on-surface">单</span>\n</div>\n<div class="flex items-center gap-2 mt-3">\n<div class="flex -space-x-2">\n<div class="w-6 h-6 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center text-[10px] font-bold border-2 border-surface-container-lowest z-30">新</div>\n<div class="w-6 h-6 rounded-full bg-surface-container-high border-2 border-surface-container-lowest z-20"></div>\n<div class="w-6 h-6 rounded-full bg-surface-container border-2 border-surface-container-lowest z-10"></div>\n</div>\n<span class="text-xs text-on-surface-variant">其中新客占比 65%</span>\n</div>\n',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('geo-roi')
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="geo" /></div>
    <!-- Header -->
    <div class="mb-6 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface">{{ t('GEO 效果归因看板') }}</h1>
        <p class="font-body-md text-body-md text-on-surface-variant mt-1">
          LBS Marketing Performance &amp; ROI Analysis
        </p>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-sm text-on-surface-variant">{{ t('统计周期:') }}</span>
        <button
          class="flex items-center gap-2 px-3 py-1.5 border border-outline-variant rounded bg-surface-container-lowest text-on-surface text-sm font-medium hover:bg-surface-container transition-colors"
        >
          {{ t('本周 (This Week)') }}
          <span class="material-symbols-outlined text-sm">arrow_drop_down</span>
        </button>
      </div>
    </div>
    <!-- AI Insight Banner (R0 - Info) -->
    <div
      class="mb-8 bg-primary-fixed rounded-lg p-4 flex items-start gap-3 border-l-4 border-primary shadow-sm"
    >
      <span class="material-symbols-outlined text-primary mt-0.5" data-icon="auto_awesome"
        >auto_awesome</span
      >
      <div>
        <h3 class="font-label-lg text-label-lg text-on-primary-fixed-variant font-bold">
          {{ t('AI Insight / 智能洞察') }}
        </h3>
        <p class="font-body-md text-body-md text-on-primary-fixed font-medium mt-1">
          {{ t('火车站投放贡献了本周30%的新客。')
          }}<span class="font-normal text-on-primary-fixed-variant ml-2">{{
            t('建议在即将到来的周末高峰期维持该区域的预算竞价，预期可带来额外15%转化提升。')
          }}</span>
        </p>
      </div>
    </div>
    <!-- KPI Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-gutter mb-8">
      <template v-for="(item, i) in rows" :key="i"
        ><div :class="item.cls" v-html="item.raw"></div
      ></template>
    </div>
    <!-- Detailed Analysis Layout -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
      <!-- Conversion Funnel (Span 7) -->
      <div
        class="lg:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
      >
        <div class="flex items-center justify-between mb-6">
          <h2 class="font-headline-md text-headline-md text-on-surface">
            {{ t('转化漏斗 (Conversion Funnel)') }}
          </h2>
          <button class="text-primary text-sm font-medium hover:underline flex items-center">
            {{ t('导出明细') }} <span class="material-symbols-outlined text-sm ml-1">download</span>
          </button>
        </div>
        <div class="flex flex-col gap-4 mt-8 relative">
          <!-- Step 1: Impression -->
          <div class="relative z-10 flex items-center">
            <div class="w-1/3 text-right pr-6 font-label-lg text-on-surface-variant">
              {{ t('曝光 (Impression)') }}
            </div>
            <div class="w-2/3">
              <div
                class="h-10 bg-primary-fixed rounded-r-lg flex items-center px-4"
                style="width: 100%"
              >
                <span class="font-num-md text-on-primary-fixed-variant font-bold">125,000</span>
              </div>
            </div>
          </div>
          <!-- Connector -->
          <div
            class="absolute left-1/3 top-10 bottom-4 w-px bg-outline-variant -ml-px opacity-50 z-0"
          ></div>
          <!-- Step 2: Click -->
          <div class="relative z-10 flex items-center">
            <div class="w-1/3 text-right pr-6 font-label-lg text-on-surface-variant">
              {{ t('点击 (Click)') }}
              <div class="text-xs text-outline mt-0.5">CTR: 4.2%</div>
            </div>
            <div class="w-2/3">
              <div
                class="h-10 bg-primary-fixed-dim rounded-r-lg flex items-center px-4 transition-all hover:bg-primary-fixed cursor-default"
                style="width: 65%"
              >
                <span class="font-num-md text-on-primary-fixed-variant font-bold">5,250</span>
              </div>
            </div>
          </div>
          <!-- Step 3: Visit -->
          <div class="relative z-10 flex items-center">
            <div class="w-1/3 text-right pr-6 font-label-lg text-on-surface-variant">
              {{ t('到店 (Visit)') }}
              <div class="text-xs text-outline mt-0.5">{{ t('转化率: 8.5%') }}</div>
            </div>
            <div class="w-2/3">
              <div
                class="h-10 bg-primary-container rounded-r-lg flex items-center px-4 transition-all"
                style="width: 40%"
              >
                <span class="font-num-md text-on-primary-container font-bold">446</span>
              </div>
            </div>
          </div>
          <!-- Step 4: Booking -->
          <div class="relative z-10 flex items-center mt-2">
            <div class="w-1/3 text-right pr-6">
              <div class="font-label-lg text-primary font-bold">{{ t('预订 (Booking)') }}</div>
              <div class="text-xs text-primary mt-0.5">{{ t('最终转化: 19.2%') }}</div>
            </div>
            <div class="w-2/3">
              <div
                class="h-12 bg-primary rounded-r-lg flex items-center px-4 shadow-sm"
                style="width: 20%"
              >
                <span class="font-num-md text-on-primary font-bold text-lg">86</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- Traffic Source Breakdown (Span 5) -->
      <div
        class="lg:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
      >
        <h2 class="font-headline-md text-headline-md text-on-surface mb-6">
          {{ t('流量来源拆解 (Traffic Sources)') }}
        </h2>
        <div class="space-y-6">
          <!-- Source: Baidu -->
          <div>
            <div class="flex justify-between items-center mb-2">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-primary text-xl">map</span>
                <span class="font-label-lg text-on-surface">{{ t('百度地图 (Baidu Maps)') }}</span>
              </div>
              <span class="font-num-md text-on-surface font-semibold">45%</span>
            </div>
            <div class="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
              <div class="bg-primary h-full rounded-full" style="width: 45%"></div>
            </div>
            <div class="flex justify-between text-xs text-on-surface-variant mt-1">
              <span>{{ t('转化订单: 39单') }}</span>
              <span>ROI: 4.5x</span>
            </div>
          </div>
          <!-- Source: Amap -->
          <div>
            <div class="flex justify-between items-center mb-2">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-secondary text-xl">navigation</span>
                <span class="font-label-lg text-on-surface">{{ t('高德地图 (Amap)') }}</span>
              </div>
              <span class="font-num-md text-on-surface font-semibold">32%</span>
            </div>
            <div class="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
              <div class="bg-secondary h-full rounded-full" style="width: 32%"></div>
            </div>
            <div class="flex justify-between text-xs text-on-surface-variant mt-1">
              <span>{{ t('转化订单: 27单') }}</span>
              <span>ROI: 3.9x</span>
            </div>
          </div>
          <!-- Source: Meituan LBS -->
          <div>
            <div class="flex justify-between items-center mb-2">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-tertiary text-xl">storefront</span>
                <span class="font-label-lg text-on-surface">{{ t('美团LBS (Meituan)') }}</span>
              </div>
              <span class="font-num-md text-on-surface font-semibold">23%</span>
            </div>
            <div class="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
              <div class="bg-tertiary h-full rounded-full" style="width: 23%"></div>
            </div>
            <div class="flex justify-between text-xs text-on-surface-variant mt-1">
              <span>{{ t('转化订单: 20单') }}</span>
              <span>ROI: 4.1x</span>
            </div>
          </div>
        </div>
        <!-- AI Tinge Optimization Tip -->
        <div
          class="mt-6 p-3 bg-surface border-l-2 border-tertiary rounded-r text-sm text-on-surface-variant"
        >
          <span class="font-bold text-tertiary">{{ t('优化建议:') }}</span>
          {{ t('美团LBS本周转化成本上升，建议将10%预算倾斜至转化率更高的百度地图本地服务版块。') }}
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
