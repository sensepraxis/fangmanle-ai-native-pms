// SPDX-License-Identifier: Apache-2.0
import { computed, ref, type ComputedRef } from 'vue'
import { api } from '../../../lib/api'
import { hotelStore } from '../../../store/hotel'
import { fmtDate, statusClsMaint, statusLabelMaint } from './useAssetProfileDerived'
import { t } from '../../../lib/i18n'
import { localizeSeedText } from '../../../lib/localizeSeed'

function mapEventType(evType?: string) {
  if (evType === 'predict') return 'ai'
  if (evType === 'retire') return 'future'
  if (evType === 'maintain' || evType === 'repair') return 'past-dim'
  return 'past'
}

function mapMaintRow(m: any) {
  const taskTypeRaw = m.task_type || '维保'
  const taskType = localizeSeedText(taskTypeRaw) || t(taskTypeRaw)
  const isMaint = /保养|维保|maint/i.test(taskTypeRaw)
  return {
    id: `WO-${m.id}`,
    maintId: m.id,
    type: taskType,
    typeCls:
      taskTypeRaw === '查房'
        ? 'var(--surface-container-high)'
        : isMaint
          ? 'rgba(168,79,206,0.18)'
          : 'var(--secondary-container)',
    typeOn:
      taskTypeRaw === '查房'
        ? 'var(--on-surface-variant)'
        : isMaint
          ? 'var(--tertiary)'
          : 'var(--on-secondary-container)',
    dueDate: fmtDate(m.due_date),
    completedAt: m.completed_at ? String(m.completed_at).replace('T', ' ').slice(0, 16) : '',
    createdAt: m.created_at ? String(m.created_at).replace('T', ' ').slice(0, 16) : '',
    owner: localizeSeedText(m.owner) || '—',
    status: statusLabelMaint(m.status),
    statusCls: statusClsMaint(m.status),
    rawStatus: m.status || 'scheduled',
    note: localizeSeedText(m.note || ''),
    cost: m.cost != null ? Number(m.cost) : null,
  }
}

function buildRootCauses(b: any, id: number, insight?: string) {
  const causes: string[] = []
  for (const al of (b?.alerts || []).filter((x: any) => x.asset_id === id).slice(0, 2)) {
    causes.push(al.message || '重复告警')
  }
  const repairs = (b?.events || []).filter(
    (e: any) => e.asset_id === id && e.event_type === 'repair',
  )
  if (repairs.length >= 2) causes.push(`近 12 个月同类维修 ${repairs.length} 次`)
  if (!causes.length && insight) causes.push(insight)
  return causes.slice(0, 3)
}

export function useAssetProfileLoad(opts: {
  assetId: ComputedRef<number>
  onBeforeLoad?: () => void
}) {
  const { assetId, onBeforeLoad } = opts

  const loading = ref(true)
  const empty = ref(false)
  const raw = ref<any>(null)
  const timeline = ref<any[]>([])
  const workOrders = ref<any[]>([])
  const woDetail = ref<any>(null)
  const woDetailLoading = ref(false)
  const selectedWoId = ref<string | null>(null)
  const alerts = ref<any[]>([])
  const rootCauses = ref<string[]>([])
  const assetEvents = ref<any[]>([])

  const woDetailOpen = computed(() => !!selectedWoId.value)
  const woProgressSteps = computed(() =>
    (woDetail.value?.progress_steps || [t('已创建'), t('已派工'), t('维修中'), t('已完成')]).map(
      (s: string) => t(s),
    ),
  )
  const woProgressStep = computed(() => Number(woDetail.value?.progress_step || 1))

  const woSummary = computed(() => {
    const open = workOrders.value.filter((w) => w.rawStatus !== 'done').length
    const done = workOrders.value.length - open
    return { total: workOrders.value.length, open, done }
  })

  function closeWorkOrderDetail() {
    selectedWoId.value = null
    woDetail.value = null
  }

  async function openWorkOrderDetail(w: { id: string; maintId: number }) {
    if (selectedWoId.value === w.id) {
      closeWorkOrderDetail()
      return
    }
    selectedWoId.value = w.id
    woDetailLoading.value = true
    woDetail.value = null
    try {
      woDetail.value = await api.assetMaintenanceDetail(
        assetId.value,
        w.maintId,
        hotelStore.hotelId,
      )
    } catch {
      woDetail.value = null
      selectedWoId.value = null
    } finally {
      woDetailLoading.value = false
    }
  }

  async function load() {
    loading.value = true
    closeWorkOrderDetail()
    onBeforeLoad?.()
    assetEvents.value = []
    try {
      const b = await api.assetsBoard(hotelStore.hotelId)
      const found = (b?.assets || []).find((x: any) => Number(x.id) === assetId.value)
      if (!found) {
        empty.value = true
        raw.value = null
        return
      }
      empty.value = false
      raw.value = found

      const evMap = b?.events_by_asset || {}
      const ev = (evMap[found.id] || evMap[String(found.id)] || []).filter(
        (e: any) => !e.asset_id || Number(e.asset_id) === Number(found.id),
      )
      assetEvents.value = ev
      const loc = found.room_no
        ? t('{n} 房', { n: found.room_no })
        : localizeSeedText(found.location) || '—'
      if (ev.length) {
        timeline.value = ev
          .slice()
          .sort((x: any, y: any) =>
            String(x.happened_at || '').localeCompare(String(y.happened_at || '')),
          )
          .map((e: any) => ({
            title: localizeSeedText(e.title) || e.title,
            time: e.happened_at ? String(e.happened_at).replace('T', ' ').slice(0, 16) : '',
            desc: localizeSeedText(e.note || ''),
            type: mapEventType(e.event_type),
            action: e.event_type === 'predict' ? t('生成预防性工单') : '',
          }))
      } else {
        const insight = localizeSeedText(found.insight || '')
        timeline.value = [
          {
            title: t('入库采购'),
            time: `${found.purchase_date || '—'} 10:30`,
            desc: '',
            type: 'past',
            action: '',
          },
          {
            title: t('初次安装'),
            time: `${found.purchase_date || '—'} • ${loc}`,
            desc: '',
            type: 'past',
            action: '',
          },
          {
            title: t('历次维保记录'),
            time: insight || '—',
            desc: '',
            type: 'past-dim',
            action: '',
          },
          {
            title: t('AI 故障预测点'),
            time: '',
            desc: insight
              ? t('基于设备监测数据：{insight}', { insight })
              : t('基于当前功耗异常波动，预计关键部件将在 60 天内出现老化衰减。'),
            type: 'ai',
            action: t('生成预防性工单'),
          },
          {
            title: t('预计报废时间'),
            time: t('依据折旧期推算'),
            desc: '',
            type: 'future',
            action: '',
          },
        ]
      }

      try {
        const maintRows = await api.assetMaintenance(found.id, hotelStore.hotelId)
        workOrders.value = (maintRows || []).map(mapMaintRow)
      } catch {
        workOrders.value = []
      }

      alerts.value = (b?.alerts || []).filter((al: any) => Number(al.asset_id) === Number(found.id))
      rootCauses.value = buildRootCauses(b, found.id, found.insight)
    } catch {
      empty.value = true
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    empty,
    raw,
    timeline,
    workOrders,
    woDetail,
    woDetailLoading,
    selectedWoId,
    alerts,
    rootCauses,
    assetEvents,
    woDetailOpen,
    woProgressSteps,
    woProgressStep,
    woSummary,
    closeWorkOrderDetail,
    openWorkOrderDetail,
    load,
  }
}
