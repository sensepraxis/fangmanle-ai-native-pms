<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'
import { authHeaders } from '../../lib/api/client'

/**
 * 企微「客户联系 → 聊天工具栏」侧边栏页
 * 管家在与客户 1:1 聊天时点工具栏图标打开 → getContext → sendChatMessage 直发
 */
import { ref, onMounted } from 'vue'
import {
  initWecomSidebarSdk,
  sendWecomChatText,
  isSidebarChatEntry,
  isWecomUa,
  type WecomContext,
} from '../../lib/wecomJssdk'

const loading = ref(true)
const ctx = ref<WecomContext | null>(null)
const guest = ref<any>(null)
const initError = ref('')
const material = ref('')
const draft = ref('')
const generated = ref(false)
const generating = ref(false)
const sending = ref(false)
const hint = ref('')
const error = ref('')
const lastSentDraft = ref('')
const source = ref('')

async function loadGuest(externalUserId: string) {
  const res = await fetch(
    `/api/wecom/sidebar/guest?external_userid=${encodeURIComponent(externalUserId)}`,
    {
      headers: authHeaders(),
    },
  )
  const json = await res.json().catch(() => ({}))
  if (!res.ok || json.ok === false) {
    throw new Error(json.detail || json.message || t('加载客人失败'))
  }
  guest.value = json.data
}

async function bootstrap() {
  loading.value = true
  initError.value = ''
  try {
    if (!isWecomUa()) {
      initError.value = t(
        '请在企业微信中打开：与客户 1:1 聊天 → 点击输入框上方工具栏图标 → 进入「PMS 关怀」',
      )
      return
    }
    ctx.value = await initWecomSidebarSdk()
    const eid = ctx.value.externalUserId
    if (!eid) {
      initError.value = t('未能获取当前聊天客户 ID，请确认从客户 1:1 会话的聊天工具栏打开')
      return
    }
    if (!isSidebarChatEntry(ctx.value.entry)) {
      initError.value = `当前入口为「${ctx.value.entry || '未知'}」，请在客户 1:1 聊天的聊天工具栏中打开本页`
      return
    }
    await loadGuest(eid)
  } catch (e: any) {
    initError.value = e?.message || t('初始化失败')
  } finally {
    loading.value = false
  }
}

async function generateDraft() {
  if (!guest.value?.external_userid || generating.value) return
  const m = material.value.trim()
  if (!m) {
    error.value = t('请先填写关怀素材')
    return
  }
  generating.value = true
  error.value = ''
  try {
    const res = await fetch('/api/v1/wecom/sidebar/care-draft', {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ external_userid: guest.value.external_userid, material: m }),
    })
    const json = await res.json().catch(() => ({}))
    if (!res.ok || json.ok === false) throw new Error(json.detail || '生成失败')
    draft.value = json.data?.content || ''
    generated.value = true
    source.value = [
      t(json.data?.source_cn || json.data?.source || ''),
      json.data?.profile_used && json.data?.profile_summary
        ? t('参考画像：{summary}', { summary: json.data.profile_summary })
        : '',
    ]
      .filter(Boolean)
      .join(' · ')
    hint.value = json.data?.hint || ''
    lastSentDraft.value = ''
  } catch (e: any) {
    error.value = e?.message || t('AI 生成失败')
  } finally {
    generating.value = false
  }
}

async function sendCare() {
  const text = draft.value.trim()
  if (!text || sending.value || !guest.value?.external_userid) return
  sending.value = true
  error.value = ''
  try {
    await sendWecomChatText(text)
    const res = await fetch('/api/v1/wecom/sidebar/care-sent', {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        external_userid: guest.value.external_userid,
        content: text,
        sender_userid: ctx.value?.userId || undefined,
      }),
    })
    const json = await res.json().catch(() => ({}))
    if (!res.ok || json.ok === false) throw new Error(json.detail || '发送记录失败')
    lastSentDraft.value = text
    hint.value = json.data?.hint || '已发送到当前 1:1 会话，可继续编辑后再次发送'
  } catch (e: any) {
    error.value = e?.message || t('发送失败')
  } finally {
    sending.value = false
  }
}

onMounted(bootstrap)
</script>

