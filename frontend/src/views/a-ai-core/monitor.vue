<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// 数据来源：后端 demo 接口（确定性种子数据），实体 = ai-engine
// 列表/表格通过 v-for 渲染 rows；字段缺失时回退原型示例值，保证版式 1:1。
const hotelId = 1
const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('ai-engine')
})
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto space-y-6">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface mb-2">
            {{ t('系统监控与AI性能') }}
          </h1>
          <p class="text-on-surface-variant">{{ t('实时健康状态及智能引擎效能追踪') }}</p>
        </div>
        <div class="flex items-center gap-3">
          <span
            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-low border border-outline-variant text-label-lg font-label-lg text-on-surface-variant"
          >
            <span class="w-2 h-2 rounded-full bg-primary"></span>
            {{ t('系统运行正常') }}</span
          >
          <span
            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-tertiary-fixed border border-tertiary-container text-label-lg font-label-lg text-on-tertiary-fixed"
          >
            <span class="material-symbols-outlined text-[16px] text-tertiary"
              >arrow_back_ios_new</span
            >
            {{ t('AI 引擎活跃') }}</span
          >
        </div>
      </div>
      <!-- Bento Grid Layout -->
      <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        <!-- KPI Card 1: Demand Forecast -->
        <div
          class="col-span-1 md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-[0_4px_12px_rgba(0,0,0,0.03)] hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)] transition-shadow"
        >
          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center gap-2 text-on-surface-variant">
              <span class="material-symbols-outlined text-primary">monitoring</span>
              <h3 class="font-headline-md text-headline-md">{{ t('需求预测准确率') }}</h3>
            </div>
            <span class="material-symbols-outlined text-outline">info</span>
          </div>
          <div class="flex items-end gap-3 mb-2">
            <span class="font-num-xl text-display-lg text-on-surface leading-none">94.2%</span>
            <span
              class="flex items-center text-primary font-label-lg text-label-lg bg-primary-fixed px-2 py-0.5 rounded"
            >
              <span class="material-symbols-outlined text-[14px]">trending_up</span> +1.5%
            </span>
          </div>
          <p class="text-on-surface-variant text-sm mt-4">
            {{ t('过去7天平均值。AI模型目前对周末需求的预测置信度最高。') }}
          </p>
          <!-- Mini Chart Placeholder -->
          <div class="h-16 mt-4 w-full flex items-end gap-1 opacity-70">
            <div class="w-1/6 bg-primary-container h-3/5 rounded-t"></div>
            <div class="w-1/6 bg-primary-container h-4/5 rounded-t"></div>
            <div class="w-1/6 bg-primary-container h-2/5 rounded-t"></div>
            <div class="w-1/6 bg-primary h-full rounded-t"></div>
            <div class="w-1/6 bg-primary-container h-4/5 rounded-t"></div>
            <div class="w-1/6 bg-primary-container h-3/5 rounded-t"></div>
          </div>
        </div>
        <!-- KPI Card 2: Auto Assignment -->
        <div
          class="col-span-1 md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-[0_4px_12px_rgba(0,0,0,0.03)] ai-tinge"
        >
          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center gap-2 text-on-surface-variant">
              <span class="material-symbols-outlined text-tertiary">smart_toy</span>
              <h3 class="font-headline-md text-headline-md">{{ t('自动化排房成功率') }}</h3>
            </div>
          </div>
          <div class="flex items-end gap-3 mb-2">
            <span class="font-num-xl text-display-lg text-on-surface leading-none">88.7%</span>
            <span class="text-on-surface-variant font-label-lg text-label-lg">{{
              t('无人工干预')
            }}</span>
          </div>
          <div class="mt-6 space-y-3">
            <div class="flex justify-between items-center text-sm">
              <span class="text-on-surface-variant">{{ t('成功执行') }}</span>
              <span class="font-num-md text-num-md">{{ t('412 单') }}</span>
            </div>
            <div class="w-full bg-surface-container-high rounded-full h-2">
              <div class="bg-tertiary h-2 rounded-full" style="width: 88.7%"></div>
            </div>
            <div class="flex justify-between items-center text-sm mt-2">
              <span class="text-on-surface-variant">{{ t('需人工审核 (R1/R2)') }}</span>
              <span class="font-num-md text-num-md text-secondary">{{ t('53 单') }}</span>
            </div>
          </div>
        </div>
        <!-- KPI Card 3: Guest Satisfaction -->
        <div
          class="col-span-1 md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-[0_4px_12px_rgba(0,0,0,0.03)]"
        >
          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center gap-2 text-on-surface-variant">
              <span class="material-symbols-outlined text-on-surface-variant"
                >sentiment_satisfied</span
              >
              <h3 class="font-headline-md text-headline-md">{{ t('AI交互客需满意度') }}</h3>
            </div>
          </div>
          <div class="flex items-end gap-3 mb-2">
            <span class="font-num-xl text-display-lg text-on-surface leading-none">4.8</span>
            <span class="text-on-surface-variant font-label-lg text-label-lg">/ 5.0</span>
          </div>
          <div class="flex gap-1 mt-3 mb-4">
            <span class="material-symbols-outlined text-on-surface-variant fill">star</span>
            <span class="material-symbols-outlined text-on-surface-variant fill">star</span>
            <span class="material-symbols-outlined text-on-surface-variant fill">star</span>
            <span class="material-symbols-outlined text-on-surface-variant fill">star</span>
            <span class="material-symbols-outlined text-on-surface-variant fill text-opacity-80"
              >star_half</span
            >
          </div>
          <p class="text-on-surface-variant text-sm border-t border-outline-variant pt-3">
            {{ t('"AI客服响应迅速，准确解决了延迟退房的问题。" - 最近好评词云提取') }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 原型辅助类（gfnav 外壳已移除，这里保留内容区用到的样式） */
.ai-glow {
  box-shadow: 0 0 15px rgba(140, 51, 179, 0.15);
}
.ai-border-glow {
  border-left: 2px solid var(--tertiary);
}
.hide-scrollbar::-webkit-scrollbar {
  display: none;
}
.hide-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
</style>
