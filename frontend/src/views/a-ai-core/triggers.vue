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
    <!-- Header Bar -->
    <div
      class="bg-surface-container-lowest px-6 py-4 flex justify-between items-center border-b border-outline-variant shrink-0"
    >
      <div>
        <h1 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">account_tree</span>
          {{ t('指令执行逻辑编排') }}
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant mt-1">
          {{ t('工作流: 客诉噪音自动处理与补偿') }}
        </p>
      </div>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 border border-outline-variant rounded-lg text-on-surface hover:bg-surface-container font-label-lg transition-colors"
        >
          {{ t('取消') }}
        </button>
        <button
          class="px-4 py-2 bg-primary text-on-primary rounded-lg hover:bg-primary/90 font-label-lg transition-colors flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-[18px]">save</span>
          {{ t('保存并激活') }}
        </button>
      </div>
    </div>
    <!-- Editor Workspace -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Left Panel: Nodes Library -->
      <aside
        class="w-[280px] bg-surface-container-lowest border-r border-outline-variant flex flex-col overflow-y-auto shrink-0"
      >
        <div
          class="p-4 border-b border-outline-variant font-headline-md text-headline-md flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-on-surface-variant">library_add</span>
          {{ t('节点资源库') }}
        </div>
        <div class="p-4 space-y-6">
          <!-- Category -->
          <div>
            <h3
              class="font-label-lg text-label-lg text-on-surface-variant mb-3 px-1 uppercase tracking-wider"
            >
              {{ t('触发器 (Triggers)') }}
            </h3>
            <div class="space-y-2">
              <div
                class="flex items-center gap-3 p-3 bg-surface border border-outline-variant rounded-lg cursor-grab hover:border-primary hover:shadow-sm transition-all"
              >
                <div
                  class="w-8 h-8 rounded bg-secondary-container flex items-center justify-center text-on-secondary-container"
                >
                  <span class="material-symbols-outlined text-[20px]">forum</span>
                </div>
                <span class="font-body-md text-body-md">{{ t('接收客诉消息') }}</span>
              </div>
              <div
                class="flex items-center gap-3 p-3 bg-surface border border-outline-variant rounded-lg cursor-grab hover:border-primary hover:shadow-sm transition-all"
              >
                <div
                  class="w-8 h-8 rounded bg-secondary-container flex items-center justify-center text-on-secondary-container"
                >
                  <span class="material-symbols-outlined text-[20px]">schedule</span>
                </div>
                <span class="font-body-md text-body-md">{{ t('定时任务') }}</span>
              </div>
            </div>
          </div>
          <!-- Category -->
          <div>
            <h3
              class="font-label-lg text-label-lg text-tertiary mb-3 px-1 flex items-center gap-1 uppercase tracking-wider"
            >
              <span class="material-symbols-outlined text-[16px]">auto_awesome</span>
              {{ t('AI 技能 (Skills)') }}
            </h3>
            <div class="space-y-2">
              <div
                class="flex items-center gap-3 p-3 bg-tertiary-fixed border border-tertiary/30 rounded-lg cursor-grab hover:border-tertiary hover:shadow-sm transition-all"
              >
                <div
                  class="w-8 h-8 rounded bg-tertiary text-on-tertiary flex items-center justify-center"
                >
                  <span class="material-symbols-outlined text-[20px]">psychology</span>
                </div>
                <span class="font-body-md text-body-md text-on-tertiary-container">{{
                  t('意图与实体提取')
                }}</span>
              </div>
              <div
                class="flex items-center gap-3 p-3 bg-tertiary-fixed border border-tertiary/30 rounded-lg cursor-grab hover:border-tertiary hover:shadow-sm transition-all"
              >
                <div
                  class="w-8 h-8 rounded bg-tertiary text-on-tertiary flex items-center justify-center"
                >
                  <span class="material-symbols-outlined text-[20px]">translate</span>
                </div>
                <span class="font-body-md text-body-md text-on-tertiary-container">{{
                  t('多语言翻译')
                }}</span>
              </div>
            </div>
          </div>
          <!-- Category -->
          <div>
            <h3
              class="font-label-lg text-label-lg text-on-surface-variant mb-3 px-1 uppercase tracking-wider"
            >
              {{ t('动作 (Actions)') }}
            </h3>
            <div class="space-y-2">
              <div
                class="flex items-center gap-3 p-3 bg-surface border border-outline-variant rounded-lg cursor-grab hover:border-primary hover:shadow-sm transition-all"
              >
                <div
                  class="w-8 h-8 rounded bg-primary-container flex items-center justify-center text-primary"
                >
                  <span class="material-symbols-outlined text-[20px]">notifications_active</span>
                </div>
                <span class="font-body-md text-body-md">{{ t('发送内部通知') }}</span>
              </div>
              <div
                class="flex items-center gap-3 p-3 bg-surface border border-outline-variant rounded-lg cursor-grab hover:border-primary hover:shadow-sm transition-all"
              >
                <div
                  class="w-8 h-8 rounded bg-primary-container flex items-center justify-center text-primary"
                >
                  <span class="material-symbols-outlined text-[20px]">local_activity</span>
                </div>
                <span class="font-body-md text-body-md">{{ t('发放权益/卡券') }}</span>
              </div>
            </div>
          </div>
        </div>
      </aside>
      <!-- Center Canvas: Flow Editor -->
      <section class="flex-1 canvas-bg relative overflow-auto p-12 flex flex-col items-center">
        <!-- Node 1: Trigger -->
        <div
          class="relative w-[320px] bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm z-10 hover:shadow-md transition-shadow"
        >
          <div
            class="bg-secondary-container text-on-secondary-container px-4 py-2 rounded-t-xl flex justify-between items-center border-b border-outline-variant"
          >
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-[18px]">forum</span>
              <span class="font-label-lg text-label-lg font-bold">{{ t('触发器') }}</span>
            </div>
            <span
              class="material-symbols-outlined text-outline cursor-pointer hover:text-on-surface"
              >more_vert</span
            >
          </div>
          <div class="p-4">
            <div class="font-body-md text-body-md font-medium">{{ t('接收客诉消息') }}</div>
            <div
              class="font-label-lg text-label-lg text-on-surface-variant mt-2 bg-surface-container-low p-2 rounded"
            >
              {{ t('来源: 所有渠道 (App, 前台, 电话)') }}
            </div>
          </div>
          <!-- Connection Port Bottom -->
          <div
            class="absolute -bottom-2 left-1/2 -translate-x-1/2 w-4 h-4 bg-surface border-2 border-outline-variant rounded-full cursor-crosshair"
          ></div>
        </div>
        <!-- Connector Line Vertical -->
        <div class="w-[2px] h-[40px] bg-outline-variant"></div>
        <!-- Node 2: AI Analysis -->
        <div
          class="relative w-[340px] bg-surface-container-lowest border-2 border-tertiary rounded-xl shadow-[0_0_15px_rgba(140,51,179,0.1)] z-10"
        >
          <div
            class="bg-tertiary-fixed text-on-tertiary-container px-4 py-2 rounded-t-xl flex justify-between items-center border-b border-tertiary/20"
          >
            <div class="flex items-center gap-2">
              <span
                class="material-symbols-outlined text-[18px] text-tertiary"
                style="font-variation-settings: 'FILL' 1"
                >auto_awesome</span
              >
              <span class="font-label-lg text-label-lg font-bold">{{ t('AI 技能分析') }}</span>
            </div>
          </div>
          <div class="p-4">
            <div class="font-body-md text-body-md font-medium">{{ t('意图与实体提取') }}</div>
            <div class="mt-3 space-y-2">
              <div class="flex items-center gap-2 text-label-lg">
                <span class="text-on-surface-variant w-16">{{ t('提取目标:') }}</span>
                <span class="bg-surface-container p-1 rounded font-num-md text-primary">{{
                  t('"噪音", "太吵"')
                }}</span>
              </div>
              <div class="flex items-center gap-2 text-label-lg">
                <span class="text-on-surface-variant w-16">{{ t('判断条件:') }}</span>
                <span class="text-on-surface">{{ t('包含上述关键字 -&gt; 分支A') }}</span>
              </div>
            </div>
          </div>
          <!-- Connection Ports -->
          <div
            class="absolute -top-2 left-1/2 -translate-x-1/2 w-4 h-4 bg-tertiary border-2 border-surface rounded-full"
          ></div>
          <div
            class="absolute -bottom-2 left-1/2 -translate-x-1/2 w-4 h-4 bg-tertiary border-2 border-surface rounded-full cursor-crosshair"
          ></div>
        </div>
        <!-- Split Connectors -->
        <div class="flex w-[400px] justify-between relative mt-[40px]">
          <!-- Horizontal line -->
          <div
            class="absolute top-0 left-[25%] right-[25%] h-[2px] bg-outline-variant -mt-[40px]"
          ></div>
          <!-- Vertical drops -->
          <div class="w-[2px] h-[40px] bg-outline-variant absolute left-[25%] -top-[40px]"></div>
          <div class="w-[2px] h-[40px] bg-outline-variant absolute right-[25%] -top-[40px]"></div>
          <!-- Action 1: Notify -->
          <div
            class="relative w-[240px] bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm z-10 hover:shadow-md transition-shadow -ml-[60px]"
          >
            <div
              class="bg-primary-container text-on-primary-container px-3 py-2 rounded-t-xl flex items-center gap-2 border-b border-outline-variant"
            >
              <span class="material-symbols-outlined text-[18px]">notifications_active</span>
              <span class="font-label-lg text-label-lg font-bold">{{ t('动作: 通知') }}</span>
            </div>
            <div class="p-4">
              <div class="font-body-md text-body-md">{{ t('发送至客房主管') }}</div>
              <div
                class="font-label-lg text-label-lg text-on-surface-variant mt-2 border border-dashed border-outline-variant p-2 rounded text-xs"
              >
                {{ t('{room} 报告噪音问题，请立即核实。', { room: t('房间号') }) }}
              </div>
            </div>
            <div
              class="absolute -top-2 left-1/2 -translate-x-1/2 w-4 h-4 bg-surface border-2 border-outline-variant rounded-full"
            ></div>
          </div>
          <!-- Action 2: Coupon -->
          <div
            class="relative w-[240px] bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm z-10 hover:shadow-md transition-shadow -mr-[60px]"
          >
            <div
              class="bg-primary-container text-on-primary-container px-3 py-2 rounded-t-xl flex items-center gap-2 border-b border-outline-variant"
            >
              <span class="material-symbols-outlined text-[18px]">local_activity</span>
              <span class="font-label-lg text-label-lg font-bold">{{ t('动作: 发放') }}</span>
            </div>
            <div class="p-4">
              <div class="font-body-md text-body-md">{{ t('发放早餐券') }}</div>
              <div
                class="font-label-lg text-label-lg text-on-surface-variant mt-2 bg-surface-container-low p-2 rounded text-xs flex justify-between"
              >
                <span>{{ t('类型: 免费双早') }}</span>
                <span class="text-primary font-num-md">x1</span>
              </div>
            </div>
            <div
              class="absolute -top-2 left-1/2 -translate-x-1/2 w-4 h-4 bg-surface border-2 border-outline-variant rounded-full"
            ></div>
          </div>
        </div>
      </section>
      <!-- Right Panel: Live Simulation -->
      <aside
        class="w-[320px] bg-surface-container-lowest border-l border-outline-variant flex flex-col shrink-0"
      >
        <div class="p-4 border-b border-outline-variant flex items-center justify-between">
          <div class="font-headline-md text-headline-md flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">play_circle</span>
            {{ t('实时模拟测试') }}
          </div>
        </div>
        <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
          <!-- Input Test Data -->
          <div class="space-y-3">
            <label class="font-label-lg text-label-lg font-bold text-on-surface block">{{
              t('输入测试数据')
            }}</label>
            <textarea
              class="w-full h-24 bg-surface border border-outline-variant rounded-lg p-3 text-body-md text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none resize-none"
              :placeholder="t('输入模拟的客诉内容...')"
              >{{ t('“隔壁房间一直在放很大声的音乐，根本没法休息，太吵了！”') }}</textarea>
            <button
              class="w-full py-2 bg-surface-container-high hover:bg-surface-variant text-on-surface rounded-lg font-label-lg transition-colors border border-outline-variant flex items-center justify-center gap-2"
            >
              <span class="material-symbols-outlined text-[18px]">history</span>
              {{ t('从历史数据随机抽取') }}
            </button>
            <button
              class="w-full py-2 bg-primary text-on-primary rounded-lg font-label-lg hover:bg-primary/90 transition-colors shadow-sm flex items-center justify-center gap-2"
            >
              <span class="material-symbols-outlined text-[18px]">science</span>
              {{ t('运行测试') }}
            </button>
          </div>
          <hr class="border-outline-variant" />
          <!-- Execution Log -->
          <div>
            <h4 class="font-label-lg text-label-lg font-bold text-on-surface mb-4">
              {{ t('执行日志 (AI 推理过程)') }}
            </h4>
            <div class="relative pl-6 space-y-4">
              <!-- Timeline line -->
              <div class="absolute left-[11px] top-2 bottom-2 w-[2px] bg-surface-variant"></div>
              <!-- Step 1 -->
              <div class="relative">
                <div
                  class="absolute -left-[27px] top-1 w-[14px] h-[14px] rounded-full bg-primary ring-4 ring-surface-container-lowest"
                ></div>
                <div class="font-label-lg text-label-lg text-on-surface font-medium">
                  {{ t('接收到输入') }}
                </div>
                <div class="text-xs text-on-surface-variant mt-1 font-num-md">0ms</div>
              </div>
              <!-- Step 2 (AI) -->
              <div class="relative">
                <div
                  class="absolute -left-[27px] top-1 w-[14px] h-[14px] rounded-full bg-tertiary ring-4 ring-surface-container-lowest"
                ></div>
                <div
                  class="font-label-lg text-label-lg text-tertiary font-bold flex items-center gap-1"
                >
                  <span class="material-symbols-outlined text-[14px]">auto_awesome</span>
                  {{ t('AI 实体提取成功') }}
                </div>
                <div
                  class="bg-tertiary-fixed border border-tertiary/20 p-2 rounded mt-2 text-sm text-on-tertiary-container"
                >
                  {{ t('匹配到关键词:') }}
                  <strong class="text-tertiary font-num-md">{{ t('"太吵"') }}</strong
                  >.<br />
                  {{ t('意图分类: 噪音投诉 (置信度 98%)') }}
                </div>
                <div class="text-xs text-on-surface-variant mt-1 font-num-md">124ms</div>
              </div>
              <!-- Step 3 -->
              <div class="relative">
                <div
                  class="absolute -left-[27px] top-1 w-[14px] h-[14px] rounded-full bg-primary ring-4 ring-surface-container-lowest"
                ></div>
                <div class="font-label-lg text-label-lg text-on-surface font-medium">
                  {{ t('触发分支 A (通知主管)') }}
                </div>
                <div class="text-xs text-on-surface-variant mt-1 font-num-md">130ms</div>
              </div>
              <!-- Step 4 -->
              <div class="relative">
                <div
                  class="absolute -left-[27px] top-1 w-[14px] h-[14px] rounded-full bg-primary ring-4 ring-surface-container-lowest"
                ></div>
                <div class="font-label-lg text-label-lg text-on-surface font-medium">
                  {{ t('触发分支 B (发放补偿)') }}
                </div>
                <div class="text-xs text-on-surface-variant mt-1 font-num-md">135ms</div>
              </div>
              <!-- Success Banner -->
              <div
                class="mt-4 bg-surface-low border border-outline-variant text-on-surface-variant p-3 rounded-lg flex items-start gap-2"
              >
                <span class="material-symbols-outlined text-[20px]">check_circle</span>
                <div>
                  <div class="font-label-lg font-bold">{{ t('模拟运行成功') }}</div>
                  <div class="text-xs mt-1">{{ t('流程按预期执行完毕，无错误发生。') }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>
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
