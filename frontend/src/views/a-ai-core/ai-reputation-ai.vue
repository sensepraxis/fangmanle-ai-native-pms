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
    <div class="max-w-[max-content-width] mx-auto">
      <!-- Page Header -->
      <div class="mb-8 flex justify-between items-end">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface mb-2">
            {{ t('AI 评价自动追回 (Reputation AI)') }}
          </h1>
          <p class="font-body-lg text-body-lg text-on-surface-variant">
            {{ t('全网声誉监控与智能危机干预') }}
          </p>
        </div>
        <div class="flex gap-2">
          <span
            class="inline-flex items-center gap-1 bg-surface-container px-3 py-1 rounded-full text-label-lg text-on-surface-variant"
          >
            <span class="w-2 h-2 rounded-full bg-green-500"></span> {{ t('实时监控中') }}</span
          >
          <button
            class="bg-primary text-on-primary px-4 py-2 rounded-lg font-label-lg hover:bg-primary-container hover:text-on-primary-container transition-colors shadow-sm flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-sm">sync</span> {{ t('强制刷新平台数据') }}
          </button>
        </div>
      </div>
      <!-- Bento Grid Layout -->
      <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        <!-- Section 1: Overall Reputation Score (Spans 4 cols) -->
        <div
          class="md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col justify-between relative overflow-hidden"
        >
          <div class="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
            <span class="material-symbols-outlined text-9xl text-primary">monitoring</span>
          </div>
          <div>
            <h2
              class="font-headline-md text-headline-md text-on-surface flex items-center gap-2 mb-1"
            >
              <span class="material-symbols-outlined text-primary">star_rate</span>
              {{ t('综合声誉指数') }}
            </h2>
            <p class="font-body-md text-body-md text-on-surface-variant mb-6">
              {{ t('过去 30 天全网数据') }}
            </p>
          </div>
          <div class="flex items-end gap-4 mb-6">
            <span class="font-num-xl text-num-xl text-display-lg text-primary leading-none"
              >4.82</span
            >
            <span
              class="font-label-lg text-label-lg text-green-600 bg-green-100 px-2 py-0.5 rounded flex items-center"
            >
              <span class="material-symbols-outlined text-sm">trending_up</span> +0.05
            </span>
          </div>
          <div class="space-y-4">
            <!-- Platform bars -->
            <div>
              <div class="flex justify-between text-label-lg text-on-surface mb-1">
                <span>{{ t('携程 (Ctrip)') }}</span>
                <span class="font-num-md">4.9 / 5.0</span>
              </div>
              <div class="w-full bg-surface-container rounded-full h-2">
                <div class="bg-blue-500 h-2 rounded-full" style="width: 98%"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-label-lg text-on-surface mb-1">
                <span>{{ t('美团 (Meituan)') }}</span>
                <span class="font-num-md">4.7 / 5.0</span>
              </div>
              <div class="w-full bg-surface-container rounded-full h-2">
                <div class="bg-yellow-500 h-2 rounded-full" style="width: 94%"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-label-lg text-on-surface mb-1">
                <span>{{ t('去哪儿 (Qunar)') }}</span>
                <span class="font-num-md">4.8 / 5.0</span>
              </div>
              <div class="w-full bg-surface-container rounded-full h-2">
                <div class="bg-teal-500 h-2 rounded-full" style="width: 96%"></div>
              </div>
            </div>
          </div>
        </div>
        <!-- Section 2: Sentiment Analysis & Word Cloud (Spans 8 cols) -->
        <div
          class="md:col-span-8 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col ai-border-glow"
        >
          <div class="flex justify-between items-center mb-6">
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-tertiary">psychology</span>
              {{ t('AI 情感分析与高频词汇') }}
            </h2>
            <div class="flex gap-4 font-label-lg text-on-surface">
              <div class="flex items-center gap-1">
                <div class="w-3 h-3 rounded-full bg-green-500"></div>
                {{ t('正向 (82%)') }}
              </div>
              <div class="flex items-center gap-1">
                <div class="w-3 h-3 rounded-full bg-gray-400"></div>
                {{ t('中立 (12%)') }}
              </div>
              <div class="flex items-center gap-1">
                <div class="w-3 h-3 rounded-full bg-red-500"></div>
                {{ t('负向 (6%)') }}
              </div>
            </div>
          </div>
          <div class="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Simulated Word Cloud -->
            <div
              class="bg-surface-container-low rounded-lg p-4 flex flex-wrap content-center justify-center gap-3 min-h-[200px]"
            >
              <span class="text-green-600 text-2xl font-bold">{{ t('服务热情') }}</span>
              <span class="text-red-500 text-lg font-medium opacity-80">{{ t('隔音差') }}</span>
              <span class="text-green-500 text-xl font-semibold">{{ t('位置便利') }}</span>
              <span class="text-gray-500 text-sm">{{ t('早餐一般') }}</span>
              <span class="text-green-700 text-3xl font-bold">{{ t('房间干净') }}</span>
              <span class="text-red-600 text-md font-medium">{{ t('空调噪音') }}</span>
              <span class="text-green-500 text-lg font-semibold">{{ t('性价比高') }}</span>
              <span class="text-gray-600 text-md">{{ t('床垫偏硬') }}</span>
              <span class="text-green-600 text-xl font-bold">{{ t('前台小雅很棒') }}</span>
            </div>
            <!-- AI Insights -->
            <div class="flex flex-col justify-center gap-3">
              <div
                class="bg-tertiary-fixed/30 border border-tertiary-fixed-dim rounded-lg p-3 text-sm"
              >
                <strong class="text-on-tertiary-fixed block mb-1">{{ t('💡 AI 洞察分析') }}</strong>
                <p class="text-on-surface-variant">
                  {{ t('本周关于“隔音差”和“空调噪音”的负面提及比上周增加') }} <strong>15%</strong
                  >{{
                    t(
                      '。主要集中在临街的 3 楼客房 (301-305)。建议安排工程部检查或主动为该区域客人提供耳塞。',
                    )
                  }}
                </p>
              </div>
              <div
                class="bg-surface-container rounded-lg p-3 text-sm border border-outline-variant"
              >
                <strong class="text-on-surface block mb-1">{{ t('📈 亮点提炼') }}</strong>
                <p class="text-on-surface-variant">
                  {{
                    t(
                      '“前台服务”和“房间清洁度”持续获得好评，已自动为您生成 3 条可用于小红书/携程的营销素材文案。',
                    )
                  }}
                </p>
              </div>
            </div>
          </div>
        </div>
        <!-- Section 3: Negative Sentiment Recovery Alerts (Spans 4 cols) -->
        <div
          class="md:col-span-4 bg-error-container/20 rounded-xl p-0 border border-error/20 shadow-sm overflow-hidden flex flex-col"
        >
          <div class="bg-error-container p-4 border-b border-error/20">
            <h2
              class="font-headline-md text-headline-md text-on-error-container flex items-center gap-2"
            >
              <span class="material-symbols-outlined">warning</span> {{ t('负面评价紧急追回 (2)') }}
            </h2>
            <p class="font-body-md text-body-md text-on-error-container/80 text-sm mt-1">
              {{ t('需在 24 小时内处理以降低影响') }}
            </p>
          </div>
          <div class="flex-1 p-4 space-y-4 overflow-y-auto custom-scrollbar max-h-[400px]">
            <!-- Alert Card 1 -->
            <div
              class="bg-surface-container-lowest rounded-lg p-4 border-l-4 border-error shadow-sm"
            >
              <div class="flex justify-between items-start mb-2">
                <span class="font-label-lg font-bold text-on-surface">{{
                  t('张先生 (携程 2星)')
                }}</span>
                <span class="text-xs text-on-surface-variant">{{ t('2小时前') }}</span>
              </div>
              <p class="text-body-md text-on-surface-variant text-sm mb-3">
                {{ t('"晚上旁边房间太吵了，打电话给前台也没解决，没睡好。"') }}
              </p>
              <div
                class="bg-surface-container-low rounded p-2 mb-3 text-xs border border-outline-variant"
              >
                <span class="text-tertiary font-bold flex items-center gap-1 mb-1">
                  <span class="material-symbols-outlined text-[14px]">auto_awesome</span>
                  {{ t('AI 追回建议') }}</span
                >
                {{
                  t(
                    '建议立即致电致歉，并补偿【下次入住免费升房券】或【50元微信红包】安抚情绪，引导修改评价。',
                  )
                }}
              </div>
              <div class="flex gap-2">
                <button
                  class="flex-1 bg-primary text-on-primary text-xs py-2 rounded hover:bg-primary-container transition"
                >
                  {{ t('一键拨号') }}
                </button>
                <button
                  class="flex-1 bg-surface text-primary border border-outline-variant text-xs py-2 rounded hover:bg-surface-container-low transition"
                >
                  {{ t('发送补偿短信') }}
                </button>
              </div>
            </div>
            <!-- Alert Card 2 -->
            <div
              class="bg-surface-container-lowest rounded-lg p-4 border-l-4 border-orange-500 shadow-sm"
            >
              <div class="flex justify-between items-start mb-2">
                <span class="font-label-lg font-bold text-on-surface">{{
                  t('李女士 (美团 3星)')
                }}</span>
                <span class="text-xs text-on-surface-variant">{{ t('5小时前') }}</span>
              </div>
              <p class="text-body-md text-on-surface-variant text-sm mb-3">
                {{ t('"早餐种类太少了，九点去基本没热的东西吃。"') }}
              </p>
              <div
                class="bg-surface-container-low rounded p-2 mb-3 text-xs border border-outline-variant"
              >
                <span class="text-tertiary font-bold flex items-center gap-1 mb-1">
                  <span class="material-symbols-outlined text-[14px]">auto_awesome</span>
                  {{ t('AI 追回建议') }}</span
                >
                {{
                  t(
                    '历史记录显示该客人是金卡会员。建议发送致歉短信，并附赠【双人精美下午茶套餐】代金券挽回好感。',
                  )
                }}
              </div>
              <div class="flex gap-2">
                <button
                  class="w-full bg-surface text-on-surface border border-outline-variant text-xs py-2 rounded hover:bg-surface-container-low transition"
                >
                  {{ t('生成挽回话术') }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <!-- Section 4: AI Response Queue (Spans 8 cols) -->
        <div
          class="md:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm flex flex-col h-full max-h-[500px]"
        >
          <div
            class="p-6 border-b border-outline-variant flex justify-between items-center bg-surface-container-low/50 rounded-t-xl"
          >
            <div>
              <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined text-primary">replace_audio</span>
                {{ t('AI 智能回复队列') }}
              </h2>
              <p class="font-body-md text-body-md text-on-surface-variant text-sm mt-1">
                {{ t('AI 已根据客人入住历史和具体反馈生成个性化回复草稿') }}
              </p>
            </div>
            <button
              class="bg-surface text-primary border border-outline-variant px-3 py-1.5 rounded-lg text-sm font-label-lg hover:bg-surface-container-low transition flex items-center gap-1"
            >
              <span class="material-symbols-outlined text-sm">done_all</span>
              {{ t('批量发布 (5)') }}
            </button>
          </div>
          <div class="flex-1 overflow-y-auto p-0 custom-scrollbar">
            <table class="w-full text-left border-collapse">
              <thead class="bg-surface-container sticky top-0 z-10">
                <tr>
                  <th class="p-4 font-label-lg text-on-surface-variant w-[20%]">
                    {{ t('来源 / 评分') }}
                  </th>
                  <th class="p-4 font-label-lg text-on-surface-variant w-[30%]">
                    {{ t('客人原评') }}
                  </th>
                  <th
                    class="p-4 font-label-lg text-on-surface-variant w-[40%] text-tertiary flex items-center gap-1"
                  >
                    <span class="material-symbols-outlined text-sm">auto_awesome</span>
                    {{ t('AI 拟定回复') }}
                  </th>
                  <th class="p-4 font-label-lg text-on-surface-variant w-[10%] text-center">
                    {{ t('操作') }}
                  </th>
                </tr>
              </thead>
              <tr v-for="(item, i) in rows" :key="i">
                <td class="p-4 align-top">{{ item.cmd || '携程 ★★★★★ 王先生 · 高级大床房' }}</td>
                <td class="p-4 align-top">
                  {{
                    item.status ||
                    '"前台小雅服务特别好，看带了小孩主动给了儿童牙刷，房间很大很干净，下次来出差还住…'
                  }}
                </td>
                <td class="p-4 align-top">
                  {{
                    item.by ||
                    '"尊敬的王先生您好！非常感谢您的五星好评，也感谢您对前台小雅的认可！得知您和孩子…'
                  }}
                </td>
                <td class="p-4 align-top text-center">{{ item.at || 'send' }}</td>
              </tr>
            </table>
          </div>
        </div>
      </div>
      <!-- End Bento Grid -->
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
