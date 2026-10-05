<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'
import AcquisitionLoopPanel from '../../components/AcquisitionLoopPanel.vue'

// 内容种草中心页：忠实移植自 room-board.html 内容区（原文件名为 room-board，内容即内容种草中心）
// 列表用 v-for；无数据时用 api.demo('content-seeding') 兜底，缺失回退原型示例。

const hotelId = 1
const meta = ref<any>({
  title: t('内容种草中心'),
  subtitle: t('内容集成中心 - AI 驱动的社媒管理。'),
})

// 今日创作建议（主列表，受 api.demo 覆盖）
const ideas = ref<any[]>([
  {
    badge: t('小红书'),
    badgeClass: 'bg-tertiary-container/20 text-tertiary',
    tag: t('热点'),
    title: t('#周末逃离城市计划'),
    desc: t(
      '基于近期降温天气，AI 建议发布带有“私汤”、“温暖”标签的短图文。已有 80% 本地竞品开始推送此类内容。',
    ),
    btn: t('一键生成草稿'),
    btnClass:
      'bg-surface-container text-primary hover:bg-primary-container/10 border-outline-variant',
    glow: 'ai-glow',
  },
  {
    badge: t('视频号'),
    badgeClass: 'bg-secondary-container text-on-secondary-container',
    tag: t('节假日预热'),
    title: t('元旦跨年氛围感'),
    desc: t('建议剪辑一段 15s 的酒店大堂壁炉氛围视频，配以温馨音乐，提前锁定跨年夜房源预订。'),
    btn: t('查看灵感'),
    btnClass:
      'bg-surface-container text-on-surface hover:bg-surface-variant border-outline-variant',
    glow: 't(',
  },
])

// 近期日历事件
const events = ref<any[]>([
  {
    day: '今天',
    dayClass: 'bg-primary-container/10 text-primary',
    title: t('下午茶上新推广'),
    time: '14:00',
    badge: t('未发布'),
    badgeClass: 'bg-error-container text-on-error-container',
  },
  {
    day: t('24日'),
    dayClass: 'bg-surface-container-high text-on-surface-variant',
    title: t('圣诞主题房探店视频'),
    time: t('待定'),
    badge: t('草稿中'),
    badgeClass: 'bg-secondary-container text-on-secondary-container',
    dim: true,
  },
])

// 素材库
const assets = ref<any[]>([
  {
    img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDyzYWPht5MnC8rsiXjofG6Eh3ldODJLmNuUbqR06hOuzfZJTLljBe-kctxfQ-WGqanlHAYNJ_y4l9PIH3UK2w2ZKevxAV4RBkn2BdB3_lMQdechSDRC7zhPgyeu9ph3NPDlCZkaPEPyNgQv39RLl7NCEPSqJyWMLuXCy2uqq-ePCe8rEnIYfJQkTCU1Zh_qxC-k6VzHyGn0Yt69tQcK6xnjPiMO8K85OWx_VeqVzcxbf22E2Iz5B4',
  },
])

