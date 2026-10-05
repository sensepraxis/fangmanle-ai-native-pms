<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t, getLocale } from '../../lib/i18n'

/**
 * 客户资源全景列表 —— 忠实还原原型 global-guest-directory.html 内容区
 * 数据：GET /api/guests（guests + guest_identities + guest_tags + orders）
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { VIP_CN } from '../../lib/ui'
import { explainSegmentRule, type RuleExplain } from '../../lib/segmentRule'
import CrmTaskDrawer from '../../components/CrmTaskDrawer.vue'

const route = useRoute()
const router = useRouter()

const rows = ref<any[]>([])
const tagDefs = ref<any[]>([])
const cohortN = ref(0)
const segmentGuestIds = ref<number[] | null>(null)
const segmentMemberCount = ref(0)
const segmentRuleRaw = ref('')
const segmentResolvedName = ref('')
/** 后端 rule_to_sql 编译结果（优先于前端本地编译） */
const segmentSqlFromApi = ref(')')
const segmentMeaningFromApi = ref('')
const segmentBulletsFromApi = ref<string[]>([])
const segmentSourceFromApi = ref('')
const q = ref('')
const loading = ref(true)
const pageSize = ref(10)
const page = ref(1)
const segVip = ref(false)
const segCorp = ref(false)
const segLeisure = ref(false)
const activeTag = ref('')
const sourceFilter = ref('')
const selectedIds = ref<number[]>([])
const taskOpen = ref(false)

const segmentQ = computed(() =>
  typeof route.query.segment === 'string' ? route.query.segment : '',
)
const segmentIdQ = computed(() => {
  const v = route.query.segment_id
  if (typeof v === 'string' && v) return Number(v)
  return NaN
})
const ruleQ = computed(() => (typeof route.query.rule === 'string' ? route.query.rule : ''))
const filterQ = computed(() => (typeof route.query.filter === 'string' ? route.query.filter : ''))
const arrivalDateQ = computed(() =>
  typeof route.query.arrival === 'string' ? route.query.arrival : '',
)
const tagQ = computed(() => (typeof route.query.tag === 'string' ? route.query.tag : ''))
const segmentMode = computed(() => !!segmentQ.value)
const banner = computed(() => {
  if (segmentQ.value) return segmentQ.value
  if (tagQ.value) return t('标签：{tag}', { tag: tagQ.value })
  if (arrivalDateQ.value) return t('到店日 {date}', { date: fmtBannerDate(arrivalDateQ.value) })
  return filterQ.value
})
const todayMode = computed(() => filterQ.value.includes('今日到店') || !!arrivalDateQ.value)

const ruleExplain = computed<RuleExplain>(() => {
  const local = explainSegmentRule(
    segmentRuleRaw.value || ruleQ.value,
    segmentResolvedName.value || segmentQ.value,
  )
  if (segmentSqlFromApi.value) {
    return {
      ...local,
      source: (segmentSourceFromApi.value as RuleExplain['source']) || local.source,
      sourceLabel: t('过滤条件（SQL）'),
      expression: segmentSqlFromApi.value,
      sql: segmentSqlFromApi.value,
      meaning: segmentMeaningFromApi.value || local.meaning,
      bullets: segmentBulletsFromApi.value.length ? segmentBulletsFromApi.value : local.bullets,
    }
  }
  return { ...local, sourceLabel: t('过滤条件（SQL）') }
})

const arrivalCalendar = ref<any[]>([])
const activeArrival = ref('')

function fmtBannerDate(iso: string) {
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return iso
  if (getLocale() === 'en') return `${Number(m[2])}/${Number(m[3])}`
  return t('{m}月{d}日', { m: Number(m[2]), d: Number(m[3]) })
}

function todayIso() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const WEEKDAY = ['日', '一', '二', '三', '四', '五', '六']
function calLabel(iso: string, weekday?: number) {
  const m = String(iso || '').match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return iso
  const label = `${m[1]}/${Number(m[2])}/${Number(m[3])}`
  if (weekday == null) return label
  if (getLocale() === 'en') {
    const en = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    return `${label} ${en[weekday] || ''}`
  }
  return `${label} ${t('周{w}', { w: WEEKDAY[weekday] })}`
}

const VIP_SET = new Set([
  'silver',
  'gold',
  'platinum',
  'diamond',
  t('银卡'),
  t('金卡'),
  t('白金'),
  t('钻石'),
  'vip',
])

const VIP_PILL: Record<string, string> = {
  platinum: 'vip-pill vip-platinum',
  gold: 'vip-pill vip-gold',
  silver: 'vip-pill vip-silver',
  normal: 'vip-pill vip-normal',
  diamond: 'vip-pill vip-platinum',
}

const HIGH_LTV = 5000

const kpis = computed(() => {
  const n = rows.value.length
  const vip = rows.value.filter((g) => {
    const v = String(g.vip_level || '')
    return VIP_SET.has(v.toLowerCase()) || VIP_SET.has(v)
  }).length
  return { total: n, vip, cohort: cohortN.value }
})

