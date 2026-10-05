<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 订单详情：客账 + 换房/续住/同住/加收/收款/证件揭密/登记单/未到店
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { fmt, ORDER_ST_CN, ORDER_ST_PILL, PAY_CN, PAY_PILL, toast } from '../lib/ui'
import {
  stayTypeLabel,
  formatOrderDateTime,
  isUnassignedOrder,
  assignStatusOf,
  ASSIGN_ST_CN,
  ASSIGN_ST_PILL,
  localizeLineDesc,
} from '../lib/orderFlow'

const route = useRoute()
const router = useRouter()
const o = ref<any>(null)
const rooms = ref<any[]>([])
const loading = ref(true)
const busy = ref(false)

const changeRoomId = ref<number | null>(null)
const extendNights = ref(1)
const roommate = ref({ guest_name: '', phone: '', id_doc_no: '' })
const chargeForm = ref({ amount: 50, description: '' })
const payForm = ref({ amount: 0, method: 'wechat', pos_slip_no: '' })
const revealMap = ref<Record<number, string>>({})

const SOURCE_LABEL: Record<string, string> = {
  ota: 'OTA 渠道',
  voucher: '团购核销',
  direct: '散客直订',
  group: '团体订单',
  map: '地图预订',
  geo: 'GEO 推荐',
  longstay: '常住客',
  agreement: '协议客',
  wechat: '私域/其他',
}

const LINE_ST: Record<string, string> = {
  held: '待分房',
  assigned: '已预分',
  checked_in: '在住',
  checked_out: '已退',
  cancelled: '已取消',
}

type CheckoutKind = 'prepaid' | 'collect' | 'corp'

function resolveKind(ord: any): CheckoutKind {
  const sg = String(ord?.source_group || '')
  const pay = String(ord?.payment_status || '')
  if (sg === 'agreement' || pay === 'on_account') return 'corp'
  if (sg === 'ota' || sg === 'voucher' || pay === 'paid') return 'prepaid'
  return 'collect'
}

const checkoutKind = computed(() => (o.value ? resolveKind(o.value) : 'collect'))
const checkoutBtnLabel = computed(() => {
  if (checkoutKind.value === 'corp') return t('挂账退房')
  if (checkoutKind.value === 'prepaid') return t('核对退房')
  return t('收银退房')
})

const folio = computed(() => o.value?.folio || null)
const checkins = computed(() => o.value?.checkins || [])
const groupLines = computed(() => o.value?.group_lines || [])
const deposits = computed(() => o.value?.deposits || null)
const depositItems = computed(() => deposits.value?.items || [])
const hasDeposits = computed(() => Number(deposits.value?.count || 0) > 0)
const depositHeld = computed(() => Number(deposits.value?.held_count || 0) > 0)
const isGroup = computed(
  () =>
    !!o.value?.is_group ||
    o.value?.order_type === 5 ||
    o.value?.source_group === 'group' ||
    !!o.value?.group_name,
)
const preAssignment = computed(() => o.value?.pre_assignment || null)
const roomAssignments = computed(() => o.value?.room_assignments || [])
const stayRoomNo = computed(
  () =>
    o.value?.stay_room_no || checkins.value.find((c: any) => c.status === 'inhouse')?.room_no || '',
)
const stayRoomId = computed(() => o.value?.stay_room_id || null)
const vacantRooms = computed(() =>
  rooms.value.filter((r) => ['vacant', 'clean', 'inspected'].includes(r.status)),
)
const canPreAssign = computed(() => {
  if (!o.value) return false
  return ['pending', 'confirmed'].includes(String(o.value.status || ''))
})
const assignLabel = computed(() =>
  o.value ? t(ASSIGN_ST_CN[assignStatusOf(o.value)] || assignStatusOf(o.value)) : '',
)

async function assignLine(line: any) {
  const candidates = vacantRooms.value.filter(
    (r) => !line.room_type_id || r.room_type_id === line.room_type_id,
  )
  if (!candidates.length) {
    toast(t('无匹配空净房'))
    return
  }
  const pick = candidates[0]
  if (!confirm(t('为第 {line} 行预分 {room}？', { line: line.line_no, room: pick.room_no }))) return
  busy.value = true
  try {
    await api.assignGroupLine(o.value.id, line.id, pick.id)
    toast(t('已预分 {room}', { room: pick.room_no }))
    await load()
  } catch (e: any) {
    toast(e?.message || t('排房失败'))
  } finally {
    busy.value = false
  }
}

