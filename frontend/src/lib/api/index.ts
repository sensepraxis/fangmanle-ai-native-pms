// SPDX-License-Identifier: Apache-2.0
// Merged API surface
import { systemApi } from './system'
import { analyticsApi } from './analytics'
import { roomsApi } from './rooms'
import { ordersApi } from './orders'
import { financeApi } from './finance'
import { guestsApi } from './guests'
import { hkApi } from './hk'
import { pricingApi } from './pricing'
import { assetsApi } from './assets'
import { mktApi } from './mkt'
import { miscApi } from './misc'

export const api = {
  ...systemApi,
  ...analyticsApi,
  ...roomsApi,
  ...ordersApi,
  ...financeApi,
  ...guestsApi,
  ...hkApi,
  ...pricingApi,
  ...assetsApi,
  ...mktApi,
  ...miscApi,
}
