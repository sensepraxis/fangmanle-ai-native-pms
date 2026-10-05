<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/** 团体订单创建：字段对齐原型（基本信息 / 房量 / 分房清单 / 费用 / 备注） */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import OrdersFlowNav from '../../components/OrdersFlowNav.vue'

const router = useRouter()
const roomTypes = ref<any[]>([])
const submitting = ref(false)

const groupName = ref('')
const groupType = ref('旅游团')
const status = ref('confirmed')
const contactName = ref('')
const contactPhone = ref('')
const settleMode = ref('unified')
const settleParty = ref('')
const salesName = ref('')
const checkIn = ref('')
const checkOut = ref('')
const note = ref('')
const otherAmount = ref(0)
const depositAmount = ref(0)

type BlockRow = { room_type_id: number; qty: number; unit_price: number }
type LineRow = {
  guest_name: string
  id_last4: string
  room_type_id: number
  check_in: string
  check_out: string
  note: string
}

const blocks = ref<BlockRow[]>([])
const lines = ref<LineRow[]>([])

const nights = computed(() => {
  if (!checkIn.value || !checkOut.value) return 1
  const a = new Date(checkIn.value).getTime()
  const b = new Date(checkOut.value).getTime()
  if (!(b > a)) return 1
  return Math.max(1, Math.round((b - a) / 86400000))
})

const roomFeeTotal = computed(() =>
  round2(
    blocks.value.reduce(
      (s, b) => s + Number(b.unit_price || 0) * Math.max(1, Number(b.qty || 1)) * nights.value,
      0,
    ),
  ),
)
const grandTotal = computed(() => round2(roomFeeTotal.value + Number(otherAmount.value || 0)))
const balanceDue = computed(() =>
  round2(Math.max(0, grandTotal.value - Number(depositAmount.value || 0))),
)

function round2(n: number) {
  return Math.round(n * 100) / 100
}

