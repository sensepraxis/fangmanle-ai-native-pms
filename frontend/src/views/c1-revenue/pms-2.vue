<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 护栏与 PMS 写回设置：护栏参数 + 执行模式 + 写回监控对账
// 长尾域数据：api.demo('rate') 生成写回对账明细
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import { fmt } from '../../lib/ui'

const rows = ref<any[]>([])
onMounted(async () => {
  rows.value = await api.demo('rate')
})
// 写回对账：以建议价为 AI 价，当前价为 PMS 实际价，比较是否一致
function disc(r: any) {
  const ai = Number(r.suggested_price || 0)
  const pms = Number(r.current_price || 0)
  return { ai, pms, ok: ai === pms }
}
</script>

<template>
  <div class="page">
    <div class="max-w-[1440px] mx-auto">
      <!-- 页头 -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="font-headline-lg text-headline-lg text-on-background">
            {{ t('护栏与 PMS 写回设置') }}
          </h1>
          <p class="font-body-md text-body-md text-on-surface-variant mt-1">
            {{ t('配置 AI 调价的安全边界及系统同步行为') }}
          </p>
        </div>
        <div class="flex items-center gap-4">
          <button
            class="px-4 py-2 border border-outline-variant rounded-lg font-label-lg text-label-lg text-on-surface hover:bg-surface-container-low transition-colors"
          >
            {{ t('取消修改') }}
          </button>
          <button
            class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg text-label-lg hover:bg-surface-tint shadow-sm transition-colors"
          >
            {{ t('保存配置') }}
          </button>
        </div>
      </div>
      <!-- Bento 布局 -->
      <div class="grid grid-cols-12 gap-gutter">
        <!-- 护栏参数配置 -->
        <div
          class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <div class="flex items-center gap-2 mb-6 border-b border-outline-variant pb-4">
            <span class="material-symbols-outlined text-primary">security</span>
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('护栏参数配置') }}
            </h2>
            <span
              class="ml-2 px-2 py-0.5 bg-surface-container-high rounded text-xs text-on-surface-variant font-medium"
              >{{ t('全局生效') }}</span
            >
          </div>
          <div class="grid grid-cols-2 gap-6">
            <div class="space-y-2">
              <label class="font-label-lg text-label-lg text-on-surface block">{{
                t('最低价地板 (¥)')
              }}</label>
              <p class="text-xs text-on-surface-variant mb-2">
                {{ t('AI 调价建议永远不会低于此价格') }}
              </p>
              <div class="relative">
                <span
                  class="absolute inset-y-0 left-0 pl-3 flex items-center text-on-surface-variant"
                  >¥</span
                >
                <input
                  class="block w-full pl-8 pr-3 py-2 border border-outline-variant rounded-lg bg-surface-container-lowest text-on-surface font-num-md text-num-md focus:ring-1 focus:ring-primary focus:border-primary"
                  type="number"
                  value="299"
                />
              </div>
            </div>
            <div class="space-y-2">
              <label class="font-label-lg text-label-lg text-on-surface block">{{
                t('最大日变动幅度 (%)')
              }}</label>
              <p class="text-xs text-on-surface-variant mb-2">
                {{ t('限制单日价格上涨或下跌的最大百分比') }}
              </p>
              <div class="relative">
                <input
                  class="block w-full pl-3 pr-8 py-2 border border-outline-variant rounded-lg bg-surface-container-lowest text-on-surface font-num-md text-num-md focus:ring-1 focus:ring-primary focus:border-primary"
                  type="number"
                  value="15"
                />
                <span
                  class="absolute inset-y-0 right-0 pr-3 flex items-center text-on-surface-variant"
                  >%</span
                >
              </div>
            </div>
            <div class="space-y-2">
              <label class="font-label-lg text-label-lg text-on-surface block">{{
                t('超售上限 (间)')
              }}</label>
              <p class="text-xs text-on-surface-variant mb-2">
                {{ t('允许系统自动处理的最大超售房间数') }}
              </p>
              <input
                class="block w-full px-3 py-2 border border-outline-variant rounded-lg bg-surface-container-lowest text-on-surface font-num-md text-num-md focus:ring-1 focus:ring-primary focus:border-primary"
                type="number"
                value="0"
              />
            </div>
            <div class="space-y-2">
              <label class="font-label-lg text-label-lg text-on-surface block">{{
                t('协议价保护')
              }}</label>
              <p class="text-xs text-on-surface-variant mb-2">
                {{ t('保护特定房型的企业协议价不被覆盖') }}
              </p>
              <div
                class="flex items-center justify-between p-3 border border-outline-variant rounded-lg bg-surface-container-low"
              >
                <span class="text-sm font-medium">{{ t('启用协议价保护') }}</span>
                <label class="relative inline-flex items-center cursor-pointer">
                  <input checked class="sr-only peer" type="checkbox" />
                  <div
                    class="w-11 h-6 bg-surface-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"
                  ></div>
                </label>
              </div>
            </div>
          </div>
          <div
            class="mt-6 p-4 rounded-lg border border-[#FBC02D] bg-[#FFF9C4]/20 flex items-start gap-3"
          >
            <span class="material-symbols-outlined text-[#F57F17]">warning</span>
            <div>
              <h4 class="font-label-lg text-label-lg text-on-surface">
                {{ t('当前最低价地板设置低于历史均值 20%') }}
              </h4>
              <p class="text-sm text-on-surface-variant mt-1">
                {{ t('Review Suggested: 建议将最低价地板提高至 ¥350 以保护利润率。') }}
              </p>
            </div>
          </div>
        </div>
        <!-- 执行模式 -->
        <div class="col-span-12 lg:col-span-4 flex flex-col gap-gutter">
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex-1"
          >
            <div class="flex items-center gap-2 mb-4 border-b border-outline-variant pb-4">
              <span class="material-symbols-outlined text-tertiary">smart_toy</span>
              <h2 class="font-headline-md text-headline-md text-on-surface">{{ t('执行模式') }}</h2>
            </div>
            <div class="space-y-4">
              <label
                class="flex items-start gap-3 p-4 rounded-lg border-2 border-primary bg-primary-fixed/30 cursor-pointer relative overflow-hidden group"
              >
                <input
                  checked
                  class="mt-1 text-primary focus:ring-primary"
                  name="execution_mode"
                  type="radio"
                />
                <div>
                  <span class="block font-label-lg text-label-lg text-on-surface mb-1">{{
                    t('自动执行 (带护栏)')
                  }}</span>
                  <span class="block text-sm text-on-surface-variant">{{
                    t('AI 生成建议后自动同步至 PMS，仅在触发高风险护栏 (R3) 时要求人工确认。')
                  }}</span>
                </div>
              </label>
              <label
                class="flex items-start gap-3 p-4 rounded-lg border border-outline-variant hover:bg-surface-container-low cursor-pointer transition-colors"
              >
                <input
                  class="mt-1 text-primary focus:ring-primary"
                  name="execution_mode"
                  type="radio"
                />
                <div>
                  <span class="block font-label-lg text-label-lg text-on-surface mb-1">{{
                    t('逐条确认')
                  }}</span>
                  <span class="block text-sm text-on-surface-variant">{{
                    t('所有调价建议均需人工审核并手动点击确认后方可写入 PMS。')
                  }}</span>
                </div>
              </label>
            </div>
          </div>
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm relative overflow-hidden"
          >
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary"></div>
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-tertiary">visibility</span>
                <h3 class="font-headline-md text-headline-md text-on-surface">
                  {{ t('影子模式') }}
                </h3>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input class="sr-only peer" type="checkbox" />
                <div
                  class="w-11 h-6 bg-surface-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-tertiary"
                ></div>
              </label>
            </div>
            <p class="text-sm text-on-surface-variant">
              {{ t('开启后，AI 将生成调价策略并记录，但') }} <strong>{{ t('仅观察不写回') }}</strong
              >{{ t('真实 PMS 环境。用于灰度验证 AI 策略效果。') }}
            </p>
          </div>
        </div>
        <!-- 写回监控与对账 -->
        <div
          class="col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <div class="flex items-center justify-between mb-6 border-b border-outline-variant pb-4">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-secondary">sync_alt</span>
              <h2 class="font-headline-md text-headline-md text-on-surface">
                {{ t('写回监控与对账') }}
              </h2>
            </div>
            <div class="flex items-center gap-2">
              <span class="flex h-3 w-3 relative">
                <span
                  class="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-green-400 opacity-75"
                ></span>
                <span class="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
              </span>
              <span class="text-sm text-on-surface-variant">{{ t('PMS 同步在线') }}</span>
            </div>
          </div>
          <div class="grid grid-cols-4 gap-4 mb-6">
            <div class="p-4 bg-surface-container rounded-lg border border-outline-variant/50">
              <p class="text-sm text-on-surface-variant mb-1">{{ t('今日同步次数') }}</p>
              <p class="font-num-xl text-num-xl text-on-surface">1,420</p>
            </div>
            <div class="p-4 bg-surface-container rounded-lg border border-outline-variant/50">
              <p class="text-sm text-on-surface-variant mb-1">{{ t('成功率') }}</p>
              <p class="font-num-xl text-num-xl text-on-surface">99.8%</p>
            </div>
            <div class="p-4 bg-error-container/30 rounded-lg border border-error/30">
              <p class="text-sm text-on-error-container mb-1">{{ t('异常警告') }}</p>
              <p class="font-num-xl text-num-xl text-error">3</p>
            </div>
            <div class="p-4 bg-surface-container rounded-lg border border-outline-variant/50">
              <p class="text-sm text-on-surface-variant mb-1">{{ t('上次同步时间') }}</p>
              <p class="font-num-md text-num-md text-on-surface mt-2">14:32:05</p>
            </div>
          </div>
          <!-- 对账表（数据驱动：demo('rate')） -->
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant">
                  <th class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant">
                    {{ t('房型') }}
                  </th>
                  <th class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant">
                    {{ t('AI 建议价') }}
                  </th>
                  <th class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant">
                    {{ t('PMS 实际价') }}
                  </th>
                  <th class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant">
                    {{ t('状态') }}
                  </th>
                  <th class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant">
                    {{ t('操作') }}
                  </th>
                </tr>
              </thead>
              <tbody class="text-sm font-body-md">
                <tr
                  v-for="r in rows"
                  :key="r.id"
                  class="border-b border-outline-variant/50 hover:bg-surface-container-low transition-colors"
                  :class="{ 'bg-surface-variant/20': !disc(r).ok }"
                >
                  <td class="py-3 px-4 text-on-surface">{{ r.room_type }}</td>
                  <td class="py-3 px-4 font-num-md text-on-surface">
                    {{ fmt(r.suggested_price) }}
                  </td>
                  <td
                    class="py-3 px-4 font-num-md"
                    :class="disc(r).ok ? 'text-on-surface' : 'text-error font-medium'"
                  >
                    {{ fmt(r.current_price) }}
                  </td>
                  <td class="py-3 px-4">
                    <span
                      v-if="disc(r).ok"
                      class="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800 border border-green-200"
                    >
                      <span class="material-symbols-outlined text-[14px]">check_circle</span>
                      {{ t('成功') }}</span
                    >
                    <span
                      v-else
                      class="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-error-container text-on-error-container border border-error/30"
                    >
                      <span class="material-symbols-outlined text-[14px]">error</span>
                      {{ t('价格不一致') }}</span
                    >
                  </td>
                  <td class="py-3 px-4">
                    <button class="text-primary hover:underline font-medium">
                      {{ disc(r).ok ? t('详情') : t('强制对齐') }}
                    </button>
                  </td>
                </tr>
                <tr v-if="!rows.length">
                  <td colspan="5" class="py-8 text-center text-on-surface-variant">
                    {{ t('暂无写回记录') }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
