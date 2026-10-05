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
    cls: 'card-level-1 p-6 relative group overflow-hidden',
    raw: '\n<div class="absolute inset-y-0 left-0 w-1 bg-tertiary"></div> <!-- AI Tinge -->\n<div class="flex justify-between items-start mb-4">\n<div class="flex gap-4 items-center">\n<img alt="Streamer Avatar" class="w-16 h-16 rounded-full border-2 border-outline-variant object-cover" data-alt="A portrait of a trendy Chinese travel influencer, female, early 20s, smiling, wearing stylish casual outdoor clothing, high quality photography, bright lighting." src="https://lh3.googleusercontent.com/aida-public/AB6AXuBmDzT8ADgvZd5g-Xm4RFSkRruHBs1gtB8-hbBQ85VL1YYKHKvy7OsJ0KFcdWsdMNS_S-oWrfwqw9ULYpnOtLFYDp71wGS7Mi3QuOIgREY2zQO1VHl7meOtmG8unsOET2ggnKmYk50fcKGR3tdaSetES4oyNu3cuDdBwcsECT8mQsGB7Pk7uK0lMWRZv7rsmDCX-KLPpGrXeCJ6VXqlHcYNyFOOc8DdLeAzL9ij5eTKVt-t6dgbCls">\n<div>\n<h3 class="font-headline-lg text-headline-lg text-on-background flex items-center gap-2">\n                                        旅行的林子\n                                        <span class="bg-tertiary-container text-on-tertiary-container text-xs px-2 py-0.5 rounded-full font-label-lg flex items-center gap-1">\n<span class="material-symbols-outlined text-[12px] icon-fill">auto_awesome</span>\n                                            98% 匹配\n                                        </span>\n</h3>\n<p class="text-sm text-on-surface-variant flex items-center gap-1">\n<span class="material-symbols-outlined text-[14px]">group</span> 125W 粉丝 \n                                        <span class="mx-2 text-outline-variant">|</span>\n<span class="material-symbols-outlined text-[14px]">location_on</span> 江浙沪\n                                    </p>\n</div>\n</div>\n<div class="flex gap-2">\n<button class="bg-surface-container text-on-surface font-label-lg px-3 py-1.5 rounded text-sm hover:bg-surface-variant transition-colors border border-outline-variant">\n                                    分发脚本\n                                </button>\n<button class="bg-primary text-on-primary font-label-lg px-3 py-1.5 rounded text-sm hover:bg-on-primary-fixed-variant transition-colors">\n                                    发送邀请\n                                </button>\n</div>\n</div>\n<!-- Metrics Grid -->\n<div class="grid grid-cols-4 gap-4 mb-4 bg-surface-bright rounded-lg p-4 border border-outline-variant">\n<div>\n<p class="text-xs text-on-surface-variant mb-1">近期转化率</p>\n<p class="font-num-xl text-num-xl text-primary">4.2%</p>\n</div>\n<div>\n<p class="text-xs text-on-surface-variant mb-1 flex items-center gap-1">千次曝光成交额(GPM) <span class="material-symbols-outlined text-[12px] text-outline cursor-help" title="Gross Merchandise Value per Mille">info</span></p>\n<p class="font-num-xl text-num-xl text-on-background">¥4,120</p>\n</div>\n<div class="col-span-2">\n<p class="text-xs text-on-surface-variant mb-1 flex items-center gap-1">\n<span class="material-symbols-outlined text-[14px] text-tertiary icon-fill">auto_awesome</span>\n                                    AI 预测本次合作 ROI\n                                </p>\n<div class="flex items-center gap-2 mt-2">\n<div class="w-full h-2 bg-surface-variant rounded-full overflow-hidden">\n<div class="h-full bg-tertiary progress-bar-fill rounded-full" style="--target-width: 85%;"></div>\n</div>\n<span class="font-num-md text-num-md text-tertiary font-bold">1:4.5</span>\n</div>\n</div>\n</div>\n<!-- Script & Status Area -->\n<div class="flex items-center justify-between text-sm bg-surface-container-low p-3 rounded">\n<div class="flex items-center gap-2">\n<span class="material-symbols-outlined text-outline">description</span>\n<span class="text-on-surface">推荐脚本：</span>\n<a class=")text-primary hover:underline" href="#">《周末避世指南：隐藏在山林间的绝美民宿》</a>\n</div>\n<div class="flex items-center gap-2">\n<span class="w-2 h-2 rounded-full bg-outline"></span>\n<span class="text-on-surface-variant text-xs">未联系</span>\n</div>\n</div>\n',
  },
  {
    id: 1,
    cls: 'card-level-1 p-6 relative group overflow-hidden',
    raw: '\n<div class="flex justify-between items-start mb-4">\n<div class="flex gap-4 items-center">\n<img alt="Streamer Avatar" class="w-16 h-16 rounded-full border-2 border-outline-variant object-cover" data-alt="A portrait of a male lifestyle influencer, late 20s, holding a coffee cup in a minimalist cafe, casual chic attire, high quality photography, soft natural light." src="https://lh3.googleusercontent.com/aida-public/AB6AXuCeIn_JuLhQ_rG_kZ5YRfTb1nBSFquvdJtNTHyIpXVHUYJv3uN9377rGo_0INy5z2qhpqR4-Sxp1QyzenklmmkBSE0iXYC79FVd1reIo1zlyhbQQLrDI6iLkx3baVAUqBjp4qa3KRqjugOBH6F5IiIuTlnukNnE3n2paCinwlv8evW9pAttkGb7AZ9A5n1qS-oXlzNpvEJKni1plpmI6j9RrqM4GRNqppybncHEwCbOfP3fC49arEg">\n<div>\n<h3 class="font-headline-lg text-headline-lg text-on-background flex items-center gap-2">\n                                        陈老板带你住\n                                        <span class="bg-surface-container-highest text-on-surface-variant text-xs px-2 py-0.5 rounded-full font-label-lg">\n                                            82% 匹配\n                                        </span>\n</h3>\n<p class="text-sm text-on-surface-variant flex items-center gap-1">\n<span class="material-symbols-outlined text-[14px]">group</span> 85W 粉丝 \n                                        <span class="mx-2 text-outline-variant">|</span>\n<span class="material-symbols-outlined text-[14px]">location_on</span> 全国\n                                    </p>\n</div>\n</div>\n<div class="flex gap-2">\n<button class="bg-surface-container text-on-surface font-label-lg px-3 py-1.5 rounded text-sm hover:bg-surface-variant transition-colors border border-outline-variant">\n                                    分发脚本\n                                </button>\n<button class="bg-surface-container-highest text-on-surface font-label-lg px-3 py-1.5 rounded text-sm hover:bg-outline-variant transition-colors">\n                                    邀请中\n                                </button>\n</div>\n</div>\n<!-- Metrics Grid -->\n<div class="grid grid-cols-4 gap-4 mb-4 bg-surface-bright rounded-lg p-4 border border-outline-variant">\n<div>\n<p class="text-xs text-on-surface-variant mb-1">近期转化率</p>\n<p class="font-num-xl text-num-xl text-on-background">2.8%</p>\n</div>\n<div>\n<p class="text-xs text-on-surface-variant mb-1 flex items-center gap-1">千次曝光成交额(GPM)</p>\n<p class="font-num-xl text-num-xl text-on-background">¥2,850</p>\n</div>\n<div class="col-span-2">\n<p class="text-xs text-on-surface-variant mb-1 flex items-center gap-1">\n<span class="material-symbols-outlined text-[14px] text-tertiary icon-fill">auto_awesome</span>\n                                    AI 预测本次合作 ROI\n                                </p>\n<div class="flex items-center gap-2 mt-2">\n<div class="w-full h-2 bg-surface-variant rounded-full overflow-hidden">\n<div class="h-full bg-primary progress-bar-fill rounded-full" style="--target-width: 60%;"></div>\n</div>\n<span class="font-num-md text-num-md text-on-background font-medium">1:2.8</span>\n</div>\n</div>\n</div>\n<!-- Script & Status Area -->\n<div class="flex items-center justify-between text-sm bg-surface-container-low p-3 rounded border border-[#ffd54f]"> <!-- Low Risk yellow border logic applied slightly here for \'Pending\' -->\n<div class="flex items-center gap-2">\n<span class="material-symbols-outlined text-outline">description</span>\n<span class="text-on-surface">已发送脚本：</span>\n<span class="text-on-surface-variant">《设计感拉满的避暑圣地》</span>\n</div>\n<div class="flex items-center gap-2 text-secondary">\n<span class="w-2 h-2 rounded-full bg-[#fbc02d]"></span>\n<span class="text-xs font-medium">等待博主确认 (已发送 2天)</span>\n</div>\n</div>\n',
  },
  {
    id: 2,
    cls: 'card-level-1 p-6 relative group overflow-hidden border-l-4 border-l-[#4caf50]',
    raw: '\n<div class="flex justify-between items-start mb-4">\n<div class="flex gap-4 items-center">\n<img alt="Streamer Avatar" class="w-16 h-16 rounded-full border-2 border-[#4caf50] object-cover p-0.5" data-alt="A vibrant lifestyle shot of a young couple taking a selfie with a scenic mountain view in the background, high energy, travel influencer style." src="https://lh3.googleusercontent.com/aida-public/AB6AXuCK25Gzx-tzauE1ci2VNoT0bODvW2rfnW6MSlqXGPySklFYCCYo8Uj0d8KObIGFLwFWeK_zv3TIJw485hEa-G2HENcxa9BhgDxLDon6yR7ZX-KpqpIvsQnQ3n36tRK9LdWbVkuRBYW3BexmRueFIw6zv_xxtxHT1bKjXaFogM6g3vK4uYxjn820GbQwE6hHV0dxk4NF0Vx-VlvNLxVUfnQLhBi9DIY9rVRGjFxYXFwB2fGCZwkzTVg">\n<div>\n<h3 class="font-headline-lg text-headline-lg text-on-background flex items-center gap-2">\n                                        周末去哪儿\n                                        <span class="bg-surface-container-highest text-on-surface-variant text-xs px-2 py-0.5 rounded-full font-label-lg">\n                                            75% 匹配\n                                        </span>\n</h3>\n<p class="text-sm text-on-surface-variant flex items-center gap-1">\n<span class="material-symbols-outlined text-[14px]">group</span> 50W 粉丝 \n                                        <span class="mx-2 text-outline-variant">|</span>\n<span class="material-symbols-outlined text-[14px]">location_on</span> 杭州周边\n                                    </p>\n</div>\n</div>\n<div class="flex gap-2">\n<button class="bg-[#e8f5e9] text-[#2e7d32] font-label-lg px-3 py-1.5 rounded text-sm hover:bg-[#c8e6c9] transition-colors border border-[#a5d6a7] flex items-center gap-1">\n<span class="material-symbols-outlined text-[16px]">chat</span>\n                                    沟通中\n                                </button>\n</div>\n</div>\n<!-- Status Alert (R0 Info style logic) -->\n<div class="bg-[#e3f2fd] border border-[#bbdefb] p-3 rounded mb-4 flex items-start gap-2">\n<span class="material-symbols-outlined text-[#1976d2] mt-0.5">info</span>\n<div>\n<p class="text-sm text-[#0d47a1] font-medium">博主已接受邀请</p>\n<p class="text-xs text-[#1565c0] mt-1">预计直播时间：2023年10月25日 20:00。请准备专属优惠券链接。</p>\n</div>\n</div>\n',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('influencer')
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
    <!-- Page Header -->
    <div class="flex justify-between items-end mb-8">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background mb-2">
          {{ t('抖音达人库') }}
        </h1>
        <p class="text-on-surface-variant font-body-lg">
          {{ t('AI智能匹配旅游博主，精准预测直播转化收益。') }}
        </p>
      </div>
      <div class="flex gap-4">
        <button
          class="bg-surface-container text-on-surface font-label-lg px-4 py-2 rounded-lg border border-outline-variant hover:bg-surface-container-high transition-colors flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-sm">history</span>
          {{ t('合作记录') }}
        </button>
        <button
          class="bg-primary text-on-primary font-label-lg px-4 py-2 rounded-lg hover:bg-on-primary-fixed-variant transition-colors flex items-center gap-2 shadow-sm ai-glow"
        >
          <span class="material-symbols-outlined text-sm icon-fill">auto_awesome</span>
          {{ t('AI批量邀请') }}
        </button>
      </div>
    </div>
    <!-- Dashboard Grid -->
    <div class="grid grid-cols-12 gap-gutter mb-8">
      <!-- Filters & Context (Span 3) -->
      <div class="col-span-12 lg:col-span-3 flex flex-col gap-gutter">
        <!-- AI Insight Card -->
        <div
          class="card-level-1 p-6 relative overflow-hidden bg-surface-bright border-l-4 border-l-tertiary"
        >
          <div class="absolute top-0 right-0 p-4 opacity-10">
            <span class="material-symbols-outlined text-6xl text-tertiary icon-fill"
              >auto_awesome</span
            >
          </div>
          <h2
            class="font-headline-md text-headline-md text-on-background mb-4 flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-tertiary icon-fill text-xl"
              >psychology</span
            >
            {{ t('AI 匹配洞察') }}
          </h2>
          <p class="text-on-surface-variant text-sm mb-4">
            {{
              t(
                '根据您的精品酒店特性（"山景"、"设计感"、"情侣度假"），AI筛选出以下近期在江浙沪地区转化表现优异的旅游博主。',
              )
            }}
          </p>
          <div class="bg-surface-container-low rounded p-3 text-xs text-on-surface">
            <span class="block font-medium mb-1 text-primary">{{ t('推荐策略：') }}</span>
            {{ t('建议本周主推') }} <strong>{{ t('#周末逃离计划') }}</strong>
            {{ t('话题，搭配博主 "旅行的林子" 的探店直播，预计ROI可达 1:4.2。') }}
          </div>
        </div>
        <!-- Filter Panel -->
        <div class="card-level-1 p-6">
          <h3
            class="font-headline-md text-headline-md text-on-background mb-4 flex items-center justify-between"
          >
            {{ t('筛选条件') }}
            <span class="material-symbols-outlined text-outline text-lg">filter_list</span>
          </h3>
          <div class="space-y-4">
            <div>
              <label class="block text-xs font-label-lg text-on-surface-variant mb-1">{{
                t('受众标签')
              }}</label>
              <div class="flex flex-wrap gap-2">
                <span
                  class="bg-primary-container text-on-primary-container px-2 py-1 rounded-full text-xs cursor-pointer border border-primary"
                  >{{ t('旅游探店') }}</span
                >
                <span
                  class="bg-primary-container text-on-primary-container px-2 py-1 rounded-full text-xs cursor-pointer border border-primary"
                  >{{ t('情侣出行') }}</span
                >
                <span
                  class="bg-surface-container-high text-on-surface px-2 py-1 rounded-full text-xs cursor-pointer hover:bg-surface-variant transition-colors border border-outline-variant"
                  >{{ t('亲子度假') }}</span
                >
                <span
                  class="bg-surface-container-high text-on-surface px-2 py-1 rounded-full text-xs cursor-pointer hover:bg-surface-variant transition-colors border border-outline-variant"
                  >{{ t('高端酒店') }}</span
                >
              </div>
            </div>
            <div>
              <label class="block text-xs font-label-lg text-on-surface-variant mb-1">{{
                t('带货能力 (GPM)')
              }}</label>
              <input
                class="w-full h-1 bg-surface-variant rounded-lg appearance-none cursor-pointer accent-primary"
                max="10000"
                min="0"
                type="range"
                value="3000"
              />
              <div class="flex justify-between text-[10px] text-outline mt-1">
                <span>¥0</span>
                <span>¥3000+</span>
                <span>¥10000</span>
              </div>
            </div>
            <div>
              <label class="block text-xs font-label-lg text-on-surface-variant mb-1">{{
                t('合作模式')
              }}</label>
              <select
                class="w-full bg-surface text-on-surface text-sm rounded border-outline-variant focus:ring-primary focus:border-primary p-2"
              >
                <option>{{ t('纯佣金 (CPS)') }}</option>
                <option>{{ t('坑位费 + 佣金') }}</option>
                <option>{{ t('免费置换 (探店体验)') }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>
      <!-- Match Results (Span 9) -->
      <div class="col-span-12 lg:col-span-9 flex flex-col gap-gutter">
        <template v-for="(item, i) in rows" :key="i"
          ><div :class="item.cls" v-html="item.raw"></div
        ></template>
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
