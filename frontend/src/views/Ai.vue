<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { formatAiModelMeta } from '../lib/aiModelMeta'
import { confidenceLabel } from '../lib/aiConfidence'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import AnalyticsOpsNav from '../components/AnalyticsOpsNav.vue'

type FlowItem =
  | { kind: 'user'; text: string }
  | { kind: 'sys'; tag?: string; text: string }
  | { kind: 'thinking'; text: string }
  | { kind: 'stream'; tag: string; text: string; done?: boolean }
  | {
      kind: 'clarify'
      prompt: string
      options: { value?: string; label: string; intent_id?: string }[]
      ghost?: { label: string; action: 'none' | 'cancel' }
      mode: 'intent' | 'slot' | 'confirm' | 'oos' | 'action'
      slot?: string
      query_id?: number
      intent_id?: string
      slots?: Record<string, unknown>
      presets?: { question: string }[]
    }
  | {
      kind: 'decompose'
      prompt: string
      query_id?: number
      intent_id?: string
      slots?: Record<string, unknown>
      pipeline: { step: string; title: string; detail: string }[]
      normalized_question?: string
    }
  | {
      kind: 'result'
      intent_label: string
      note?: string
      summary: string
      key_points: string[]
      rows: {
        label: string
        value: unknown
        note?: string
        tone?: string
        guest_id?: string
        guest_name?: string
      }[]
      unit?: string
      series: { name: string; value: number }[]
      answer_source?: string
      model_meta?: string
      confidence?: string
      tips?: { id?: string; name: string; desc?: string; expected_impact?: string }[]
      is_followup?: boolean
      query_id?: number
      need_pii_ack?: boolean
      can_ack_pii?: boolean
      pii_level?: string
      pii_accessed?: boolean
      ack_by?: string
      ack_busy?: boolean
    }

const router = useRouter()
/** 与后端约定：period / baseline 传中文 msgid，展示时再 t() */
const PERIODS = ['本周', '本月', '本季'] as const
const period = ref<string>('本月')
const baseline = ref<string>('同比')
const input = ref('')
const busy = ref(false)
const flow = ref<FlowItem[]>([
  {
    kind: 'sys',
    tag: t('AI 问数'),
    text: t('你好。可以直接点下面的常见问题，或用自己的话问经营数据。不确定时我会先跟你确认再查。'),
  },
])
const presets = ref<{ intent_id: string; question: string; label: string }[]>([
  { intent_id: 'channel_profit_loss', question: '本月哪些渠道在亏钱？', label: '哪些渠道在亏钱' },
  { intent_id: 'business_churn', question: '商务客是不是在流失？', label: '商务客流失' },
  { intent_id: 'ota_share_ratio', question: 'OTA 占比是否过高？', label: 'OTA 占比' },
  { intent_id: 'member_repurchase', question: '会员复购有没有变差？', label: '会员复购' },
  {
    intent_id: 'occupancy_compare_mom',
    question: '这个月入住率相比上个月如何？',
    label: '入住率环比',
  },
  {
    intent_id: 'guest_top_rank_cumulative_payment',
    question: '累计消费最高的前 5 个客人是谁？',
    label: '累计消费 Top5',
  },
])
const glossary = ref<
  {
    standard_term: string
    aliases: string[]
    unit?: string
    definition?: string
    domain?: string
    sample_query?: string
  }[]
>([])
const sessionId = ref<string | undefined>()
const clarifyRound = ref(0)
const flowEl = ref<HTMLElement | null>(null)
let pendingQuestion = ''

async function scrollBottom() {
  await nextTick()
  if (flowEl.value) flowEl.value.scrollTop = flowEl.value.scrollHeight
}

function removeThinking() {
  flow.value = flow.value.filter((x) => x.kind !== 'thinking')
}

onMounted(async () => {
  try {
    const cat = await api.insightsAiAskCatalog(hotelStore.hotelId)
    if (cat?.presets?.length) presets.value = cat.presets
    if (cat?.glossary?.length) glossary.value = cat.glossary
  } catch {
    /* 用本地默认 */
  }
})

async function ask(q: string) {
  const text = (q || '').trim()
  if (!text || busy.value) return
  pendingQuestion = text
  input.value = ''
  flow.value.push({ kind: 'user', text: t(text) })
  flow.value.push({ kind: 'thinking', text: t('正在理解你的问题…') })
  busy.value = true
  await scrollBottom()
  try {
    const res = await api.insightsAiAskRoute(hotelStore.hotelId, {
      question: text,
      period: period.value,
      baseline: baseline.value,
      session_id: sessionId.value,
      clarify_round: clarifyRound.value,
    })
    removeThinking()
    sessionId.value = res.session_id
    clarifyRound.value = res.clarify_round || 0
    await handleRoutePayload(res)
  } catch (e: any) {
    removeThinking()
    flow.value.push({
      kind: 'sys',
      tag: t('提示'),
      text: t('暂时没理解清楚：{msg}。可以换个说法，或点下面的常见问题。', {
        msg: String(e?.message || e || ''),
      }),
    })
  } finally {
    busy.value = false
    await scrollBottom()
  }
}

