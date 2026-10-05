<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'
import { commercialEnabled } from '../lib/branding'

/**
 * 经营分析 AI 行动卡 —— 简报 / 建议 / 置信度 / 一键执行
 */
import { ref, computed, watch } from 'vue'
import { formatAiModelMeta } from '../lib/aiModelMeta'
import { confidenceLabel } from '../lib/aiConfidence'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { toast } from '../lib/ui'

const props = withDefaults(
  defineProps<{
    /** health | channel | attribution | all */
    module?: string
    /** 紧凑模式（嵌入子页） */
    compact?: boolean
    /** 是否展示简报头 */
    showBriefing?: boolean
  }>(),
  {
    module: 'all',
    compact: false,
    showBriefing: true,
  },
)

const emit = defineEmits<{
  loaded: [payload: any]
}>()

const router = useRouter()
const loading = ref(false)
const executing = ref<string | null>(null)
const payload = ref<any>(null)
const draftOpen = ref(false)
const draftText = ref('')
const draftTitle = ref('')
const hasRun = computed(() => !!payload.value)

const briefing = computed(() => payload.value?.briefing || null)
const sourceLabel = computed(() => {
  const s = payload.value?.source
  if (s === 'llm') return t('AI 建议')
  if (s === 'unavailable' || s === 'fallback' || s === 'rules_disabled') return t('AI 暂不可用')
  return s || '—'
})

const actions = computed(() => {
  if (payload.value?.source !== 'llm') return []
  const list = Array.isArray(payload.value?.actions) ? payload.value.actions : []
  if (props.module === 'all') return list
  return list.filter((a: any) => a.module === props.module)
})

const confCls: Record<string, string> = {
  high: 'conf-high',
  medium: 'conf-mid',
  low: 'conf-low',
}
const confText = (c: string) => confidenceLabel(c)

async function load() {
  if (loading.value) return
  loading.value = true
  try {
    payload.value = await api.analyticsAiActions(hotelStore.hotelId)
    emit('loaded', payload.value)
  } catch (e: any) {
    payload.value = null
    toast(e?.message || t('AI 行动加载失败'))
  } finally {
    loading.value = false
  }
}

async function runAction(a: any) {
  if (!a || executing.value) return
  executing.value = a.id
  try {
    const res = await api.analyticsAiExecute(hotelStore.hotelId, a)
    toast(res?.message || t('已执行'))
    if (
      res?.draft_message &&
      (a.action_type === 'remind_pay' || a.action_type === 'prep_collect')
    ) {
      draftText.value = res.draft_message
      draftTitle.value = a.action_type === 'prep_collect' ? t('前台交接草稿') : t('预付提醒话术')
      draftOpen.value = true
    }
    // 写操作为主：不自动跳转，详情按钮可另行打开
  } catch (e: any) {
    toast(e?.message || t('执行失败'))
  } finally {
    executing.value = null
  }
}

function goLink(a: any) {
  const link = a.deep_link
  if (link) router.push(link)
}

async function copyDraft() {
  try {
    await navigator.clipboard.writeText(draftText.value)
    toast(t('已复制'))
  } catch {
    toast(t('复制失败，请手动选择'), false)
  }
  draftOpen.value = false
}

/** 切换酒店时清空结果，需用户再次主动生成 */
watch(
  () => hotelStore.hotelId,
  () => {
    payload.value = null
    emit('loaded', null)
  },
)

defineExpose({ reload: load, payload })
</script>

