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
    <!-- Header area -->
    <div class="mb-6 flex justify-between items-center shrink-0">
      <div>
        <h1 class="font-headline-lg text-headline-lg text-on-surface">{{ t('店长 AI 助理') }}</h1>
        <p class="text-body-md text-on-surface-variant mt-1">
          {{ t('自然语言数据分析与经营决策支持') }}
        </p>
      </div>
      <button
        class="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-full hover:bg-primary/90 transition-colors shadow-sm"
      >
        <span class="material-symbols-outlined text-sm">add</span>
        <span class="font-label-lg text-label-lg">{{ t('新对话') }}</span>
      </button>
    </div>
    <!-- Chat Workspace -->
    <div
      class="flex-1 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm flex flex-col overflow-hidden"
    >
      <!-- Chat History Area -->
      <div class="flex-1 overflow-y-auto p-6 flex flex-col gap-6 bg-surface-bright">
        <!-- System Welcome -->
        <div class="flex gap-4">
          <div
            class="w-10 h-10 rounded-full bg-tertiary-container flex items-center justify-center shrink-0"
          >
            <span class="material-symbols-outlined text-on-tertiary-container">robot_2</span>
          </div>
          <div class="flex-1 max-w-3xl">
            <div
              class="bg-surface-container-lowest p-4 rounded-2xl rounded-tl-none border border-outline-variant shadow-sm"
            >
              <p class="text-body-md text-on-surface">
                {{
                  t(
                    '您好！我是您的店长 AI 助理。您可以向我询问有关经营数据、房价策略或住客评价的任何问题。今天想了解什么？',
                  )
                }}
              </p>
              <div class="mt-4 flex flex-wrap gap-2">
                <button
                  class="px-3 py-1.5 bg-surface-container-low border border-outline-variant rounded-full text-label-lg font-label-lg text-on-surface-variant hover:bg-surface-container transition-colors flex items-center gap-1"
                >
                  <span class="material-symbols-outlined text-sm text-tertiary">trending_up</span>
                  {{ t('预测国庆期间的预订情况') }}
                </button>
                <button
                  class="px-3 py-1.5 bg-surface-container-low border border-outline-variant rounded-full text-label-lg font-label-lg text-on-surface-variant hover:bg-surface-container transition-colors flex items-center gap-1"
                >
                  <span class="material-symbols-outlined text-sm text-primary">balance</span>
                  {{ t('对比上个月的成本支出') }}
                </button>
                <button
                  class="px-3 py-1.5 bg-surface-container-low border border-outline-variant rounded-full text-label-lg font-label-lg text-on-surface-variant hover:bg-surface-container transition-colors flex items-center gap-1"
                >
                  <span class="material-symbols-outlined text-sm text-error"
                    >sentiment_dissatisfied</span
                  >
                  {{ t('分析最近差评的主要原因') }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <!-- User Message -->
        <div class="flex gap-4 flex-row-reverse">
          <div
            class="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center shrink-0"
          >
            <span class="material-symbols-outlined text-on-primary-container">person</span>
          </div>
          <div class="max-w-2xl">
            <div class="bg-primary text-on-primary p-4 rounded-2xl rounded-tr-none shadow-sm">
              <p class="text-body-md">
                {{ t('帮我算一下下周的预估平均净利润，并和历史同期做个对比。') }}
              </p>
            </div>
          </div>
        </div>
        <!-- AI Response with Data Component -->
        <div class="flex gap-4">
          <div
            class="w-10 h-10 rounded-full bg-tertiary-container flex items-center justify-center shrink-0"
          >
            <span class="material-symbols-outlined text-on-tertiary-container">robot_2</span>
          </div>
          <div class="flex-1 max-w-4xl">
            <div
              class="bg-surface-container-lowest p-5 rounded-2xl rounded-tl-none border border-outline-variant shadow-sm ai-glow ai-border-left"
            >
              <div class="flex items-center gap-2 mb-3 text-tertiary">
                <span class="material-symbols-outlined text-sm">arrow_back_ios_new</span>
                <span class="font-label-lg text-label-lg font-bold">{{ t('AI 数据洞察') }}</span>
              </div>
              <p class="text-body-md text-on-surface mb-4">
                {{
                  t(
                    '根据当前的预订进度（OTB）以及历史同期的转化模型预测，下周（10.23-10.29）的预估净利润情况如下：',
                  )
                }}
              </p>
              <!-- Insight Bento Card -->
              <div class="grid grid-cols-3 gap-4 mb-4">
                <div
                  class="bg-surface-container-low p-4 rounded-xl border border-outline-variant flex flex-col justify-between"
                >
                  <span class="text-label-lg text-on-surface-variant">{{ t('预估净利润') }}</span>
                  <div class="mt-2">
                    <span class="font-num-xl text-display-lg text-on-surface">¥42,500</span>
                    <div class="flex items-center text-primary mt-1 text-label-lg font-label-lg">
                      <span class="material-symbols-outlined text-sm mr-1">arrow_upward</span>
                      <span>{{ t('+12.4% 同期') }}</span>
                    </div>
                  </div>
                </div>
                <div
                  class="bg-surface-container-low p-4 rounded-xl border border-outline-variant flex flex-col justify-between"
                >
                  <span class="text-label-lg text-on-surface-variant">{{ t('预期 RevPAR') }}</span>
                  <div class="mt-2">
                    <span class="font-num-xl text-headline-lg text-on-surface">¥315</span>
                    <div class="flex items-center text-primary mt-1 text-label-lg font-label-lg">
                      <span class="material-symbols-outlined text-sm mr-1">arrow_upward</span>
                      <span>{{ t('+5.2% 同期') }}</span>
                    </div>
                  </div>
                </div>
                <div
                  class="bg-surface-container-low p-4 rounded-xl border border-outline-variant flex flex-col justify-between"
                >
                  <span class="text-label-lg text-on-surface-variant">{{ t('主要增长驱动') }}</span>
                  <div class="mt-2 flex flex-col gap-1">
                    <span
                      class="inline-block px-2 py-1 bg-surface-container-highest rounded text-label-lg text-on-surface"
                      >{{ t('商旅协议客 +15%') }}</span
                    >
                    <span
                      class="inline-block px-2 py-1 bg-surface-container-highest rounded text-label-lg text-on-surface"
                      >{{ t('高级房型预订 +8%') }}</span
                    >
                  </div>
                </div>
              </div>
              <p
                class="text-body-md text-on-surface-variant border-t border-outline-variant pt-3 mt-3"
              >
                <strong>{{ t('AI 建议：') }}</strong
                >{{
                  t(
                    '下周三、周四的商务预订需求强劲，建议略微上调基础房型的保留价（建议调整区间：+¥15~¥25），以最大化收益。',
                  )
                }}
              </p>
              <!-- Action buttons -->
              <div class="mt-4 flex gap-3">
                <button
                  class="px-4 py-2 bg-primary-container text-on-primary-container rounded-lg font-label-lg text-label-lg hover:bg-primary transition-colors flex items-center gap-2"
                >
                  <span class="material-symbols-outlined text-sm">tune</span>
                  {{ t('查看并应用调价建议') }}
                </button>
                <button
                  class="px-4 py-2 bg-surface text-primary border border-primary rounded-lg font-label-lg text-label-lg hover:bg-surface-container-low transition-colors"
                >
                  {{ t('下载详细报表') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- Input Area -->
      <div class="p-4 bg-surface-container-lowest border-t border-outline-variant shrink-0">
        <div
          class="max-w-4xl mx-auto relative flex items-end gap-2 bg-surface-container-low rounded-2xl p-2 border border-outline-variant focus-within:border-primary transition-colors"
        >
          <button
            class="p-2 text-on-surface-variant hover:text-primary transition-colors rounded-full shrink-0"
          >
            <span class="material-symbols-outlined">attach_file</span>
          </button>
          <textarea
            class="w-full bg-transparent border-none focus:ring-0 text-body-md text-on-surface resize-none py-2 px-1 max-h-32 min-h-[40px]"
            :placeholder="t(`输入您的问题，例如：'生成上个月的经营报表'...`)"
            rows="1"
          ></textarea>
          <button
            class="p-2 bg-primary text-on-primary rounded-full hover:bg-primary/90 transition-colors shrink-0 flex items-center justify-center h-10 w-10"
          >
            <span class="material-symbols-outlined">send</span>
          </button>
        </div>
        <div class="max-w-4xl mx-auto mt-2 text-center">
          <span class="text-xs text-on-surface-variant font-label-lg">{{
            t('AI 生成的内容可能存在误差，建议涉及重大经营决策时进行复核。')
          }}</span>
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
