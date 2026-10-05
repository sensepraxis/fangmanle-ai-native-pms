<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import TagDomainSubnav from '../../components/TagDomainSubnav.vue'

const router = useRouter()
const SEGMENT_NAME = t('NL查询·亲子高层回头客')
const FILTER_RULE = 'family AND repeat AND ltv>2000'
const rows = ref<any[]>([])
const guests = ref<any[]>([])
const saving = ref(false)
const matchCount = ref(0)
const nlQuery = ref(t('找去年住过三次以上、喜欢高层且带孩子的回头客'))
const analyzing = ref(false)

onMounted(async () => {
  const [demo, gs] = await Promise.all([
    api.demo('semantic-history').catch(() => []),
    api.listGuests(hotelStore.hotelId).catch(() => []),
  ])
  rows.value = demo || []
  guests.value = gs || []
  matchCount.value = matchNlGuests(guests.value).length
})

function matchNlGuests(gs: any[]) {
  return gs.filter((g) => {
    const ltv = Number(g.ltv || g.spend || 0)
    const tags = (g.tags || []).map((t: string) => String(t))
    const family = tags.some((t) => /亲子|家庭|儿童|小孩/.test(t))
    const repeat = tags.some((t) => /常客|回头|复购/.test(t)) || ltv >= 2000
    return ltv >= 1500 && family && repeat
  })
}

const matchedGuests = computed(() => matchNlGuests(guests.value))

function runAnalyze() {
  analyzing.value = true
  matchCount.value = matchNlGuests(guests.value).length
  setTimeout(() => {
    analyzing.value = false
  }, 400)
}

function viewInDirectory() {
  router.push({ path: '/b-data/global-guest-directory', query: { segment: SEGMENT_NAME } })
}

async function saveAsSegment() {
  if (saving.value) return
  saving.value = true
  try {
    const ids = matchedGuests.value.map((g) => g.id)
    const res = await api.createSegment(hotelStore.hotelId, {
      name: SEGMENT_NAME,
      filter_rule: FILTER_RULE,
      guest_ids: ids,
    })
    const n = res?.member_count ?? ids.length
    if (confirm(`已保存分群「${SEGMENT_NAME}」，覆盖 ${n} 人。是否前往客群列表？`)) {
      router.push('/b-data/cohort-list')
    }
  } catch (e: any) {
    alert(e?.message || '保存分群失败')
  } finally {
    saving.value = false
  }
}

function goCampaign() {
  router.push('/acquisition')
}
</script>

