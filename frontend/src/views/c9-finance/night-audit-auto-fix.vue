<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// C9 夜审自动修复（night-audit-auto-fix）
// 可嵌入「夜间审计」页下方
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const props = withDefaults(
  defineProps<{
    embedded?: boolean
  }>(),
  { embedded: false },
)

const router = useRouter()

const progress = ref(92)

type Issue = {
  id?: number
  tag: string
  tagCls: string
  bar: string
  badgeCls: string
  ref: string
  title: string
  text: string
  ai: string
  action: 'approve' | 'fix' | 'self'
}
const issues = ref<Issue[]>([])

function mapException(e: any): Issue {
  const sev = e.severity || 'mid'
  const fixed = e.status === 'fixed' || e.status === 'ignored'
  if (sev === 'high') {
    return {
      id: e.id,
      tag: 'R2 - 需确认',
      tagCls: 'bg-[#f57c00] text-white',
      bar: 'bg-[#f57c00]',
      badgeCls: 'bg-[#f57c00]/50 bg-[#ffe0b2]/20',
      ref: e.code || `#${e.id}`,
      title: e.title,
      text: e.detail || '',
      ai: fixed ? '已处理完成。' : '建议人工复核后一键修复账务差异。',
      action: fixed ? 'self' : 'fix',
    }
  }
  if (sev === 'low') {
    return {
      id: e.id,
      tag: 'R0 - 信息',
      tagCls: 'bg-primary text-white',
      bar: 'bg-primary',
      badgeCls: 'bg-primary/30 bg-primary-container/10',
      ref: e.code || 'SYS',
      title: e.title,
      text: e.detail || '',
      ai: fixed ? '已自愈。' : '低风险，可自动入账对齐。',
      action: fixed ? 'self' : 'approve',
    }
  }
  return {
    id: e.id,
    tag: 'R1 - 建议复核',
    tagCls: 'bg-[#fbc02d] text-black',
    bar: 'bg-[#fbc02d]',
    badgeCls: 'bg-[#fbc02d]/50 bg-[#fff9c4]/20',
    ref: e.code || `#${e.id}`,
    title: e.title,
    text: e.detail || '',
    ai: fixed ? '已修复。' : 'AI 建议补账并与传感器/渠道数据对齐。',
    action: fixed ? 'self' : 'approve',
  }
}

async function load() {
  try {
    const data = await api.listAuditExceptions(hotelStore.hotelId)
    issues.value = (data || []).map(mapException)
    if (data?.length) {
      const open = data.filter((x: any) => x.status === 'open').length
      progress.value = Math.max(40, Math.round(100 - (open / Math.max(data.length, 1)) * 60))
    } else {
      progress.value = 100
    }
  } catch {
    issues.value = []
  }
}