async function checkinLine(line: any) {
  if (!confirm(t('确认第 {line} 行办理入住？', { line: line.line_no }))) return
  busy.value = true
  try {
    await api.checkinGroupLine(o.value.id, line.id, {
      guest_name: line.guest_name,
      room_id: line.room_id || undefined,
    })
    toast(t('该间已入住'))
    await load()
  } catch (e: any) {
    toast(e?.message || t('入住失败'))
  } finally {
    busy.value = false
  }
}

async function load() {
  loading.value = true
  try {
    o.value = await api.getOrder(Number(route.params.id))
    const bal = Number(o.value?.folio?.balance ?? o.value?.folio_balance ?? 0)
    payForm.value.amount = Math.max(0, bal)
    rooms.value = await api.listRooms(hotelStore.hotelId).catch(() => [])
  } finally {
    loading.value = false
  }
}
onMounted(() => {
  chargeForm.value.description = t('迷你吧/杂费')
  load()
})
watch(() => route.params.id, load)

async function doCheckin() {
  if (isUnassignedOrder(o.value)) {
    router.push({
      path: '/c5-frontdesk/pending-assignment',
      query: { orderId: String(o.value.id) },
    })
    return
  }
  if (!confirm(t('确认办理入住（使用已预分房间）？'))) return
  await api.checkin(o.value.id)
  toast(t('已办理入住'))
  load()
}
function goPreAssign() {
  router.push({ path: '/c5-frontdesk/pending-assignment', query: { orderId: String(o.value.id) } })
}
function goCheckout() {
  router.push({
    path: '/c5-frontdesk/cashiering-checkout',
    query: { orderId: String(o.value.id) },
  })
}
function goGuest() {
  if (o.value?.guest_id) router.push(`/guests/${o.value.guest_id}`)
}
function goRoom() {
  const id = stayRoomId.value || o.value?.pre_room_id
  if (id) router.push(`/rooms/${id}`)
}
function goRc() {
  router.push(`/c5-frontdesk/rc-print?orderId=${o.value.id}`)
}

function goDeposit(depositId?: string) {
  if (depositId) {
    router.push({ path: '/c9-finance/deposit-management', query: { open: depositId } })
  } else {
    router.push('/c9-finance/deposit-management')
  }
}

function depositStatusClass(st: string) {
  if (['RELEASED', 'RELEASED_AFTER_CAPTURE', 'CAPTURED'].includes(st)) return 'dep-ok'
  if (['EXPIRED', 'DISPUTED'].includes(st)) return 'dep-bad'
  if (st === 'PARTIAL_CAPTURE') return 'dep-warn'
  return 'dep-hold'
}

const ASSIGN_TYPE_CN: Record<string, string> = {
  pre_assign: '预分房',
  checkin: '入住分房',
  change: '换房',
  release: '释放',
}

async function run(fn: () => Promise<void>, okMsg: string) {
  if (busy.value) return
  busy.value = true
  try {
    await fn()
    toast(okMsg)
    await load()
  } catch (e: any) {
    toast(e?.message || t('操作失败'), false)
  } finally {
    busy.value = false
  }
}

function doChangeRoom() {
  if (!changeRoomId.value) {
    toast(t('请选择目标房间'), false)
    return
  }
  run(() => api.changeRoom(o.value.id, changeRoomId.value!, t('前台换房')), t('已换房'))
}
function doExtend() {
  run(() => api.extendStay(o.value.id, Math.max(1, Number(extendNights.value) || 1)), t('已续住'))
}
function doRoommate() {
  if (!roommate.value.guest_name.trim()) {
    toast(t('请填写同住人姓名'), false)
    return
  }
  run(
    () =>
      api.addRoommate(o.value.id, {
        guest_name: roommate.value.guest_name.trim(),
        phone: roommate.value.phone.trim() || undefined,
        id_doc_type: 'id_card',
        id_doc_no: roommate.value.id_doc_no.trim() || undefined,
      }),
    t('已添加同住人'),
  )
}
function doCharge() {
  run(
    () =>
      api.folioCharge(o.value.id, {
        amount: Number(chargeForm.value.amount),
        description: chargeForm.value.description,
      }),
    t('已加收'),
  )
}
function doPay() {
  if (!payForm.value.pos_slip_no.trim() && payForm.value.method !== 'cash') {
    toast(t('请录入收银小票号（现金可空）'), false)
    return
  }
  run(
    () =>
      api.folioPay(o.value.id, {
        amount: Number(payForm.value.amount),
        method: payForm.value.method,
        pos_slip_no: payForm.value.pos_slip_no.trim() || undefined,
        settle_type: 'partial',
      }),
    t('已收款入账'),
  )
}
function doNoShow() {
  if (!confirm(t('确认标记未到店？'))) return
  run(() => api.markNoShow(o.value.id, t('客人未到')), t('已标记未到店'))
}

