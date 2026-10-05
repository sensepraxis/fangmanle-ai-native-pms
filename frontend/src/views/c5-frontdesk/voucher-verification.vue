<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 团购券核销：券码查询 → 展示 lookup 结果 → 录入客人 → verify 成单
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import OrdersFlowNav from '../../components/OrdersFlowNav.vue'

const router = useRouter()
const code = ref('')
const tab = ref<'single' | 'batch'>('single')
const queried = ref(false)
const looking = ref(false)
const verifying = ref(false)
const guestName = ref('')
const guestPhone = ref('')

type VoucherResult = {
  valid: boolean
  platform: string
  roomTitle: string
  roomShort: string
  roomTypeId: number | null
  extras: string[]
  rules: { icon: string; text: string; warn: boolean }[]
  availLabel: string
  availText: string
  floorTag: string
  faceValue: number
  channelId: number | null
}

type GuestMatch = {
  name: string
  phone: string
  phoneRaw: string
  tag: string
  historyType: string
  pref: string
  guestId: number | null
}

const result = ref<VoucherResult | null>(null)
const match = ref<GuestMatch | null>(null)
const upsell = ref<{ est: string; pct: number; body: string } | null>(null)

function maskPhone(p?: string) {
  const s = (p || '').replace(/\D/g, '')
  if (s.length < 7) return p || '—'
  return `${s.slice(0, 3)}****${s.slice(-4)}`
}

function availLabelOf(n: number) {
  if (n >= 8) return t('房源充足')
  if (n > 0) return t('紧张')
  return t('售罄')
}

async function resolveGuestMatch(phone: string) {
  const digits = (phone || '').replace(/\D/g, '')
  if (digits.length < 7) {
    match.value = null
    return
  }
  const guests = await api.listGuests(hotelStore.hotelId).catch(() => [])
  const g = (guests || []).find((x: any) => String(x.phone || '').replace(/\D/g, '') === digits)
  if (!g) {
    match.value = {
      name: guestName.value || '到店核销客人',
      phone: maskPhone(digits),
      phoneRaw: digits,
      tag: '新客',
      historyType: '—',
      pref: '—',
      guestId: null,
    }
    return
  }
  guestName.value = guestName.value || g.name || ''
  let tag = g.vip_level && g.vip_level !== 'normal' ? `VIP · ${g.vip_level}` : '老客回流'
  let historyType = '—'
  let pref = '—'
  try {
    const g360 = await api.guest360(g.id)
    const tags = (g360?.tags || []).map((t: any) => t.name).filter(Boolean)
    if (tags[0]) {
      pref = tags[0]
      tag = tags[0]
    }
    const last = (g360?.orders || [])[0]
    if (last?.room_type_name) historyType = last.room_type_name
  } catch {
    /* keep defaults */
  }
  match.value = {
    name: g.name,
    phone: maskPhone(g.phone),
    phoneRaw: g.phone || digits,
    tag,
    historyType,
    pref,
    guestId: g.id,
  }
}

async function buildUpsell(preferTypeName?: string) {
  const rooms = await api.listRooms(hotelStore.hotelId).catch(() => [])
  const vacant = (rooms || []).filter((r: any) =>
    ['vacant', 'clean', 'inspected'].includes(r.status),
  )
  const total = Math.max(1, (rooms || []).length)
  const vacantRate = Math.round((vacant.length / total) * 100)
  const deluxe = (rooms || []).find(
    (r: any) =>
      /豪华|海景|套房|Deluxe/i.test(r.room_type_name || '') &&
      ['vacant', 'clean', 'inspected'].includes(r.status) &&
      r.room_type_name !== preferTypeName,
  )
  if (!deluxe) {
    upsell.value = {
      est: '+¥0',
      pct: Math.min(90, vacantRate),
      body: `当前可用房 ${vacant.length} 间（空置约 ${vacantRate}%）。暂无更高房型可升级建议。`,
    }
    return
  }
  const base = Number(deluxe.base_price || 0)
  const ai = Number(deluxe.ai_price || 0)
  const uplift =
    ai > base * 0.5
      ? Math.max(50, Math.round(ai - base * 0.5))
      : Math.max(50, Math.round(base * 0.25))
  const discountPct = base > 0 ? Math.round((1 - (base - uplift) / Math.max(base, 1)) * 50) : 50
  upsell.value = {
    est: `+¥${uplift.toFixed(2)}`,
    pct: Math.min(90, Math.max(35, vacantRate)),
    body: `检测到「${deluxe.room_type_name}」空净可用，整店空置约 ${vacantRate}%。可按客史发送约 ${Math.min(50, Math.max(20, discountPct))}% 折扣升级邀请。`,
  }
}

