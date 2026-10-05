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
    <!-- Page Header -->
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
      <div>
        <h1 class="text-display-lg font-display-lg text-on-background flex items-center gap-2">
          {{ t('AI 差评预警') }}
        </h1>
        <p class="text-body-lg font-body-lg text-on-surface-variant mt-1">
          {{ t('实时情感分析与影响预测。') }}
        </p>
      </div>
      <div class="flex gap-3">
        <button
          class="bg-surface-container-low text-on-surface border border-outline-variant px-4 py-2 rounded-full text-label-lg font-label-lg hover:bg-surface-container-high transition-colors flex items-center gap-2"
        >
          {{ t('历史') }}</button
        ><button
          class="bg-primary text-on-primary px-5 py-2 rounded-full text-label-lg font-label-lg hover:bg-on-primary-fixed-variant transition-colors flex items-center gap-2 shadow-sm"
        >
          {{ t('全部自动处理') }}
        </button>
      </div>
    </div>
    <!-- Guardrail Banner (R1 - Low Risk / R2 - Medium Risk context) -->
    <div
      class="bg-surface-low border-l-4 border-outline-variant p-4 rounded-r-lg mb-8 flex items-start gap-3 shadow-sm"
    >
      <div class="flex-1">
        <h3 class="text-label-lg font-label-lg text-on-surface-variant">
          {{ t('需操作：检测到情感下滑') }}
        </h3>
        <p class="text-body-md font-body-md text-on-surface-variant mt-1">
          {{ t('AI 检测到过去 4 小时实时聊天互动中正面情感下降 15%。请核查以下潜在问题。') }}
        </p>
      </div>
    </div>
    <!-- Bento Grid Layout -->
    <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
      <!-- Potential Bad Reviews (Spans 8 cols) -->
      <div
        class="md:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col relative overflow-hidden"
      >
        <div class="absolute top-0 left-0 w-1 h-full bg-error"></div>
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-headline-md font-headline-md text-on-background flex items-center gap-2">
            {{ t('潜在差评') }}
          </h2>
          <span
            class="bg-error-container text-on-error-container px-3 py-1 rounded-full text-label-lg font-label-lg font-medium"
            >{{ t('预测 3 条') }}</span
          >
        </div>
        <div class="space-y-4">
          <!-- Item 1 -->
          <div
            class="bg-surface-container p-4 rounded-lg border border-outline-variant hover:border-error transition-colors"
          >
            <div class="flex justify-between items-start mb-2">
              <div class="flex items-center gap-3">
                <span
                  class="bg-surface-tint text-on-primary w-10 h-10 rounded-full flex items-center justify-center text-num-md font-num-md"
                  >301</span
                >
                <div>
                  <h4 class="text-label-lg font-label-lg text-on-background">
                    {{ t('Mr. Zhang (贵宾)') }}
                  </h4>
                  <p class="text-body-md font-body-md text-on-surface-variant text-sm">
                    {{ t('明日退房') }}
                  </p>
                </div>
              </div>
              <span
                class="bg-error/10 text-error px-2 py-1 rounded text-xs font-bold border border-error/20 flex items-center gap-1"
                >{{ t('92% 差评风险') }}</span
              >
            </div>
            <p
              class="text-body-md font-body-md text-on-background italic bg-surface-container-lowest p-3 rounded mt-2 border-l-2 border-error"
            >
              {{ t('“空调有异响且太热。20 分钟前已在微信发消息。”') }}
            </p>
            <div class="mt-4 flex gap-2 justify-end">
              <button
                class="bg-surface-container-low text-on-surface px-4 py-1.5 rounded-full text-label-lg font-label-lg hover:bg-surface-container-high transition-colors border border-outline-variant flex items-center gap-1"
              >
                {{ t('查看聊天') }}</button
              ><button
                class="bg-primary-container text-on-primary-container px-4 py-1.5 rounded-full text-label-lg font-label-lg hover:bg-surface-tint transition-colors flex items-center gap-1 shadow-sm relative overflow-hidden group"
              >
                <div class="absolute inset-0 ai-shimmer opacity-30 group-hover:opacity-50"></div>
                {{ t('发起 AI 触达') }}
              </button>
            </div>
          </div>
          <!-- Item 2 -->
          <div
            class="bg-surface-container p-4 rounded-lg border border-outline-variant hover:border-outline-variant transition-colors"
          >
            <div class="flex justify-between items-start mb-2">
              <div class="flex items-center gap-3">
                <span
                  class="bg-surface-tint text-on-primary w-10 h-10 rounded-full flex items-center justify-center text-num-md font-num-md"
                  >405</span
                >
                <div>
                  <h4 class="text-label-lg font-label-lg text-on-background">Ms. Li</h4>
                  <p class="text-body-md font-body-md text-on-surface-variant text-sm">
                    {{ t('2 小时前已退房') }}
                  </p>
                </div>
              </div>
              <span
                class="bg-surface-low text-on-surface-variant px-2 py-1 rounded text-xs font-bold border border-outline-variant/50 flex items-center gap-1"
                >{{ t('75% 差评风险') }}</span
              >
            </div>
            <p
              class="text-body-md font-body-md text-on-background italic bg-surface-container-lowest p-3 rounded mt-2 border-l-2 border-outline-variant"
            >
              {{ t('前台互动语义分析：检测到因退房缓慢引发的挫败感。') }}
            </p>
            <div class="mt-4 flex gap-2 justify-end">
              <button
                class="bg-primary-container text-on-primary-container px-4 py-1.5 rounded-full text-label-lg font-label-lg hover:bg-surface-tint transition-colors flex items-center gap-1 shadow-sm"
              >
                {{ t('发送致歉补偿') }}
              </button>
            </div>
          </div>
        </div>
      </div>
      <!-- Review Impact Forecast (Spans 4 cols) -->
      <div
        class="md:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col relative"
      >
        <div class="absolute top-0 left-0 w-1 h-full bg-tertiary"></div>
        <h2
          class="text-headline-md font-headline-md text-on-background flex items-center gap-2 mb-4"
        >
          {{ t('影响预测') }}
        </h2>
        <p class="text-body-md font-body-md text-on-surface-variant mb-6">
          {{ t('若预测差评发布后的预计影响。') }}
        </p>
        <div class="space-y-6">
          <!-- Ctrip Impact -->
          <div>
            <div class="flex justify-between text-label-lg font-label-lg mb-1">
              <span class="text-on-background font-bold">{{ t('携程评分') }}</span
              ><span class="text-error font-bold">4.8 → 4.6</span>
            </div>
            <div class="w-full bg-surface-variant rounded-full h-2.5">
              <div class="bg-primary h-2.5 rounded-full relative" style="width: 96%">
                <div class="absolute right-0 top-0 h-full bg-error" style="width: 15%"></div>
              </div>
            </div>
            <p class="text-xs text-on-surface-variant mt-1 text-right">
              {{ t('预计排名下降：-12 位') }}
            </p>
          </div>
          <!-- Meituan Impact -->
          <div>
            <div class="flex justify-between text-label-lg font-label-lg mb-1">
              <span class="text-on-background font-bold">{{ t('美团评分') }}</span
              ><span class="text-on-surface-variant font-bold">4.9 → 4.8</span>
            </div>
            <div class="w-full bg-surface-variant rounded-full h-2.5">
              <div class="bg-primary h-2.5 rounded-full relative" style="width: 98%">
                <div class="absolute right-0 top-0 h-full bg-surface-low" style="width: 5%"></div>
              </div>
            </div>
            <p class="text-xs text-on-surface-variant mt-1 text-right">
              {{ t('预计排名下降：-3 位') }}
            </p>
          </div>
        </div>
        <div class="mt-auto pt-6 border-t border-outline-variant">
          <div class="bg-tertiary/10 p-3 rounded-lg border border-tertiary/20">
            <p
              class="text-body-md font-body-md text-on-tertiary-fixed text-sm flex items-start gap-2"
            >
              <span
                >{{ t('避免 1 条差评约可节省') }}<strong class="text-tertiary">¥1,200</strong
                >{{ t('本月后续预订。') }}</span
              >
            </p>
          </div>
        </div>
      </div>
      <!-- Critical Issues Detected (Spans 12 cols) -->
      <div
        class="md:col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm mt-4"
      >
        <h2
          class="text-headline-md font-headline-md text-on-background flex items-center gap-2 mb-6"
        >
          {{ t('严重问题检测（AI 综合）') }}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <!-- Issue Card 1 -->
          <div
            class="bg-surface p-4 rounded-lg border border-outline-variant hover:shadow-md transition-shadow"
          >
            <div class="flex items-center gap-2 mb-3">
              <span
                class="bg-error/20 text-error p-1.5 rounded-md flex items-center justify-center"
              ></span>
              <h4 class="text-label-lg font-label-lg text-on-background font-bold">
                {{ t('隔音') }}
              </h4>
            </div>
            <p class="text-body-md font-body-md text-on-surface-variant mb-4">
              {{ t('投诉集中在 301-305 房，反映 22 点后走廊噪音。') }}
            </p>
            <div
              class="flex items-center justify-between mt-auto pt-3 border-t border-outline-variant"
            >
              <span class="text-xs text-on-surface-variant bg-surface-variant px-2 py-1 rounded">{{
                t('48 小时内 5 次提及')
              }}</span
              ><button
                class="text-primary text-label-lg font-label-lg hover:underline flex items-center gap-1"
              >
                {{ t('查看详情') }}
              </button>
            </div>
          </div>
          <!-- Issue Card 2 -->
          <div
            class="bg-surface p-4 rounded-lg border border-outline-variant hover:shadow-md transition-shadow relative overflow-hidden"
          >
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-surface-low"></div>
            <div class="flex items-center gap-2 mb-3 pl-2">
              <span
                class="bg-surface-low/20 text-on-surface-variant p-1.5 rounded-md flex items-center justify-center"
              ></span>
              <h4 class="text-label-lg font-label-lg text-on-background font-bold">
                {{ t('清洁度下降') }}
              </h4>
            </div>
            <p class="text-body-md font-body-md text-on-surface-variant mb-4 pl-2">
              {{ t('今日 2 楼毛巾出现两次轻微毛屑。') }}
            </p>
            <div
              class="flex items-center justify-between mt-auto pt-3 border-t border-outline-variant pl-2"
            >
              <button
                class="bg-surface-container-high text-on-surface px-3 py-1.5 rounded-full text-xs font-label-lg hover:bg-surface-variant transition-colors flex items-center gap-1 w-full justify-center"
              >
                {{ t('指派客房审计') }}
              </button>
            </div>
          </div>
          <!-- Issue Card 3 (Empty State/Positive) -->
          <div
            class="bg-surface p-4 rounded-lg border border-outline-variant border-dashed flex flex-col items-center justify-center text-center opacity-70"
          >
            <h4 class="text-label-lg font-label-lg text-on-surface-variant">
              {{ t('未检测到其他严重模式。') }}
            </h4>
            <p class="text-xs text-on-surface-variant mt-1">{{ t('AI 持续监测中。') }}</p>
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
