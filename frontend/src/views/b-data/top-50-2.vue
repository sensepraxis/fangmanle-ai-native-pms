<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// 数据来源：后端 demo 接口（确定性种子数据），实体 = semantic-history
// 列表/表格通过 v-for 渲染 rows；字段缺失时回退原型示例值，保证版式 1:1。
const hotelId = 1
const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('semantic-history')
})
</script>

<template>
  <div class="page">
    <!-- Header Section -->
    <div class="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background mb-2">{{ t('客群查询') }}</h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('基于自然语言的深度客群挖掘与智能分群') }}
        </p>
      </div>
      <div
        class="flex items-center gap-2 text-tertiary bg-tertiary-fixed/30 px-4 py-2 rounded-full border border-tertiary-fixed"
      >
        <span class="material-symbols-outlined text-sm">auto_awesome</span>
        <span class="font-label-lg text-label-lg">Powered by pgvector AI Retrieval</span>
      </div>
    </div>
    <!-- NL-First Search Bar (Bento Item 1 - Hero) -->
    <div
      class="bg-surface-container-lowest rounded-xl p-8 mb-8 border border-outline-variant relative overflow-hidden group"
    >
      <!-- Subtle AI Tinge -->
      <div class="absolute top-0 left-0 w-1 h-full bg-tertiary opacity-80"></div>
      <div class="relative z-10 max-w-3xl mx-auto">
        <div class="relative">
          <span
            class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-tertiary text-2xl"
            >search</span
          >
          <input
            class="w-full pl-14 pr-32 py-5 bg-surface rounded-full border-2 border-outline-variant focus:border-tertiary focus:ring-4 focus:ring-tertiary-fixed transition-all font-body-lg text-body-lg text-on-background shadow-sm placeholder:text-on-surface-variant/60"
            :placeholder="t('描述你想寻找的客群特征...')"
            type="text"
            value="找去年住过三次以上、喜欢高层且带孩子的回头客"
          />
          <button
            class="absolute right-3 top-1/2 -translate-y-1/2 bg-tertiary text-on-tertiary px-6 py-2 rounded-full font-label-lg text-label-lg hover:bg-tertiary/90 transition-colors shadow-md flex items-center gap-2"
          >
            {{ t('分析') }}
            <span class="material-symbols-outlined text-sm">arrow_forward</span>
          </button>
        </div>
        <!-- Suggestions -->
        <div class="mt-4 flex flex-wrap gap-2 justify-center">
          <span class="text-on-surface-variant font-label-lg text-label-lg mr-2 mt-1">{{
            t('AI 推荐查询:')
          }}</span>
          <button
            class="px-3 py-1 bg-surface-container rounded-full text-on-surface-variant font-label-lg text-label-lg hover:bg-surface-container-highest transition-colors border border-outline-variant/50"
          >
            {{ t('近三个月取消过订单的商务客') }}
          </button>
          <button
            class="px-3 py-1 bg-surface-container rounded-full text-on-surface-variant font-label-lg text-label-lg hover:bg-surface-container-highest transition-colors border border-outline-variant/50"
          >
            {{ t('周末入住倾向且评价提及"安静"的客人') }}
          </button>
        </div>
      </div>
      <!-- Atmospheric background element -->
      <div
        class="absolute -right-20 -bottom-20 w-64 h-64 bg-tertiary-fixed rounded-full blur-3xl opacity-20 pointer-events-none"
      ></div>
    </div>
    <!-- Results Section (Bento Grid) -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
      <!-- Summary Stats (Col Span 3) -->
      <div class="lg:col-span-3 flex flex-col gap-gutter">
        <div class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant">
          <h3 class="font-headline-md text-headline-md text-on-background mb-4">
            {{ t('分析洞察') }}
          </h3>
          <div class="space-y-4">
            <div>
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('匹配客群规模') }}
              </p>
              <p class="font-num-xl text-num-xl text-primary flex items-baseline gap-1">
                142
                <span class="font-body-md text-body-md text-on-surface-variant">{{ t('人') }}</span>
              </p>
            </div>
            <div class="h-px bg-outline-variant/50 w-full"></div>
            <div>
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('预计转化率提升') }}
              </p>
              <p class="font-num-xl text-num-xl text-tertiary flex items-baseline gap-1">
                +12.5%
                <span class="material-symbols-outlined text-sm text-tertiary">trending_up</span>
              </p>
            </div>
            <div class="h-px bg-outline-variant/50 w-full"></div>
            <div>
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-2">
                {{ t('语义解析构成') }}
              </p>
              <div class="flex flex-wrap gap-1">
                <span class="px-2 py-1 bg-primary-fixed text-on-primary-fixed rounded text-xs">{{
                  t('频次 &gt; 3')
                }}</span>
                <span class="px-2 py-1 bg-primary-fixed text-on-primary-fixed rounded text-xs">{{
                  t('偏好: 高层')
                }}</span>
                <span class="px-2 py-1 bg-primary-fixed text-on-primary-fixed rounded text-xs">{{
                  t('标签: 亲子')
                }}</span>
                <span class="px-2 py-1 bg-primary-fixed text-on-primary-fixed rounded text-xs">{{
                  t('时间: 去年')
                }}</span>
              </div>
            </div>
          </div>
        </div>
        <!-- Action Card -->
        <div
          class="bg-primary-container text-on-primary-container rounded-xl p-6 shadow-md relative overflow-hidden"
        >
          <div class="relative z-10">
            <h3 class="font-headline-md text-headline-md mb-2">{{ t('一键营销') }}</h3>
            <p class="font-body-md text-body-md mb-6 opacity-90">
              {{ t('为这142位高潜客户发送专属「亲子高层」周末特惠套餐。') }}
            </p>
            <button
              class="w-full bg-on-primary text-primary font-headline-md text-headline-md py-3 rounded-lg hover:bg-white/90 transition-colors shadow-sm flex items-center justify-center gap-2"
            >
              {{ t('创建营销活动') }}
              <span class="material-symbols-outlined">campaign</span>
            </button>
          </div>
          <span
            class="material-symbols-outlined absolute -right-4 -bottom-4 text-[120px] opacity-10 pointer-events-none"
            >mark_email_read</span
          >
        </div>
      </div>
      <!-- Detailed Results List (Col Span 9) -->
      <div
        class="lg:col-span-9 bg-surface-container-lowest rounded-xl border border-outline-variant overflow-hidden flex flex-col"
      >
        <div
          class="px-6 py-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low/50"
        >
          <h2 class="font-headline-md text-headline-md text-on-background flex items-center gap-2">
            {{ t('高匹配度客户列表') }}
            <span
              class="px-2 py-0.5 bg-surface-variant text-on-surface-variant rounded-full text-xs font-num-md"
              >Top 50</span
            >
          </h2>
          <div class="flex gap-2">
            <button
              class="p-2 text-on-surface-variant hover:bg-surface-variant rounded-lg transition-colors tooltip"
            >
              <span class="material-symbols-outlined">filter_list</span>
            </button>
            <button
              class="p-2 text-on-surface-variant hover:bg-surface-variant rounded-lg transition-colors"
            >
              <span class="material-symbols-outlined">download</span>
            </button>
          </div>
        </div>
        <div class="flex-1 overflow-auto p-6 space-y-4">
          <!-- Result Card 1 -->
          <div
            class="flex items-start gap-4 p-4 rounded-xl border border-outline-variant hover:bg-surface-container-low transition-colors group cursor-pointer relative"
          >
            <!-- Match Score Indicator -->
            <div class="absolute top-4 right-4 flex items-center gap-1 text-tertiary">
              <span class="material-symbols-outlined text-sm">network_node</span>
              <span class="font-num-md text-num-md">{{ t('98% 匹配') }}</span>
            </div>
            <div
              class="w-12 h-12 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-headline-md flex-shrink-0"
            >
              {{ t('王') }}
            </div>
            <div class="flex-1">
              <div class="flex items-baseline gap-3 mb-1">
                <h4 class="font-headline-md text-headline-md text-on-background">
                  {{ t('王女士 (V4)') }}
                </h4>
                <span class="font-num-md text-num-md text-on-surface-variant text-sm"
                  >ID: CUS-8921</span
                >
              </div>
              <div class="flex flex-wrap gap-2 mb-3">
                <span
                  class="inline-flex items-center gap-1 px-2 py-1 bg-surface-variant text-on-surface-variant rounded text-xs font-label-lg"
                >
                  <span class="material-symbols-outlined text-[14px]">hotel</span>
                  {{ t('去年入住 5 次') }}</span
                >
                <span
                  class="inline-flex items-center gap-1 px-2 py-1 bg-tertiary-fixed text-on-tertiary-fixed-variant rounded text-xs font-label-lg border border-tertiary-fixed-dim"
                >
                  <span class="material-symbols-outlined text-[14px]">psychology</span>
                  {{ t('偏好: 20层以上') }}</span
                >
                <span
                  class="inline-flex items-center gap-1 px-2 py-1 bg-surface-variant text-on-surface-variant rounded text-xs font-label-lg"
                >
                  <span class="material-symbols-outlined text-[14px]">child_care</span>
                  {{ t('历史带儿童: 2次') }}</span
                >
              </div>
              <p
                class="font-body-md text-body-md text-on-surface-variant text-sm bg-surface p-2 rounded-lg border-l-2 border-outline-variant"
              >
                <strong>{{ t('AI 摘要:') }}</strong>
                {{
                  t('高价值商务兼休闲客。上次入住(11月)留言要求安静且视野好。对房间设施要求较高。')
                }}
              </p>
            </div>
          </div>
          <!-- Result Card 2 -->
          <div
            class="flex items-start gap-4 p-4 rounded-xl border border-outline-variant hover:bg-surface-container-low transition-colors group cursor-pointer relative"
          >
            <div class="absolute top-4 right-4 flex items-center gap-1 text-tertiary">
              <span class="material-symbols-outlined text-sm">network_node</span>
              <span class="font-num-md text-num-md">{{ t('95% 匹配') }}</span>
            </div>
            <div
              class="w-12 h-12 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-headline-md flex-shrink-0"
            >
              {{ t('李') }}
            </div>
            <div class="flex-1">
              <div class="flex items-baseline gap-3 mb-1">
                <h4 class="font-headline-md text-headline-md text-on-background">
                  {{ t('李先生 (V3)') }}
                </h4>
                <span class="font-num-md text-num-md text-on-surface-variant text-sm"
                  >ID: CUS-3442</span
                >
              </div>
              <div class="flex flex-wrap gap-2 mb-3">
                <span
                  class="inline-flex items-center gap-1 px-2 py-1 bg-surface-variant text-on-surface-variant rounded text-xs font-label-lg"
                >
                  <span class="material-symbols-outlined text-[14px]">hotel</span>
                  {{ t('去年入住 3 次') }}</span
                >
                <span
                  class="inline-flex items-center gap-1 px-2 py-1 bg-tertiary-fixed text-on-tertiary-fixed-variant rounded text-xs font-label-lg border border-tertiary-fixed-dim"
                >
                  <span class="material-symbols-outlined text-[14px]">psychology</span>
                  {{ t('偏好: 景观房') }}</span
                >
                <span
                  class="inline-flex items-center gap-1 px-2 py-1 bg-surface-variant text-on-surface-variant rounded text-xs font-label-lg"
                >
                  <span class="material-symbols-outlined text-[14px]">child_care</span>
                  {{ t('历史带儿童: 3次') }}</span
                >
              </div>
              <p
                class="font-body-md text-body-md text-on-surface-variant text-sm bg-surface p-2 rounded-lg border-l-2 border-outline-variant"
              >
                <strong>{{ t('AI 摘要:') }}</strong>
                {{ t('典型的家庭周末游客户。喜欢在餐厅使用儿童套餐，曾多次预定高楼层行政房。') }}
              </p>
            </div>
          </div>
          <!-- Result Card 3 -->
          <div
            class="flex items-start gap-4 p-4 rounded-xl border border-outline-variant hover:bg-surface-container-low transition-colors group cursor-pointer relative"
          >
            <div class="absolute top-4 right-4 flex items-center gap-1 text-tertiary opacity-80">
              <span class="material-symbols-outlined text-sm">network_node</span>
              <span class="font-num-md text-num-md">{{ t('88% 匹配') }}</span>
            </div>
            <div
              class="w-12 h-12 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-headline-md flex-shrink-0"
            >
              {{ t('张') }}
            </div>
            <div class="flex-1">
              <div class="flex items-baseline gap-3 mb-1">
                <h4 class="font-headline-md text-headline-md text-on-background">
                  {{ t('张女士 (V2)') }}
                </h4>
                <span class="font-num-md text-num-md text-on-surface-variant text-sm"
                  >ID: CUS-1190</span
                >
              </div>
              <div class="flex flex-wrap gap-2 mb-3">
                <span
                  class="inline-flex items-center gap-1 px-2 py-1 bg-surface-variant text-on-surface-variant rounded text-xs font-label-lg"
                >
                  <span class="material-symbols-outlined text-[14px]">hotel</span>
                  {{ t('去年入住 4 次') }}</span
                >
                <span
                  class="inline-flex items-center gap-1 px-2 py-1 bg-tertiary-fixed text-on-tertiary-fixed-variant rounded text-xs font-label-lg border border-tertiary-fixed-dim"
                >
                  <span class="material-symbols-outlined text-[14px]">psychology</span>
                  {{ t('偏好: 远离电梯') }}</span
                >
                <span
                  class="inline-flex items-center gap-1 px-2 py-1 bg-surface-variant text-on-surface-variant rounded text-xs font-label-lg"
                >
                  <span class="material-symbols-outlined text-[14px]">child_care</span>
                  {{ t('历史带儿童: 1次') }}</span
                >
              </div>
              <p
                class="font-body-md text-body-md text-on-surface-variant text-sm bg-surface p-2 rounded-lg border-l-2 border-outline-variant"
              >
                <strong>{{ t('AI 摘要:') }}</strong>
                {{
                  t(
                    '语义关联较弱(未明确要求高层，但要求远离电梯通常意味着对环境有要求)。有过一次亲子入住记录。',
                  )
                }}
              </p>
            </div>
          </div>
          <div class="text-center pt-4 pb-2">
            <button class="text-primary font-label-lg text-label-lg hover:underline">
              {{ t('加载更多结果...') }}
            </button>
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
