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
    cls: 'p-4 border-b border-outline-variant flex justify-between items-center bg-surface-bright',
    raw: '<h2 class="font-headline-md text-headline-md flex items-center gap-2">周边态势</h2><span class="px-2 py-1 bg-primary-fixed text-on-primary-fixed rounded text-xs font-label-lg">POI 状态：已激活且已验证</span>',
  },
  {
    id: 1,
    cls: 'relative flex-1 min-h-[300px] bg-surface-container',
    raw: '\n<!-- Map Placeholder -->\n<div class="absolute inset-0 bg-cover bg-center" data-location="Hangzhou" style="background-image: url(\'https://lh3.googleusercontent.com/aida-public/AB6AXuCM9QvVRCv9IEGgk4ZquUiGL3iUq6h-xuc9ZWAcDdRB4QYemYHrQPlT2ejKQpmMzizokVyKfG3gXP4ORUyxuxjlVQeZzQMF1e5ZhH2r_qu3k1jBnlz_naR2OGmVAjEfuQXMv6OSHA8pZgNjtDqgtxzjEX0P6r9dGuTnpTw6lXpupjybgEK1xwDXOQOYSHlaAfPcI3XXZSNNbWgVrF1fbssmCDhlVf393LhG5KYF4xouv5kTmjSgW4M\')"></div>\n<!-- Overlay Details (Glassmorphism) -->\n<div class="absolute bottom-4 left-4 right-4 bg-surface-container-lowest/90 backdrop-blur-md p-4 rounded-lg border border-outline-variant/50 flex gap-4"><div class="flex-1 border-r border-outline-variant/30 pr-4"><p class="text-xs text-on-surface-variant font-label-lg mb-1">本店热度</p><p class="font-num-xl text-num-xl text-primary">8,432<span class="text-xs text-on-surface-variant font-body-md">浏览/天</span></p></div><div class="flex-1 border-r border-outline-variant/30 px-4"><p class="text-xs text-on-surface-variant font-label-lg mb-1">周边竞品</p><p class="font-num-xl text-num-xl text-secondary">12<span class="text-xs text-on-surface-variant font-body-md">3公里内</span></p></div><div class="flex-1 pl-4"><p class="text-xs text-on-surface-variant font-label-lg mb-1">AI 建议</p><p class="text-sm text-tertiary font-body-md flex items-center gap-1">定向周末周边游。</p></div></div>',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('poi')
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="douyin" /></div>
    <!-- Header -->
    <header class="mb-6 flex justify-between items-end">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background">{{ t('抖音 POI 管理') }}</h1>
        <p class="text-on-surface-variant font-body-md mt-1">
          {{ t('监测存在感、管理优惠券并优化预订转化。') }}
        </p>
      </div>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 border border-outline rounded-full font-label-lg text-on-surface flex items-center gap-2 hover:bg-surface-container-low transition-colors"
        >
          {{ t('同步数据') }}</button
        ><button
          class="px-4 py-2 bg-primary text-on-primary rounded-full font-label-lg flex items-center gap-2 shadow-sm hover:opacity-90 transition-opacity"
        >
          {{ t('新建团购') }}
        </button>
      </div>
    </header>
    <!-- Bento Grid Layout -->
    <div class="grid grid-cols-12 gap-gutter">
      <!-- Map & Competitor Widget (Spans 8 cols) -->
      <section
        class="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden shadow-sm flex flex-col"
      >
        <template v-for="(item, i) in rows" :key="i"
          ><div :class="item.cls" v-html="item.raw"></div
        ></template>
      </section>
      <!-- Conversion Funnel (Spans 4 cols) -->
      <section
        class="col-span-12 lg:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm flex flex-col"
      >
        <h2 class="font-headline-md text-headline-md flex items-center gap-2 mb-4">
          {{ t('转化漏斗') }}
        </h2>
        <div class="flex-1 flex flex-col justify-center gap-4">
          <!-- Funnel Step 1 -->
          <div class="relative pl-6 pb-4 border-l-2 border-primary-fixed-dim">
            <div
              class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-primary flex items-center justify-center border-2 border-surface-container-lowest"
            ></div>
            <div class="flex justify-between items-baseline mb-1">
              <span class="font-label-lg text-on-surface">{{ t('POI 浏览量') }}</span
              ><span class="font-num-md text-num-md">45,210</span>
            </div>
            <div class="w-full bg-surface-container h-2 rounded-full overflow-hidden">
              <div class="bg-primary-fixed-dim h-full w-[100%]"></div>
            </div>
          </div>
          <!-- Funnel Step 2 -->
          <div class="relative pl-6 pb-4 border-l-2 border-primary-fixed-dim">
            <div
              class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-primary flex items-center justify-center border-2 border-surface-container-lowest"
            ></div>
            <div class="flex justify-between items-baseline mb-1">
              <span class="font-label-lg text-on-surface">{{ t('领券/加购') }}</span
              ><span class="font-num-md text-num-md">3,840</span>
            </div>
            <div class="w-full bg-surface-container h-2 rounded-full overflow-hidden flex">
              <div class="bg-primary-container h-full w-[45%]"></div>
              <span class="ml-2 text-xs text-on-surface-variant">8.5%</span>
            </div>
          </div>
          <!-- Funnel Step 3 -->
          <div class="relative pl-6">
            <div
              class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-tertiary flex items-center justify-center border-2 border-surface-container-lowest shadow-[0_0_8px_rgba(140,51,179,0.4)]"
            ></div>
            <div class="flex justify-between items-baseline mb-1">
              <span class="font-label-lg text-tertiary font-bold">{{ t('实际核销') }}</span
              ><span class="font-num-md text-num-md text-tertiary font-bold">812</span>
            </div>
            <div class="w-full bg-surface-container h-2 rounded-full overflow-hidden flex">
              <div class="bg-tertiary h-full w-[21%]"></div>
              <span class="ml-2 text-xs text-on-surface-variant">21.1%</span>
            </div>
          </div>
        </div>
        <div class="mt-4 p-3 bg-surface-bright border-l-2 border-tertiary rounded-r-lg">
          <p class="text-sm text-on-surface flex gap-2">
            {{ t('AI 提示：转化率高于品类均值 4%。') }}
          </p>
        </div>
      </section>
      <!-- Group Buying Vouchers (Spans 7 cols) -->
      <section
        class="col-span-12 lg:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm"
      >
        <div class="flex justify-between items-center mb-4">
          <h2 class="font-headline-md text-headline-md flex items-center gap-2">
            {{ t('团购券管理') }}
          </h2>
          <span class="text-sm text-primary cursor-pointer hover:underline">{{
            t('查看全部')
          }}</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Voucher Card 1 -->
          <div
            class="border border-outline-variant rounded-lg p-4 bg-surface-bright relative overflow-hidden group hover:border-primary-fixed-dim transition-colors cursor-pointer"
          >
            <div
              class="absolute top-0 right-0 bg-primary text-on-primary text-xs px-2 py-1 rounded-bl-lg font-label-lg z-10"
            >
              {{ t('启用') }}
            </div>
            <h3 class="font-headline-md text-[16px] mb-1">{{ t('2天1晚 浪漫海景双床房') }}</h3>
            <div class="flex items-end gap-2 mb-3">
              <span class="text-error font-num-xl text-num-xl">¥599</span
              ><span class="text-outline line-through text-sm">¥899</span>
            </div>
            <div class="flex justify-between text-sm text-on-surface-variant">
              <span>{{ t('已售：') }}<strong class="text-on-surface">450</strong></span
              ><span>{{ t('库存：') }}<strong class="text-on-surface">50</strong></span>
            </div>
            <div
              class="mt-3 pt-3 border-t border-outline-variant/50 flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <button class="text-primary text-sm hover:underline">{{ t('编辑') }}</button
              ><button class="text-primary text-sm hover:underline">{{ t('视频链接') }}</button>
            </div>
          </div>
          <!-- Voucher Card 2 -->
          <div
            class="border border-outline-variant rounded-lg p-4 bg-surface-bright relative overflow-hidden group hover:border-primary-fixed-dim transition-colors cursor-pointer"
          >
            <div
              class="absolute top-0 right-0 bg-outline text-on-surface-lowest text-xs px-2 py-1 rounded-bl-lg font-label-lg z-10"
            >
              {{ t('已排程') }}
            </div>
            <h3 class="font-headline-md text-[16px] mb-1">{{ t('周末早午餐 单人自助') }}</h3>
            <div class="flex items-end gap-2 mb-3">
              <span class="text-on-surface font-num-xl text-num-xl">¥128</span
              ><span class="text-outline line-through text-sm">¥188</span>
            </div>
            <div class="flex justify-between text-sm text-on-surface-variant">
              <span>{{ t('已售：') }}<strong class="text-on-surface">0</strong></span
              ><span>{{ t('库存：') }}<strong class="text-on-surface">200</strong></span>
            </div>
            <div
              class="mt-3 pt-3 border-t border-outline-variant/50 flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <button class="text-primary text-sm hover:underline">{{ t('编辑') }}</button
              ><button class="text-primary text-sm hover:underline">{{ t('视频链接') }}</button>
            </div>
          </div>
        </div>
      </section>
      <!-- AI Video Hooks (Spans 5 cols) -->
      <section
        class="col-span-12 lg:col-span-5 bg-surface-container-lowest border border-tertiary-fixed-dim rounded-xl p-5 shadow-[0_4px_12px_rgba(140,51,179,0.05)] flex flex-col relative overflow-hidden"
      >
        <!-- Decorative AI Glow -->
        <div
          class="absolute -top-10 -right-10 w-32 h-32 bg-tertiary-fixed blur-3xl opacity-50 rounded-full pointer-events-none"
        ></div>
        <div class="flex justify-between items-center mb-4 z-10">
          <h2 class="font-headline-md text-headline-md flex items-center gap-2 text-tertiary">
            {{ t('AI 视频灵感') }}
          </h2>
          <button
            class="text-tertiary hover:bg-tertiary-fixed/50 p-1 rounded transition-colors"
          ></button>
        </div>
        <p class="text-sm text-on-surface-variant mb-4 z-10">
          {{ t('基于当前抖音热门标签与你的 POI 特征，为创作者推荐的内容角度。') }}
        </p>
        <div class="flex-1 flex flex-col gap-3 z-10">
          <!-- Hook 1 -->
          <div
            class="p-3 border border-outline-variant rounded-lg bg-surface hover:border-tertiary-fixed-dim transition-colors cursor-pointer group"
          >
            <div class="flex justify-between items-start mb-1">
              <span class="font-label-lg text-on-surface">{{ t('“宝藏周末”') }}</span
              ><span class="text-xs text-primary bg-primary-fixed px-2 py-0.5 rounded">{{
                t('高潜力')
              }}</span>
            </div>
            <p class="text-sm text-on-surface-variant line-clamp-2">
              {{ t('聚焦阳台静谧的清晨海景。使用热门 lofi 音频。') }}
            </p>
            <div class="mt-2 text-xs flex gap-2">
              <span class="text-outline">#staycation</span
              ><span class="text-outline">#boutiquehotel</span>
            </div>
          </div>
          <!-- Hook 2 -->
          <div
            class="p-3 border border-outline-variant rounded-lg bg-surface hover:border-tertiary-fixed-dim transition-colors cursor-pointer group"
          >
            <div class="flex justify-between items-start mb-1">
              <span class="font-label-lg text-on-surface">{{ t('“房型参观 + 早午餐”') }}</span
              ><span class="text-xs text-outline bg-surface-container px-2 py-0.5 rounded">{{
                t('平稳')
              }}</span>
            </div>
            <p class="text-sm text-on-surface-variant line-clamp-2">
              {{ t('快节奏剪辑房型亮点，结尾揭晓 ¥128 早午餐券。') }}
            </p>
            <div class="mt-2 text-xs flex gap-2">
              <span class="text-outline">#hotelreview</span
              ><span class="text-outline">#foodie</span>
            </div>
          </div>
        </div>
      </section>
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
