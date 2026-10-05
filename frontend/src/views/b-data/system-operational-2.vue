<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// 数据来源：后端 demo 接口（确定性种子数据），实体 = channel-sync
// 列表/表格通过 v-for 渲染 rows；字段缺失时回退原型示例值，保证版式 1:1。
const hotelId = 1
const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('channel-sync')
})
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 class="font-headline-lg text-headline-lg text-on-surface flex items-center gap-2">
            {{ t('数据同步状态') }}
            <span
              class="bg-surface-container-high text-on-surface-variant text-xs px-2 py-1 rounded-full font-num-md flex items-center gap-1 border border-outline-variant"
            >
              <span class="w-2 h-2 rounded-full bg-green-500"></span>
              System Operational
            </span>
          </h1>
          <p class="font-body-md text-body-md text-on-surface-variant mt-1">
            {{ t('监控各渠道订单与库存同步情况') }}
          </p>
        </div>
        <div class="flex items-center gap-3">
          <button
            class="flex items-center gap-2 bg-surface-container text-on-surface border border-outline-variant hover:bg-surface-container-high px-4 py-2 rounded-lg font-label-lg transition-colors"
          >
            <span class="material-symbols-outlined text-[18px]">history</span>
            {{ t('查看同步日志') }}
          </button>
          <button
            class="flex items-center gap-2 bg-primary text-on-primary hover:bg-primary/90 px-4 py-2 rounded-lg font-label-lg shadow-sm transition-colors"
          >
            <span class="material-symbols-outlined text-[18px]">sync</span>
            {{ t('一键全渠道同步') }}
          </button>
        </div>
      </div>
      <!-- Global Stats Bento -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <!-- Stat 1 -->
        <div
          class="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-sm flex flex-col justify-between"
        >
          <div class="text-on-surface-variant font-label-lg flex items-center gap-2">
            <span class="material-symbols-outlined text-[18px]">check_circle</span>
            {{ t('24h 成功同步') }}
          </div>
          <div class="mt-2 flex items-baseline gap-2">
            <span class="font-num-xl text-num-xl text-on-surface">1,248</span>
            <span class="text-xs text-green-600 font-num-md">↑ 12%</span>
          </div>
        </div>
        <!-- Stat 2 -->
        <div
          class="bg-error-container/30 p-5 rounded-xl border border-error-container shadow-sm flex flex-col justify-between relative overflow-hidden"
        >
          <div
            class="absolute top-0 right-0 w-16 h-16 bg-error-container/50 rounded-bl-full -mr-8 -mt-8"
          ></div>
          <div class="text-on-error-container font-label-lg flex items-center gap-2">
            <span class="material-symbols-outlined text-[18px]">error</span>
            {{ t('待处理失败重试') }}
          </div>
          <div class="mt-2 flex items-baseline gap-2">
            <span class="font-num-xl text-num-xl text-error">3</span>
            <span class="text-xs text-on-surface-variant font-num-md">{{
              t('来自 2 个渠道')
            }}</span>
          </div>
        </div>
        <!-- Stat 3 -->
        <div
          class="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-sm flex flex-col justify-between"
        >
          <div class="text-on-surface-variant font-label-lg flex items-center gap-2">
            <span class="material-symbols-outlined text-[18px]">sync_alt</span>
            {{ t('平均延迟') }}
          </div>
          <div class="mt-2 flex items-baseline gap-2">
            <span class="font-num-xl text-num-xl text-on-surface">1.2s</span>
            <span class="text-xs text-on-surface-variant font-num-md">{{ t('稳定') }}</span>
          </div>
        </div>
        <!-- AI Insight -->
        <div
          class="bg-gradient-to-br from-tertiary-fixed to-surface-container-lowest p-5 rounded-xl border border-tertiary-fixed shadow-sm flex flex-col justify-between relative"
        >
          <div class="absolute top-2 right-2 text-tertiary">
            <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
              >arrow_back_ios_new</span
            >
          </div>
          <div class="text-on-tertiary-fixed-variant font-label-lg">{{ t('AI 对账分析') }}</div>
          <p class="mt-2 text-sm text-on-surface-variant leading-tight">
            {{ t('发现携程渠道存在 2 笔金额差异 (') }}<span class="font-num-md">¥12.50</span
            >{{ t(')，已标记需核对。') }}
          </p>
          <button class="mt-2 text-tertiary text-sm font-label-lg text-left hover:underline w-max">
            {{ t('查看详情 →') }}
          </button>
        </div>
      </div>
      <!-- Channels Grid -->
      <h2 class="font-headline-md text-headline-md text-on-surface mb-4">
        {{ t('渠道监控详情') }}
      </h2>
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Meituan Card -->
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col"
        >
          <div
            class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low"
          >
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-lg bg-yellow-400 flex items-center justify-center font-bold text-black text-lg"
              >
                {{ t('美') }}
              </div>
              <div>
                <div class="font-headline-md text-base text-on-surface">{{ t('美团酒店') }}</div>
                <div class="text-xs text-on-surface-variant flex items-center gap-1">
                  <span class="w-2 h-2 rounded-full bg-green-500 inline-block"></span>
                  {{ t('实时同步中') }}
                </div>
              </div>
            </div>
            <button
              class="text-primary hover:bg-primary-container/20 p-1.5 rounded transition-colors"
              :title="t('手动同步')"
            >
              <span class="material-symbols-outlined text-[20px]">sync</span>
            </button>
          </div>
          <div class="p-4 flex-1">
            <div class="grid grid-cols-2 gap-y-4 text-sm mb-4">
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('上次成功') }}</div>
                <div class="font-num-md text-on-surface">14:23:45</div>
              </div>
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('今日订单') }}</div>
                <div class="font-num-md text-on-surface">{{ t('42 笔') }}</div>
              </div>
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('失败重试') }}</div>
                <div class="font-num-md text-on-surface">{{ t('0 次') }}</div>
              </div>
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('平均耗时') }}</div>
                <div class="font-num-md text-on-surface">0.8s</div>
              </div>
            </div>
            <div class="border-t border-outline-variant pt-3 mt-2">
              <div class="text-xs text-on-surface-variant mb-2">{{ t('对账状态 (本周)') }}</div>
              <div
                class="bg-green-50 text-green-700 text-xs px-2 py-1.5 rounded flex items-center gap-1.5 border border-green-100"
              >
                <span class="material-symbols-outlined text-[14px]">check_circle</span>
                {{ t('完全匹配，无差异') }}
              </div>
            </div>
          </div>
        </div>
        <!-- Ctrip Card (Warning State) -->
        <div
          class="bg-surface-container-lowest rounded-xl border border-yellow-300 shadow-sm overflow-hidden flex flex-col relative"
        >
          <!-- Guardrail Banner R1 -->
          <div class="absolute top-0 left-0 w-full h-1 bg-yellow-400"></div>
          <div
            class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low"
          >
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white text-lg"
              >
                {{ t('携') }}
              </div>
              <div>
                <div class="font-headline-md text-base text-on-surface">{{ t('携程旅行') }}</div>
                <div class="text-xs text-yellow-600 flex items-center gap-1">
                  <span
                    class="w-2 h-2 rounded-full bg-yellow-500 inline-block animate-pulse"
                  ></span>
                  {{ t('存在异常') }}
                </div>
              </div>
            </div>
            <button
              class="text-primary hover:bg-primary-container/20 p-1.5 rounded transition-colors"
              :title="t('手动同步')"
            >
              <span class="material-symbols-outlined text-[20px]">sync</span>
            </button>
          </div>
          <div class="p-4 flex-1">
            <div class="grid grid-cols-2 gap-y-4 text-sm mb-4">
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('上次成功') }}</div>
                <div class="font-num-md text-on-surface">14:20:12</div>
              </div>
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('今日订单') }}</div>
                <div class="font-num-md text-on-surface">{{ t('128 笔') }}</div>
              </div>
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('失败重试') }}</div>
                <div class="font-num-md text-error font-bold flex items-center gap-1">
                  {{ t('2 次') }}
                  <span class="material-symbols-outlined text-[14px]">warning</span>
                </div>
              </div>
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('平均耗时') }}</div>
                <div class="font-num-md text-on-surface">2.4s</div>
              </div>
            </div>
            <div class="border-t border-outline-variant pt-3 mt-2">
              <div class="text-xs text-on-surface-variant mb-2">{{ t('对账状态 (本周)') }}</div>
              <div
                class="bg-yellow-50 text-yellow-800 text-xs px-2 py-1.5 rounded flex items-center justify-between border border-yellow-200"
              >
                <div class="flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-[14px]">info</span>
                  {{ t('2笔差异，待确认') }}
                </div>
                <button class="underline hover:text-yellow-600">Review</button>
              </div>
            </div>
          </div>
        </div>
        <!-- Douyin Card -->
        <div
          class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col"
        >
          <div
            class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low"
          >
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-lg bg-black flex items-center justify-center font-bold text-white text-lg"
              >
                {{ t('抖') }}
              </div>
              <div>
                <div class="font-headline-md text-base text-on-surface">
                  {{ t('抖音生活服务') }}
                </div>
                <div class="text-xs text-on-surface-variant flex items-center gap-1">
                  <span class="w-2 h-2 rounded-full bg-green-500 inline-block"></span>
                  {{ t('实时同步中') }}
                </div>
              </div>
            </div>
            <button
              class="text-primary hover:bg-primary-container/20 p-1.5 rounded transition-colors"
              :title="t('手动同步')"
            >
              <span class="material-symbols-outlined text-[20px]">sync</span>
            </button>
          </div>
          <div class="p-4 flex-1">
            <div class="grid grid-cols-2 gap-y-4 text-sm mb-4">
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('上次成功') }}</div>
                <div class="font-num-md text-on-surface">14:24:01</div>
              </div>
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('今日订单') }}</div>
                <div class="font-num-md text-on-surface">{{ t('15 笔') }}</div>
              </div>
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('失败重试') }}</div>
                <div class="font-num-md text-on-surface">{{ t('0 次') }}</div>
              </div>
              <div>
                <div class="text-on-surface-variant mb-1 text-xs">{{ t('平均耗时') }}</div>
                <div class="font-num-md text-on-surface">1.1s</div>
              </div>
            </div>
            <div class="border-t border-outline-variant pt-3 mt-2">
              <div class="text-xs text-on-surface-variant mb-2">{{ t('对账状态 (本周)') }}</div>
              <div
                class="bg-green-50 text-green-700 text-xs px-2 py-1.5 rounded flex items-center gap-1.5 border border-green-100"
              >
                <span class="material-symbols-outlined text-[14px]">check_circle</span>
                {{ t('完全匹配，无差异') }}
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- Recent Activity Table -->
      <div
        class="mt-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden"
      >
        <div
          class="p-4 border-b border-outline-variant bg-surface-container-low flex justify-between items-center"
        >
          <h3 class="font-headline-md text-base text-on-surface">{{ t('近期同步日志') }}</h3>
          <div class="flex gap-2">
            <button
              class="text-xs text-on-surface-variant hover:text-on-surface border border-outline-variant rounded px-2 py-1 bg-surface-container-lowest"
            >
              {{ t('全部') }}
            </button>
            <button
              class="text-xs text-error border border-error/30 rounded px-2 py-1 bg-error-container/10"
            >
              {{ t('仅看失败') }}
            </button>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm text-left">
            <thead
              class="text-xs text-on-surface-variant uppercase bg-surface-container-lowest border-b border-outline-variant"
            >
              <tr>
                <th class="px-4 py-3 font-medium" scope="col">{{ t('时间') }}</th>
                <th class="px-4 py-3 font-medium" scope="col">{{ t('渠道') }}</th>
                <th class="px-4 py-3 font-medium" scope="col">{{ t('类型') }}</th>
                <th class="px-4 py-3 font-medium" scope="col">{{ t('状态') }}</th>
                <th class="px-4 py-3 font-medium" scope="col">{{ t('详情 / 耗时') }}</th>
              </tr>
            </thead>
            <tr v-for="(item, i) in rows" :key="i">
              <td class="px-4 py-3 font-num-md text-on-surface-variant text-xs">
                {{ item.channel || '14:24:01' }}
              </td>
              <td class="px-4 py-3">{{ item.status || t('抖音') }}</td>
              <td class="px-4 py-3">{{ item.last_sync || t('订单推送 (创建)') }}</td>
              <td class="px-4 py-3">{{ item.orders || 'done Success' }}</td>
              <td class="px-4 py-3 text-on-surface-variant font-num-md text-xs">
                {{ item.errors || 'OID: D8392... (1.1s)' }}
              </td>
            </tr>
          </table>
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
