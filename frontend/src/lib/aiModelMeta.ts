// SPDX-License-Identifier: Apache-2.0
/** 仅在真实 LLM 调用成功时展示厂商/模型；规则或失败路径不贴模型名 */
export function formatAiModelMeta(insight: any): string {
  if (!insight || typeof insight !== 'object') return ''
  const src = String(insight.source || insight.answer_source || insight.ai_source || '')
    .trim()
    .toLowerCase()
  if (src && src !== 'llm') return ''
  const label = String(insight.provider_label || insight.provider || '').trim()
  const model = String(insight.model || insight.model_name || '').trim()
  if (label && model) return `${label} · ${model}`
  return model || label || ''
}
