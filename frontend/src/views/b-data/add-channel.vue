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
    <!-- TopNavBar -->

    <!-- Content Canvas -->
    <div class="p-container-padding flex-1">
      <!-- Page Header -->
      <div class="mb-8">
        <div class="flex items-center gap-2 text-label-lg text-on-surface-variant mb-2">
          <a class="hover:text-primary" href="#">{{ t('系统设置') }}</a
          ><span>{{ t('数据集成') }}</span>
        </div>
        <h1 class="font-display-lg text-display-lg text-on-background">
          {{ t('同步规则与策略配置') }}
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant mt-2 max-w-2xl">
          {{
            t('管理房满乐 PMS 与已连接渠道间的数据流转。配置优先级、AI 冲突解决与数据隐私保护。')
          }}
        </p>
      </div>
      <!-- Bento Grid Layout -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
        <!-- 1. Channel Priority Settings (Spans 8 cols) -->
        <div
          class="lg:col-span-8 bg-surface-container-lowest rounded-xl p-6 shadow-[0_4px_12px_rgba(0,0,0,0.03)] border border-outline-variant"
        >
          <div class="flex items-center justify-between mb-6">
            <div>
              <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
                {{ t('渠道优先级设置') }}
              </h2>
              <p class="font-body-md text-sm text-on-surface-variant mt-1">
                {{ t('拖拽设置同步冲突时哪个渠道数据优先。') }}
              </p>
            </div>
            <button
              class="text-primary hover:bg-primary/10 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            >
              {{ t('添加渠道') }}
            </button>
          </div>
          <div class="space-y-3">
            <!-- Priority Item 1 -->
            <div
              class="flex items-center justify-between p-4 bg-surface rounded-lg border border-outline-variant cursor-move hover:border-primary transition-colors"
            >
              <div class="flex items-center gap-4">
                <div
                  class="w-8 h-8 rounded bg-primary-container flex items-center justify-center text-on-primary-container font-bold"
                >
                  L
                </div>
                <div>
                  <div class="font-label-lg text-label-lg text-on-surface">{{ t('本地 PMS') }}</div>
                  <div class="text-xs text-on-surface-variant">{{ t('主记录') }}</div>
                </div>
              </div>
              <div class="bg-primary/10 text-primary px-2 py-1 rounded text-xs font-bold">
                {{ t('优先级 1') }}
              </div>
            </div>
            <!-- Priority Item 2 -->
            <div
              class="flex items-center justify-between p-4 bg-surface rounded-lg border border-outline-variant cursor-move hover:border-primary transition-colors"
            >
              <div class="flex items-center gap-4">
                <div
                  class="w-8 h-8 rounded bg-blue-100 flex items-center justify-center text-blue-800 font-bold"
                >
                  C
                </div>
                <div>
                  <div class="font-label-lg text-label-lg text-on-surface">{{ t('携程') }}</div>
                  <div class="text-xs text-on-surface-variant">{{ t('OTA 渠道') }}</div>
                </div>
              </div>
              <div
                class="bg-surface-variant text-on-surface-variant px-2 py-1 rounded text-xs font-bold"
              >
                {{ t('优先级 2') }}
              </div>
            </div>
            <!-- Priority Item 3 -->
            <div
              class="flex items-center justify-between p-4 bg-surface rounded-lg border border-outline-variant cursor-move hover:border-primary transition-colors"
            >
              <div class="flex items-center gap-4">
                <div
                  class="w-8 h-8 rounded bg-orange-100 flex items-center justify-center text-orange-800 font-bold"
                >
                  M
                </div>
                <div>
                  <div class="font-label-lg text-label-lg text-on-surface">{{ t('美团') }}</div>
                  <div class="text-xs text-on-surface-variant">{{ t('OTA 渠道') }}</div>
                </div>
              </div>
              <div
                class="bg-surface-variant text-on-surface-variant px-2 py-1 rounded text-xs font-bold"
              >
                {{ t('优先级 3') }}
              </div>
            </div>
          </div>
        </div>
        <!-- 2. AI Conflict Resolution (Spans 4 cols) -->
        <div
          class="lg:col-span-4 bg-surface-container-lowest rounded-xl p-6 shadow-[0_4px_12px_rgba(0,0,0,0.03)] border border-outline-variant ai-tinge"
        >
          <div class="mb-6">
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('AI 冲突处理逻辑') }}
            </h2>
            <p class="font-body-md text-sm text-on-surface-variant mt-1">
              {{ t('让 AI 自动解决价格与房量冲突。') }}
            </p>
          </div>
          <div class="space-y-6">
            <!-- Toggle 1 -->
            <div class="flex items-center justify-between">
              <div>
                <div class="font-label-lg text-label-lg text-on-surface">{{ t('高价优先') }}</div>
                <div class="text-xs text-on-surface-variant max-w-[200px]">
                  {{ t('冲突时 AI 将选择收益最大化的价格。') }}
                </div>
              </div>
              <div
                class="relative inline-block w-12 mr-2 align-middle select-none transition duration-200 ease-in"
              >
                <input
                  checked
                  class="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer checked:bg-primary transition-all duration-300"
                  id="toggle1"
                  name="toggle"
                  type="checkbox"
                /><label
                  class="toggle-label block overflow-hidden h-6 rounded-full bg-surface-variant cursor-pointer transition-colors duration-300"
                  for="toggle1"
                ></label>
              </div>
            </div>
            <!-- Toggle 2 -->
            <div class="flex items-center justify-between">
              <div>
                <div class="font-label-lg text-label-lg text-on-surface">
                  {{ t('智能超售保护') }}
                </div>
                <div class="text-xs text-on-surface-variant max-w-[200px]">
                  {{ t('AI 预测取消率，安全管理最后房源。') }}
                </div>
              </div>
              <div
                class="relative inline-block w-12 mr-2 align-middle select-none transition duration-200 ease-in"
              >
                <input
                  checked
                  class="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer checked:bg-primary transition-all duration-300"
                  id="toggle2"
                  name="toggle"
                  type="checkbox"
                /><label
                  class="toggle-label block overflow-hidden h-6 rounded-full bg-surface-variant cursor-pointer transition-colors duration-300"
                  for="toggle2"
                ></label>
              </div>
            </div>
          </div>
          <!-- AI Insight Banner -->
          <div
            class="mt-6 bg-tertiary-container/10 border border-tertiary-container/30 rounded-lg p-3 flex gap-3 items-start"
          >
            <p class="text-xs text-on-surface">
              {{ t('AI 已解决') }} <strong>{{ t('42 处冲突') }}</strong
              >{{ t('上周，预计节省') }} <strong>¥1,250</strong>{{ t('潜在营收损失。') }}
            </p>
          </div>
        </div>
        <!-- 3. Sync Frequency Config (Spans 6 cols) -->
        <div
          class="lg:col-span-6 bg-surface-container-lowest rounded-xl p-6 shadow-[0_4px_12px_rgba(0,0,0,0.03)] border border-outline-variant"
        >
          <div class="mb-6">
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('同步频率配置') }}
            </h2>
          </div>
          <div class="space-y-5">
            <div>
              <label class="block font-label-lg text-label-lg text-on-surface mb-2">{{
                t('增量同步频率')
              }}</label
              ><select
                class="w-full bg-surface border border-outline-variant text-on-surface text-sm rounded-lg focus:ring-primary focus:border-primary block p-2.5"
              >
                <option>{{ t('实时 - 推荐') }}</option>
                <option>{{ t('每 5 分钟') }}</option>
                <option>{{ t('每 15 分钟') }}</option>
              </select>
              <p class="text-xs text-on-surface-variant mt-1">
                {{ t('仅更新变更的数据（例如：新预订、快速调价）。') }}
              </p>
            </div>
            <div>
              <label class="block font-label-lg text-label-lg text-on-surface mb-2">{{
                t('全量定时同步')
              }}</label>
              <div class="flex gap-4">
                <input
                  class="bg-surface border border-outline-variant text-on-surface text-sm rounded-lg focus:ring-primary focus:border-primary block w-32 p-2.5"
                  type="time"
                  value="03:00"
                /><select
                  class="flex-1 bg-surface border border-outline-variant text-on-surface text-sm rounded-lg focus:ring-primary focus:border-primary block p-2.5"
                >
                  <option>{{ t('每天') }}</option>
                  <option>{{ t('每周一') }}</option>
                </select>
              </div>
              <p class="text-xs text-on-surface-variant mt-1">
                {{ t('重新同步全部主数据以确保绝对一致。建议于非高峰时段执行。') }}
              </p>
            </div>
          </div>
        </div>
        <!-- 4. Sensitive Data Masking (Spans 6 cols) -->
        <div
          class="lg:col-span-6 bg-surface-container-lowest rounded-xl p-6 shadow-[0_4px_12px_rgba(0,0,0,0.03)] border border-outline-variant"
        >
          <div class="mb-6">
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('敏感数据同步屏蔽') }}
            </h2>
            <p class="font-body-md text-sm text-on-surface-variant mt-1">
              {{ t('通过对发往第三方渠道的数据脱敏保护客人隐私。') }}
            </p>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <!-- Masking Options -->
            <label
              class="flex items-start gap-3 p-3 border border-outline-variant rounded-lg cursor-pointer hover:bg-surface transition-colors"
              ><input
                checked
                class="mt-1 w-4 h-4 text-primary bg-surface border-outline-variant rounded focus:ring-primary"
                type="checkbox"
              />
              <div>
                <div class="font-label-lg text-sm text-on-surface">{{ t('客人手机号') }}</div>
                <div class="text-xs text-on-surface-variant">
                  {{ t('隐藏中间位（138****1234）') }}
                </div>
              </div></label
            ><label
              class="flex items-start gap-3 p-3 border border-outline-variant rounded-lg cursor-pointer hover:bg-surface transition-colors"
              ><input
                checked
                class="mt-1 w-4 h-4 text-primary bg-surface border-outline-variant rounded focus:ring-primary"
                type="checkbox"
              />
              <div>
                <div class="font-label-lg text-sm text-on-surface">{{ t('证件/护照号') }}</div>
                <div class="text-xs text-on-surface-variant">{{ t('仅同步末 4 位') }}</div>
              </div></label
            ><label
              class="flex items-start gap-3 p-3 border border-outline-variant rounded-lg cursor-pointer hover:bg-surface transition-colors"
              ><input
                class="mt-1 w-4 h-4 text-primary bg-surface border-outline-variant rounded focus:ring-primary"
                type="checkbox"
              />
              <div>
                <div class="font-label-lg text-sm text-on-surface">{{ t('支付明细') }}</div>
                <div class="text-xs text-on-surface-variant">{{ t('绝不同步原始卡号') }}</div>
              </div></label
            ><label
              class="flex items-start gap-3 p-3 border border-outline-variant rounded-lg cursor-pointer hover:bg-surface transition-colors"
              ><input
                class="mt-1 w-4 h-4 text-primary bg-surface border-outline-variant rounded focus:ring-primary"
                type="checkbox"
              />
              <div>
                <div class="font-label-lg text-sm text-on-surface">{{ t('特殊要求') }}</div>
                <div class="text-xs text-on-surface-variant">{{ t('不纳入对外同步') }}</div>
              </div></label
            >
          </div>
        </div>
        <!-- Action Bar -->
        <div class="lg:col-span-12 flex justify-end gap-4 mt-4">
          <button
            class="px-6 py-2.5 rounded-lg border border-outline-variant text-on-surface font-label-lg text-label-lg hover:bg-surface-container-high transition-colors"
          >
            {{ t('放弃更改') }}</button
          ><button
            class="px-6 py-2.5 rounded-lg bg-primary text-on-primary font-label-lg text-label-lg hover:bg-primary/90 transition-colors shadow-sm"
          >
            {{ t('保存配置') }}
          </button>
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