async function doQuery() {
  const raw = code.value.trim()
  if (!raw) {
    toast(t('请输入券码'))
    return
  }
  if (looking.value) return
  looking.value = true
  queried.value = false
  result.value = null
  match.value = null
  try {
    const info = await api.voucherLookup({
      hotel_id: hotelStore.hotelId,
      voucher_code: raw,
    })
    const nights = Number(info.nights || 1)
    const typeName = info.room_type_name || '标准房'
    const vacant = Number(info.vacant_rooms || 0)
    result.value = {
      valid: !!info.valid,
      platform: info.platform || '团购',
      roomTitle: `${typeName} ${nights}晚`,
      roomShort: typeName,
      roomTypeId: info.room_type_id ?? null,
      extras: Array.isArray(info.extras) ? info.extras : [],
      rules: [
        { icon: 'calendar_today', text: `有效期至: ${info.expires_at || '—'}`, warn: false },
        {
          icon: 'info',
          text: info.rule_note || '周末及法定节假日可能需补差价',
          warn: true,
        },
      ],
      availLabel: availLabelOf(vacant),
      availText: `剩余 ${vacant} 间可用`,
      floorTag: String(info.floor_tag ?? '—').slice(0, 4),
      faceValue: Number(info.face_value || 0),
      channelId: info.channel_id ?? null,
    }
    await Promise.all([buildUpsell(typeName), resolveGuestMatch(guestPhone.value)])
    queried.value = true
  } catch (e: any) {
    toast(e?.message || t('券码无效'))
    queried.value = false
  } finally {
    looking.value = false
  }
}

async function onPhoneBlur() {
  if (!queried.value) return
  await resolveGuestMatch(guestPhone.value)
}

async function confirmVoucher() {
  if (!result.value || verifying.value) return
  const name = (guestName.value || match.value?.name || '').trim()
  if (!name) {
    toast(t('请填写入住人姓名'))
    return
  }
  verifying.value = true
  try {
    let rtId = result.value.roomTypeId
    if (!rtId) {
      const rooms = await api.listRooms(hotelStore.hotelId)
      rtId =
        rooms.find((r: any) => r.room_type_name === result.value!.roomShort)?.room_type_id ||
        rooms[0]?.room_type_id
    }
    const data = await api.voucherVerify({
      hotel_id: hotelStore.hotelId,
      voucher_code: code.value.trim(),
      guest_name: name,
      phone: (guestPhone.value || match.value?.phoneRaw || '').replace(/\D/g, '') || undefined,
      room_type_id: rtId,
      channel_id: result.value.channelId || undefined,
      auto_checkin: true,
    })
    toast(t('核销成功，已办理入住'))
    const oid = data?.order?.id
    if (oid) router.push(`/orders/${oid}`)
    else router.push('/orders')
  } catch (e: any) {
    toast(e?.message || t('核销失败'))
  } finally {
    verifying.value = false
  }
}

function sendUpsell() {
  if (!upsell.value) return
  toast(t('升房邀请已记录'))
}

watch(
  () => hotelStore.hotelId,
  () => {
    queried.value = false
    result.value = null
    match.value = null
    upsell.value = null
  },
)
</script>