function fmtMoney(n: number) {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function defaultRtId() {
  return roomTypes.value[0]?.id || 0
}

function priceOf(rtId: number) {
  const rt = roomTypes.value.find((t) => t.id === rtId)
  return Number(rt?.base_price || 0)
}

function initDates() {
  const t = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  checkIn.value = `${t.getFullYear()}-${p(t.getMonth() + 1)}-${p(t.getDate())}`
  const t2 = new Date(t.getTime() + 2 * 86400000)
  checkOut.value = `${t2.getFullYear()}-${p(t2.getMonth() + 1)}-${p(t2.getDate())}`
}

function addBlock() {
  const id = defaultRtId()
  blocks.value.push({ room_type_id: id, qty: 1, unit_price: priceOf(id) })
}

function removeBlock(i: number) {
  blocks.value.splice(i, 1)
}

function onBlockTypeChange(row: BlockRow) {
  row.unit_price = priceOf(row.room_type_id)
}

function addLine() {
  const id = blocks.value[0]?.room_type_id || defaultRtId()
  lines.value.push({
    guest_name: '',
    id_last4: '',
    room_type_id: id,
    check_in: checkIn.value,
    check_out: checkOut.value,
    note: '',
  })
}

function removeLine(i: number) {
  lines.value.splice(i, 1)
}

/** 按房量块生成/补齐分房清单空行 */
function syncLinesFromBlocks() {
  const needed: { room_type_id: number }[] = []
  for (const b of blocks.value) {
    for (let i = 0; i < Math.max(1, Number(b.qty) || 1); i++) {
      needed.push({ room_type_id: b.room_type_id })
    }
  }
  const next: LineRow[] = needed.map((n, idx) => {
    const prev = lines.value[idx]
    return {
      guest_name: prev?.guest_name || '',
      id_last4: prev?.id_last4 || '',
      room_type_id: n.room_type_id,
      check_in: prev?.check_in || checkIn.value,
      check_out: prev?.check_out || checkOut.value,
      note: prev?.note || '',
    }
  })
  lines.value = next
}

watch(
  () => blocks.value.map((b) => `${b.room_type_id}:${b.qty}`).join('|'),
  () => {
    if (!blocks.value.length) return
    const totalQty = blocks.value.reduce((s, b) => s + Math.max(1, Number(b.qty) || 1), 0)
    if (lines.value.length !== totalQty) syncLinesFromBlocks()
  },
)

watch([checkIn, checkOut], () => {
  for (const ln of lines.value) {
    if (!ln.check_in) ln.check_in = checkIn.value
    if (!ln.check_out) ln.check_out = checkOut.value
  }
})

async function loadMeta() {
  roomTypes.value = await api.listRoomTypes(hotelStore.hotelId).catch(() => [])
  if (!blocks.value.length && roomTypes.value[0]) {
    addBlock()
    blocks.value[0].qty = 2
    syncLinesFromBlocks()
  }
}

async function submit() {
  if (!groupName.value.trim()) return toast(t('请填写团体名称'))
  if (!contactName.value.trim()) return toast(t('请填写联系人'))
  if (!blocks.value.length) return toast(t('请至少添加一种房型'))
  const totalQty = blocks.value.reduce((s, b) => s + Math.max(1, Number(b.qty) || 1), 0)
  if (totalQty < 2) return toast(t('团体至少预订 2 间'))
  if (submitting.value) return
  submitting.value = true
  try {
    const data = await api.createGroupOrder({
      hotel_id: hotelStore.hotelId,
      group_name: groupName.value.trim(),
      group_type: groupType.value,
      status: status.value,
      contact_name: contactName.value.trim(),
      phone: contactPhone.value.trim() || undefined,
      settle_mode: settleMode.value,
      settle_party: settleParty.value.trim() || undefined,
      sales_name: salesName.value.trim() || undefined,
      check_in: checkIn.value,
      check_out: checkOut.value,
      note: note.value.trim() || undefined,
      other_amount: Number(otherAmount.value) || 0,
      deposit_amount: Number(depositAmount.value) || 0,
      blocks: blocks.value.map((b) => ({
        room_type_id: b.room_type_id,
        qty: Math.max(1, Number(b.qty) || 1),
        unit_price: Number(b.unit_price) || 0,
      })),
      lines: lines.value.map((ln) => ({
        guest_name: ln.guest_name.trim(),
        id_last4: ln.id_last4.trim(),
        room_type_id: ln.room_type_id,
        check_in: ln.check_in || checkIn.value,
        check_out: ln.check_out || checkOut.value,
        note: ln.note.trim(),
      })),
    })
    toast(t('团体单已创建 · {no}', { no: data.order_no || '' }))
    const id = data.id || data.order?.id
    if (id) router.push(`/orders/${id}`)
    else router.push('/orders?source=group')
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
  <div class="page group-page">
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
          <div class="text-xs text-on-surface-variant mb-0.5">{{ t('预订管理 / 团体预订') }}</div>
          <h1 class="font-headline-md text-headline-md text-on-surface">{{ t('新建团体订单') }}</h1>
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

    <!-- 1. 团体基本信息 -->
    <section class="card">
      <h2 class="sec-title">{{ t('团体基本信息') }}</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <label class="field">
          <span>{{ t('团体名称') }}</span>
          <input v-model="groupName" :placeholder="t('如：上海康养旅行团')" />
        </label>
        <label class="field">
          <span>{{ t('团队类型') }}</span>
          <select v-model="groupType">
            <option>{{ t('旅游团') }}</option>
            <option>{{ t('企业团') }}</option>
            <option>{{ t('会议团') }}</option>
            <option>{{ t('其他') }}</option>
          </select>
        </label>
        <label class="field">
          <span>{{ t('订单状态') }}</span>
          <select v-model="status">
            <option value="pending">{{ t('待确认') }}</option>
            <option value="confirmed">{{ t('已确认') }}</option>
          </select>
        </label>
        <label class="field">
          <span>{{ t('联系人') }}</span>
          <input v-model="contactName" :placeholder="t('领队 / 对接人')" />
        </label>
        <label class="field">
          <span>{{ t('联系电话') }}</span>
          <input v-model="contactPhone" :placeholder="t('手机号')" />
        </label>
        <label class="field">
          <span>{{ t('结账形式') }}</span>
          <select v-model="settleMode">
            <option value="unified">{{ t('统一结账') }}</option>
            <option value="split">{{ t('分账结账') }}</option>
          </select>
        </label>
        <label class="field">
          <span>{{ t('结算单位') }}</span>
          <input v-model="settleParty" :placeholder="t('如：苏一国旅')" />
        </label>
        <label class="field">
          <span>{{ t('销售') }}</span>
          <input v-model="salesName" :placeholder="t('如：王经理')" />
        </label>
      </div>
    </section>

    <!-- 2. 预订房量与分配 -->
    <section class="card">
      <div class="flex flex-wrap items-end justify-between gap-3 mb-3">
        <h2 class="sec-title mb-0">{{ t('预订房量与分配') }}</h2>
        <div class="flex flex-wrap gap-3 items-end">
          <label class="field tight">
            <span>{{ t('入住日期') }}</span>
            <input v-model="checkIn" type="date" />
          </label>
          <label class="field tight">
            <span>{{ t('离店日期') }}</span>
            <input v-model="checkOut" type="date" />
          </label>
          <div class="nights-pill">
            {{ t('住宿晚数') }} <b>{{ nights }}</b> {{ t('晚') }}
          </div>
        </div>
      </div>
      <table class="tbl">
        <thead>
          <tr>
            <th style="width: 40px">#</th>
            <th>{{ t('房型') }}</th>
            <th style="width: 100px">{{ t('数量') }}</th>
            <th style="width: 140px">{{ t('单价/间/晚') }}</th>
            <th style="width: 120px">{{ t('小计') }}</th>
            <th style="width: 64px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(b, i) in blocks" :key="i">
            <td>{{ i + 1 }}</td>
            <td>
              <select v-model.number="b.room_type_id" class="inp" @change="onBlockTypeChange(b)">
                <option v-for="rt in roomTypes" :key="rt.id" :value="rt.id">{{ rt.name }}</option>
              </select>
            </td>
            <td>
              <input v-model.number="b.qty" type="number" min="1" class="inp" />
            </td>
            <td>
              <input v-model.number="b.unit_price" type="number" min="0" step="1" class="inp" />
            </td>
            <td class="num">¥ {{ fmtMoney(b.unit_price * Math.max(1, b.qty || 1) * nights) }}</td>
            <td>
              <button type="button" class="link-danger" @click="removeBlock(i)">
                {{ t('删除') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <button type="button" class="link-add" @click="addBlock">{{ t('+ 添加房型') }}</button>
      <button type="button" class="link-add ml-4" @click="syncLinesFromBlocks">
        {{ t('按房量生成分房清单') }}
      </button>
    </section>

    <!-- 3. 分房清单 -->
    <section class="card">
      <h2 class="sec-title">{{ t('分房清单') }}</h2>
      <table class="tbl">
        <thead>
          <tr>
            <th style="width: 36px">#</th>
            <th>{{ t('客人姓名') }}</th>
            <th style="width: 100px">{{ t('证件后四位') }}</th>
            <th>{{ t('房型') }}</th>
            <th style="width: 120px">{{ t('入住') }}</th>
            <th style="width: 120px">{{ t('离店') }}</th>
            <th>{{ t('备注') }}</th>
            <th style="width: 56px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(ln, i) in lines" :key="i">
            <td>{{ i + 1 }}</td>
            <td><input v-model="ln.guest_name" class="inp" :placeholder="t('姓名')" /></td>
            <td>
              <input v-model="ln.id_last4" class="inp" maxlength="4" :placeholder="t('后四位')" />
            </td>
            <td>
              <select v-model.number="ln.room_type_id" class="inp">
                <option v-for="rt in roomTypes" :key="rt.id" :value="rt.id">{{ rt.name }}</option>
              </select>
            </td>
            <td><input v-model="ln.check_in" type="date" class="inp" /></td>
            <td><input v-model="ln.check_out" type="date" class="inp" /></td>
            <td><input v-model="ln.note" class="inp" :placeholder="t('可选')" /></td>
            <td>
              <button type="button" class="link-danger" @click="removeLine(i)">
                {{ t('移除') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <button type="button" class="link-add" @click="addLine">{{ t('+ 添加客人') }}</button>
      <p class="hint">{{ t('房号可在订单详情中逐间排房；此处先录入名单与房型。') }}</p>
    </section>

    <!-- 4. 费用汇总 -->
    <section class="card">
      <h2 class="sec-title">{{ t('费用汇总') }}</h2>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        <label class="field">
          <span>{{ t('房费合计') }}</span>
          <input :value="fmtMoney(roomFeeTotal)" readonly class="readonly" />
        </label>
        <label class="field">
          <span>{{ t('其他费用(餐饮/会议)') }}</span>
          <input v-model.number="otherAmount" type="number" min="0" step="1" />
        </label>
        <label class="field">
          <span>{{ t('已收定金') }}</span>
          <input v-model.number="depositAmount" type="number" min="0" step="1" />
        </label>
      </div>
      <div class="fee-foot">
        <div>
          {{ t('费用总计') }} <b>¥ {{ fmtMoney(grandTotal) }}</b>
        </div>
        <div class="due">
          {{ t('应付余额') }} <b>¥ {{ fmtMoney(balanceDue) }}</b>
        </div>
      </div>
    </section>

    <!-- 5. 备注 -->
    <section class="card">
      <h2 class="sec-title">{{ t('备注') }}</h2>
      <textarea v-model="note" rows="3" :placeholder="t('如：大巴牌照、到店时间、含早要求等')" />
    </section>
  </div>
</template>

<style scoped>
.group-page {
  width: 100%;
  max-width: none;
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
.field.tight {
  min-width: 150px;
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
.card textarea:focus,
.inp:focus {
  border-color: var(--primary, #005bbf);
}
.field input.readonly {
  background: #eef1f4;
  color: #374151;
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
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.tbl th {
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  padding: 8px 6px;
  border-bottom: 1px solid #e5e7eb;
}
.tbl td {
  padding: 6px;
  border-bottom: 1px solid #f1f3f5;
  vertical-align: middle;
}
.tbl .num {
  font-variant-numeric: tabular-nums;
  color: #374151;
}
.inp {
  width: 100%;
  border: 1px solid #e2e5ea;
  background: #f8fafc;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 13px;
  outline: none;
}
.link-add {
  margin-top: 10px;
  border: none;
  background: none;
  color: var(--primary, #005bbf);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
.link-danger {
  border: none;
  background: none;
  color: #dc2626;
  font-size: 12px;
  cursor: pointer;
}
.hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #9aa1ad;
}
.fee-foot {
  display: flex;
  justify-content: flex-end;
  gap: 24px;
  flex-wrap: wrap;
  font-size: 14px;
  color: #4b5563;
}
.fee-foot b {
  color: #111827;
  margin-left: 6px;
}
.fee-foot .due b {
  color: #dc2626;
  font-size: 18px;
}
.ml-4 {
  margin-left: 1rem;
}
</style>
