<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// PA-5_2 库存分配（收益管理 C1）：房型 × 渠道配额优化（滑块）
// 数据：api.listChannels 取渠道名与佣金率，按配额滑块渲染
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

const channels = ref<any[]>([])
onMounted(async () => {
  channels.value = await api.listChannels()
})
// 按渠道序号给一个初始配额
function allot(i: number) {
  return [20, 15, 10, 5][i % 4]
}
function suggest(i: number) {
  return ['+5', '-10', '维持现状', '+5'][i % 4]
}
function suggestCls(i: number) {
  return i === 1 ? 'text-error font-medium' : 'text-tertiary font-medium'
}
</script>

<template>
  <div class="page">
    <div class="flex-1 overflow-y-auto">
      <div class="max-w-max-content-width mx-auto flex flex-col gap-6">
        <!-- 控制条 -->
        <div
          class="flex justify-between items-end bg-surface-container-lowest p-4 rounded-xl border border-outline-variant shadow-sm"
        >
          <div class="flex gap-4 items-center">
            <div>
              <label class="block text-sm font-label-lg text-on-surface-variant mb-1">{{
                t('日期范围')
              }}</label>
              <div
                class="flex items-center gap-2 border border-outline-variant rounded-lg px-3 py-1.5 bg-surface"
              >
                <span class="material-symbols-outlined text-secondary text-[18px]"
                  >calendar_today</span
                >
                <span class="font-body-md">{{ t('2023-11-01 至 2023-11-07') }}</span>
              </div>
            </div>
            <div>
              <label class="block text-sm font-label-lg text-on-surface-variant mb-1">{{
                t('目标优化')
              }}</label>
              <select
                class="border border-outline-variant rounded-lg px-3 py-1.5 bg-surface font-body-md focus:ring-primary focus:border-primary"
              >
                <option>{{ t('最大化 RevPAR (推荐)') }}</option>
                <option>{{ t('最大化入住率') }}</option>
                <option>{{ t('平衡各渠道') }}</option>
              </select>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-sm font-label-lg text-on-surface-variant">{{
              t('AI 自动执行调整')
            }}</span>
            <label class="relative inline-flex items-center cursor-pointer">
              <input checked class="sr-only peer" type="checkbox" />
              <div
                class="w-11 h-6 bg-surface-container-highest peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-tertiary"
              ></div>
            </label>
          </div>
        </div>

        <!-- 护栏洞察 -->
        <div
          class="bg-primary-fixed/30 border border-primary-fixed rounded-lg p-4 flex items-start gap-3"
        >
          <span class="material-symbols-outlined text-primary mt-0.5">info</span>
          <div>
            <h4 class="font-label-lg text-on-primary-fixed font-semibold">
              {{ t('AI 洞察: 商务客源回升') }}
            </h4>
            <p class="text-sm text-on-primary-fixed/80 mt-1">
              {{
                t(
                  '根据历史数据及当前预订趋势，下周直销及协议客需求预计上涨 15%。已建议减少 OTA 渠道标准间配额以优化整体收益。',
                )
              }}
            </p>
          </div>
        </div>

        <!-- 房型 × 渠道配额矩阵（v-for 绑定 listChannels） -->
        <div class="grid grid-cols-12 gap-4">
          <div
            class="col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col"
          >
            <div
              class="px-5 py-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low/50"
            >
              <div class="flex items-center gap-3">
                <h3 class="font-headline-md text-on-surface">{{ t('标准大床房') }}</h3>
                <span
                  class="px-2 py-0.5 bg-secondary-container text-on-secondary-container rounded text-xs font-num-md"
                  >{{ t('总量: 50间') }}</span
                >
              </div>
              <div class="flex items-center gap-2 text-sm">
                <span class="w-2 h-2 rounded-full bg-error"></span>
                {{ t('高需求 (建议收紧低价渠道)') }}
              </div>
            </div>
            <div class="p-5 grid grid-cols-4 gap-6">
              <div
                v-for="(c, i) in channels"
                :key="c.id"
                class="flex flex-col gap-2 p-3 rounded-lg border border-outline-variant"
                :class="{ 'ai-glow bg-surface': i === 0 }"
              >
                <div class="flex justify-between items-center">
                  <span class="font-label-lg text-on-surface font-semibold flex items-center gap-1">
                    <span v-if="i === 0" class="material-symbols-outlined text-[16px] text-tertiary"
                      >star</span
                    >{{ c.name || t('渠道') }}</span
                  >
                  <span class="font-num-xl text-on-surface"
                    >{{ allot(i) }}<span class="text-sm text-secondary">{{ t('间') }}</span></span
                  >
                </div>
                <input class="w-full mt-2" max="50" min="0" type="range" :value="allot(i)" />
                <div class="flex justify-between text-xs text-on-surface-variant mt-1">
                  <span>{{ t('佣金率') }} {{ ((c.commission_rate || 0) * 100).toFixed(0) }}%</span>
                  <span :class="suggestCls(i)">AI 建议: {{ suggest(i) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