<template>
  <div v-if="commercialEnabled()" class="ai-hub" :class="{ compact }">
    <!-- 未触发：仅展示入口 -->
    <div v-if="!hasRun && !loading" class="idle">
      <div class="idle-copy">
        <span class="material-symbols-outlined spark">auto_awesome</span>
        <div>
          <h3>{{ t('AI 行动中枢') }}</h3>
        </div>
      </div>
      <button type="button" class="btn primary generate" @click="load">
        {{ t('AI生成今日行动建议') }}
      </button>
    </div>

    <!-- 生成中 -->
    <div v-else-if="loading" class="idle loading-idle">
      <div class="idle-copy">
        <span class="material-symbols-outlined spark spin">progress_activity</span>
        <div>
          <h3>{{ t('AI 正在研判…') }}</h3>
          <p>{{ t('本地模型分析中，约需 20～40 秒，请稍候。') }}</p>
        </div>
      </div>
    </div>

    <!-- 已生成 -->
    <template v-else>
      <div v-if="showBriefing" class="brief">
        <div class="brief-top">
          <span class="material-symbols-outlined spark">auto_awesome</span>
          <div class="brief-titles">
            <h3>{{ briefing?.headline || t('AI 行动中枢') }}</h3>
            <p class="meta">
              <span>{{ sourceLabel }}</span>
              <span v-if="formatAiModelMeta(payload)" class="conf">{{
                formatAiModelMeta(payload)
              }}</span>
              <span
                v-if="briefing?.confidence"
                class="conf"
                :class="confCls[briefing.confidence]"
                >{{ confText(briefing.confidence) }}</span
              >
            </p>
          </div>
          <button type="button" class="refresh" :disabled="loading" @click="load">
            {{ t('重新生成') }}
          </button>
        </div>
        <p v-if="briefing?.summary && payload?.source === 'llm'" class="summary">
          {{ briefing.summary }}
        </p>
        <p v-if="briefing?.confidence_note && payload?.source === 'llm'" class="note">
          {{ briefing.confidence_note }}
        </p>
        <p v-if="payload?.source !== 'llm'" class="err">
          {{ t('未能调用大模型，未生成 AI 建议。') }}
        </p>
        <p v-else-if="payload?.llm_error" class="err">{{ t(payload.llm_error) }}</p>
      </div>

      <div v-if="!showBriefing" class="compact-bar">
        <span class="compact-label">{{ t('本模块 AI 建议') }}</span>
        <button type="button" class="refresh" :disabled="loading" @click="load">
          {{ t('重新生成') }}
        </button>
      </div>

      <div v-if="!actions.length" class="empty">{{ t('暂无该模块的可执行建议') }}</div>

      <div class="cards">
        <article v-for="a in actions" :key="a.id" class="card" :data-module="a.module">
          <header>
            <span class="mod">{{
              a.module === 'health'
                ? t('订单健康')
                : a.module === 'channel'
                  ? t('渠道洞察')
                  : t('营销归因')
            }}</span>
            <span class="conf" :class="confCls[a.confidence]">{{ confText(a.confidence) }}</span>
          </header>
          <h4>{{ a.title }}</h4>
          <p class="body">{{ a.body }}</p>
          <p class="sug">
            <strong>{{ t('建议：') }}</strong
            >{{ a.suggestion }}
          </p>
          <p class="note">
            {{ a.confidence_note }}
            <template v-if="a.sample_size"> · {{ t('样本 {n}', { n: a.sample_size }) }}</template>
          </p>
          <footer>
            <button type="button" class="btn primary" :disabled="!!executing" @click="runAction(a)">
              {{
                executing === a.id ? t('执行中…') : a.action_label ? t(a.action_label) : t('执行')
              }}
            </button>
            <button v-if="a.deep_link" type="button" class="btn ghost" @click="goLink(a)">
              {{ t('详情') }}
            </button>
          </footer>
        </article>
      </div>
    </template>

    <div v-if="draftOpen" class="draft-mask" @click.self="draftOpen = false">
      <div class="draft-box">
        <h4>{{ draftTitle }}</h4>
        <textarea v-model="draftText" rows="5" />
        <div class="draft-actions">
          <button type="button" class="btn primary" @click="copyDraft">{{ t('复制话术') }}</button>
          <button type="button" class="btn ghost" @click="draftOpen = false">
            {{ t('关闭') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-hub {
  margin-bottom: 1rem;
}
.idle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  background: #f3e8f9;
  border: 1px solid rgba(140, 51, 179, 0.28);
  border-radius: 0.85rem;
  padding: 1rem 1.1rem;
  margin-bottom: 0.85rem;
}
.idle-copy {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  flex: 1;
  min-width: 200px;
}
.idle-copy h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #1c1b1f;
}
.idle-copy p {
  margin: 0.3rem 0 0;
  font-size: 0.8rem;
  color: #79747e;
  line-height: 1.45;
}
.generate {
  flex-shrink: 0;
}
.loading-idle {
  border-style: solid;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.compact-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}