const FOLIO_ST_CN: Record<string, string> = {
  open: '未结',
  partial: '部分结清',
  closed: '已结清',
}
const ENTRY_TYPE_CN: Record<string, string> = {
  room: '房费',
  room_charge: '房费',
  night_audit: '夜审日租',
  monthly_rent: '月租',
  misc: '杂费',
  fnb: '餐饮',
  deposit: '押金',
  tax: '税费',
  adjustment: '调账',
}
const PAY_METHOD_CN: Record<string, string> = {
  wechat: '微信',
  alipay: '支付宝',
  card: '银行卡',
  cash: '现金',
  pos: '收银机',
  transfer: '转账',
  on_account: '挂账',
}
async function doReveal(ci: any) {
  if (!ci?.id) return
  const password = window.prompt(t('二次校验：请输入当前登录密码以查看完整证件号'))
  if (password == null) return
  if (!String(password).trim()) {
    toast(t('已取消：需要密码二次校验'), false)
    return
  }
  const reason = window.prompt(t('查看原因（将写入不可删审计）'), t('前台核查')) || '前台核查'
  try {
    const r = await api.revealCheckinIdDoc(ci.id, {
      reason,
      password: String(password),
    })
    revealMap.value = { ...revealMap.value, [ci.id]: r.id_doc_no }
    toast(t('已解密并记审计（高权限+二次校验）'))
  } catch (e: any) {
    toast(e?.message || t('揭密失败'), false)
  }
}
</script>

