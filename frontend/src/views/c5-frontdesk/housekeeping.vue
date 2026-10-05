<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// C5 常住客生活服务配置：客人 / 标签 / 在住订单 / 客需
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import OrdersFlowNav from '../../components/OrdersFlowNav.vue'
import HousekeepingFlowNav from '../../components/HousekeepingFlowNav.vue'

const amenities = ref<string[]>([])
const insights = ref<{ icon: string; text: string; suggest: string; actions?: boolean }[]>([])
const cleanDays = ref<string[]>(['周二 (Tue)', '周五 (Fri)'])
const cleanDayOptions = computed(() => [
  { value: '周二 (Tue)', label: t('周二 (Tue)') },
  { value: '周三 (Wed)', label: t('周三 (Wed)') },
  { value: '周四 (Thu)', label: t('周四 (Thu)') },
  { value: '周五 (Fri)', label: t('周五 (Fri)') },
])
const guestName = ref('常住客')
const guestTitle = ref('')
const roomNo = ref('—')
const stayRange = ref('')
const stayDays = ref(0)
const vipLevel = ref('')
const loadError = ref('')

const FALLBACK_AMENITIES = [
  'Extra Pillows (多加枕头)',
  'High Floor Only (只住高层)',
  'Decaf Coffee (低因咖啡)',
]