.compact-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: #49454f;
}
.brief {
  background: #f3e8f9;
  border: 1px solid rgba(140, 51, 179, 0.28);
  border-radius: 0.85rem;
  padding: 1rem 1.1rem;
  margin-bottom: 0.85rem;
}
.brief-top {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
}
.spark {
  color: #8c33b3;
  font-variation-settings: 'FILL' 1;
}
.brief-titles {
  flex: 1;
  min-width: 0;
}
.brief-titles h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #1c1b1f;
}
.meta {
  margin: 0.25rem 0 0;
  font-size: 0.72rem;
  color: #79747e;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}
.summary {
  margin: 0.65rem 0 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: #49454f;
}
.note {
  margin: 0.35rem 0 0;
  font-size: 0.7rem;
  color: #9a94a0;
}
.err {
  margin: 0.4rem 0 0;
  font-size: 0.72rem;
  color: #ba1a1a;
}
.refresh {
  flex-shrink: 0;
  border: 1px solid #cac4d0;
  background: #fff;
  border-radius: 0.5rem;
  padding: 0.35rem 0.7rem;
  font-size: 0.75rem;
  cursor: pointer;
}
.refresh:disabled {
  opacity: 0.6;
  cursor: wait;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.75rem;
}
.compact .cards {
  grid-template-columns: 1fr;
}
.card {
  border: 1px solid #e7e0ec;
  border-radius: 0.75rem;
  padding: 0.85rem 0.95rem;
  background: #fffbff;
  border-left: 3px solid #005bbf;
}
.card[data-module='channel'] {
  border-left-color: #8c33b3;
}
.card[data-module='attribution'] {
  border-left-color: #d97706;
}
.card header {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}
.mod {
  font-size: 0.65rem;
  font-weight: 700;
  color: #79747e;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.conf {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
}
.conf-high {
  background: rgba(16, 185, 129, 0.15);
  color: #047857;
}
.conf-mid {
  background: rgba(245, 158, 11, 0.18);
  color: #b45309;
}
.conf-low {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}
.card h4 {
  margin: 0 0 0.35rem;
  font-size: 0.9rem;
  font-weight: 700;
  color: #1c1b1f;
}
.body,
.sug {
  margin: 0 0 0.35rem;
  font-size: 0.78rem;
  line-height: 1.45;
  color: #49454f;
}
footer {
  display: flex;
  gap: 0.45rem;
  margin-top: 0.55rem;
}
.btn {
  border-radius: 0.45rem;
  padding: 0.35rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}
.btn.primary {
  background: #005bbf;
  color: #fff;
}
.btn.primary:disabled {
  opacity: 0.55;
  cursor: wait;
}
.btn.ghost {
  background: transparent;
  border-color: #cac4d0;
  color: #49454f;
}
.empty {
  padding: 1rem;
  text-align: center;
  color: #9a94a0;
  font-size: 0.8rem;
}
.draft-mask {
  position: fixed;
  inset: 0;
  background: rgba(28, 27, 31, 0.45);
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
.draft-box {
  background: #fff;
  border-radius: 0.85rem;
  padding: 1.1rem;
  width: min(420px, 100%);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}
.draft-box h4 {
  margin: 0 0 0.65rem;
}
.draft-box textarea {
  width: 100%;
  border: 1px solid #cac4d0;
  border-radius: 0.5rem;
  padding: 0.6rem;
  font-size: 0.85rem;
  resize: vertical;
}
.draft-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
  justify-content: flex-end;
}
</style>
