<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'
import { commercialEnabled } from '../lib/branding'

/**
 * 通用触发式 AI 叙事面板（narrative_html + actions + 模型标识）。
 * 域入口只传 fetcher / executor，UI 与交互统一。
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { formatAiModelMeta } from '../lib/aiModelMeta'
import { confidenceLabel } from '../lib/aiConfidence'
import { toast } from '../lib/ui'

const props = withDefaults(
  defineProps<{
    title: string
    idle?: string
    runLabel?: string
    rerunLabel?: string
    waitLabel?: string
    compact?: boolean
    resetKey?: string | number
    fetcher: () => Promise<any>
    executor?: (action: Record<string, any>) => Promise<any>
  }>(),
  {
    idle: t('点击后结合当前事实生成解读与可执行建议'),
    runLabel: t('生成 AI 解读'),
    rerunLabel: t('重新解读'),
    waitLabel: t('正在生成解读…'),
    compact: false,
  },
)

const emit = defineEmits<{
  (e: 'result', insight: any): void
}>()

const router = useRouter()
const loading = ref(false)
const insight = ref<any | null>(null)
const error = ref('')
const executing = ref<string | null>(null)

const confText = (c: string) => confidenceLabel(c)

const sourceLabel = computed(() => {
  const s = insight.value?.source
  if (s === 'llm') return t('AI 解读')
  if (s === 'unavailable') return t('AI 暂不可用')
  if (s === 'fallback') return t('AI 暂不可用')
  if (s === 'rules_disabled') return t('AI 暂不可用')
  return ''
})

const modelMeta = computed(() => formatAiModelMeta(insight.value))

watch(
  () => props.resetKey,
  () => {
    insight.value = null
    error.value = ''
  },
)

async function run() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await props.fetcher()
    insight.value = res
    emit('result', res)
  } catch (e: any) {
    insight.value = null
    error.value = e?.message || t('生成失败')
    toast(error.value, false)
  } finally {
    loading.value = false
  }
}

function goPath(path: string) {
  const p = String(path || '').trim()
  if (!p) return
  if (p.startsWith('/')) {
    const [pathname, qs] = p.split('?')
    const query: Record<string, string> = {}
    if (qs) {
      for (const part of qs.split('&')) {
        const [k, v] = part.split('=')
        if (k) query[decodeURIComponent(k)] = decodeURIComponent(v || '')
      }
    }
    router.push({ path: pathname, query })
    return
  }
  router.push(p)
}

async function runAction(a: any) {
  if (!a || executing.value) return
  if (a.action_type === 'open_path' || !props.executor) {
    goPath(a.path || '/')
    return
  }
  executing.value = a.id
  try {
    const res = await props.executor(a)
    toast(res?.message || t('已执行'))
    if (res?.deep_link) goPath(res.deep_link)
  } catch (e: any) {
    toast(e?.message || t('执行失败'), false)
  } finally {
    executing.value = null
  }
}

defineExpose({ run, insight })
</script>

<template>
  <section v-if="commercialEnabled()" class="narrative-ai" :class="{ compact }">
    <div class="ai-head">
      <div class="ai-head-l">
        <span class="ai-mark">AI</span>
        <h3>{{ title }}</h3>
      </div>
      <button type="button" class="ai-run" :disabled="loading" @click="run">
        {{ loading ? t('生成中…') : insight ? rerunLabel : runLabel }}
      </button>
    </div>

    <template v-if="loading">
      <p class="ai-wait">{{ waitLabel }}</p>
    </template>
    <template v-else-if="insight">
      <p class="ai-meta">
        <span>{{ sourceLabel }}</span>
        <span v-if="modelMeta" class="conf-pill mono">{{ modelMeta }}</span>
        <span v-if="insight.confidence && insight.source === 'llm'" class="conf-pill">{{
          confText(insight.confidence)
        }}</span>
        <span v-if="insight.confidence_note && insight.source === 'llm'">
          · {{ insight.confidence_note }}</span
        >
      </p>
      <div v-if="insight.source === 'llm' && insight.reply_draft" class="reply-draft">
        <div class="reply-h">{{ t('建议回复草稿') }}</div>
        <p>{{ insight.reply_draft }}</p>
      </div>
      <div v-if="insight.source === 'llm' && insight.narrative_html" class="ai-insight-body">
        <div v-html="insight.narrative_html" />
      </div>
      <p v-else-if="insight.source !== 'llm'" class="ai-idle">
        {{ t('未能调用大模型生成解读。下面如有事实条目，来自查询数据，不是 AI 结论。') }}
      </p>
      <ul v-if="insight.source !== 'llm' && insight.facts?.length" class="ai-facts">
        <li v-for="(f, i) in insight.facts" :key="i">{{ t(String(f)) }}</li>
      </ul>
      <div v-if="insight.source === 'llm' && insight.actions?.length" class="dx-actions">
        <div class="dx-actions-h">{{ t('可执行建议') }}</div>
        <div class="dx-action-list">
          <article v-for="a in insight.actions" :key="a.id" class="dx-action-card">
            <div class="dx-action-title">{{ a.title || a.action_label }}</div>
            <div v-if="a.body" class="dx-action-body">{{ a.body }}</div>
            <button type="button" class="dx-act" :disabled="!!executing" @click="runAction(a)">
              {{ executing === a.id ? t('执行中…') : a.action_label || t('执行') }}
            </button>
          </article>
        </div>
      </div>
      <p v-if="insight.llm_error && insight.source !== 'llm'" class="ai-soft-err">
        {{ t(insight.llm_error) }}
      </p>
    </template>
    <template v-else-if="idle">
      <p class="ai-idle">{{ idle }}</p>
    </template>
    <p v-if="error" class="ai-err">{{ error }}</p>
  </section>
</template>

<style scoped>
.narrative-ai {
  border: 1px solid var(--line, #e2e8f0);
  border-radius: 12px;
  padding: 14px 16px;
  background: #fff;
  margin: 12px 0;
}
.narrative-ai.compact {
  padding: 12px 14px;
  margin: 8px 0;
}
.ai-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}
.ai-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
}
.ai-head-l {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-mark {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--brand, #2563eb);
  background: var(--soft, #eff6ff);
  border: 1px solid #bfd4f5;
  border-radius: 4px;
  padding: 1px 6px;
}
.ai-run {
  border: none;
  background: var(--brand, #2563eb);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 14px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}
.ai-run:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.ai-wait,
.ai-idle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--ink3, #64748b);
}
.ai-facts {
  margin: 8px 0 0;
  padding-left: 18px;
  font-size: 13px;
  color: #1e293b;
  line-height: 1.5;
}
.ai-meta {
  font-size: 11px;
  color: var(--ink3, #64748b);
  margin: 0 0 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.conf-pill {
  background: #e2e8f0;
  border-radius: 4px;
  padding: 1px 6px;
  font-weight: 700;
  color: #475569;
}
.conf-pill.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-weight: 600;
}
.reply-draft {
  border: 1px dashed #bfd4f5;
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.reply-h {
  font-size: 11px;
  font-weight: 800;
  color: var(--brand, #2563eb);
  margin-bottom: 4px;
}
.reply-draft p {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: #1e293b;
}
.ai-err {
  font-size: 12px;
  color: #dc2626;
  background: #fef2f2;
  border-radius: 6px;
  padding: 8px 10px;
  margin-top: 10px;
}
.ai-soft-err {
  font-size: 12px;
  color: var(--ink3, #64748b);
  margin: 8px 0 0;
}
.ai-insight-body {
  margin-bottom: 12px;
}
.ai-insight-body :deep(.ai-insight) {
  display: grid;
  gap: 10px;
}
@media (min-width: 720px) {
  .ai-insight-body :deep(.ai-insight) {
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
}
.ai-insight-body :deep(.ai-insight-sec) {
  border-radius: 10px;
  padding: 12px 14px;
  border: 1px solid var(--line, #e2e8f0);
  background: #f8fafc;
}
.ai-insight-body :deep(.ai-insight-h) {
  font-size: 12px;
  font-weight: 800;
  color: var(--brand, #2563eb);
  margin-bottom: 8px;
}
.ai-insight-body :deep(ul) {
  margin: 0;
  padding-left: 18px;
}
.ai-insight-body :deep(li) {
  font-size: 13px;
  line-height: 1.5;
  color: #1e293b;
  margin-bottom: 4px;
}
.dx-actions {
  margin-top: 4px;
}
.dx-actions-h {
  font-size: 12px;
  font-weight: 800;
  color: var(--ink2, #334155);
  margin-bottom: 8px;
}
.dx-action-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.dx-action-card {
  border: 1px solid var(--line, #e2e8f0);
  border-radius: 10px;
  padding: 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dx-action-title {
  font-size: 13px;
  font-weight: 700;
}
.dx-action-body {
  font-size: 12px;
  color: var(--ink2, #334155);
  line-height: 1.45;
  flex: 1;
}
.dx-act {
  align-self: flex-start;
  margin-top: 4px;
  border: 1px solid #bfd4f5;
  background: var(--soft, #eff6ff);
  color: var(--brand, #2563eb);
  font-size: 12px;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  white-space: normal;
  text-align: left;
  line-height: 1.3;
  max-width: 100%;
}
.dx-act:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
