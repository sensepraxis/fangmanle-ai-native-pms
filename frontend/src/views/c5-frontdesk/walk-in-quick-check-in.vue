<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { commercialEnabled } from '../../lib/branding'

/**
 * 散客即时入住 —— 视觉对齐原型；业务：不对接收银机/制卡，确认入住并开客账
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { formatAiModelMeta } from '../../lib/aiModelMeta'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import OrdersFlowNav from '../../components/OrdersFlowNav.vue'

const router = useRouter()
const guest = ref<any>(null)
const rooms = ref<any[]>([])
const selectedRoomId = ref<number | null>(null)
const guestName = ref('')
const guestPhone = ref('')
const nights = ref(1)
const depositAmount = ref(200)
const needHint = ref('')
const submitting = ref(false)
const recommending = ref(false)
const idMasked = ref('')
const guestTip = ref('请手工登记姓名、手机与证件号码，再填写上方房间诉求并点「AI 推房」。')
const quote = ref({ rack: 0, online: 0, aiFloor: 0, floorLimit: 0 })
const doneOrder = ref<any>(null)
const showCardTip = ref(false)
const needTags = ref<string[]>([])
const recommendMeta = ref('')
const recommendSource = ref('')
const recommendModelMeta = ref('')
const hasRecommended = ref(false)

const selectedRoom = computed(() => rooms.value.find((r) => r.id === selectedRoomId.value) || null)

const totalHint = computed(() => {
  const rate = quote.value.aiFloor || 0
  const n = Math.max(1, Number(nights.value) || 1)
  return Math.round(rate * n)
})

const canRecommend = computed(() => {
  return Boolean(guestName.value.trim() && needHint.value.trim() && !recommending.value)
})

function statusLabel(s?: string) {
  if (s === 'clean' || s === 'vacant' || s === 'inspected') return t('空净')
  return s || '可用'
}

function resetIdentity() {
  guest.value = null
  guestName.value = ''
  guestPhone.value = ''
  idMasked.value = ''
  guestTip.value = t('请手工登记姓名、手机与证件号码，再填写上方房间诉求并点「AI 推房」。')
}

function resetRecommend() {
  rooms.value = []
  selectedRoomId.value = null
  needTags.value = []
  recommendMeta.value = ''
  recommendSource.value = ''
  recommendModelMeta.value = ''
  hasRecommended.value = false
  quote.value = { rack: 0, online: 0, aiFloor: 0, floorLimit: 0 }
}

async function load() {
  doneOrder.value = null
  showCardTip.value = false
  resetIdentity()
  resetRecommend()
  needHint.value = ''
}

function onIdScanDemo() {
  // 本区仅作引导：不自动生成证件号，请手工登记
  guestTip.value = t('请在下方手工填写姓名、手机与证件号码。')
}

function refreshQuote(pricing?: any[]) {
  const room = selectedRoom.value || rooms.value[0]
  if (!room) {
    quote.value = { rack: 0, online: 0, aiFloor: 0, floorLimit: 0 }
    return
  }
  const base = Number(room.base_price || room.ai_price || 400)
  const ai = Number(room.ai_price || base)
  const list = pricing || []
  const today = new Date().toISOString().slice(0, 10)
  const todayPs = list.filter((p: any) => {
    const d = String(p.biz_date || '').slice(0, 10)
    return !d || d === today
  })
  const pick = todayPs.find((p: any) => p.room_type_id === room.room_type_id) || todayPs[0]
  const suggested = Number(pick?.suggested_price || pick?.current_price || ai || base)
  const current = Number(pick?.current_price || base)
  quote.value = {
    rack: Math.round(current * 1.12 || base * 1.12),
    online: Math.round(current || base),
    aiFloor: Math.round(suggested),
    floorLimit: Math.round(suggested * 0.9),
  }
}

function pickRoom(id: number) {
  selectedRoomId.value = id
  refreshQuote()
}

async function runAiRecommend(pricingCache?: any[]) {
  if (!guestName.value.trim()) {
    toast(t('请先填写左侧入住人姓名'))
    return
  }
  const need = needHint.value.trim()
  if (!need) {
    toast(t('请先输入上方房间诉求'))
    return
  }
  if (recommending.value) return
  recommending.value = true
  try {
    const res = await api.roomsAiRecommend({
      hotel_id: hotelStore.hotelId,
      need,
      limit: 8,
    })
    rooms.value = res?.rooms || []
    needTags.value = res?.parsed?.tags || []
    recommendMeta.value = res?.message || ''
    recommendSource.value = String(res?.source || '')
    recommendModelMeta.value = formatAiModelMeta(res)
    hasRecommended.value = true
    selectedRoomId.value = rooms.value[0]?.id ?? null
    const pricing = pricingCache || (await api.listPricing(hotelStore.hotelId).catch(() => []))
    refreshQuote(pricing)
    if (rooms.value.length) {
      const via = recommendSource.value.startsWith('llm') ? t('智能推荐') : t('推荐')
      toast(t('AI 推房完成（{via}）· {n} 间', { via, n: rooms.value.length }))
    } else {
      toast(res?.message || t('暂无匹配房间'))
    }
  } catch (e: any) {
    toast(e?.message || t('AI 推房失败'))
  } finally {
    recommending.value = false
  }
}

async function confirmWalkIn() {
  if (submitting.value) return
  if (!selectedRoomId.value) {
    toast(t('请选择房间'))
    return
  }
  if (!guestName.value.trim()) {
    toast(t('请填写入住人姓名'))
    return
  }
  submitting.value = true
  try {
    const rtId = rooms.value.find((r) => r.id === selectedRoomId.value)?.room_type_id
    if (!rtId) throw new Error('房型无效')
    const o = await api.walkInCheckin({
      hotel_id: hotelStore.hotelId,
      guest_name: guestName.value.trim(),
      phone: guestPhone.value.trim() || undefined,
      id_doc_type: 'id_card',
      id_doc_no: idMasked.value.trim() || undefined,
      room_type_id: rtId,
      room_id: selectedRoomId.value,
      nights: Math.max(1, Number(nights.value) || 1),
      deposit_amount: Math.max(0, Number(depositAmount.value) || 0),
      note: `散客即时入住 · ${needHint.value || '无特殊偏好'}`,
    })
    doneOrder.value = o
    toast(t('已入住并开账'))
  } catch (e: any) {
    toast(e?.message || t('入住失败'), false)
  } finally {
    submitting.value = false
  }
}

function goOrder() {
  if (!doneOrder.value?.id) return
  router.push(`/orders/${doneOrder.value.id}`)
}

function goCashier() {
  if (!doneOrder.value?.id) return
  router.push(`/c5-frontdesk/cashiering-checkout?orderId=${doneOrder.value.id}`)
}

function resetFlow() {
  doneOrder.value = null
  showCardTip.value = false
  load()
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(selectedRoomId, () => refreshQuote())
watch([guestName, guestPhone], () => {
  if (guestName.value.trim()) {
    guestTip.value = t('已填写身份；请在上方输入房间诉求后点「AI 推房」。')
  }
})
</script>

<template>
  <div class="page">
    <div class="flex justify-between items-center flex-wrap gap-3 mb-4">
      <button type="button" class="back-link" style="margin: 0" @click="router.push('/orders')">
        <span class="material-symbols-outlined">arrow_back</span>{{ t('返回订单中心') }}
      </button>
      <OrdersFlowNav mode="base" hide-back />
    </div>

    <!-- 自然语言指令栏 + AI 推房 -->
    <div
      v-if="commercialEnabled()"
      style="position: relative; width: 100%; max-width: 1100px; margin: 0 auto 16px"
    >
      <div
        style="
          position: absolute;
          inset: 0 0 0 16px;
          display: flex;
          align-items: center;
          pointer-events: none;
        "
      >
        <span class="material-symbols-outlined" style="color: var(--tertiary)">mic</span>
      </div>
      <input
        v-model="needHint"
        class="toolbar-input"
        style="width: 100%; padding: 14px 140px 14px 44px; border-radius: 999px; font-size: 15px"
        :placeholder="t('例如：客人要一个安静的大床房，预算 700 元以内…')"
        @keydown.enter.prevent="runAiRecommend()"
      />
      <button
        type="button"
        class="btn btn-primary"
        style="
          position: absolute;
          right: 8px;
          top: 8px;
          bottom: 8px;
          border-radius: 999px;
          padding: 0 18px;
          display: flex;
          align-items: center;
          gap: 6px;
          font-weight: 700;
        "
        :disabled="!canRecommend"
        @click="runAiRecommend()"
      >
        <span class="material-symbols-outlined" style="font-size: 18px">auto_awesome</span>
        {{ recommending ? t('推房中…') : 'AI 推房' }}
      </button>
    </div>
    <div
      v-if="needTags.length || recommendMeta"
      style="
        max-width: 1100px;
        margin: 0 auto 20px;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
        justify-content: center;
      "
    >
      <span
        v-for="tag in needTags"
        :key="t"
        style="
          font-size: 12px;
          padding: 4px 10px;
          border-radius: 999px;
          background: var(--tertiary-fixed, #f3e8ff);
          color: var(--tertiary);
          font-weight: 600;
        "
        >{{ t }}</span
      >
      <span v-if="recommendModelMeta" style="font-size: 12px; color: var(--on-surface-variant)">{{
        recommendModelMeta
      }}</span>
      <span v-if="recommendMeta" style="font-size: 12px; color: var(--on-surface-variant)">{{
        recommendMeta
      }}</span>
    </div>

    <!-- 成功态：仍用原型卡片风格 -->
    <div
      v-if="doneOrder"
      class="card-clean card-pad"
      style="max-width: 1100px; margin: 0 auto; border-top: 4px solid var(--primary)"
    >
      <h2
        style="
          font-size: 18px;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 0 0 12px;
        "
      >
        <span
          class="material-symbols-outlined"
          style="color: var(--primary); font-variation-settings: 'FILL' 1"
          >check_circle</span
        >
        {{ t('入住完成，客账已开立') }}
      </h2>
      <p style="margin: 0 0 12px; font-size: 14px; color: var(--on-surface-variant)">
        {{ t('单号') }} {{ doneOrder.order_no }}
        <template v-if="doneOrder.folio_no"> · 账本 {{ doneOrder.folio_no }}</template>
        <template v-if="doneOrder.room_no"> · {{ doneOrder.room_no }} 房</template>
        <template v-if="doneOrder.checkin?.id_doc_mask">
          · 证件 {{ doneOrder.checkin.id_doc_mask }}</template
        >
      </p>
      <ul
        style="
          margin: 0 0 16px;
          padding-left: 18px;
          font-size: 13px;
          color: var(--on-surface-variant);
          line-height: 1.7;
        "
      >
        <li>{{ t('请用店内收银机收款（押金 / 房费）') }}</li>
        <li>{{ t('收款后在结账页录入支付方式与小票号') }}</li>
        <li>{{ t('房卡请在店内制卡机按房号制卡（系统不对接制卡机）') }}</li>
      </ul>
      <div style="display: flex; flex-wrap: wrap; gap: 10px">
        <button type="button" class="btn btn-primary" @click="goOrder">
          {{ t('查看订单与账本') }}
        </button>
        <button type="button" class="btn btn-ghost" @click="goCashier">
          {{ t('去录入收款') }}
        </button>
        <button type="button" class="btn btn-ghost" @click="showCardTip = !showCardTip">
          {{ t('制卡说明') }}
        </button>
        <button type="button" class="btn btn-ghost" @click="resetFlow">{{ t('再办一单') }}</button>
      </div>
      <p
        v-if="showCardTip"
        style="
          margin: 12px 0 0;
          padding: 10px 12px;
          background: var(--surface-container-low);
          border-radius: 8px;
          font-size: 12px;
          color: var(--on-surface-variant);
          line-height: 1.5;
        "
      >
        制卡机与酒店系统通常独立：在制卡软件输入房号 {{ doneOrder.room_no || '—' }} 与离店日期即可。
      </p>
    </div>

    <div
      v-else
      class="grid"
      style="grid-template-columns: 5fr 4fr 3fr; gap: 16px; align-items: start"
    >
      <!-- 左：身份信息采录 -->
      <div class="card-clean card-pad" style="border-bottom: 4px solid var(--primary)">
        <h2
          style="
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 0 0 16px;
          "
        >
          <span class="material-symbols-outlined" style="color: var(--primary)">id_card</span
          >{{ t('身份信息采录') }}
        </h2>
        <div
          style="
            height: 128px;
            border: 2px dashed var(--outline-variant);
            border-radius: 8px;
            background: var(--surface-container-lowest);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
            cursor: pointer;
          "
          @click="onIdScanDemo"
        >
          <span
            style="
              position: absolute;
              top: 0;
              left: 0;
              width: 100%;
              height: 2px;
              background: var(--primary);
              box-shadow: 0 0 8px rgba(0, 91, 191, 0.8);
            "
          />
          <span
            class="material-symbols-outlined"
            style="color: var(--primary); font-size: 36px; margin-bottom: 8px"
            >document_scanner</span
          >
          <p style="font-size: 13px; color: var(--on-surface-variant)">
            {{ t('请手工填写下方姓名、手机与证件号码') }}
          </p>
        </div>
        <div style="display: flex; flex-direction: column; gap: 16px">
          <div>
            <label
              style="
                display: block;
                font-size: 13px;
                color: var(--on-surface-variant);
                margin-bottom: 4px;
              "
              >{{ t('姓名') }}</label
            >
            <input
              v-model="guestName"
              class="toolbar-input"
              style="width: 100%"
              :placeholder="t('请输入姓名')"
            />
          </div>
          <div>
            <label
              style="
                display: block;
                font-size: 13px;
                color: var(--on-surface-variant);
                margin-bottom: 4px;
              "
              >{{ t('手机') }}</label
            >
            <input
              v-model="guestPhone"
              class="toolbar-input"
              style="width: 100%"
              :placeholder="t('选填')"
            />
          </div>
          <div>
            <label
              style="
                display: block;
                font-size: 13px;
                color: var(--on-surface-variant);
                margin-bottom: 4px;
              "
              >{{ t('证件号码') }}</label
            >
            <input
              v-model="idMasked"
              class="toolbar-input"
              style="width: 100%"
              :placeholder="t('请手工登记证件号码')"
              maxlength="18"
            />
          </div>
          <div
            style="
              display: flex;
              align-items: center;
              gap: 8px;
              padding: 12px;
              background: var(--primary-fixed);
              border: 1px solid var(--primary-fixed-dim);
              border-radius: 8px;
            "
          >
            <span class="material-symbols-outlined" style="color: var(--primary)"
              >verified_user</span
            >
            <span style="font-size: 13px; color: var(--on-primary-fixed)">{{ guestTip }}</span>
          </div>
        </div>
      </div>

      <!-- 中：AI 智能荐房 -->
      <div
        v-if="commercialEnabled()"
        class="card-clean card-pad"
        style="border-top: 4px solid var(--tertiary)"
      >
        <h2
          style="
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            margin: 0 0 16px;
          "
        >
          <span style="display: flex; align-items: center; gap: 8px">
            <span
              class="material-symbols-outlined"
              style="color: var(--tertiary); font-variation-settings: 'FILL' 1"
              >auto_awesome</span
            >{{ t('AI 智能荐房') }}</span
          >
          <span
            style="
              font-size: 12px;
              background: var(--surface-container-high);
              padding: 4px 8px;
              border-radius: 6px;
              color: var(--on-surface-variant);
            "
          >
            {{ needTags.length ? needTags.join(' · ') : t('基于需求') }}</span
          >
        </h2>
        <div style="display: flex; flex-direction: column; gap: 16px">
          <div
            v-if="recommending"
            style="text-align: center; color: var(--on-surface-variant); padding: 24px 16px"
          >
            {{ t('AI 正在检索空净可售房…') }}
          </div>
          <template v-else>
            <div
              v-for="(r, i) in rooms"
              :key="r.id"
              class="card-clean card-pad room-pick"
              :class="{ active: selectedRoomId === r.id }"
              :style="
                selectedRoomId === r.id
                  ? { border: '2px solid var(--primary)', background: 'rgba(0,91,191,0.06)' }
                  : { opacity: i === 0 ? 1 : 0.85 }
              "
              style="cursor: pointer; position: relative"
              @click="pickRoom(r.id)"
            >
              <div
                v-if="i === 0"
                style="
                  position: absolute;
                  top: 8px;
                  right: 8px;
                  background: var(--primary);
                  color: #fff;
                  font-size: 11px;
                  padding: 2px 8px;
                  border-radius: 6px;
                  font-weight: 700;
                "
              >
                {{ t('最佳匹配') }}
              </div>
              <div
                style="
                  display: flex;
                  justify-content: space-between;
                  align-items: flex-start;
                  margin-bottom: 8px;
                "
              >
                <div
                  :style="{
                    font: `700 22px 'Roboto Mono', monospace`,
                    color: i === 0 ? 'var(--primary)' : 'var(--on-surface)',
                  }"
                >
                  {{ r.room_no }}
                </div>
                <div style="font-size: 13px; color: var(--on-surface-variant)">
                  {{ r.room_type_name }}
                </div>
              </div>
              <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap">
                <span
                  style="
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    font-size: 12px;
                    padding: 2px 8px;
                    background: var(--surface-container-highest);
                    border-radius: 6px;
                  "
                >
                  <span
                    class="material-symbols-outlined"
                    style="font-size: 14px; color: #1e8e3e; font-variation-settings: 'FILL' 1"
                    >check_circle</span
                  >
                  {{ statusLabel(r.status) }}</span
                >
                <span
                  v-if="r.floor"
                  style="
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    font-size: 12px;
                    padding: 2px 8px;
                    background: var(--surface-container-highest);
                    border-radius: 6px;
                  "
                >
                  <span class="material-symbols-outlined" style="font-size: 14px">apartment</span
                  >{{ r.floor }} {{ t('楼') }}</span
                >
              </div>
              <p class="ai-insight">
                <span class="ai-label">{{ t('AI 分析：') }}</span>
                <span class="ai-body">{{
                  r.ai_tip ||
                  (i === 0
                    ? t('空净可即办，匹配散客即时入住。')
                    : `建议价 ¥${r.ai_price || r.base_price || '—'}。`)
                }}</span>
              </p>
            </div>
            <div
              v-if="!rooms.length"
              style="
                text-align: center;
                color: var(--on-surface-variant);
                padding: 28px 16px;
                line-height: 1.6;
                font-size: 13px;
              "
            >
              <template v-if="!hasRecommended"
                >{{ t('请先填写左侧身份信息与上方房间诉求，') }}<br />{{
                  t('再点击「AI 推房」获取推荐。')
                }}</template
              >
              <template v-else>{{ t('暂无匹配房间，请调整诉求后再次「AI 推房」') }}</template>
            </div>
          </template>
        </div>
      </div>

      <!-- 右：动态报价 + 操作 -->
      <div style="display: flex; flex-direction: column; gap: 16px">
        <div class="card-clean card-pad">
          <h2
            style="
              font-size: 18px;
              font-weight: 600;
              display: flex;
              align-items: center;
              gap: 8px;
              margin: 0 0 16px;
            "
          >
            <span class="material-symbols-outlined" style="color: var(--primary)">sell</span
            >{{ t('动态报价') }}
          </h2>
          <div
            style="
              background: var(--surface-container-low);
              border-radius: 8px;
              padding: 16px;
              text-align: center;
              margin-bottom: 16px;
            "
          >
            <div style="font-size: 13px; color: var(--on-surface-variant)">
              {{ t('今日门市价 / 网络最低价') }}
            </div>
            <div
              style="
                font:
                  500 14px 'Roboto Mono',
                  monospace;
                color: var(--outline);
                text-decoration: line-through;
              "
            >
              {{ quote.rack ? `¥${quote.rack} / ¥${quote.online}` : '— / —' }}
            </div>
            <div style="font-size: 13px; color: var(--tertiary); margin-top: 8px">
              {{ t('AI 建议散客底价') }}
            </div>
            <div
              style="
                font:
                  700 28px 'Roboto Mono',
                  monospace;
                color: var(--primary);
              "
            >
              {{ quote.aiFloor ? `¥${quote.aiFloor}` : '—' }}
            </div>
            <div style="font-size: 12px; color: var(--on-surface-variant); margin-top: 8px">
              <template v-if="quote.aiFloor">{{ nights }} 晚预估 · ¥{{ totalHint }}</template>
              <template v-else>{{ t('推房后显示报价') }}</template>
            </div>
          </div>
          <div
            style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px"
          >
            <div>
              <label
                style="
                  display: block;
                  font-size: 12px;
                  color: var(--on-surface-variant);
                  margin-bottom: 4px;
                "
                >{{ t('入住晚数') }}</label
              >
              <input
                v-model.number="nights"
                class="toolbar-input"
                style="width: 100%"
                type="number"
                min="1"
                max="30"
              />
            </div>
            <div>
              <label
                style="
                  display: block;
                  font-size: 12px;
                  color: var(--on-surface-variant);
                  margin-bottom: 4px;
                "
                >{{ t('建议收押金') }}</label
              >
              <input
                v-model.number="depositAmount"
                class="toolbar-input"
                style="width: 100%"
                type="number"
                min="0"
                step="50"
              />
            </div>
          </div>
          <div
            v-if="quote.floorLimit"
            style="
              background: var(--error-container);
              color: var(--on-error-container);
              padding: 8px 12px;
              border-radius: 8px;
              border: 1px solid rgba(186, 26, 26, 0.2);
              display: flex;
              align-items: flex-start;
              gap: 8px;
            "
          >
            <span class="material-symbols-outlined" style="color: var(--error); margin-top: 2px"
              >warning</span
            >
            <div style="font-size: 13px">
              <strong>{{ t('注意：') }}</strong
              >若低于 ¥{{ quote.floorLimit }}，需触发主管二次确认。
            </div>
          </div>
        </div>

        <div
          class="card-clean card-pad"
          style="
            display: flex;
            flex-direction: column;
            gap: 12px;
            border-top: 4px solid var(--surface-tint);
          "
        >
          <p style="margin: 0; font-size: 12px; color: var(--on-surface-variant); line-height: 1.5">
            {{
              t(
                '收银用店内收银机，制卡用独立制卡机。完成入住占房并开立客账；押金为登记金额，非即时扣款。',
              )
            }}
          </p>
          <button
            type="button"
            class="btn btn-ghost"
            style="
              width: 100%;
              padding: 12px;
              display: flex;
              align-items: center;
              justify-content: center;
              gap: 8px;
              font-weight: 700;
            "
            @click="showCardTip = !showCardTip"
          >
            <span class="material-symbols-outlined">contactless</span
            >{{ t('制卡说明（独立设备）') }}
          </button>
          <p
            v-if="showCardTip"
            style="
              margin: 0;
              font-size: 12px;
              color: var(--on-surface-variant);
              line-height: 1.45;
              padding: 8px 10px;
              background: var(--surface-container-low);
              border-radius: 8px;
            "
          >
            入住成功后，在制卡机输入房号
            {{ selectedRoom?.room_no || '—' }} 与离店日写卡。系统不发起制卡指令。
          </p>
          <button
            type="button"
            class="btn btn-primary"
            style="
              width: 100%;
              padding: 14px;
              display: flex;
              align-items: center;
              justify-content: center;
              gap: 8px;
              font-weight: 700;
            "
            :disabled="submitting || !selectedRoomId"
            @click="confirmWalkIn"
          >
            <span class="material-symbols-outlined">hotel</span>
            {{ submitting ? t('办理中…') : t('确认入住并开账') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar-input {
  padding: 8px 12px;
  border: 1px solid #e7e9ee;
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
  outline: none;
}
.ai-insight {
  margin: 0;
  padding-left: 8px;
  border-left: 2px solid var(--tertiary, #8c33b3);
  font-size: 13px;
  line-height: 1.45;
  color: var(--tertiary, #8c33b3);
  font-style: italic;
}
.ai-label {
  color: var(--tertiary, #8c33b3);
  font-style: italic;
  font-weight: 700;
}
.ai-body {
  color: var(--tertiary, #8c33b3);
  font-style: italic;
  font-weight: 600;
}
@media (max-width: 800px) {
  .page .grid {
    grid-template-columns: 1fr !important;
  }
}
@media (min-width: 801px) and (max-width: 1100px) {
  .page .grid {
    grid-template-columns: 1fr 1fr !important;
  }
}
</style>