<template>
  <div class="page voucher-page">
    <div class="flex items-center justify-between flex-wrap gap-3 mb-2">
      <div class="flex items-center gap-4">
        <button
          type="button"
          class="p-2 rounded-full hover:bg-surface-variant transition-colors text-on-surface-variant"
          @click="router.push('/orders')"
        >
          <span class="material-symbols-outlined">arrow_back</span>
        </button>
        <div>
          <h1 class="font-headline-md text-headline-md text-on-surface">{{ t('团购券核销') }}</h1>
          <p class="font-body-md text-body-md text-on-surface-variant mt-1">
            {{ t('支持抖音、美团等平台票券验证与快速落单') }}
          </p>
        </div>
      </div>
      <div class="flex items-center gap-3 flex-wrap justify-end">
        <div
          class="flex items-center gap-2 bg-surface-container-lowest px-4 py-2 rounded-full border border-outline-variant shadow-sm"
        >
          <div class="w-2.5 h-2.5 rounded-full bg-primary sync-dot" />
          <span class="font-label-lg text-label-lg text-on-surface-variant">{{
            t('抖音/美团 实时同步中')
          }}</span>
        </div>
        <OrdersFlowNav mode="base" hide-back />
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-12 gap-gutter">
      <div class="xl:col-span-8 flex flex-col gap-gutter">
        <div
          class="bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-sm p-6 overflow-hidden relative"
        >
          <div
            class="absolute -right-20 -top-20 w-64 h-64 bg-primary/5 rounded-full blur-3xl pointer-events-none"
          />
          <div class="flex border-b border-outline-variant mb-6 relative z-10">
            <button
              type="button"
              class="px-6 py-3 font-label-lg text-label-lg transition-colors"
              :class="
                tab === 'single'
                  ? 'font-bold text-primary border-b-2 border-primary'
                  : 'text-on-surface-variant hover:text-on-surface'
              "
              @click="tab = 'single'"
            >
              {{ t('单券核销') }}
            </button>
            <button
              type="button"
              class="px-6 py-3 font-label-lg text-label-lg transition-colors"
              :class="
                tab === 'batch'
                  ? 'font-bold text-primary border-b-2 border-primary'
                  : 'text-on-surface-variant hover:text-on-surface'
              "
              @click="tab = 'batch'"
            >
              {{ t('批量核销') }}
            </button>
          </div>

          <div v-if="tab === 'single'" class="flex flex-col gap-4 relative z-10">
            <label class="font-label-lg text-label-lg text-on-surface-variant">{{
              t('输入或扫码获取券码')
            }}</label>
            <div class="flex gap-4 flex-wrap">
              <div
                class="flex-1 min-w-[240px] relative flex items-center bg-surface-container-low rounded-xl border-2 border-outline-variant focus-within:border-primary transition-colors overflow-hidden"
              >
                <span class="material-symbols-outlined text-on-surface-variant pl-4"
                  >confirmation_number</span
                >
                <input
                  v-model="code"
                  class="code-input w-full bg-transparent border-none outline-none font-num-xl text-num-xl text-on-surface py-4 px-4 focus:ring-0 tracking-wider"
                  :placeholder="t('输入 12-16 位券码')"
                  type="text"
                  @keyup.enter="doQuery"
                />
                <button
                  type="button"
                  class="p-4 text-primary hover:bg-surface-variant transition-colors border-l border-outline-variant flex items-center gap-2 shrink-0"
                  @click="doQuery"
                >
                  <span class="material-symbols-outlined">qr_code_scanner</span>
                  <span class="font-label-lg text-label-lg font-medium">{{ t('扫码') }}</span>
                </button>
              </div>
              <button
                type="button"
                class="bg-primary text-on-primary rounded-xl px-8 font-headline-md text-headline-md shadow-sm hover:opacity-90 transition-opacity"
                :disabled="looking"
                @click="doQuery"
              >
                {{ looking ? t('查询中…') : t('查询') }}
              </button>
            </div>
          </div>

          <div v-else class="relative z-10 py-8 text-center text-on-surface-variant font-body-md">
            {{ t('批量核销暂未开放，请使用单券核销。') }}
          </div>
        </div>

        <div
          v-if="queried && result"
          class="bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-sm flex flex-col overflow-hidden"
        >
          <div
            class="bg-surface-container p-6 border-b border-outline-variant flex justify-between items-center flex-wrap gap-3"
          >
            <div class="flex items-center gap-3">
              <span class="material-symbols-outlined text-primary text-3xl icon-fill"
                >check_circle</span
              >
              <div>
                <h3 class="font-headline-md text-headline-md text-on-surface">
                  {{ t('券码有效，可核销') }}
                </h3>
                <p class="font-num-md text-num-md text-on-surface-variant mt-1">{{ code }}</p>
              </div>
            </div>
            <div class="platform-tag flex items-center gap-1 px-3 py-1 rounded-full border">
              <span class="material-symbols-outlined text-sm">local_mall</span>
              <span class="font-label-lg text-label-lg font-bold">{{ result.platform }}</span>
            </div>
          </div>

          <div class="p-6 grid grid-cols-2 gap-y-6 gap-x-8">
            <div class="col-span-2 md:col-span-1 flex flex-col gap-1">
              <span class="font-label-lg text-label-lg text-on-surface-variant">{{
                t('包含内容')
              }}</span>
              <div
                class="font-body-lg text-body-lg text-on-surface font-medium flex items-center gap-2"
              >
                <span class="material-symbols-outlined text-secondary">bed</span>
                {{ result.roomTitle }}
                <span
                  v-if="result.faceValue"
                  class="text-on-surface-variant font-num-md text-num-md"
                >
                  · ¥{{ result.faceValue.toFixed(0) }}</span
                >
              </div>
              <div
                v-if="result.extras.length"
                class="font-body-md text-body-md text-on-surface-variant pl-8 flex flex-col gap-1 mt-1"
              >
                <span v-for="(ex, i) in result.extras" :key="i">{{ ex }}</span>
              </div>
              <div v-else class="font-body-md text-body-md text-on-surface-variant pl-8 mt-1">
                {{ t('无附加权益说明') }}
              </div>
            </div>

            <div class="col-span-2 md:col-span-1 flex flex-col gap-1">
              <span class="font-label-lg text-label-lg text-on-surface-variant">{{
                t('使用规则')
              }}</span>
              <div class="font-body-md text-body-md text-on-surface flex flex-col gap-2">
                <div
                  v-for="(r, i) in result.rules"
                  :key="i"
                  class="flex items-center gap-2"
                  :class="r.warn ? 'text-error' : ''"
                >
                  <span
                    class="material-symbols-outlined text-sm"
                    :class="r.warn ? '' : 'text-on-surface-variant'"
                    >{{ r.icon }}</span
                  >
                  <span>{{ r.text }}</span>
                </div>
              </div>
            </div>

            <div class="col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div class="flex flex-col gap-1">
                <label class="font-label-lg text-label-lg text-on-surface-variant">{{
                  t('入住人姓名')
                }}</label>
                <input
                  v-model="guestName"
                  class="rounded-xl border border-outline-variant bg-surface-container-low px-3 py-2.5 font-body-md text-on-surface outline-none focus:border-primary"
                  :placeholder="t('必填')"
                />
              </div>
              <div class="flex flex-col gap-1">
                <label class="font-label-lg text-label-lg text-on-surface-variant">{{
                  t('手机号（可选，用于匹配客史）')
                }}</label>
                <input
                  v-model="guestPhone"
                  class="rounded-xl border border-outline-variant bg-surface-container-low px-3 py-2.5 font-body-md text-on-surface outline-none focus:border-primary"
                  :placeholder="t('填写后自动匹配')"
                  @blur="onPhoneBlur"
                />
              </div>
            </div>

            <div class="col-span-2 h-px bg-outline-variant/50" />

            <div
              class="col-span-2 flex items-center justify-between bg-surface-container-low p-4 rounded-xl border border-outline-variant flex-wrap gap-3"
            >
              <div class="flex items-center gap-4">
                <div
                  class="w-12 h-12 rounded-lg bg-primary-container flex items-center justify-center text-primary font-num-xl text-num-xl"
                >
                  {{ result.floorTag }}
                </div>
                <div>
                  <div class="font-body-md text-body-md text-on-surface font-medium">
                    {{ t('当前「') }}{{ result.roomShort }}」{{ t('房态') }}
                  </div>
                  <div class="font-label-lg text-label-lg text-on-surface-variant mt-0.5">
                    {{ result.availText }}
                  </div>
                </div>
              </div>
              <span
                class="avail-ok px-3 py-1 rounded font-label-lg text-label-lg flex items-center gap-1 border"
              >
                <span class="material-symbols-outlined text-sm">check</span>
                {{ result.availLabel }}</span
              >
            </div>
          </div>

          <div
            class="bg-surface-container p-4 border-t border-outline-variant flex justify-end gap-4 flex-wrap"
          >
            <button
              type="button"
              class="px-6 py-2 font-label-lg text-label-lg text-on-surface-variant hover:bg-surface-variant rounded-full transition-colors border border-outline-variant bg-surface-container-lowest"
              @click="router.push('/orders')"
            >
              {{ t('取消') }}
            </button>
            <button
              type="button"
              class="px-8 py-2 font-label-lg text-label-lg bg-primary text-on-primary rounded-full hover:opacity-90 transition-opacity shadow-sm flex items-center gap-2"
              :disabled="verifying"
              @click="confirmVoucher"
            >
              <span class="material-symbols-outlined text-sm">how_to_reg</span>
              {{ verifying ? t('核销中…') : t('确认核销并排房') }}
            </button>
          </div>
        </div>
      </div>

      <div class="xl:col-span-4 flex flex-col gap-gutter">
        <div
          class="bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-sm p-6 relative overflow-hidden"
        >
          <div class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary" />
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-tertiary">memory</span>
            <h3 class="font-headline-md text-headline-md text-on-surface">
              {{ t('AI 智能匹配分析') }}
            </h3>
          </div>

          <div v-if="match" class="flex items-center gap-4 mb-6">
            <div
              class="w-14 h-14 rounded-full border-2 border-surface-container-high bg-primary-container text-on-primary flex items-center justify-center font-bold"
            >
              {{ (match.name || '?').slice(0, 1) }}
            </div>
            <div>
              <div class="font-body-lg text-body-lg font-medium text-on-surface">
                {{ match.name }}
              </div>
              <div
                class="font-label-lg text-label-lg text-on-surface-variant flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-[14px]">phone_iphone</span>
                {{ match.phone }}
              </div>
            </div>
            <div
              class="ml-auto bg-surface-container-high px-2 py-1 rounded text-label-lg font-label-lg text-secondary whitespace-nowrap"
            >
              {{ match.tag }}
            </div>
          </div>
          <p v-else class="font-body-md text-body-md text-on-surface-variant mb-6 leading-relaxed">
            {{
              queried
                ? t('填写手机号后可匹配客史；未匹配时按新客核销。')
                : t('查询券码后，可按手机号匹配客史。')
            }}
          </p>

          <div class="grid grid-cols-2 gap-4 border-t border-outline-variant/50 pt-4">
            <div>
              <div class="font-label-lg text-label-lg text-on-surface-variant">
                {{ t('历史入住房型') }}
              </div>
              <div class="font-body-md text-body-md text-on-surface mt-1 font-medium">
                {{ match?.historyType || '—' }}
              </div>
            </div>
            <div>
              <div class="font-label-lg text-label-lg text-on-surface-variant">
                {{ t('消费偏好') }}
              </div>
              <div
                class="font-body-md text-body-md text-on-surface mt-1 font-medium flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-sm text-tertiary">restaurant</span>
                {{ match?.pref || '—' }}
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="upsell"
          class="upsell-card rounded-2xl border border-outline-variant shadow-md p-6 relative overflow-hidden group hover:shadow-lg transition-shadow"
        >
          <div class="relative z-10 flex flex-col h-full">
            <div class="flex items-center gap-2 mb-3">
              <span class="material-symbols-outlined text-on-tertiary-fixed-variant"
                >trending_up</span
              >
              <h3 class="font-headline-md text-headline-md text-on-tertiary-fixed">
                {{ t('AI 升房收益建议') }}
              </h3>
            </div>
            <p class="font-body-md text-body-md text-on-tertiary-fixed/90 leading-relaxed mb-6">
              {{ upsell.body }}
            </p>
            <div class="upsell-metric rounded-xl p-4 mb-6 border">
              <div class="flex justify-between items-center mb-2">
                <span class="font-label-lg text-label-lg text-on-tertiary-fixed">{{
                  t('预计额外收益')
                }}</span>
                <span class="font-num-xl text-num-xl text-on-tertiary-fixed font-bold">{{
                  upsell.est
                }}</span>
              </div>
              <div class="w-full bg-on-tertiary-fixed/10 rounded-full h-1.5">
                <div class="bg-tertiary h-1.5 rounded-full" :style="{ width: upsell.pct + '%' }" />
              </div>
            </div>
            <button
              type="button"
              class="mt-auto w-full upsell-cta rounded-xl py-3 font-label-lg text-label-lg flex items-center justify-center gap-2 hover:opacity-90 transition-opacity shadow-sm"
              @click="sendUpsell"
            >
              <span class="material-symbols-outlined text-sm">send</span>
              {{ t('一键发送升级邀请') }}
            </button>
          </div>
        </div>
        <div
          v-else
          class="rounded-2xl border border-dashed border-outline-variant bg-surface-container-lowest p-6 text-on-surface-variant font-body-md"
        >
          {{ t('查询券码后，将根据当前空房计算升房建议。') }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.voucher-page {
  background: var(--surface-container-low, #f2f4f5);
}

.sync-dot {
  animation: sync-pulse 1.6s ease-in-out infinite;
}

@keyframes sync-pulse {
  0%,
  100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(0, 91, 191, 0.45);
  }
  50% {
    opacity: 0.75;
    box-shadow: 0 0 0 6px rgba(0, 91, 191, 0);
  }
}

.icon-fill {
  font-variation-settings: 'FILL' 1;
}

.code-input {
  box-shadow: none !important;
}

.platform-tag {
  background: #ffe4e6;
  color: #e11d48;
  border-color: #fecdd3;
}

.avail-ok {
  background: #dcfce7;
  color: #166534;
  border-color: #bbf7d0;
}

.upsell-card {
  background: var(--tertiary-fixed, #f8d8ff);
}

.upsell-metric {
  background: color-mix(in srgb, var(--surface-container-lowest, #fff) 40%, transparent);
  border-color: color-mix(in srgb, var(--on-tertiary-fixed, #320047) 10%, transparent);
  backdrop-filter: blur(6px);
}

.upsell-cta {
  background: var(--on-tertiary-fixed, #320047);
  color: var(--on-primary, #fff);
}

.text-on-tertiary-fixed {
  color: var(--on-tertiary-fixed, #320047);
}
.text-on-tertiary-fixed-variant {
  color: var(--on-tertiary-fixed-variant, #721199);
}
.text-on-tertiary-fixed\/90 {
  color: color-mix(in srgb, var(--on-tertiary-fixed, #320047) 90%, transparent);
}
.bg-on-tertiary-fixed\/10 {
  background: color-mix(in srgb, var(--on-tertiary-fixed, #320047) 10%, transparent);
}
</style>
