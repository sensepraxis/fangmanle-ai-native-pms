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
    <div class="max-w-max-content-width mx-auto p-container-padding">
      <!-- Page Header -->
      <div class="mb-8">
        <h1 class="font-display-lg text-display-lg text-on-background mb-2">
          {{ t('行业指令模板库') }}
        </h1>
        <p class="font-body-lg text-body-lg text-on-surface-variant">
          {{ t('浏览、定制并一键部署高价值的自然语言AI指令至您的工作台。') }}
        </p>
      </div>
      <!-- Categories & Filters -->
      <div class="flex gap-4 mb-8 overflow-x-auto pb-2 no-scrollbar">
        <button
          class="px-6 py-2 rounded-full bg-primary text-on-primary font-label-lg text-label-lg shadow-sm whitespace-nowrap"
        >
          {{ t('全部模板') }}</button
        ><button
          class="px-6 py-2 rounded-full bg-surface-container text-on-surface-variant hover:bg-surface-container-high font-label-lg text-label-lg border border-outline-variant whitespace-nowrap transition-colors"
        >
          {{ t('收益增长') }}</button
        ><button
          class="px-6 py-2 rounded-full bg-surface-container text-on-surface-variant hover:bg-surface-container-high font-label-lg text-label-lg border border-outline-variant whitespace-nowrap transition-colors"
        >
          {{ t('服务优化') }}</button
        ><button
          class="px-6 py-2 rounded-full bg-surface-container text-on-surface-variant hover:bg-surface-container-high font-label-lg text-label-lg border border-outline-variant whitespace-nowrap transition-colors"
        >
          {{ t('宾客体验') }}</button
        ><button
          class="px-6 py-2 rounded-full bg-surface-container text-on-surface-variant hover:bg-surface-container-high font-label-lg text-label-lg border border-outline-variant whitespace-nowrap transition-colors"
        >
          {{ t('库存控制') }}
        </button>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
        <!-- Left Column: Featured & Popular -->
        <div class="lg:col-span-8 flex flex-col gap-6">
          <h2 class="font-headline-md text-headline-md text-on-background flex items-center gap-2">
            {{ t('官方推荐') }}
          </h2>
          <!-- Template Card 1 (Bento style) -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm hover:shadow-md transition-shadow p-6 flex flex-col gap-4 relative overflow-hidden group"
          >
            <!-- AI Tinge Highlight -->
            <div
              class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary group-hover:w-1.5 transition-all"
            ></div>
            <div class="flex justify-between items-start">
              <div>
                <span
                  class="inline-block px-2 py-1 rounded bg-tertiary-fixed text-on-tertiary-fixed font-label-lg text-label-lg text-xs mb-2"
                  >{{ t('收益增长') }}</span
                >
                <h3 class="font-headline-md text-headline-md text-on-background mb-1">
                  {{ t('竞对价格监控与预警') }}
                </h3>
              </div>
            </div>
            <div
              class="bg-surface-container-low p-4 rounded-lg font-body-md text-on-surface border border-outline-variant"
            >
              “{{ t('监测') }} 5km {{ t('半径内竞对') }} OTA {{ t('价格变动，若我的价格高') }} >{{
                t('10% 则告警。”')
              }}<br /><span class="text-on-surface-variant mt-2 block">{{
                t('“监控半径5公里内竞争对手的OTA价格变化，如果我的价格高出10%以上，请提醒我。”')
              }}</span>
            </div>
            <div class="flex items-center gap-2 mt-2">
              <span class="font-label-lg text-label-lg text-on-surface-variant text-sm">{{
                t('AI 逻辑：数据抓取、阈值告警、定时任务')
              }}</span>
            </div>
            <div class="flex justify-end gap-3 mt-4 pt-4 border-t border-outline-variant">
              <button
                class="px-4 py-2 rounded-lg text-primary hover:bg-primary-fixed transition-colors font-label-lg text-label-lg font-bold"
              >
                {{ t('自定义参数') }}</button
              ><button
                class="px-4 py-2 rounded-lg bg-primary text-on-primary hover:bg-primary-fixed-variant transition-colors font-label-lg text-label-lg font-bold flex items-center gap-2"
              >
                {{ t('部署到工作台') }}
              </button>
            </div>
          </div>
          <!-- Template Card 2 -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm hover:shadow-md transition-shadow p-6 flex flex-col gap-4 relative overflow-hidden group"
          >
            <div
              class="absolute left-0 top-0 bottom-0 w-1 bg-primary group-hover:w-1.5 transition-all"
            ></div>
            <div class="flex justify-between items-start">
              <div>
                <span
                  class="inline-block px-2 py-1 rounded bg-primary-fixed text-on-primary-fixed font-label-lg text-label-lg text-xs mb-2"
                  >{{ t('库存控制') }}</span
                >
                <h3 class="font-headline-md text-headline-md text-on-background mb-1">
                  {{ t('智能房态降级保护') }}
                </h3>
              </div>
            </div>
            <div
              class="bg-surface-container-low p-4 rounded-lg font-body-md text-on-surface border border-outline-variant"
            >
              {{ t('“若 16:00 前入住率达 85%，自动关闭折扣渠道并将剩余标准房留给散客。”')
              }}<br /><span class="text-on-surface-variant mt-2 block">{{
                t('“如果下午4点入住率达到85%，自动关闭折扣渠道，并将剩余标准客房保留给上门散客。”')
              }}</span>
            </div>
            <div class="flex items-center gap-2 mt-2">
              <span class="font-label-lg text-label-lg text-on-surface-variant text-sm">{{
                t('AI 逻辑：实时入住率检查、渠道管理 API 推送')
              }}</span>
            </div>
            <div class="flex justify-end gap-3 mt-4 pt-4 border-t border-outline-variant">
              <button
                class="px-4 py-2 rounded-lg text-primary hover:bg-primary-fixed transition-colors font-label-lg text-label-lg font-bold"
              >
                {{ t('自定义参数') }}</button
              ><button
                class="px-4 py-2 rounded-lg bg-primary text-on-primary hover:bg-primary-fixed-variant transition-colors font-label-lg text-label-lg font-bold flex items-center gap-2"
              >
                {{ t('部署到工作台') }}
              </button>
            </div>
          </div>
        </div>
        <!-- Right Column: Community & Stats -->
        <div class="lg:col-span-4 flex flex-col gap-6">
          <!-- Stats Card -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
          >
            <h3 class="font-headline-md text-headline-md text-on-background mb-4">
              {{ t('库区概览') }}
            </h3>
            <div class="space-y-4">
              <div class="flex justify-between items-center border-b border-outline-variant pb-2">
                <span class="font-body-md text-on-surface-variant">{{ t('可用模板总数') }}</span
                ><span class="font-num-md text-num-md font-bold text-on-background">1,204</span>
              </div>
              <div class="flex justify-between items-center border-b border-outline-variant pb-2">
                <span class="font-body-md text-on-surface-variant">{{ t('本周新增') }}}</span
                ><span class="font-num-md text-num-md font-bold text-primary">+42</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="font-body-md text-on-surface-variant">{{ t('您已部署的指令') }}}</span
                ><span class="font-num-md text-num-md font-bold text-on-background">7</span>
              </div>
            </div>
          </div>
          <!-- Community Favorites -->
          <h2
            class="font-headline-md text-headline-md text-on-background flex items-center gap-2 mt-2"
          >
            {{ t('社区热门') }}
          </h2>
          <div class="space-y-3">
            <!-- Mini Card 1 -->
            <div
              class="bg-surface-container-lowest rounded-lg border border-outline-variant p-4 flex gap-3 hover:bg-surface-container-low transition-colors cursor-pointer"
            >
              <div
                class="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center shrink-0"
              ></div>
              <div>
                <h4 class="font-label-lg text-label-lg font-bold text-on-background line-clamp-1">
                  {{ t('退房后自动指派清洁工单') }}
                </h4>
                <p class="font-body-md text-xs text-on-surface-variant mt-1 line-clamp-2">
                  {{ t('“当房态变为‘已退房’时，自动分配……”') }}
                </p>
                <div class="flex items-center gap-1 mt-2 text-xs text-on-surface-variant">
                  8,932
                </div>
              </div>
            </div>
            <!-- Mini Card 2 -->
            <div
              class="bg-surface-container-lowest rounded-lg border border-outline-variant p-4 flex gap-3 hover:bg-surface-container-low transition-colors cursor-pointer"
            >
              <div
                class="w-10 h-10 rounded-full bg-tertiary-container flex items-center justify-center shrink-0"
              ></div>
              <div>
                <h4 class="font-label-lg text-label-lg font-bold text-on-background line-clamp-1">
                  {{ t('生成个性化欢迎信') }}
                </h4>
                <p class="font-body-md text-xs text-on-surface-variant mt-1 line-clamp-2">
                  {{ t('“为回头客起草欢迎邮件，提及他们过往入住……”') }}
                </p>
                <div class="flex items-center gap-1 mt-2 text-xs text-on-surface-variant">
                  5,421
                </div>
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
