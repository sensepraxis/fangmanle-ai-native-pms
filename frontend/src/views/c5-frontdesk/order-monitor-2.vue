<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 订单异常与流失预警（监测流·变体）—— 移植自 C5-frontdesk-orders/order-monitor-2.html
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'

// AI 监测动态（告警流）—— 本变体聚焦取消/流失/机器标记
const alerts = ref<any[]>([
  {
    id: 1,
    level: 'critical',
    title: '异常取消',
    time: '刚刚',
    body: '过去一小时内检测到 12/24 预订出现 10 笔以上取消。',
    suggestion: '核查 OTA 渠道竞对价格，可能存在价格不一致。',
    action: '排查',
  },
  {
    id: 2,
    level: 'warning',
    title: '流失机会风险',
    time: '15 分钟前',
    body: '“套房”类目流量高，但转化率较均值低 22%。',
    suggestion: '',
    action: '复核定价',
  },
  {
    id: 3,
    level: 'info',
    title: '机器活动标记',
    time: '1 小时前',
    body: '检测到同一 IP 的异常多日期锁房，已释放。',
    suggestion: '',
    action: '',
  },
])

onMounted(async () => {
  try {
    const r = await api.demo('risk')
    if (r.length) {
      alerts.value = r.map((x: any, i: number) => ({
        id: x.id ?? i + 1,
        level: x.level === '高' ? 'critical' : x.level === '低' ? 'info' : 'warning',
        title: x.type,
        time: x.triggered_at || '刚刚',
        body: x.desc,
        suggestion: x.handled ? '已处理' : '',
        action: x.handled ? '' : '排查',
      }))
    }
  } catch (e) {}
})
</script>