async function loadSegmentMembers() {
  const name = segmentQ.value
  if (!name) {
    segmentGuestIds.value = null
    segmentMemberCount.value = 0
    segmentRuleRaw.value = ''
    segmentResolvedName.value = ''
    segmentSqlFromApi.value = ''
    segmentMeaningFromApi.value = ''
    segmentBulletsFromApi.value = []
    segmentSourceFromApi.value = ''
    return
  }
  try {
    const segs = await api.listSegments(hotelStore.hotelId)
    let hit: any = null
    if (!Number.isNaN(segmentIdQ.value)) {
      hit = (segs || []).find((s: any) => Number(s.id) === segmentIdQ.value)
    }
    if (!hit) {
      hit = (segs || []).find((s: any) => s.name === name)
    }
    // 命中分群后一律用成员 ID 过滤；空分群应显示 0 人，不能退回「全量列表」
    const ids = hit ? hit.guest_ids || [] : []
    segmentGuestIds.value = hit ? ids : []
    segmentMemberCount.value = hit ? Number(hit.member_count ?? ids.length) : 0
    segmentResolvedName.value = hit?.name || name
    // 优先用库里的规则；URL rule 作展示兜底（消除「只有名字没有条件」）
    segmentRuleRaw.value = String(hit?.filter_rule || hit?.rule || ruleQ.value || '')
    segmentSqlFromApi.value = String(hit?.sql || '')
    segmentMeaningFromApi.value = String(hit?.rule_meaning || '')
    segmentBulletsFromApi.value = Array.isArray(hit?.rule_bullets)
      ? hit.rule_bullets.map(String)
      : []
    segmentSourceFromApi.value = String(hit?.rule_source || '')
  } catch {
    segmentGuestIds.value = []
    segmentMemberCount.value = 0
    segmentRuleRaw.value = ruleQ.value || ''
    segmentResolvedName.value = name
    segmentSqlFromApi.value = ''
    segmentMeaningFromApi.value = ''
    segmentBulletsFromApi.value = []
    segmentSourceFromApi.value = ''
  }
}

async function loadCalendar() {
  try {
    arrivalCalendar.value = (await api.guestArrivalCalendar(hotelStore.hotelId, 7)) || []
  } catch {
    arrivalCalendar.value = []
  }
}

async function load() {
  loading.value = true
  try {
    const [gs, tags, segs] = await Promise.all([
      api.listGuests(hotelStore.hotelId),
      api.listTags().catch(() => []),
      api.listSegments(hotelStore.hotelId).catch(() => []),
    ])
    rows.value = gs || []
    tagDefs.value = tags || []
    cohortN.value = (segs || []).length
    await loadCalendar()
  } catch {
    rows.value = []
    cohortN.value = 0
  } finally {
    loading.value = false
  }
  syncArrivalFromRoute()
  await loadSegmentMembers()
}

function syncArrivalFromRoute() {
  if (arrivalDateQ.value) {
    activeArrival.value = arrivalDateQ.value.slice(0, 10)
  } else if (filterQ.value.includes('今日到店')) {
    activeArrival.value = todayIso()
  } else {
    activeArrival.value = ''
  }
}
onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(segmentQ, loadSegmentMembers)
watch(segmentIdQ, loadSegmentMembers)
watch(
  () => route.query,
  () => {
    syncArrivalFromRoute()
    if (segmentQ.value) return
    if (tagQ.value) {
      activeTag.value = tagQ.value
      return
    }
    if (filterQ.value.includes('VIP')) segVip.value = true
    if (filterQ.value.includes('高流失') || filterQ.value.includes('高风险'))
      activeTag.value = '高风险'
    if (filterQ.value.includes('高LTV') || filterQ.value.includes('高 LTV'))
      activeTag.value = '高 LTV'
  },
  { immediate: true },
)

/** 仅分群成员（未做二次筛选） */
const segmentBaseRows = computed(() => {
  if (segmentGuestIds.value === null) return rows.value
  const idSet = new Set(segmentGuestIds.value)
  return rows.value.filter((g) => idSet.has(g.id))
})

const filtered = computed(() => {
  let list = segmentMode.value ? [...segmentBaseRows.value] : [...rows.value]
  const text = q.value.trim()
  if (text) {
    list = list.filter(
      (g) =>
        String(g.name || '').includes(text) ||
        String(g.phone || '').includes(text) ||
        String(g.one_id || '').includes(text),
    )
  }
  if (segVip.value) {
    list = list.filter((g) => !['', 'normal', '普通'].includes(String(g.vip_level || 'normal')))
  }
  if (activeTag.value === '高 LTV' || activeTag.value === t('高 LTV')) {
    list = list.filter(
      (g) =>
        Number(g.ltv || g.spend || 0) >= 5000 ||
        (g.tags || []).some((tg: string) => /高|High|LTV|value/i.test(String(tg))),
    )
  } else if (activeTag.value === '高风险' || activeTag.value === t('高风险')) {
    list = list.filter(
      (g) =>
        Number(g.churn_risk || 0) >= 0.5 ||
        (g.tags || []).some((tg: string) => /风险|投诉|risk|complaint/i.test(String(tg))),
    )
  } else if (activeTag.value === '常客' || activeTag.value === t('常客')) {
    list = list.filter(
      (g) =>
        (g.tags || []).some((tg: string) => /常客|回头|repeat|loyal/i.test(String(tg))) ||
        Number(g.ltv || 0) > 2000,
    )
  } else if (activeTag.value) {
    list = list.filter((g) => (g.tags || []).includes(activeTag.value))
  }
  if (sourceFilter.value) {
    const key = sourceFilter.value
    const keyEn = t(key)
    list = list.filter((g) => {
      const s = String(g.sources || '')
      return s.includes(key) || (keyEn !== key && s.includes(keyEn))
    })
  }
  if (!segmentMode.value && segmentQ.value.includes('本月新客')) {
    const now = new Date()
    list = list.filter((g) => {
      const d = g.created_at || g.last_visit
      if (!d) return true
      const dt = new Date(d)
      return dt.getMonth() === now.getMonth() && dt.getFullYear() === now.getFullYear()
    })
  }
  if (filterQ.value.includes('今日到店') || activeArrival.value) {
    const target = activeArrival.value || todayIso()
    const today = todayIso()
    list = list.filter((g) => {
      const arr = String(g.arrival_date || g.today_stay?.check_in || '').slice(0, 10)
      if (arr === target) return true
      if (target === today && g.in_stay) return true
      return false
    })
    list.sort((a, b) => {
      const score = (g: any) => (g.arriving_today ? 2 : 0) + (g.in_stay ? 1 : 0)
      return score(b) - score(a)
    })
  }
  return list
})

