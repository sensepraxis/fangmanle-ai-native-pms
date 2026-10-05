// SPDX-License-Identifier: Apache-2.0
/**
 * 企微关怀：弹窗状态、AI 话术生成/发送、侧边栏 SDK
 */
import { ref, onMounted, type Ref, type ComputedRef } from 'vue'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { api } from '../../lib/api'
import { t } from '../../lib/i18n'
import { privateChannelVendor } from '../../lib/branding'
import {
  initWecomSidebarSdk,
  sendWecomChatText,
  isWecomUa,
  isSidebarChatEntry,
} from '../../lib/wecomJssdk'

export function useGuestCare(opts: {
  guestId: ComputedRef<number | undefined> | Ref<number | undefined>
  wecomBound: ComputedRef<boolean> | Ref<boolean>
  wecomExternalId: ComputedRef<string> | Ref<string>
}) {
  const { guestId, wecomBound, wecomExternalId } = opts

  const careOpen = ref(false)
  const careMaterial = ref('')
  const careDraft = ref('')
  const careGenerated = ref(false)
  const careGenerating = ref(false)
  const careSending = ref(false)
  const careHint = ref('')
  const careError = ref('')
  const careSource = ref('')
  const careCopied = ref(false)
  const careSent = ref(false)
  const wecomSdkReady = ref(false)
  const wecomInChat = ref(false)

  onMounted(async () => {
    if (privateChannelVendor() !== 'wecom') return
    if (!isWecomUa()) return
    try {
      const ctx = await initWecomSidebarSdk()
      wecomSdkReady.value = true
      wecomInChat.value = isSidebarChatEntry(ctx.entry)
    } catch {
      wecomSdkReady.value = false
    }
  })

  async function openCareModal() {
    if (!guestId.value) return
    careOpen.value = true
    careMaterial.value = ''
    careDraft.value = ''
    careGenerated.value = false
    careError.value = ''
    careHint.value = ''
    careSource.value = ''
    careSent.value = false
    careCopied.value = false
  }

  function closeCareModal() {
    careOpen.value = false
  }

  async function copyCareDraft() {
    const text = careDraft.value.trim()
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
      careCopied.value = true
      setTimeout(() => {
        careCopied.value = false
      }, 2500)
    } catch {
      careError.value = t('复制失败，请手动选中话术复制')
    }
  }

  async function generateCareDraft() {
    if (!guestId.value || careGenerating.value) return
    const material = careMaterial.value.trim()
    if (!material) {
      careError.value = t('请先填写上方的关怀素材')
      return
    }
    careGenerating.value = true
    careError.value = ''
    try {
      const res = await api.guestWecomCareDraft(Number(guestId.value), material)
      careDraft.value = res.content || ''
      careGenerated.value = true
      const modelMeta = formatAiModelMeta(res)
      careSource.value = [
        t(res.source_cn || res.source || ''),
        modelMeta,
        res.profile_used && res.profile_summary
          ? t('参考画像：{summary}', { summary: res.profile_summary })
          : '',
      ]
        .filter(Boolean)
        .join(' · ')
      careHint.value = res.hint || ''
      if (res.source !== 'llm') {
        careHint.value =
          `${res.hint || ''} ${t('未能调用大模型，未生成关怀话术（模板不会冒充 AI）。')}`.trim()
      }
    } catch (e: any) {
      careError.value = e?.message || t('生成关怀话术失败')
    } finally {
      careGenerating.value = false
    }
  }

  async function sendCareMessage() {
    const text = careDraft.value.trim()
    if (!text || careSending.value || !guestId.value) return
    const useWecom = privateChannelVendor() === 'wecom'
    if (useWecom && !wecomBound.value) {
      careError.value = t('该客人尚未绑定企微，无法推送。请先完成扫码加好友与手机号归集。')
      return
    }
    careSending.value = true
    careError.value = ''
    try {
      if (!useWecom) {
        await copyCareDraft()
        careSent.value = true
        careHint.value = t('已复制话术。本部署未启用企微，请通过短信或链接发送。')
        return
      }
      if (wecomSdkReady.value && wecomInChat.value) {
        await sendWecomChatText(text)
        const res = await api.wecomSidebarCareSent(wecomExternalId.value, text)
        careSent.value = true
        careHint.value = res.hint || t('已通过聊天工具栏直发到当前 1:1 会话')
        careError.value = ''
        return
      }
      if (wecomSdkReady.value && !wecomInChat.value) {
        careError.value = t(
          '当前不在客户 1:1 聊天侧边栏。请打开与该客户的私聊 → 点击聊天工具栏「PMS 关怀」，或在此会话中打开侧边栏后再发送。',
        )
        return
      }
      await copyCareDraft()
      const res = await api.guestWecomCareSend(Number(guestId.value), text)
      careSent.value = true
      careHint.value = [
        res.hint || res.status_cn || t('已通知管家在 1:1 会话发送'),
        ...(res.steps || []),
      ].join(' → ')
      careError.value = ''
    } catch (e: any) {
      careError.value = e?.message || t('发送失败')
    } finally {
      careSending.value = false
    }
  }

  return {
    careOpen,
    careMaterial,
    careDraft,
    careGenerated,
    careGenerating,
    careSending,
    careHint,
    careError,
    careSource,
    careCopied,
    careSent,
    wecomSdkReady,
    wecomInChat,
    openCareModal,
    closeCareModal,
    copyCareDraft,
    generateCareDraft,
    sendCareMessage,
  }
}