<template>
  <div class="page">
    <div class="flex justify-between items-end border-b border-outline-variant pb-4 mb-6">
      <div>
        <h1 class="text-display-lg font-display-lg text-on-surface">
          {{ t('订单异常与流失预警') }}
        </h1>
        <p class="text-body-lg font-body-lg text-on-surface-variant mt-1">
          {{ t('实时监测预订生命周期与风险评估。') }}
        </p>
      </div>
      <div class="flex items-center gap-2 text-label-lg font-label-lg">
        <span class="relative flex h-3 w-3">
          <span
            class="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"
          ></span>
          <span class="relative inline-flex rounded-full h-3 w-3 bg-primary"></span>
        </span>
        <span class="text-primary font-bold">{{ t('系统在线') }}</span>
      </div>
    </div>

    <div
      class="bg-surface-container-low border border-outline-variant rounded-lg overflow-hidden py-2 px-4 flex items-center mb-6"
    >
      <div class="flex-1 text-label-lg font-label-lg text-on-surface-variant">
        <span class="mx-4"
          ><span class="text-primary">09:42</span>{{ t('- 新预订 #4492 已通过直订确认。') }}</span
        >
        <span class="mx-4"
          ><span class="text-error">09:40</span
          >{{ t('- 取消预警：#4490（OTA）- 检测到价格差异。') }}</span
        >
        <span class="mx-4"
          ><span class="text-tertiary">09:35</span
          >{{ t('- AI 监测：豪华大床房流量激增，转化率下降。') }}</span
        >
        <span class="mx-4"
          ><span class="text-primary">09:30</span>{{ t('- #4488 款项已结清。') }}</span
        >
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
      <div
        class="md:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-4 flex flex-col h-[600px] shadow-sm"
      >
        <div class="flex items-center justify-between mb-4 border-b border-outline-variant pb-2">
          <h2 class="text-headline-md font-headline-md flex items-center gap-2">
            {{ t('AI 监测动态') }}
          </h2>
        </div>
        <div class="flex-1 overflow-y-auto space-y-4 pr-2">
          <div
            v-for="a in alerts"
            :key="a.id"
            class="rounded-lg p-3 relative overflow-hidden border"
            :class="{
              'bg-orange-50 border-orange-300': a.level === 'warning',
              'bg-error-container/20 border-error': a.level === 'critical',
              'bg-primary-container/10 border-primary-container': a.level === 'info',
            }"
          >
            <div
              class="absolute top-0 left-0 w-1 h-full"
              :class="{
                'bg-orange-500': a.level === 'warning',
                'bg-error': a.level === 'critical',
                'bg-primary': a.level === 'info',
              }"
            ></div>
            <div class="flex items-start gap-3 pl-2">
              <div>
                <div class="flex justify-between items-center mb-1">
                  <h3 class="text-label-lg font-label-lg font-bold text-on-surface">
                    {{ a.title }}
                  </h3>
                  <span class="text-[10px] text-on-surface-variant">{{ a.time }}</span>
                </div>
                <p class="text-body-md font-body-md text-on-surface-variant text-sm mb-2">
                  {{ a.body }}
                </p>
                <div
                  v-if="a.suggestion"
                  class="bg-surface-container-highest p-2 rounded text-xs border border-outline-variant border-dashed"
                >
                  <span class="font-bold text-on-surface">{{ t('AI 建议：') }}</span
                  >{{ a.suggestion }}
                </div>
                <div v-if="a.action" class="mt-2 flex gap-2">
                  <button
                    class="text-label-lg font-label-lg px-3 py-1 rounded border border-outline-variant transition-colors"
                    :class="
                      a.level === 'critical'
                        ? 'bg-error text-on-error hover:bg-error/90'
                        : 'bg-surface-container-high text-on-surface hover:bg-surface-container-highest'
                    "
                  >
                    {{ a.action }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="md:col-span-8 flex flex-col gap-gutter">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-gutter">
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-sm relative overflow-hidden"
          >
            <h3 class="text-label-lg font-label-lg text-on-surface-variant mb-1">
              {{ t('异常取消') }}
            </h3>
            <div class="flex items-end gap-2 mb-2">
              <span class="text-num-xl font-num-xl text-error">14</span
              ><span class="text-body-md font-body-md text-on-surface-variant mb-1">{{
                t('/ 今日')
              }}</span>
            </div>
            <div class="flex items-center text-error text-sm font-label-lg">
              {{ t('较昨日 +5') }}
            </div>
          </div>
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-sm relative overflow-hidden"
          >
            <h3 class="text-label-lg font-label-lg text-on-surface-variant mb-1">
              {{ t('流失机会') }}
            </h3>
            <div class="flex items-end gap-2 mb-2">
              <span class="text-num-xl font-num-xl text-orange-600">¥12,450</span>
            </div>
            <div class="flex items-center text-on-surface-variant text-sm font-label-lg">
              {{ t('预计流失营收（24小时）') }}
            </div>
          </div>
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-sm relative overflow-hidden"
          >
            <h3 class="text-label-lg font-label-lg text-on-surface-variant mb-1">
              {{ t('支付风险') }}
            </h3>
            <div class="flex items-end gap-2 mb-2">
              <span class="text-num-xl font-num-xl text-on-surface">3</span
              ><span class="text-body-md font-body-md text-on-surface-variant mb-1">{{
                t('待处理')
              }}</span>
            </div>
            <div class="flex items-center text-primary text-sm font-label-lg">
              {{ t('2 小时内自动取消') }}
            </div>
          </div>
        </div>

        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-sm flex-1 flex flex-col"
        >
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-headline-md font-headline-md text-on-surface">
              {{ t('转化与取消趋势') }}
            </h3>
            <div class="flex gap-2">
              <button
                class="text-label-lg font-label-lg px-3 py-1 rounded bg-surface-container-high border border-outline-variant"
              >
                24h
              </button>
              <button
                class="text-label-lg font-label-lg px-3 py-1 rounded hover:bg-surface-container-low text-on-surface-variant"
              >
                7d
              </button>
            </div>
          </div>
          <div
            class="flex-1 bg-surface-container flex items-center justify-center rounded-lg border border-outline-variant border-dashed relative"
          >
            <div
              class="absolute inset-0 opacity-20 bg-[radial-gradient(#c1c6d6_1px,transparent_1px)] [background-size:16px_16px]"
            ></div>
            <div class="text-center z-10">
              <p class="text-body-md font-body-md text-on-surface-variant">
                {{ t('实时可视化渲染中……') }}
              </p>
            </div>
          </div>
          <div class="mt-4 grid grid-cols-2 gap-4 border-t border-outline-variant pt-4">
            <div>
              <span class="text-label-lg font-label-lg text-on-surface-variant block mb-1">{{
                t('主要取消原因(AI推断)')
              }}</span>
              <div class="flex items-center gap-2">
                <div class="w-full bg-surface-container-high rounded-full h-2.5">
                  <div class="bg-error h-2.5 rounded-full" style="width: 45%"></div>
                </div>
                <span class="text-body-md font-body-md">{{ t('45% 价格一致性') }}</span>
              </div>
            </div>
            <div>
              <span class="text-label-lg font-label-lg text-on-surface-variant block mb-1">{{
                t('流量转化差值')
              }}</span>
              <div class="flex items-center gap-2">
                <div class="w-full bg-surface-container-high rounded-full h-2.5">
                  <div class="bg-orange-500 h-2.5 rounded-full" style="width: 30%"></div>
                </div>
                <span class="text-body-md font-body-md text-orange-600 font-bold">-30%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
