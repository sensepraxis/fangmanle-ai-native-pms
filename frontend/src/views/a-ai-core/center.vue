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
    <!-- Chat Interface -->
    <div class="flex-1 flex flex-col h-full border-r border-outline-variant/50">
      <!-- Header -->
      <div
        class="px-container-padding py-4 border-b border-surface-variant bg-surface-bright/50 backdrop-blur flex justify-between items-center"
      >
        <div>
          <h1 class="font-headline-md text-headline-md text-on-surface">
            {{ t('对话式指令中心') }}
          </h1>
          <p class="font-body-md text-body-md text-on-surface-variant text-sm mt-1">
            {{ t('自然语言处理工作台') }}
          </p>
        </div>
        <div class="flex gap-2">
          <span
            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container text-on-surface-variant text-sm"
          >
            <span class="w-2 h-2 rounded-full bg-primary"></span>
            {{ t('AI Agent 在线') }}</span
          >
        </div>
      </div>
      <!-- Chat History -->
      <div
        class="flex-1 overflow-y-auto p-container-padding flex flex-col gap-6"
        id="chat-container"
      >
        <!-- Date Separator -->
        <div class="flex justify-center">
          <span
            class="text-xs font-label-lg text-on-surface-variant bg-surface px-3 py-1 rounded-full border border-surface-variant"
            >{{ t('今天 09:41 AM') }}</span
          >
        </div>
        <!-- User Message -->
        <div class="flex gap-4 justify-end message-anim">
          <div class="max-w-[70%]">
            <div class="bg-primary text-on-primary rounded-2xl rounded-tr-none px-5 py-3 shadow-sm">
              <p class="font-body-md text-body-md">
                {{
                  t('分析下周（10.16 - 10.22）的入住率趋势，并根据当前预订情况建议库存调整策略。')
                }}
              </p>
            </div>
          </div>
          <div
            class="w-8 h-8 rounded-full bg-surface-container-high flex-shrink-0 flex items-center justify-center overflow-hidden border border-outline-variant"
          >
            <img
              alt="Xiao Lin"
              class="w-full h-full object-cover"
              data-alt="A close-up, professional headshot of a boutique hotel manager named Xiao Lin. She is wearing a modern, crisp white blouse with a subtle AI Blue lanyard. The lighting is soft and natural, suggesting a bright, welcoming hotel lobby environment in the background. The mood is confident and efficient."
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuBVH1v3FgsQNmcI7Qg8350DgbkM3n-ydsGEDrZxTbkzg04yBRof32i6e0Q079XukGVTymN4pnJQssVAbBKNvzNd5aZRW_l-tQjNOX_b-H2WPe4VQHdgF448lZn-sPtV0bTIyxnU1AUfCO-iQdxsdP4qu4gh7acwpQ301KLF9mLpLHOz3gv1UZ_VDeLZlsHIl1Pq6PoGKE8zhKij5q7OkaxH9ykJvcDUn8huQ04sVUNWPCgizyIOM0I"
            />
          </div>
        </div>
        <!-- AI Response -->
        <div class="flex gap-4 message-anim" style="animation-delay: 0.1s">
          <div
            class="w-8 h-8 rounded-full bg-primary-container text-primary flex-shrink-0 flex items-center justify-center border border-primary/20"
          >
            <span
              class="material-symbols-outlined text-sm"
              style="font-variation-settings: 'FILL' 1"
              >auto_awesome</span
            >
          </div>
          <div class="max-w-[85%] w-full">
            <div
              class="bg-surface rounded-2xl rounded-tl-none border border-outline-variant/50 p-5 shadow-sm ai-tinge"
            >
              <p class="font-body-md text-body-md text-on-surface mb-4">
                {{
                  t(
                    '好的，已为您分析下周（10.16 - 10.22）的数据。受即将举办的「城市设计周」影响，预计后半周将迎来预订高峰。',
                  )
                }}
              </p>
              <!-- Structured Data Component -->
              <div class="grid grid-cols-3 gap-4 mb-5">
                <div class="bg-surface-bright rounded-xl p-4 border border-surface-variant">
                  <div class="text-sm text-on-surface-variant mb-1">{{ t('预计平均入住率') }}</div>
                  <div class="font-num-xl text-num-xl text-on-surface">
                    82<span class="text-lg">%</span>
                  </div>
                  <div class="text-xs text-primary mt-1 flex items-center gap-1">
                    <span class="material-symbols-outlined text-[14px]">trending_up</span>
                    {{ t('环比上涨 15%') }}
                  </div>
                </div>
                <div class="bg-surface-bright rounded-xl p-4 border border-surface-variant">
                  <div class="text-sm text-on-surface-variant mb-1">{{ t('当前未订房源') }}</div>
                  <div class="font-num-xl text-num-xl text-on-surface">
                    18<span class="text-lg">{{ t('间') }}</span>
                  </div>
                  <div class="text-xs text-on-surface-variant mt-1">
                    {{ t('主要集中在前半周') }}
                  </div>
                </div>
                <div class="bg-surface-bright rounded-xl p-4 border border-surface-variant">
                  <div class="text-sm text-on-surface-variant mb-1">{{ t('建议调价幅度') }}</div>
                  <div class="font-num-xl text-num-xl text-tertiary">
                    +10<span class="text-lg">%</span>
                  </div>
                  <div class="text-xs text-on-surface-variant mt-1">
                    {{ t('针对周四至周六高级大床房') }}
                  </div>
                </div>
              </div>
              <!-- Actionable Guardrail -->
              <div
                class="bg-primary-fixed/30 border border-primary/20 rounded-xl p-4 flex gap-4 items-start"
              >
                <span
                  class="material-symbols-outlined text-primary mt-0.5"
                  style="font-variation-settings: 'FILL' 1"
                  >info</span
                >
                <div class="flex-1">
                  <h4 class="font-label-lg text-label-lg text-on-surface font-semibold mb-1">
                    {{ t('策略建议：智能调价与库存保留') }}
                  </h4>
                  <p class="text-sm text-on-surface-variant mb-3">
                    {{
                      t(
                        '建议将周四至周六的「高级大床房」基础价格上调 10%，并预留 3 间作为 Walk-in 应急库存。此操作预计提升 RevPAR 约 ¥120。',
                      )
                    }}
                  </p>
                  <div class="flex gap-3">
                    <button
                      class="bg-primary hover:bg-primary/90 text-on-primary px-4 py-2 rounded-lg font-label-lg text-sm transition-colors flex items-center gap-2"
                    >
                      <span class="material-symbols-outlined text-[18px]">bolt</span>
                      {{ t('一键执行建议策略') }}
                    </button>
                    <button
                      class="bg-transparent border border-outline hover:bg-surface-variant/50 text-on-surface px-4 py-2 rounded-lg font-label-lg text-sm transition-colors"
                    >
                      {{ t('查看详情对比') }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- Input Area -->
      <div class="p-container-padding border-t border-surface-variant bg-surface-bright">
        <div
          class="relative bg-surface rounded-xl border border-outline-variant shadow-sm focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-all"
        >
          <textarea
            class="w-full bg-transparent border-none focus:ring-0 resize-none p-4 pb-12 font-body-md text-on-surface placeholder:text-on-surface-variant/70 min-h-[100px]"
            :placeholder="t(`继续提问，或输入斜杠 '/' 唤出快捷指令面板...`)"
          ></textarea>
          <div class="absolute bottom-3 left-4 flex gap-2">
            <button
              class="p-1.5 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors"
              :title="t('添加附件')"
            >
              <span class="material-symbols-outlined text-lg">attach_file</span>
            </button>
            <button
              class="p-1.5 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors"
              :title="t('历史记录')"
            >
              <span class="material-symbols-outlined text-lg">history</span>
            </button>
          </div>
          <div class="absolute bottom-3 right-4 flex gap-2 items-center">
            <span class="text-xs text-on-surface-variant mr-2">{{ t('↵ 发送 / ⇧↵ 换行') }}</span>
            <button
              class="bg-primary hover:bg-primary/90 text-on-primary w-8 h-8 rounded-lg flex items-center justify-center transition-colors shadow-sm"
            >
              <span
                class="material-symbols-outlined text-[18px]"
                style="font-variation-settings: 'FILL' 1"
                >send</span
              >
            </button>
          </div>
        </div>
      </div>
    </div>
    <!-- Contextual Intelligence Panel (Right Sidebar) -->
    <aside class="w-[360px] bg-surface-container-lowest flex flex-col hidden lg:flex">
      <div class="px-6 py-4 border-b border-surface-variant bg-surface-bright/50">
        <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
          <span class="material-symbols-outlined text-tertiary">lightbulb</span>
          {{ t('上下文情报') }}
        </h2>
      </div>
      <div class="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
        <!-- Context Card: Chart -->
        <div class="bg-surface rounded-xl border border-outline-variant/50 p-4 shadow-sm">
          <div class="flex justify-between items-center mb-4">
            <h3 class="font-label-lg text-label-lg text-on-surface font-semibold">
              {{ t('下周入住率预测折线图') }}
            </h3>
            <button class="text-on-surface-variant hover:text-primary transition-colors">
              <span class="material-symbols-outlined text-[18px]">open_in_new</span>
            </button>
          </div>
          <!-- Placeholder for Chart -->
          <div
            class="h-32 bg-surface-container-low rounded-lg relative overflow-hidden flex items-end px-2 pb-2 gap-1"
            data-alt="A clean, modern data visualization line chart showing hotel occupancy trends. The x-axis shows days of the week, the y-axis shows percentages. A smooth, glowing AI Blue line trends upwards towards the weekend, with a secondary dotted Tertiary Purple line indicating predicted peaks. The background is a crisp, bright light mode surface."
            style="
              background-image: url('https://lh3.googleusercontent.com/aida-public/AB6AXuAe19CS8kBbKwvljn7NO6v7Vmssh1LmKjS3HEVjt4uNApOx22Sg3-B5bvjQz-hH5F78HHqF1utk4ad25GjZZJVxSLwKcT1eKIuX4n2_g-_ybfBXYZxCDB-V_-O9194OfW78R0ocp9O4FI0mXKQ00my3JOaF3VnhIZEnRgNlyPhQB2eLoX33DAK4mbvSHWJKN4jn8sHQ_uNMpLTL_z3JY7iwuwLJZA8qnJaRYCUB0ibaRIOiw5NsNHU');
              background-size: cover;
            "
          >
            <!-- CSS mock chart bars for fallback -->
            <div
              class="w-full flex items-end justify-between px-2 h-full py-2 opacity-80 mix-blend-multiply"
            >
              <div class="w-[12%] bg-outline-variant h-[40%] rounded-t-sm"></div>
              <div class="w-[12%] bg-outline-variant h-[45%] rounded-t-sm"></div>
              <div class="w-[12%] bg-outline-variant h-[50%] rounded-t-sm"></div>
              <div class="w-[12%] bg-primary/40 h-[70%] rounded-t-sm"></div>
              <div class="w-[12%] bg-primary/60 h-[85%] rounded-t-sm"></div>
              <div class="w-[12%] bg-primary/80 h-[95%] rounded-t-sm"></div>
              <div class="w-[12%] bg-outline-variant h-[60%] rounded-t-sm"></div>
            </div>
          </div>
          <div class="flex justify-between text-xs text-on-surface-variant mt-2 px-1">
            <span>10.16</span>
            <span>10.19</span>
            <span>10.22</span>
          </div>
        </div>
        <!-- Context Card: Current Data -->
        <div class="bg-surface rounded-xl border border-outline-variant/50 p-4 shadow-sm">
          <h3 class="font-label-lg text-label-lg text-on-surface font-semibold mb-3">
            {{ t('当前相关房型状态') }}
          </h3>
          <div class="space-y-3">
            <div
              class="flex justify-between items-center p-2 rounded-lg hover:bg-surface-container-low transition-colors cursor-pointer border border-transparent hover:border-outline-variant/30"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded bg-primary-container text-primary flex items-center justify-center font-num-md text-sm"
                >
                  201
                </div>
                <div>
                  <div class="text-sm font-medium text-on-surface">{{ t('高级大床房') }}</div>
                  <div class="text-xs text-on-surface-variant">{{ t('周四入住 (张先生)') }}</div>
                </div>
              </div>
              <span
                class="px-2 py-0.5 rounded text-[10px] font-medium bg-surface-low text-on-surface-variant border border-outline-variant"
                >{{ t('已确认') }}</span
              >
            </div>
            <div
              class="flex justify-between items-center p-2 rounded-lg hover:bg-surface-container-low transition-colors cursor-pointer border border-transparent hover:border-outline-variant/30"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded bg-surface-container-high text-on-surface-variant flex items-center justify-center font-num-md text-sm"
                >
                  305
                </div>
                <div>
                  <div class="text-sm font-medium text-on-surface">{{ t('高级大床房') }}</div>
                  <div class="text-xs text-on-surface-variant">{{ t('空净房') }}</div>
                </div>
              </div>
              <span
                class="px-2 py-0.5 rounded text-[10px] font-medium bg-surface-container text-on-surface-variant border border-outline-variant"
                >{{ t('待定') }}</span
              >
            </div>
          </div>
          <button
            class="w-full mt-3 py-2 text-sm text-primary hover:bg-primary/5 rounded-lg transition-colors font-medium"
          >
            {{ t('查看完整房态表') }}
          </button>
        </div>
      </div>
    </aside>
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