async function handleRoutePayload(res: any) {
  const st = res.status
  if (st === 'out_of_scope') {
    flow.value.push({
      kind: 'clarify',
      mode: 'oos',
      prompt: res.message || t('这个问题我暂时答不了。'),
      options: [],
      presets: res.presets || presets.value,
    })
    return
  }
  if (st === 'action_block') {
    flow.value.push({
      kind: 'clarify',
      mode: 'action',
      prompt: res.message || t('这是操作不是问数。'),
      options: [{ label: t('去价格助手'), value: 'pricing' }],
      ghost: { label: t('知道了'), action: 'none' },
    })
    return
  }
  if (st === 'clarify_intent') {
    flow.value.push({
      kind: 'clarify',
      mode: 'intent',
      prompt: res.prompt,
      query_id: res.query_id,
      options: (res.options || []).map((o: any) => ({
        intent_id: o.intent_id,
        label: o.intent_label || o.label,
        value: o.intent_id,
      })),
      ghost: { label: t('都不是，重新问'), action: 'none' },
    })
    return
  }
  if (st === 'clarify_slot') {
    flow.value.push({
      kind: 'clarify',
      mode: 'slot',
      prompt: res.prompt,
      query_id: res.query_id,
      intent_id: res.intent_id,
      slot: res.slot,
      options: (res.options || []).map((o: any) => ({
        value: String(o.value),
        label: o.label,
      })),
      ghost: { label: t('先不查了'), action: 'cancel' },
    })
    return
  }
  if (st === 'auto_execute') {
    await runConfirm({
      kind: 'clarify',
      mode: 'confirm',
      prompt: res.prompt || '',
      query_id: res.query_id,
      intent_id: res.intent_id,
      slots: res.slots,
      options: [],
    })
    return
  }
  if (st === 'decompose_confirm') {
    const bl = res.slots?._baseline || res.slots?.baseline
    if (bl === t('环比') || bl === t('同比')) baseline.value = bl
    flow.value.push({
      kind: 'decompose',
      prompt: res.prompt || t('按下面理解去查数？'),
      query_id: res.query_id,
      intent_id: res.intent_id,
      slots: res.slots,
      pipeline: res.pipeline || [],
      normalized_question: res.normalized_question,
    })
    return
  }
  if (st === 'confirm') {
    flow.value.push({
      kind: 'clarify',
      mode: 'confirm',
      prompt: res.prompt,
      query_id: res.query_id,
      intent_id: res.intent_id,
      slots: res.slots,
      options: [{ label: t('是，就查这个'), value: 'yes' }],
      ghost: { label: t('不是，重新问'), action: 'cancel' },
    })
  }
}

async function onDecomposeConfirm(item: Extract<FlowItem, { kind: 'decompose' }>) {
  const idx = flow.value.indexOf(item)
  if (idx >= 0) flow.value.splice(idx, 1)
  busy.value = true
  try {
    await runConfirm({
      kind: 'clarify',
      mode: 'confirm',
      prompt: item.prompt,
      query_id: item.query_id,
      intent_id: item.intent_id,
      slots: item.slots,
      options: [],
    })
  } finally {
    busy.value = false
    await scrollBottom()
  }
}

