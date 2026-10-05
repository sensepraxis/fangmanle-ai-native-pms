// SPDX-License-Identifier: Apache-2.0
// API: misc
import { req } from './client'

export const miscApi = {
  patchReview: (reviewId: number, body: { replied: boolean; reply_content?: string }) =>
    req<any>('PATCH', `/reviews/${reviewId}`, body),
}
