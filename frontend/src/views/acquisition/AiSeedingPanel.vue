<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** AI种草 — 内容灵感与脚本建议（非平台发帖台） */
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const ideas = ref<{ title: string; angle: string; hot?: boolean }[]>([])
const loading = ref(false)

const defaults = [
  { title: t('#周末微度假'), angle: t('周边短途 · 宠物友好 · 高互动话题'), hot: true },
  { title: t('#入住即度假'), angle: t('客房氛围 + 在地体验组合脚本'), hot: false },
  { title: t('#雨天私汤计划'), angle: t('天气热点 · 温暖系短图文分镜'), hot: true },
]

const cards = computed(() => (ideas.value.length ? ideas.value : defaults))

async function load() {
  loading.value = true
  try {
    const r = await api.demo('content')
    if (Array.isArray(r) && r.length) {
      ideas.value = r.slice(0, 6).map((x: any, i: number) => ({
        title: x.title || x.name || `灵感 ${i + 1}`,
        angle: x.desc || x.hint || x.content || t('AI 建议拍摄角度与文案骨架'),
        hot: i < 2,
      }))
    }
  } catch {
    ideas.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface mb-2">{{ t('AI种草') }}</h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('热点选题、拍摄脚本与文案骨架 — 在官方 App 完成最终发布') }}
        </p>
      </div>
      <button
        type="button"
        class="px-4 py-2 rounded-lg bg-primary text-on-primary font-label-lg text-sm"
      >
        {{ t('创作灵感库') }}
      </button>
    </div>

    <div
      class="rounded-xl border border-secondary/30 bg-secondary-container/40 px-4 py-3 text-sm text-on-secondary-container"
    >
      {{ t('成片与发布请在对应公域 App 内完成；此处生成脚本并导出。') }}
    </div>

    <p v-if="loading" class="text-sm text-on-surface-variant">{{ t('加载中…') }}</p>

    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <article
        v-for="(c, i) in cards"
        :key="i"
        class="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 shadow-sm flex flex-col gap-3"
      >
        <div class="flex items-center justify-between">
          <span
            class="text-xs font-bold px-2 py-1 rounded"
            :class="
              c.hot
                ? 'bg-tertiary-container text-on-tertiary-container'
                : 'bg-surface-container-high text-on-surface-variant'
            "
          >
            {{ c.hot ? t('热点') : t('选题') }}</span
          >
          <span class="material-symbols-outlined text-on-surface-variant text-[18px]"
            >auto_awesome</span
          >
        </div>
        <h3 class="font-headline-md text-headline-md text-on-surface m-0">{{ c.title }}</h3>
        <p class="text-sm text-on-surface-variant flex-1 m-0">{{ c.angle }}</p>
        <button
          type="button"
          class="w-full py-2 rounded-lg border border-outline-variant bg-surface-container text-primary font-label-lg text-sm hover:bg-primary-container/10"
        >
          {{ t('生成拍摄脚本') }}
        </button>
      </article>
    </div>
  </div>
</template>