async function onClarifyOption(
  item: Extract<FlowItem, { kind: 'clarify' }>,
  opt: { value?: string; label: string; intent_id?: string },
) {
  if (busy.value) return
  const idx = flow.value.indexOf(item)
  if (idx >= 0) flow.value.splice(idx, 1)

  if (item.mode === 'action' && opt.value === 'pricing') {
    router.push('/pricing')
    return
  }
  if (item.mode === 'oos' && opt.label) {
    await ask(opt.label)
    return
  }

  busy.value = true
  try {
    if (item.mode === 'intent') {
      flow.value.push({ kind: 'thinking', text: t('已选意图，准备确认…') })
      const res = await api.insightsAiAskClarify(hotelStore.hotelId, {
        query_id: item.query_id!,
        question: pendingQuestion,
        intent_id: opt.intent_id || opt.value,
        period: period.value,
        baseline: baseline.value,
        clarify_round: clarifyRound.value,
      })
      removeThinking()
      clarifyRound.value = res.clarify_round || clarifyRound.value + 1
      await handleRoutePayload(res)
    } else if (item.mode === 'slot') {
      flow.value.push({ kind: 'thinking', text: t('已补齐参数…') })
      if (item.slot === 'period' && opt.value) period.value = opt.value
      const res = await api.insightsAiAskClarify(hotelStore.hotelId, {
        query_id: item.query_id!,
        question: pendingQuestion,
        intent_id: item.intent_id,
        slot: item.slot,
        slot_value: opt.value,
        period: period.value,
        baseline: baseline.value,
        clarify_round: clarifyRound.value,
      })
      removeThinking()
      clarifyRound.value = res.clarify_round || clarifyRound.value + 1
      await handleRoutePayload(res)
    } else if (item.mode === 'confirm' && opt.value === 'yes') {
      await runConfirm(item)
    }
  } catch (e: any) {
    removeThinking()
    flow.value.push({ kind: 'sys', tag: t('系统'), text: e?.message || t('操作失败') })
  } finally {
    busy.value = false
    await scrollBottom()
  }
}

async function onGhost(item: Extract<FlowItem, { kind: 'clarify' }>) {
  const idx = flow.value.indexOf(item)
  if (idx >= 0) flow.value.splice(idx, 1)
  if (item.ghost?.action === 'cancel' && item.query_id) {
    try {
      await api.insightsAiAskConfirm(hotelStore.hotelId, {
        query_id: item.query_id,
        confirmed: false,
      })
    } catch {
      /* ignore */
    }
  }
  if (item.mode === 'oos') return
  flow.value.push({
    kind: 'sys',
    tag: t('系统'),
    text: t('已取消。可换种说法，或直接点上面的默认问题。'),
  })
  await scrollBottom()
}

async function runConfirm(item: Extract<FlowItem, { kind: 'clarify' }>) {
  removeThinking()
  flow.value.push({ kind: 'thinking', text: t('正在查询…') })
  await scrollBottom()

  let streamIdx = -1
  const ensureStream = (tag: string) => {
    if (streamIdx < 0 || flow.value[streamIdx]?.kind !== 'stream') {
      flow.value.push({ kind: 'stream', tag, text: '' })
      streamIdx = flow.value.length - 1
    } else {
      ;(flow.value[streamIdx] as any).tag = tag
    }
  }

  try {
    await api.insightsAiAskConfirmStream(
      hotelStore.hotelId,
      async (evt) => {
        if (evt.type === 'stage') {
          removeThinking()
          if (evt.stage === 'llm') {
            ensureStream(t('正在整理回答'))
          } else {
            flow.value.push({ kind: 'thinking', text: evt.message || t('处理中…') })
          }
          await scrollBottom()
        } else if (evt.type === 'query_done') {
          removeThinking()
          await scrollBottom()
        } else if (evt.type === 'token' && evt.content) {
          removeThinking()
          ensureStream(t('正在整理回答'))
          const cur = flow.value[streamIdx] as Extract<FlowItem, { kind: 'stream' }>
          cur.text += evt.content
          await scrollBottom()
        } else if (evt.type === 'fallback') {
          /* 静默降级 */
        } else if (evt.type === 'error') {
          removeThinking()
          flow.value.push({
            kind: 'sys',
            tag: t('提示'),
            text: evt.message || t('查询失败，请稍后重试'),
          })
        } else if (evt.type === 'done') {
          removeThinking()
          if (streamIdx >= 0 && flow.value[streamIdx]?.kind === 'stream') {
            ;(flow.value[streamIdx] as any).done = true
          }
          const res = evt.data || {}
          if (res.status === 'clarify_slot') {
            await handleRoutePayload(res)
            return
          }
          if (res.status === 'pii_denied') {
            flow.value.push({
              kind: 'sys',
              tag: t('权限'),
              text: res.message || t('无权限查看客户个人数据'),
            })
            return
          }
          if (res.status !== 'answered') {
            flow.value.push({ kind: 'sys', tag: t('提示'), text: res.message || t('暂无结果') })
            return
          }
          pushResult(res)
        }
      },
      {
        query_id: item.query_id!,
        confirmed: true,
        intent_id: item.intent_id,
        slots: item.slots,
        period: period.value,
        baseline: baseline.value,
      },
    )
  } catch (e: any) {
    removeThinking()
    flow.value.push({ kind: 'sys', tag: t('提示'), text: e?.message || t('查询失败，请稍后重试') })
  }
  await scrollBottom()
}