<template>
  <div class="page">
    <TagDomainSubnav />
    <div class="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-background mb-2">{{ t('客群查询') }}</h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          {{ t('基于自然语言的深度客群挖掘与智能分群') }}
        </p>
      </div>
      <div
        class="flex items-center gap-2 text-tertiary bg-tertiary-fixed/30 px-4 py-2 rounded-full border border-tertiary-fixed"
      >
        <span class="material-symbols-outlined text-sm">auto_awesome</span>
        <span class="font-label-lg text-label-lg">Powered by pgvector AI Retrieval</span>
      </div>
    </div>
    <div
      class="bg-surface-container-lowest rounded-xl p-8 mb-8 border border-outline-variant relative overflow-hidden group"
    >
      <div class="absolute top-0 left-0 w-1 h-full bg-tertiary opacity-80"></div>
      <div class="relative z-10 max-w-3xl mx-auto">
        <div class="relative">
          <span
            class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-tertiary text-2xl"
            >search</span
          >
          <input
            v-model="nlQuery"
            class="hero-search w-full pl-14 pr-32 py-5 bg-surface rounded-full border-2 border-outline-variant focus:border-tertiary focus:ring-4 focus:ring-tertiary-fixed transition-all font-body-lg text-body-lg text-on-background shadow-sm placeholder:text-on-surface-variant/60"
            :placeholder="t('描述你想寻找的客群特征...')"
            type="text"
          />
          <button
            type="button"
            class="absolute right-3 top-1/2 -translate-y-1/2 bg-tertiary text-on-tertiary px-6 py-2 rounded-full font-label-lg text-label-lg hover:bg-tertiary/90 transition-colors shadow-md flex items-center gap-2"
            :disabled="analyzing"
            @click="runAnalyze"
          >
            {{ analyzing ? t('分析中…') : t('分析') }}
            <span class="material-symbols-outlined text-sm">arrow_forward</span>
          </button>
        </div>
        <div class="mt-4 flex flex-wrap gap-2 justify-center">
          <span class="text-on-surface-variant font-label-lg text-label-lg mr-2 mt-1">{{
            t('AI 推荐查询:')
          }}</span>
          <button
            type="button"
            class="px-3 py-1 bg-surface-container rounded-full text-on-surface-variant font-label-lg text-label-lg hover:bg-surface-container-highest transition-colors border border-outline-variant/50"
          >
            {{ t('近三个月取消过订单的商务客') }}
          </button>
          <button
            type="button"
            class="px-3 py-1 bg-surface-container rounded-full text-on-surface-variant font-label-lg text-label-lg hover:bg-surface-container-highest transition-colors border border-outline-variant/50"
          >
            {{ t('周末入住倾向且评价提及"安静"的客人') }}
          </button>
        </div>
      </div>
      <div
        class="absolute -right-20 -bottom-20 w-64 h-64 bg-tertiary-fixed rounded-full blur-3xl opacity-20 pointer-events-none"
      ></div>
    </div>
    <div class="mb-6 flex flex-wrap gap-2 items-center">
      <button
        type="button"
        class="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm font-semibold"
        @click="viewInDirectory"
      >
        {{ t('在全景列表查看成员') }}
      </button>
      <button
        type="button"
        class="px-4 py-2 rounded-lg border border-outline-variant text-sm font-semibold hover:bg-surface-container-low disabled:opacity-50"
        :disabled="saving"
        @click="saveAsSegment"
      >
        {{
          saving
            ? t('保存中…')
            : t('保存为分群（{n} 人）', { n: matchCount || matchedGuests.length })
        }}
      </button>
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
      <div class="lg:col-span-3 flex flex-col gap-gutter">
        <div class="bg-surface-container-lowest rounded-xl p-6 border border-outline-variant">
          <h3 class="font-headline-md text-headline-md text-on-background mb-4">
            {{ t('分析洞察') }}
          </h3>
          <div class="space-y-4">
            <div>
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('匹配客群规模') }}
              </p>
              <p class="font-num-xl text-num-xl text-primary flex items-baseline gap-1">
                {{ matchCount || matchedGuests.length || '—' }}
                <span class="font-body-md text-body-md text-on-surface-variant">{{ t('人') }}</span>
              </p>
            </div>
            <div class="h-px bg-outline-variant/50 w-full"></div>
            <div>
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                {{ t('预计转化率提升') }}
              </p>
              <p class="font-num-xl text-num-xl text-tertiary flex items-baseline gap-1">
                +12.5%
                <span class="material-symbols-outlined text-sm text-tertiary">trending_up</span>
              </p>
            </div>
          </div>
        </div>
        <div
          class="bg-primary-container text-on-primary-container rounded-xl p-6 shadow-md relative overflow-hidden"
        >
          <div class="relative z-10">
            <h3 class="font-headline-md text-headline-md mb-2">{{ t('一键营销') }}</h3>
            <p class="font-body-md text-body-md mb-6 opacity-90">
              {{ t('为匹配客户发送专属「亲子高层」周末特惠套餐。') }}
            </p>
            <button
              type="button"
              class="w-full bg-on-primary text-primary font-headline-md text-headline-md py-3 rounded-lg hover:bg-white/90 transition-colors shadow-sm flex items-center justify-center gap-2"
              @click="goCampaign"
            >
              {{ t('创建营销活动') }}
              <span class="material-symbols-outlined">campaign</span>
            </button>
          </div>
          <span
            class="material-symbols-outlined absolute -right-4 -bottom-4 text-[120px] opacity-10 pointer-events-none"
            >mark_email_read</span
          >
        </div>
      </div>
      <div
        class="lg:col-span-9 bg-surface-container-lowest rounded-xl border border-outline-variant overflow-hidden flex flex-col"
      >
        <div
          class="px-6 py-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low/50"
        >
          <h2 class="font-headline-md text-headline-md text-on-background flex items-center gap-2">
            {{ t('高匹配度客户列表') }}
            <span
              class="px-2 py-0.5 bg-surface-variant text-on-surface-variant rounded-full text-xs font-num-md"
              >Top {{ Math.min(matchedGuests.length, 50) || 50 }}</span
            >
          </h2>
        </div>
        <div class="flex-1 overflow-auto p-6 space-y-4">
          <div v-if="!matchedGuests.length" class="text-on-surface-variant text-sm">
            {{ t('暂无匹配客人，可先保存分群规则或调整筛选条件。') }}
          </div>
          <div
            v-for="g in matchedGuests.slice(0, 50)"
            :key="g.id"
            class="flex items-start gap-4 p-4 rounded-xl border border-outline-variant hover:bg-surface-container-low transition-colors cursor-pointer"
            @click="router.push(`/guests/${g.id}`)"
          >
            <div
              class="w-12 h-12 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-headline-md flex-shrink-0"
            >
              {{ String(g.name || '?').slice(0, 1) }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-baseline gap-3 mb-1 flex-wrap">
                <h4 class="font-headline-md text-headline-md text-on-background">{{ g.name }}</h4>
                <span class="font-num-md text-num-md text-on-surface-variant text-sm"
                  >LTV ¥{{ Number(g.ltv || g.spend || 0).toLocaleString('zh-CN') }}</span
                >
              </div>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="tag in (g.tags || []).slice(0, 4)"
                  :key="tag"
                  class="px-2 py-1 bg-surface-variant text-on-surface-variant rounded text-xs"
                  >{{ tag }}</span
                >
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-glow {
  box-shadow: 0 0 15px rgba(140, 51, 179, 0.15);
}
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
</style>
