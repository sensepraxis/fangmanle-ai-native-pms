<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * AI 多语言翻译聊天 —— 对照原型 room-302-john-doe.html
 * 数据：GET /api/housekeeping/ai-assistant（service_requests + 在住客史）
 */
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import HousekeepingFlowNav from '../../components/HousekeepingFlowNav.vue'

const FALLBACK = {
  room: '302',
  guest: 'John Doe',
  messages: [
    {
      role: 'guest',
      text: 'Hi, the air conditioning is making a loud noise. Can someone check it?',
      time: '14:02',
    },
    { type: 'translation', text: t('您好，空调噪音很大，能否派人检查一下？') },
  ],
  smartReplies: [
    { text: t('已安排工程部 15 分钟内上门'), tertiary: true },
    { text: t('为您升级至安静楼层'), tertiary: true },
    { text: t('赠送迷你吧券致歉'), tertiary: false },
  ],
  sentiment: {
    label: t('关注'),
    desc: t('暂无开放客需，展示默认会话。'),
  },
  confidence: {
    pct: 90,
    text: t('高置信'),
    desc: t('会话由客需工单分拣生成，不是大模型对话。'),
  },
  actions: [
    { label: t('创建工程工单'), sub: t('优先处理'), icon: 'build', tone: 'primary' },
    { label: t('发起换房评估'), sub: t('查空房'), icon: 'swap_horiz', tone: 'tertiary' },
    {
      label: t('经理介入'),
      sub: t('转交前台/值班经理'),
      icon: 'supervisor_account',
      tone: 'error',
    },
  ],
}

const data = ref<any>({ ...FALLBACK })
const draft = ref('')
const autoTranslate = ref(true)

const initials = computed(() => {
  const g = String(data.value.guest || 'JD')
  const parts = g.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return g.slice(0, 2).toUpperCase()
})

function toChatMessages(raw: any[], suggestion?: string) {
  const out: any[] = []
  for (const m of raw || []) {
    if (m.role === 'guest') {
      out.push({ role: 'guest', text: m.text, time: m.time })
      // 中文客需：附一条「译文」示意（内容即原文）
      if (m.text && /[\u4e00-\u9fff]/.test(m.text)) {
        out.push({ type: 'translation', text: m.text })
      } else if (m.text) {
        out.push({ type: 'translation', text: m.text })
      }
    } else if ((m.role === 'ai' || m.role === 'desk') && m.text) {
      out.push({ role: 'guest', text: m.text, time: m.time }) // 模板仅渲染 guest + translation；AI 回复放侧栏建议
    }
  }
  if (!out.length && suggestion) {
    out.push(
      { role: 'guest', text: suggestion, time: '—' },
      { type: 'translation', text: suggestion },
    )
  }
  return out.length ? out : FALLBACK.messages
}

function mapActions(actions: { label: string }[] | undefined, content: string) {
  if (!actions?.length) return FALLBACK.actions
  const icons = ['build', 'swap_horiz', 'supervisor_account', 'room_service']
  const tones = ['primary', 'tertiary', 'error', 'primary']
  return actions.slice(0, 3).map((a, i) => ({
    label: a.label,
    sub: content.slice(0, 16) || t('建议执行'),
    icon: icons[i % icons.length],
    tone: tones[i % tones.length],
  }))
}

async function load() {
  try {
    const raw = await api.housekeepingAiAssistant(hotelStore.hotelId)
    const list = raw?.conversations || []
    const activeId = raw?.active_id
    const conv =
      list.find((c: any) => c.id === activeId) || list.find((c: any) => c.open) || list[0]

    if (!conv) {
      data.value = { ...FALLBACK }
      return
    }

    const content = conv.preview || ''
    const conf = Math.round(Number(conv.confidence || 94))
    data.value = {
      room: conv.room || FALLBACK.room,
      guest: conv.guest || conv.context?.guest || FALLBACK.guest,
      messages: toChatMessages(conv.messages, content),
      smartReplies: [
        { text: conv.suggestion || t('好的，我马上为您安排'), tertiary: true },
        { text: t('已同步前台与工程'), tertiary: true },
        { text: t('需要我帮您升级房间吗？'), tertiary: false },
      ].filter((x, i, arr) => arr.findIndex((y) => y.text === x.text) === i),
      sentiment: {
        label:
          conv.priority || content.includes('空调') || content.includes('冷')
            ? t('焦虑')
            : conv.open
              ? t('关注')
              : t('平稳'),
        desc: conv.open
          ? `未结客需「${content}」。${conv.context?.tags ? `客史标签：${conv.context.tags}` : t('建议按 SLA 响应。')}`
          : t('该会话已解决，可回看话术与闭环记录。'),
      },
      confidence: {
        pct: conf,
        text: conf >= 90 ? t('高置信') : conf >= 70 ? t('中置信') : t('待复核'),
        desc: `渠道 ${conv.channel || '—'} · ${conv.stay_label || ''}`.trim(),
      },
      actions: mapActions(conv.actions, content),
    }
    if (conv.suggestion) draft.value = ''
  } catch {
    data.value = { ...FALLBACK }
  }
}

