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
    <!-- Top App Bar (Contextual Header) -->

    <!-- Content Grid Area -->
    <div
      class="p-container-padding flex-grow grid grid-cols-1 md:grid-cols-12 gap-gutter items-start max-w-max-content-width mx-auto w-full"
    >
      <!-- LEFT COLUMN: Anomaly Inbox (Span 4) -->
      <section class="md:col-span-4 lg:col-span-4 flex flex-col gap-4">
        <div class="flex items-center justify-between pb-2 border-b border-outline-variant/30">
          <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
            {{ t('异常预警队列') }}
            <span
              class="bg-error-container text-on-error-container text-xs font-num-md px-2 py-0.5 rounded-full"
              >3</span
            >
          </h2>
          <button class="text-primary hover:text-primary-fixed-variant transition-colors">
            <span class="material-symbols-outlined text-sm">filter_list</span>
          </button>
        </div>
        <!-- List Items -->
        <div class="flex flex-col gap-3">
          <!-- Active Item (Selected) -->
          <div
            class="bg-surface-container-lowest border border-primary/50 shadow-[0_2px_12px_rgba(0,91,191,0.08)] rounded-xl p-4 cursor-pointer relative overflow-hidden group"
          >
            <!-- AI Tinge Left Border -->
            <div
              class="absolute left-0 top-0 bottom-0 w-1 bg-primary group-hover:w-1.5 transition-all"
            ></div>
            <div class="flex justify-between items-start mb-2">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-error text-sm icon-fill">warning</span>
                <span class="font-label-lg text-label-lg text-error">{{ t('高优先级') }}</span>
              </div>
              <span class="font-label-lg text-label-lg text-on-surface-variant text-xs">{{
                t('10 分钟前')
              }}</span>
            </div>
            <h3 class="font-headline-lg text-headline-lg-mobile text-on-surface mb-1">
              {{ t('携程房价与 PMS 不一致') }}
            </h3>
            <p class="font-body-md text-body-md text-on-surface-variant line-clamp-2 mb-3">
              {{ t('豪华大床房 (10/12) 的 OTA 挂牌价低于本地 PMS 设定的底线价格。') }}
            </p>
            <div class="flex items-center gap-2 text-xs text-on-surface-variant">
              <span class="bg-surface-container px-2 py-1 rounded font-num-md">ID: ERR-8921</span>
              <span class="flex items-center gap-1 text-tertiary">
                <span class="material-symbols-outlined text-[14px]">auto_awesome</span>
                {{ t('已生成诊断') }}</span
              >
            </div>
          </div>
          <!-- Inactive Item 2 -->
          <div
            class="bg-surface-container-lowest border border-outline-variant hover:border-outline hover:shadow-sm rounded-xl p-4 cursor-pointer transition-all opacity-80 hover:opacity-100"
          >
            <div class="flex justify-between items-start mb-2">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-secondary text-sm">sync_problem</span>
                <span class="font-label-lg text-label-lg text-secondary">{{ t('中优先级') }}</span>
              </div>
              <span class="font-label-lg text-label-lg text-on-surface-variant text-xs">{{
                t('1 小时前')
              }}</span>
            </div>
            <h3 class="font-headline-lg text-headline-lg-mobile text-on-surface mb-1">
              {{ t('Agoda 房态同步失败') }}
            </h3>
            <p class="font-body-md text-body-md text-on-surface-variant line-clamp-1 mb-3">
              {{ t('API 频率限制，标准双床房库存未更新。') }}
            </p>
            <div class="flex items-center gap-2 text-xs text-on-surface-variant">
              <span class="bg-surface-container px-2 py-1 rounded font-num-md">ID: ERR-8919</span>
            </div>
          </div>
          <!-- Inactive Item 3 -->
          <div
            class="bg-surface-container-lowest border border-outline-variant hover:border-outline hover:shadow-sm rounded-xl p-4 cursor-pointer transition-all opacity-80 hover:opacity-100"
          >
            <div class="flex justify-between items-start mb-2">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-secondary text-sm">info</span>
                <span class="font-label-lg text-label-lg text-secondary">{{ t('低优先级') }}</span>
              </div>
              <span class="font-label-lg text-label-lg text-on-surface-variant text-xs">{{
                t('3 小时前')
              }}</span>
            </div>
            <h3 class="font-headline-lg text-headline-lg-mobile text-on-surface mb-1">
              {{ t('美团促销活动映射异常') }}
            </h3>
            <p class="font-body-md text-body-md text-on-surface-variant line-clamp-1 mb-3">
              {{ t('国庆特惠套餐未能识别房型映射。') }}
            </p>
            <div class="flex items-center gap-2 text-xs text-on-surface-variant">
              <span class="bg-surface-container px-2 py-1 rounded font-num-md">ID: ERR-8902</span>
            </div>
          </div>
        </div>
      </section>
      <!-- RIGHT COLUMN: Detail Canvas (Span 8) -->
      <section class="md:col-span-8 lg:col-span-8 flex flex-col gap-6">
        <!-- Main Detail Card -->
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-[1.25rem] p-6 md:p-8 shadow-sm relative overflow-hidden"
        >
          <!-- Decorative subtle gradient top right -->
          <div
            class="absolute -top-24 -right-24 w-64 h-64 bg-tertiary/5 rounded-full blur-3xl pointer-events-none"
          ></div>
          <!-- Header -->
          <div
            class="flex justify-between items-start mb-6 border-b border-outline-variant/30 pb-6"
          >
            <div>
              <div class="flex items-center gap-3 mb-2">
                <span
                  class="bg-error-container text-on-error-container px-3 py-1 rounded-lg font-label-lg text-label-lg flex items-center gap-1"
                >
                  <span class="material-symbols-outlined text-[16px]">dangerous</span>
                  {{ t('异常待处理') }}</span
                >
                <span class="font-num-md text-num-md text-on-surface-variant">ERR-8921</span>
              </div>
              <h2 class="font-display-lg text-display-lg text-on-surface">
                {{ t('携程房价与 PMS 本地库不一致') }}
              </h2>
              <p class="font-body-lg text-body-lg text-on-surface-variant mt-1">
                {{ t('影响房型：豪华大床房 | 影响日期：2023-10-12') }}
              </p>
            </div>
            <button
              class="w-10 h-10 rounded-full border border-outline-variant hover:bg-surface-container flex items-center justify-center text-on-surface transition-colors"
            >
              <span class="material-symbols-outlined">more_vert</span>
            </button>
          </div>
          <!-- AI Diagnosis Panel (Explainable AI) -->
          <div
            class="bg-gradient-to-br from-tertiary-fixed/40 to-surface-container-lowest border border-tertiary/20 rounded-xl p-5 mb-8 relative"
          >
            <div class="flex items-start gap-4">
              <div
                class="w-10 h-10 rounded-full bg-tertiary-container text-on-tertiary-container flex items-center justify-center shrink-0"
              >
                <span class="material-symbols-outlined">psychology</span>
              </div>
              <div>
                <h3
                  class="font-headline-md text-headline-md text-on-surface flex items-center gap-2 mb-2"
                >
                  {{ t('AI 智能诊断详情') }}
                  <span class="material-symbols-outlined text-tertiary text-sm icon-fill"
                    >auto_awesome</span
                  >
                </h3>
                <p class="font-body-md text-body-md text-on-surface-variant mb-4 leading-relaxed">
                  {{ t('检测到价格冲突。系统日志显示，今日 09:14 运营人员在 PMS 后台将')
                  }}<strong class="text-on-surface">{{ t('豪华大床房') }}</strong
                  >{{ t('的价格从 ¥380 上调至') }} <strong class="text-primary">¥450</strong
                  >{{
                    t(
                      '。然而，携程渠道的接口返回错误 `ERR_RATE_LIMIT`，导致更新指令被挂起。目前携程前台依然售卖 ¥380，存在',
                    )
                  }}<strong class="text-error">{{ t('倒挂风险') }}</strong
                  >。
                </p>
                <div class="grid grid-cols-2 gap-4">
                  <div
                    class="bg-surface-container-low rounded-lg p-3 border border-outline-variant/50"
                  >
                    <div class="text-xs font-label-lg text-on-surface-variant mb-1">
                      {{ t('根本原因 (Root Cause)') }}
                    </div>
                    <div class="font-body-md text-on-surface font-medium flex items-center gap-2">
                      <span class="material-symbols-outlined text-error text-[18px]">api</span>
                      {{ t('API 并发限制拦截') }}
                    </div>
                  </div>
                  <div
                    class="bg-surface-container-low rounded-lg p-3 border border-outline-variant/50"
                  >
                    <div class="text-xs font-label-lg text-on-surface-variant mb-1">
                      {{ t('风险评估 (Risk Level)') }}
                    </div>
                    <div class="font-body-md text-error font-medium flex items-center gap-2">
                      <span class="material-symbols-outlined text-[18px]">trending_down</span>
                      {{ t('收益流失风险 (¥70/单)') }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <!-- Sync Traceability Graph (链路追踪图) -->
          <div class="mb-10">
            <h3
              class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2"
            >
              <span class="material-symbols-outlined text-on-surface-variant">schema</span>
              {{ t('同步链路追踪') }}
            </h3>
            <div
              class="bg-surface-container flex items-center justify-between p-8 rounded-xl border border-outline-variant/30 overflow-x-auto"
            >
              <!-- Node 1: PMS -->
              <div class="flex flex-col items-center relative z-10 w-32">
                <div
                  class="w-16 h-16 bg-surface border-2 border-primary rounded-2xl shadow-sm flex items-center justify-center mb-3"
                >
                  <span class="material-symbols-outlined text-primary text-3xl">dns</span>
                </div>
                <span class="font-label-lg text-label-lg text-on-surface font-bold">{{
                  t('PMS 本地库')
                }}</span>
                <span
                  class="font-num-md text-num-md text-primary mt-1 px-2 py-0.5 bg-primary-fixed rounded"
                  >¥ 450</span
                >
                <span class="text-[10px] text-on-surface-variant mt-1">{{
                  t('更新于 09:14')
                }}</span>
              </div>
              <!-- Connector 1 -->
              <div
                class="flex-grow flex flex-col items-center justify-center relative min-w-[100px] h-20 -mx-4"
              >
                <svg class="w-full h-8" preserveaspectratio="none">
                  <line stroke="#005bbf" stroke-width="2" x1="0" x2="100%" y1="50%" y2="50%"></line>
                  <!-- Animated pulse -->
                  <line
                    class="anim-line"
                    stroke="#adc7ff"
                    stroke-width="4"
                    x1="0"
                    x2="100%"
                    y1="50%"
                    y2="50%"
                  ></line>
                  <polygon
                    fill="#005bbf"
                    points="100%,50% 90%,30% 90%,70%"
                    transform="translate(-10, -15) scale(0.6) translate(100, 25)"
                  ></polygon>
                </svg>
                <span
                  class="text-xs text-primary font-medium absolute -top-2 bg-surface-container px-2"
                  >{{ t('指令下发成功') }}</span
                >
              </div>
              <!-- Node 2: Gateway -->
              <div class="flex flex-col items-center relative z-10 w-32">
                <div
                  class="w-16 h-16 bg-surface border-2 border-outline rounded-2xl shadow-sm flex items-center justify-center mb-3"
                >
                  <span class="material-symbols-outlined text-secondary text-3xl">router</span>
                </div>
                <span class="font-label-lg text-label-lg text-on-surface">{{ t('渠道网关') }}</span>
                <span
                  class="font-num-md text-num-md text-on-surface mt-1 px-2 py-0.5 bg-surface-variant rounded"
                  >¥ 450</span
                >
                <span class="text-[10px] text-on-surface-variant mt-1">{{
                  t('接收于 09:14:02')
                }}</span>
              </div>
              <!-- Connector 2 (Error) -->
              <div
                class="flex-grow flex flex-col items-center justify-center relative min-w-[100px] h-20 -mx-4"
              >
                <svg class="w-full h-8" preserveaspectratio="none">
                  <line
                    stroke="#ba1a1a"
                    stroke-dasharray="4 4"
                    stroke-width="2"
                    x1="0"
                    x2="100%"
                    y1="50%"
                    y2="50%"
                  ></line>
                  <polygon
                    fill="#ba1a1a"
                    points="100%,50% 90%,30% 90%,70%"
                    transform="translate(-10, -15) scale(0.6) translate(100, 25)"
                  ></polygon>
                </svg>
                <span
                  class="text-xs text-error font-medium absolute -top-2 bg-surface-container px-2 flex items-center gap-1"
                >
                  <span class="material-symbols-outlined text-[12px]">error</span>
                  {{ t('限流拦截 (429)') }}</span
                >
              </div>
              <!-- Node 3: OTA -->
              <div class="flex flex-col items-center relative z-10 w-32">
                <div
                  class="w-16 h-16 bg-error-container border-2 border-error rounded-2xl shadow-sm flex items-center justify-center mb-3 relative"
                >
                  <span class="material-symbols-outlined text-error text-3xl">language</span>
                  <span
                    class="absolute -top-2 -right-2 w-6 h-6 bg-error text-on-error rounded-full flex items-center justify-center"
                  >
                    <span class="material-symbols-outlined text-[14px]">priority_high</span>
                  </span>
                </div>
                <span class="font-label-lg text-label-lg text-on-surface font-bold">{{
                  t('携程 (Ctrip)')
                }}</span>
                <span
                  class="font-num-md text-num-md text-error mt-1 px-2 py-0.5 bg-surface-lowest border border-error/50 rounded line-through decoration-error"
                  >¥ 380</span
                >
                <span class="text-[10px] text-error mt-1">{{ t('未同步 (脏数据)') }}</span>
              </div>
            </div>
          </div>
          <!-- Recommended Fixes (Guardrails & Confirm Kit) -->
          <div>
            <h3 class="font-headline-md text-headline-md text-on-surface mb-4">
              {{ t('修复方案推荐') }}
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Option 1: AI Auto-reconcile (Primary/Preferred) -->
              <button
                class="group flex flex-col text-left border-2 border-primary bg-primary-fixed/10 hover:bg-primary-fixed/20 rounded-xl p-5 transition-all outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
              >
                <div class="flex justify-between items-center w-full mb-2">
                  <div class="flex items-center gap-2">
                    <span class="material-symbols-outlined text-primary">auto_awesome</span>
                    <span class="font-headline-lg text-headline-lg-mobile text-primary font-bold">{{
                      t('AI 自动对平')
                    }}</span>
                  </div>
                  <span
                    class="bg-primary text-on-primary text-xs px-2 py-1 rounded-full font-label-lg"
                    >{{ t('推荐') }}</span
                  >
                </div>
                <p class="font-body-md text-body-md text-on-surface-variant mb-4">
                  {{
                    t(
                      '智能调度引擎将绕过 API 限制峰值，在通道空闲时自动重试并校验同步结果，直至一致。',
                    )
                  }}
                </p>
                <div
                  class="mt-auto flex items-center text-primary font-label-lg text-label-lg group-hover:translate-x-1 transition-transform"
                >
                  {{ t('一键执行') }}
                  <span class="material-symbols-outlined text-sm ml-1">arrow_forward</span>
                </div>
              </button>
              <!-- Option 2: Force Local Sync (R2 Risk level) -->
              <button
                class="group flex flex-col text-left border-2 border-outline-variant hover:border-error bg-surface hover:bg-error-container/10 rounded-xl p-5 transition-all outline-none focus:ring-2 focus:ring-error focus:ring-offset-2"
              >
                <div class="flex justify-between items-center w-full mb-2">
                  <div class="flex items-center gap-2">
                    <span class="material-symbols-outlined text-on-surface">sync_alt</span>
                    <span
                      class="font-headline-lg text-headline-lg-mobile text-on-surface font-bold"
                      >{{ t('强制以本地为准同步') }}</span
                    >
                  </div>
                </div>
                <p class="font-body-md text-body-md text-on-surface-variant mb-4">
                  {{ t('立即覆盖携程当前数据。该操作属于')
                  }}<span class="text-error font-medium">{{ t('中风险 (R2)') }}</span
                  >{{ t('，可能会覆盖渠道端后台的临时促销设置，需确认执行。') }}
                </p>
                <div
                  class="mt-auto flex items-center text-on-surface font-label-lg text-label-lg group-hover:text-error transition-colors"
                >
                  {{ t('手动确认执行') }}
                  <span class="material-symbols-outlined text-sm ml-1">warning</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </section>
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