async function load() {
  loadError.value = ''
  const hid = hotelStore.hotelId
  try {
    const [guests, rooms, srs] = await Promise.all([
      api.listGuests(hid),
      api.listRooms(hid),
      api.listServiceRequests(hid).catch(() => []),
    ])
    const vipFirst =
      (guests || []).find((g: any) => String(g.vip_level || '').toLowerCase() !== 'normal') ||
      (guests || []).sort((a: any, b: any) => Number(b.ltv || 0) - Number(a.ltv || 0))[0]
    if (!vipFirst) {
      amenities.value = FALLBACK_AMENITIES
      insights.value = [
        { icon: 'info', text: t('暂无客人画像。'), suggest: '请确认种子数据已灌入。' },
      ]
      return
    }

    const detail = await api.guest360(vipFirst.id)
    const g = detail?.guest || vipFirst
    guestName.value = g.name || '客人'
    vipLevel.value = g.vip_level || 'normal'
    guestTitle.value = `${g.city || '常住'} · ${String(vipLevel.value).toUpperCase()}`

    const orders = detail?.orders || []
    const stay = orders.find((o: any) => o.status === 'checked_in') || orders[0]
    if (stay) {
      stayRange.value = `${String(stay.check_in || '').slice(0, 10)} - ${String(stay.check_out || '').slice(0, 10)}`
      stayDays.value =
        Number(stay.nights) ||
        (() => {
          const ci = stay.check_in ? new Date(stay.check_in) : null
          const co = stay.check_out ? new Date(stay.check_out) : null
          return ci && co ? Math.max(1, Math.round((+co - +ci) / 86400000)) : 0
        })()
    } else {
      stayRange.value = t('长期协议在住')
      stayDays.value = Math.round(Number(g.ltv || 0) / 80) || 30
    }
    const occ =
      (rooms || []).find(
        (r: any) => (r.guest_name === g.name || r.guest_id === g.id) && r.status === 'occupied',
      ) || (rooms || []).find((r: any) => r.status === 'occupied')
    roomNo.value = occ?.room_no || '—'

    const tags = (detail?.tags || []).map((t: any) => t.name).filter(Boolean)
    amenities.value = tags.length ? tags : FALLBACK_AMENITIES

    const openSr = (srs || []).filter((s: any) => {
      const open = s.open ?? !['done', 'closed', 'cancelled'].includes(s.status)
      return open && (s.guest_id === g.id || s.room === roomNo.value || s.room_no === roomNo.value)
    })

    const nextInsights: typeof insights.value = []
    if (tags.some((t: string) => /宠物|pet/i.test(t))) {
      nextInsights.push({
        icon: 'pets',
        text: t('系统标签显示该客人带宠物相关偏好。'),
        suggest: '建议：每 14 天安排一次深度除螨清洁。',
        actions: true,
      })
    }
    if (tags.some((t: string) => /过敏|allergy|羽绒/i.test(t))) {
      nextInsights.push({
        icon: 'health_and_safety',
        text: t('客人存在过敏相关标签。'),
        suggest: '建议：换乳胶床品，并在房卡备注同步房务。',
        actions: true,
      })
    }
    if (openSr.length) {
      nextInsights.push({
        icon: 'room_service',
        text: `当前关联开放客需 ${openSr.length} 条（如 ${openSr[0].title || openSr[0].type || '服务'}）。`,
        suggest: '建议：优先闭环客需后再排深度清洁。',
      })
    }
    if (Number(g.churn_risk || 0) >= 0.5) {
      nextInsights.push({
        icon: 'trending_down',
        text: `流失风险偏高（${Math.round(Number(g.churn_risk) * 100)}%）。`,
        suggest: '建议：主动关怀 + 固定打扫时段，提升体验粘性。',
      })
    }
    if (!nextInsights.length) {
      nextInsights.push({
        icon: 'restaurant',
        text: `LTV ¥${Math.round(Number(g.ltv || 0))}，画像标签 ${tags.length || 0} 个。`,
        suggest: '建议：按标签维护用品偏好，并固定偏好打扫时段。',
      })
    }
    insights.value = nextInsights
  } catch (e: any) {
    loadError.value = e?.message || t('加载失败')
    amenities.value = FALLBACK_AMENITIES
    insights.value = [
      { icon: 'info', text: t('客人数据暂不可用。'), suggest: '请登录后重试，或重启后端。' },
    ]
  }
}
onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <main class="flex-1 bg-background overflow-y-auto p-container-padding">
    <div class="max-w-max-content-width mx-auto">
      <div class="flex justify-between items-end mb-8 flex-wrap gap-3">
        <div>
          <div class="flex items-center gap-2 text-on-surface-variant mb-2">
            <span class="text-label-lg cursor-pointer hover:text-primary">{{ t('常住支线') }}</span>
            <span class="material-symbols-outlined text-[16px]">chevron_right</span>
            <span class="text-label-lg"
              >{{ guestName }} ({{ String(vipLevel || 'VIP').toUpperCase() }})</span
            >
          </div>
          <h1 class="text-display-lg font-display-lg text-on-surface">
            {{ t('常住客生活服务配置') }}
          </h1>
          <p class="text-body-md font-body-md text-on-surface-variant mt-1">
            {{ t('房号') }} <span class="font-num-md text-primary font-bold">{{ roomNo }}</span> ·
            {{ t('入住期:') }} {{ stayRange || '—' }}
            · 可交房务客需执行
          </p>
          <p v-if="loadError" class="text-xs mt-1" style="color: var(--error)">{{ loadError }}</p>
        </div>
        <div class="flex flex-col items-end gap-3">
          <OrdersFlowNav mode="longstay" hide-back />
          <HousekeepingFlowNav mode="guest" />
          <div class="flex gap-3">
            <button
              class="px-4 py-2 rounded border border-outline text-on-surface font-label-lg hover:bg-surface-container-low transition-colors"
              type="button"
            >
              {{ t('取消') }}
            </button>
            <button
              class="px-4 py-2 rounded bg-primary text-on-primary font-label-lg hover:bg-primary/90 transition-colors shadow-sm"
              type="button"
            >
              {{ t('保存配置') }}
            </button>
          </div>
        </div>
      </div>
      <div class="grid grid-cols-12 gap-gutter">
        <div class="col-span-12 lg:col-span-8 flex flex-col gap-6">
          <div class="bg-surface rounded-xl border border-outline-variant/50 p-6 shadow-sm">
            <div class="flex items-center gap-3 mb-6">
              <div
                class="w-10 h-10 rounded-full bg-primary-fixed/30 flex items-center justify-center text-primary"
              >
                <span class="material-symbols-outlined">cleaning_services</span>
              </div>
              <h2 class="text-headline-md font-headline-md text-on-surface">
                {{ t('客房打扫计划 (Housekeeping)') }}
              </h2>
            </div>
            <div class="space-y-6">
              <div>
                <label class="block text-label-lg font-label-lg text-on-surface mb-2">{{
                  t('深度清洁频率 (Full Clean)')
                }}</label>
                <div class="flex flex-wrap gap-3">
                  <label
                    v-for="d in cleanDayOptions"
                    :key="d.value"
                    class="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      :checked="cleanDays.includes(d.value)"
                      class="w-5 h-5 rounded border-outline text-primary focus:ring-primary"
                      type="checkbox"
                    />
                    <span class="text-body-md font-body-md text-on-surface">{{ d.label }}</span>
                  </label>
                </div>
              </div>
              <div class="p-4 bg-surface-container-low rounded-lg border border-outline-variant/30">
                <div class="flex items-center justify-between mb-3">
                  <span class="text-label-lg font-label-lg text-on-surface">{{
                    t('日常整理 (Light Clean)')
                  }}</span>
                  <label class="relative inline-flex items-center cursor-pointer">
                    <input checked="" class="sr-only peer" type="checkbox" value="" />
                    <div
                      class="w-11 h-6 bg-surface-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"
                    ></div>
                  </label>
                </div>
                <p class="text-body-md font-body-md text-on-surface-variant text-sm">
                  {{ t('每日进行垃圾倾倒、毛巾更换及床铺简易整理。排除深度清洁日。') }}
                </p>
              </div>
            </div>
          </div>
          <div class="bg-surface rounded-xl border border-outline-variant/50 p-6 shadow-sm">
            <div class="flex items-center gap-3 mb-6">
              <div
                class="w-10 h-10 rounded-full bg-secondary-container/50 flex items-center justify-center text-on-secondary-container"
              >
                <span class="material-symbols-outlined">coffee</span>
              </div>
              <h2 class="text-headline-md font-headline-md text-on-surface">
                {{ t('客房用品偏好 (Amenity Preferences)') }}
              </h2>
            </div>
            <div class="flex flex-wrap gap-2 mb-4">
              <span
                v-for="(a, i) in amenities"
                :key="i"
                class="inline-flex items-center gap-1 px-3 py-1 bg-surface-container-highest rounded-full text-label-lg font-label-lg text-on-surface border border-outline-variant"
              >
                {{ a }}
                <button
                  class="material-symbols-outlined text-[16px] text-on-surface-variant hover:text-error ml-1"
                  type="button"
                >
                  close
                </button>
              </span>
            </div>
          </div>
        </div>
        <div class="col-span-12 lg:col-span-4 flex flex-col gap-6">
          <div
            class="bg-surface rounded-xl border-l-4 border-l-tertiary border-y border-r border-outline-variant/50 p-6 shadow-sm relative overflow-hidden"
          >
            <div class="flex items-center gap-2 mb-4 relative z-10">
              <span class="material-symbols-outlined text-tertiary">psychology</span>
              <h3 class="text-headline-md font-headline-md text-on-surface">
                {{ t('AI 管家洞察') }}
              </h3>
            </div>
            <div class="space-y-4 relative z-10">
              <div
                v-for="(ins, i) in insights"
                :key="i"
                class="bg-tertiary-fixed/30 p-4 rounded-lg border border-tertiary/20"
              >
                <div class="flex items-start gap-3">
                  <span class="material-symbols-outlined text-tertiary mt-0.5 text-[20px]">{{
                    ins.icon
                  }}</span>
                  <div>
                    <p class="text-body-md font-body-md text-on-surface text-sm">{{ ins.text }}</p>
                    <p class="text-label-lg font-label-lg text-tertiary mt-1">{{ ins.suggest }}</p>
                  </div>
                </div>
                <div v-if="ins.actions" class="mt-3 flex gap-2">
                  <button
                    class="text-xs px-3 py-1.5 bg-tertiary text-on-tertiary rounded font-medium"
                    type="button"
                  >
                    {{ t('一键应用配置') }}
                  </button>
                  <button
                    class="text-xs px-3 py-1.5 border border-tertiary text-tertiary rounded font-medium"
                    type="button"
                  >
                    {{ t('忽略') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div class="bg-surface rounded-xl border border-outline-variant/50 p-6 shadow-sm">
            <div
              class="text-label-lg font-label-lg text-on-surface-variant mb-4 uppercase tracking-wider"
            >
              {{ t('客户速览') }}
            </div>
            <div class="flex items-center gap-4 mb-6">
              <div
                class="w-16 h-16 rounded-full bg-secondary-container flex items-center justify-center text-2xl font-semibold text-on-secondary-container"
              >
                {{ (guestName || t('客'))[0] }}
              </div>
              <div>
                <div class="text-headline-md font-headline-md text-on-surface">{{ guestName }}</div>
                <div class="text-body-md font-body-md text-on-surface-variant text-sm">
                  {{ guestTitle || t('常住客') }}
                </div>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <div class="text-[12px] text-on-surface-variant mb-1">{{ t('累计入住天数') }}</div>
                <div class="font-num-xl text-num-xl text-on-surface">
                  {{ stayDays }}<span class="text-sm font-normal ml-1">{{ t('天') }}</span>
                </div>
              </div>
              <div>
                <div class="text-[12px] text-on-surface-variant mb-1">{{ t('本期房费状态') }}</div>
                <div
                  class="inline-flex items-center px-2 py-1 rounded bg-[#e6f4ea] text-[#137333] text-xs font-medium border border-[#ceead6]"
                >
                  {{ t('已结清') }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>
