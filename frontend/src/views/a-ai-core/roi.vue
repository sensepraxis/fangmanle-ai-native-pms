<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// 数据来源：后端 demo 接口（确定性种子数据），实体 = ai-command
// 列表/表格通过 v-for 渲染 rows；字段缺失时回退原型示例值，保证版式 1:1。
const hotelId = 1
const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('ai-command')
})
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto">
      <!-- Page Header -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-display-lg font-display-lg text-on-background mb-2">
            {{ t('口碑修复 ROI 与趋势看板') }}
          </h1>
          <p class="text-body-md font-body-md text-on-surface-variant">
            {{ t('声誉修复 ROI 与 AI 效能摘要') }}
          </p>
        </div>
        <div class="flex gap-4">
          <select
            class="bg-surface-container-lowest border border-outline-variant text-on-surface text-label-lg font-label-lg rounded-lg px-4 py-2 focus:ring-primary"
          >
            <option>{{ t('近 30 天') }}</option>
            <option>{{ t('本季度') }}</option>
            <option>{{ t('年初至今') }}</option></select
          ><button
            class="bg-primary text-on-primary text-label-lg font-label-lg px-6 py-2 rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            {{ t('导出报告') }}
          </button>
        </div>
      </div>
      <!-- Top KPIs -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-gutter mb-8">
        <!-- KPI 1 -->
        <div
          class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm ai-tinge"
        >
          <div class="flex justify-between items-start mb-4">
            <span class="text-label-lg font-label-lg text-on-surface-variant">{{
              t('AI 已挽回评分')
            }}</span>
          </div>
          <div class="text-display-lg font-display-lg text-on-background">+0.42</div>
          <div class="text-label-lg font-label-lg text-primary mt-2">{{ t('目标：+0.30') }}</div>
        </div>
        <!-- KPI 2 -->
        <div
          class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm"
        >
          <div class="flex justify-between items-start mb-4">
            <span class="text-label-lg font-label-lg text-on-surface-variant">{{
              t('预计节省营收')
            }}</span>
          </div>
          <div class="text-display-lg font-display-lg text-on-background">¥124,500</div>
          <div class="text-label-lg font-label-lg text-on-surface-variant mt-2">
            {{ t('来自 86 条已化解评论') }}
          </div>
        </div>
        <!-- KPI 3 -->
        <div
          class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm"
        >
          <div class="flex justify-between items-start mb-4">
            <span class="text-label-lg font-label-lg text-on-surface-variant">{{
              t('修复成功率')
            }}</span>
          </div>
          <div class="text-display-lg font-display-lg text-on-background">78%</div>
          <div class="text-label-lg font-label-lg text-on-surface-variant mt-2">
            {{ t('较上周期 +12%') }}
          </div>
        </div>
        <!-- KPI 4 -->
        <div
          class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm"
        >
          <div class="flex justify-between items-start mb-4">
            <span class="text-label-lg font-label-lg text-on-surface-variant">{{
              t('AI 平均响应时长')
            }}</span>
          </div>
          <div class="text-display-lg font-display-lg text-on-background">4.2m</div>
          <div class="text-label-lg font-label-lg text-on-surface-variant mt-2">
            {{ t('行业均值：14 小时') }}
          </div>
        </div>
      </div>
      <!-- Main Bento Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
        <!-- Score Recovery Chart (Spans 8 cols) -->
        <div
          class="col-span-1 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6 relative overflow-hidden flex flex-col h-[400px]"
        >
          <div class="flex justify-between items-center mb-6 z-10">
            <h2
              class="text-headline-md font-headline-md text-on-background flex items-center gap-2"
            >
              {{ t('评分修复轨迹') }}
            </h2>
            <div class="flex gap-4 text-label-lg font-label-lg text-on-surface-variant">
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full bg-outline-variant"></div>
                {{ t('预测（无 AI）') }}
              </div>
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full bg-primary"></div>
                {{ t('实际（含 AI）') }}
              </div>
            </div>
          </div>
          <div
            class="flex-1 w-full bg-surface-container-low rounded-lg border border-outline-variant border-dashed flex items-center justify-center text-on-surface-variant relative"
          >
            <!-- Placeholder for actual chart -->
            <div
              class="absolute bottom-0 left-0 w-full h-full flex items-end px-8 pb-8 gap-4 opacity-50"
            >
              <!-- Mock Chart Bars -->
              <div class="flex-1 bg-outline-variant h-[20%] rounded-t-sm"></div>
              <div class="flex-1 bg-primary h-[30%] rounded-t-sm"></div>
              <div class="flex-1 bg-outline-variant h-[25%] rounded-t-sm"></div>
              <div class="flex-1 bg-primary h-[45%] rounded-t-sm"></div>
              <div class="flex-1 bg-outline-variant h-[30%] rounded-t-sm"></div>
              <div class="flex-1 bg-primary h-[60%] rounded-t-sm"></div>
              <div class="flex-1 bg-outline-variant h-[28%] rounded-t-sm"></div>
              <div class="flex-1 bg-primary h-[85%] rounded-t-sm"></div>
            </div>
            <span
              class="z-10 bg-surface-container-lowest px-4 py-2 rounded-full shadow-sm text-label-lg border border-outline-variant"
              >{{ t('图表可视化区域') }}</span
            >
          </div>
        </div>
        <!-- Guest Satisfaction Turnaround Funnel (Spans 4 cols) -->
        <div
          class="col-span-1 lg:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6 flex flex-col h-[400px]"
        >
          <h2 class="text-headline-md font-headline-md text-on-background mb-6">
            {{ t('干预漏斗') }}
          </h2>
          <div class="flex-1 flex flex-col gap-3 justify-center">
            <!-- Funnel Step 1 -->
            <div
              class="w-full bg-surface-container-low rounded-lg p-3 flex justify-between items-center border border-outline-variant"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded-full bg-error-container text-on-error-container flex items-center justify-center"
                ></div>
                <span class="text-label-lg font-label-lg text-on-surface">{{ t('不满客人') }}</span>
              </div>
              <span class="text-num-md font-num-md">245</span>
            </div>
            <div class="w-full flex justify-center"></div>
            <!-- Funnel Step 2 -->
            <div
              class="w-[90%] mx-auto bg-surface-container-low rounded-lg p-3 flex justify-between items-center border border-outline-variant ai-tinge"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded-full bg-tertiary-container text-on-tertiary-container flex items-center justify-center"
                ></div>
                <span class="text-label-lg font-label-lg text-on-surface">{{
                  t('AI 已触达')
                }}</span>
              </div>
              <span class="text-num-md font-num-md">240</span>
            </div>
            <div class="w-full flex justify-center"></div>
            <!-- Funnel Step 3 -->
            <div
              class="w-[80%] mx-auto bg-surface-container-low rounded-lg p-3 flex justify-between items-center border border-outline-variant"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center"
                ></div>
                <span class="text-label-lg font-label-lg text-on-surface">{{ t('已补偿') }}</span>
              </div>
              <span class="text-num-md font-num-md">186</span>
            </div>
            <div class="w-full flex justify-center"></div>
            <!-- Funnel Step 4 -->
            <div
              class="w-[70%] mx-auto bg-surface-container-low rounded-lg p-3 flex justify-between items-center border border-outline-variant"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded-full bg-surface-tint text-on-primary flex items-center justify-center"
                ></div>
                <span class="text-label-lg font-label-lg text-on-surface">{{ t('正向改评') }}</span>
              </div>
              <span class="text-num-md font-num-md text-primary font-bold">152</span>
            </div>
          </div>
        </div>
        <!-- Competitor Benchmark (Spans 6 cols) -->
        <div
          class="col-span-1 lg:col-span-6 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6"
        >
          <h2 class="text-headline-md font-headline-md text-on-background mb-6">
            {{ t('行业基准') }}
          </h2>
          <div class="space-y-4">
            <div
              class="flex items-center justify-between p-4 bg-surface-container-low rounded-lg border border-outline-variant"
            >
              <div class="flex items-center gap-4">
                <div class="text-num-md font-num-md w-8 text-center text-on-surface-variant">1</div>
                <div
                  class="w-10 h-10 rounded bg-primary text-on-primary flex items-center justify-center font-bold"
                >
                  {{ t('我方') }}
                </div>
                <div>
                  <div class="text-label-lg font-label-lg text-on-surface">
                    {{ t('本酒店（AI 管理）') }}
                  </div>
                  <div
                    class="text-body-md font-body-md text-tertiary flex items-center gap-1 text-sm"
                  >
                    {{ t('增长最快') }}
                  </div>
                </div>
              </div>
              <div class="text-num-xl font-num-xl text-on-background">4.82</div>
            </div>
            <div class="flex items-center justify-between p-4 border border-transparent">
              <div class="flex items-center gap-4">
                <div class="text-num-md font-num-md w-8 text-center text-on-surface-variant">2</div>
                <div class="w-10 h-10 rounded bg-surface-variant flex items-center justify-center">
                  C
                </div>
                <div>
                  <div class="text-label-lg font-label-lg text-on-surface">{{ t('竞品 A') }}</div>
                  <div class="text-body-md font-body-md text-on-surface-variant text-sm">
                    {{ t('精品酒店') }}
                  </div>
                </div>
              </div>
              <div class="text-num-xl font-num-xl text-on-surface-variant">4.75</div>
            </div>
            <div class="flex items-center justify-between p-4 border border-transparent">
              <div class="flex items-center gap-4">
                <div class="text-num-md font-num-md w-8 text-center text-on-surface-variant">3</div>
                <div class="w-10 h-10 rounded bg-surface-variant flex items-center justify-center">
                  C
                </div>
                <div>
                  <div class="text-label-lg font-label-lg text-on-surface">{{ t('竞品 B') }}</div>
                  <div class="text-body-md font-body-md text-on-surface-variant text-sm">
                    {{ t('连锁酒店') }}
                  </div>
                </div>
              </div>
              <div class="text-num-xl font-num-xl text-on-surface-variant">4.61</div>
            </div>
          </div>
        </div>
        <!-- Recent AI Interventions List (Spans 6 cols) -->
        <div
          class="col-span-1 lg:col-span-6 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6"
        >
          <div class="flex justify-between items-center mb-6">
            <h2 class="text-headline-md font-headline-md text-on-background">
              {{ t('近期 AI 干预') }}
            </h2>
            <button class="text-primary text-label-lg font-label-lg hover:underline">
              {{ t('查看全部') }}
            </button>
          </div>
          <div class="space-y-4">
            <!-- Intervention Item -->
            <div
              class="p-4 bg-surface-container-low rounded-lg border border-outline-variant ai-tinge"
            >
              <div class="flex justify-between items-start mb-2">
                <div class="flex gap-2 items-center">
                  <span
                    class="bg-error-container text-on-error-container px-2 py-0.5 rounded text-xs font-bold"
                    >{{ t('初始：2★') }}</span
                  ><span
                    class="bg-primary-container text-on-primary-container px-2 py-0.5 rounded text-xs font-bold"
                    >{{ t('修订：5★') }}</span
                  >
                </div>
                <span class="text-label-lg font-label-lg text-on-surface-variant">{{
                  t('2 小时前')
                }}</span>
              </div>
              <p class="text-body-md font-body-md text-on-surface mb-2">
                {{ t('客人投诉 302 房空调噪音。') }}
              </p>
              <div class="flex gap-2">
                <span
                  class="inline-flex items-center gap-1 bg-surface-variant text-on-surface-variant px-2 py-1 rounded-md text-xs"
                  >{{ t('AI 已致歉') }}</span
                ><span
                  class="inline-flex items-center gap-1 bg-surface-variant text-on-surface-variant px-2 py-1 rounded-md text-xs"
                  >{{ t('已赠送免费早餐') }}</span
                >
              </div>
            </div>
            <!-- Intervention Item -->
            <div
              class="p-4 bg-surface-container-low rounded-lg border border-outline-variant ai-tinge"
            >
              <div class="flex justify-between items-start mb-2">
                <div class="flex gap-2 items-center">
                  <span
                    class="bg-error-container text-on-error-container px-2 py-0.5 rounded text-xs font-bold"
                    >{{ t('初始：3★') }}</span
                  ><span
                    class="bg-primary-container text-on-primary-container px-2 py-0.5 rounded text-xs font-bold"
                    >{{ t('修订：4★') }}</span
                  >
                </div>
                <span class="text-label-lg font-label-lg text-on-surface-variant">{{
                  t('昨日')
                }}</span>
              </div>
              <p class="text-body-md font-body-md text-on-surface mb-2">
                {{ t('评论提及入住办理延迟。') }}
              </p>
              <div class="flex gap-2">
                <span
                  class="inline-flex items-center gap-1 bg-surface-variant text-on-surface-variant px-2 py-1 rounded-md text-xs"
                  >{{ t('AI 已解释政策') }}</span
                ><span
                  class="inline-flex items-center gap-1 bg-surface-variant text-on-surface-variant px-2 py-1 rounded-md text-xs"
                  >{{ t('下次入住 9 折') }}</span
                >
              </div>
            </div>
          </div>
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
