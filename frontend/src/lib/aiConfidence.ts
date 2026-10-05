// SPDX-License-Identifier: Apache-2.0
/** AI 置信度展示：兼容 high|medium|low 与 高|中|低，跟当前 locale。 */
import { t } from './i18n'

const TO_MSGID: Record<string, string> = {
  high: '高置信',
  medium: '中置信',
  low: '低置信',
  高: '高置信',
  中: '中置信',
  低: '低置信',
  高置信: '高置信',
  中置信: '中置信',
  低置信: '低置信',
}

export function confidenceLabel(raw?: string | null): string {
  if (raw == null || raw === '') return ''
  const s = String(raw).trim()
  const msgid = TO_MSGID[s.toLowerCase()] || TO_MSGID[s]
  return msgid ? t(msgid) : s
}
