<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// 酒店上下文（固定为 1 号店）
const hotelId = 1
// seed 保留原型示例卡片，保证 1:1 视觉；onMounted 后由真实接口数据覆盖
const seed: any[] = [
  {
    id: 0,
    cls: 'col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant blur-card',
    raw: '\n<div class="flex justify-between items-center mb-6">\n<h3 class="font-headline-md text-headline-md text-on-surface">LTV Distribution by Segment</h3>\n<select class="bg-surface-container text-on-surface border-none rounded-md text-sm font-label-lg py-1 px-3 focus:ring-primary">\n<option>Last 12 Months</option>\n<option>YTD</option>\n<option>All Time</option>\n</select>\n</div>\n<div class="h-80 w-full relative">\n<canvas id="ltvChart"></canvas>\n</div>\n',
  },
  {
    id: 1,
    cls: 'col-span-12 lg:col-span-4 bg-surface-container-lowest rounded-xl p-6 border-l-4 border-l-tertiary border-y border-r border-y-outline-variant border-r-outline-variant blur-card relative overflow-hidden',
    raw: '\n<div class="absolute top-0 right-0 p-4 opacity-10">\n<span class="material-symbols-outlined text-8xl text-tertiary">psychiatry</span>\n</div>\n<div class="flex items-center gap-2 mb-4 relative z-10">\n<span class="material-symbols-outlined text-tertiary">arrow_back_ios_new</span>\n<h3 class="font-headline-md text-headline-md text-on-surface">AI Insights & Predictions</h3>\n</div>\n<div class="space-y-4 relative z-10">\n<div class="p-4 bg-tertiary/5 rounded-lg border border-tertiary/20">\n<p class="font-label-lg text-label-lg text-tertiary mb-1">Predicted High-Value Segment</p>\n<h4 class="font-headline-lg text-headline-lg text-on-surface mb-2">Corporate Leisure (Bleisure)</h4>\n<p class="font-body-md text-body-md text-on-surface-variant text-sm">Based on recent booking patterns, guests blending business trips with weekend stays show a 42% higher projected LTV than standard corporate accounts.</p>\n</div>\n<div class="p-4 bg-surface-container-low rounded-lg border border-outline-variant">\n<p class="font-label-lg text-label-lg text-on-surface-variant mb-1">Retention Risk Alert</p>\n<div class="flex items-start gap-3">\n<span class="material-symbols-outlined text-error mt-0.5">warning</span>\n<p class="font-body-md text-body-md text-on-surface text-sm">VIP segment retention dropped 3% in Q3. AI suggests offering personalized wellness packages to re-engage top spenders.</p>\n</div>\n</div>\n</div>\n',
  },
  {
    id: 2,
    cls: 'col-span-12 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant blur-card mt-4',
    raw: '\n<div class="flex justify-between items-center mb-6">\n<h3 class="font-headline-md text-headline-md text-on-surface">Retention Cohort Analysis</h3>\n<div class="flex gap-2">\n<span class="px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-label-lg">3 Months</span>\n<span class="px-3 py-1 bg-surface-container text-on-surface-variant rounded-full text-xs font-label-lg">6 Months</span>\n<span class="px-3 py-1 bg-surface-container text-on-surface-variant rounded-full text-xs font-label-lg">12 Months</span>\n</div>\n</div>\n<div class="overflow-x-auto">\n<table class="w-full text-left border-collapse">\n<thead>\n<tr class="border-b border-outline-variant">\n<th class="py-3 px-4 font-label-lg text-on-surface-variant">Acquisition Month</th>\n<th class="py-3 px-4 font-label-lg text-on-surface-variant">New Guests</th>\n<th class="py-3 px-4 font-label-lg text-on-surface-variant">M1</th>\n<th class="py-3 px-4 font-label-lg text-on-surface-variant">M2</th>\n<th class="py-3 px-4 font-label-lg text-on-surface-variant">M3</th>\n</tr>\n</thead>\n<tbody class="font-num-md text-sm">\n<!-- Simulated Heatmap Rows -->\n<tr class="border-b border-outline-variant/50">\n<td class="py-3 px-4 text-on-surface">Jan 2024</td>\n<td class="py-3 px-4 text-on-surface">450</td>\n<td class="py-3 px-4 bg-primary/40 text-on-primary-fixed">24%</td>\n<td class="py-3 px-4 bg-primary/30 text-on-primary-fixed">18%</td>\n<td class="py-3 px-4 bg-primary/20 text-on-primary-fixed">12%</td>\n</tr>\n<tr class="border-b border-outline-variant/50">\n<td class="py-3 px-4 text-on-surface">Feb 2024</td>\n<td class="py-3 px-4 text-on-surface">380</td>\n<td class="py-3 px-4 bg-primary/35 text-on-primary-fixed">21%</td>\n<td class="py-3 px-4 bg-primary/25 text-on-primary-fixed">15%</td>\n<td class="py-3 px-4 bg-primary/15 text-on-primary-fixed">10%</td>\n</tr>\n<tr>\n<td class="py-3 px-4 text-on-surface">Mar 2024</td>\n<td class="py-3 px-4 text-on-surface">520</td>\n<td class="py-3 px-4 bg-primary/45 text-on-primary-fixed">28%</td>\n<td class="py-3 px-4 bg-primary/30 text-on-primary-fixed">17%</td>\n<td class="py-3 px-4 bg-surface-container-low text-on-surface-variant">-</td>\n</tr>\n</tbody>\n</table>\n</div>\n',
  },
  {
    id: 3,
    cls: 'col-span-12 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant blur-card mt-4',
    raw: '\n<h3 class="font-headline-md text-headline-md text-on-surface mb-6">Top High-Contribution Guests (AI Ranked)</h3>\n<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">\n<!-- Guest Card 1 -->\n<div class="p-4 border border-outline-variant rounded-lg hover:border-primary transition-colors cursor-pointer group">\n<div class="flex justify-between items-start mb-3">\n<div class="flex items-center gap-3">\n<div class="w-10 h-10 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-headline-md">\n                                    JW\n                                </div>\n<div>\n<h4 class="font-label-lg text-on-surface group-hover:text-primary transition-colors">Johnathan Wu</h4>\n<span class="text-xs font-label-lg text-tertiary bg-tertiary/10 px-2 py-0.5 rounded">VIP - Corporate</span>\n</div>\n</div>\n<span class="material-symbols-outlined text-outline-variant">more_vert</span>\n</div>\n<div class="grid grid-cols-2 gap-2 mt-4">\n<div>\n<p class="text-xs text-on-surface-variant font-label-lg">Historical Revenue</p>\n<p class="font-num-md text-on-surface">¥45,200</p>\n</div>\n<div>\n<p class="text-xs text-on-surface-variant font-label-lg flex items-center gap-1">\n                                    Predicted Future <span class="material-symbols-outlined text-[12px] text-tertiary">arrow_back_ios_new</span>\n</p>\n<p class="font-num-md text-tertiary">¥28,500 <span class="text-xs text-on-surface-variant font-body-md">(Nxt 12M)</span></p>\n</div>\n</div>\n</div>\n<!-- Guest Card 2 -->\n<div class="p-4 border border-outline-variant rounded-lg hover:border-primary transition-colors cursor-pointer group">\n<div class="flex justify-between items-start mb-3">\n<div class="flex items-center gap-3">\n<div class="w-10 h-10 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-headline-md">\n                                    SL\n                                </div>\n<div>\n<h4 class="font-label-lg text-on-surface group-hover:text-primary transition-colors">Sarah Lee</h4>\n<span class="text-xs font-label-lg text-primary bg-primary/10 px-2 py-0.5 rounded">Leisure Frequent</span>\n</div>\n</div>\n<span class="material-symbols-outlined text-outline-variant">more_vert</span>\n</div>\n<div class="grid grid-cols-2 gap-2 mt-4">\n<div>\n<p class="text-xs text-on-surface-variant font-label-lg">Historical Revenue</p>\n<p class="font-num-md text-on-surface">¥32,800</p>\n</div>\n<div>\n<p class="text-xs text-on-surface-variant font-label-lg flex items-center gap-1">\n                                    Predicted Future <span class="material-symbols-outlined text-[12px] text-tertiary">arrow_back_ios_new</span>\n</p>\n<p class="font-num-md text-tertiary">¥19,200 <span class="text-xs text-on-surface-variant font-body-md">(Nxt 12M)</span></p>\n</div>\n</div>\n</div>\n<!-- Guest Card 3 -->\n<div class="p-4 border border-outline-variant rounded-lg hover:border-primary transition-colors cursor-pointer group">\n<div class="flex justify-between items-start mb-3">\n<div class="flex items-center gap-3">\n<div class="w-10 h-10 rounded-full bg-surface-variant text-on-surface-variant flex items-center justify-center font-headline-md">\n                                    MC\n                                </div>\n<div>\n<h4 class="font-label-lg text-on-surface group-hover:text-primary transition-colors">Michael Chen</h4>\n<span class="text-xs font-label-lg text-secondary bg-secondary/10 px-2 py-0.5 rounded">Business</span>\n</div>\n</div>\n<span class="material-symbols-outlined text-outline-variant">more_vert</span>\n</div>\n<div class="grid grid-cols-2 gap-2 mt-4">\n<div>\n<p class="text-xs text-on-surface-variant font-label-lg">Historical Revenue</p>\n<p class="font-num-md text-on-surface">¥29,150</p>\n</div>\n<div>\n<p class="text-xs text-on-surface-variant font-label-lg flex items-center gap-1">\n                                    Predicted Future <span class="material-symbols-outlined text-[12px] text-tertiary">arrow_back_ios_new</span>\n</p>\n<p class="font-num-md text-tertiary">¥15,000 <span class="text-xs text-on-surface-variant font-body-md">(Nxt 12M)</span></p>\n</div>\n</div>\n</div>\n</div>\n',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('relation')
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-8 flex justify-between items-end">
      <div>
        <h2 class="font-display-lg text-display-lg text-on-surface mb-2">
          {{ t('客户终身价值 (LTV) 与复购分析') }}
        </h2>
        <p class="font-body-lg text-body-lg text-on-surface-variant">
          Analyze long-term revenue potential and guest retention patterns to optimize loyalty
          programs.
        </p>
      </div>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 border border-outline-variant text-on-surface rounded-lg font-label-lg hover:bg-surface-container-low transition-colors"
        >
          Export Report
        </button>
        <button
          class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg hover:bg-primary/90 transition-colors flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-sm">auto_awesome</span>
          Run AI Recalculation
        </button>
      </div>
    </div>
    <!-- Bento Grid Layout -->
    <div class="grid grid-cols-12 gap-gutter">
      <template v-for="(item, i) in rows" :key="i"
        ><div :class="item.cls" v-html="item.raw"></div
      ></template>
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
