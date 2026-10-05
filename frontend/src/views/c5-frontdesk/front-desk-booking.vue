<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 前台预订：电话 / 企微等先建预订单（独立页，与团购/散客/团体一致） */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import OrdersFlowNav from '../../components/OrdersFlowNav.vue'

const router = useRouter()
const roomTypes = ref<any[]>([])
const channels = ref<any[]>([])
const submitting = ref(false)

const guestName = ref('')
const phone = ref('')
const roomTypeId = ref(0)
const channelId = ref(0)
const rooms = ref(1)
const checkIn = ref('')
const checkOut = ref('')
const note = ref('')
const externalOrderNo = ref('')
const status = ref('confirmed')

const selectedChannel = computed(() => channels.value.find((c) => c.id === channelId.value) || null)

const isOtaChannel = computed(() => {
  const code = String(selectedChannel.value?.code || '').toLowerCase()
  const type = String(selectedChannel.value?.type || '').toLowerCase()
  return type === 'ota' || ['ota', 'ctrip', 'meituan', 'fliggy'].includes(code)
})

const nights = computed(() => {
  if (!checkIn.value || !checkOut.value) return 1
  const a = new Date(checkIn.value).getTime()
  const b = new Date(checkOut.value).getTime()
  if (!(b > a)) return 1
  return Math.max(1, Math.round((b - a) / 86400000))
})

const unitPrice = computed(() => {
  const rt = roomTypes.value.find((t) => t.id === roomTypeId.value)
  return Number(rt?.base_price || 0)
})

const estimateTotal = computed(
  () =>
    Math.round(unitPrice.value * nights.value * Math.max(1, Number(rooms.value) || 1) * 100) / 100,
)

function initDates() {
  const t = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  checkIn.value = `${t.getFullYear()}-${p(t.getMonth() + 1)}-${p(t.getDate())}`
  const t2 = new Date(t.getTime() + 86400000)
  checkOut.value = `${t2.getFullYear()}-${p(t2.getMonth() + 1)}-${p(t2.getDate())}`
}

function preferDirectChannel() {
  const prefer = ['direct', 'wechat', 'wecom']
  for (const code of prefer) {
    const hit = channels.value.find((c) => c.code === code)
    if (hit) return hit.id
  }
  return channels.value[0]?.id || 0
}

async function loadMeta() {
  const [rts, chs] = await Promise.all([
    api.listRoomTypes(hotelStore.hotelId).catch(() => []),
    api.listChannels().catch(() => []),
  ])
  roomTypes.value = rts || []
  channels.value = chs || []
  if (!roomTypeId.value && roomTypes.value[0]) roomTypeId.value = roomTypes.value[0].id
  if (!channelId.value) channelId.value = preferDirectChannel()
}

async function submit() {
  if (!guestName.value.trim()) return toast(t('请填写客人姓名'))
  if (!roomTypeId.value) return toast(t('请选择房型'))
  if (!channelId.value) return toast(t('请选择渠道'))
  if (!checkIn.value || !checkOut.value) return toast(t('请填写入住/离店日期'))
  if (new Date(checkOut.value) <= new Date(checkIn.value)) return toast(t('离店日期须晚于入住'))
  if (isOtaChannel.value && !externalOrderNo.value.trim()) {
    return toast(t('OTA 渠道请填写渠道订单号'))
  }
  if (submitting.value) return
  submitting.value = true
  try {
    const data = await api.createOrder({
      hotel_id: hotelStore.hotelId,
      guest_name: guestName.value.trim(),
      phone: phone.value.trim() || undefined,
      room_type_id: roomTypeId.value,
      channel_id: channelId.value,
      check_in: checkIn.value,
      check_out: checkOut.value,
      rooms: Math.max(1, Number(rooms.value) || 1),
      note: note.value.trim() || undefined,
      status: status.value,
      external_order_no: externalOrderNo.value.trim() || undefined,
    })
    toast(t('预订单已创建 · {no}', { no: data.order_no || '' }))
    const id = data.id || data.order?.id
    if (id) router.push(`/orders/${id}`)
    else router.push('/orders?source=direct')
  } catch (e: any) {
    toast(e?.message || t('创建失败'))
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  initDates()
  await loadMeta()
})
</script>