<template>
  <div class="page order-detail">
    <a class="back-link" @click="router.push('/orders')">
      <span class="material-symbols-outlined" style="font-size: 18px">arrow_back</span>
      {{ t('返回订单列表') }}</a
    >

    <div v-if="loading" style="color: #9aa1ad; font-size: 13px">{{ t('加载中…') }}</div>
    <div v-else-if="o">
      <div class="page-actions">
        <div class="page-head" style="margin: 0">
          <h1>{{ o.order_no }}</h1>
          <p>
            {{ o.check_in }} ~ {{ o.check_out }} · {{ o.nights }} {{ t('晚 ·') }} {{ o.rooms }}
            {{ t('间') }}
          </p>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap">
          <button v-if="canPreAssign" class="btn btn-ghost" @click="doNoShow">
            {{ t('未到店') }}
          </button>
          <button
            v-if="canPreAssign && isUnassignedOrder(o) && !isGroup"
            class="btn btn-primary"
            @click="goPreAssign"
          >
            {{ t('待分房') }}
          </button>
          <button
            v-if="canPreAssign && !isUnassignedOrder(o) && !isGroup"
            class="btn btn-primary"
            @click="doCheckin"
          >
            {{ t('办理入住') }}
          </button>
          <button v-if="o.status === 'checked_in'" class="btn btn-ghost" @click="goRc">
            {{ t('入住登记单') }}
          </button>
          <button v-if="o.status === 'checked_in'" class="btn btn-primary" @click="goCheckout">
            {{ checkoutBtnLabel }}
          </button>
        </div>
      </div>

      <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap">
        <span class="pill" :class="ORDER_ST_PILL[o.status] || 'pill-slate'">{{
          t(ORDER_ST_CN[o.status] || o.status)
        }}</span>
        <span class="pill" :class="ASSIGN_ST_PILL[assignStatusOf(o)] || 'pill-slate'">{{
          assignLabel
        }}</span>
        <span class="pill" :class="PAY_PILL[o.payment_status] || 'pill-slate'">{{
          t(PAY_CN[o.payment_status] || o.payment_status)
        }}</span>
        <span class="pill pill-blue">{{ t(o.channel_name || '') }}</span>
        <span v-if="o.folio_no" class="pill pill-slate">{{ t('账本') }} {{ o.folio_no }}</span>
        <span v-if="o.source_group" class="pill pill-slate">{{
          t(SOURCE_LABEL[o.source_group] || o.source_group)
        }}</span>
        <span
          v-if="hasDeposits"
          class="pill deposit-pill"
          :title="depositHeld ? t('仍有在押押金') : t('押金已全部归零')"
        >
          {{ t('押金') }} {{ deposits.count }} {{ t('笔') }}
          <template v-if="depositHeld"> {{ t('· 在押') }} {{ fmt(deposits.held_yuan) }}</template>
          <template v-else> {{ t('· 已归零') }}</template>
        </span>
      </div>

      <div class="detail-split">
        <!-- 左栏 -->
        <div class="detail-col">
          <!-- 预订信息 -->
          <div class="card-clean card-pad">
            <div class="sec-title">{{ t('预订信息') }}</div>
            <div class="id-grid">
              <div>
                <span class="id-label">{{ t('系统订单号') }}</span
                ><b class="mono">{{ o.order_no }}</b>
              </div>
              <div>
                <span class="id-label">{{ t('渠道订单号') }}</span
                ><b class="mono">{{ o.external_order_no || '—' }}</b>
              </div>
              <div>
                <span class="id-label">{{ t('预分房单号') }}</span
                ><b class="mono">{{ o.reception_no || '—' }}</b>
              </div>
              <div>
                <span class="id-label">{{ t('入住类型') }}</span
                ><b>{{ stayTypeLabel(o) }}</b>
              </div>
              <div>
                <span class="id-label">{{ t('预订房型') }}</span
                ><b>{{ o.room_type_name || '—' }}</b>
              </div>
              <div>
                <span class="id-label">{{ t('创建时间') }}</span
                ><b>{{ formatOrderDateTime(o.created_at) }}</b>
              </div>
              <div>
                <span class="id-label">{{ t('主客') }}</span
                ><b>{{ o.guest_name }}</b>
              </div>
              <div>
                <span class="id-label">{{ t('手机') }}</span
                ><b>{{ o.phone || '—' }}</b>
              </div>
              <div v-if="isGroup">
                <span class="id-label">{{ t('团体名称') }}</span
                ><b>{{ o.group_name || '—' }}</b>
              </div>
              <div v-if="isGroup">
                <span class="id-label">{{ t('团队类型') }}</span
                ><b>{{ o.group_type || '—' }}</b>
              </div>
              <div v-if="isGroup">
                <span class="id-label">{{ t('结账形式') }}</span
                ><b>{{ o.settle_mode === 'split' ? t('分账结账') : t('统一结账') }}</b>
              </div>
              <div v-if="isGroup">
                <span class="id-label">{{ t('结算单位') }}</span
                ><b>{{ o.settle_party || '—' }}</b>
              </div>
              <div v-if="isGroup">
                <span class="id-label">{{ t('销售') }}</span
                ><b>{{ o.sales_name || '—' }}</b>
              </div>
              <div v-if="isGroup">
                <span class="id-label">{{ t('房间行') }}</span
                ><b>{{ groupLines.length }} {{ t('间') }}</b>
              </div>
              <div v-if="isGroup && o.room_fee_total != null">
                <span class="id-label">{{ t('房费合计') }}</span
                ><b>{{ fmt(o.room_fee_total) }}</b>
              </div>
              <div v-if="isGroup && o.other_amount">
                <span class="id-label">{{ t('其他费用') }}</span
                ><b>{{ fmt(o.other_amount) }}</b>
              </div>
              <div v-if="isGroup && o.deposit_amount">
                <span class="id-label">{{ t('已收定金') }}</span
                ><b>{{ fmt(o.deposit_amount) }}</b>
              </div>
              <div v-if="isGroup && o.balance_due != null">
                <span class="id-label">{{ t('应付余额') }}</span
                ><b>{{ fmt(o.balance_due) }}</b>
              </div>
              <div>
                <span class="id-label">{{ t('入离日期') }}</span
                ><b>{{ o.check_in }} → {{ o.check_out }}</b>
              </div>
            </div>
            <button class="btn btn-link" style="margin-top: 10px; padding: 0" @click="goGuest">
              {{ t('客户 360 ↗') }}
            </button>
          </div>

          <!-- 押金（有记录时蓝色标识） -->
          <div v-if="hasDeposits" class="card-clean card-pad deposit-card">
            <div class="sec-title deposit-title">
              {{ t('押金') }}
              <button type="button" class="btn btn-link deposit-link" @click="goDeposit()">
                {{ t('押金管理 ↗') }}
              </button>
            </div>
            <p class="deposit-summary">
              {{ t('共') }} <b>{{ deposits.count }}</b> {{ t('笔') }}
              <template v-if="depositHeld">
                {{ t('· 在押') }} <b>{{ deposits.held_count }}</b> {{ t('笔，合计') }}
                <b>{{ fmt(deposits.held_yuan) }}</b>
              </template>
              <template v-else>{{ t('· 已全部归零') }}</template>
            </p>
            <div class="deposit-list">
              <button
                v-for="d in depositItems"
                :key="d.deposit_id"
                type="button"
                class="deposit-row"
                @click="goDeposit(d.deposit_id)"
              >
                <div class="deposit-row-top">
                  <span class="mono">{{ d.deposit_id }}</span>
                  <span class="dep-pill" :class="depositStatusClass(d.status)">{{
                    d.status_label
                  }}</span>
                </div>
                <div class="deposit-row-meta">
                  {{ d.form_label }} · 原额 {{ fmt(d.original_yuan) }} · 可退
                  {{ fmt(d.remaining_yuan) }}
                </div>
              </button>
            </div>
          </div>

          <!-- 团体房间明细 -->
          <div v-if="isGroup" class="card-clean card-pad">
            <div class="sec-title">团体房间明细 · {{ groupLines.length }} {{ t('间') }}</div>
            <div v-if="!groupLines.length" style="font-size: 13px; color: #9aa1ad">
              {{ t('暂无房间行') }}
            </div>
            <div v-else class="table-scroll">
              <table class="table" style="width: 100%; font-size: 13px">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>{{ t('客人姓名') }}</th>
                    <th>{{ t('证件后四位') }}</th>
                    <th>{{ t('房型') }}</th>
                    <th>{{ t('房号') }}</th>
                    <th>{{ t('入离') }}</th>
                    <th>{{ t('状态') }}</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="line in groupLines" :key="line.id">
                    <td>{{ line.line_no }}</td>
                    <td>{{ line.guest_name || '—' }}</td>
                    <td class="mono">{{ line.id_last4 || '—' }}</td>
                    <td>{{ line.room_type_name || '—' }}</td>
                    <td class="mono">{{ line.room_no || t('待分配') }}</td>
                    <td style="font-size: 12px">
                      {{ (line.stay_check_in || o.check_in || '').slice(5) || '—' }}
                      →
                      {{ (line.stay_check_out || o.check_out || '').slice(5) || '—' }}
                    </td>
                    <td>{{ t(LINE_ST[line.status] || line.status) }}</td>
                    <td style="text-align: right; white-space: nowrap">
                      <button
                        v-if="line.status === 'held'"
                        class="btn btn-ghost btn-sm"
                        type="button"
                        :disabled="busy"
                        @click="assignLine(line)"
                      >
                        {{ t('排房') }}
                      </button>
                      <button
                        v-if="line.status === 'held' || line.status === 'assigned'"
                        class="btn btn-primary btn-sm"
                        type="button"
                        :disabled="busy"
                        @click="checkinLine(line)"
                      >
                        {{ t('入住') }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 预分房（非团体） -->
          <div
            v-if="!isGroup && (canPreAssign || preAssignment?.room_no)"
            class="card-clean card-pad"
          >
            <div
              style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 8px;
                margin-bottom: 10px;
                flex-wrap: wrap;
              "
            >
              <div class="sec-title" style="margin-bottom: 0">{{ t('预分房') }}</div>
              <button
                v-if="canPreAssign"
                type="button"
                class="btn btn-primary btn-sm"
                @click="goPreAssign"
              >
                {{ preAssignment?.room_no ? t('重新预分') : t('去分房') }}
              </button>
            </div>
            <p style="margin: 0 0 10px; font-size: 12px; color: #9aa1ad">
              {{ t('订单侧可空占房，非权威实体房；入住后以「入住登记」为准。') }}
            </p>
            <div v-if="preAssignment?.room_no" class="id-grid">
              <div>
                <span class="id-label">{{ t('预分至') }}</span
                ><b class="link" @click="goRoom">{{ preAssignment.room_no }}</b>
              </div>
              <div>
                <span class="id-label">{{ t('房型') }}</span
                ><b>{{ preAssignment.room_type_name || o.room_type_name || '—' }}</b>
              </div>
              <div>
                <span class="id-label">{{ t('操作人') }}</span
                ><b>{{ preAssignment.assigned_by_name || '—' }}</b>
              </div>
              <div>
                <span class="id-label">{{ t('预分时间') }}</span
                ><b>{{ formatOrderDateTime(preAssignment.assigned_at) }}</b>
              </div>
            </div>
            <div v-else style="font-size: 13px; color: #9aa1ad">{{ t('尚未预分房') }}</div>
          </div>

          <!-- 入住登记 -->
          <div class="card-clean">
            <div class="card-head">
              <span>{{ t('入住登记') }}</span>
            </div>
            <div style="padding: 16px">
              <template
                v-if="o.status === 'checked_in' || o.status === 'checked_out' || checkins.length"
              >
                <div class="id-grid" style="margin-bottom: 12px">
                  <div>
                    <span class="id-label">{{ t('在住房（权威）') }}</span>
                    <b>
                      <span v-if="stayRoomNo" class="link" @click="goRoom">{{ stayRoomNo }} ↗</span>
                      <span v-else style="color: #9aa1ad">—</span>
                    </b>
                  </div>
                  <div>
                    <span class="id-label">{{ t('入住状态') }}</span
                    ><b>{{ t(ORDER_ST_CN[o.status] || o.status) }}</b>
                  </div>
                </div>
                <div
                  v-for="ci in checkins"
                  :key="ci.id"
                  style="border-top: 1px solid #eef0f4; padding: 10px 0; font-size: 12px"
                >
                  <div
                    style="display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap"
                  >
                    <span
                      >{{ ci.guest_name || t('入住人') }} · {{ ci.room_no || '—' }} ·
                      {{ ci.id_doc_type || t('证件') }}</span
                    >
                    <b class="mono">{{ revealMap[ci.id] || ci.id_doc_mask || '—' }}</b>
                  </div>
                  <button
                    v-if="ci.has_id_doc && !revealMap[ci.id]"
                    type="button"
                    class="btn btn-link"
                    style="padding: 0; font-size: 12px"
                    @click="doReveal(ci)"
                  >
                    {{ t('查看完整证件号（审计）') }}
                  </button>
                </div>
              </template>
              <div v-else style="font-size: 13px; color: #9aa1ad">
                {{ t('尚未办理入住，无入住登记') }}
              </div>

              <div v-if="roomAssignments.length" style="margin-top: 14px">
                <div class="sec-title" style="font-size: 12px; margin-bottom: 6px">
                  {{ t('分房历史') }}
                </div>
                <div class="table-scroll">
                  <table class="data">
                    <thead>
                      <tr>
                        <th>{{ t('时间') }}</th>
                        <th>{{ t('类型') }}</th>
                        <th>{{ t('从') }}</th>
                        <th>{{ t('到') }}</th>
                        <th>{{ t('操作人') }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="a in roomAssignments" :key="a.id">
                        <td>{{ formatOrderDateTime(a.created_at) }}</td>
                        <td>{{ t(ASSIGN_TYPE_CN[a.assign_type] || a.assign_type) }}</td>
                        <td>{{ a.from_room_no || '—' }}</td>
                        <td>{{ a.to_room_no || '—' }}</td>
                        <td>{{ a.operator_name || '—' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右栏 -->
        <div class="detail-col">
          <!-- 客账 -->
          <div class="card-clean">
            <div class="card-head">
              <span>{{ t('客账') }}</span>
              <span v-if="folio" class="pill pill-slate"
                >{{ t('余额') }} {{ fmt(folio.balance) }}</span
              >
            </div>
            <div style="padding: 12px 16px">
              <div v-if="!folio" style="color: #9aa1ad; font-size: 13px; padding: 12px 0">
                {{ t('尚未开账（入住后生成）') }}
              </div>
              <template v-else>
                <div
                  style="
                    display: flex;
                    gap: 16px;
                    font-size: 12px;
                    margin-bottom: 10px;
                    color: var(--on-surface-variant);
                  "
                >
                  <span>{{ t('收费') }} {{ fmt(folio.charge_total) }}</span>
                  <span>{{ t('已收') }} {{ fmt(folio.payment_total) }}</span>
                  <span>{{ t('状态') }} {{ t(FOLIO_ST_CN[folio.status] || folio.status) }}</span>
                </div>
                <div class="table-scroll">
                  <table class="data">
                    <thead>
                      <tr>
                        <th>{{ t('日期') }}</th>
                        <th>{{ t('类型') }}</th>
                        <th>{{ t('摘要') }}</th>
                        <th class="num">{{ t('金额') }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="e in folio.entries || []" :key="e.id">
                        <td>{{ e.biz_date || '—' }}</td>
                        <td>{{ t(ENTRY_TYPE_CN[e.entry_type] || e.entry_type || '—') }}</td>
                        <td>{{ localizeLineDesc(e.description) }}</td>
                        <td class="num">{{ fmt(e.amount) }}</td>
                      </tr>
                      <tr v-if="!(folio.entries || []).length">
                        <td colspan="4" style="text-align: center; color: #9aa1ad">
                          {{ t('暂无分录') }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="(folio.payments || []).length" style="margin-top: 10px; font-size: 12px">
                  <div style="font-weight: 600; margin-bottom: 4px">{{ t('收款记录') }}</div>
                  <div
                    v-for="p in folio.payments"
                    :key="p.id"
                    style="display: flex; justify-content: space-between; gap: 8px"
                  >
                    <span
                      >{{ t(PAY_METHOD_CN[p.method] || p.method || '收银') }} · {{ t('小票') }}
                      {{ p.pos_slip_no || '—' }}</span
                    >
                    <b>{{ fmt(p.received_amount ?? p.amount) }}</b>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- 预订行项目 -->
          <div class="card-clean">
            <div class="card-head">
              <span>{{ t('预订行项目') }}</span>
            </div>
            <div style="padding: 16px">
              <div class="table-scroll">
                <table class="data">
                  <thead>
                    <tr>
                      <th>{{ t('项目') }}</th>
                      <th class="num">{{ t('数量') }}</th>
                      <th class="num">{{ t('金额') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="it in o.items" :key="it.id">
                      <td>{{ localizeLineDesc(it.description) }}</td>
                      <td class="num">{{ it.qty }}</td>
                      <td class="num">{{ fmt(it.amount) }}</td>
                    </tr>
                    <tr v-if="!o.items?.length">
                      <td colspan="3" style="text-align: center; color: #9aa1ad">
                        {{ t('暂无明细') }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div
                style="
                  display: flex;
                  justify-content: space-between;
                  margin-top: 12px;
                  font-size: 14px;
                "
              >
                <b>{{ t('订单合计') }}</b>
                <b class="tnum" style="color: var(--primary); font-size: 18px">{{
                  fmt(o.total_amount)
                }}</b>
              </div>
            </div>
          </div>

          <!-- 备注 -->
          <div v-if="o.note" class="card-clean card-pad">
            <div class="sec-title">{{ t('备注') }}</div>
            <div style="font-size: 13px; color: var(--on-surface); white-space: pre-wrap">
              {{ o.note }}
            </div>
          </div>
        </div>

        <!-- 底部全宽：在住操作 -->
        <div v-if="o.status === 'checked_in'" class="detail-span">
          <div class="card-clean card-pad">
            <div class="sec-title">{{ t('在住操作') }}</div>
            <div class="ops-grid">
              <div class="ops-box">
                <div class="ops-title">{{ t('换房') }}</div>
                <select v-model.number="changeRoomId" class="toolbar-input" style="width: 100%">
                  <option :value="null">{{ t('选择空净房') }}</option>
                  <option v-for="r in vacantRooms" :key="r.id" :value="r.id">
                    {{ r.room_no }} · {{ r.room_type_name || '' }} · {{ r.floor || '?' }}
                    {{ t('楼') }}
                  </option>
                </select>
                <button
                  class="btn btn-primary"
                  style="width: 100%; margin-top: 8px"
                  :disabled="busy"
                  @click="doChangeRoom"
                >
                  {{ t('确认换房') }}
                </button>
              </div>
              <div class="ops-box">
                <div class="ops-title">{{ t('续住') }}</div>
                <label style="font-size: 12px; color: var(--on-surface-variant)">{{
                  t('延长晚数')
                }}</label>
                <input
                  v-model.number="extendNights"
                  class="toolbar-input"
                  style="width: 100%"
                  type="number"
                  min="1"
                  max="60"
                />
                <button
                  class="btn btn-primary"
                  style="width: 100%; margin-top: 8px"
                  :disabled="busy"
                  @click="doExtend"
                >
                  {{ t('确认续住') }}
                </button>
              </div>
              <div class="ops-box">
                <div class="ops-title">{{ t('同住人') }}</div>
                <input
                  v-model="roommate.guest_name"
                  class="toolbar-input"
                  style="width: 100%; margin-bottom: 6px"
                  :placeholder="t('姓名')"
                />
                <input
                  v-model="roommate.phone"
                  class="toolbar-input"
                  style="width: 100%; margin-bottom: 6px"
                  :placeholder="t('手机（选填）')"
                />
                <input
                  v-model="roommate.id_doc_no"
                  class="toolbar-input"
                  style="width: 100%"
                  :placeholder="t('证件号（选填）')"
                />
                <button
                  class="btn btn-primary"
                  style="width: 100%; margin-top: 8px"
                  :disabled="busy"
                  @click="doRoommate"
                >
                  {{ t('添加同住') }}
                </button>
              </div>
              <div class="ops-box">
                <div class="ops-title">{{ t('住中加收') }}</div>
                <input
                  v-model="chargeForm.description"
                  class="toolbar-input"
                  style="width: 100%; margin-bottom: 6px"
                  :placeholder="t('摘要')"
                />
                <input
                  v-model.number="chargeForm.amount"
                  class="toolbar-input"
                  style="width: 100%"
                  type="number"
                  step="1"
                />
                <button
                  class="btn btn-primary"
                  style="width: 100%; margin-top: 8px"
                  :disabled="busy"
                  @click="doCharge"
                >
                  {{ t('记入客账') }}
                </button>
              </div>
              <div class="ops-box">
                <div class="ops-title">{{ t('收银收款（小票）') }}</div>
                <select
                  v-model="payForm.method"
                  class="toolbar-input"
                  style="width: 100%; margin-bottom: 6px"
                >
                  <option value="wechat">{{ t('微信/支付宝') }}</option>
                  <option value="card">{{ t('银行卡') }}</option>
                  <option value="cash">{{ t('现金') }}</option>
                </select>
                <input
                  v-model="payForm.pos_slip_no"
                  class="toolbar-input"
                  style="width: 100%; margin-bottom: 6px"
                  :placeholder="t('收银小票号')"
                />
                <input
                  v-model.number="payForm.amount"
                  class="toolbar-input"
                  style="width: 100%"
                  type="number"
                  step="0.01"
                />
                <button
                  class="btn btn-primary"
                  style="width: 100%; margin-top: 8px"
                  :disabled="busy"
                  @click="doPay"
                >
                  {{ t('确认收款') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sec-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
}
.id-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 16px;
  font-size: 13px;
}
.id-label {
  display: block;
  color: var(--on-surface-variant, #5b616e);
  font-size: 11px;
  margin-bottom: 2px;
}
.ops-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.ops-box {
  border: 1px solid #e7e9ee;
  border-radius: 10px;
  padding: 12px;
  background: #fafbfc;
}
.ops-title {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
}
.toolbar-input {
  padding: 8px 10px;
  border: 1px solid #e7e9ee;
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
}
.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
@media (min-width: 1100px) {
  .id-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .ops-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}
.deposit-pill {
  background: #e8f0fe;
  color: #1a56db;
  border: 1px solid #bfdbfe;
  font-weight: 600;
}
.deposit-card {
  border-color: #bfdbfe;
  background: #f8fbff;
}
.deposit-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #1a56db;
}
.deposit-link {
  padding: 0;
  font-size: 12px;
  color: #1a56db;
  font-weight: 600;
}
.deposit-summary {
  margin: 0 0 10px;
  font-size: 13px;
  color: #1a56db;
  line-height: 1.5;
}
.deposit-summary b {
  color: #1e40af;
}
.deposit-list {
  display: grid;
  gap: 8px;
}
.deposit-row {
  width: 100%;
  text-align: left;
  border: 1px solid #bfdbfe;
  background: #fff;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  color: #1a56db;
}
.deposit-row:hover {
  border-color: #1a56db;
  background: #eff6ff;
}
.deposit-row-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
}
.deposit-row-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #3b82f6;
}
.dep-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}
.dep-hold {
  background: #dbeafe;
  color: #1e40af;
}
.dep-warn {
  background: #fff3e0;
  color: #ef6c00;
}
.dep-bad {
  background: #fdecea;
  color: #c62828;
}
.dep-ok {
  background: #e8f5e9;
  color: #2e7d32;
}
</style>
