<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'

// 酒店上下文（固定为 1 号店）
const hotelId = 1
// seed 保留原型示例卡片，保证 1:1 视觉；onMounted 后由真实接口数据覆盖
const seed: any[] = [
  {
    id: 0,
    cls: 'p-4 rounded-lg border border-outline-variant hover:bg-surface-container-low transition-colors cursor-pointer group',
    raw: '\n<div class="flex justify-between items-center">\n<div>\n<h3 class="font-label-lg text-label-lg text-on-surface flex items-center gap-2">\n                                        前台扫码引流 (企微)\n                                        <span class="w-2 h-2 rounded-full bg-[#10b981]"></span>\n</h3>\n<p class="font-body-md text-body-md text-on-surface-variant mt-1 text-sm">">添加管家企微，即享免费延迟退房至14:00")</p>\n</div>\n<label class="relative inline-flex items-center cursor-pointer">\n<input checked="" class="sr-only peer" type="checkbox" value="">\n<div class="w-11 h-6 bg-surface-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[\'\'] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>\n</label>\n</div>\n<div class="mt-3 flex gap-4 text-xs font-label-lg text-on-surface-variant">\n<span>触发节点: 入住办理 (Check-in)</span>\n<span>转化率: <strong class="text-primary">12.4%</strong></span>\n</div>\n',
  },
  {
    id: 1,
    cls: 'p-4 rounded-lg border border-outline-variant hover:bg-surface-container-low transition-colors cursor-pointer group',
    raw: '\n<div class="flex justify-between items-center">\n<div>\n<h3 class="font-label-lg text-label-lg text-on-surface flex items-center gap-2">\n                                        离店后短信召回\n                                        <span class="w-2 h-2 rounded-full bg-[#10b981]"></span>\n</h3>\n<p class="font-body-md text-body-md text-on-surface-variant mt-1 text-sm">">感谢您的入住。点击[链接]领取下次入住9折私域专属券。")</p>\n</div>\n<label class="relative inline-flex items-center cursor-pointer">\n<input checked="" class="sr-only peer" type="checkbox" value="">\n<div class="w-11 h-6 bg-surface-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[\'\'] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>\n</label>\n</div>\n<div class="mt-3 flex gap-4 text-xs font-label-lg text-on-surface-variant">\n<span>触发节点: 离店后 2 小时</span>\n<span>转化率: <strong class="text-primary">8.1%</strong></span>\n</div>\n',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('ota')
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="ota" /></div>
    <!-- Header -->
    <header
      class="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-outline-variant pb-4"
    >
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface">{{ t('OTA转私域运营') }}</h1>
        <p class="font-body-lg text-body-lg text-on-surface-variant mt-2">
          {{ t('将美团、携程订单有效转化为私域会员，降低渠道依赖。') }}
        </p>
      </div>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 border border-outline text-on-surface font-label-lg text-label-lg rounded-full hover:bg-surface-container-low transition-colors flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-lg">download</span>
          {{ t('导出转化报告') }}
        </button>
        <button
          class="px-4 py-2 bg-primary text-on-primary font-label-lg text-label-lg rounded-full hover:bg-on-primary-fixed-variant transition-colors flex items-center gap-2 shadow-sm"
        >
          <span class="material-symbols-outlined text-lg">add</span>
          {{ t('新建转化策略') }}
        </button>
      </div>
    </header>
    <!-- Bento Grid Layout -->
    <div class="grid grid-cols-1 md:grid-cols-12 gap-6">
      <!-- Left Column (Wider) -->
      <div class="md:col-span-8 flex flex-col gap-6">
        <!-- Strategy Setup Card -->
        <section
          class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6 relative overflow-hidden"
        >
          <div class="absolute top-0 left-0 w-1 h-full bg-tertiary"></div>
          <div class="flex justify-between items-start mb-6">
            <div class="flex items-center gap-3">
              <span class="material-symbols-outlined text-tertiary text-3xl">hub</span>
              <h2 class="font-headline-md text-headline-md text-on-surface">
                {{ t('会员转化策略 (Member Conversion Strategy)') }}
              </h2>
            </div>
            <span
              class="px-3 py-1 bg-tertiary-container text-on-tertiary-container rounded-full font-label-lg text-label-lg text-xs flex items-center gap-1"
            >
              <span class="material-symbols-outlined text-sm">bolt</span>
              {{ t('AI 智能匹配运行中') }}</span
            >
          </div>
          <div class="space-y-4">
            <template v-for="(item, i) in rows" :key="i"
              ><div :class="item.cls" v-html="item.raw"></div
            ></template>
          </div>
        </section>
        <!-- Guest History / One ID Preview -->
        <section
          class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6"
        >
          <div class="flex justify-between items-center mb-6">
            <div class="flex items-center gap-3">
              <span class="material-symbols-outlined text-primary text-3xl">stream</span>
              <h2 class="font-headline-md text-headline-md text-on-surface">
                {{ t('客史合并预览 (One ID Merge)') }}
              </h2>
            </div>
            <a
              class="text-primary font-label-lg text-label-lg hover:underline flex items-center gap-1"
              href="#"
            >
              {{ t('查看全部详情') }}
              <span class="material-symbols-outlined text-sm">arrow_forward</span>
            </a>
          </div>
          <div class="bg-surface-container-low rounded-lg p-5">
            <p class="font-body-md text-body-md text-on-surface-variant mb-4 text-sm">
              {{ t('系统检测到以下OTA订单与现有私域会员信息匹配，建议合并档案以提供个性化服务。') }}
            </p>
            <div class="flex flex-col md:flex-row items-center gap-6 justify-center">
              <!-- OTA Profile -->
              <div
                class="bg-surface-container-lowest p-4 rounded-lg border border-outline-variant w-full md:w-1/3 flex flex-col items-center text-center"
              >
                <div
                  class="w-12 h-12 bg-[#ffc300]/20 text-[#ff9900] rounded-full flex items-center justify-center mb-2"
                >
                  <span class="material-symbols-outlined">api</span>
                </div>
                <span class="font-label-lg text-label-lg text-on-surface">{{
                  t('美团外卖客')
                }}</span>
                <span class="font-body-md text-body-md text-on-surface-variant text-xs mt-1">{{
                  t('手机尾号: 8842')
                }}</span>
                <span class="font-body-md text-body-md text-on-surface-variant text-xs">{{
                  t('美团订单: MT-89210')
                }}</span>
              </div>
              <!-- AI Merge Action -->
              <div class="flex flex-col items-center text-tertiary px-4">
                <span class="material-symbols-outlined text-3xl mb-1">sync_alt</span>
                <span
                  class="font-label-lg text-label-lg text-xs bg-tertiary-container text-on-tertiary-container px-2 py-1 rounded-full"
                  >{{ t('AI 匹配度 98%') }}</span
                >
              </div>
              <!-- Private Profile -->
              <div
                class="bg-surface-container-lowest p-4 rounded-lg border-2 border-primary/20 w-full md:w-1/3 flex flex-col items-center text-center relative overflow-hidden"
              >
                <div
                  class="absolute top-0 right-0 w-8 h-8 bg-primary-container rounded-bl-lg flex items-center justify-center"
                >
                  <span class="material-symbols-outlined text-on-primary-container text-sm"
                    >workspace_premium</span
                  >
                </div>
                <div
                  class="w-12 h-12 bg-primary-container text-on-primary-container rounded-full flex items-center justify-center mb-2"
                >
                  <span class="material-symbols-outlined">person</span>
                </div>
                <span class="font-label-lg text-label-lg text-on-surface">{{
                  t('张伟 (金卡会员)')
                }}</span>
                <span class="font-body-md text-body-md text-on-surface-variant text-xs mt-1">{{
                  t('手机尾号: 8842')
                }}</span>
                <span class="font-body-md text-body-md text-on-surface-variant text-xs">{{
                  t('累计入住: 5晚')
                }}</span>
              </div>
            </div>
            <div class="mt-6 flex justify-end gap-3">
              <button
                class="px-4 py-2 border border-outline text-on-surface font-label-lg text-label-lg rounded-full hover:bg-surface-variant transition-colors"
              >
                {{ t('暂不合并') }}
              </button>
              <button
                class="px-4 py-2 bg-primary text-on-primary font-label-lg text-label-lg rounded-full hover:bg-on-primary-fixed-variant transition-colors shadow-sm"
              >
                {{ t('确认合并记录') }}
              </button>
            </div>
          </div>
        </section>
      </div>
      <!-- Right Column (Narrower) -->
      <div class="md:col-span-4 flex flex-col gap-6">
        <!-- Channel Direct Connect -->
        <section
          class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6"
        >
          <h2
            class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-primary">cable</span>
            {{ t('直连状态 (Channel Connect)') }}
          </h2>
          <ul class="space-y-4">
            <li
              class="flex items-center justify-between p-3 rounded-lg bg-surface-container-low border border-transparent hover:border-outline-variant transition-colors"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded-full bg-[#ffc300] flex items-center justify-center text-white font-bold text-xs"
                >
                  {{ t('美') }}
                </div>
                <div>
                  <div class="font-label-lg text-label-lg text-on-surface">{{ t('美团酒店') }}</div>
                  <div class="font-body-md text-body-md text-on-surface-variant text-xs">
                    {{ t('已同步 15 分钟前') }}
                  </div>
                </div>
              </div>
              <span
                class="px-2 py-1 bg-[#10b981]/10 text-[#10b981] rounded text-xs font-label-lg flex items-center gap-1"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span> {{ t('正常') }}</span
              >
            </li>
            <li
              class="flex items-center justify-between p-3 rounded-lg bg-surface-container-low border border-transparent hover:border-outline-variant transition-colors"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 rounded-full bg-[#0f4098] flex items-center justify-center text-white font-bold text-xs"
                >
                  {{ t('携') }}
                </div>
                <div>
                  <div class="font-label-lg text-label-lg text-on-surface">{{ t('携程旅行') }}</div>
                  <div class="font-body-md text-body-md text-on-surface-variant text-xs">
                    {{ t('已同步 2 分钟前') }}
                  </div>
                </div>
              </div>
              <span
                class="px-2 py-1 bg-[#10b981]/10 text-[#10b981] rounded text-xs font-label-lg flex items-center gap-1"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span> {{ t('正常') }}</span
              >
            </li>
          </ul>
        </section>
        <!-- Reputation Management -->
        <section
          class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6 relative"
        >
          <div
            class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary to-tertiary"
          ></div>
          <h2
            class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2 mt-2"
          >
            <span class="material-symbols-outlined text-primary">reviews</span>
            {{ t('网评管理 (Reputation)') }}
          </h2>
          <div class="grid grid-cols-2 gap-4 mb-6">
            <div class="bg-surface-container-low p-4 rounded-lg text-center">
              <div class="font-num-xl text-num-xl text-on-surface">
                4.8<span class="text-sm font-body-md text-on-surface-variant">/5</span>
              </div>
              <div class="font-label-lg text-label-lg text-on-surface-variant mt-1">
                {{ t('美团平均分') }}
              </div>
            </div>
            <div class="bg-surface-container-low p-4 rounded-lg text-center">
              <div class="font-num-xl text-num-xl text-on-surface">
                4.7<span class="text-sm font-body-md text-on-surface-variant">/5</span>
              </div>
              <div class="font-label-lg text-label-lg text-on-surface-variant mt-1">
                {{ t('携程平均分') }}
              </div>
            </div>
          </div>
          <div class="border-t border-outline-variant pt-4">
            <h3 class="font-label-lg text-label-lg text-on-surface mb-3">
              {{ t('待处理差评警报 (Warning)') }}
            </h3>
            <!-- Alert Item -->
            <div class="bg-[#ffdad6]/30 border border-[#ffdad6] rounded-lg p-3 relative">
              <div class="absolute -left-1 top-3 w-2 h-8 bg-error rounded-r-md"></div>
              <div class="pl-2">
                <div class="flex justify-between items-start">
                  <span class="font-label-lg text-label-lg text-on-surface text-sm">{{
                    t('携程 - 匿名用户')
                  }}</span>
                  <span class="text-xs text-on-surface-variant">{{ t('昨天 22:15') }}</span>
                </div>
                <div class="flex items-center gap-1 mt-1 mb-2">
                  <span
                    class="material-symbols-outlined text-error text-sm"
                    style="font-variation-settings: 'FILL' 1"
                    >star</span
                  >
                  <span
                    class="material-symbols-outlined text-error text-sm"
                    style="font-variation-settings: 'FILL' 1"
                    >star</span
                  >
                  <span
                    class="material-symbols-outlined text-outline-variant text-sm"
                    style="font-variation-settings: 'FILL' 1"
                    >star</span
                  >
                  <span
                    class="material-symbols-outlined text-outline-variant text-sm"
                    style="font-variation-settings: 'FILL' 1"
                    >star</span
                  >
                  <span
                    class="material-symbols-outlined text-outline-variant text-sm"
                    style="font-variation-settings: 'FILL' 1"
                    >star</span
                  >
                </div>
                <p class="font-body-md text-body-md text-on-surface-variant text-xs line-clamp-2">
                  {{ t('\"隔音太差了，半夜能听到走廊说话，热水也不够热...\"') }}
                </p>
                <button
                  class="mt-3 text-primary font-label-lg text-label-lg text-xs hover:underline flex items-center gap-1"
                >
                  {{ t('AI生成回复草稿') }}
                  <span class="material-symbols-outlined text-[14px]">smart_toy</span>
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 原型自定义工具类（v-html 内联卡片的根节点由 Vue 渲染，可命中） */
.ai-glow {
  box-shadow: 0 0 15px rgba(140, 51, 179, 0.15);
  border-left: 2px solid #8c33b3;
}
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