<template>
  <div class="page booking-page form-shell">
    <div class="flex items-center justify-between flex-wrap gap-3 mb-5">
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="p-2 rounded-full hover:bg-surface-variant text-on-surface-variant"
          @click="router.push('/orders')"
        >
          <span class="material-symbols-outlined">arrow_back</span>
        </button>
        <div>
          <div class="text-xs text-on-surface-variant mb-0.5">{{ t('预订管理 / 前台预订') }}</div>
          <h1 class="font-headline-md text-headline-md text-on-surface">{{ t('新建前台预订') }}</h1>
        </div>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <OrdersFlowNav mode="base" hide-back />
        <button
          type="button"
          class="px-4 py-2 rounded-lg border border-outline-variant text-sm"
          @click="router.push('/orders')"
        >
          {{ t('取消') }}
        </button>
        <button
          type="button"
          class="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm shadow-sm disabled:opacity-60"
          :disabled="submitting"
          @click="submit"
        >
          {{ submitting ? t('提交中…') : t('提交确认') }}
        </button>
      </div>
    </div>

    <p class="hint">
      {{ t('电话、企微等先建预订单；到店后再分房入住。无预订单请走「散客即时入住」。') }}
    </p>

    <div class="form-shell-split">
      <section class="card">
        <h2 class="sec-title">{{ t('客人信息') }}</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label class="field">
            <span>{{ t('客人姓名') }}</span>
            <input v-model="guestName" :placeholder="t('张三')" />
          </label>
          <label class="field">
            <span>{{ t('手机号') }}</span>
            <input v-model="phone" placeholder="13800001234" />
          </label>
          <label class="field">
            <span>{{ t('订单状态') }}</span>
            <select v-model="status">
              <option value="pending">{{ t('待确认') }}</option>
              <option value="confirmed">{{ t('已确认') }}</option>
            </select>
          </label>
        </div>
      </section>

      <section class="card">
        <h2 class="sec-title">{{ t('住宿信息') }}</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label class="field">
            <span>{{ t('房型') }}</span>
            <select v-model.number="roomTypeId">
              <option v-for="rt in roomTypes" :key="rt.id" :value="rt.id">
                {{ rt.name }} · ¥{{ rt.base_price }}
              </option>
            </select>
          </label>
          <label class="field">
            <span>{{ t('间数') }}</span>
            <input v-model.number="rooms" type="number" min="1" max="20" />
          </label>
          <label class="field">
            <span>{{ t('渠道来源') }}</span>
            <select v-model.number="channelId">
              <option v-for="c in channels" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </label>
          <label class="field">
            <span>{{ t('入住') }}</span>
            <input v-model="checkIn" type="date" />
          </label>
          <label class="field">
            <span>{{ t('离店') }}</span>
            <input v-model="checkOut" type="date" />
          </label>
          <div class="nights-pill self-end">
            {{ t('共') }} <b>{{ nights }}</b> {{ t('晚 · 估房价') }} <b>¥{{ estimateTotal }}</b>
          </div>
          <label v-if="isOtaChannel" class="field sm:col-span-2">
            <span>{{ t('渠道订单号') }}</span>
            <input
              v-model="externalOrderNo"
              :placeholder="t('携程 / 美团 / 飞猪等平台单号（必填）')"
            />
          </label>
        </div>
      </section>

      <section class="card form-span">
        <h2 class="sec-title">{{ t('备注') }}</h2>
        <textarea
          v-model="note"
          rows="3"
          :placeholder="t('如：预计晚到、需静音房、企微对接人等')"
        />
      </section>
    </div>
  </div>
</template>

<style scoped>
.booking-page {
  width: 100%;
}
.hint {
  font-size: 13px;
  color: var(--on-surface-variant, #6b7280);
  margin: 0 0 14px;
}
.card {
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant, #e2e5ea);
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 14px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}
.sec-title {
  font-size: 14px;
  font-weight: 700;
  margin: 0 0 12px;
  color: var(--on-surface, #1f2329);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
}
.field input,
.field select,
.card textarea {
  border: 1px solid var(--outline-variant, #e2e5ea);
  background: var(--surface-container-low, #f4f6f8);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  color: var(--on-surface, #1f2329);
  outline: none;
}
.field input:focus,
.field select:focus,
.card textarea:focus {
  border-color: var(--primary, #005bbf);
}
.card textarea {
  width: 100%;
  resize: vertical;
  min-height: 72px;
}
.nights-pill {
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  border-radius: 8px;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
}
.nights-pill b {
  color: #111827;
  margin: 0 2px;
}
</style>
