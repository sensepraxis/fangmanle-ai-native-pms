<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 客群运营工作台
 * AI 白话找人 → 保存为分群 → 已有分群网格
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import CrmTaskDrawer from '../../components/CrmTaskDrawer.vue'
import CrmTaskBoard from '../../components/CrmTaskBoard.vue'
import SegmentCompareDrawer from '../../components/SegmentCompareDrawer.vue'

const router = useRouter()
const route = useRoute()
const guestN = ref(0)
const tagCatalog = ref<any[]>([])
const guests = ref<any[]>([])
const rawSegs = ref<any[]>([])
const loading = ref(true)
const taskOpen = ref(false)
const taskSeg = ref<Segment | null>(null)
const boardOpen = ref(false)
const taskBoard = ref<{ reload?: () => void } | null>(null)
const openTaskN = ref(0)
const saveTip = ref('')
const compareOpen = ref(false)
const compareBase = ref<Segment | null>(null)

/** AI 查询（真查库） */
const nlQuery = ref(t('近3个月入住时间大于2天的高价值客户'))
const lexiconOpen = ref(true)
const analyzing = ref(false)
const hasAnalyzed = ref(false)
const saving = ref(false)
const resultRef = ref<HTMLElement | null>(null)
const matchedGuests = ref<any[]>([])
const matchCount = ref(0)
const filterRule = ref('')
const filterSpec = ref<Record<string, unknown> | null>(null)
const compiledSql = ref('')
const intentSource = ref('')
const intentExpr = ref('')
const intentMeaning = ref('')
const intentModelMeta = ref('')
const streamStage = ref('')
const streamText = ref('')
const streamBoxRef = ref<HTMLElement | null>(null)
const analyzeAbort = ref<AbortController | null>(null)
const linkNote = ref('')
const queryError = ref('')
const applyingTagId = ref<number | null>(null)

type SegTone = 'vip' | 'risk' | 'ai' | 'growth' | 'neutral'

type Segment = {
  id: string
  name: string
  rule: string
  sql?: string
  meaning?: string
  cover: number
  tone: SegTone
  badge?: string
  ai?: boolean
  confidence?: number
  growth?: string
  alert?: string
  alertCta?: string
}

const TONE_META: Record<string, Partial<Segment>> = {
  vip: { badge: t('高价值'), tone: 'vip' },
  risk: {
    badge: t('待运营'),
    tone: 'risk',
    alert: t('建议优先住中关怀介入'),
    alertCta: t('发起关怀'),
  },
  ai: { badge: 'AI', tone: 'ai', ai: true },
  growth: { tone: 'growth' },
  neutral: { badge: t('分群'), tone: 'neutral' },
}

async function load() {
  loading.value = true
  try {
    const [gs, tags, segs, tasks] = await Promise.all([
      api.listGuests(hotelStore.hotelId),
      api.listTags().catch(() => []),
      api.listSegments(hotelStore.hotelId).catch(() => []),
      api.listCrmTasks(hotelStore.hotelId, 'open').catch(() => []),
    ])
    guests.value = gs || []
    guestN.value = (gs || []).length
    tagCatalog.value = tags || []
    rawSegs.value = segs || []
    openTaskN.value = (tasks || []).length
  } catch {
    guests.value = []
    guestN.value = 0
    tagCatalog.value = []
    rawSegs.value = []
    openTaskN.value = 0
  } finally {
    loading.value = false
  }
}

function closeTaskBoard() {
  boardOpen.value = false
  load()
}
onMounted(() => {
  load()
  consumeSuggestQuery()
})
watch(
  () => hotelStore.hotelId,
  () => {
    hasAnalyzed.value = false
    load()
  },
)
watch(
  () => route.query.suggest,
  () => consumeSuggestQuery(),
)

function consumeSuggestQuery() {
  const s = typeof route.query.suggest === 'string' ? route.query.suggest.trim() : ''
  if (!s) return
  nlQuery.value = s
  router.replace({ path: '/b-data/cohort-list', query: {} })
}

const liveTags = computed(() =>
  (tagCatalog.value || [])
    .filter((t: any) => Number(t.cover_count || 0) > 0)
    .slice()
    .sort((a: any, b: any) => Number(b.cover_count || 0) - Number(a.cover_count || 0)),
)

const zeroCoverTags = computed(() =>
  (tagCatalog.value || []).filter((t: any) => Number(t.cover_count || 0) === 0),
)

const tagHealth = computed(() => {
  const total = tagCatalog.value.length
  const live = liveTags.value.length
  const zero = zeroCoverTags.value.length
  return { total, live, zero }
})

const sortedTagCatalog = computed(() =>
  (tagCatalog.value || [])
    .slice()
    .sort((a: any, b: any) => Number(b.cover_count || 0) - Number(a.cover_count || 0)),
)

/** 推荐话术：优先用已打标标签，保证能出结果 */
const suggestions = computed(() => {
  const live = liveTags.value
  const out: string[] = []
  const hv =
    live.find((row: any) => String(row.code || '').toLowerCase() === 'high_value') ||
    tagCatalog.value.find((row: any) => String(row.code || '').toLowerCase() === 'high_value')
  if (hv) out.push(t('近3个月入住时间大于2天的{name}', { name: hv.name }))
  const byCode = (code: string) =>
    live.find((row: any) => String(row.code || '').toLowerCase() === code)
  const biz = byCode('business')
  const fam = byCode('family')
  const rep = byCode('repeat')
  if (biz) out.push(t('近三个月取消过订单的{name}', { name: biz.name }))
  if (rep && fam) {
    out.push(t('近一年住过三次以上、喜欢高层的{fam}里的{rep}', { fam: fam.name, rep: rep.name }))
  } else if (fam) {
    out.push(t('近一年带孩子入住的{name}', { name: fam.name }))
  }
  for (const row of live) {
    if (out.length >= 3) break
    const line = t('近90天的{name}', { name: row.name })
    if (!out.includes(line)) out.push(line)
  }
  if (!out.length) {
    out.push(t('近3个月入住时间大于2天的高价值客户'), t('近三个月取消过订单的客人'))
  }
  return out.slice(0, 3)
})

