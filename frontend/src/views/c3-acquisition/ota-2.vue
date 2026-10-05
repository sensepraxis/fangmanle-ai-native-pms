<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'

// OTA 动态调价与活动管理页：忠实移植自 ota-2.html 内容区
// 列表用 v-for；无数据时用 api.demo('ota-2') 兜底，缺失回退原型示例。

const hotelId = 1
const meta = ref<any>({
  title: t('OTA 动态调价与活动管理'),
  subtitle: t('轻松管理跨渠道定价策略并同步促销。'),
})

// AI 调价建议（主列表，受 api.demo 覆盖）
const suggestions = ref<any[]>([
  {
    tag: t('高优先级'),
    tagClass: 'bg-error/10 text-error',
    channel: t('携程'),
    room: t('豪华大床房'),
    time: t('今晚'),
    desc: t('周边竞对（5km内）均已下调价格15%。建议下调以抢占最后预订窗口。'),
    curLabel: t('当前价'),
    cur: '¥580',
    curClass: 'text-on-surface line-through',
    sugLabel: t('建议价'),
    sug: '¥498',
    sugClass: 'text-tertiary font-num-xl',
    border: 'border-l-2 border-tertiary',
    btns: [
      { t: t('一键执行'), cls: 'flex-1 bg-tertiary text-on-tertiary' },
      {
        t: t('忽略'),
        cls: 'px-4 py-2 border border-outline-variant rounded-lg text-on-surface-variant',
      },
    ],
  },
  {
    tag: t('日常调优'),
    tagClass: 'bg-primary-container/20 text-primary',
    channel: t('美团'),
    room: t('标准双床房'),
    time: t('本周末'),
    desc: t('预计本周末本地有大型演出活动，需求量上升，建议微调上浮。'),
    curLabel: t('当前价'),
    cur: '¥320',
    curClass: 'text-on-surface',
    sugLabel: t('建议价'),
    sug: '¥358',
    sugClass: 'text-primary font-bold',
    border: 'border-l-2 border-primary',
    btns: [{ t: t('采纳建议'), cls: 'flex-1 bg-primary text-on-primary' }],
  },
])

// 价格护栏
const guardrails = ref<any[]>([
  { label: t('最低保底价'), scope: t('全局生效'), icon: 'bg-error/10 text-error', value: '¥199' },
  {
    label: t('最高限价'),
    scope: t('全局生效'),
    icon: 'bg-primary/10 text-primary',
    value: '¥1,299',
  },
])

// 渠道促销同步
const promos = ref<any[]>([
  {
    channel: 'Ctrip',
    channelClass: 'bg-blue-50 text-blue-600 border-blue-100',
    name: t('早鸟特惠'),
    desc: t('提前7天预订享85折'),
    status: t('启用'),
    statusClass: 'bg-green-100 text-green-800',
    on: true,
  },
  {
    channel: t('美团'),
    channelClass: 'bg-yellow-50 text-yellow-600 border-yellow-100',
    name: t('尾房甩卖'),
    desc: t('当日18:00后预订立减50元'),
    status: t('启用'),
    statusClass: 'bg-green-100 text-green-800',
    on: true,
  },
  {
    channel: t('全部'),
    channelClass: 'bg-gray-100 text-gray-500 border-gray-200',
    name: t('连住优惠'),
    desc: t('连住3晚及以上享9折'),
    status: t('已暂停'),
    statusClass: 'bg-gray-100 text-gray-600',
    on: false,
    dim: true,
  },
])

// 活动日历
const calendar = ref<any[]>([
  {
    title: t('双11 预售期'),
    date: '10.20 - 10.31',
    desc: t('全渠道库存锁定，需提前设定阶梯价格。'),
    dot: 'bg-surface border-2 border-primary',
    box: 'bg-primary-container/10 border-primary/20',
    titleClass: 'text-primary',
    chips: [t('携程已同步'), t('飞猪待确认')],
  },
  {
    title: t('双11 狂欢期'),
    date: '11.01 - 11.11',
    desc: t('建议启用 AI 动态调价，根据实时满房率自动溢价。'),
    dot: 'bg-surface border-2 border-tertiary',
    box: 'bg-tertiary-container/10 border-tertiary/20',
    titleClass: 'text-tertiary',
    link: t('配置 AI 策略'),
  },
  {
    title: t('元旦特惠'),
    date: '12.25 - 01.03',
    desc: t('活动策划中，尚未推送至渠道。'),
    dot: 'bg-surface-container-highest border-2 border-outline-variant',
    box: 'bg-surface-container-lowest border-outline-variant',
    titleClass: 'text-on-surface',
    dim: true,
  },
])

