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
    cls: 'bg-surface p-2 rounded-lg shadow-sm border border-outline-variant text-on-surface hover:bg-surface-container transition-colors',
    raw: '\n<span class="material-symbols-outlined" data-icon="add">add</span>\n',
  },
  {
    id: 1,
    cls: 'bg-surface p-2 rounded-lg shadow-sm border border-outline-variant text-on-surface hover:bg-surface-container transition-colors',
    raw: '\n<span class="material-symbols-outlined" data-icon="remove">remove</span>\n',
  },
  {
    id: 2,
    cls: 'bg-surface p-2 rounded-lg shadow-sm border border-outline-variant text-on-surface hover:bg-surface-container transition-colors mt-2',
    raw: '\n<span class="material-symbols-outlined" data-icon="my_location">my_location</span>\n',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('competitor')
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="ota" /></div>
    <!-- Header Section -->
    <div
      class="px-container-padding py-4 flex justify-between items-end shrink-0 bg-surface z-10 border-b border-surface-container"
    >
      <div>
        <div class="flex items-center gap-2 text-on-surface-variant mb-1">
          <span class="font-label-lg text-label-lg">GEO Workflow</span>
          <span class="material-symbols-outlined text-sm">chevron_right</span>
          <span class="font-label-lg text-label-lg text-primary">{{ t('商圈竞争分析') }}</span>
        </div>
        <h1 class="text-headline-lg font-headline-lg text-on-surface">
          {{ t('竞品组 (Competitor Set) 分析') }}
        </h1>
      </div>
      <!-- AI Insight Banner (R0 Info) -->
      <div
        class="bg-primary-fixed border-l-4 border-primary p-3 rounded-r-lg max-w-md flex gap-3 items-start shadow-sm"
      >
        <span class="material-symbols-outlined text-primary shrink-0" data-icon="auto_awesome"
          >auto_awesome</span
        >
        <div>
          <p class="font-body-md text-body-md text-on-primary-fixed text-sm">
            <strong class="font-bold">{{ t('AI 洞察:') }}</strong>
            {{ t('您在火车站商圈的曝光率比竞对A低15%。') }}
          </p>
        </div>
      </div>
    </div>
    <!-- Dashboard Layout -->
    <div class="flex-1 flex overflow-hidden p-gutter gap-gutter">
      <!-- Left Panel: Map View -->
      <div
        class="flex-1 bg-surface rounded-xl border border-outline-variant overflow-hidden flex flex-col shadow-sm relative"
      >
        <!-- Map Header -->
        <div
          class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-lowest z-10 absolute top-0 w-full"
        >
          <h2 class="font-headline-md text-headline-md text-on-surface">{{ t('商圈地图') }}</h2>
          <div class="flex gap-2">
            <span
              class="inline-flex items-center gap-1 px-3 py-1 bg-surface-container rounded-full text-label-lg font-label-lg text-on-surface-variant"
            >
              <span class="w-2 h-2 rounded-full bg-primary"></span>
              {{ t('本店') }}</span
            >
            <span
              class="inline-flex items-center gap-1 px-3 py-1 bg-surface-container rounded-full text-label-lg font-label-lg text-on-surface-variant"
            >
              <span class="w-2 h-2 rounded-full bg-error"></span>
              {{ t('竞对A') }}</span
            >
            <span
              class="inline-flex items-center gap-1 px-3 py-1 bg-surface-container rounded-full text-label-lg font-label-lg text-on-surface-variant"
            >
              <span class="w-2 h-2 rounded-full bg-tertiary"></span>
              {{ t('竞对B') }}</span
            >
          </div>
        </div>
        <!-- Map Placeholder Image -->
        <div class="w-full h-full relative" data-location="Shanghai" style="">
          <img
            class="w-full h-full object-cover"
            data-alt="A stylized, clean UI map view of a modern city center like Shanghai, focusing on a train station district. The map should be light-themed with subtle blues, grays, and whites. There should be glowing markers indicating hotel locations, with one prominent blue marker for the main property and red/purple markers for competitors. The style is modern corporate, highly legible, and looks like a sophisticated data visualization dashboard."
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuB7F8M3TmIkOfN8U9jPWR21g7AHx36Y2Y8BOJDt1guizcTRhR-kmZNZSV5PZYFwR1SrG2M-b0q2wDFTpyfrSeOTPxuB4e7xcoqZ8e4D3xwuk9HczXRjcy84PFqE8VN5CcKFbduDWISgx6alCYR0RsKSvF-d38vmc-dHT8FMBugfuqZT3WNfvOjwv8736mspzT6PdrUjKVXJVxTqrgrxRkiRqMoqlbffQgxu6UHx1Cm6D7HeUnemPe4"
          />
          <!-- Overlay map controls -->
          <div class="absolute bottom-4 right-4 flex flex-col gap-2">
            <template v-for="(item, i) in rows" :key="i"
              ><div :class="item.cls" v-html="item.raw"></div
            ></template>
          </div>
        </div>
      </div>
      <!-- Right Panel: Data Analytics -->
      <div class="w-96 flex flex-col gap-gutter shrink-0 overflow-y-auto pb-gutter pr-2">
        <!-- Visibility Index Card -->
        <div class="bg-surface rounded-xl border border-outline-variant p-4 shadow-sm">
          <div class="flex justify-between items-center mb-4">
            <h3 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-primary" data-icon="visibility"
                >visibility</span
              >
              {{ t('曝光指数对比') }}
            </h3>
          </div>
          <div class="space-y-4">
            <!-- Hotel A -->
            <div>
              <div class="flex justify-between mb-1">
                <span class="font-label-lg text-label-lg text-on-surface">{{
                  t('竞对A (火车站前)')
                }}</span>
                <span class="font-num-md text-num-md text-on-surface">85%</span>
              </div>
              <div class="w-full bg-surface-container-highest rounded-full h-2">
                <div class="bg-error h-2 rounded-full" style="width: 85%"></div>
              </div>
            </div>
            <!-- Main Hotel -->
            <div>
              <div class="flex justify-between mb-1">
                <span class="font-label-lg text-label-lg text-primary font-bold">{{
                  t('本店')
                }}</span>
                <span class="font-num-md text-num-md text-primary font-bold">70%</span>
              </div>
              <div class="w-full bg-surface-container-highest rounded-full h-2">
                <div class="bg-primary h-2 rounded-full relative" style="width: 70%">
                  <!-- Missing 15% indicator -->
                  <div
                    class="absolute right-0 translate-x-full h-full border-b-2 border-dashed border-error w-[21%] opacity-50"
                  ></div>
                </div>
              </div>
              <p class="text-xs text-error mt-1 text-right">{{ t('-15% 缺口') }}</p>
            </div>
            <!-- Hotel B -->
            <div>
              <div class="flex justify-between mb-1">
                <span class="font-label-lg text-label-lg text-on-surface">{{
                  t('竞对B (东广场)')
                }}</span>
                <span class="font-num-md text-num-md text-on-surface">62%</span>
              </div>
              <div class="w-full bg-surface-container-highest rounded-full h-2">
                <div class="bg-tertiary h-2 rounded-full" style="width: 62%"></div>
              </div>
            </div>
          </div>
        </div>
        <!-- Price vs Distance Scatter Plot -->
        <div
          class="bg-surface rounded-xl border border-outline-variant p-4 shadow-sm flex-1 flex flex-col min-h-[300px]"
        >
          <div class="flex justify-between items-center mb-4">
            <h3 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-primary" data-icon="scatter_plot"
                >scatter_plot</span
              >
              {{ t('价格与距离分布') }}
            </h3>
          </div>
          <div class="flex-1 relative border-l border-b border-outline-variant ml-6 mb-6">
            <!-- Y Axis Label -->
            <div
              class="absolute -left-6 top-1/2 -translate-y-1/2 -rotate-90 text-xs text-on-surface-variant font-label-lg whitespace-nowrap"
            >
              {{ t('均价 (¥)') }}
            </div>
            <!-- X Axis Label -->
            <div
              class="absolute -bottom-6 left-1/2 -translate-x-1/2 text-xs text-on-surface-variant font-label-lg"
            >
              {{ t('距火车站距离 (km)') }}
            </div>
            <!-- Plot Points (Simulated) -->
            <div
              class="absolute bottom-[40%] left-[20%] w-4 h-4 bg-error rounded-full border-2 border-surface shadow-sm group cursor-help"
            >
              <div
                class="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-inverse-surface text-inverse-on-surface text-xs p-2 rounded whitespace-nowrap z-20"
              >
                {{ t('竞对A: ¥280, 0.5km') }}
              </div>
            </div>
            <!-- Main Hotel -->
            <div
              class="absolute bottom-[60%] left-[40%] w-5 h-5 bg-primary rounded-full border-2 border-surface shadow-md group cursor-help z-10"
            >
              <div class="absolute inset-0 bg-primary rounded-full animate-ping opacity-20"></div>
              <div
                class="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-inverse-surface text-inverse-on-surface text-xs p-2 rounded whitespace-nowrap z-20"
              >
                {{ t('本店: ¥350, 1.2km') }}
              </div>
            </div>
            <div
              class="absolute bottom-[30%] left-[60%] w-3 h-3 bg-tertiary rounded-full border-2 border-surface shadow-sm group cursor-help"
            >
              <div
                class="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-inverse-surface text-inverse-on-surface text-xs p-2 rounded whitespace-nowrap z-20"
              >
                {{ t('竞对B: ¥220, 1.8km') }}
              </div>
            </div>
            <!-- AI Trend Line Simulation -->
            <svg
              class="absolute inset-0 w-full h-full pointer-events-none opacity-30"
              preserveaspectratio="none"
            >
              <line
                stroke="#727785"
                stroke-dasharray="4 4"
                stroke-width="1"
                x1="0"
                x2="100%"
                y1="100%"
                y2="0"
              ></line>
            </svg>
          </div>
        </div>
        <!-- Action Section -->
        <div class="bg-surface rounded-xl border border-outline-variant p-4 shadow-sm mt-auto">
          <h4 class="font-label-lg text-label-lg text-on-surface mb-2">{{ t('推荐操作') }}</h4>
          <p class="text-sm text-on-surface-variant mb-4">
            {{ t('通过针对性投放，预计可夺回 8-12% 的火车站商圈流量。') }}
          </p>
          <button
            class="w-full bg-primary hover:bg-surface-tint text-on-primary font-label-lg text-label-lg py-3 px-4 rounded-full transition-colors flex justify-center items-center gap-2 shadow-sm active:scale-95"
          >
            <span class="material-symbols-outlined text-sm" data-icon="campaign">campaign</span>
            {{ t('创建针对性投放') }}
          </button>
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