function applyReply(text: string) {
  draft.value = text
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page ml-page">
    <!-- 动线入口（原型无此条；保留以便客需链跳转） -->
    <div class="flow-bar">
      <HousekeepingFlowNav mode="guest" />
    </div>

    <div class="workspace">
      <!-- 聊天主体 -->
      <section class="chat-panel">
        <header class="chat-head">
          <div class="guest-meta">
            <div class="avatar-lg">{{ initials }}</div>
            <div>
              <h2 class="chat-title">{{ data.room }} {{ t('房间 -') }} {{ data.guest }}</h2>
              <p class="online"><span class="dot"></span>{{ t('在线') }}</p>
            </div>
          </div>
          <button type="button" class="icon-more" :aria-label="t('更多')">
            <span class="material-symbols-outlined">more_vert</span>
          </button>
        </header>

        <div class="chat-body no-scrollbar">
          <template v-for="(m, i) in data.messages" :key="i">
            <div v-if="m.role === 'guest'" class="msg-block">
              <div class="msg-row">
                <div class="avatar-sm">{{ initials }}</div>
                <div class="bubble">{{ m.text }}</div>
              </div>
              <span v-if="m.time" class="msg-time">{{ m.time }}</span>
            </div>
            <div v-else-if="m.type === 'translation'" class="trans-row">
              <div class="trans-box ai-tinge">
                <span class="trans-tag">{{ t('【AI 翻译】') }}</span
                >{{ m.text }}
              </div>
            </div>
          </template>
          <div class="sys-pill-wrap">
            <span class="sys-pill">{{ t('AI 已介入翻译与建议') }}</span>
          </div>
        </div>

        <footer class="chat-foot">
          <div class="smart-replies no-scrollbar">
            <button
              v-for="r in data.smartReplies"
              :key="r.text"
              type="button"
              class="reply-chip"
              :class="{ tertiary: r.tertiary }"
              @click="applyReply(r.text)"
            >
              {{ r.text }}
            </button>
          </div>
          <div class="composer">
            <div class="composer-box">
              <textarea
                v-model="draft"
                rows="2"
                :placeholder="t('输入中文回复 (AI 将自动翻译为英文)...')"
              />
              <div class="composer-bar">
                <div class="composer-tools">
                  <button type="button">
                    <span class="material-symbols-outlined">attach_file</span>
                  </button>
                  <button type="button"><span class="material-symbols-outlined">mood</span></button>
                </div>
                <label class="auto-tr">
                  <span>{{ t('自动翻译开启') }}</span>
                  <input v-model="autoTranslate" type="checkbox" class="toggle" />
                </label>
              </div>
            </div>
            <button type="button" class="send-btn" :aria-label="t('发送')">
              <span class="material-symbols-outlined">send</span>
            </button>
          </div>
        </footer>
      </section>

      <!-- 右侧 AI 面板 -->
      <aside class="side-panel no-scrollbar">
        <div class="side-card sentiment">
          <div class="tint"></div>
          <div class="side-inner">
            <h3 class="side-title">{{ t('客户情绪感知') }}</h3>
            <div class="mood-pill">{{ data.sentiment.label }}</div>
            <p class="side-desc">{{ data.sentiment.desc }}</p>
          </div>
        </div>

        <div class="side-card ai-tinge conf">
          <h3 class="side-title">{{ t('AI 翻译置信度') }}</h3>
          <div class="conf-row">
            <span class="conf-pct">{{ data.confidence.pct }}%</span>
            <span class="conf-label">{{ data.confidence.text }}</span>
          </div>
          <div class="conf-bar">
            <div class="conf-fill" :style="{ width: (data.confidence.pct || 0) + '%' }"></div>
          </div>
          <p class="side-note">{{ data.confidence.desc }}</p>
        </div>

        <div class="side-card">
          <h3 class="side-title">{{ t('建议操作') }}</h3>
          <div class="act-list">
            <button v-for="a in data.actions" :key="a.label" type="button" class="act-btn">
              <div class="act-ico" :class="a.tone">
                <span class="material-symbols-outlined">{{ a.icon }}</span>
              </div>
              <div class="act-text">
                <div class="act-label">{{ a.label }}</div>
                <div class="act-sub">{{ a.sub }}</div>
              </div>
              <span class="material-symbols-outlined chev">chevron_right</span>
            </button>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.ml-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  min-height: 0;
  gap: 12px;
  box-sizing: border-box;
}
.flow-bar {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
}
.workspace {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 16px;
  align-items: stretch;
}

