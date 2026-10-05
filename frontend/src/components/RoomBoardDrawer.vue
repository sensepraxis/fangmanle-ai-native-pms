<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 房态看板 · 按状态动态操作抽屉
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { STATUS_CN, toast } from '../lib/ui'
import { canBoardAction, resolveBoardRole, roleLabel, type BoardRole } from '../lib/roomBoardPerms'

const props = defineProps<{
  open: boolean
  room: any | null
  canMutate?: boolean
}>()

const emit = defineEmits<{
  close: []
  refreshed: []
}>()

const router = useRouter()
const detail = ref<any>(null)
const loading = ref(false)
const busy = ref(false)

const role = computed<BoardRole>(() => resolveBoardRole(hotelStore.user?.role))
const st = computed(() => String(props.room?.status || ''))
const kind = computed(() => {
  const s = st.value
  if (['VC', 'vacant', 'clean'].includes(s)) return 'vc'
  if (['VD', 'dirty', 'cleaning'].includes(s)) return 'vd'
  if (['OCC', 'occupied'].includes(s)) return 'occ'
  if (s === 'EA') return 'ea'
  if (s === 'DO') return 'do'
  if (['OOO', 'maintenance', 'ooo'].includes(s)) return 'ooo'
  if (s === 'BLK') return 'blk'
  return 'vc'
})

const titleStatus = computed(() => STATUS_CN[st.value] || props.room?.status_label || st.value)
const priceText = computed(() => {
  const p = props.room?.ai_price ?? props.room?.base_price
  if (p == null || !canBoardAction(role.value, 'price')) return null
  return `¥${Math.round(Number(p))}`
})

function can(a: Parameters<typeof canBoardAction>[1]) {
  return canBoardAction(role.value, a)
}

function maskName(n?: string | null) {
  const s = String(n || '').trim()
  if (!s) return '—'
  if (s.length === 1) return s + '*'
  return s[0] + '*'.repeat(Math.min(2, s.length - 1))
}
function maskPhone(p?: string | null) {
  const s = String(p || '').replace(/\D/g, '')
  if (s.length < 7) return s || '—'
  return s.slice(0, 3) + '****' + s.slice(-4)
}

watch(
  () => [props.open, props.room?.id] as const,
  async ([open, id]) => {
    detail.value = null
    if (!open || !id) return
    loading.value = true
    try {
      detail.value = await api.getRoom(Number(id))
    } catch {
      detail.value = null
    } finally {
      loading.value = false
    }
  },
)

function close() {
  emit('close')
}

async function setStatus(next: string, promptLabel?: string, defReason?: string) {
  if (!props.room || !props.canMutate) {
    toast(t('规划日只读，请切回今日'), false)
    return
  }
  if (busy.value) return
  busy.value = true
  try {
    let reason: string | undefined
    if (promptLabel) {
      reason = window.prompt(promptLabel, defReason || '') || defReason || promptLabel
    }
    await api.setRoomStatus(props.room.id, next, reason)
    toast(t('房间 {no} → {st}', { no: props.room.room_no, st: STATUS_CN[next] || next }))
    emit('refreshed')
    close()
  } catch (e: any) {
    toast(e?.message || t('操作失败'), false)
  } finally {
    busy.value = false
  }
}

function goWalkIn() {
  router.push({
    path: '/c5-frontdesk/walk-in-quick-check-in',
    query: { room_id: String(props.room?.id || ''), room_no: props.room?.room_no || '' },
  })
  close()
}
function goBook() {
  router.push({
    path: '/c5-frontdesk/front-desk-booking',
    query: {
      room_id: String(props.room?.id || ''),
      room_type_id: String(props.room?.room_type_id || ''),
    },
  })
  close()
}
function goOrder() {
  if (props.room?.order_id) router.push(`/orders/${props.room.order_id}`)
  else toast(t('暂无关联订单'), false)
  close()
}
function goCheckout() {
  if (props.room?.order_id) {
    router.push({
      path: '/c5-frontdesk/cashiering-checkout',
      query: { order_id: String(props.room.order_id) },
    })
  } else toast(t('暂无关联订单'), false)
  close()
}
function goDispatch() {
  router.push('/c6-housekeeping/dispatch')
  close()
}
function goChangeRoom() {
  if (props.room?.order_id) router.push(`/orders/${props.room.order_id}`)
  else toast(t('请先打开订单办理换房'), false)
  close()
}