const segments = computed<Segment[]>(() =>
  rawSegs.value.map((s) => {
    const tone = (s.tone || 'neutral') as SegTone
    const meta = TONE_META[tone] || TONE_META.neutral
    return {
      id: String(s.id),
      name: s.name,
      rule: s.rule_meaning || s.rule || s.filter_rule || '—',
      sql: s.sql || '',
      meaning: s.rule_meaning || '',
      cover: Number(s.member_count || 0),
      tone,
      badge: meta.badge,
      ai: meta.ai,
      alert: meta.alert,
      alertCta: meta.alertCta,
    }
  }),
)

const previewGuests = computed(() => matchedGuests.value.slice(0, 10))

const intentTagCodes = computed(() => {
  const tags = filterSpec.value?.tag_codes_any
  return Array.isArray(tags) ? tags.map(String).filter(Boolean) : []
})

type IntentMapItem = { kind: string; label: string; value: string }

const intentMapping = computed<IntentMapItem[]>(() => {
  if (!hasAnalyzed.value || !filterSpec.value) return []
  const spec = filterSpec.value
  const out: IntentMapItem[] = []
  for (const code of intentTagCodes.value) {
    out.push({
      kind: 'tag',
      label: tagLabel(code),
      value: `tag:${code}`,
    })
  }
  const wd = Number(spec.window_days)
  if (wd) {
    out.push({ kind: 'window', label: t('近 {n} 天', { n: wd }), value: `window_days=${wd}` })
  }
  const statuses = spec.order_status
  if (Array.isArray(statuses) && statuses.length) {
    out.push({
      kind: 'status',
      label: t('订单 {status}', { status: (statuses as string[]).join('/') }),
      value: `order_status=${(statuses as string[]).join('|')}`,
    })
  }
  const mn = Number(spec.min_nights)
  if (mn > 0) {
    out.push({
      kind: 'nights',
      label: t('单次入住 ≥ {n} 天', { n: mn }),
      value: `min_nights=${mn}`,
    })
  }
  const ms = Number(spec.min_stays)
  if (ms > 0) {
    out.push({ kind: 'stays', label: t('实住 ≥ {n} 次', { n: ms }), value: `min_stays=${ms}` })
  }
  if (spec.require_children_orders) {
    out.push({ kind: 'flag', label: t('带儿童/亲子'), value: 'require_children_orders' })
  }
  if (spec.prefer_high_floor) {
    out.push({ kind: 'flag', label: t('偏好高层'), value: 'prefer_high_floor' })
  }
  return out
})

type EmptyDiag = {
  kind: 'untagged' | 'no_match' | 'plain'
  title: string
  detail: string
  tags: { id?: number; code: string; name: string; cover: number }[]
}

const emptyDiagnose = computed<EmptyDiag | null>(() => {
  if (!hasAnalyzed.value || matchCount.value > 0 || analyzing.value) return null
  const codes = intentTagCodes.value
  if (!codes.length) {
    return {
      kind: 'plain',
      title: t('暂无匹配客人'),
      detail: t('可换个描述再分析，或先在标签管理完善词表。'),
      tags: [],
    }
  }
  const tags = codes.map((code) => {
    const hit = tagCatalog.value.find(
      (t: any) =>
        String(t.code || '').toLowerCase() === code.toLowerCase() || String(t.name || '') === code,
    )
    return {
      id: hit?.id != null ? Number(hit.id) : undefined,
      code,
      name: hit?.name || code,
      cover: Number(hit?.cover_count || 0),
    }
  })
  const untagged = tags.filter((t) => t.cover <= 0)
  if (untagged.length) {
    return {
      kind: 'untagged',
      title: t('标签尚未打到客人身上'),
      detail: t('AI 已识别到标签，但覆盖为 0。请先应用打标，再重新分析。'),
      tags: untagged,
    }
  }
  return {
    kind: 'no_match',
    title: t('标签有人，但组合条件无人命中'),
    detail: t('可放宽时间窗/订单状态，或点标签查看已有覆盖名单。'),
    tags,
  }
})

function insertTagName(name: string) {
  const n = String(name || '').trim()
  if (!n) return
  const q = nlQuery.value.trim()
  if (!q) {
    nlQuery.value = n
    return
  }
  if (q.includes(n)) return
  // EN：空格拼接；中文：用「的」
  const en = /[A-Za-z]/.test(q) && !/[\u4e00-\u9fff]/.test(q)
  nlQuery.value = en ? `${q} ${n}` : /的$/.test(q) ? `${q}${n}` : `${q}的${n}`
}

function toggleLexicon() {
  lexiconOpen.value = !lexiconOpen.value
}

function segmentNameFromQuery(q: string) {
  const short = (q || '').trim().slice(0, 24)
  return short ? t('NL查询·{q}', { q: short }) : t('NL查询·自定义客群')
}

function applyAnalyzeResult(res: any, q: string) {
  matchedGuests.value = res?.guests || []
  matchCount.value = Number(res?.match_count ?? matchedGuests.value.length)
  filterRule.value = res?.filter_rule || q
  filterSpec.value = res?.filter_spec || null
  compiledSql.value = res?.sql || (res?.filter_spec as any)?.sql || ''
  intentSource.value = res?.intent_source || ''
  intentExpr.value = res?.intent_expr || res?.filter_spec?.expression || ''
  intentMeaning.value = res?.intent_meaning || res?.filter_spec?.meaning || ''
  intentModelMeta.value = formatAiModelMeta(res)
  linkNote.value = res?.link_note || ''
  hasAnalyzed.value = true
}