<template>
  <div class="sidebar-page">
    <header class="head">
      <h1 class="title">{{ t('PMS 关怀') }}</h1>
      <p class="sub">{{ t('聊天工具栏 · 1:1 直发（不走群发助手）') }}</p>
    </header>

    <div v-if="loading" class="state">{{ t('正在连接企微…') }}</div>
    <div v-else-if="initError" class="state error-box">
      <p class="err-title">{{ t('无法使用') }}</p>
      <p class="err-msg">{{ initError }}</p>
      <details class="help">
        <summary>{{ t('什么是「从侧边栏打开」？') }}</summary>
        <ol>
          <li>
            {{ t('打开') }} <strong>{{ t('企业微信') }}</strong
            >{{ t('，进入与某位客户的') }} <strong>{{ t('1:1 私聊') }}</strong>
          </li>
          <li>
            {{ t('在输入框上方找到') }} <strong>{{ t('聊天工具栏') }}</strong
            >{{ t('（需管理员在「客户联系 → 聊天工具栏」配置本页 URL）') }}
          </li>
          <li>
            {{ t('点击') }} <strong>{{ t('PMS 关怀') }}</strong> {{ t('图标 → 右侧滑出本页面') }}
          </li>
          <li>{{ t('填写素材 → AI 生成 → 点击发送，消息会直接进入当前聊天窗口') }}</li>
        </ol>
      </details>
    </div>
    <template v-else-if="guest">
      <section class="guest-card">
        <p class="guest-name">{{ guest.guest_name || t('客人') }}</p>
        <p class="guest-meta">
          {{ t('尾号') }} {{ guest.phone_tail || '—' }} · #{{ guest.guest_id }}
        </p>
        <p v-if="guest.salutation" class="guest-salute">{{ guest.salutation }}</p>
      </section>

      <label class="label" for="sb-material">{{ t('关怀素材') }}</label>
      <textarea
        id="sb-material"
        v-model="material"
        class="textarea"
        rows="3"
        :placeholder="t('例如：感谢领券、提醒入住日期…')"
        :disabled="generating || sending"
      />

      <div class="row">
        <button
          v-if="commercialEnabled()"
          type="button"
          class="btn"
          :disabled="generating || !material.trim()"
          @click="generateDraft"
        >
          {{ generating ? t('生成中…') : generated ? t('AI 重新生成') : t('AI 生成') }}
        </button>
        <span v-if="source" class="src">{{ source }}</span>
      </div>

      <label class="label" for="sb-draft">{{ t('话术（可编辑）') }}</label>
      <textarea
        id="sb-draft"
        v-model="draft"
        class="textarea"
        rows="6"
        :placeholder="t('填写素材后点 AI 生成')"
        :disabled="generating"
      />

      <p v-if="hint" class="hint">{{ hint }}</p>
      <p v-if="error" class="err">{{ error }}</p>

      <button
        type="button"
        class="btn primary send"
        :disabled="sending || !draft.trim()"
        @click="sendCare"
      >
        {{
          sending
            ? t('发送中…')
            : lastSentDraft && lastSentDraft === draft.trim()
              ? t('再次发送')
              : t('发送到当前会话')
        }}
      </button>
    </template>
  </div>
</template>

<style scoped>
.sidebar-page {
  min-height: 100vh;
  max-width: 420px;
  margin: 0 auto;
  padding: 16px;
  background: var(--surface, #f8fafc);
  font-size: 14px;
  color: var(--on-surface, #0f172a);
}
.head {
  margin-bottom: 16px;
}
.title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}
.sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: #64748b;
}
.state {
  padding: 24px 12px;
  text-align: center;
  color: #64748b;
}
.error-box {
  text-align: left;
  background: #fff;
  border: 1px solid #fecaca;
  border-radius: 12px;
  padding: 16px;
}
.err-title {
  margin: 0 0 8px;
  font-weight: 700;
  color: #b91c1c;
}
.err-msg {
  margin: 0 0 12px;
  line-height: 1.5;
}
.help {
  font-size: 12px;
  color: #475569;
}
.help ol {
  margin: 8px 0 0;
  padding-left: 18px;
  line-height: 1.6;
}
.guest-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 14px;
}
.guest-name {
  margin: 0;
  font-weight: 700;
  font-size: 16px;
}
.guest-meta,
.guest-salute {
  margin: 4px 0 0;
  font-size: 12px;
  color: #64748b;
}
.label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
  color: #475569;
}
.textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px;
  font-size: 14px;
  line-height: 1.5;
  resize: vertical;
  margin-bottom: 12px;
  font-family: inherit;
}
.row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn.primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.send {
  width: 100%;
  padding: 12px;
  font-size: 15px;
  font-weight: 600;
  margin-top: 8px;
}
.src {
  font-size: 11px;
  color: #64748b;
}
.hint {
  font-size: 12px;
  color: #059669;
  margin: 0 0 8px;
}
.err {
  font-size: 12px;
  color: #dc2626;
  margin: 0 0 8px;
}
</style>
