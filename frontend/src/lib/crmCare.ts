// SPDX-License-Identifier: Apache-2.0
/** 关怀标记：优先 API，localStorage 作离线兜底 */
const LS_KEY = 'fml_cared_reviews'

function readLocal(): Record<string, boolean> {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || '{}')
  } catch {
    return {}
  }
}

function writeLocal(map: Record<string, boolean>) {
  localStorage.setItem(LS_KEY, JSON.stringify(map))
}

export function isReviewCared(reviewId: number, replied?: boolean) {
  if (replied) return true
  return !!readLocal()[String(reviewId)]
}

export function markReviewCaredLocal(reviewId: number) {
  const m = readLocal()
  m[String(reviewId)] = true
  writeLocal(m)
}

export async function markReviewCared(
  reviewId: number,
  replyContent: string,
  patchReview: (id: number, body: { replied: boolean; reply_content: string }) => Promise<unknown>,
) {
  markReviewCaredLocal(reviewId)
  try {
    await patchReview(reviewId, { replied: true, reply_content: replyContent })
  } catch {
    /* 离线兜底已写入 localStorage */
  }
}