async function runAnalyze() {
  if (analyzing.value) return
  const q = nlQuery.value.trim()
  if (!q) {
    queryError.value = t('请输入客群描述')
    return
  }
  analyzeAbort.value?.abort()
  const ac = new AbortController()
  analyzeAbort.value = ac

  analyzing.value = true
  queryError.value = ''
  saveTip.value = ''
  streamStage.value = t('正在理解…')
  streamText.value = ''
  hasAnalyzed.value = false
  matchedGuests.value = []
  matchCount.value = 0
  try {
    await api.nlQuerySegmentsStream(
      hotelStore.hotelId,
      q,
      (evt) => {
        if (evt.type === 'stage' && evt.content) {
          streamStage.value = evt.content
        } else if (evt.type === 'token' && evt.content) {
          streamText.value += evt.content
          nextTick(() => {
            const el = streamBoxRef.value
            if (el) el.scrollTop = el.scrollHeight
          })
        } else if (evt.type === 'error') {
          queryError.value = evt.message || t('分析失败')
        } else if (evt.type === 'done' && evt.data) {
          streamStage.value = t('完成')
          applyAnalyzeResult(evt.data, q)
        }
      },
      ac.signal,
    )
    if (!hasAnalyzed.value && !queryError.value) {
      queryError.value = t('未收到完整分析结果')
    }
    await nextTick()
    resultRef.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  } catch (e: any) {
    if (e?.name === 'AbortError') return
    queryError.value = e?.message || t('查询失败')
    hasAnalyzed.value = false
    matchedGuests.value = []
    matchCount.value = 0
  } finally {
    analyzing.value = false
    if (analyzeAbort.value === ac) analyzeAbort.value = null
  }
}

function applySuggestion(s: string) {
  nlQuery.value = s
  runAnalyze()
}

function clearResult() {
  analyzeAbort.value?.abort()
  hasAnalyzed.value = false
  saveTip.value = ''
  queryError.value = ''
  matchedGuests.value = []
  matchCount.value = 0
  filterRule.value = ''
  filterSpec.value = null
  compiledSql.value = ''
  intentSource.value = ''
  intentExpr.value = ''
  intentMeaning.value = ''
  intentModelMeta.value = ''
  streamStage.value = ''
  streamText.value = ''
}

function viewMatchedInDirectory() {
  const name = segmentNameFromQuery(nlQuery.value)
  router.push({
    path: '/b-data/global-guest-directory',
    query: {
      segment: name,
      rule: filterRule.value || undefined,
    },
  })
}

async function saveAsSegment() {
  if (saving.value || !matchedGuests.value.length) return
  saving.value = true
  saveTip.value = ''
  try {
    const name = segmentNameFromQuery(nlQuery.value)
    const ids = matchedGuests.value.map((g) => Number(g.id)).filter(Boolean)
    const res = await api.createSegment(hotelStore.hotelId, {
      name,
      filter_rule: filterRule.value || nlQuery.value.trim(),
      guest_ids: ids,
    })
    const n = res?.member_count ?? ids.length
    saveTip.value = t('已保存「{name}」，覆盖 {n} 人（真实订单/标签查询）', { name, n })
    await load()
  } catch (e: any) {
    saveTip.value = e?.message || t('保存分群失败')
  } finally {
    saving.value = false
  }
}

function goMembers(s: Segment) {
  router.push({
    path: '/b-data/global-guest-directory',
    query: {
      segment: s.name,
      segment_id: s.id,
    },
  })
}

const deletingId = ref('')

async function deleteSegment(s: Segment, e?: Event) {
  e?.stopPropagation()
  if (deletingId.value) return
  const okConfirm = window.confirm(
    t('确定删除分群「{name}」？成员名单会一并清除。', { name: s.name }),
  )
  if (!okConfirm) return
  deletingId.value = s.id
  try {
    await api.deleteSegment(hotelStore.hotelId, s.id)
    await load()
  } catch (err: any) {
    window.alert(err?.message || t('删除失败'))
  } finally {
    deletingId.value = ''
  }
}

function openCompare(s: Segment, e?: Event) {
  e?.stopPropagation()
  compareBase.value = s
  compareOpen.value = true
}

function goConfig() {
  router.push('/b-data/tag-management')
}

function tagLabel(code: string) {
  const c = String(code || '')
  const hit = tagCatalog.value.find(
    (row: any) => String(row.code || '') === c || String(row.name || '') === c,
  )
  return hit?.name ? t(hit.name) : c
}

function tagCover(code: string) {
  const c = String(code || '').toLowerCase()
  const hit = tagCatalog.value.find(
    (t: any) => String(t.code || '').toLowerCase() === c || String(t.name || '') === code,
  )
  return Number(hit?.cover_count || 0)
}

function openGuestsByTag(code: string) {
  router.push({
    path: '/b-data/global-guest-directory',
    query: { tag: tagLabel(code) },
  })
}

function openTagInManagement() {
  router.push('/b-data/tag-management')
}

async function applyTagFromDiagnose(tag: { id?: number; name: string }) {
  if (!tag.id || applyingTagId.value != null) return
  applyingTagId.value = tag.id
  try {
    await api.applyTag(tag.id, hotelStore.hotelId)
    await load()
    saveTip.value = t('已为「{name}」应用打标，可再次点分析', { name: t(tag.name) })
  } catch (e: any) {
    alert(e?.message || t('打标失败'))
  } finally {
    applyingTagId.value = null
  }
}

function goDirectory() {
  router.push('/b-data/global-guest-directory')
}

function goGuest(id: number | string) {
  router.push(`/guests/${id}`)
}

