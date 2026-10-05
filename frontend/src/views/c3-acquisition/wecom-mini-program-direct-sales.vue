<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'
import AcquisitionLoopPanel from '../../components/AcquisitionLoopPanel.vue'

// 酒店上下文（固定为 1 号店）
const hotelId = 1
// seed 保留原型示例卡片，保证 1:1 视觉；onMounted 后由真实接口数据覆盖
const seed: any[] = [
  {
    id: 0,
    cls: 'col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col relative overflow-hidden',
    raw: '<div class="absolute top-0 right-0 w-32 h-32 bg-primary-fixed-dim/20 rounded-bl-full -z-10 blur-2xl pointer-events-none"></div><div class="flex justify-between items-center mb-6"><div class="flex items-center gap-3"><div class="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center text-primary"></div><div><h2 class="font-headline-md text-headline-md text-on-surface">企业微信 CRM 管道</h2><p class="font-label-lg text-label-lg text-on-surface-variant">按渠道与 标准作业程序 流程自动给线索打标</p></div></div><span class="px-3 py-1 bg-tertiary-fixed text-on-tertiary-fixed-variant rounded-full font-label-lg text-xs flex items-center gap-1 border border-tertiary-fixed-dim">AI 打标已启用</span></div>\n<!-- CRM Pipeline Visualization -->\n<div class="flex-1 flex flex-col justify-center"><div class="flex gap-4 overflow-x-auto pb-4">\n<!-- Stage 1: Incoming -->\n<div class="min-w-[200px] flex-1 bg-surface-container-low rounded-lg p-4 border border-outline-variant/50"><h3 class="font-label-lg text-label-lg text-on-surface mb-3 flex justify-between items-center">新进线索<span class="bg-surface-variant text-on-surface px-2 py-0.5 rounded text-xs">24</span></h3><div class="space-y-2"><div class="bg-surface-container-lowest p-3 rounded shadow-sm border border-outline-variant/30 text-sm"><div class="flex justify-between mb-1"><span class="font-medium text-on-surface">Mr. Wang</span><span class="text-xs text-on-surface-variant">2 分钟前</span></div><div class="flex gap-1 mt-2"><span class="text-[10px] px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-200">Douyin</span><span class="text-[10px] px-1.5 py-0.5 bg-tertiary-fixed text-on-tertiary-fixed-variant rounded border border-tertiary-fixed-dim flex items-center">高意向</span></div></div><div class="bg-surface-container-lowest p-3 rounded shadow-sm border border-outline-variant/30 text-sm"><div class="flex justify-between mb-1"><span class="font-medium text-on-surface">Ms. Li</span><span class="text-xs text-on-surface-variant">15 分钟前</span></div><div class="flex gap-1 mt-2"><span class="text-[10px] px-1.5 py-0.5 bg-orange-50 text-orange-700 rounded border border-orange-200">Ctrip (OTA)</span></div></div></div></div>\n<!-- Arrow -->\n<div class="flex flex-col justify-center text-outline-variant"></div>\n<!-- Stage 2: SOP Executing -->\n<div class="min-w-[200px] flex-1 bg-surface-container-low rounded-lg p-4 border border-primary/20 relative overflow-hidden"><div class="absolute left-0 top-0 w-1 h-full bg-primary"></div><h3 class="font-label-lg text-label-lg text-on-surface mb-3 flex justify-between items-center">标准作业程序 流程<span class="bg-primary-container text-on-primary-container px-2 py-0.5 rounded text-xs">启用</span></h3><div class="space-y-3"><div class="flex items-start gap-2"><div class="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center mt-0.5 text-primary"></div><div class="text-sm"><p class="text-on-surface font-medium">发送欢迎消息</p><p class="text-xs text-on-surface-variant">基于标签个性化</p></div></div><div class="flex items-start gap-2"><div class="w-5 h-5 rounded-full bg-tertiary-fixed flex items-center justify-center mt-0.5 text-on-tertiary-fixed-variant animate-pulse"></div><div class="text-sm"><p class="text-on-surface font-medium">推荐房型</p><p class="text-xs text-tertiary">AI 正在计算最佳匹配……</p></div></div></div></div></div></div>',
  },
  {
    id: 1,
    cls: 'col-span-12 lg:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col',
    raw: '<div class="flex justify-between items-start mb-6"><h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">直售营收</h2><button class="text-primary hover:bg-surface-container rounded p-1 transition-colors"></button></div><div class="flex-1 flex flex-col justify-between"><div class="mb-4"><p class="text-sm text-on-surface-variant mb-1">免佣金营收（本月至今）</p><div class="flex items-baseline gap-2"><span class="font-num-xl text-display-lg text-on-surface">¥42,850</span><span class="text-sm text-green-600 font-medium flex items-center">+12.5%</span></div></div><div class="space-y-4"><div><div class="flex justify-between text-sm mb-1"><span class="text-on-surface-variant">小程序预订</span><span class="font-medium text-on-surface">65%</span></div><div class="w-full bg-surface-variant rounded-full h-2"><div class="bg-primary h-2 rounded-full" style="width: 65%"></div></div></div><div><div class="flex justify-between text-sm mb-1"><span class="text-on-surface-variant">企业微信转化</span><span class="font-medium text-on-surface">35%</span></div><div class="w-full bg-surface-variant rounded-full h-2"><div class="bg-secondary h-2 rounded-full" style="width: 35%"></div></div></div></div><div class="mt-6 pt-4 border-t border-outline-variant/50"><button class="w-full py-2 bg-surface-container hover:bg-surface-container-high transition-colors rounded-lg text-primary font-label-lg flex justify-center items-center gap-2 border border-outline-variant/30">管理门户设置</button></div></div>',
  },
  {
    id: 2,
    cls: 'col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant p-0 shadow-sm overflow-hidden flex flex-col md:flex-row',
    raw: '\n<!-- Left Panel: One ID Info -->\n<div class="w-full md:w-1/3 p-6 border-r border-outline-variant bg-surface/50"><div class="flex items-center gap-2 mb-4"><h3 class="font-headline-md text-headline-md text-on-surface">一号通会员</h3></div><p class="text-sm text-on-surface-variant mb-6">跨渠道客人画像与个性化优惠生成。</p><div class="bg-surface-container-lowest p-4 rounded-lg border-l-2 border-tertiary shadow-sm mb-4"><div class="flex items-center justify-between mb-3"><div class="flex items-center gap-3"><div class="w-10 h-10 rounded-full bg-surface-variant bg-cover bg-center" style="background-image: url(\'https://lh3.googleusercontent.com/aida-public/AB6AXuA9xahwJxCboOBH_lU_U9Zfy9vRbvXNIiozj1vIXcQQDjBQgMhYgbT0qtVfIpGGgzj6OxKJAu2Pjkzthg0QBUbXFiB_YU_1frORZIm4HIzx6brQG-kqCH5GEEAnSkszexSO9LTwj_Vv5_WRZu4YP4NFwDJdklrH83k-ydTLzyOtYeX7xSVSOG6DRhEggFCUiQLPBQARsef14h0IJJ-DUui_sZadmZoMYO5PAZn42C9WmkGWYitrS-k\')"></div><div><p class="font-medium text-on-surface leading-tight">Sarah Chen</p><p class="text-xs text-on-surface-variant">黄金会员</p></div></div></div><div class="grid grid-cols-2 gap-2 text-xs"><div class="bg-surface-container-low p-2 rounded"><span class="block text-on-surface-variant mb-0.5">入住次数</span><span class="font-num-md text-on-surface font-bold">12</span></div><div class="bg-surface-container-low p-2 rounded"><span class="block text-on-surface-variant mb-0.5">偏好</span><span class="text-on-surface font-medium">安静客房</span></div></div></div><button class="w-full py-2 border border-outline-variant rounded text-on-surface hover:bg-surface-container-low transition-colors text-sm font-medium flex items-center justify-center gap-2">会员等级</button></div>\n<!-- Right Panel: Personalized Offers (AI Generated) -->\n<div class="w-full md:w-2/3 p-6 bg-surface-container-lowest relative"><div class="flex justify-between items-center mb-6"><h4 class="font-headline-md text-headline-md text-on-surface">AI 个性化优惠</h4><div class="flex gap-2"><span class="px-2 py-1 bg-surface-container-low rounded text-xs text-on-surface-variant border border-outline-variant/50">目标：Sarah Chen</span></div></div><div class="grid grid-cols-1 md:grid-cols-2 gap-4">\n<!-- Offer Card 1 -->\n<div class="border border-outline-variant hover:border-tertiary/50 rounded-lg p-4 transition-colors group relative overflow-hidden bg-surface-container-lowest shadow-sm hover:shadow-md cursor-pointer"><div class="absolute inset-0 bg-gradient-to-br from-tertiary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div><div class="flex justify-between items-start mb-2"><div class="bg-tertiary-fixed text-on-tertiary-fixed-variant p-1.5 rounded-md inline-flex"></div><span class="text-xs font-medium text-tertiary flex items-center gap-1 border border-tertiary/20 rounded-full px-2 py-0.5 bg-tertiary/5">92% 匹配</span></div><h5 class="font-label-lg text-label-lg text-on-surface mb-1">免费延迟退房</h5><p class="text-xs text-on-surface-variant mb-4 line-clamp-2">基于其通常 15:00 离店的历史，提供 14:00 延迟退房可提升复购概率。</p><button class="text-sm font-medium text-primary hover:text-primary-fixed-variant flex items-center gap-1">推送至企业微信</button></div>\n<!-- Offer Card 2 -->\n<div class="border border-outline-variant hover:border-primary/50 rounded-lg p-4 transition-colors group relative overflow-hidden bg-surface-container-lowest shadow-sm hover:shadow-md cursor-pointer"><div class="flex justify-between items-start mb-2"><div class="bg-primary-container text-on-primary-container p-1.5 rounded-md inline-flex"></div><span class="text-xs font-medium text-tertiary flex items-center gap-1 border border-tertiary/20 rounded-full px-2 py-0.5 bg-tertiary/5">78% 匹配</span></div><h5 class="font-label-lg text-label-lg text-on-surface mb-1">SPA 套餐升级</h5><p class="text-xs text-on-surface-variant mb-4 line-clamp-2">折扣 SPA 权益。该客频繁预订周末休闲住宿。</p><button class="text-sm font-medium text-primary hover:text-primary-fixed-variant flex items-center gap-1">推送至小程序</button></div></div></div>',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('wecom')
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="main" /></div>
    <AcquisitionLoopPanel focus="book" />
    <div class="max-w-max-content-width mx-auto space-y-6">
      <!-- Page Header -->
      <div class="flex justify-between items-end mb-8">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface mb-2">
            {{ t('企业微信与小程序直售') }}
          </h1>
          <p class="font-body-lg text-body-lg text-on-surface-variant">
            {{ t('企微承接 + 小程序直销') }}
          </p>
        </div>
        <div class="flex gap-3">
          <button
            class="px-4 py-2 border border-outline-variant rounded-lg text-primary font-label-lg flex items-center gap-2 hover:bg-surface-container-low transition-colors bg-surface-container-lowest shadow-sm"
          >
            {{ t('生成渠道二维码') }}</button
          ><button
            class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg flex items-center gap-2 hover:bg-primary-fixed-variant transition-colors shadow-sm"
          >
            {{ t('新建推广') }}
          </button>
        </div>
      </div>
      <!-- Bento Grid Layout -->
      <div class="grid grid-cols-12 gap-gutter">
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