/* —— 聊天面板 —— */
.chat-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(25, 28, 29, 0.04);
  overflow: hidden;
}
.chat-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--outline-variant, #c1c6d6);
  background: var(--surface, #f8fafb);
  flex-shrink: 0;
}
.guest-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}
.avatar-lg {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--secondary-container, #dde0e6);
  color: var(--on-secondary-container, #5f6368);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  border: 2px solid var(--surface-container-highest, #e1e3e4);
}
.chat-title {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: var(--on-surface, #191c1d);
  line-height: 28px;
}
.online {
  margin: 2px 0 0;
  font-size: 14px;
  color: var(--on-surface-variant, #414754);
  display: flex;
  align-items: center;
  gap: 6px;
}
.online .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary, #005bbf);
}
.icon-more {
  border: none;
  background: transparent;
  color: var(--on-surface-variant);
  border-radius: 999px;
  padding: 8px;
  cursor: pointer;
}
.icon-more:hover {
  background: var(--surface-container, #eceeef);
}

.chat-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px;
  background: var(--surface-bright, #f8fafb);
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.msg-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: 80%;
  gap: 4px;
}
.msg-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.avatar-sm {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--secondary-container, #dde0e6);
  color: var(--on-secondary-container, #5f6368);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.bubble {
  background: var(--surface-container, #eceeef);
  color: var(--on-surface, #191c1d);
  padding: 12px 16px;
  border-radius: 16px;
  border-bottom-left-radius: 4px;
  font-size: 16px;
  line-height: 24px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.msg-time {
  margin-left: 40px;
  font-size: 12px;
  color: var(--on-surface-variant);
  font-family: 'Roboto Mono', monospace;
}
.trans-row {
  margin-left: 40px;
  max-width: calc(80% - 40px);
}
.trans-box {
  padding: 8px 12px;
  border-radius: 0 8px 8px 0;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-left: none;
  font-size: 14px;
  line-height: 20px;
  color: var(--on-surface-variant, #414754);
  background: var(--surface, #f8fafb);
}
.trans-tag {
  color: var(--tertiary, #8c33b3);
  font-weight: 700;
  margin-right: 4px;
}
.ai-tinge {
  border-left: 2px solid var(--tertiary, #8c33b3) !important;
  background: linear-gradient(
    90deg,
    rgba(140, 51, 179, 0.08) 0%,
    rgba(255, 255, 255, 0) 100%
  ) !important;
}
.sys-pill-wrap {
  display: flex;
  justify-content: center;
  margin: 8px 0;
}
.sys-pill {
  background: var(--surface-container-high, #e6e8e9);
  color: var(--on-surface-variant);
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 999px;
}

.chat-foot {
  flex-shrink: 0;
  padding: 16px;
  border-top: 1px solid var(--outline-variant);
  background: var(--surface, #f8fafb);
}
.smart-replies {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  margin-bottom: 16px;
}
.reply-chip {
  flex-shrink: 0;
  padding: 6px 16px;
  border-radius: 999px;
  border: 1px solid var(--outline-variant);
  background: transparent;
  color: var(--on-surface-variant);
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
}
.reply-chip.tertiary {
  border-color: var(--tertiary, #8c33b3);
  color: var(--tertiary, #8c33b3);
}
.reply-chip.tertiary:hover {
  background: var(--tertiary-fixed, #f8d8ff);
}
.reply-chip:hover {
  background: var(--surface-container-high, #e6e8e9);
}
.composer {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.composer-box {
  flex: 1;
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  background: var(--surface-container-lowest, #fff);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.composer-box:focus-within {
  border-color: var(--primary, #005bbf);
  box-shadow: 0 0 0 1px var(--primary, #005bbf);
}
.composer-box textarea {
  width: 100%;
  border: none;
  resize: none;
  padding: 12px;
  font-size: 16px;
  line-height: 24px;
  color: var(--on-surface);
  background: transparent;
  outline: none;
  font-family: inherit;
  box-sizing: border-box;
}
.composer-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-top: 1px solid var(--outline-variant);
}
.composer-tools {
  display: flex;
  gap: 4px;
  color: var(--on-surface-variant);
}
.composer-tools button {
  border: none;
  background: transparent;
  padding: 4px;
  border-radius: 6px;
  cursor: pointer;
  color: inherit;
  display: flex;
}
.composer-tools button:hover {
  background: var(--surface-container-high);
}
.composer-tools .material-symbols-outlined {
  font-size: 18px;
}
.auto-tr {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--on-surface-variant);
  cursor: pointer;
  user-select: none;
}
.toggle {
  width: 36px;
  height: 20px;
  appearance: none;
  background: var(--outline-variant);
  border-radius: 999px;
  position: relative;
  cursor: pointer;
  transition: background 0.15s;
}
.toggle::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.15s;
}
.toggle:checked {
  background: var(--primary, #005bbf);
}
.toggle:checked::after {
  transform: translateX(16px);
}
.send-btn {
  width: 48px;
  height: 48px;
  border: none;
  border-radius: 12px;
  background: var(--primary, #005bbf);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  box-shadow: 0 1px 2px rgba(0, 91, 191, 0.25);
}
.send-btn:hover {
  background: var(--primary-container, #1a73e8);
}

/* —— 右侧 —— */
.side-panel {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  padding-bottom: 8px;
}
.side-card {
  position: relative;
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 2px rgba(25, 28, 29, 0.04);
  overflow: hidden;
}
.side-card.sentiment {
  border-color: var(--error-container, #ffdad6);
}
.side-card.sentiment .tint {
  position: absolute;
  inset: 0;
  background: var(--error-container, #ffdad6);
  opacity: 0.2;
  pointer-events: none;
}
.side-inner {
  position: relative;
  z-index: 1;
}
.side-title {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 800;
  color: var(--on-surface, #191c1d);
  letter-spacing: 0.02em;
}
.mood-pill {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 6px;
  background: var(--error, #ba1a1a);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}
.side-desc {
  margin: 12px 0 0;
  font-size: 14px;
  line-height: 1.45;
  color: var(--on-surface-variant);
}
.side-card.conf {
  /* ai-tinge already on element */
}
.conf-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  margin-bottom: 8px;
}
.conf-pct {
  font-family: 'Roboto Mono', monospace;
  font-size: 28px;
  font-weight: 700;
  color: var(--primary, #005bbf);
  line-height: 1;
}
.conf-label {
  font-size: 14px;
  color: var(--on-surface-variant);
  margin-bottom: 4px;
}
.conf-bar {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: var(--surface-container-highest, #e1e3e4);
  overflow: hidden;
  margin-bottom: 8px;
}
.conf-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--primary, #005bbf);
}
.side-note {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}
.act-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.act-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  background: transparent;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
}
.act-btn:hover {
  background: var(--surface-container, #eceeef);
}
.act-ico {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.act-ico .material-symbols-outlined {
  font-size: 18px;
}
.act-ico.primary {
  background: var(--primary-container, #1a73e8);
  color: #fff;
}
.act-ico.tertiary {
  background: rgba(140, 51, 179, 0.15);
  color: var(--tertiary, #8c33b3);
}
.act-ico.error {
  background: var(--error-container, #ffdad6);
  color: var(--error, #ba1a1a);
}
.act-text {
  flex: 1;
  min-width: 0;
}
.act-label {
  font-size: 14px;
  font-weight: 700;
  color: var(--on-surface);
}
.act-sub {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-top: 2px;
}
.chev {
  color: var(--outline);
  font-size: 20px;
}

.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

@media (max-width: 960px) {
  .workspace {
    flex-direction: column;
  }
  .side-panel {
    width: 100%;
  }
  .ml-page {
    height: auto;
  }
}
</style>
