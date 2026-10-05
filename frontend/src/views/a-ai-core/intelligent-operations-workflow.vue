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
    <div class="max-w-[1024px] mx-auto w-full pb-20">
      <!-- Header -->
      <div class="mb-8">
        <h1 class="font-display-lg text-display-lg text-on-surface mb-2">
          {{ t('智能运营工作流') }}
        </h1>
        <p class="font-body-lg text-body-lg text-on-surface-variant">
          {{ t('AI 编排的实时自动化流程与动态酒店洞察。') }}
        </p>
      </div>
      <!-- Bento Grid Layout -->
      <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        <!-- Top Row: Core Metrics & Automation Status -->
        <div class="md:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-gutter">
          <!-- Revenue Card -->
          <div
            class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm hover:shadow-md transition-shadow relative overflow-hidden"
          >
            <div class="flex justify-between items-start mb-4">
              <div class="flex items-center gap-2">
                <div
                  class="w-8 h-8 rounded-full bg-primary-container/20 flex items-center justify-center text-primary"
                ></div>
                <span
                  class="font-label-lg text-label-lg text-on-surface-variant uppercase tracking-wider"
                  >{{ t('今日 RevPAR') }}</span
                >
              </div>
              <span
                class="bg-surface-variant text-on-surface text-xs px-2 py-1 rounded-md flex items-center gap-1"
                >{{ t('较上周 12%') }}</span
              >
            </div>
            <div class="font-num-xl text-[40px] leading-tight font-bold text-on-surface mb-1">
              ¥482.50
            </div>
            <p class="font-body-md text-body-md text-on-surface-variant">
              {{ t('当前入住率 84%') }}
            </p>
            <!-- Subtle AI Insight -->
            <div
              class="mt-4 p-3 bg-inverse-on-surface/50 rounded-lg border-l-2 border-tertiary flex gap-3 items-start"
            >
              <p class="font-body-md text-sm text-on-surface">
                {{ t('AI 预测受本地活动影响今夜深夜预订激增。动态定价已将标准房价上调 5%。') }}
              </p>
            </div>
          </div>
          <!-- Automation Active Flows Card -->
          <div
            class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col h-full relative"
          >
            <div class="flex justify-between items-center mb-6">
              <h3 class="font-headline-md text-headline-md text-on-surface">{{ t('活跃流程') }}</h3>
              <div
                class="flex items-center gap-2 text-tertiary bg-tertiary-container/30 px-3 py-1 rounded-full text-sm font-medium"
              >
                <span class="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span
                >{{ t('AI 编排中') }}
              </div>
            </div>
            <div class="flex-1 flex flex-col gap-4">
              <!-- Flow Item 1 -->
              <div class="flex items-start gap-4">
                <div
                  class="w-10 h-10 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center flex-shrink-0 z-10 relative"
                >
                  <div
                    class="absolute -bottom-4 left-1/2 w-px h-8 bg-outline-variant -translate-x-1/2"
                  ></div>
                </div>
                <div class="flex-1 pt-1">
                  <div class="flex justify-between items-center mb-1">
                    <span class="font-label-lg text-label-lg text-on-surface font-semibold">{{
                      t('客房调度')
                    }}</span
                    ><span class="text-xs text-on-surface-variant">{{ t('刚刚') }}</span>
                  </div>
                  <p class="text-sm text-on-surface-variant">
                    {{ t('已自动将 3 间贵宾客房（提前入住）分配给优先员工。') }}
                  </p>
                </div>
              </div>
              <!-- Flow Item 2 -->
              <div class="flex items-start gap-4">
                <div
                  class="w-10 h-10 rounded-full bg-surface-variant text-on-surface-variant flex items-center justify-center flex-shrink-0 z-10 relative"
                ></div>
                <div class="flex-1 pt-1">
                  <div class="flex justify-between items-center mb-1">
                    <span
                      class="font-label-lg text-label-lg text-on-surface font-semibold text-opacity-70"
                      >{{ t('到店前沟通') }}</span
                    ><span class="text-xs text-on-surface-variant text-opacity-70">{{
                      t('15 分钟前')
                    }}</span>
                  </div>
                  <p class="text-sm text-on-surface-variant text-opacity-70">
                    {{ t('已向 12 位到店客人发送入住指引。') }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- Right Column (Span 4): Guardrail Alert -->
        <div class="md:col-span-4 flex flex-col gap-gutter">
          <!-- R2 Risk Banner (Require Checkbox) -->
          <div class="bg-surface-low border border-outline-variant rounded-xl p-5 shadow-sm">
            <div class="flex items-start gap-3 mb-3">
              <div>
                <h4 class="font-headline-md text-[16px] font-bold text-on-surface-variant">
                  {{ t('建议复核') }}
                </h4>
                <p class="font-body-md text-sm text-on-surface-variant/80 mt-1">
                  {{ t('AI 建议将 3 楼剩余房量降价 15% 以清理库存。') }}
                </p>
              </div>
            </div>
            <label class="flex items-center gap-2 mt-4 cursor-pointer"
              ><input
                class="rounded border-outline text-primary focus:ring-primary w-4 h-4 bg-surface-container-lowest"
                type="checkbox"
              /><span class="font-body-md text-sm text-on-surface-variant">{{
                t('我确认此次价格调整')
              }}</span></label
            >
            <div class="flex gap-2 mt-4">
              <button
                class="px-4 py-2 bg-surface-container-lowest text-on-surface border border-outline-variant rounded-lg text-sm font-medium hover:bg-surface-variant transition-colors flex-1"
              >
                {{ t('忽略') }}</button
              ><button
                class="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:opacity-90 transition-opacity flex-1 opacity-50 cursor-not-allowed"
              >
                {{ t('应用规则') }}
              </button>
            </div>
          </div>
        </div>
        <!-- Bottom Row: Room Status Grid (AI Highlight) -->
        <div class="md:col-span-12 mt-4">
          <div class="flex justify-between items-center mb-4">
            <h2 class="font-headline-lg text-headline-lg text-on-surface">
              {{ t('实时房态看板状态') }}
            </h2>
            <button
              class="flex items-center gap-1 text-primary hover:bg-primary-container/10 px-3 py-1.5 rounded-lg transition-colors text-sm font-medium"
            >
              {{ t('查看完整看板') }}
            </button>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <!-- Room Card 1 (Clean) -->
            <div
              class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 hover:border-primary transition-colors cursor-pointer relative"
            >
              <div class="absolute top-0 right-0 w-8 h-8 overflow-hidden rounded-tr-xl">
                <div
                  class="absolute top-0 left-0 w-16 h-4 bg-green-500/20 rotate-45 translate-x-2 -translate-y-2"
                ></div>
              </div>
              <div class="font-num-xl text-xl mb-2 text-on-surface">201</div>
              <div class="flex items-center gap-1 text-green-700 mb-4">
                <span class="w-2 h-2 rounded-full bg-green-500"></span
                ><span class="font-label-lg text-xs font-semibold">{{ t('空净可售') }}</span>
              </div>
              <div class="text-sm text-on-surface-variant font-body-md">{{ t('标准大床房') }}</div>
            </div>
            <!-- Room Card 2 (Dirty) -->
            <div
              class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 hover:border-primary transition-colors cursor-pointer"
            >
              <div class="font-num-xl text-xl mb-2 text-on-surface">204</div>
              <div class="flex items-center gap-1 text-on-surface-variant mb-4">
                <span class="w-2 h-2 rounded-full bg-surface-low"></span
                ><span class="font-label-lg text-xs font-semibold">{{ t('待清洁') }}</span>
              </div>
              <div class="text-sm text-on-surface-variant font-body-md">{{ t('豪华套房') }}</div>
            </div>
            <!-- Room Card 3 (AI Focus/Maintenance) -->
            <div
              class="bg-surface-container-lowest border border-tertiary/40 rounded-xl p-4 cursor-pointer ai-glow relative"
            >
              <div
                class="absolute -top-2 -right-2 bg-tertiary text-on-tertiary w-6 h-6 rounded-full flex items-center justify-center shadow-md"
              ></div>
              <div class="font-num-xl text-xl mb-2 text-on-surface flex items-center gap-2">
                305
              </div>
              <div class="flex items-center gap-1 text-tertiary mb-2">
                <span class="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span
                ><span class="font-label-lg text-xs font-semibold">{{ t('维护标记') }}</span>
              </div>
              <p class="text-xs text-on-surface-variant mb-2 leading-tight">
                {{ t('上一位客人报空调故障。AI 已将该房撤出库存。') }}
              </p>
            </div>
            <!-- Room Card 4 (Occupied) -->
            <div
              class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 hover:border-primary transition-colors cursor-pointer opacity-70"
            >
              <div class="font-num-xl text-xl mb-2 text-on-surface">308</div>
              <div class="flex items-center gap-1 text-primary mb-4">
                <span class="w-2 h-2 rounded-full bg-primary"></span
                ><span class="font-label-lg text-xs font-semibold">{{ t('已入住') }}</span>
              </div>
              <div class="text-sm text-on-surface-variant font-body-md">
                {{ t('标准单人间（N2）') }}
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