function handleAlert(s: Segment, e?: Event) {
  e?.stopPropagation()
  if (s.tone === 'risk') {
    taskSeg.value = s
    taskOpen.value = true
    return
  }
  goMembers(s)
}

function onTaskDone(n: number) {
  taskSeg.value = null
  if (n > 0) {
    openTaskN.value += n
    boardOpen.value = true
    window.setTimeout(() => taskBoard.value?.reload?.(), 200)
  }
}
</script>

<template>
  <div class="page cohort">
    <header class="head">
      <div>
        <h1>{{ t('客群运营') }}</h1>
      </div>
      <div class="head-actions">
        <button type="button" class="btn" @click="boardOpen = true">
          <span class="material-symbols-outlined">task_alt</span>
          {{ t('运营任务') }}
          <span v-if="openTaskN" class="n-pill">{{ openTaskN }}</span>
        </button>
        <button type="button" class="btn primary" @click="goDirectory">
          <span class="material-symbols-outlined">home</span>
          {{ t('回客户首页') }}
        </button>
      </div>
    </header>

    <section class="ai-search">
      <div class="ai-top">
        <div class="ai-badge">
          <span class="material-symbols-outlined">auto_awesome</span>
          {{ t('AI 找人') }}
        </div>
        <button type="button" class="lex-toggle" @click="toggleLexicon">
          <span class="material-symbols-outlined">{{
            lexiconOpen ? 'expand_less' : 'expand_more'
          }}</span>
          {{ t('可用标签词表（') }}{{ tagHealth.total }}）
        </button>
      </div>
      <div class="search-row">
        <span class="material-symbols-outlined search-ico">search</span>
        <input
          v-model="nlQuery"
          type="text"
          class="search-input"
          :placeholder="t('用白话描述客群，已定义标签名会自动被识别并翻译')"
          @keydown.enter="runAnalyze"
        />
        <button type="button" class="btn-analyze" :disabled="analyzing" @click="runAnalyze">
          {{ analyzing ? t('分析中…') : t('分析') }}
          <span class="material-symbols-outlined">arrow_forward</span>
        </button>
      </div>
      <div v-if="!loading && lexiconOpen" class="tag-lexicon">
        <div class="lex-head">
          <p class="lex-hint">
            {{ t('点击标签可插入查询；分析后会在下方展示「白话 → 结构化条件」映射') }}
          </p>
          <button type="button" class="lex-mgmt" @click="goConfig">
            <span class="material-symbols-outlined">tune</span>
            {{ t('管理标签') }}
          </button>
        </div>
        <div v-if="sortedTagCatalog.length" class="lex-grid">
          <button
            v-for="tag in sortedTagCatalog"
            :key="tag.id"
            type="button"
            class="lex-card"
            :class="{ zero: Number(tag.cover_count || 0) === 0 }"
            @click="insertTagName(tag.name)"
          >
            <span class="lex-name">{{ t(tag.name) }}</span>
            <span class="lex-rule">{{ tag.rule_expr || '—' }}</span>
            <span class="lex-foot">
              <code>{{ tag.code }}</code>
              <span :class="Number(tag.cover_count || 0) > 0 ? 'cov ok' : 'cov warn'">
                {{
                  Number(tag.cover_count || 0) > 0
                    ? t('覆盖 {n} 人', { n: tag.cover_count })
                    : t('待打标')
                }}</span
              >
            </span>
          </button>
        </div>
        <p v-else class="lex-empty">
          {{ t('尚未配置标签，请先前往「管理标签」维护词表并应用打标。') }}
        </p>
      </div>
      <div class="suggests">
        <span class="sug-label">{{ t('推荐') }}</span>
        <button
          v-for="s in suggestions"
          :key="s"
          type="button"
          class="sug"
          @click="applySuggestion(s)"
        >
          {{ s }}
        </button>
      </div>
      <p v-if="queryError" class="query-err">{{ queryError }}</p>
    </section>

    <section v-if="analyzing || streamText" class="stream-panel">
      <div class="stream-head">
        <span class="material-symbols-outlined">auto_awesome</span>
        <strong>{{ t('AI 分析过程') }}</strong>
        <span v-if="analyzing" class="stream-live">
          <span class="spin material-symbols-outlined">progress_activity</span>
          {{ streamStage ? t(streamStage) : t('分析中…') }}</span
        >
        <span v-else class="stream-done">{{ streamStage ? t(streamStage) : t('已完成') }}</span>
      </div>
      <div ref="streamBoxRef" class="stream-box">
        <pre v-if="streamText" class="stream-pre">{{ streamText }}</pre>
        <p v-else class="stream-ph">{{ t('正在理解你的需求…') }}</p>
      </div>
    </section>

    <section v-if="hasAnalyzed" ref="resultRef" class="result-panel">
      <div class="result-side">
        <div class="result-meta">
          <h2>{{ t('查询结果') }}</h2>
          <p class="q-echo">「{{ nlQuery }}」</p>
          <div class="match-n">
            <span class="big">{{ matchCount }}</span>
            <span class="unit">{{ t('人匹配') }}</span>
          </div>
          <p v-if="linkNote" class="link-note">{{ t(linkNote) }}</p>
          <div v-if="intentMapping.length" class="parse-map">
            <div class="parse-head">
              <span class="material-symbols-outlined">translate</span>
              <strong>{{ t('解析映射') }}</strong>
              <span class="parse-src"></span>
            </div>
            <div class="parse-rows">
              <div v-for="(m, i) in intentMapping" :key="`${m.kind}-${i}`" class="parse-row">
                <span class="parse-label">{{ m.label }}</span>
                <span class="material-symbols-outlined parse-arrow">arrow_forward</span>
                <code class="parse-val">{{ m.value }}</code>
              </div>
            </div>
          </div>
          <p v-if="intentMeaning && !intentMapping.length" class="intent-src">
            {{ t(intentMeaning) }}
          </p>
          <p v-if="intentModelMeta" class="intent-src">{{ t('模型：') }}{{ intentModelMeta }}</p>
          <p v-if="intentExpr" class="spec-hint">{{ t('标签表达式：') }}{{ intentExpr }}</p>
          <p
            v-else-if="
              filterSpec && Array.isArray(filterSpec.order_status) && filterSpec.order_status.length
            "
            class="spec-hint"
          >
            {{ t('条件：近') }} {{ filterSpec.window_days }} {{ t('天 · 订单状态') }}
            {{ (filterSpec.order_status as string[]).join('/') }}
            <template v-if="intentTagCodes.length">
              · {{ t('标签') }} {{ intentTagCodes.map(tagLabel).join('+') }}</template
            >
          </p>
          <div v-if="intentTagCodes.length" class="intent-tags">
            <span class="itag-label">{{ t('用到的标签') }}</span>
            <button
              v-for="code in intentTagCodes"
              :key="code"
              type="button"
              class="itag"
              :title="`${t('覆盖')} ${tagCover(code)} ${t('人 · 点击查看名单')}`"
              @click="openGuestsByTag(code)"
            >
              {{ tagLabel(code) }} · {{ tagCover(code) }}
            </button>
            <button type="button" class="itag link" @click="openTagInManagement">
              {{ t('管理规则') }}
            </button>
          </div>
          <div v-if="emptyDiagnose" class="empty-diag" :class="emptyDiagnose.kind">
            <strong>{{ emptyDiagnose.title }}</strong>
            <p>{{ emptyDiagnose.detail }}</p>
            <div v-if="emptyDiagnose.tags.length" class="diag-actions">
              <template v-if="emptyDiagnose.kind === 'untagged'">
                <button
                  v-for="tag in emptyDiagnose.tags"
                  :key="tag.code"
                  type="button"
                  class="diag-btn"
                  :disabled="!tag.id || applyingTagId === tag.id"
                  @click="applyTagFromDiagnose(tag)"
                >
                  {{
                    applyingTagId === tag.id
                      ? t('打标中…')
                      : t('应用打标 · {name}', { name: t(tag.name) })
                  }}
                </button>
              </template>
              <template v-else>
                <button
                  v-for="tag in emptyDiagnose.tags"
                  :key="tag.code"
                  type="button"
                  class="diag-btn ghost"
                  @click="openGuestsByTag(tag.code)"
                >
                  {{ t('查看「{name}」名单', { name: t(tag.name) }) }}
                </button>
              </template>
              <button type="button" class="diag-btn link" @click="goConfig">
                {{ t('打开标签管理') }}
              </button>
            </div>
          </div>
          <pre v-if="compiledSql" class="sql-preview">{{ compiledSql }}</pre>
          <p v-if="saveTip" class="save-tip" :class="{ err: saveTip.includes(t('失败')) }">
            {{ saveTip }}
          </p>
        </div>
        <div class="result-actions">
          <button
            type="button"
            class="btn primary block"
            :disabled="saving || !matchCount"
            @click="saveAsSegment"
          >
            {{ saving ? t('保存中…') : t('保存为分群（{n} 人）', { n: matchCount }) }}
          </button>
          <button
            type="button"
            class="btn block"
            :disabled="!matchCount"
            @click="viewMatchedInDirectory"
          >
            {{ t('在全景列表查看') }}
          </button>
          <button type="button" class="btn ghost block" @click="clearResult">
            {{ t('收起结果') }}
          </button>
        </div>
      </div>
      <div class="result-list">
        <div class="list-head">
          <h3>{{ t('高匹配名单') }}</h3>
          <span class="pill"
            >{{ t('预览 Top {n}', { n: previewGuests.length })
            }}{{ matchCount > previewGuests.length ? ` / ${matchCount}` : '' }}</span
          >
        </div>
        <div v-if="!previewGuests.length" class="empty">
          <template v-if="emptyDiagnose">{{ emptyDiagnose.title }}</template>
          <template v-else>{{ t('暂无匹配客人，可换个描述再分析。') }}</template>
        </div>
        <button
          v-for="g in previewGuests"
          :key="g.id"
          type="button"
          class="guest-row"
          @click="goGuest(g.id)"
        >
          <span class="avatar">{{ String(g.name || '?').slice(0, 1) }}</span>
          <span class="g-main">
            <span class="g-name">{{ g.name }}</span>
            <span class="g-tags">
              <span v-for="tag in (g.tags || []).slice(0, 3)" :key="tag" class="tag">{{
                tag
              }}</span>
              <span v-if="g.cancel_count" class="tag cancel">{{
                t('取消 {n} 单', { n: g.cancel_count })
              }}</span>
              <span v-if="g.last_cancel_at" class="tag">{{
                t('最近 {d}', { d: g.last_cancel_at })
              }}</span>
            </span>
          </span>
          <span class="g-ltv"
            >LTV ¥{{ Number(g.ltv || g.spend || 0).toLocaleString('zh-CN') }}</span
          >
        </button>
      </div>
    </section>

    <section class="seg-section">
      <div class="sec-label">
        <h2>{{ t('已有分群（{n}）', { n: segments.length }) }}</h2>
      </div>
      <div class="seg-grid">
        <article v-for="s in segments" :key="s.id" class="seg-card" :class="s.tone">
          <div class="seg-top">
            <span v-if="s.badge" class="badge" :class="s.tone">{{ s.badge }}</span>
          </div>
          <h3>{{ s.name }}</h3>
          <p class="rule">{{ t(s.meaning || s.rule) }}</p>
          <div class="seg-foot">
            <div class="cover">
              <span class="num">{{ s.cover.toLocaleString('zh-CN') }}</span>
              <span class="unit">{{ t('人覆盖') }}</span>
            </div>
            <div class="seg-actions">
              <button
                type="button"
                class="seg-btn danger"
                :disabled="deletingId === s.id"
                @click.stop="deleteSegment(s, $event)"
              >
                {{ deletingId === s.id ? t('删除中…') : t('删除') }}
              </button>
              <button type="button" class="seg-btn ghost" @click.stop="openCompare(s, $event)">
                {{ t('比对客群') }}
              </button>
              <button type="button" class="seg-btn primary" @click.stop="goMembers(s)">
                {{ t('看成员') }}
              </button>
            </div>
          </div>
          <div v-if="s.alert" class="alert-bar" @click.stop="handleAlert(s, $event)">
            <span class="material-symbols-outlined">campaign</span>
            <span class="grow">{{ s.alert }}</span>
            <span class="cta">{{ s.alertCta || t('去处理') }}</span>
          </div>
        </article>
      </div>
    </section>

    <CrmTaskDrawer
      :open="taskOpen"
      :segment-id="taskSeg ? Number(taskSeg.id) : undefined"
      :segment-name="taskSeg?.name"
      default-type="recall"
      @close="taskOpen = false"
      @done="onTaskDone"
    />
    <SegmentCompareDrawer
      :open="compareOpen"
      :base="
        compareBase
          ? { id: compareBase.id, name: compareBase.name, cover: compareBase.cover }
          : null
      "
      :options="segments.map((s) => ({ id: s.id, name: s.name, cover: s.cover }))"
      @close="compareOpen = false"
    />
    <CrmTaskBoard ref="taskBoard" :open="boardOpen" @close="closeTaskBoard" />
  </div>