onMounted(async () => {
  try {
    const r: any = await api.demo('ota-2')
    if (Array.isArray(r) && r.length) suggestions.value = r
  } catch (e) {
    /* 兜底：保留原型示例调价建议 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="ota" /></div>
    <div class="max-w-max-content-width mx-auto">
      <!-- 页头 -->
      <div class="flex justify-between items-end mb-8">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface mb-2">{{ meta.title }}</h1>
          <p class="font-body-md text-body-md text-on-surface-variant">{{ meta.subtitle }}</p>
        </div>
        <div class="flex gap-3">
          <button
            class="bg-surface border border-outline-variant text-primary px-4 py-2 rounded-lg font-label-lg text-label-lg hover:bg-surface-container-low transition-colors flex items-center gap-2"
          >
            {{ t('同步所有渠道') }}
          </button>
        </div>
      </div>

      <div class="grid grid-cols-12 gap-gutter">
        <!-- AI 调价建议执行 -->
        <div
          class="col-span-12 lg:col-span-8 bg-surface rounded-xl border border-outline-variant p-6 shadow-sm relative overflow-hidden flex flex-col h-[400px]"
        >
          <div
            class="absolute top-0 right-0 w-64 h-64 bg-tertiary-container/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none"
          ></div>
          <div class="flex justify-between items-center mb-6 relative z-10">
            <div class="flex items-center gap-2">
              <h2 class="font-headline-md text-headline-md text-on-surface">
                {{ t('AI 调价建议执行') }}
              </h2>
            </div>
            <span
              class="bg-tertiary-container/20 text-tertiary px-3 py-1 rounded-full font-label-lg text-label-lg text-xs flex items-center gap-1"
            >
              <span class="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span
              >{{ t('实时监控中') }}</span
            >
          </div>
          <div class="overflow-y-auto pr-2 space-y-4 flex-grow relative z-10">
            <div
              v-for="s in suggestions"
              :key="s.room"
              class="bg-surface-bright border-t border-r border-b border-outline-variant/30 rounded-r-lg p-4 hover:shadow-md transition-shadow"
              :class="s.border"
            >
              <div class="flex justify-between items-start mb-2">
                <div class="flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded text-xs font-bold" :class="s.tagClass">{{
                    s.tag
                  }}</span>
                  <h3 class="font-label-lg text-label-lg text-on-surface">
                    {{ s.channel }} - {{ s.room }}
                  </h3>
                </div>
                <span class="font-num-md text-num-md text-on-surface-variant">{{ s.time }}</span>
              </div>
              <p class="font-body-md text-body-md text-on-surface-variant text-sm mb-3">
                {{ s.desc }}
              </p>
              <div
                class="flex items-center justify-between bg-surface-container-low p-2 rounded-md mb-3"
              >
                <div class="text-center flex-1">
                  <div class="text-xs text-on-surface-variant">{{ s.curLabel }}</div>
                  <div class="font-num-md text-num-md" :class="s.curClass">{{ s.cur }}</div>
                </div>
                <div class="text-center flex-1">
                  <div
                    class="text-xs font-bold"
                    :class="
                      s.sugClass === 'text-tertiary font-bold' ? 'text-tertiary' : 'text-primary'
                    "
                  >
                    {{ s.sugLabel }}
                  </div>
                  <div class="font-num-md text-num-md" :class="s.sugClass">{{ s.sug }}</div>
                </div>
              </div>
              <div class="flex gap-2">
                <button
                  v-for="b in s.btns"
                  :key="b.t"
                  class="py-2 rounded-lg font-label-lg text-label-lg hover:opacity-90 transition-colors"
                  :class="b.cls"
                >
                  {{ b.t }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 价格护栏状态 -->
        <div
          class="col-span-12 lg:col-span-4 bg-surface rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col h-[400px]"
        >
          <div class="flex justify-between items-center mb-6">
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('价格护栏状态') }}
            </h2>
            <button
              class="text-primary hover:bg-primary-container/10 p-1 rounded transition-colors"
            ></button>
          </div>
          <p class="font-body-md text-body-md text-on-surface-variant text-sm mb-6">
            {{ t('防止各渠道出现意外的低价引流。') }}
          </p>
          <div class="space-y-6 flex-grow">
            <div v-for="g in guardrails" :key="g.label">
              <div class="flex justify-between items-end mb-2">
                <span class="font-label-lg text-label-lg text-on-surface">{{ g.label }}</span>
                <span class="font-num-md text-num-md text-on-surface-variant text-sm">{{
                  g.scope
                }}</span>
              </div>
              <div
                class="bg-surface-container-lowest border border-outline-variant rounded-lg p-3 flex items-center justify-between"
              >
                <div class="flex items-center gap-3">
                  <div
                    class="w-8 h-8 rounded-full flex items-center justify-center"
                    :class="g.icon"
                  ></div>
                  <span class="font-body-md text-body-md text-on-surface">{{ g.value }}</span>
                </div>
                <div class="h-2 w-2 rounded-full bg-green-500"></div>
              </div>
            </div>
            <div
              class="mt-auto bg-surface-container-low p-3 rounded-lg border border-outline-variant/50 flex items-start gap-2"
            >
              <div class="text-sm">
                <span class="font-bold text-on-surface block">{{ t('护栏安全') }}</span>
                <span class="text-on-surface-variant text-xs">{{
                  t('当前所有OTA渠道挂牌价均在护栏范围内。')
                }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 渠道促销同步 -->
        <div
          class="col-span-12 lg:col-span-6 bg-surface rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <div class="flex justify-between items-center mb-6">
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('渠道促销同步') }}
            </h2>
            <button class="text-primary text-sm font-label-lg hover:underline">
              {{ t('查看全部') }}
            </button>
          </div>
          <div class="space-y-4">
            <div
              v-for="p in promos"
              :key="p.name"
              class="border border-outline-variant rounded-lg p-4 hover:bg-surface-container-lowest transition-colors flex items-center justify-between"
              :class="{ 'opacity-70': p.dim }"
            >
              <div class="flex items-center gap-4">
                <div
                  class="w-10 h-10 rounded flex items-center justify-center font-bold text-xs border"
                  :class="p.channelClass"
                >
                  {{ p.channel }}
                </div>
                <div>
                  <h3 class="font-label-lg text-label-lg text-on-surface font-bold">
                    {{ p.name }}
                  </h3>
                  <p class="text-xs text-on-surface-variant mt-1">{{ p.desc }}</p>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-[10px] px-2 py-1 rounded font-bold" :class="p.statusClass">{{
                  p.status
                }}</span>
                <label class="relative inline-flex items-center cursor-pointer">
                  <input :checked="p.on" class="sr-only peer" type="checkbox" value="" />
                  <div
                    class="w-9 h-5 bg-outline-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"
                  ></div>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- 活动日历 -->
        <div
          class="col-span-12 lg:col-span-6 bg-surface rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <div class="flex justify-between items-center mb-6">
            <h2 class="font-headline-md text-headline-md text-on-surface">{{ t('活动日历') }}</h2>
            <div class="flex gap-2">
              <button class="p-1 rounded hover:bg-surface-container-low transition-colors"></button>
              <span class="font-label-lg text-label-lg self-center px-2">{{
                t('2024年 10月')
              }}</span>
              <button class="p-1 rounded hover:bg-surface-container-low transition-colors"></button>
            </div>
          </div>
          <div
            class="relative border-l-2 border-surface-container-highest ml-4 space-y-8 mt-4 pb-4"
          >
            <div
              v-for="n in calendar"
              :key="n.title"
              class="relative pl-6"
              :class="{ 'opacity-60': n.dim }"
            >
              <div class="absolute w-4 h-4 rounded-full -left-[9px] top-1" :class="n.dot"></div>
              <div class="border rounded-lg p-3" :class="n.box">
                <div class="flex justify-between items-start">
                  <h4 class="font-label-lg text-label-lg font-bold" :class="n.titleClass">
                    {{ n.title }}
                  </h4>
                  <span
                    class="text-xs text-on-surface-variant font-mono bg-surface-container px-2 py-1 rounded"
                    >{{ n.date }}</span
                  >
                </div>
                <p class="text-sm text-on-surface-variant mt-2">{{ n.desc }}</p>
                <div v-if="n.chips" class="mt-3 flex gap-2">
                  <span
                    v-for="c in n.chips"
                    :key="c"
                    class="text-[10px] bg-white border border-outline-variant px-2 py-0.5 rounded text-on-surface-variant"
                    >{{ c }}</span
                  >
                </div>
                <button
                  v-if="n.link"
                  class="mt-2 text-xs font-bold flex items-center gap-1 hover:underline"
                  :class="n.titleClass"
                >
                  {{ n.link }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
</style>
