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
      <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <div>
          <h1 class="text-display-lg font-display-lg text-on-surface mb-2">
            {{ t('5.3.4.0 全渠道同步健康监测') }}
          </h1>
          <p class="text-body-lg font-body-lg text-on-surface-variant">
            {{ t('活跃集成与数据同步流程的实时概览。') }}
          </p>
        </div>
        <div class="flex gap-3">
          <button
            class="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-lg text-on-surface-variant hover:bg-surface-container-low transition-colors text-label-lg font-label-lg"
          >
            {{ t('查看全局日志') }}</button
          ><button
            class="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg hover:bg-surface-tint transition-colors text-label-lg font-label-lg shadow-sm"
          >
            {{ t('立即同步全部') }}
          </button>
        </div>
      </div>
      <!-- Global Trust Indicators -->
      <div class="grid grid-cols-1 gap-gutter mb-8 md:grid-cols-5">
        <!-- Overall Status -->
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex items-start gap-4 shadow-sm"
        >
          <div
            class="w-12 h-12 rounded-full bg-surface-container flex items-center justify-center text-primary shrink-0"
          ></div>
          <div>
            <h3 class="text-headline-md font-headline-md text-on-surface mb-1">
              {{ t('系统健康') }}
            </h3>
            <p class="text-body-md font-body-md text-on-surface-variant mb-2">
              {{ t('5 个集成中 4 个同步正常。') }}
            </p>
            <span
              class="inline-flex items-center gap-1 text-xs font-label-lg px-2 py-1 bg-surface-container-low text-on-surface-variant rounded"
              ><span class="w-1.5 h-1.5 rounded-full bg-surface-low"></span
              >{{ t('最近检查：2 分钟前') }}</span
            >
          </div>
        </div>
        <!-- Sync Volume -->
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col justify-between shadow-sm relative overflow-hidden group"
        >
          <!-- AI Tinge -->
          <div
            class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary opacity-50 group-hover:opacity-100 transition-opacity"
          ></div>
          <div>
            <div class="flex justify-between items-center mb-2">
              <h3
                class="text-label-lg font-label-lg text-on-surface-variant uppercase tracking-wider"
              >
                {{ t('已同步记录（24小时）') }}
              </h3>
            </div>
            <div class="text-display-lg font-display-lg font-num-xl text-on-surface">14,285</div>
          </div>
          <div class="text-label-lg font-label-lg text-primary mt-2">{{ t('较昨日 +12%') }}</div>
        </div>
        <!-- Failed Syncs -->
        <div
          class="bg-surface-container-lowest border border-error-container rounded-xl p-6 flex flex-col justify-between shadow-sm"
        >
          <div>
            <div class="flex justify-between items-center mb-2">
              <h3 class="text-label-lg font-label-lg text-error uppercase tracking-wider">
                {{ t('同步错误') }}
              </h3>
            </div>
            <div class="text-display-lg font-display-lg font-num-xl text-error">3</div>
          </div>
          <div
            class="text-label-lg font-label-lg text-on-surface-variant mt-2 flex items-center gap-1"
          >
            {{ t('需在以下复核')
            }}<span class="font-bold text-on-surface">{{ t('OTA 渠道') }}</span>
          </div>
        </div>
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col justify-between shadow-sm relative overflow-hidden group"
        >
          <div
            class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary opacity-50 group-hover:opacity-100 transition-opacity"
          ></div>
          <div>
            <div class="flex justify-between items-center mb-2">
              <h3
                class="text-label-lg font-label-lg text-on-surface-variant uppercase tracking-wider"
              >
                {{ t('AI 预测瓶颈') }}
              </h3>
            </div>
            <div class="text-display-lg font-display-lg font-num-xl text-on-surface">
              2<span class="text-body-md font-body-md text-on-surface-variant">{{
                t('高风险')
              }}</span>
            </div>
          </div>
          <div class="text-label-lg font-label-lg text-tertiary mt-2">
            {{ t('预计 15 分钟内发生延迟') }}
          </div>
        </div>
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col justify-between shadow-sm"
        >
          <div>
            <div class="flex justify-between items-center mb-2">
              <h3
                class="text-label-lg font-label-lg text-on-surface-variant uppercase tracking-wider"
              >
                {{ t('实时冲突') }}
              </h3>
            </div>
            <div class="text-display-lg font-display-lg font-num-xl text-on-surface">12</div>
          </div>
          <div class="text-label-lg font-label-lg text-on-surface-variant mt-2">
            {{ t('正在自动解决中...') }}
          </div>
        </div>
      </div>
      <!-- Integrations List (Bento-style list) -->
      <div
        class="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden"
      >
        <div
          class="px-6 py-4 border-b border-outline-variant bg-surface-bright flex justify-between items-center"
        >
          <h2 class="text-headline-md font-headline-md text-on-surface">{{ t('活跃集成') }}</h2>
          <div class="relative">
            <input
              class="pl-9 pr-4 py-1.5 border border-outline-variant rounded-md text-body-md font-body-md w-64 focus:ring-1 focus:ring-primary focus:border-primary"
              :placeholder="t('筛选集成……')"
              type="text"
            />
          </div>
        </div>
        <div class="divide-y divide-outline-variant">
          <!-- Integration 1: PMS (Success) -->
          <div
            class="p-4 sm:px-6 hover:bg-surface-container-lowest/50 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
          >
            <div class="flex items-center gap-4 flex-1">
              <div
                class="w-10 h-10 rounded-lg bg-primary-fixed flex items-center justify-center text-primary-fixed-dim shrink-0"
              ></div>
              <div>
                <h4 class="text-headline-md font-headline-md text-on-surface text-base">
                  {{ t('核心 PMS') }}
                </h4>
                <p class="text-label-lg font-label-lg text-on-surface-variant">
                  {{ t('主物业管理系统') }}
                </p>
              </div>
            </div>
            <div
              class="flex flex-col md:flex-row md:items-center gap-4 md:gap-8 flex-1 md:justify-end"
            >
              <div class="flex flex-col items-start md:items-end">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1">{{
                  t('状态')
                }}</span
                ><span
                  class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-surface-low text-on-surface-variant border border-outline-variant"
                  ><span class="w-1.5 h-1.5 rounded-full bg-surface-low"></span
                  >{{ t('已同步') }}</span
                >
              </div>
              <div class="flex flex-col items-start md:items-end w-32">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1">{{
                  t('上次同步')
                }}</span
                ><span class="text-body-md font-num-md text-on-surface">10:42 AM</span>
              </div>
              <div class="flex flex-col items-start md:items-end w-24">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1"
                  >{{ t('记录') }}}</span
                ><span class="text-body-md font-num-md text-on-surface">8,402</span>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0 md:ml-4">
              <button
                class="p-2 text-primary hover:bg-primary-fixed rounded-md transition-colors"
                :placeholder="t('立即同步')"
              ></button
              ><button
                class="p-2 text-on-surface-variant hover:bg-surface-container-highest rounded-md transition-colors"
                :placeholder="t('查看日志')"
              ></button
              ><button
                class="p-2 text-on-surface-variant hover:bg-surface-container-highest rounded-md transition-colors"
                :placeholder="t('设置')"
              ></button>
            </div>
          </div>
          <!-- Integration 2: WeCom (Syncing) -->
          <div
            class="p-4 sm:px-6 bg-surface-container-low flex flex-col md:flex-row md:items-center justify-between gap-4 border-l-2 border-primary"
          >
            <div class="flex items-center gap-4 flex-1">
              <div
                class="w-10 h-10 rounded-lg bg-surface-low flex items-center justify-center text-on-surface-variant shrink-0"
              ></div>
              <div>
                <h4
                  class="text-headline-md font-headline-md text-on-surface text-base flex items-center gap-2"
                >
                  WeCom<span class="flex h-2 w-2"
                    ><span
                      class="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-primary opacity-75"
                    ></span
                    ><span class="relative inline-flex rounded-full h-2 w-2 bg-primary"></span
                  ></span>
                </h4>
                <p class="text-label-lg font-label-lg text-on-surface-variant">
                  {{ t('企业微信员工沟通') }}
                </p>
              </div>
            </div>
            <div
              class="flex flex-col md:flex-row md:items-center gap-4 md:gap-8 flex-1 md:justify-end"
            >
              <div class="flex flex-col items-start md:items-end">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1">{{
                  t('状态')
                }}</span
                ><span
                  class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-fixed text-on-primary-fixed border border-primary-fixed-dim"
                  >{{ t('同步中……') }}</span
                >
              </div>
              <div class="flex flex-col items-start md:items-end w-32">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1">{{
                  t('上次同步')
                }}</span
                ><span class="text-body-md font-num-md text-on-surface">{{ t('进行中') }}</span>
              </div>
              <div class="flex flex-col items-start md:items-end w-24">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1"
                  >{{ t('记录') }}}</span
                ><span class="text-body-md font-num-md text-on-surface">1,105</span>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0 md:ml-4">
              <button
                class="p-2 text-on-surface-variant opacity-50 cursor-not-allowed rounded-md"
                disabled
                :placeholder="t('同步中……')"
              ></button
              ><button
                class="p-2 text-on-surface-variant hover:bg-surface-container-highest rounded-md transition-colors"
                :placeholder="t('查看日志')"
              ></button
              ><button
                class="p-2 text-on-surface-variant hover:bg-surface-container-highest rounded-md transition-colors"
                :placeholder="t('设置')"
              ></button>
            </div>
          </div>
          <!-- Integration 3: WeChat Pay (Success) -->
          <div
            class="p-4 sm:px-6 hover:bg-surface-container-lowest/50 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
          >
            <div class="flex items-center gap-4 flex-1">
              <div
                class="w-10 h-10 rounded-lg bg-surface-low flex items-center justify-center text-on-surface-variant shrink-0"
              ></div>
              <div>
                <h4 class="text-headline-md font-headline-md text-on-surface text-base">
                  WeChat Pay
                </h4>
                <p class="text-label-lg font-label-lg text-on-surface-variant">
                  {{ t('支付网关') }}
                </p>
              </div>
            </div>
            <div
              class="flex flex-col md:flex-row md:items-center gap-4 md:gap-8 flex-1 md:justify-end"
            >
              <div class="flex flex-col items-start md:items-end">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1">{{
                  t('状态')
                }}</span
                ><span
                  class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-surface-low text-on-surface-variant border border-outline-variant"
                  ><span class="w-1.5 h-1.5 rounded-full bg-surface-low"></span
                  >{{ t('已同步') }}</span
                >
              </div>
              <div class="flex flex-col items-start md:items-end w-32">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1">{{
                  t('上次同步')
                }}</span
                ><span class="text-body-md font-num-md text-on-surface">{{
                  t('10:45（上午）')
                }}</span>
              </div>
              <div class="flex flex-col items-start md:items-end w-24">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1"
                  >{{ t('记录') }}}</span
                ><span class="text-body-md font-num-md text-on-surface">432</span>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0 md:ml-4">
              <button
                class="p-2 text-primary hover:bg-primary-fixed rounded-md transition-colors"
                :placeholder="t('立即同步')"
              ></button
              ><button
                class="p-2 text-on-surface-variant hover:bg-surface-container-highest rounded-md transition-colors"
                :placeholder="t('查看日志')"
              ></button
              ><button
                class="p-2 text-on-surface-variant hover:bg-surface-container-highest rounded-md transition-colors"
                :placeholder="t('设置')"
              ></button>
            </div>
          </div>
          <!-- Integration 4: OTA (Failed - Guardrail R2) -->
          <div
            class="p-4 sm:px-6 bg-surface-low flex flex-col md:flex-row md:items-center justify-between gap-4 border-l-2 border-outline-variant"
          >
            <div class="flex items-center gap-4 flex-1">
              <div
                class="w-10 h-10 rounded-lg bg-surface-low flex items-center justify-center text-on-surface-variant shrink-0"
              ></div>
              <div>
                <h4 class="text-headline-md font-headline-md text-on-surface text-base">
                  {{ t('OTA 渠道') }}
                </h4>
                <p class="text-label-lg font-label-lg text-on-surface-variant">
                  {{ t('在线旅行社（携程，美团）') }}
                </p>
              </div>
            </div>
            <div
              class="flex flex-col md:flex-row md:items-center gap-4 md:gap-8 flex-1 md:justify-end"
            >
              <div class="flex flex-col items-start md:items-end">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1">{{
                  t('状态')
                }}</span
                ><span
                  class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-surface-low text-on-surface-variant border border-outline-variant"
                  ><span class="w-1.5 h-1.5 rounded-full bg-surface-low"></span
                  >{{ t('失败（3 个错误）') }}</span
                >
              </div>
              <div class="flex flex-col items-start md:items-end w-32">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1">{{
                  t('上次同步')
                }}</span
                ><span class="text-body-md font-num-md text-error">{{ t('09:15（上午）') }}</span>
              </div>
              <div class="flex flex-col items-start md:items-end w-24">
                <span class="text-label-lg font-label-lg text-on-surface-variant mb-1"
                  >{{ t('记录') }}}</span
                ><span class="text-body-md font-num-md text-on-surface">3,200</span>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0 md:ml-4">
              <button
                class="px-3 py-1.5 bg-surface-low text-on-surface-variant border border-outline-variant hover:bg-surface-low rounded-md transition-colors text-label-lg font-label-lg font-bold"
                :placeholder="t('需复核')"
              >
                {{ t('复核') }}</button
              ><button
                class="p-2 text-on-surface-variant hover:bg-surface-container-highest rounded-md transition-colors"
                :placeholder="t('设置')"
              ></button>
            </div>
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
