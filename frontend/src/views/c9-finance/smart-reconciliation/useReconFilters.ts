// SPDX-License-Identifier: Apache-2.0
import { computed, ref, type Ref } from 'vue'
import { toast } from '../../../lib/ui'
import type { BatchRow, Dim, Tab } from './types'
import { t } from '../../../lib/i18n'

export function useReconFilters(batches: Ref<BatchRow[]>) {
  const dim = ref<Dim>('batch')
  const tab = ref<Tab>('all')
  const channelFilter = ref('all')
  const dateLabel = ref('')

  const filtered = computed(() => {
    let list = batches.value
    if (dateLabel.value) {
      list = list.filter((b) => b.bizDate === dateLabel.value)
    }
    if (channelFilter.value !== 'all') {
      list = list.filter((b) => b.channel === channelFilter.value)
    }
    if (tab.value === 'ai') list = list.filter((b) => b.status === 'ai')
    else if (tab.value === 'human')
      list = list.filter((b) => b.status === 'human' || b.status === 'progress')
    else if (tab.value === 'closed')
      list = list.filter((b) => b.status === 'closed' || b.status === 'matched')
    return list
  })

  const dateOptions = computed(() =>
    [...new Set(batches.value.map((b) => b.bizDate).filter(Boolean))].sort().reverse(),
  )

  const channelOptions = computed(() =>
    [...new Set(batches.value.map((b) => b.channel).filter(Boolean))].sort(),
  )

  const counts = computed(() => {
    const base = dateLabel.value
      ? batches.value.filter((b) => b.bizDate === dateLabel.value)
      : batches.value
    return {
      all: base.length,
      ai: base.filter((b) => b.status === 'ai').length,
      human: base.filter((b) => b.status === 'human' || b.status === 'progress').length,
      closed: base.filter((b) => b.status === 'closed' || b.status === 'matched').length,
    }
  })

  function setDim(d: Dim) {
    dim.value = d
    toast(
      t(
        d === 'batch'
          ? '已切换到「批次日」· 按渠道结算批次聚合'
          : d === 'accrual'
            ? '已切换到「应收日」· 按 PMS 入账日聚合'
            : '已切换到「到账日」· 按银行入账日聚合',
      ),
    )
  }

  return {
    dim,
    tab,
    channelFilter,
    dateLabel,
    filtered,
    dateOptions,
    channelOptions,
    counts,
    setDim,
  }
}