function pushResult(res: any) {
  const result = res.result || {}
  const answer = res.answer || {}
  const tips = res.tips || answer.tips || result.playbook_tips || []
  const series = (answer.chart?.series || result.rows || [])
    .map((s: any) => {
      if (s.name != null) return { name: String(s.name), value: Number(s.value) || 0 }
      return { name: String(s.label || s.guest_name || ''), value: Number(s.value) || 0 }
    })
    .filter((s: { value: number }) => Number.isFinite(s.value))
  const src = String(res.answer_source || answer.source || '')
  flow.value.push({
    kind: 'result',
    intent_label: res.intent_label || t('查询结果'),
    note: res.note,
    summary: answer.summary || t('暂未查到相关数据'),
    key_points: answer.key_points || [],
    rows: result.rows || [],
    unit: result.unit,
    series,
    answer_source: src,
    model_meta: src === 'llm' ? formatAiModelMeta(res) : '',
    confidence: src === 'llm' ? answer.confidence || res.confidence || '' : '',
    tips: Array.isArray(tips) ? tips : [],
    is_followup: !!res.is_followup,
    query_id: res.query_id,
    need_pii_ack: !!res.need_pii_ack,
    can_ack_pii: !!res.can_ack_pii,
    pii_level: res.pii_level || result.pii_level || 'none',
    pii_accessed: !!res.pii_accessed,
    ack_by: '',
    ack_busy: false,
  })
}

async function onPiiAck(item: Extract<FlowItem, { kind: 'result' }>) {
  if (!item.query_id || item.ack_busy) return
  const staff = (item.ack_by || '').trim()
  if (!staff) {
    flow.value.push({ kind: 'sys', tag: t('提示'), text: t('请先填写工号再确认查看客户明细。') })
    return
  }
  if (!item.can_ack_pii) {
    flow.value.push({
      kind: 'sys',
      tag: t('权限'),
      text: t('当前账号无权限查看客户个人数据（需店长/管理员）。'),
    })
    return
  }
  item.ack_busy = true
  try {
    const res = await api.insightsAiAskPiiAck(hotelStore.hotelId, {
      query_id: item.query_id,
      ack_by: staff,
      period: period.value,
      baseline: baseline.value,
    })
    if (res.status === 'pii_denied' || res.status === 'error') {
      flow.value.push({ kind: 'sys', tag: t('提示'), text: res.message || t('确认失败') })
      return
    }
    const idx = flow.value.indexOf(item)
    if (idx >= 0) flow.value.splice(idx, 1)
    pushResult({ ...res, need_pii_ack: false, pii_accessed: true })
  } catch (e: any) {
    flow.value.push({ kind: 'sys', tag: t('提示'), text: e?.message || t('隐私确认失败') })
  } finally {
    item.ack_busy = false
  }
}

function barHeight(v: number, series: { value: number }[]) {
  const max = Math.max(...series.map((s) => Math.abs(s.value)), 1)
  return Math.max(4, (Math.abs(v) / max) * 72)
}

function toneClass(tone?: string) {
  if (tone === 'neg') return 'neg'
  if (tone === 'pos') return 'pos'
  if (tone === 'warn') return 'warn'
  return ''
}
</script>