async function fixIssue(issue: Issue) {
  if (!issue.id) {
    issue.action = 'self'
    return
  }
  try {
    await api.fixAuditException(issue.id)
    await load()
  } catch {
    issue.action = 'self'
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page" :class="{ 'is-embedded': props.embedded }">
    <div class="mb-6 flex flex-col sm:flex-row sm:justify-between sm:items-end gap-4">
      <div v-if="!props.embedded">
        <h1 class="font-display-lg text-display-lg text-on-surface">{{ t('夜审自动修复') }}</h1>
        <p class="text-on-surface-variant font-body-md mt-1">
          {{ t('AI 驱动的异常检测与自愈进度。') }}
        </p>
      </div>
      <div v-else class="flex-1">
        <p class="text-on-surface-variant font-body-md">{{ t('AI 驱动的异常检测与自愈进度。') }}</p>
      </div>
      <div class="flex flex-wrap gap-3 justify-end">
        <button
          type="button"
          class="px-4 py-2 rounded-lg border border-outline-variant font-label-lg text-on-surface hover:bg-surface-container-low"
          @click="router.push('/c9-finance/night-audit')"
        >
          {{ t('返回夜间审计') }}
        </button>
        <button
          type="button"
          class="bg-primary text-on-primary px-6 py-3 rounded-full font-label-lg hover:bg-surface-tint shadow-sm flex items-center gap-2 transition-transform active:scale-95"
        >
          <span class="material-symbols-outlined">auto_fix_high</span> {{ t('一键批量修复') }}
        </button>
      </div>
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
      <div class="lg:col-span-4 flex flex-col gap-gutter">
        <div
          class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm flex flex-col items-center text-center"
        >
          <div class="relative w-32 h-32 mb-4 flex items-center justify-center">
            <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <path
                class="text-surface-container-high"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
              />
              <path
                class="text-primary"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                :stroke-dasharray="`${progress}, 100`"
                stroke-width="3"
              />
            </svg>
            <div class="absolute flex flex-col items-center">
              <span class="font-display-lg text-on-surface">{{ progress }}%</span>
            </div>
          </div>
          <h3 class="font-headline-md text-on-surface mb-1">{{ t('夜审进行中') }}</h3>
          <p
            class="text-error font-label-lg flex items-center gap-1 bg-error-container text-on-error-container px-3 py-1 rounded-full mt-2"
          >
            <span class="material-symbols-outlined text-sm">warning</span>
            {{ t('发现') }} {{ issues.filter((i) => i.action !== 'self').length }} {{ t('个异常') }}
          </p>
          <button
            type="button"
            class="mt-4 text-sm font-bold text-primary hover:underline"
            @click="router.push('/c9-finance/night-audit')"
          >
            {{ t('返回夜间审计 →') }}
          </button>
        </div>
        <div
          class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant shadow-sm ai-tinge relative overflow-hidden"
        >
          <div class="absolute top-0 right-0 p-4 opacity-10">
            <span class="material-symbols-outlined text-6xl text-tertiary">analytics</span>
          </div>
          <h3 class="font-headline-sm text-on-surface mb-4 flex items-center gap-2">
            <span class="material-symbols-outlined text-tertiary">eco</span>
            {{ t('AI 财务影响分析') }}
          </h3>
          <div class="space-y-4">
            <div>
              <p class="text-on-surface-variant text-sm mb-1">{{ t('预计节省人工工时') }}</p>
              <p class="font-num-xl text-primary">
                1.5 <span class="text-sm font-normal text-on-surface-variant">{{ t('小时') }}</span>
              </p>
            </div>
            <div class="h-px w-full bg-outline-variant/50"></div>
            <div>
              <p class="text-on-surface-variant text-sm mb-1">{{ t('修复精准度评估') }}</p>
              <p class="font-num-xl text-tertiary-container">99.8%</p>
            </div>
          </div>
        </div>
      </div>
      <div
        class="lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col"
      >
        <div
          class="p-6 border-b border-outline-variant bg-surface flex justify-between items-center"
        >
          <h3 class="font-headline-md text-on-surface">{{ t('异常检测列表') }}</h3>
          <span class="text-on-surface-variant text-sm flex items-center gap-1"
            ><span class="material-symbols-outlined text-sm">filter_list</span>
            {{ t('过滤') }}</span
          >
        </div>
        <div class="p-6 space-y-6 flex-1 bg-background">
          <div
            v-for="(it, i) in issues"
            :key="it.id || i"
            class="border rounded-lg p-5 flex flex-col md:flex-row gap-4 relative"
            :class="it.badgeCls"
          >
            <div class="absolute left-0 top-0 bottom-0 w-1 rounded-l-lg" :class="it.bar"></div>
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-2">
                <span class="px-2 py-0.5 rounded text-xs font-bold" :class="it.tagCls">{{
                  it.tag
                }}</span>
                <span class="font-num-md bg-surface-container px-2 py-1 rounded text-on-surface">{{
                  it.ref
                }}</span>
              </div>
              <h4 class="font-headline-sm text-on-surface font-semibold mb-1">{{ it.title }}</h4>
              <p class="text-on-surface-variant text-sm mb-3">{{ it.text }}</p>
              <div
                class="bg-surface-container-low rounded p-3 border border-outline-variant/50 ai-tinge"
              >
                <p class="text-tertiary text-sm font-medium flex items-center gap-1 mb-1">
                  <span class="material-symbols-outlined text-sm">smart_toy</span>
                  {{ t('AI 建议') }}
                </p>
                <p class="text-on-surface text-sm">{{ it.ai }}</p>
              </div>
            </div>
            <div
              class="flex items-end md:items-center justify-end md:justify-center w-full md:w-auto"
              :class="it.action === 'fix' ? 'flex-col gap-2' : ''"
            >
              <button
                v-if="it.action === 'approve'"
                class="border border-outline text-on-surface px-4 py-2 rounded-full font-label-lg hover:bg-surface-container transition-colors flex items-center gap-2"
                @click="fixIssue(it)"
              >
                <span class="material-symbols-outlined text-sm">check</span> {{ t('批准') }}
              </button>
              <template v-else-if="it.action === 'fix'">
                <label
                  class="flex items-center gap-2 text-sm text-on-surface-variant cursor-pointer"
                  ><input
                    class="rounded text-primary focus:ring-primary border-outline"
                    type="checkbox"
                  />
                  {{ t('确认风险') }}</label
                >
                <button
                  class="bg-surface-container-high text-on-surface px-4 py-2 rounded-full font-label-lg hover:bg-surface-container-highest transition-colors flex items-center gap-2 disabled:opacity-50"
                  @click="fixIssue(it)"
                >
                  <span class="material-symbols-outlined text-sm">build</span> {{ t('修复') }}
                </button>
              </template>
              <span
                v-else
                class="text-primary font-label-lg flex items-center gap-1 bg-primary-container px-3 py-1 rounded-full"
              >
                <span class="material-symbols-outlined text-sm">check_circle</span
                >{{ t('已自愈') }}</span
              >
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