async function markDueOut() {
  if (!props.room || !props.canMutate) return
  busy.value = true
  try {
    await api.markDueOut(props.room.id, '看板标记预离')
    toast(t('已标记预离'))
    emit('refreshed')
    close()
  } catch (e: any) {
    toast(e?.message || t('失败'), false)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open && room" class="rbd-root" @keydown.esc="close">
      <div class="rbd-mask" @click="close" />
      <aside class="rbd-drawer" role="dialog" aria-modal="true">
        <header class="rbd-head">
          <div>
            <div class="rbd-no">{{ room.room_no }}</div>
            <div class="rbd-sub">
              {{ room.room_type_name || t('标准') }}
              <span class="rbd-st">· {{ titleStatus }}</span>
              <span v-if="kind === 'vd'" class="rbd-hint">{{ t('（待清洁）') }}</span>
            </div>
            <div v-if="priceText" class="rbd-price">{{ t('今日参考价') }} {{ priceText }}</div>
            <div class="rbd-role">{{ t('当前角色') }}：{{ roleLabel(role) }}</div>
          </div>
          <button type="button" class="rbd-x" @click="close" :aria-label="t('关闭')">
            <span class="material-symbols-outlined">close</span>
          </button>
        </header>

        <div class="rbd-body">
          <p v-if="loading" class="muted">{{ t('加载详情…') }}</p>

          <!-- 1 空净 -->
          <template v-if="kind === 'vc'">
            <section class="rbd-sec">
              <h3>{{ t('主操作') }}</h3>
              <div class="rbd-acts">
                <button v-if="can('checkin')" type="button" class="act primary" @click="goWalkIn">
                  {{ t('快速入住') }}
                </button>
                <button v-if="can('book')" type="button" class="act" @click="goBook">
                  {{ t('快速预订') }}
                </button>
                <button v-if="can('dirty')" type="button" class="act" @click="setStatus('VD')">
                  {{ t('标脏') }}
                </button>
                <button
                  v-if="can('ooo')"
                  type="button"
                  class="act"
                  @click="setStatus('OOO', t('维修原因'), t('设备故障'))"
                >
                  {{ t('维修') }}
                </button>
                <button
                  v-if="can('lock')"
                  type="button"
                  class="act"
                  @click="setStatus('BLK', t('锁房原因'), t('预留升级'))"
                >
                  {{ t('锁房') }}
                </button>
              </div>
            </section>
            <section class="rbd-sec">
              <h3>{{ t('辅助信息') }}</h3>
              <ul class="info">
                <li>{{ t('状态：空净可售') }}</li>
                <li v-if="room.status_note">{{ t('备注') }}：{{ room.status_note }}</li>
                <li>{{ t('设施 / 无烟等：暂无结构化字段') }}</li>
                <li>{{ t('未来几日占用：请结合「房态库存」查看') }}</li>
              </ul>
            </section>
          </template>

          <!-- 2 空脏 -->
          <template v-else-if="kind === 'vd'">
            <section class="rbd-sec">
              <h3>{{ t('主操作') }}</h3>
              <div class="rbd-acts">
                <button v-if="can('hkTake')" type="button" class="act primary" @click="goDispatch">
                  {{ t('派单') }}
                </button>
                <button v-if="can('hkDone')" type="button" class="act" @click="goDispatch">
                  {{ t('我已打扫') }}
                </button>
                <button v-if="can('hkInspect')" type="button" class="act" @click="goDispatch">
                  {{ t('查房通过') }}
                </button>
                <button
                  v-if="can('ooo')"
                  type="button"
                  class="act"
                  @click="setStatus('OOO', t('报修原因'), t('设备故障'))"
                >
                  {{ t('报修') }}
                </button>
              </div>
            </section>
            <section class="rbd-sec">
              <h3>{{ t('辅助信息') }}</h3>
              <ul class="info">
                <li>{{ t('当前：空脏房（待清洁）') }}</li>
                <li v-if="room.open_hk">
                  任务：{{ room.open_hk.title }} · {{ room.open_hk.assignee }}
                </li>
                <li>{{ t('上次退房客人：请在订单/流水中查看') }}</li>
              </ul>
            </section>
          </template>

          <!-- 3 已入住 -->
          <template v-else-if="kind === 'occ'">
            <section class="rbd-sec">
              <h3>{{ t('主操作') }}</h3>
              <div class="rbd-acts">
                <button
                  v-if="can('checkout')"
                  type="button"
                  class="act primary"
                  @click="goCheckout"
                >
                  {{ t('办理退房') }}
                </button>
                <button
                  v-if="can('extend')"
                  type="button"
                  class="act"
                  @click="setStatus('OCC', t('续住说明'), t('续住'))"
                >
                  {{ t('续住') }}
                </button>
                <button v-if="can('changeRoom')" type="button" class="act" @click="goChangeRoom">
                  {{ t('换房') }}
                </button>
                <button v-if="can('extend')" type="button" class="act" @click="markDueOut">
                  {{ t('标预离') }}
                </button>
                <button v-if="can('viewOrder')" type="button" class="act" @click="goOrder">
                  {{ t('查看订单') }}
                </button>
              </div>
            </section>
            <section class="rbd-sec">
              <h3>{{ t('在住信息') }}</h3>
              <ul class="info">
                <li>{{ t('客人') }}：{{ maskName(room.guest_name) }}</li>
                <li>
                  {{ t('入住') }}：{{ room.check_in || '—' }} · {{ t('离店') }}：{{
                    room.check_out || '—'
                  }}
                </li>
                <li v-if="room.nights">{{ t('入住天数') }}：{{ room.nights }}</li>
                <li v-if="priceText && can('price')">{{ t('房价参考') }}：{{ priceText }}</li>
                <li>{{ t('手机') }}：{{ maskPhone(detail?.guest_phone || detail?.phone) }}</li>
              </ul>
              <button
                v-if="can('viewOrder') && room.order_id"
                type="button"
                class="link"
                @click="goOrder"
              >
                {{ t('查看完整订单详情 →') }}
              </button>
            </section>
          </template>

          <!-- 4 预抵 -->
          <template v-else-if="kind === 'ea'">
            <section class="rbd-sec">
              <h3>{{ t('主操作') }}</h3>
              <div class="rbd-acts">
                <button v-if="can('checkin')" type="button" class="act primary" @click="goWalkIn">
                  {{ t('办理入住') }}
                </button>
                <button v-if="can('viewOrder')" type="button" class="act" @click="goOrder">
                  {{ t('修改预订') }}
                </button>
                <button v-if="can('viewOrder')" type="button" class="act" @click="goOrder">
                  {{ t('取消预订') }}
                </button>
                <button v-if="can('changeRoom')" type="button" class="act" @click="goChangeRoom">
                  {{ t('换房') }}
                </button>
              </div>
            </section>
            <section class="rbd-sec">
              <h3>{{ t('预抵信息') }}</h3>
              <ul class="info">
                <li>预订人：{{ maskName(room.guest_name) }}</li>
                <li>预计入住：{{ room.check_in || '—' }} · 离店：{{ room.check_out || '—' }}</li>
                <li v-if="priceText && can('price')">房价：{{ priceText }}</li>
                <li v-if="room.ai_tip">{{ room.ai_tip }}</li>
              </ul>
            </section>
          </template>

          <!-- 5 预离 -->
          <template v-else-if="kind === 'do'">
            <section class="rbd-sec">
              <h3>{{ t('主操作') }}</h3>
              <div class="rbd-acts">
                <button
                  v-if="can('checkout')"
                  type="button"
                  class="act primary"
                  @click="goCheckout"
                >
                  {{ t('办理退房') }}
                </button>
                <button
                  v-if="can('extend')"
                  type="button"
                  class="act"
                  @click="setStatus('OCC', t('续住'), t('续住清除预离'))"
                >
                  {{ t('续住') }}
                </button>
                <button
                  v-if="can('extend')"
                  type="button"
                  class="act"
                  @click="toast(t('延迟退房请在订单备注登记'))"
                >
                  {{ t('延迟退房') }}
                </button>
                <button v-if="can('viewOrder')" type="button" class="act" @click="goOrder">
                  {{ t('查看订单') }}
                </button>
              </div>
            </section>
            <section class="rbd-sec">
              <h3>{{ t('预离提醒') }}</h3>
              <ul class="info">
                <li>客人：{{ maskName(room.guest_name) }}</li>
                <li>{{ t('计划离店') }}：{{ room.check_out || t('今日') }}</li>
                <li>{{ t('请确认账单 / 押金 / 迷你吧后再退房') }}</li>
              </ul>
            </section>
          </template>

          <!-- 6 维修 / 锁房 -->
          <template v-else-if="kind === 'ooo' || kind === 'blk'">
            <section class="rbd-sec">
              <h3>{{ t('主操作') }}</h3>
              <div class="rbd-acts">
                <button
                  v-if="kind === 'ooo' && can('clearOoo')"
                  type="button"
                  class="act primary"
                  @click="setStatus('VC', t('解除维修'), t('解除维修·空净'))"
                >
                  {{ t('解除维修·空净') }}
                </button>
                <button
                  v-if="kind === 'ooo' && can('clearOoo')"
                  type="button"
                  class="act"
                  @click="setStatus('VD', t('解除维修'), t('解除·空脏'))"
                >
                  {{ t('解除·空脏') }}
                </button>
                <button
                  v-if="kind === 'blk' && can('clearLock')"
                  type="button"
                  class="act primary"
                  @click="setStatus('VC', t('解锁'), t('解锁'))"
                >
                  {{ t('解除锁房') }}
                </button>
                <button
                  v-if="kind === 'ooo' && can('ooo')"
                  type="button"
                  class="act"
                  @click="setStatus('OOO', t('延长说明'), t('延长维修'))"
                >
                  {{ t('延长维修') }}
                </button>
              </div>
            </section>
            <section class="rbd-sec">
              <h3>{{ t('原因与恢复') }}</h3>
              <ul class="info">
                <li>{{ t('原因') }}：{{ room.status_note || '—' }}</li>
                <li>{{ t('预计恢复') }}：{{ room.status_until || t('未填写') }}</li>
                <li v-if="kind === 'ooo'">
                  {{ t('关联：已自动生成维修工单，完成后可点「解除」或在任务页点「维修完成」') }}
                </li>
                <li v-if="detail?.status_log?.length">
                  最近流水：{{ detail.status_log[0].from_status }} →
                  {{ detail.status_log[0].to_status }} （{{
                    detail.status_log[0].reason || t('无备注')
                  }}）
                </li>
              </ul>
            </section>
          </template>
        </div>
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.rbd-root {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  justify-content: flex-end;
}
.rbd-mask {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
}
.rbd-drawer {
  position: relative;
  width: min(420px, 100vw);
  height: 100%;
  background: #fff;
  box-shadow: -8px 0 28px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  animation: slideIn 0.2s ease-out;
}
@keyframes slideIn {
  from {
    transform: translateX(24px);
    opacity: 0.6;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
.rbd-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 18px 14px;
  border-bottom: 1px solid #e8eaed;
}
.rbd-no {
  font:
    700 26px 'Roboto Mono',
    ui-monospace,
    monospace;
  line-height: 1.1;
}
.rbd-sub {
  margin-top: 6px;
  font-size: 13px;
  color: #5f6368;
}
.rbd-st {
  font-weight: 700;
  color: #202124;
}
.rbd-hint {
  color: #d93025;
}
.rbd-price {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 700;
  color: #1a73e8;
}
.rbd-role {
  margin-top: 6px;
  font-size: 11px;
  color: #80868b;
}
.rbd-x {
  border: none;
  background: #f1f3f4;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  display: grid;
  place-items: center;
}
.rbd-body {
  flex: 1;
  overflow: auto;
  padding: 16px 18px 28px;
}
.rbd-sec {
  margin-bottom: 20px;
}
.rbd-sec h3 {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 700;
  color: #5f6368;
}
.rbd-acts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.act {
  border: 1px solid #dadce0;
  background: #fff;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  color: #202124;
}
.act.primary {
  background: #1a73e8;
  border-color: #1a73e8;
  color: #fff;
}
.act:hover {
  filter: brightness(0.97);
}
.info {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #3c4043;
  line-height: 1.7;
}
.link {
  margin-top: 10px;
  border: none;
  background: none;
  color: #1a73e8;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
.muted {
  font-size: 13px;
  color: #80868b;
}
</style>
