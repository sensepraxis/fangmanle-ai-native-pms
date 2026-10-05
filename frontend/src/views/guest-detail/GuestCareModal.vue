<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

defineProps<{
  open: boolean
  guestName: string
  careMaterial: string
  careDraft: string
  careSource: string
  careHint: string
  careError: string
  careSent: boolean
  careCopied: boolean
  careGenerating: boolean
  careGenerated: boolean
  careSending: boolean
  wecomBound: boolean
  wecomInChat: boolean
  wecom: any
}>()

const emit = defineEmits<{
  close: []
  'update:careMaterial': [string]
  'update:careDraft': [string]
  generate: []
  send: []
  copy: []
}>()
</script>

<template>
  <div v-if="open" class="care-overlay" @click.self="emit('close')">
    <div class="care-modal" role="dialog" aria-labelledby="care-title">
      <div class="care-head">
        <div>
          <h2 id="care-title" class="care-title">
            {{ t('发送关怀 ·') }} {{ guestName || t('客人') }}
          </h2>
        </div>
        <button type="button" class="care-close" :aria-label="t('关闭')" @click="emit('close')">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
      <p v-if="careSource" class="care-src">{{ t('文案来源：') }}{{ careSource }}</p>
      <label class="care-label" for="care-material">{{ t('关怀素材（人工填写）') }}</label>
      <textarea
        id="care-material"
        class="care-textarea care-material"
        rows="3"
        :placeholder="t('例如：提醒客人 9 月入住可提前选房型；感谢领券；询问到店时间…')"
        :value="careMaterial"
        :disabled="careGenerating || careSending"
        @input="emit('update:careMaterial', ($event.target as HTMLTextAreaElement).value)"
      />
      <label class="care-label" for="care-draft">{{ t('AI 生成话术（可编辑）') }}</label>
      <textarea
        id="care-draft"
        class="care-textarea"
        rows="7"
        :placeholder="t('填写素材后点击「AI 生成」')"
        :value="careDraft"
        :disabled="careGenerating"
        @input="emit('update:careDraft', ($event.target as HTMLTextAreaElement).value)"
      />
      <p v-if="careHint" class="care-hint">{{ careHint }}</p>
      <div v-if="careSent" class="care-delivery">
        <ol v-if="wecomInChat" class="care-steps">
          <li>
            {{ t('消息已通过企微') }} <strong>sendChatMessage</strong>
            {{ t('发送到当前 1:1 会话') }}
          </li>
          <li>{{ t('无需复制粘贴，不走群发助手') }}</li>
        </ol>
        <ol v-else class="care-steps">
          <li>{{ t('话术已复制到剪贴板') }}</li>
          <li>
            {{ t('管家') }} {{ wecom?.follow_userid || t('跟进人') }} {{ t('会收到企微应用通知') }}
          </li>
          <li>
            {{ t('打开与该客户的') }} <strong>{{ t('1:1 聊天') }}</strong>
            {{ t('→ 长按粘贴 → 发送') }}
          </li>
        </ol>
        <div class="care-delivery-actions">
          <button v-if="!wecomInChat" type="button" class="btn-hero" @click="emit('copy')">
            {{ careCopied ? t('已复制') : t('再次复制话术') }}
          </button>
        </div>
      </div>
      <p v-if="careError" class="care-err">{{ careError }}</p>
      <div class="care-actions">
        <button
          type="button"
          class="btn-hero"
          :disabled="careGenerating || !careMaterial.trim()"
          @click="emit('generate')"
        >
          <span class="material-symbols-outlined text-[18px]">auto_awesome</span>
          {{ careGenerating ? t('AI 生成中…') : careGenerated ? t('AI 重新生成') : t('AI 生成') }}
        </button>
        <button type="button" class="btn-hero" @click="emit('close')">{{ t('取消') }}</button>
        <button
          type="button"
          class="btn-hero primary"
          :disabled="careSending || !careDraft.trim() || !wecomBound"
          @click="emit('send')"
        >
          <span class="material-symbols-outlined text-[18px]">send</span>
          {{
            careSending ? t('提交中…') : wecomInChat ? t('直发到当前会话') : t('发送到 1:1 会话')
          }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './guest-detail-shared.css';
</style>
