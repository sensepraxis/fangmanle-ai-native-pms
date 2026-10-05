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
    <!-- Header -->
    <header
      class="h-16 flex items-center justify-center px-6 bg-surface-container-lowest border-b border-outline-variant shrink-0"
    >
      <h1 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
        <span
          class="material-symbols-outlined text-tertiary"
          data-icon="sparkles"
          data-weight="fill"
          style="font-variation-settings: 'FILL' 1"
          >arrow_back_ios_new</span
        >
        AI Workbench
      </h1>
    </header>
    <!-- Chat Canvas -->
    <div class="flex-1 overflow-y-auto px-4 md:px-24 py-8 hide-scrollbar flex flex-col gap-8 pb-32">
      <!-- Welcome / Empty State (Initially visible, hides when chatting) -->
      <div class="flex flex-col items-center justify-center text-center mt-12 mb-8">
        <div
          class="w-16 h-16 bg-tertiary-container text-on-tertiary-container rounded-2xl flex items-center justify-center mb-4 shadow-sm ai-glow"
        >
          <span class="material-symbols-outlined text-4xl" data-icon="robot_2">robot_2</span>
        </div>
        <h2 class="font-display-lg text-display-lg text-on-surface mb-2">
          {{ t('您好，我是小智') }}
        </h2>
        <p class="font-body-lg text-body-lg text-on-surface-variant max-w-lg">
          {{ t('您的AI智能管家。您可以直接通过自然语言与我对话，管理房态、分析收益或处理订单。') }}
        </p>
        <!-- Suggested Prompts Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8 w-full max-w-3xl">
          <button
            class="flex items-start gap-3 p-4 bg-surface-container-lowest rounded-xl border border-outline-variant hover:border-tertiary hover:shadow-sm transition-all text-left"
          >
            <span class="material-symbols-outlined text-tertiary mt-1" data-icon="monitoring"
              >monitoring</span
            >
            <div>
              <div class="font-label-lg text-label-lg text-on-surface">
                {{ t('生成上周收益报告') }}
              </div>
              <div class="font-body-md text-body-md text-on-surface-variant mt-1 text-sm">
                "Generate revenue report for last week"
              </div>
            </div>
          </button>
          <button
            class="flex items-start gap-3 p-4 bg-surface-container-lowest rounded-xl border border-outline-variant hover:border-tertiary hover:shadow-sm transition-all text-left"
          >
            <span class="material-symbols-outlined text-tertiary mt-1" data-icon="timeline"
              >timeline</span
            >
            <div>
              <div class="font-label-lg text-label-lg text-on-surface">
                {{ t('预测下个假期的入住率') }}
              </div>
              <div class="font-body-md text-body-md text-on-surface-variant mt-1 text-sm">
                "Predict occupancy for next holiday"
              </div>
            </div>
          </button>
          <button
            class="flex items-start gap-3 p-4 bg-surface-container-lowest rounded-xl border border-outline-variant hover:border-tertiary hover:shadow-sm transition-all text-left"
          >
            <span class="material-symbols-outlined text-tertiary mt-1" data-icon="cleaning_services"
              >cleaning_services</span
            >
            <div>
              <div class="font-label-lg text-label-lg text-on-surface">
                {{ t('显示5楼的脏房') }}
              </div>
              <div class="font-body-md text-body-md text-on-surface-variant mt-1 text-sm">
                "Show me dirty rooms on 5th floor"
              </div>
            </div>
          </button>
          <button
            class="flex items-start gap-3 p-4 bg-surface-container-lowest rounded-xl border border-outline-variant hover:border-tertiary hover:shadow-sm transition-all text-left"
          >
            <span class="material-symbols-outlined text-tertiary mt-1" data-icon="price_change"
              >price_change</span
            >
            <div>
              <div class="font-label-lg text-label-lg text-on-surface">
                {{ t('分析周边竞对价格并建议调价') }}
              </div>
              <div class="font-body-md text-body-md text-on-surface-variant mt-1 text-sm">
                "Analyze competitor pricing..."
              </div>
            </div>
          </button>
        </div>
      </div>
      <!-- Example Conversation (Mocked) -->
      <!-- User Message -->
      <div class="flex justify-end w-full max-w-4xl mx-auto">
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-2xl rounded-tr-sm px-6 py-4 max-w-[80%] shadow-sm"
        >
          <p class="font-body-lg text-body-lg text-on-surface">
            {{ t('显示5楼目前的脏房状态，并指派给今天值班的阿姨。') }}
          </p>
        </div>
      </div>
      <!-- AI Response -->
      <div class="flex justify-start w-full max-w-4xl mx-auto gap-4">
        <div
          class="w-8 h-8 rounded-full bg-tertiary-container text-on-tertiary-container flex items-center justify-center shrink-0 mt-1"
        >
          <span class="material-symbols-outlined text-sm" data-icon="sparkles" data-weight="fill"
            >arrow_back_ios_new</span
          >
        </div>
        <div class="flex-1 flex flex-col gap-3">
          <p class="font-body-lg text-body-lg text-on-surface">
            {{ t('好的，已为您查出5楼目前有 3 间脏房。今天排班的客房服务员是') }}
            <strong>{{ t('张阿姨') }}</strong> {{ t('和') }} <strong>{{ t('李阿姨') }}</strong
            >{{ t('。我已经为您生成了分配建议，请确认执行：') }}
          </p>
          <!-- AI Generated Embedded UI Component -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant p-5 shadow-sm ai-border-glow mt-2"
          >
            <div class="flex justify-between items-center mb-4">
              <h3 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined text-tertiary" data-icon="room_service"
                  >room_service</span
                >
                {{ t('客房清洁分配单') }}
              </h3>
              <span
                class="bg-surface-container px-2 py-1 rounded text-sm text-on-surface-variant font-num-md"
                >{{ t('14:30 PM 更新') }}</span
              >
            </div>
            <div class="space-y-3">
              <!-- Room Item -->
              <div
                class="flex items-center justify-between p-3 bg-surface-container-low rounded-lg border border-transparent hover:border-outline-variant transition-colors"
              >
                <div class="flex items-center gap-4">
                  <div
                    class="w-12 h-12 bg-tertiary-container rounded flex items-center justify-center text-on-tertiary font-num-xl"
                  >
                    502
                  </div>
                  <div>
                    <div class="font-label-lg text-label-lg text-on-surface">
                      {{ t('豪华大床房') }}
                    </div>
                    <div class="text-sm text-on-surface-variant">
                      {{ t('退房打扫 (预计 45 分钟)') }}
                    </div>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <select
                    class="bg-surface-container-lowest border-outline-variant rounded-md text-sm text-on-surface px-3 py-1.5 focus:ring-primary focus:border-primary"
                  >
                    <option>{{ t('分配给 张阿姨') }}</option>
                    <option>{{ t('分配给 李阿姨') }}</option>
                  </select>
                </div>
              </div>
              <!-- Room Item -->
              <div
                class="flex items-center justify-between p-3 bg-surface-container-low rounded-lg border border-transparent hover:border-outline-variant transition-colors"
              >
                <div class="flex items-center gap-4">
                  <div
                    class="w-12 h-12 bg-tertiary-container rounded flex items-center justify-center text-on-tertiary font-num-xl"
                  >
                    508
                  </div>
                  <div>
                    <div class="font-label-lg text-label-lg text-on-surface">
                      {{ t('标准双床房') }}
                    </div>
                    <div class="text-sm text-on-surface-variant">
                      {{ t('续住打扫 (预计 20 分钟)') }}
                    </div>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <select
                    class="bg-surface-container-lowest border-outline-variant rounded-md text-sm text-on-surface px-3 py-1.5 focus:ring-primary focus:border-primary"
                  >
                    <option>{{ t('分配给 李阿姨') }}</option>
                    <option>{{ t('分配给 张阿姨') }}</option>
                  </select>
                </div>
              </div>
            </div>
            <div class="mt-4 pt-4 border-t border-outline-variant flex justify-end gap-3">
              <button
                class="px-4 py-2 rounded-lg font-label-lg text-on-surface-variant hover:bg-surface-container transition-colors"
              >
                {{ t('取消') }}
              </button>
              <button
                class="px-4 py-2 rounded-lg font-label-lg bg-primary text-on-primary hover:bg-primary-container transition-colors flex items-center gap-2"
              >
                <span class="material-symbols-outlined text-sm" data-icon="send">send</span>
                {{ t('确认并发送通知') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Input Area (NL Command Bar) -->
    <div
      class="absolute bottom-0 left-0 w-full bg-gradient-to-t from-surface-container-low via-surface-container-low to-transparent pt-10 pb-6 px-4 md:px-24"
    >
      <div class="max-w-4xl mx-auto relative">
        <!-- Floating Action / Context Chips above input -->
        <div class="flex gap-2 mb-3 overflow-x-auto hide-scrollbar">
          <button
            class="shrink-0 bg-surface-container-lowest border border-outline-variant rounded-full px-4 py-1.5 text-sm text-on-surface hover:bg-surface-container transition-colors flex items-center gap-1"
          >
            <span class="material-symbols-outlined text-xs text-primary" data-icon="add_circle"
              >add_circle</span
            >
            {{ t('新建工单') }}
          </button>
          <button
            class="shrink-0 bg-surface-container-lowest border border-outline-variant rounded-full px-4 py-1.5 text-sm text-on-surface hover:bg-surface-container transition-colors flex items-center gap-1"
          >
            <span class="material-symbols-outlined text-xs text-primary" data-icon="event"
              >event</span
            >
            {{ t('查看排班') }}
          </button>
        </div>
        <div
          class="relative bg-surface-container-lowest rounded-2xl shadow-md border border-outline-variant focus-within:border-tertiary focus-within:ring-1 focus-within:ring-tertiary transition-all ai-glow flex items-center min-h-[60px] pl-4 pr-2"
        >
          <span class="material-symbols-outlined text-tertiary mr-2 shrink-0" data-icon="sparkles"
            >arrow_back_ios_new</span
          >
          <textarea
            class="w-full bg-transparent border-none focus:ring-0 resize-none py-4 text-on-surface placeholder-on-surface-variant font-body-lg hide-scrollbar"
            :placeholder="t('让 AI 预测需求或调整模型…')"
            rows="1"
            style="max-height: 200px"
          ></textarea>
          <div class="flex items-center gap-2 shrink-0">
            <div
              class="hidden sm:flex items-center text-xs text-outline font-num-md bg-surface-container px-2 py-1 rounded"
            >
              ⌘ K
            </div>
            <button
              class="w-10 h-10 rounded-xl bg-tertiary text-on-tertiary flex items-center justify-center hover:bg-tertiary-container hover:text-on-tertiary-container transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span class="material-symbols-outlined" data-icon="arrow_upward">arrow_upward</span>
            </button>
          </div>
        </div>
        <div class="text-center mt-2">
          <span class="text-xs text-on-surface-variant opacity-70">{{
            t('AI 可能会产生不准确的信息，请在执行关键操作前仔细核对。')
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