onMounted(async () => {
  try {
    const r: any = await api.demo('content-seeding')
    if (Array.isArray(r) && r.length) ideas.value = r
  } catch (e) {
    /* 兜底：保留原型示例创作建议 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="main" /></div>
    <AcquisitionLoopPanel focus="overview" />
    <div class="max-w-[1440px] mx-auto">
      <!-- 页头 -->
      <div class="flex justify-between items-end mb-8">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-background mb-2">{{ meta.title }}</h1>
          <p class="font-body-lg text-body-lg text-on-surface-variant">{{ meta.subtitle }}</p>
        </div>
        <button
          class="bg-primary text-on-primary font-label-lg text-label-lg px-6 py-3 rounded-full hover:bg-primary-fixed-dim hover:text-on-primary-fixed transition-colors shadow-sm flex items-center gap-2"
        >
          {{ t('新建内容') }}
        </button>
      </div>

      <div class="grid grid-cols-12 gap-gutter">
        <!-- 今日创作建议 -->
        <div class="col-span-12 lg:col-span-8 grid grid-cols-2 gap-gutter">
          <div class="col-span-2">
            <h2
              class="font-headline-md text-headline-md text-on-background mb-4 flex items-center gap-2"
            >
              {{ t('今日创作建议') }}
            </h2>
          </div>
          <div
            v-for="it in ideas"
            :key="it.title"
            class="bg-surface-container-lowest rounded-xl p-6 shadow-sm border border-outline-variant flex flex-col justify-between"
            :class="it.glow"
          >
            <div>
              <div class="flex justify-between items-start mb-4">
                <span class="text-xs font-bold px-2 py-1 rounded" :class="it.badgeClass">{{
                  it.badge
                }}</span>
                <span class="text-on-surface-variant text-sm flex items-center gap-1">{{
                  it.tag
                }}</span>
              </div>
              <h3 class="font-headline-lg text-headline-lg text-on-surface mb-2">{{ it.title }}</h3>
              <p class="font-body-md text-body-md text-on-surface-variant line-clamp-3 mb-4">
                {{ it.desc }}
              </p>
            </div>
            <button
              class="w-full bg-surface-container font-label-lg py-2 rounded-lg hover:bg-primary-container/10 transition-colors border"
              :class="it.btnClass"
            >
              {{ it.btn }}
            </button>
          </div>
        </div>

        <!-- 近期日历 -->
        <div
          class="col-span-12 lg:col-span-4 bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant flex flex-col"
        >
          <div class="p-6 border-b border-outline-variant flex justify-between items-center">
            <h2 class="font-headline-md text-headline-md text-on-background">
              {{ t('近期日历') }}
            </h2>
            <button class="text-primary hover:bg-primary-container/10 p-1 rounded"></button>
          </div>
          <div class="p-4 flex-1">
            <div class="space-y-4">
              <div v-for="e in events" :key="e.title" class="flex gap-4 items-start">
                <div
                  class="flex flex-col items-center justify-center rounded-lg w-12 h-12 flex-shrink-0"
                  :class="e.dayClass"
                >
                  <span class="text-sm font-bold">{{ e.day }}</span>
                </div>
                <div
                  class="flex-1 bg-surface rounded-lg p-3 border border-outline-variant"
                  :class="{ 'opacity-75': e.dim }"
                >
                  <div class="flex justify-between mb-1">
                    <span class="font-label-lg text-on-surface">{{ e.title }}</span>
                    <span class="text-xs text-on-surface-variant">{{ e.time }}</span>
                  </div>
                  <span class="text-xs px-2 py-0.5 rounded" :class="e.badgeClass">{{
                    e.badge
                  }}</span>
                </div>
              </div>
            </div>
          </div>
          <div
            class="p-4 border-t border-outline-variant bg-surface-container-low/50 mt-auto rounded-b-xl"
          >
            <button class="w-full text-center text-primary font-label-lg hover:underline">
              {{ t('查看完整日历') }}
            </button>
          </div>
        </div>

        <!-- 素材库快速预览 -->
        <div class="col-span-12 mt-4">
          <div class="flex justify-between items-center mb-4">
            <h2 class="font-headline-md text-headline-md text-on-background">
              {{ t('素材库快速预览') }}
            </h2>
            <a
              class="text-primary font-label-lg hover:underline flex items-center gap-1"
              href="#"
              >{{ t('全部素材') }}</a
            >
          </div>
          <div class="grid grid-cols-4 gap-4">
            <div
              v-for="(a, i) in assets"
              :key="i"
              class="aspect-square bg-surface-container rounded-xl overflow-hidden relative group"
            >
              <img class="w-full h-full object-cover" :src="a.img" :alt="t('素材')" />
              <div
                class="absolute inset-0 bg-on-background/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
              >
                <button class="bg-surface text-on-surface rounded-full p-2"></button>
              </div>
            </div>
            <div
              class="aspect-square bg-surface-container rounded-xl overflow-hidden relative group border-2 border-dashed border-outline-variant flex items-center justify-center hover:bg-surface-container-high transition-colors cursor-pointer"
            >
              <div class="text-center text-on-surface-variant">
                <p class="font-label-lg">{{ t('上传新素材') }}</p>
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
.ai-glow {
  box-shadow: 0 0 15px rgba(140, 51, 179, 0.15);
  border-left: 2px solid #8c33b3;
}
</style>
