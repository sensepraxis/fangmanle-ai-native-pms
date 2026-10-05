<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// 数据来源：后端 demo 接口（确定性种子数据），实体 = oneid
// 列表/表格通过 v-for 渲染 rows；字段缺失时回退原型示例值，保证版式 1:1。
const hotelId = 1
const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('oneid')
})
</script>

<template>
  <div class="page">
    <div class="max-w-[max-content-width] mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-6 gap-4">
        <div>
          <h2 class="font-display-lg text-display-lg text-on-background mb-1">
            {{ t('李伟的智能画像') }}
          </h2>
          <p class="font-body-md text-body-md text-on-surface-variant">
            {{ t('基于历史 12 次入住数据分析预测') }}
          </p>
        </div>
        <div class="flex gap-3">
          <button
            class="px-4 py-2 border border-outline rounded-lg text-on-surface hover:bg-surface-container-low transition-colors font-label-lg flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-[18px]">download</span>
            {{ t('导出报告') }}
          </button>
        </div>
      </div>
      <!-- Bento Grid Layout -->
      <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        <!-- Top Row: Next Best Action (AI Insight) -->
        <div
          class="col-span-1 md:col-span-12 bg-surface-bright rounded-xl border border-outline-variant shadow-sm overflow-hidden ai-border-left"
        >
          <div
            class="p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6"
          >
            <div class="flex items-start gap-4">
              <div class="p-3 bg-tertiary-fixed rounded-full text-tertiary shadow-sm">
                <span class="material-symbols-outlined text-[24px]">auto_awesome</span>
              </div>
              <div>
                <div class="flex items-center gap-2 mb-1">
                  <h3 class="font-headline-md text-headline-md text-on-surface">
                    {{ t('AI 下一步行动建议') }}
                  </h3>
                  <span
                    class="bg-tertiary-fixed-dim text-on-tertiary-fixed-variant text-xs px-2 py-0.5 rounded-full font-medium"
                    >{{ t('置信度 92%') }}</span
                  >
                </div>
                <p class="font-body-md text-body-md text-on-surface-variant max-w-2xl">
                  {{ t('预测李先生下个月（11月15日左右）将庆祝结婚纪念日。建议在入住前 3 天推送') }}
                  <strong>{{ t('"浪漫江景双人套餐"') }}</strong
                  >{{ t('，包含高级红酒与行政酒廊权限。') }}
                </p>
              </div>
            </div>
            <div class="flex gap-3 shrink-0 w-full md:w-auto">
              <button
                class="flex-1 md:flex-none px-4 py-2 border border-outline rounded-lg text-on-surface hover:bg-surface-container-low transition-colors font-label-lg"
              >
                {{ t('忽略建议') }}
              </button>
              <button
                class="flex-1 md:flex-none px-4 py-2 bg-primary text-on-primary rounded-lg hover:bg-surface-tint shadow-sm transition-colors font-label-lg flex items-center justify-center gap-2"
              >
                <span class="material-symbols-outlined text-[18px]">send</span>
                {{ t('一键配置营销策略') }}
              </button>
            </div>
          </div>
        </div>
        <!-- Left Column: Psychographic Radar Chart -->
        <div class="col-span-1 md:col-span-5 flex flex-col gap-gutter">
          <div
            class="bg-surface rounded-xl border border-outline-variant shadow-sm p-6 flex-1 flex flex-col"
          >
            <h3
              class="font-headline-md text-headline-md text-on-surface mb-2 flex items-center gap-2"
            >
              <span class="material-symbols-outlined text-secondary">psychology</span>
              {{ t('心理特征雷达') }}
            </h3>
            <p class="font-body-md text-body-md text-on-surface-variant mb-6 text-sm">
              {{ t('核心偏好因子评估') }}
            </p>
            <div
              class="flex-1 min-h-[300px] relative bg-surface-container-lowest rounded-lg border border-outline-variant/50 p-4 flex items-center justify-center"
            >
              <!-- Abstract Representation of a Radar Chart using SVG/HTML structure for styling -->
              <div class="relative w-64 h-64">
                <!-- Radar Grid (Simplified for UI visualization) -->
                <svg class="absolute inset-0 w-full h-full" viewbox="0 0 100 100">
                  <polygon
                    fill="none"
                    points="50,10 90,30 90,70 50,90 10,70 10,30"
                    stroke="#e1e3e4"
                    stroke-width="0.5"
                  ></polygon>
                  <polygon
                    fill="none"
                    points="50,25 75,40 75,60 50,75 25,60 25,40"
                    stroke="#e1e3e4"
                    stroke-width="0.5"
                  ></polygon>
                  <polygon
                    fill="none"
                    points="50,40 60,45 60,55 50,60 40,55 40,45"
                    stroke="#e1e3e4"
                    stroke-width="0.5"
                  ></polygon>
                  <!-- Axis Lines -->
                  <line stroke="#e1e3e4" stroke-width="0.5" x1="50" x2="50" y1="50" y2="10"></line>
                  <line stroke="#e1e3e4" stroke-width="0.5" x1="50" x2="90" y1="50" y2="30"></line>
                  <line stroke="#e1e3e4" stroke-width="0.5" x1="50" x2="90" y1="50" y2="70"></line>
                  <line stroke="#e1e3e4" stroke-width="0.5" x1="50" x2="50" y1="50" y2="90"></line>
                  <line stroke="#e1e3e4" stroke-width="0.5" x1="50" x2="10" y1="50" y2="70"></line>
                  <line stroke="#e1e3e4" stroke-width="0.5" x1="50" x2="10" y1="50" y2="30"></line>
                  <!-- Data Polygon -->
                  <polygon
                    fill="rgba(26, 115, 232, 0.2)"
                    points="50,15 85,35 70,65 50,85 20,65 30,35"
                    stroke="#005bbf"
                    stroke-width="1.5"
                  ></polygon>
                  <!-- Data Points -->
                  <circle cx="50" cy="15" fill="#005bbf" r="2"></circle>
                  <circle cx="85" cy="35" fill="#005bbf" r="2"></circle>
                  <circle cx="70" cy="65" fill="#005bbf" r="2"></circle>
                  <circle cx="50" cy="85" fill="#005bbf" r="2"></circle>
                  <circle cx="20" cy="65" fill="#005bbf" r="2"></circle>
                  <circle cx="30" cy="35" fill="#005bbf" r="2"></circle>
                </svg>
                <!-- Labels -->
                <div
                  class="absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-label-lg text-on-surface whitespace-nowrap"
                >
                  {{ t('静音要求极高 (90)') }}
                </div>
                <div class="absolute top-6 -right-10 text-xs font-label-lg text-on-surface">
                  {{ t('偏好高楼层 (85)') }}
                </div>
                <div class="absolute bottom-10 -right-8 text-xs font-label-lg text-on-surface">
                  {{ t('夜床服务 (60)') }}
                </div>
                <div
                  class="absolute -bottom-6 left-1/2 -translate-x-1/2 text-xs font-label-lg text-on-surface whitespace-nowrap"
                >
                  {{ t('重口味/辛辣餐饮 (75)') }}
                </div>
                <div class="absolute bottom-10 -left-6 text-xs font-label-lg text-on-surface">
                  {{ t('快速退房 (70)') }}
                </div>
                <div class="absolute top-6 -left-8 text-xs font-label-lg text-on-surface">
                  {{ t('乳胶枕头 (65)') }}
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- Right Column: Consumption Fingerprint -->
        <div class="col-span-1 md:col-span-7 flex flex-col gap-gutter">
          <div class="bg-surface rounded-xl border border-outline-variant shadow-sm p-6 flex-1">
            <div class="flex justify-between items-center mb-6">
              <div>
                <h3
                  class="font-headline-md text-headline-md text-on-surface flex items-center gap-2"
                >
                  <span class="material-symbols-outlined text-secondary">fingerprint</span>
                  {{ t('消费指纹 (TTV: ¥45,200)') }}
                </h3>
                <p class="font-body-md text-body-md text-on-surface-variant mt-1 text-sm">
                  {{ t('客房外消费 (ANC) 占比极高') }}
                </p>
              </div>
              <select
                class="bg-surface-container-low border-outline-variant text-sm rounded-lg py-1.5 pl-3 pr-8 focus:ring-primary"
              >
                <option>{{ t('过去 12 个月') }}</option>
                <option>{{ t('所有历史记录') }}</option>
              </select>
            </div>
            <!-- Spend Distribution Bar Chart (Custom HTML/CSS) -->
            <div class="space-y-5">
              <!-- Category 1 -->
              <div>
                <div class="flex justify-between text-sm mb-1.5">
                  <span class="font-medium text-on-surface flex items-center gap-2">
                    <span class="w-3 h-3 rounded-sm bg-primary"></span>
                    {{ t('客房消费 (Room)') }}</span
                  >
                  <span class="font-num-md text-on-surface-variant">¥22,600 (50%)</span>
                </div>
                <div class="w-full bg-surface-container-high rounded-full h-2.5 overflow-hidden">
                  <div class="bg-primary h-2.5 rounded-full" style="width: 50%"></div>
                </div>
              </div>
              <!-- Category 2 -->
              <div>
                <div class="flex justify-between text-sm mb-1.5">
                  <span class="font-medium text-on-surface flex items-center gap-2">
                    <span class="w-3 h-3 rounded-sm bg-tertiary-container"></span>
                    {{ t('餐饮 (F&amp;B)') }}</span
                  >
                  <span class="font-num-md text-on-surface-variant">¥13,560 (30%)</span>
                </div>
                <div class="w-full bg-surface-container-high rounded-full h-2.5 overflow-hidden">
                  <div class="bg-tertiary-container h-2.5 rounded-full" style="width: 30%"></div>
                </div>
                <p class="text-xs text-on-surface-variant mt-1 ml-5">
                  {{ t('主要偏好：客房送餐 (深夜)、大堂吧威士忌') }}
                </p>
              </div>
              <!-- Category 3 -->
              <div>
                <div class="flex justify-between text-sm mb-1.5">
                  <span class="font-medium text-on-surface flex items-center gap-2">
                    <span class="w-3 h-3 rounded-sm bg-secondary"></span>
                    {{ t('水疗与康体 (Spa &amp; Wellness)') }}</span
                  >
                  <span class="font-num-md text-on-surface-variant">¥6,780 (15%)</span>
                </div>
                <div class="w-full bg-surface-container-high rounded-full h-2.5 overflow-hidden">
                  <div class="bg-secondary h-2.5 rounded-full" style="width: 15%"></div>
                </div>
              </div>
              <!-- Category 4 -->
              <div>
                <div class="flex justify-between text-sm mb-1.5">
                  <span class="font-medium text-on-surface flex items-center gap-2">
                    <span class="w-3 h-3 rounded-sm bg-outline"></span>
                    {{ t('其他 (交通/洗衣等)') }}</span
                  >
                  <span class="font-num-md text-on-surface-variant">¥2,260 (5%)</span>
                </div>
                <div class="w-full bg-surface-container-high rounded-full h-2.5 overflow-hidden">
                  <div class="bg-outline h-2.5 rounded-full" style="width: 5%"></div>
                </div>
              </div>
            </div>
            <!-- Insight Pill -->
            <div
              class="mt-6 bg-surface-container-low p-4 rounded-lg flex items-start gap-3 border border-outline-variant/30"
            >
              <span class="material-symbols-outlined text-primary text-[20px] mt-0.5">info</span>
              <div>
                <p class="font-label-lg text-on-surface font-medium mb-1">
                  {{ t('高净值餐饮转化客户') }}
                </p>
                <p class="text-sm text-on-surface-variant">
                  {{
                    t(
                      '该客人的 F&amp;B 占比高出同级别会员平均值 18%。建议在下次预订时，优先推销包含餐饮抵扣额度的房价计划 (Rate Plan)。',
                    )
                  }}
                </p>
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
