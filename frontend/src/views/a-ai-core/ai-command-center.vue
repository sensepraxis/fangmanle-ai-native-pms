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
    <div class="mb-6 flex justify-between items-end">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface m-0">{{ t('工作区预览') }}</h1>
        <p class="font-body-lg text-body-lg text-on-surface-variant mt-1">
          {{ t('AI 正在执行您的指令') }}
        </p>
      </div>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 bg-surface-container border border-outline-variant rounded-lg text-on-surface font-label-lg text-label-lg hover:bg-surface-variant transition-colors flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-[18px]">close</span> {{ t('取消操作') }}
        </button>
        <button
          class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg text-label-lg hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm"
        >
          <span class="material-symbols-outlined text-[18px]">check_circle</span>
          {{ t('一键确认全部') }}
        </button>
      </div>
    </div>
    <!-- Bento Grid Layout -->
    <div class="grid grid-cols-12 gap-gutter">
      <!-- AI Action Card: Group Check-in Prep (Spans 7 cols) -->
      <div
        class="col-span-12 xl:col-span-7 bg-surface-container-lowest rounded-xl border-l-4 border-l-tertiary border border-outline-variant/50 shadow-sm flex flex-col overflow-hidden"
      >
        <div
          class="p-4 border-b border-outline-variant/30 flex justify-between items-center bg-surface-bright"
        >
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-tertiary">groups</span>
            <h3 class="font-headline-md text-headline-md text-on-surface m-0 text-lg">
              {{ t('明日团队入住准备 (草稿)') }}
            </h3>
          </div>
          <span
            class="px-2 py-1 rounded bg-secondary-container text-on-secondary-container font-label-lg text-[11px] uppercase tracking-wider"
            >{{ t('AI 生成') }}</span
          >
        </div>
        <div class="p-5 flex-1">
          <div class="flex gap-4 mb-6">
            <div
              class="flex-1 p-3 rounded-lg bg-surface-container-low border border-outline-variant/30"
            >
              <p class="font-label-lg text-on-surface-variant mb-1">{{ t('预计团队数') }}</p>
              <p class="font-num-xl text-num-xl text-primary m-0">4</p>
            </div>
            <div
              class="flex-1 p-3 rounded-lg bg-surface-container-low border border-outline-variant/30"
            >
              <p class="font-label-lg text-on-surface-variant mb-1">{{ t('占用客房') }}</p>
              <p class="font-num-xl text-num-xl text-primary m-0">82</p>
            </div>
            <div
              class="flex-1 p-3 rounded-lg bg-surface-container-low border border-outline-variant/30"
            >
              <p class="font-label-lg text-on-surface-variant mb-1">{{ t('集中到达时间') }}</p>
              <p class="font-num-xl text-num-xl text-on-surface m-0">14:00</p>
            </div>
          </div>
          <h4 class="font-label-lg text-label-lg text-on-surface mb-3">
            {{ t('AI 预排房明细 (部分)') }}
          </h4>
          <div class="border border-outline-variant/30 rounded-lg overflow-hidden">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr
                  class="bg-surface-container-low font-label-lg text-on-surface-variant text-xs uppercase tracking-wider"
                >
                  <th class="p-3 border-b border-outline-variant/30">{{ t('团队名称') }}</th>
                  <th class="p-3 border-b border-outline-variant/30">{{ t('房型') }}</th>
                  <th class="p-3 border-b border-outline-variant/30">{{ t('分配楼层') }}</th>
                  <th class="p-3 border-b border-outline-variant/30">{{ t('状态') }}</th>
                </tr>
              </thead>
              <tr v-for="(item, i) in rows" :key="i">
                <td class="p-3 text-on-surface font-medium">
                  {{ item.cmd || t('夕阳红旅行团 A组') }}
                </td>
                <td class="p-3 text-on-surface-variant">
                  {{ item.status || t('双床标间 (20间)') }}
                </td>
                <td class="p-3 font-num-md">{{ item.by || '3F, 4F (靠近电梯)' }}</td>
                <td class="p-3">{{ item.at || 'warning 需保洁优先' }}</td>
              </tr>
            </table>
          </div>
        </div>
      </div>
      <!-- AI Action Card: Revenue Leaks (Spans 5 cols) -->
      <div
        class="col-span-12 xl:col-span-5 bg-surface-container-lowest rounded-xl border border-outline-variant/50 shadow-sm flex flex-col relative overflow-hidden"
      >
        <!-- Soft glow behind the card for AI feel -->
        <div
          class="absolute -top-10 -right-10 w-32 h-32 bg-tertiary/10 rounded-full blur-3xl pointer-events-none"
        ></div>
        <div
          class="p-4 border-b border-outline-variant/30 flex justify-between items-center bg-surface-bright z-10"
        >
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-error">trending_down</span>
            <h3 class="font-headline-md text-headline-md text-on-surface m-0 text-lg">
              {{ t('上周收益漏洞') }}
            </h3>
          </div>
        </div>
        <div class="p-5 flex-1 z-10 flex flex-col">
          <div class="mb-4">
            <p class="font-label-lg text-on-surface-variant mb-1">
              {{ t('估算流失总额 (9.11 - 9.17)') }}
            </p>
            <p class="font-num-xl text-[32px] font-bold text-error leading-none m-0">¥ 12,450</p>
          </div>
          <div class="space-y-4 flex-1">
            <!-- Leak Item 1 -->
            <div class="bg-error-container/30 border border-error/20 rounded-lg p-3">
              <div class="flex justify-between items-start mb-1">
                <span class="font-label-lg text-on-error-container font-semibold">{{
                  t('OTA 渠道倒挂')
                }}</span>
                <span class="font-num-md text-error font-bold">¥ 8,200</span>
              </div>
              <p class="font-body-md text-xs text-on-surface-variant">
                {{
                  t(
                    '发现携程渠道协议价配置错误，低于直销最低价 15%。AI 建议立即冻结协议代码 C-892。',
                  )
                }}
              </p>
              <button
                class="mt-2 text-xs font-label-lg text-error hover:underline flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-[14px]">edit</span> {{ t('修复配置') }}
              </button>
            </div>
            <!-- Leak Item 2 -->
            <div class="bg-surface-container-low border border-outline-variant/30 rounded-lg p-3">
              <div class="flex justify-between items-start mb-1">
                <span class="font-label-lg text-on-surface font-medium">{{
                  t('超额免费升级')
                }}</span>
                <span class="font-num-md text-on-surface-variant">¥ 3,150</span>
              </div>
              <p class="font-body-md text-xs text-on-surface-variant">
                {{
                  t(
                    '前台在满房压力下，执行了 14 次无预期的免费升级至行政套房。AI 建议优化房态控制。',
                  )
                }}
              </p>
            </div>
            <!-- Leak Item 3 -->
            <div class="bg-surface-container-low border border-outline-variant/30 rounded-lg p-3">
              <div class="flex justify-between items-start mb-1">
                <span class="font-label-lg text-on-surface font-medium">{{
                  t('连住取消率攀升')
                }}</span>
                <span class="font-num-md text-on-surface-variant">¥ 1,100</span>
              </div>
              <p class="font-body-md text-xs text-on-surface-variant">
                {{ t('周五晚周边活动取消导致 3 个长住订单提前离店。') }}
              </p>
            </div>
          </div>
        </div>
      </div>
      <!-- AI Suggested Action: Stepper Pattern (Spans 12 cols) -->
      <div
        class="col-span-12 bg-surface-bright rounded-xl border border-outline-variant/50 p-5 mt-2 flex items-center justify-between"
      >
        <div class="flex items-center gap-4 w-2/3">
          <div
            class="w-12 h-12 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center shrink-0"
          >
            <span class="material-symbols-outlined icon-fill">campaign</span>
          </div>
          <div>
            <h4 class="font-headline-md text-base text-on-surface m-0 mb-1">
              {{ t('AI 提议：启动国庆黄金周预热策略') }}
            </h4>
            <p class="font-body-md text-sm text-on-surface-variant m-0">
              {{ t('根据历史数据和当前搜索热度，建议上调基础房型 10% 价格，并推送早鸟套餐。') }}
            </p>
          </div>
        </div>
        <div class="flex gap-2 shrink-0">
          <button
            class="px-4 py-2 border border-outline-variant rounded-lg text-on-surface font-label-lg hover:bg-surface-container transition-colors"
          >
            {{ t('查看详情') }}
          </button>
          <!-- Guardrail Banner Style: R1 (Review Suggested) mapped to a button action -->
          <button
            class="px-4 py-2 bg-tertiary-container text-on-tertiary-container rounded-lg font-label-lg hover:bg-tertiary-container/80 transition-colors flex items-center gap-1 border border-tertiary/20"
          >
            <span class="material-symbols-outlined text-[16px]">bolt</span> {{ t('授权执行') }}
          </button>
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
