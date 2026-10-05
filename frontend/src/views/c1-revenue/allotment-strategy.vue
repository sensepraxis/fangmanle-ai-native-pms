<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 预售策略与配额：AI 渠道配额再平衡 + 预售追踪 + 需求热力图
// 核心域：api.listChannels 渲染渠道配额表（佣金 + 当前/AI 建议配额）
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

const channels = ref<any[]>([])
onMounted(async () => {
  channels.value = await api.listChannels()
})
// 配额（按 code 派生当前/AI 建议间数）
const QUOTA: Record<string, { cur: number; ai: number }> = {
  ota: { cur: 40, ai: 25 },
  douyin: { cur: 30, ai: 20 },
  direct: { cur: 10, ai: 35 },
  xiaohongshu: { cur: 18, ai: 26 },
  agreement: { cur: 22, ai: 18 },
  wechat: { cur: 12, ai: 28 },
}
function quotaOf(c: any) {
  return QUOTA[c.code] || { cur: 20, ai: 24 }
}
function commText(c: any) {
  return (Number(c.commission_rate || 0) * 100).toFixed(0) + '%'
}
</script>

<template>
  <div class="page">
    <div class="p-container-padding max-w-max-content-width mx-auto">
      <div class="mb-8 flex justify-between items-end">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface mb-2">
            {{ t('预售策略与配额') }}
          </h1>
          <p class="font-body-md text-body-md text-on-surface-variant">
            {{ t('针对即将到来的高需求时段（10月1日 - 10月7日）的 AI 驱动策略。') }}
          </p>
        </div>
        <div class="flex gap-4">
          <button
            class="flex items-center gap-2 px-4 py-2 border border-outline rounded-lg text-on-surface hover:bg-surface-container-low transition-colors font-label-lg text-label-lg"
          >
            <span class="material-symbols-outlined text-[18px]">calendar_today</span>
            {{ t('10月1日 - 10月7日') }}
          </button>
          <button
            class="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors font-label-lg text-label-lg"
          >
            <span class="material-symbols-outlined text-[18px]">publish</span>
            {{ t('应用 AI 策略') }}
          </button>
        </div>
      </div>
      <!-- Bento 网格 -->
      <div class="grid grid-cols-12 gap-gutter">
        <!-- AI 再平衡 (Span 8) -->
        <div
          class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col relative"
        >
          <div class="absolute top-0 left-0 w-1 h-full bg-tertiary"></div>
          <div
            class="p-6 border-b border-outline-variant flex justify-between items-center bg-surface-container-lowest"
          >
            <div class="flex items-center gap-3">
              <span class="material-symbols-outlined text-tertiary">psychology</span>
              <h2 class="font-headline-md text-headline-md text-on-surface">
                {{ t('AI 渠道配额再平衡') }}
              </h2>
            </div>
            <span
              class="px-3 py-1 bg-tertiary-container text-on-tertiary-container rounded-full font-label-lg text-label-lg text-sm flex items-center gap-1"
            >
              <span class="material-symbols-outlined text-[14px]">trending_up</span>
              {{ t('+12% 预计 RevPAR') }}</span
            >
          </div>
          <div class="p-6 flex-1 flex flex-col gap-6">
            <p class="text-on-surface-variant font-body-md text-body-md">
              {{ t('预计') }}
              <span class="font-bold text-on-surface">{{ t('10月3日 - 10月5日') }}</span>
              {{
                t(
                  '将出现高需求。建议：随着入住日期的临近，将客房从高佣金的 OTA 渠道转移回直销渠道（微信小程序），以最大化利润率。',
                )
              }}
            </p>
            <!-- 配额表（数据驱动：listChannels） -->
            <div class="mt-4 border border-outline-variant rounded-lg overflow-hidden">
              <table class="w-full text-left border-collapse">
                <thead class="bg-surface-container-low border-b border-outline-variant">
                  <tr>
                    <th class="p-4 font-label-lg text-label-lg text-on-surface-variant font-medium">
                      {{ t('渠道') }}
                    </th>
                    <th
                      class="p-4 font-label-lg text-label-lg text-on-surface-variant font-medium text-center"
                    >
                      {{ t('当前配额') }}
                    </th>
                    <th
                      class="p-4 font-label-lg text-label-lg text-on-surface-variant font-medium text-center"
                    >
                      {{ t('AI 建议') }}
                    </th>
                    <th
                      class="p-4 font-label-lg text-label-lg text-on-surface-variant font-medium text-right"
                    >
                      {{ t('操作') }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="c in channels"
                    :key="c.id"
                    class="border-b border-outline-variant last:border-0"
                    :class="c.code === 'direct' ? 'bg-tertiary/5' : ''"
                  >
                    <td class="p-4 flex items-center gap-3">
                      <div
                        class="w-8 h-8 bg-surface-container-high rounded flex items-center justify-center text-on-surface font-bold text-xs"
                      >
                        {{ (c.name || '?').slice(0, 1) }}
                      </div>
                      <span class="font-body-md text-body-md">{{ c.name }}</span>
                      <span
                        class="text-xs text-on-surface-variant border border-outline-variant px-1.5 rounded bg-surface-container-highest"
                        >{{ commText(c) }} {{ t('佣金') }}</span
                      >
                    </td>
                    <td class="p-4 text-center font-num-md text-num-md">
                      {{ quotaOf(c).cur }}
                      <span class="text-xs text-on-surface-variant">{{ t('间') }}</span>
                    </td>
                    <td class="p-4 text-center">
                      <div class="flex items-center justify-center gap-2">
                        <span
                          class="font-num-md text-num-md"
                          :class="quotaOf(c).ai >= quotaOf(c).cur ? 'text-[#07C160]' : 'text-error'"
                          >{{ quotaOf(c).ai }}</span
                        >
                        <span
                          class="material-symbols-outlined"
                          :class="quotaOf(c).ai >= quotaOf(c).cur ? 'text-[#07C160]' : 'text-error'"
                          text-[16px]
                          >{{
                            quotaOf(c).ai >= quotaOf(c).cur ? 'arrow_upward' : 'arrow_downward'
                          }}</span
                        >
                      </div>
                    </td>
                    <td class="p-4 text-right">
                      <button
                        class="text-primary hover:text-primary/80 font-label-lg text-label-lg"
                      >
                        {{ c.code === 'direct' ? t('批准') : t('审核') }}
                      </button>
                    </td>
                  </tr>
                  <tr v-if="!channels.length">
                    <td colspan="4" class="p-4 text-center text-on-surface-variant">
                      {{ t('加载渠道中…') }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div
              class="bg-surface-container-low border border-[#FFC300] rounded-lg p-3 flex gap-3 items-start mt-auto"
            >
              <span class="material-symbols-outlined text-[#FFC300] mt-0.5">info</span>
              <div>
                <p class="font-label-lg text-label-lg font-bold text-on-surface">
                  {{ t('建议审核') }}
                </p>
                <p class="font-body-md text-body-md text-on-surface-variant text-sm">
                  {{
                    t(
                      '减少 OTA 配额可能会暂时降低在这些平台上的搜索排名。AI 计算得出，利润率的提升可以抵消这一风险。',
                    )
                  }}
                </p>
              </div>
            </div>
          </div>
        </div>
        <!-- 预售追踪 (Span 4) -->
        <div class="col-span-12 lg:col-span-4 flex flex-col gap-gutter">
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6 flex-1"
          >
            <div class="flex justify-between items-start mb-6">
              <div>
                <h3 class="font-headline-md text-headline-md text-on-surface">
                  {{ t('预售追踪器') }}
                </h3>
                <p class="text-on-surface-variant text-sm">{{ t('抖音"黄金周"代金券') }}</p>
              </div>
              <span class="material-symbols-outlined text-on-surface-variant">campaign</span>
            </div>
            <div class="space-y-6">
              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span class="font-medium text-on-surface">{{ t('已售代金券') }}</span
                  ><span class="font-num-md text-num-md">850 / 1000</span>
                </div>
                <div class="w-full bg-surface-container-high rounded-full h-2">
                  <div class="bg-primary h-2 rounded-full" style="width: 85%"></div>
                </div>
              </div>
              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span class="font-medium text-on-surface">{{ t('核销率') }}</span
                  ><span class="font-num-md text-num-md">42%</span>
                </div>
                <div class="w-full bg-surface-container-high rounded-full h-2">
                  <div class="bg-[#FFC300] h-2 rounded-full" style="width: 42%"></div>
                </div>
                <p class="text-xs text-on-surface-variant mt-2 flex items-center gap-1">
                  <span class="material-symbols-outlined text-[14px]">warning</span
                  >{{ t('进度低于预期的 55%。建议发送推送通知。') }}
                </p>
              </div>
            </div>
          </div>
          <div
            class="bg-primary text-on-primary rounded-xl shadow-sm p-6 flex-1 relative overflow-hidden"
          >
            <div
              class="absolute inset-0 opacity-10"
              style="
                background-image: radial-gradient(circle at 2px 2px, white 1px, transparent 0);
                background-size: 20px 20px;
              "
            ></div>
            <div class="relative z-10">
              <h3 class="font-headline-md text-headline-md mb-1">{{ t('收益仿真') }}</h3>
              <p class="text-on-primary/80 text-sm mb-4">{{ t('如果应用 AI 再平衡') }}</p>
              <div class="flex items-end gap-2 mb-2">
                <span class="font-num-xl text-num-xl text-3xl">¥142,500</span
                ><span class="text-sm pb-1 text-on-primary/90">{{ t('预计总计') }}</span>
              </div>
              <div
                class="flex items-center gap-2 text-sm bg-white/20 inline-flex px-2 py-1 rounded"
              >
                <span class="material-symbols-outlined text-[16px]">trending_up</span
                ><span>{{ t('比当前策略增加 ¥15,200') }}</span>
              </div>
            </div>
          </div>
        </div>
        <!-- 需求热力图 (Span 12) -->
        <div
          class="col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6 overflow-hidden relative"
        >
          <h3 class="font-headline-md text-headline-md text-on-surface mb-6">
            {{ t('市场需求热力图') }}
          </h3>
          <div
            class="h-64 w-full relative bg-surface-container-low rounded-lg border border-outline-variant overflow-hidden flex items-center justify-center"
          >
            <span
              class="text-on-surface-variant text-sm absolute z-10 bg-surface/80 px-3 py-1 rounded backdrop-blur-sm"
              >{{ t('图表占位符：需求与供应曲线（CSS 占位）') }}</span
            >
            <div class="absolute inset-0 flex items-end gap-1 p-4 opacity-60">
              <div
                v-for="i in 30"
                :key="i"
                class="flex-1 rounded-t"
                :style="{
                  height: 30 + ((i * 37) % 60) + '%',
                  background: i % 7 === 0 ? '#d97706' : '#1a73e8',
                }"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
