// SPDX-License-Identifier: Apache-2.0
import { computed, ref, type ComputedRef, type Ref } from 'vue'
import { api } from '../../../lib/api'
import { hotelStore } from '../../../store/hotel'
import { getLocale, t } from '../../../lib/i18n'
import { localizeAssetAiText } from '../../../lib/localizeSeed'

export function useAssetAiStream(opts: {
  raw: Ref<any>
  fallbackNextAction: ComputedRef<{ conf: number; text: string }>
  aiConf: ComputedRef<number>
  verdict: ComputedRef<{ label: string; tone: string }>
  needsRepair: ComputedRef<boolean>
}) {
  const { raw, fallbackNextAction, aiConf, verdict, needsRepair } = opts

  const aiNextAction = ref<any>(null)
  const aiNextLoading = ref(false)
  const aiStreamText = ref('')
  let aiAbort: AbortController | null = null

  const nextAction = computed(() => {
    if (aiNextAction.value?.source && aiNextAction.value.source !== 'llm') {
      return { conf: null, text: '' }
    }
    // EN：流式过程不展示可能含中文的碎片，等 done 后再显示
    if (aiNextLoading.value && aiStreamText.value && !getLocale().startsWith('en')) {
      return {
        conf: aiNextAction.value?.conf ?? null,
        text: aiStreamText.value,
      }
    }
    if (
      aiNextAction.value?.text &&
      (!aiNextAction.value.source || aiNextAction.value.source === 'llm')
    ) {
      return {
        conf: Number(aiNextAction.value.conf || aiConf.value),
        text: localizeAssetAiText(String(aiNextAction.value.text)),
      }
    }
    return { conf: null, text: '' }
  })

  const aiActionType = computed(() => {
    const t = aiNextAction.value?.action_type
    if (t === 'replace' || t === 'repair' || t === 'maintain' || t === 'monitor') return t
    if (verdict.value.tone === 'replace') return 'replace'
    if (needsRepair.value) return 'repair'
    return 'maintain'
  })

  const aiSourceLabel = computed(() => {
    if (aiNextLoading.value) return t('生成中')
    if (aiNextAction.value?.source === 'llm') return t('LLM 生成')
    if (aiNextAction.value?.source === 'unavailable' || aiNextAction.value?.source === 'fallback')
      return t('AI 暂不可用')
    return ''
  })

  const showAiActionButtons = computed(
    () =>
      Boolean(aiNextAction.value?.text) &&
      aiNextAction.value?.source === 'llm' &&
      !aiNextLoading.value,
  )

  function stopAiStream() {
    aiAbort?.abort()
    aiAbort = null
  }

  function resetAiState() {
    stopAiStream()
    aiNextAction.value = null
    aiStreamText.value = ''
  }

  async function triggerAiNextAction() {
    if (!raw.value?.id || aiNextLoading.value) return
    stopAiStream()
    aiNextLoading.value = true
    aiNextAction.value = null
    aiStreamText.value = ''
    aiAbort = new AbortController()
    try {
      await api.assetAiNextActionStream(
        raw.value.id,
        hotelStore.hotelId,
        (evt) => {
          if (evt.type === 'token' && evt.content) {
            // 流式仅作加载期内部缓冲；最终以 done 的结构化字段展示，不暴露原始 JSON
            aiStreamText.value += evt.content
          } else if (evt.type === 'done' && evt.data) {
            aiNextAction.value = evt.data
            aiStreamText.value = ''
          }
        },
        aiAbort.signal,
      )
    } catch (e: any) {
      if (e?.name !== 'AbortError') {
        aiNextAction.value = {
          source: 'unavailable',
          llm_error: e?.message || t('请求失败'),
          text: '',
        }
      }
    } finally {
      aiNextLoading.value = false
      aiAbort = null
    }
  }

  return {
    aiNextAction,
    aiNextLoading,
    aiStreamText,
    nextAction,
    aiActionType,
    aiSourceLabel,
    showAiActionButtons,
    stopAiStream,
    resetAiState,
    triggerAiNextAction,
  }
}
