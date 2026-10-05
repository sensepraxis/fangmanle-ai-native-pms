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
    <div class="mb-6 flex justify-between items-end">
      <div>
        <h1 class="text-display-lg font-display-lg text-on-surface">{{ t('自动化申诉工作台') }}</h1>
        <p class="text-body-lg font-body-lg text-on-surface-variant mt-1">
          {{ t('OTA 评论的 AI 辅助争议处理') }}
        </p>
      </div>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 border border-outline rounded-lg text-label-lg font-label-lg text-on-surface hover:bg-surface-variant transition-colors flex items-center gap-2"
        >
          {{ t('查看历史') }}
        </button>
      </div>
    </div>
    <div class="grid grid-cols-12 gap-gutter">
      <!-- Left Column: Context & Evidence -->
      <div class="col-span-12 lg:col-span-4 flex flex-col gap-gutter">
        <!-- Targeted Review Card -->
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 flex flex-col gap-4"
        >
          <div class="flex justify-between items-start border-b border-outline-variant pb-4">
            <div>
              <span
                class="inline-block px-2 py-1 bg-error-container text-on-error-container text-xs rounded font-bold mb-2"
                >{{ t('携程 - 1 星') }}</span
              >
              <h3 class="text-headline-md font-headline-md text-on-surface">
                {{ t('“房间脏且空调不工作”') }}
              </h3>
              <p class="text-label-lg font-label-lg text-on-surface-variant mt-1">
                {{ t('订单 #88921 • 304 房 • 2 天前退房') }}
              </p>
            </div>
          </div>
          <div class="text-body-md font-body-md text-on-surface-variant">
            {{ t('“糟糕体验。浴室发现头发，空调整夜吹热风。这价格不可接受。” - Li 客') }}
          </div>
        </div>
        <!-- AI Evidence Gatherer (Bento Style) -->
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 ai-tinge flex flex-col gap-4"
        >
          <div class="flex items-center gap-2 mb-2">
            <h3 class="text-headline-md font-headline-md text-on-surface">
              {{ t('AI 证据分析') }}
            </h3>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div
              class="bg-surface p-3 rounded-lg border border-outline-variant relative overflow-hidden group"
            >
              <img
                class="absolute inset-0 w-full h-full object-cover opacity-40 group-hover:opacity-60 transition-opacity"
                data-="A top-down view of a pristine, modern hotel bathroom sink area, gleaming white porcelain, perfectly folded fluffy towels, bright natural light pouring in, high-end clean aesthetic."
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuD1VeqtJQsmSnTi3NIKLUeqq0YRPgfbWiroCjG4QaAVFHcRG-02vG43rO1Q97d07QUki4CI6_j4y7rSWwUvc3tWAn2W0MxmRKhv57saoM37AzoIUttfTqJBSoDtWfzn7jEhOQUMwWCARCan1HD0hnmhVJMzhSlw_wr-Bwrdlw43YiiVCUQSiiTgm9CbmzrTjXC2q5vHDgq193HJqOfKmOKr60Fal1gfOzJ4dFTWqourhRcWkhgW-hk"
              />
              <div class="relative z-10">
                <p class="text-label-lg font-label-lg font-bold text-on-surface">
                  {{ t('客房日志') }}
                </p>
                <p class="text-xs text-on-surface-variant">
                  {{ t('14:30 标记清洁。14:45 经理核验。') }}
                </p>
                <span
                  class="inline-block mt-2 px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded"
                  >{{ t('凭证有效') }}</span
                >
              </div>
            </div>
            <div
              class="bg-surface p-3 rounded-lg border border-outline-variant relative overflow-hidden group"
            >
              <div
                class="absolute inset-0 w-full h-full bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-100 to-surface opacity-50"
              ></div>
              <div class="relative z-10">
                <p class="text-label-lg font-label-lg font-bold text-on-surface">
                  {{ t('IoT 空调系统日志') }}
                </p>
                <p class="text-xs text-on-surface-variant">
                  {{ t('304 房整夜温度稳定在 22°C。') }}
                </p>
                <span
                  class="inline-block mt-2 px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded"
                  >{{ t('凭证有效') }}</span
                >
              </div>
            </div>
          </div>
          <p
            class="text-body-md font-body-md text-on-surface-variant mt-2 border-l-2 border-tertiary pl-3 italic"
          >
            {{ t('“检测到矛盾陈述。内部系统在入住前及入住期间核验了房间清洁度与空调功能。”') }}
          </p>
        </div>
      </div>
      <!-- Middle Column: AI Appeal Generator -->
      <div class="col-span-12 lg:col-span-5 flex flex-col gap-gutter">
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 flex-1 flex flex-col"
        >
          <div class="flex justify-between items-center mb-4">
            <div class="flex items-center gap-2">
              <h2 class="text-headline-md font-headline-md text-on-surface">
                {{ t('起草申诉函') }}
              </h2>
            </div>
            <button
              class="text-primary hover:bg-primary-container/10 px-3 py-1.5 rounded-md text-label-lg font-label-lg transition-colors flex items-center gap-1"
            >
              {{ t('重新生成') }}
            </button>
          </div>
          <div class="flex-1 bg-surface border border-outline-variant rounded-lg p-4 mb-4 relative">
            <textarea
              class="w-full h-full bg-transparent border-none resize-none focus:ring-0 text-body-md font-body-md text-on-surface p-0"
              :placeholder="t('AI 正在生成申诉……')"
              >{{
                t(
                  '主题：针对恶意评价的申诉 - 订单 #88921\n\n    尊敬的携程评价处理团队：\n\n    我们就住客 Li 针对订单 #88921（入住 304 客房）留下的 1 星评价正式提出申诉，该评价包含关于我店设施与服务与事实不符的陈述。\n\n    申诉点 1：“客房不干净”\n    证据：附上我店客房服务巡检记录及带时间戳的主管核验照片，证实 304 客房已在入住当日 14:45 按标准清洁并验收。\n\n    申诉点 2：“空调不工作 / 吹热风”\n    证据：附上我店中央 IoT 气候控制系统的导出数据。数据显示 304 客房的空调运行正常，在住客整个入住期间稳定维持 22°C。\n\n    鉴于客观系统证据与住客陈述直接矛盾，我们依据平台关于事实不符反馈的政策，请求删除该评价。\n\n    感谢您对此事的及时处理。',
                )
              }}</textarea>
            <div class="absolute bottom-4 right-4 flex gap-2">
              <button
                class="bg-surface-container-high hover:bg-surface-variant p-2 rounded-full text-on-surface-variant transition-colors"
                :placeholder="t('复制到剪贴板')"
              ></button>
            </div>
          </div>
          <!-- Guardrail / Submit action -->
          <div
            class="bg-blue-50 border border-blue-200 rounded-lg p-4 flex justify-between items-center"
          >
            <div class="flex items-center gap-3">
              <div>
                <p class="text-label-lg font-label-lg font-bold text-on-surface">
                  {{ t('待提交') }}
                </p>
                <p class="text-xs text-on-surface-variant">{{ t('自动提交将附上所选证据。') }}</p>
              </div>
            </div>
            <button
              class="bg-primary text-on-primary px-6 py-2 rounded-lg text-label-lg font-label-lg font-bold hover:bg-on-primary-fixed-variant transition-colors shadow-sm"
            >
              {{ t('提交申诉') }}
            </button>
          </div>
        </div>
      </div>
      <!-- Right Column: Status Tracker -->
      <div class="col-span-12 lg:col-span-3">
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 h-full"
        >
          <h3 class="text-headline-md font-headline-md text-on-surface mb-6">
            {{ t('申诉状态') }}
          </h3>
          <div class="relative pl-6 border-l-2 border-outline-variant pb-8">
            <div
              class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-primary ring-4 ring-surface-container-lowest"
            ></div>
            <h4 class="text-label-lg font-label-lg font-bold text-on-surface">
              {{ t('证据已收集') }}
            </h4>
            <p class="text-xs text-on-surface-variant mt-1">{{ t('AI 已完成内部日志扫描。') }}</p>
            <span class="text-xs text-on-surface-variant mt-1 block">{{ t('10:05（上午）') }}</span>
          </div>
          <div class="relative pl-6 border-l-2 border-outline-variant pb-8">
            <div
              class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-primary ring-4 ring-surface-container-lowest flex items-center justify-center"
            >
              <div class="w-2 h-2 bg-white rounded-full"></div>
            </div>
            <h4 class="text-label-lg font-label-lg font-bold text-on-surface">
              {{ t('起草申诉中') }}
            </h4>
            <p class="text-xs text-on-surface-variant mt-1">{{ t('草稿已生成，待经理复核。') }}</p>
            <span class="text-xs text-on-surface-variant mt-1 block">{{ t('10:06（上午）') }}</span>
          </div>
          <div class="relative pl-6 border-l-2 border-transparent pb-8 opacity-50">
            <div
              class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-surface-container-highest ring-4 ring-surface-container-lowest"
            ></div>
            <h4 class="text-label-lg font-label-lg font-bold text-on-surface">
              {{ t('已提交至 OTA') }}
            </h4>
            <p class="text-xs text-on-surface-variant mt-1">{{ t('待提交。') }}</p>
          </div>
          <div class="relative pl-6 border-transparent opacity-50">
            <div
              class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-surface-container-highest ring-4 ring-surface-container-lowest"
            ></div>
            <h4 class="text-label-lg font-label-lg font-bold text-on-surface">
              {{ t('平台裁定') }}
            </h4>
            <p class="text-xs text-on-surface-variant mt-1">{{ t('提交后预计 1-2 个工作日。') }}</p>
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