<template>
  <div class="page ask-page">
    <AnalyticsOpsNav />

    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-5 gap-4">
      <header class="page-head" style="margin-bottom: 0">
        <h1>{{ t('AI 问数') }}</h1>
      </header>
      <div class="flex flex-wrap items-center gap-2">
        <div class="seg" role="tablist" :aria-label="t('时间范围')">
          <button
            v-for="p in PERIODS"
            :key="p"
            type="button"
            :class="{ on: period === p }"
            @click="period = p"
          >
            {{ t(p) }}
          </button>
        </div>
        <div class="seg" role="tablist" :aria-label="t('对比基准')">
          <button type="button" :class="{ on: baseline === '同比' }" @click="baseline = '同比'">
            {{ t('同比') }}
          </button>
          <button type="button" :class="{ on: baseline === '环比' }" @click="baseline = '环比'">
            {{ t('环比') }}
          </button>
        </div>
      </div>
    </div>

    <div class="workspace">
      <div class="workspace-top">
        <div class="hint-row">
          <span class="material-symbols-outlined text-[16px] text-secondary">lightbulb</span>
          <span class="font-label-lg text-label-lg text-secondary">{{
            t('常见问题，点一下即可提问')
          }}</span>
        </div>
        <div class="chips">
          <button
            v-for="p in presets"
            :key="p.intent_id + p.question"
            type="button"
            class="chip"
            :disabled="busy"
            @click="ask(p.question)"
          >
            <span class="material-symbols-outlined text-[15px] text-tertiary">chat_bubble</span>
            {{ t(p.question) }}
          </button>
        </div>

        <details v-if="glossary.length" class="glossary">
          <summary>
            <span class="material-symbols-outlined text-[16px]">menu_book</span>
            {{ t('业务术语小词典（') }}{{ glossary.length }}）
          </summary>
          <div class="glossary-body">
            <div v-for="g in glossary" :key="g.standard_term" class="g-row">
              <div class="g-term">
                <strong>{{ t(g.aliases?.[0] || g.standard_term) }}</strong>
                <span v-if="g.unit" class="g-unit">{{ t(g.unit) }}</span>
                <span v-if="g.domain" class="g-dom">{{ t(g.domain) }}</span>
              </div>
              <div class="g-alias">
                {{ t('又称：')
                }}{{
                  (g.aliases || [])
                    .slice(0, 5)
                    .map((a) => t(a))
                    .join(' / ')
                }}
              </div>
              <div v-if="g.definition" class="g-def">{{ t('口径：') }}{{ t(g.definition) }}</div>
            </div>
          </div>
        </details>
      </div>

      <div ref="flowEl" class="flow">
        <template v-for="(item, i) in flow" :key="i">
          <div v-if="item.kind === 'user'" class="msg msg-user">
            <div class="avatar av-user">
              <span class="material-symbols-outlined">person</span>
            </div>
            <div class="bubble bubble-user">
              <p class="text-body-md">{{ item.text }}</p>
            </div>
          </div>

          <div
            v-else-if="item.kind === 'sys' || item.kind === 'thinking' || item.kind === 'stream'"
            class="msg"
          >
            <div class="avatar av-ai">
              <span class="material-symbols-outlined">smart_toy</span>
            </div>
            <div class="bubble bubble-ai">
              <div class="bubble-meta">
                <span>{{
                  item.kind === 'thinking'
                    ? t('进度')
                    : item.kind === 'stream'
                      ? item.tag
                      : t(item.tag || 'AI 问数')
                }}</span>
                <span v-if="item.kind === 'stream'">{{ item.done ? t('完成') : t('生成中') }}</span>
              </div>
              <p v-if="item.kind === 'sys'" class="text-body-md text-on-surface">{{ item.text }}</p>
              <div v-else-if="item.kind === 'thinking'" class="thinking">
                {{ item.text }}
                <span class="dot" /><span class="dot" /><span class="dot" />
              </div>
              <pre v-else class="stream-text">{{ item.text || '…' }}</pre>
            </div>
          </div>

          <div v-else-if="item.kind === 'decompose'" class="msg">
            <div class="avatar av-ai">
              <span class="material-symbols-outlined">smart_toy</span>
            </div>
            <div class="bubble bubble-ai card-insight">
              <div class="insight-title">
                <span class="material-symbols-outlined text-[16px]">account_tree</span>
                {{ t('已理解你的问题') }}
              </div>
              <div v-for="p in item.pipeline" :key="p.step" class="pipe-step">
                <span class="pipe-n">{{ p.step }}</span>
                <div>
                  <div class="pipe-h">{{ t(p.title) }}</div>
                  <div class="pipe-d">{{ t(p.detail) }}</div>
                </div>
              </div>
              <p class="confirm-q">{{ t(item.prompt) }}</p>
              <div class="opts">
                <button type="button" class="btn-main" @click="onDecomposeConfirm(item)">
                  {{ t('是的，去查') }}
                </button>
                <button type="button" class="btn-ghost" @click="flow.splice(flow.indexOf(item), 1)">
                  {{ t('不是，重新问') }}
                </button>
              </div>
            </div>
          </div>

          <div v-else-if="item.kind === 'clarify'" class="msg">
            <div class="avatar av-ai">
              <span class="material-symbols-outlined">smart_toy</span>
            </div>
            <div class="bubble bubble-ai card-insight">
              <p class="confirm-q">{{ t(item.prompt) }}</p>
              <div class="opts">
                <button
                  v-for="(o, oi) in item.options"
                  :key="oi"
                  type="button"
                  class="btn-main"
                  @click="onClarifyOption(item, o)"
                >
                  {{ t(o.label) }}
                </button>
                <button
                  v-for="(pr, pi) in item.presets || []"
                  :key="'p' + pi"
                  type="button"
                  class="btn-ghost"
                  @click="onClarifyOption(item, { label: pr.question, value: pr.question })"
                >
                  {{ pr.question }}
                </button>
                <button v-if="item.ghost" type="button" class="btn-ghost" @click="onGhost(item)">
                  {{ item.ghost.label }}
                </button>
              </div>
            </div>
          </div>

          <div v-else-if="item.kind === 'result'" class="msg">
            <div class="avatar av-ai">
              <span class="material-symbols-outlined">smart_toy</span>
            </div>
            <div class="bubble bubble-ai card-insight result-card">
              <div class="insight-title">
                <span class="material-symbols-outlined text-[16px]">analytics</span>
                {{ item.intent_label }}
                <span v-if="item.answer_source === 'llm' && item.model_meta" class="pill model">{{
                  item.model_meta
                }}</span>
                <span v-else-if="item.answer_source === 'unavailable'" class="pill conf">{{
                  t('AI 暂不可用')
                }}</span>
                <span
                  v-else-if="item.answer_source && item.answer_source !== 'llm'"
                  class="pill conf"
                  >{{ t('规则查询') }}</span
                >
                <span v-if="item.answer_source === 'llm' && item.confidence" class="pill conf">{{
                  confidenceLabel(item.confidence)
                }}</span>
                <span v-if="item.pii_level && item.pii_level !== 'none'" class="pill pii">{{
                  t('隐私脱敏')
                }}</span>
              </div>
              <p v-if="item.answer_source === 'unavailable' && !item.summary" class="summary">
                {{ t('未能调用大模型生成解读。下面是本次查询到的数据，不是 AI 结论。') }}
              </p>
              <p v-else class="summary">{{ t(item.summary) }}</p>
              <ul v-if="item.key_points?.length" class="kps">
                <li v-for="(kp, ki) in item.key_points" :key="ki">{{ t(kp) }}</li>
              </ul>
              <div v-if="item.tips?.length" class="tip-cards">
                <div v-for="(tip, ti) in item.tips" :key="tip.id || ti" class="tip-card">
                  <div class="tip-name">{{ t(tip.name) }}</div>
                  <p v-if="tip.desc" class="tip-desc">{{ t(tip.desc) }}</p>
                  <div v-if="tip.expected_impact" class="tip-impact">
                    {{ t(tip.expected_impact) }}
                  </div>
                </div>
              </div>
              <div v-if="item.rows?.length && !item.tips?.length" class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>{{ t('维度') }}</th>
                      <th>{{ t('数值') }}{{ item.unit ? `(${item.unit})` : '' }}</th>
                      <th>{{ t('说明') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(r, ri) in item.rows" :key="ri">
                      <td>
                        <span v-if="r.guest_id" class="gid">{{ r.guest_id }}</span>
                        {{ r.guest_name || t(r.label) }}
                      </td>
                      <td :class="toneClass(r.tone)">{{ r.value }}</td>
                      <td class="note">{{ r.note ? t(r.note) : '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-if="item.series?.length" class="chart">
                <div class="bars">
                  <div v-for="(s, si) in item.series" :key="si" class="bar-col">
                    <div
                      class="bar"
                      :class="{ neg: s.value < 0 }"
                      :style="{ height: barHeight(s.value, item.series) + 'px' }"
                    />
                    <span class="bar-lbl">{{ String(s.name).slice(0, 4) }}</span>
                  </div>
                </div>
              </div>
              <div v-if="item.need_pii_ack" class="pii-ack">
                <p class="pii-warn">
                  {{
                    t(
                      '以下为可识别个人客户信息，依据《个人信息保护法》需二次确认。请确认你的管理者身份后查看明细。',
                    )
                  }}
                </p>
                <div class="pii-row">
                  <label>
                    {{ t('工号') }}
                    <input
                      v-model="item.ack_by"
                      :disabled="!item.can_ack_pii || item.ack_busy"
                      :placeholder="t('请输入工号')"
                    />
                  </label>
                  <button
                    type="button"
                    class="btn-main danger"
                    :disabled="!item.can_ack_pii || item.ack_busy"
                    @click="onPiiAck(item)"
                  >
                    {{ item.can_ack_pii ? t('我确认查看客户明细') : t('无权限') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div class="composer">
        <div class="composer-box" :class="{ disabled: busy }">
          <input
            v-model="input"
            :disabled="busy"
            class="composer-input"
            :placeholder="t('输入问题，例如：累计消费最高的前 5 个客人是谁')"
            @keyup.enter="ask(input)"
          />
          <button
            type="button"
            class="send-btn"
            :disabled="busy || !input.trim()"
            :aria-label="t('发送')"
            @click="ask(input)"
          >
            <span class="material-symbols-outlined">send</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ask-page {
  padding-bottom: 2.5rem;
}
.seg {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  background: #f3f4f6;
  border-radius: 12px;
}
.seg button {
  border: none;
  background: transparent;
  border-radius: 9px;
  padding: 8px 12px;
  font-size: 12.5px;
  font-weight: 600;
  color: #5b616e;
  cursor: pointer;
  font-family: inherit;
}
.seg button:hover {
  background: #fff;
  color: #1f2329;
}
.seg button.on {
  background: #1f2329;
  color: #fff;
}

.workspace {
  display: flex;
  flex-direction: column;
  background: var(--surface-container-lowest, #fffbfe);
  border: 1px solid var(--outline-variant, #cac4d0);
  border-radius: 0.85rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  overflow: hidden;
  min-height: 560px;
}
.workspace-top {
  padding: 1rem 1.1rem 0.75rem;
  border-bottom: 1px solid color-mix(in srgb, var(--outline-variant) 55%, transparent);
  background: var(--surface-container-lowest, #fff);
}
.hint-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--outline-variant, #cac4d0);
  background: var(--surface-container-low, #f7f2fa);
  color: var(--on-surface-variant, #49454f);
  border-radius: 999px;
  padding: 7px 12px;
  font-size: 12.5px;
  font-weight: 550;
  cursor: pointer;
  font-family: inherit;
  transition:
    background 0.15s,
    border-color 0.15s,
    color 0.15s;
}
.chip:hover:not(:disabled) {
  background: var(--surface-container, #f3edf7);
  color: var(--on-surface, #1c1b1f);
  border-color: color-mix(in srgb, var(--primary) 35%, var(--outline-variant));
}
.chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.glossary {
  margin-top: 12px;
  border: 1px solid var(--outline-variant);
  border-radius: 10px;
  padding: 8px 12px;
  background: var(--surface, #fef7ff);
  font-size: 12px;
}
.glossary summary {
  cursor: pointer;
  font-weight: 650;
  color: var(--on-surface);
  list-style: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.glossary summary::-webkit-details-marker {
  display: none;
}
.glossary-body {
  margin-top: 10px;
  display: grid;
  gap: 10px;
  max-height: 200px;
  overflow: auto;
}
.g-term {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.g-unit,
.g-dom {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--surface-container-high, #ece6f0);
  color: var(--secondary, #625b71);
}
.g-alias,
.g-def {
  color: var(--on-surface-variant);
  margin-top: 2px;
  line-height: 1.45;
}

.flow {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  overflow-y: auto;
  max-height: calc(100vh - 420px);
  min-height: 300px;
  padding: 1.25rem 1.1rem;
  background: var(--surface-bright, #fef7ff);
}
.msg {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  max-width: 920px;
}
.msg-user {
  flex-direction: row-reverse;
  align-self: flex-end;
  margin-left: auto;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.avatar .material-symbols-outlined {
  font-size: 18px;
}
.av-ai {
  background: var(--tertiary-container, #ffd8e4);
  color: var(--on-tertiary-container, #31111d);
}
.av-user {
  background: var(--primary-container, #eaddff);
  color: var(--on-primary-container, #21005d);
}
.bubble {
  max-width: min(720px, 100%);
  padding: 14px 16px;
  border-radius: 16px;
  line-height: 1.55;
}
.bubble-user {
  background: var(--primary);
  color: var(--on-primary, #fff);
  border-top-right-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.bubble-ai {
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant);
  border-top-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  color: var(--on-surface);
}
.bubble-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 650;
  color: var(--tertiary, #7d5260);
}
.card-insight {
  border-left: 2px solid var(--tertiary, #7d5260);
}
.insight-title {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 700;
  color: var(--tertiary, #7d5260);
}
.pipe-step {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}
.pipe-n {
  flex: 0 0 22px;
  height: 22px;
  border-radius: 50%;
  background: #1f2329;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.pipe-h {
  font-size: 12.5px;
  font-weight: 650;
  color: var(--on-surface);
}
.pipe-d {
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.confirm-q {
  margin: 10px 0 8px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--on-surface);
  line-height: 1.5;
}
.opts {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.btn-main,
.btn-ghost {
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 12.5px;
  font-weight: 650;
  cursor: pointer;
  font-family: inherit;
  transition:
    background 0.15s,
    color 0.15s;
}
.btn-main {
  border: none;
  background: #1f2329;
  color: #fff;
}
.btn-main:hover:not(:disabled) {
  background: #111827;
}
.btn-main:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn-main.danger {
  background: #b42318;
}
.btn-main.danger:hover:not(:disabled) {
  background: #912018;
}
.btn-ghost {
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest, #fff);
  color: var(--on-surface-variant);
}
.btn-ghost:hover {
  background: var(--surface-container-low, #f7f2fa);
  color: var(--on-surface);
}

.summary {
  margin: 0 0 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--surface-container-low, #f7f2fa);
  border: 1px solid color-mix(in srgb, var(--outline-variant) 70%, transparent);
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--on-surface);
}
.kps {
  margin: 0 0 10px;
  padding-left: 18px;
  font-size: 13px;
  color: var(--on-surface-variant);
  line-height: 1.55;
}
.tip-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 8px 0;
}
.tip-card {
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 12px 14px;
  background: var(--surface, #fef7ff);
}
.tip-name {
  font-weight: 700;
  font-size: 13px;
}
.tip-desc {
  margin: 4px 0 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--on-surface-variant);
}
.tip-impact {
  margin-top: 6px;
  font-size: 12px;
  font-weight: 650;
  color: var(--primary);
}
.table-wrap {
  overflow-x: auto;
  margin: 8px 0;
  border: 1px solid var(--outline-variant);
  border-radius: 10px;
}
.table-wrap table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.table-wrap th,
.table-wrap td {
  padding: 9px 12px;
  text-align: left;
  border-bottom: 1px solid color-mix(in srgb, var(--outline-variant) 65%, transparent);
}
.table-wrap th {
  background: var(--surface-container-low, #f7f2fa);
  color: var(--on-surface-variant);
  font-weight: 650;
  font-size: 12px;
}
.table-wrap tr:last-child td {
  border-bottom: none;
}
.table-wrap .note {
  color: var(--on-surface-variant);
}
.pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 650;
  background: var(--surface-container-high, #ece6f0);
  color: var(--secondary, #625b71);
  margin-left: 4px;
}
.pill.pii {
  background: color-mix(in srgb, #b42318 12%, #fff);
  color: #b42318;
}
.pill.model {
  background: color-mix(in srgb, #3730a3 10%, #fff);
  color: #3730a3;
  font-variant-numeric: tabular-nums;
}
.gid {
  display: inline-block;
  font-size: 10px;
  font-family: ui-monospace, monospace;
  color: var(--on-surface-variant);
  margin-right: 4px;
}
.pii-ack {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid color-mix(in srgb, #b42318 30%, var(--outline-variant));
  border-radius: 12px;
  background: color-mix(in srgb, #b42318 5%, #fff);
}
.pii-warn {
  margin: 0 0 10px;
  font-size: 12.5px;
  color: #b42318;
  line-height: 1.45;
}
.pii-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-end;
}
.pii-row label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.pii-row input {
  min-width: 140px;
  padding: 8px 10px;
  border: 1px solid var(--outline-variant);
  border-radius: 10px;
  font-family: inherit;
  background: #fff;
}
.neg {
  color: #b42318;
  font-weight: 650;
}
.pos {
  color: #067647;
  font-weight: 650;
}
.warn {
  color: #b54708;
  font-weight: 650;
}
.chart {
  margin: 12px 0 4px;
}
.bars {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 96px;
  border-bottom: 1px solid var(--outline-variant);
  padding: 0 4px;
}
.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  min-width: 0;
}
.bar {
  width: 70%;
  max-width: 36px;
  background: var(--primary);
  border-radius: 4px 4px 0 0;
  opacity: 0.85;
}
.bar.neg {
  background: #b42318;
}
.bar-lbl {
  font-size: 10px;
  color: var(--on-surface-variant);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
.thinking {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--on-surface-variant);
  font-size: 13px;
}
.stream-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
  color: var(--on-surface);
  max-height: 220px;
  overflow-y: auto;
}
.dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--primary);
  animation: blink 1s infinite;
}
.dot:nth-child(2) {
  animation-delay: 0.2s;
}
.dot:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes blink {
  0%,
  100% {
    opacity: 0.2;
  }
  50% {
    opacity: 1;
  }
}

.composer {
  padding: 12px 14px 14px;
  border-top: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest, #fff);
}
.composer-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface-container-low, #f7f2fa);
  border: 1px solid var(--outline-variant);
  border-radius: 16px;
  padding: 6px 8px 6px 14px;
  transition: border-color 0.15s;
}
.composer-box:focus-within {
  border-color: var(--primary);
}
.composer-box.disabled {
  opacity: 0.7;
}
.composer-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
  font-family: inherit;
  color: var(--on-surface);
  min-height: 36px;
}
.composer-input::placeholder {
  color: var(--on-surface-variant);
}
.send-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 999px;
  background: var(--primary);
  color: var(--on-primary, #fff);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}
.send-btn:hover:not(:disabled) {
  filter: brightness(0.95);
}
.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
@media (max-width: 720px) {
  .flow {
    max-height: calc(100vh - 480px);
  }
  .bubble {
    max-width: 100%;
  }
}
</style>