</template>

<style scoped>
/* 不限制 max-width — 与其他页面一致撑满可用宽度 */
.cohort {
  width: 100%;
}

.head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 20px;
}
.head h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 750;
}
.head p {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--on-surface-variant);
  max-width: 520px;
}
.head-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.n-pill {
  margin-left: 2px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--primary);
  color: var(--on-primary);
  font-size: 11px;
  line-height: 18px;
  text-align: center;
}
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 9px 14px;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  font-size: 13px;
  font-weight: 650;
}
.btn.primary {
  background: var(--primary);
  color: var(--on-primary);
  border-color: transparent;
}
.btn.ghost {
  background: transparent;
  border-color: transparent;
  color: var(--on-surface-variant);
}
.btn.block {
  width: 100%;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn .material-symbols-outlined {
  font-size: 18px;
}

.ai-search {
  margin-bottom: 20px;
  padding: 18px 20px;
  border-radius: 16px;
  background: color-mix(in srgb, var(--tertiary, #8c33b3) 6%, var(--surface-container-lowest));
  border: 1px solid color-mix(in srgb, var(--tertiary, #8c33b3) 22%, var(--outline-variant));
}
.ai-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 700;
  color: var(--tertiary, #8c33b3);
}
.lex-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  color: var(--on-surface-variant);
  font-size: 12px;
  font-weight: 650;
  padding: 5px 10px;
  border-radius: 999px;
  cursor: pointer;
}
.lex-toggle:hover {
  border-color: var(--primary);
  color: var(--primary);
}
.lex-toggle .material-symbols-outlined {
  font-size: 18px;
}
.tag-lexicon {
  margin: 12px 0 14px;
  padding: 12px;
  border-radius: 12px;
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
}
.lex-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.lex-hint {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}
.lex-mgmt {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: var(--primary);
  color: var(--on-primary);
  font-size: 12px;
  font-weight: 650;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
}
.lex-mgmt .material-symbols-outlined {
  font-size: 16px;
}
.lex-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 8px;
}
.lex-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  text-align: left;
  padding: 10px 11px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-low, #f3f1ec);
  cursor: pointer;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.lex-card:hover {
  border-color: var(--primary);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.lex-card.zero {
  opacity: 0.88;
}
.lex-name {
  font-size: 13px;
  font-weight: 750;
  color: var(--on-surface);
}
.lex-rule {
  font-size: 11px;
  color: var(--on-surface-variant);
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.7em;
}
.lex-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
  margin-top: 2px;
}
.lex-foot code {
  font-size: 10px;
  color: var(--on-surface-variant);
  background: transparent;
}
.lex-foot .cov {
  font-size: 10px;
  font-weight: 700;
}
.lex-foot .cov.ok {
  color: #16a34a;
}
.lex-foot .cov.warn {
  color: #c2410c;
}
.lex-empty {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.ai-badge .material-symbols-outlined {
  font-size: 16px;
}
.search-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 6px 6px 14px;
  border-radius: 999px;
  background: var(--surface-container-lowest);
  border: 1.5px solid var(--outline-variant);
}
.search-row:focus-within {
  border-color: var(--tertiary, #8c33b3);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tertiary, #8c33b3) 18%, transparent);
}
.search-ico {
  color: var(--tertiary, #8c33b3);
  font-size: 22px;
  flex-shrink: 0;
}
.search-input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  font-size: 15px;
  padding: 10px 4px;
  outline: none;
  color: var(--on-surface);
}
.btn-analyze {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  padding: 10px 18px;
  border: none;
  border-radius: 999px;
  background: var(--tertiary, #8c33b3);
  color: var(--on-tertiary, #fff);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.btn-analyze:disabled {
  opacity: 0.65;
  cursor: wait;
}
.btn-analyze .material-symbols-outlined {
  font-size: 16px;
}
.suggests {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}
.sug-label {
  font-size: 12px;
  color: var(--on-surface-variant);
  font-weight: 650;
}
.sug {
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  font-size: 12px;
  color: var(--on-surface-variant);
  cursor: pointer;
  max-width: 100%;
  text-align: left;
}
.sug:hover {
  border-color: var(--tertiary, #8c33b3);
  color: var(--on-surface);
}
.query-err {
  margin: 10px 0 0;
  font-size: 12px;
  font-weight: 650;
  color: #c2410c;
}
.stream-panel {
  margin-bottom: 16px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid color-mix(in srgb, var(--tertiary, #8c33b3) 28%, var(--outline-variant));
  background: color-mix(in srgb, var(--tertiary, #8c33b3) 6%, var(--surface, #fff));
}
.stream-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
  font-size: 13px;
}
.stream-head .material-symbols-outlined {
  font-size: 18px;
  color: var(--tertiary, #8c33b3);
}
.stream-live {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  font-size: 12px;
  color: var(--tertiary, #8c33b3);
  font-weight: 650;
}
.stream-live .spin {
  font-size: 16px;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.stream-done {
  margin-left: auto;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.stream-box {
  max-height: 180px;
  overflow: auto;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: #fff;
  padding: 10px 12px;
}
.stream-pre {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color: var(--on-surface);
}
.stream-ph {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.link-note {
  margin: 8px 0 0;
  font-size: 11px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}
.parse-map {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-low, #f8f6f2);
}
.parse-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 12px;
}
.parse-head .material-symbols-outlined {
  font-size: 16px;
  color: var(--tertiary, #8c33b3);
}
.parse-src {
  margin-left: auto;
  font-size: 11px;
  font-weight: 650;
  color: var(--on-surface-variant);
}
.parse-rows {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.parse-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 12px;
}
.parse-label {
  font-weight: 700;
  color: var(--on-surface);
}
.parse-arrow {
  font-size: 14px;
  color: var(--on-surface-variant);
}
.parse-val {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 6px;
  background: var(--surface-container-lowest);
  color: var(--tertiary, #8c33b3);
  font-family: ui-monospace, monospace;
}
.intent-src {
  margin: 8px 0 0;
  font-size: 12px;
  font-weight: 650;
  color: var(--on-surface);
  line-height: 1.4;
}
.spec-hint {
  margin: 6px 0 0;
  font-size: 11px;
  font-weight: 650;
  color: var(--tertiary, #8c33b3);
}
.intent-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
}
.itag-label {
  font-size: 11px;
  font-weight: 650;
  color: var(--on-surface-variant);
}
.itag {
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest, #fff);
  color: var(--primary);
  font-size: 12px;
  font-weight: 650;
  padding: 3px 9px;
  border-radius: 999px;
  cursor: pointer;
}
.itag:hover {
  border-color: var(--primary);
}
.itag.link {
  background: transparent;
  border-style: dashed;
}
.tag-empty-hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: #9a3412;
  line-height: 1.45;
}
.tag-empty-hint .inline-link {
  border: none;
  background: transparent;
  color: var(--primary);
  font-weight: 700;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
}
.empty-diag {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #fdba74;
  background: #fff7ed;
  color: #9a3412;
}
.empty-diag.no_match {
  border-color: color-mix(in srgb, var(--primary) 30%, var(--outline-variant));
  background: color-mix(in srgb, var(--primary) 6%, #fff);
  color: var(--on-surface);
}
.empty-diag.plain {
  border-color: var(--outline-variant);
  background: var(--surface-container-low);
  color: var(--on-surface-variant);
}
.empty-diag strong {
  display: block;
  font-size: 13px;
}
.empty-diag p {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.45;
  opacity: 0.92;
}
.diag-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.diag-btn {
  border: 1px solid transparent;
  background: var(--primary);
  color: var(--on-primary);
  font-size: 12px;
  font-weight: 650;
  padding: 5px 10px;
  border-radius: 8px;
  cursor: pointer;
}
.diag-btn.ghost {
  background: var(--surface-container-lowest);
  color: var(--primary);
  border-color: var(--outline-variant);
}
.diag-btn.link {
  background: transparent;
  color: var(--primary);
  border-style: dashed;
  border-color: var(--outline-variant);
}
.diag-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.sql-preview {
  margin: 10px 0 0;
  padding: 10px 12px;
  max-height: 160px;
  overflow: auto;
  font-size: 10px;
  line-height: 1.45;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--on-surface);
  background: color-mix(in srgb, var(--surface-container-high, #f3edf7) 80%, transparent);
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
}
.tag.cancel {
  background: #ffedd5;
  color: #9a3412;
}

.result-panel {
  display: grid;
  grid-template-columns: minmax(220px, 280px) 1fr;
  gap: 14px;
  margin-bottom: 20px;
  padding: 16px;
  border-radius: 16px;
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
}
@media (max-width: 900px) {
  .result-panel {
    grid-template-columns: 1fr;
  }
}
.result-side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.result-meta h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 750;
}
.q-echo {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.match-n {
  margin-top: 12px;
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.match-n .big {
  font-size: 32px;
  font-weight: 750;
  color: var(--primary);
}
.match-n .unit {
  font-size: 13px;
  color: var(--on-surface-variant);
}
.save-tip {
  margin: 8px 0 0;
  font-size: 12px;
  font-weight: 650;
  color: #16a34a;
}
.save-tip.err {
  color: #c2410c;
}
.result-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.result-list {
  border-radius: 12px;
  border: 1px solid var(--outline-variant);
  background: var(--surface);
  overflow: hidden;
  max-height: 360px;
  display: flex;
  flex-direction: column;
}
.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
}
.list-head h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
}
.pill {
  font-size: 11px;
  font-weight: 650;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-variant);
  color: var(--on-surface-variant);
}
.empty {
  padding: 24px 14px;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.guest-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  text-align: left;
  padding: 10px 14px;
  border: none;
  border-bottom: 1px solid var(--outline-variant);
  background: transparent;
  cursor: pointer;
}
.guest-row:last-child {
  border-bottom: none;
}
.guest-row:hover {
  background: var(--surface-container-low);
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  background: var(--secondary-container, #dce4ff);
  color: var(--on-secondary-container, #001a41);
  font-weight: 700;
  font-size: 14px;
}
.g-main {
  flex: 1;
  min-width: 0;
}
.g-name {
  display: block;
  font-size: 14px;
  font-weight: 700;
}
.g-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--surface-variant);
  color: var(--on-surface-variant);
}
.g-ltv {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  font-variant-numeric: tabular-nums;
}

.seg-section {
  margin-bottom: 16px;
}
.sec-label {
  margin-bottom: 12px;
}
.sec-label h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 750;
}
.sec-label p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}

.seg-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 1100px) {
  .seg-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .seg-grid {
    grid-template-columns: 1fr;
  }
}
.seg-card {
  position: relative;
  text-align: left;
  cursor: default;
  padding: 18px 18px 16px;
  border-radius: 14px;
  /* 纸面底 + 轻微纵向光感 */
  background: linear-gradient(165deg, #ffffff 0%, #fbfaf8 48%, #f4f1ec 100%);
  /* 外框描边 */
  border: 1.5px solid #c9c2b6;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 176px;
  /* 镜框：内衬白边 → 衬垫 → 外阴影 */
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.95),
    inset 0 0 0 5px #f7f4ef,
    inset 0 0 0 6px rgba(120, 110, 95, 0.22),
    0 1px 1px rgba(40, 35, 28, 0.04),
    0 6px 16px rgba(40, 35, 28, 0.07),
    0 14px 28px rgba(40, 35, 28, 0.05);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}
.seg-card::before {
  content: '';
  pointer-events: none;
  position: absolute;
  inset: 7px;
  border-radius: 9px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: inset 0 0 0 1px rgba(90, 80, 70, 0.06);
}
.seg-card:hover {
  transform: translateY(-2px);
  border-color: #a89f90;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.98),
    inset 0 0 0 5px #faf7f2,
    inset 0 0 0 6px rgba(100, 90, 75, 0.28),
    0 2px 4px rgba(40, 35, 28, 0.06),
    0 10px 22px rgba(40, 35, 28, 0.1),
    0 20px 36px rgba(40, 35, 28, 0.07);
}
.seg-card.vip {
  border-color: color-mix(in srgb, #b45309 42%, #c9c2b6);
  background: linear-gradient(165deg, #fffefb 0%, #fffbeb 52%, #fef3c7 100%);
}
.seg-card.risk {
  border-color: color-mix(in srgb, #ea580c 38%, #c9c2b6);
  background: linear-gradient(165deg, #fffefc 0%, #fff7ed 55%, #ffedd5 100%);
}
.seg-card.ai {
  border-color: color-mix(in srgb, #7c3aed 28%, #c9c2b6);
  background: linear-gradient(165deg, #fffefe 0%, #faf5ff 55%, #f3e8ff 100%);
}
.seg-card.growth {
  border-color: color-mix(in srgb, #16a34a 35%, #c9c2b6);
  background: linear-gradient(165deg, #fefffe 0%, #f0fdf4 55%, #dcfce7 100%);
}
.seg-card h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 750;
  position: relative;
  z-index: 1;
}
.rule {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant);
  line-height: 1.45;
  flex: 1;
  position: relative;
  z-index: 1;
}
.seg-top,
.seg-foot,
.alert-bar {
  position: relative;
  z-index: 1;
}
.seg-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-height: 22px;
}
.badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-container-low);
  color: var(--on-surface-variant);
}
.badge.vip {
  background: #fef3c7;
  color: #92400e;
}
.badge.risk {
  background: #ffedd5;
  color: #9a3412;
}
.badge.ai {
  background: var(--tertiary-fixed, #f8d8ff);
  color: var(--on-tertiary-fixed-variant, #721199);
}
.badge.growth {
  background: #dcfce7;
  color: #166534;
}
.conf,
.growth {
  font-size: 12px;
  font-weight: 650;
  margin-left: auto;
  color: var(--on-surface-variant);
}
.growth {
  color: #16a34a;
}
.seg-foot {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
}
.cover .num {
  font-size: 22px;
  font-weight: 750;
}
.cover .unit {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-left: 4px;
}
.seg-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.seg-btn {
  appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s,
    color 0.15s,
    box-shadow 0.15s;
}
.seg-btn:disabled {
  opacity: 0.55;
  cursor: wait;
}
.seg-btn.primary {
  color: #fff;
  background: var(--primary, #005bbf);
  border-color: color-mix(in srgb, var(--primary, #005bbf) 80%, #000);
  box-shadow: 0 1px 2px rgba(0, 60, 140, 0.18);
}
.seg-btn.primary:hover:not(:disabled) {
  filter: brightness(1.05);
  box-shadow: 0 2px 6px rgba(0, 60, 140, 0.22);
}
.seg-btn.ghost {
  color: var(--primary, #005bbf);
  background: #fff;
  border-color: color-mix(in srgb, var(--primary, #005bbf) 35%, var(--outline-variant));
}
.seg-btn.ghost:hover:not(:disabled) {
  background: color-mix(in srgb, var(--primary, #005bbf) 8%, #fff);
}
.seg-btn.danger {
  color: #9a3412;
  background: #fff7ed;
  border-color: #fdba74;
}
.seg-btn.danger:hover:not(:disabled) {
  background: #ffedd5;
  border-color: #fb923c;
  color: #7c2d12;
}
.link {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--primary);
  font-size: 13px;
  font-weight: 650;
  padding: 0;
}
.alert-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 12px;
  font-weight: 600;
}
.alert-bar .material-symbols-outlined {
  font-size: 16px;
}
.alert-bar .grow {
  flex: 1;
}
.alert-bar .cta {
  color: var(--primary);
}

.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
</style>