const segmentPoolN = computed(() =>
  segmentMode.value ? segmentBaseRows.value.length : rows.value.length,
)
const hasSecondaryFilter = computed(
  () =>
    !!(
      q.value.trim() ||
      segVip.value ||
      segCorp.value ||
      segLeisure.value ||
      activeTag.value ||
      sourceFilter.value
    ),
)

const total = computed(() => filtered.value.length)
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

watch(filtered, () => {
  page.value = 1
})

function maskPhone(p?: string) {
  const s = String(p || '').replace(/\D/g, '')
  if (s.length >= 7) return `+86 ${s.slice(0, 3)} **** ${s.slice(-4)}`
  return p || '—'
}

function vipLabel(v?: string) {
  return VIP_CN[v || ''] || VIP_CN[(v || '').toLowerCase()] || v || t('普通')
}

function vipClass(v?: string) {
  return VIP_PILL[(v || 'normal').toLowerCase()] || VIP_PILL.normal
}

function fmtMoney(n: number) {
  return `¥${Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function fmtDate(d?: string) {
  if (!d) return '—'
  const s = String(d).slice(0, 10)
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return s
  const date = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  if (getLocale() === 'en') {
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
  }
  return t('{y}年{m}月{d}日', { y: m[1], m: Number(m[2]), d: Number(m[3]) })
}

function initial(name?: string, city?: string) {
  if (city) return String(city).slice(0, 2)
  return String(name || '?').slice(0, 1)
}

function openGuest360(g: any) {
  if (g?.id) router.push(`/guests/${g.id}`)
}

const todayArrivalN = computed(() => {
  const t = todayIso()
  return rows.value.filter((g) => {
    const arr = String(g.arrival_date || g.today_stay?.check_in || '').slice(0, 10)
    return arr === t || (g.arriving_today && arr === t) || g.in_stay
  }).length
})

function applyPreset(kind: 'today' | 'vip' | 'churn') {
  if (kind === 'today') {
    segVip.value = false
    activeTag.value = ''
    const iso = todayIso()
    activeArrival.value = iso
    router.push({
      path: '/b-data/global-guest-directory',
      query: { filter: '今日到店', arrival: iso },
    })
    return
  }
  if (kind === 'vip') {
    segVip.value = true
    activeTag.value = ''
    router.push({ path: '/b-data/global-guest-directory' })
    return
  }
  activeTag.value = '高风险'
  router.push({ path: '/b-data/global-guest-directory', query: { segment: '高流失风险' } })
}

function isHighValue(g: any) {
  return Number(g.spend ?? g.ltv ?? 0) >= HIGH_LTV
}
function isChurnRisk(g: any) {
  return Number(g.churn_risk || 0) >= 0.45
}

function go(path: string) {
  if (!path) return
  router.push(path)
}

const allPageSelected = computed(
  () => pageRows.value.length > 0 && pageRows.value.every((g) => selectedIds.value.includes(g.id)),
)

function toggleAllPage() {
  if (allPageSelected.value) {
    const pageSet = new Set(pageRows.value.map((g) => g.id))
    selectedIds.value = selectedIds.value.filter((id) => !pageSet.has(id))
  } else {
    const merged = new Set([...selectedIds.value, ...pageRows.value.map((g) => g.id)])
    selectedIds.value = [...merged]
  }
}

function toggleRow(id: number) {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter((x) => x !== id)
  } else {
    selectedIds.value = [...selectedIds.value, id]
  }
}

function openBatchTask() {
  if (!selectedIds.value.length) return
  taskOpen.value = true
}

function clearBanner() {
  activeArrival.value = ''
  segVip.value = false
  activeTag.value = ''
  sourceFilter.value = ''
  q.value = ''
  router.push('/b-data/global-guest-directory')
}

function clearSecondaryOnly() {
  q.value = ''
  segVip.value = false
  segCorp.value = false
  segLeisure.value = false
  activeTag.value = ''
  sourceFilter.value = ''
}

function goCohort() {
  router.push('/b-data/cohort-list')
}

function pickArrivalDay(iso: string) {
  activeArrival.value = iso
  router.push({
    path: '/b-data/global-guest-directory',
    query: { filter: '今日到店', arrival: iso },
  })
}

function toggleTag(name: string) {
  activeTag.value = activeTag.value === name ? '' : name
}

function setSource(name: string) {
  sourceFilter.value = sourceFilter.value === name ? '' : name
}

const sidebarTags = computed(() => {
  const fromDb = (tagDefs.value || []).map((t: any) => String(t.name || '')).filter(Boolean)
  if (fromDb.length) return [...new Set(fromDb)].slice(0, 12)
  return [t('常客'), t('高消费'), t('投诉过'), t('家庭'), t('高 LTV'), t('高风险'), t('常旅客')]
})

function goTagManagement() {
  router.push('/b-data/tag-management')
}
</script>

<template>
  <div class="page ggd">
    <section v-if="segmentMode" class="seg-ctx">
      <div class="seg-ctx-top">
        <button type="button" class="ctx-back" @click="goCohort">
          <span class="material-symbols-outlined">arrow_back</span>
          {{ t('回客群运营') }}
        </button>
        <span class="ctx-mode">{{ t('分群成员模式') }}</span>
        <span class="ctx-scope">{{ t('下方只显示本分群已保存成员，不是全店客人') }}</span>
      </div>
      <div class="seg-ctx-grid">
        <div class="ctx-block">
          <div class="ctx-k">{{ t('当前分群') }}</div>
          <div class="ctx-v name">{{ segmentResolvedName || segmentQ }}</div>
          <div class="ctx-meta">
            {{ t('已保存 {n} 人', { n: segmentPoolN })
            }}<template v-if="hasSecondaryFilter">
              · {{ t('二次筛选后 {n} 人', { n: total }) }}</template
            >
          </div>
        </div>
        <div class="ctx-block grow">
          <div class="ctx-k">{{ t('过滤条件（SQL）') }}</div>
          <pre class="ctx-expr">{{ ruleExplain.sql || ruleExplain.expression }}</pre>
        </div>
        <div class="ctx-block grow">
          <div class="ctx-k">{{ t('语义解读') }}</div>
          <p class="ctx-meaning">{{ ruleExplain.meaning }}</p>
          <ul v-if="ruleExplain.bullets.length" class="ctx-bullets">
            <li v-for="b in ruleExplain.bullets" :key="b">{{ b }}</li>
          </ul>
        </div>
      </div>
      <div class="seg-ctx-actions">
        <button type="button" class="ctx-btn ghost" @click="clearBanner">
          {{ t('退出分群，看全店客人') }}
        </button>
        <button v-if="hasSecondaryFilter" type="button" class="ctx-btn" @click="clearSecondaryOnly">
          {{ t('清除二次筛选') }}
        </button>
      </div>
    </section>

    <div
      v-else-if="banner"
      class="mb-4 flex items-center justify-between gap-3 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3"
    >
      <div class="text-sm text-on-surface">
        <template v-if="arrivalDateQ || filterQ.includes('今日到店')">
          {{ t('到店日历筛选：') }}
          <strong>{{ fmtBannerDate(activeArrival || todayIso()) }}</strong>
          <span class="text-on-surface-variant"> · {{ t('共 {n} 位', { n: total }) }}</span>
        </template>
        <template v-else-if="tagQ || activeTag"
          >{{ t('标签筛选：') }} <strong>{{ t(String(tagQ || activeTag)) }}</strong>
          <span class="text-on-surface-variant"> · {{ t('共 {n} 位', { n: total }) }}</span>
        </template>
        <template v-else
          >{{ t('预设筛选：') }} <strong>{{ t(String(filterQ)) }}</strong></template
        >
      </div>
      <button
        type="button"
        class="text-sm font-semibold text-primary hover:underline"
        @click="clearBanner"
      >
        {{ t('清除') }}
      </button>
    </div>

    <header class="page-head shrink-0">
      <div>
        <h1 class="text-headline-lg font-headline-lg text-on-background">{{ t('客户总览') }}</h1>
      </div>
      <button type="button" class="oneid-link" @click="go('/b-data/one-id')">
        <span class="material-symbols-outlined">fingerprint</span>
        {{ t('OneID归并台') }}
      </button>
    </header>

    <!-- 分群模式下隐藏首页三卡，避免「这是全店入口还是分群」混淆 -->
    <section v-if="!segmentMode" class="home-entries shrink-0">
      <button type="button" class="entry" @click="applyPreset('today')">
        <span class="entry-ico material-symbols-outlined">today</span>
        <div class="entry-body">
          <strong>{{ t('查今日客人') }}</strong>
          <span>{{
            loading ? '—' : t('今日到店 {n} 位 · 与订单日历联动', { n: todayArrivalN })
          }}</span>
        </div>
      </button>
      <button type="button" class="entry" @click="go('/b-data/cohort-list')">
        <span class="entry-ico material-symbols-outlined">filter_alt</span>
        <div class="entry-body">
          <strong>{{ t('客群运营') }}</strong>
          <span>{{ loading ? '—' : t('{n} 个活跃分群 · 召回与营销', { n: kpis.cohort }) }}</span>
        </div>
      </button>
      <button type="button" class="entry" @click="go('/b-data/one-id')">
        <span class="entry-ico material-symbols-outlined">fingerprint</span>
        <div class="entry-body">
          <strong>{{ t('OneID归并台') }}</strong>
          <span>{{ t('跨渠道身份归并 · 冲突复核') }}</span>
        </div>
      </button>
    </section>

    <section v-if="todayMode && arrivalCalendar.length" class="arrival-cal shrink-0">
      <div class="cal-head">
        <span class="material-symbols-outlined">calendar_month</span>
        {{ t('到店日历（按订单入住日）') }}
      </div>
      <div class="cal-days">
        <button
          v-for="d in arrivalCalendar"
          :key="d.date"
          type="button"
          class="cal-day"
          :class="{ on: activeArrival === d.date, today: d.is_today }"
          @click="pickArrivalDay(d.date)"
        >
          <span class="cal-d">{{ calLabel(d.date, d.weekday) }}</span>
          <span class="cal-n">{{ t('{n} 到店', { n: d.arrivals }) }}</span>
        </button>
      </div>
    </section>

    <div class="flex flex-1 gap-6 min-h-0 overflow-hidden ggd-body">
      <!-- Filter Sidebar -->
      <aside
        class="w-64 bg-surface-container-lowest border border-outline-variant rounded-xl flex flex-col overflow-y-auto shrink-0"
      >
        <div
          class="p-4 border-b border-outline-variant sticky top-0 bg-surface-container-lowest z-10 flex justify-between items-center"
        >
          <h2 class="text-headline-md font-headline-md text-on-surface">
            {{ segmentMode ? t('在分群内再筛') : t('筛选条件') }}
          </h2>
          <button
            type="button"
            class="text-primary text-label-lg font-label-lg hover:underline"
            @click="segmentMode ? clearSecondaryOnly() : clearBanner()"
          >
            {{ segmentMode ? t('重置二次筛选') : t('重置') }}
          </button>
        </div>
        <p v-if="segmentMode" class="px-4 pt-3 text-[12px] leading-snug text-on-surface-variant">
          {{
            t('这些选项只在「{seg}」的 {n} 人里收窄，不会把其它客人加进来。', {
              seg: segmentResolvedName || segmentQ,
              n: segmentPoolN,
            })
          }}
        </p>
        <div class="p-4 space-y-6">
          <div class="relative">
            <span
              class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]"
              >search</span
            >
            <input
              v-model="q"
              class="w-full pl-10 pr-3 py-2 bg-surface-container-low border border-outline-variant rounded-lg text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              :placeholder="t('搜索筛选……')"
              type="text"
            />
          </div>
          <div>
            <h3 class="text-label-lg font-label-lg text-on-surface mb-3 flex items-center gap-2">
              {{ t('分群') }}
            </h3>
            <div class="space-y-2">
              <label class="flex items-center gap-2 cursor-pointer group">
                <input
                  v-model="segVip"
                  class="rounded border-outline-variant text-primary focus:ring-primary w-4 h-4 cursor-pointer"
                  type="checkbox"
                />
                <span
                  class="text-body-md font-body-md text-on-surface-variant group-hover:text-on-surface"
                  >{{ t('贵宾客户') }}</span
                >
              </label>
              <label class="flex items-center gap-2 cursor-pointer group">
                <input
                  v-model="segCorp"
                  class="rounded border-outline-variant text-primary focus:ring-primary w-4 h-4 cursor-pointer"
                  type="checkbox"
                />
                <span
                  class="text-body-md font-body-md text-on-surface-variant group-hover:text-on-surface"
                  >{{ t('企业') }}</span
                >
              </label>
              <label class="flex items-center gap-2 cursor-pointer group">
                <input
                  v-model="segLeisure"
                  class="rounded border-outline-variant text-primary focus:ring-primary w-4 h-4 cursor-pointer"
                  type="checkbox"
                />
                <span
                  class="text-body-md font-body-md text-on-surface-variant group-hover:text-on-surface"
                  >{{ t('休闲') }}</span
                >
              </label>
            </div>
          </div>
          <hr class="border-outline-variant" />
          <div>
            <div class="mb-3 flex items-center justify-between gap-2">
              <h3 class="text-label-lg font-label-lg text-on-surface m-0">{{ t('标签') }}</h3>
              <button
                type="button"
                class="text-primary text-[12px] font-semibold hover:underline"
                @click="goTagManagement"
              >
                {{ t('管理') }}
              </button>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="tag in sidebarTags"
                :key="tag"
                type="button"
                class="px-2 py-1 rounded text-label-lg font-label-lg text-xs cursor-pointer border transition-colors"
                :class="
                  activeTag === tag
                    ? 'bg-primary-container text-on-primary-container border-primary-container'
                    : tag === '高 LTV' || tag === t('高 LTV')
                      ? 'bg-tertiary-fixed text-on-tertiary-fixed-variant border-tertiary-fixed-dim hover:bg-tertiary-fixed-dim'
                      : tag === '高风险' || tag === t('高风险')
                        ? 'bg-error-container text-on-error-container border-error hover:bg-error/10'
                        : 'bg-surface-container-high text-on-surface-variant border-outline-variant hover:bg-surface-variant'
                "
                @click="toggleTag(tag)"
              >
                {{ t(tag) }}
              </button>
            </div>
          </div>
          <hr class="border-outline-variant" />
          <div>
            <h3 class="text-label-lg font-label-lg text-on-surface mb-3 flex items-center gap-2">
              {{ t('来源') }}
            </h3>
            <div class="space-y-2">
              <label class="flex items-center gap-2 cursor-pointer group">
                <input
                  :checked="sourceFilter.includes('Ctrip') || sourceFilter.includes('OTA')"
                  class="rounded border-outline-variant text-primary w-4 h-4"
                  type="checkbox"
                  @change="setSource('Ctrip')"
                />
                <span
                  class="text-body-md font-body-md text-on-surface-variant group-hover:text-on-surface"
                  >OTA (Ctrip/Booking)</span
                >
              </label>
              <label class="flex items-center gap-2 cursor-pointer group">
                <input
                  :checked="sourceFilter.includes('微信')"
                  class="rounded border-outline-variant text-primary w-4 h-4"
                  type="checkbox"
                  @change="setSource('微信')"
                />
                <span
                  class="text-body-md font-body-md text-on-surface-variant group-hover:text-on-surface"
                  >{{ t('直订（微信）') }}</span
                >
              </label>
              <label class="flex items-center gap-2 cursor-pointer group">
                <input
                  :checked="sourceFilter === '散客'"
                  class="rounded border-outline-variant text-primary w-4 h-4"
                  type="checkbox"
                  @change="setSource('散客')"
                />
                <span
                  class="text-body-md font-body-md text-on-surface-variant group-hover:text-on-surface"
                  >{{ t('散客') }}</span
                >
              </label>
            </div>
          </div>
        </div>
      </aside>

      <!-- Data Table -->
      <div
        class="flex-1 bg-surface-container-lowest border border-outline-variant rounded-xl flex flex-col overflow-hidden min-w-0"
      >
        <div
          class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-lowest flex-wrap gap-2"
        >
          <div class="flex items-center gap-3 flex-wrap">
            <div class="relative w-72 max-w-full">
              <span
                class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]"
                >search</span
              >
              <input
                v-model="q"
                class="w-full pl-10 pr-3 py-2 bg-surface-container-low border border-outline-variant rounded-lg text-body-md font-body-md focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                :placeholder="t('按姓名、电话或证件号搜索……')"
                type="text"
              />
            </div>
            <button
              v-if="selectedIds.length"
              type="button"
              class="batch-btn"
              @click="openBatchTask"
            >
              {{ t('批量运营（{n}）', { n: selectedIds.length }) }}
            </button>
          </div>
          <div class="text-body-md font-body-md text-on-surface-variant">
            <template v-if="loading">{{ t('加载中…') }}</template>
            <template v-else-if="segmentMode">
              {{ t('分群 {n} 人', { n: segmentPoolN })
              }}<template v-if="hasSecondaryFilter">
                → {{ t('当前 {n} 人', { n: total }) }}</template
              >
              ·
              {{
                t('本页 {from}–{to}', {
                  from: pageRows.length ? (page - 1) * pageSize + 1 : 0,
                  to: (page - 1) * pageSize + pageRows.length,
                })
              }}</template
            >
            <template v-else>
              {{
                t('显示 {total} 位客人中的 {from}–{to} 位', {
                  total: total.toLocaleString(),
                  from: pageRows.length ? (page - 1) * pageSize + 1 : 0,
                  to: (page - 1) * pageSize + pageRows.length,
                })
              }}
            </template>
          </div>
        </div>

        <div class="flex-1 overflow-auto">
          <table class="w-full text-left border-collapse min-w-[800px]">
            <thead class="bg-surface-container-low sticky top-0 z-10 shadow-sm">
              <tr>
                <th class="p-4 w-10 border-b border-outline-variant">
                  <input type="checkbox" :checked="allPageSelected" @change="toggleAllPage" />
                </th>
                <th
                  class="p-4 text-label-lg font-label-lg text-on-surface-variant border-b border-outline-variant font-medium"
                >
                  {{ t('客人') }}
                </th>
                <th
                  class="p-4 text-label-lg font-label-lg text-on-surface-variant border-b border-outline-variant font-medium"
                >
                  {{ t('等级') }}
                </th>
                <th
                  class="p-4 text-label-lg font-label-lg text-on-surface-variant border-b border-outline-variant font-medium"
                >
                  {{ t('来源') }}
                </th>
                <th
                  class="p-4 text-label-lg font-label-lg text-on-surface-variant border-b border-outline-variant font-medium text-right"
                >
                  {{ t('总消费') }}
                </th>
                <th
                  class="p-4 text-label-lg font-label-lg text-on-surface-variant border-b border-outline-variant font-medium"
                >
                  {{ todayMode ? t('到店信息') : t('最近到访') }}
                </th>
                <th
                  class="p-4 text-label-lg font-label-lg text-on-surface-variant border-b border-outline-variant font-medium"
                >
                  {{ t('标签') }}
                </th>
                <th
                  class="p-4 text-label-lg font-label-lg text-on-surface-variant border-b border-outline-variant font-medium text-right"
                >
                  {{ t('操作') }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant">
              <tr v-if="!loading && !pageRows.length">
                <td :colspan="8" class="p-8 text-center text-on-surface-variant">
                  <template v-if="segmentMode && !segmentPoolN">{{
                    t('该分群尚无已保存成员（不是查询失败）。可回客群运营重新分析并保存。')
                  }}</template>
                  <template v-else-if="segmentMode && hasSecondaryFilter">{{
                    t('分群内 {n} 人里，没有符合当前二次筛选的记录。可点「清除二次筛选」。', {
                      n: segmentPoolN,
                    })
                  }}</template>
                  <template v-else>{{ t('暂无匹配客人') }}</template>
                </td>
              </tr>
              <tr
                v-for="(g, i) in pageRows"
                :key="g.id"
                class="hover:bg-surface-container-lowest transition-colors group cursor-pointer"
                :class="i % 2 ? 'bg-surface-bright' : 'bg-white'"
                @click="openGuest360(g)"
              >
                <td class="p-4" @click.stop>
                  <input
                    type="checkbox"
                    :checked="selectedIds.includes(g.id)"
                    @change="toggleRow(g.id)"
                  />
                </td>
                <td class="p-4">
                  <div class="flex items-center gap-3">
                    <div
                      class="w-10 h-10 rounded-full overflow-hidden bg-surface-container flex items-center justify-center text-primary font-bold shrink-0 border border-outline-variant text-sm"
                    >
                      {{ initial(g.name, g.city) }}
                    </div>
                    <div>
                      <div class="flex items-center gap-1.5 flex-wrap">
                        <span class="text-body-md font-body-md font-medium text-on-surface">{{
                          g.name || '—'
                        }}</span>
                        <span
                          v-if="g.arriving_today"
                          class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary border border-primary/30"
                          >{{ t('今日到店') }}</span
                        >
                        <span
                          v-else-if="g.in_stay"
                          class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200"
                          >{{ t('在住') }}</span
                        >
                        <span
                          v-if="isHighValue(g)"
                          class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200"
                          >{{ t('高价值') }}</span
                        >
                        <span
                          v-if="isChurnRisk(g)"
                          class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-50 text-red-700 border border-red-200"
                          >{{ t('流失预警') }}</span
                        >
                      </div>
                      <div class="text-label-lg font-label-lg text-on-surface-variant">
                        {{ maskPhone(g.phone) }}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="p-4">
                  <span
                    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border"
                    :class="vipClass(g.vip_level)"
                    >{{ vipLabel(g.vip_level) }}</span
                  >
                </td>
                <td class="p-4 text-body-md font-body-md text-on-surface-variant">
                  {{ g.sources || t('散客') }}
                </td>
                <td class="p-4 text-right font-num-md text-num-md text-on-surface font-medium">
                  {{ fmtMoney(g.spend ?? g.ltv) }}
                </td>
                <td class="p-4 text-body-md font-body-md text-on-surface-variant">
                  <template v-if="todayMode">
                    <div class="leading-snug">
                      <div>
                        <template v-if="g.today_stay?.room_no"
                          >{{ g.today_stay.room_no }} {{ t('房') }} ·
                        </template>
                        {{ fmtDate(g.arrival_date || g.today_stay?.check_in || g.last_visit) }}
                      </div>
                      <div
                        v-if="g.arrival_time || g.today_stay?.arrival_time"
                        class="text-xs text-primary mt-0.5"
                      >
                        {{ t('预计到店') }} {{ g.arrival_time || g.today_stay?.arrival_time }}
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <template v-if="g.today_stay?.room_no"
                      >{{ g.today_stay.room_no }} {{ t('房') }} ·
                    </template>
                    {{
                      fmtDate(g.arrival_date || g.today_stay?.check_in || g.last_visit)
                    }}</template
                  >
                </td>
                <td class="p-4">
                  <div class="flex gap-1 flex-wrap">
                    <span
                      v-for="tag in (g.tags || []).slice(0, 3)"
                      :key="tag"
                      class="px-2 py-0.5 rounded text-[11px] font-medium border"
                      :class="
                        /高\s*LTV|高净值|High.?LTV|high.?value/i.test(String(tag))
                          ? 'bg-tertiary-fixed text-on-tertiary-fixed-variant border-tertiary-fixed-dim'
                          : /风险|投诉|risk|complaint/i.test(String(tag))
                            ? 'bg-error-container text-on-error-container border-error'
                            : 'bg-surface-variant text-on-surface border-outline-variant'
                      "
                      >{{ t(tag) }}</span
                    >
                    <span v-if="!(g.tags || []).length" class="text-on-surface-variant text-xs"
                      >—</span
                    >
                  </div>
                </td>
                <td class="p-4 text-right">
                  <button type="button" class="act-btn" @click.stop="openGuest360(g)">
                    {{ t('客户画像') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div
          class="p-4 border-t border-outline-variant bg-surface-container-lowest flex justify-between items-center shrink-0 flex-wrap gap-2"
        >
          <div class="flex items-center gap-2">
            <span class="text-label-lg font-label-lg text-on-surface-variant">{{
              t('每页行数：')
            }}</span>
            <select
              v-model.number="pageSize"
              class="bg-transparent border border-outline-variant rounded text-label-lg font-label-lg py-1 pl-2 pr-6 text-on-surface focus:ring-primary focus:border-primary"
            >
              <option :value="10">10</option>
              <option :value="25">25</option>
              <option :value="50">50</option>
            </select>
          </div>
          <div class="flex items-center gap-1">
            <button
              type="button"
              class="w-8 h-8 flex items-center justify-center rounded text-on-surface hover:bg-surface-container-low text-label-lg disabled:opacity-40"
              :disabled="page <= 1"
              @click="page--"
            >
              ‹
            </button>
            <button
              v-for="p in Math.min(pageCount, 5)"
              :key="p"
              type="button"
              class="w-8 h-8 flex items-center justify-center rounded text-label-lg font-label-lg"
              :class="
                p === page
                  ? 'bg-primary text-on-primary'
                  : 'text-on-surface hover:bg-surface-container-low'
              "
              @click="page = p"
            >
              {{ p }}
            </button>
            <span v-if="pageCount > 5" class="text-on-surface-variant px-1">…</span>
            <button
              type="button"
              class="w-8 h-8 flex items-center justify-center rounded text-on-surface hover:bg-surface-container-low text-label-lg disabled:opacity-40"
              :disabled="page >= pageCount"
              @click="page++"
            >
              ›
            </button>
          </div>
        </div>
      </div>
    </div>
    <CrmTaskDrawer
      :open="taskOpen"
      :guest-ids="selectedIds"
      default-type="recall"
      @close="taskOpen = false"
      @done="selectedIds = []"
    />
  </div>
</template>

<style scoped>
.ggd {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 160px);
}
.ggd-body {
  flex: 1;
  min-height: 420px;
}

.seg-ctx {
  margin-bottom: 16px;
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--primary) 28%, var(--outline-variant));
  background: color-mix(in srgb, var(--primary) 6%, var(--surface-container-lowest));
}
.seg-ctx-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  margin-bottom: 12px;
}
.ctx-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  padding: 0;
  color: var(--primary);
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
}
.ctx-back .material-symbols-outlined {
  font-size: 16px;
}
.ctx-mode {
  font-size: 11px;
  font-weight: 750;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--primary);
  color: var(--on-primary);
}
.ctx-scope {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.seg-ctx-grid {
  display: grid;
  grid-template-columns: minmax(160px, 0.8fr) minmax(200px, 1.1fr) minmax(220px, 1.2fr);
  gap: 12px;
}
@media (max-width: 960px) {
  .seg-ctx-grid {
    grid-template-columns: 1fr;
  }
}
.ctx-block {
  min-width: 0;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
}
.ctx-k {
  font-size: 11px;
  font-weight: 750;
  color: var(--on-surface-variant);
  letter-spacing: 0.02em;
}
.ctx-v.name {
  margin-top: 4px;
  font-size: 16px;
  font-weight: 750;
}
.ctx-meta {
  margin-top: 4px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.ctx-expr {
  display: block;
  margin-top: 6px;
  font-size: 11px;
  font-weight: 650;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.45;
  color: var(--on-surface);
  max-height: 180px;
  overflow: auto;
}
.ctx-src {
  margin-top: 6px;
  font-size: 11px;
  color: var(--primary);
  font-weight: 650;
}
.ctx-meaning {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.45;
}
.ctx-bullets {
  margin: 6px 0 0;
  padding-left: 16px;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.seg-ctx-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.ctx-btn {
  padding: 7px 12px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}
.ctx-btn.ghost {
  background: transparent;
  color: var(--on-surface-variant);
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.oneid-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border: none;
  background: transparent;
  color: var(--on-surface-variant);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 8px;
  flex-shrink: 0;
}
.oneid-link .material-symbols-outlined {
  font-size: 18px;
}
.oneid-link:hover {
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 8%, transparent);
}

.home-entries {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
@media (max-width: 768px) {
  .home-entries {
    grid-template-columns: 1fr;
  }
}
.entry {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  cursor: pointer;
  text-align: left;
  transition:
    border-color 0.12s,
    box-shadow 0.12s;
}
.entry:hover {
  border-color: color-mix(in srgb, var(--primary) 35%, var(--outline-variant));
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.entry-ico {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: color-mix(in srgb, var(--primary) 10%, #fff);
  color: var(--primary);
  flex-shrink: 0;
  font-size: 22px;
}
.entry-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.entry-body strong {
  font-size: 14px;
  font-weight: 750;
  color: var(--on-surface);
}
.entry-body span {
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}

.arrival-cal {
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
}
.cal-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 650;
  color: var(--on-surface-variant);
  margin-bottom: 10px;
}
.cal-head .material-symbols-outlined {
  font-size: 18px;
}
.cal-days {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}
.cal-day {
  flex: 0 0 auto;
  min-width: 88px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  cursor: pointer;
  text-align: left;
}
.cal-day.today {
  border-color: color-mix(in srgb, var(--primary) 40%, var(--outline-variant));
}
.cal-day.on {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, #fff);
}
.cal-d {
  display: block;
  font-size: 11px;
  color: var(--on-surface-variant);
}
.cal-n {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--on-surface);
  margin-top: 2px;
}
.vip-pill {
  border-width: 1px;
  border-style: solid;
}
/* 普通：中性灰 */
.vip-normal {
  background: #f1f3f5;
  color: #64748b;
  border-color: #cbd5e1;
}
/* 银卡：银灰蓝，与普通明显区分 */
.vip-silver {
  background: #e8eef7;
  color: #334155;
  border-color: #94a3b8;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.35);
}
/* 金卡 */
.vip-gold {
  background: #fff4d6;
  color: #a16207;
  border-color: #f5d78e;
}
/* 白金 / 钻石 */
.vip-platinum {
  background: #f3e8ff;
  color: #7e22ce;
  border-color: #d8b4fe;
}
.batch-btn {
  padding: 8px 14px;
  border-radius: 10px;
  border: none;
  background: var(--primary);
  color: var(--on-primary);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}
.act-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 650;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  border: 1px solid var(--outline-variant, #c1c6d6);
  background: var(--surface-container-lowest, #fff);
  color: var(--primary, #005bbf);
  transition:
    background 0.12s,
    border-color 0.12s;
}
.act-btn:hover {
  border-color: var(--primary, #005bbf);
  background: color-mix(in srgb, var(--primary, #005bbf) 8%, #fff);
}
</style>
