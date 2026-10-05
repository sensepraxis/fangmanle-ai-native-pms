<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * AI 客需流转 —— 对照原型 workflow.html
 * 左：客源输入 + AI 意图解析
 * 中：进行中客需时间线（接收→解析→派单→在途→完成）
 * 右：宾客偏好摘要 + 内部协作备注
 * 数据：housekeeping/board（service_requests / staff / room_status）
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
const router = useRouter()

type Sr = {
  id: number
  room: string
  content: string
  channel: string
  time: string
  open: boolean
  priority?: number
  assignee?: string
  iot?: boolean
}

const list = ref<Sr[]>([])
const staff = ref<any[]>([])
const roomStatus = ref<any>({})
const selectedId = ref<number | null>(null)
const noteDraft = ref('')

const selected = computed(() => {
  const rows = list.value
  if (!rows.length) return null
  return rows.find((r) => r.id === selectedId.value) || rows.find((r) => r.open) || rows[0]
})

function inferIntent(sr: Sr | null) {
  const text = sr?.content || ''
  const room = sr?.room || '—'
  let type = t('客需服务')
  let item = text.slice(0, 12) || t('服务请求')
  let qty = t('按需')
  if (/毛巾|浴巾|面巾/.test(text)) {
    type = t('客用品补给')
    item = t('毛巾')
    qty = t('未指定（默认 2）')
  } else if (/被子|枕|床/.test(text)) {
    type = t('客用品补给')
    item = /枕/.test(text) ? t('枕芯') : t('被子')
    qty = '1'
  } else if (/水|牙具|拖鞋/.test(text)) {
    type = t('客用品补给')
    item = text.replace(/送|加|需要/g, '').slice(0, 8) || t('客用品')
    qty = '2'
  } else if (/空调|电视|灯|门锁|漏水/.test(text)) {
    type = t('工程协查')
    item = text.slice(0, 10)
    qty = '—'
  } else if (/打扫|清洁|卫生间/.test(text)) {
    type = '住中整理'
    item = t('客房清洁')
    qty = t('1 次')
  }
  return { type, item, qty, room }
}

const intent = computed(() => inferIntent(selected.value))

const source = computed(() => {
  const sr = selected.value
  if (!sr) {
    return {
      guest: t('暂无开放客需'),
      time: '—',
      channel: t('系统'),
      message: t('当前无待处理住中请求。'),
    }
  }
  return {
    guest: `客人（${sr.room} 房）`,
    time: sr.time || t('刚刚'),
    channel: sr.channel || t('系统'),
    message: sr.content || '—',
  }
})

/** 原型时间线：接收 → 解析 → 派单 → 在途 → 完成 */
const steps = computed(() => {
  const sr = selected.value
  if (!sr) return []
  const assignee = sr.assignee && sr.assignee !== t('未分配') ? sr.assignee : null
  const st = staff.value.find((s) => s.name === assignee)
  const open = !!sr.open
  const urgent = (sr.priority || 5) <= 2

  const timeline = [
    {
      label: t('请求已接收'),
      time: sr.time || '—',
      desc: `${sr.channel || t('系统')} · Room ${sr.room}`,
      done: true,
      current: false,
      pending: false,
    },
    {
      label: t('AI 意图解析'),
      time: sr.time || '—',
      desc: `${intent.value.type} · ${intent.value.item}`,
      done: true,
      current: false,
      pending: false,
    },
    {
      label: assignee ? t('已派单 · {name}', { name: assignee }) : t('待就近派单'),
      time: open ? (urgent ? t('优先') : t('进行中')) : t('已完成'),
      desc: assignee
        ? st?.area
          ? `${st.area} · 负荷 ${st.load ?? 0}%`
          : t('就近匹配完成')
        : t('等待可用保洁接单'),
      done: !!assignee,
      current: open && !!assignee,
      pending: open && !assignee,
      assignee: assignee || undefined,
      location: st?.area || (assignee ? t('楼层支援') : undefined),
      load: st?.load,
    },
    {
      label: open ? (urgent ? t('紧急处理中') : t('员工处理中')) : t('客房送达/处理完成'),
      time: open ? t('跟进中') : t('已关闭'),
      desc: open
        ? sr.iot
          ? t('含设备类诉求，必要时转工程')
          : t('按解析结果执行客需')
        : t('客人确认或前台关闭'),
      done: !open,
      current: open && !assignee,
      pending: open,
    },
    {
      label: t('完成确认'),
      time: open ? t('待完成') : sr.time || '—',
      desc: open ? t('关闭后写入协作备注与结算质检') : t('已归档'),
      done: !open,
      current: false,
      pending: open,
    },
  ]

  // 保证只有一个 current
  let seen = false
  for (const s of timeline) {
    if (s.current && !seen) {
      seen = true
      continue
    }
    if (s.current) {
      s.current = false
      if (!s.done) s.pending = true
    }
  }
  if (!seen) {
    const idx = timeline.findIndex((s) => !s.done)
    if (idx >= 0) {
      timeline[idx].current = true
      timeline[idx].pending = false
    }
  }
  return timeline
})

const prefSummary = computed(() => {
  const rs = roomStatus.value || {}
  const openSr = list.value.filter((x) => x.open).length
  const dirty = rs.dirty ?? 0
  const cleaning = rs.cleaning ?? 0
  const ooo = rs.ooo ?? 0
  const openClean =
    rs.dirty != null
      ? Math.max(0, (rs.dirty || 0) + (rs.cleaning || 0))
      : staff.value.reduce((a, s) => a + (s.open || 0), 0)
  return `开放清扫 ${openClean} · 客需 ${openSr} · 脏房 ${dirty} · 打扫中 ${cleaning} · 维修关房 ${ooo}`
})

const preferences = computed(() => {
  const sr = selected.value
  const items: any[] = []
  if (sr?.iot || /空调|工程/.test(sr?.content || '')) {
    items.push({
      icon: 'build',
      title: t('设备类客需'),
      desc: t('建议先派近楼层保洁初检，无效再转工程工单'),
      tone: 'tertiary',
    })
  } else if (/毛巾|被子|水|牙具|枕/.test(sr?.content || '')) {
    items.push({
      icon: 'shopping_bag',
      title: t('客用品补给偏好'),
      desc: t('默认按双人配置补送；VIP 房优先加急通道'),
      tone: 'tertiary',
    })
  } else {
    items.push({
      icon: 'spa',
      title: t('住中服务偏好'),
      desc: t('静音时段避免敲门；完成后企微回访一句'),
      tone: 'tertiary',
    })
  }
  const near = [...staff.value].sort((a, b) => (a.load || 0) - (b.load || 0))[0]
  if (near) {
    items.push({
      icon: 'near_me',
      title: `就近推荐 · ${near.name}`,
      desc: `${near.area || t('全楼')} · 当前负荷 ${near.load ?? 0}%${near.busy ? t('（忙碌）') : t('（可接）')}`,
      tone: 'secondary',
    })
  }
  if ((sr?.priority || 5) <= 2) {
    items.push({
      icon: 'priority_high',
      title: t('高优 SLA'),
      desc: t('紧急客需目标 15 分钟内响应，超时自动催办'),
      tone: 'secondary',
    })
  }
  return items
})

const notes = computed(() => {
  const rows = list.value.slice(0, 6)
  const out: any[] = []
  rows.forEach((sr, i) => {
    out.push({
      tag: t('客'),
      role: 'guest',
      author: `Room ${sr.room}`,
      time: sr.time || '—',
      text: sr.content || '',
    })
    if (sr.assignee && sr.assignee !== t('未分配') && i < 3) {
      out.push({
        tag: sr.assignee.slice(0, 1),
        role: 'housekeeper',
        author: sr.assignee,
        time: sr.time || '—',
        text: sr.open
          ? `已接 ${sr.room}：${(sr.content || '').slice(0, 16)}，正在处理`
          : `${sr.room} 客需已完成关闭`,
      })
    }
  })
  return out.slice(0, 8)
})

function selectSr(sr: Sr) {
  selectedId.value = sr.id
}

async function load() {
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId)
    const srs: Sr[] = (board?.service_requests || []).map((x: any) => ({
      id: x.id,
      room: x.room || x.room_no || '—',
      content: x.content || x.msg || '',
      channel: x.channel || t('系统'),
      time: x.time || '—',
      open: !!x.open,
      priority: x.priority,
      assignee: x.assignee || t('未分配'),
      iot: !!x.iot,
    }))
    // 开放优先
    srs.sort((a, b) => Number(b.open) - Number(a.open) || (a.priority || 5) - (b.priority || 5))
    list.value = srs
    staff.value = board?.staff || []
    roomStatus.value = board?.room_status || {}
    const firstOpen = srs.find((x) => x.open) || srs[0]
    selectedId.value = firstOpen?.id ?? null
  } catch {
    list.value = []
    staff.value = []
    roomStatus.value = {}
    selectedId.value = null
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)

function goGuestHub() {
  router.push('/c6-housekeeping/in-stay-guest-request-management')
}

function goHousekeepingHub() {
  router.push('/c6-housekeeping/housekeeping')
}
</script>

<template>
  <div class="page">
    <div class="page-head head-row">
      <div>
        <div class="back-row">
          <button class="back-link" type="button" @click="goGuestHub">
            <span class="material-symbols-outlined">arrow_back</span>{{ t('返回客需看板') }}
          </button>
          <button class="back-link muted" type="button" @click="goHousekeepingHub">
            {{ t('客房服务管理') }}
          </button>
        </div>
        <h1>{{ t('AI 客需流转') }}</h1>
        <p>{{ t('住中请求解析、跟进与自动派发（区别于清扫派工）。') }}</p>
      </div>
      <div class="head-actions">
        <button class="btn btn-ghost" type="button" @click="goGuestHub">
          <span class="material-symbols-outlined">list_alt</span>{{ t('客需看板') }}
        </button>
        <button class="btn btn-ghost" type="button">
          <span class="material-symbols-outlined">filter_list</span>{{ t('筛选') }}
        </button>
      </div>
    </div>

    <div class="grid main-grid">
      <!-- 左：客源输入 + 意图 -->
      <div class="col">
        <div class="card-clean card-pad source-card">
          <div class="sec-head muted">
            <span class="material-symbols-outlined">forum</span>
            <h2>{{ t('客源输入') }}</h2>
          </div>

          <div class="inbox">
            <button
              v-for="sr in list.slice(0, 5)"
              :key="sr.id"
              type="button"
              class="inbox-item"
              :class="{ active: selected && selected.id === sr.id }"
              @click="selectSr(sr)"
            >
              <div class="inbox-top">
                <span class="chip">{{ sr.channel }}</span>
                <span class="room">Room {{ sr.room }}</span>
                <span class="time">{{ sr.time }}</span>
              </div>
              <p class="inbox-msg">{{ sr.content }}</p>
            </button>
            <div v-if="!list.length" class="empty">{{ t('暂无客需消息') }}</div>
          </div>

          <div class="focus-bubble">
            <div class="who">
              <div class="avatar">{{ (source.guest || t('客')).charAt(0) }}</div>
              <div>
                <div class="who-name">{{ source.guest }}</div>
                <div class="who-meta">{{ source.time }} · {{ source.channel }}</div>
              </div>
            </div>
            <p class="bubble">{{ source.message }}</p>
          </div>

          <div class="intent-wrap">
            <div class="intent-badge">
              <span class="material-symbols-outlined">auto_awesome</span>
            </div>
            <div class="intent-box">
              <div class="intent-title">
                <span class="material-symbols-outlined">psychology</span>
                {{ t('AI 意图解析成功') }}
              </div>
              <div class="intent-grid">
                <div>
                  <span class="k">{{ t('类型:') }}</span> <b>{{ intent.type }}</b>
                </div>
                <div>
                  <span class="k">{{ t('物品:') }}</span> <b>{{ intent.item }}</b>
                </div>
                <div>
                  <span class="k">{{ t('数量:') }}</span> <b>{{ intent.qty }}</b>
                </div>
                <div>
                  <span class="k">{{ t('房号:') }}</span> <b class="num">{{ intent.room }}</b>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中：时间线 -->
      <div class="col">
        <div class="card-clean card-pad timeline-card">
          <div class="tk-head">
            <div>
              <span class="status-pill">{{ selected?.open ? t('进行中') : t('已完成') }}</span>
              <h3>{{ selected?.content || t('暂无开放客需') }}</h3>
              <div class="tk-id">
                {{ selected?.id ? `#TK-${selected.id}` : '#—' }} · Room {{ selected?.room || '—' }}
              </div>
            </div>
            <button class="icon-btn" type="button">
              <span class="material-symbols-outlined">more_vert</span>
            </button>
          </div>

          <div class="timeline">
            <div class="rail"></div>
            <div v-for="(s, i) in steps" :key="i" class="step">
              <div
                class="dot"
                :class="{
                  done: s.done,
                  current: s.current,
                  pending: s.pending && !s.current && !s.done,
                }"
              >
                <span v-if="s.done" class="material-symbols-outlined">check</span>
                <i v-else-if="s.current" class="pulse"></i>
              </div>
              <div class="step-body">
                <div class="step-top">
                  <span
                    class="step-label"
                    :class="{ current: s.current, muted: s.pending && !s.current }"
                    >{{ s.label }}</span
                  >
                  <span class="step-time">{{ s.time }}</span>
                </div>
                <p v-if="s.desc" class="step-desc">{{ s.desc }}</p>
                <div v-if="s.assignee" class="assignee">
                  <div class="avatar-sm">{{ s.assignee.charAt(0) }}</div>
                  <div>
                    <div class="as-name">{{ s.assignee }}</div>
                    <div v-if="s.location" class="as-loc">
                      <span class="material-symbols-outlined">location_on</span>{{ s.location }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="!steps.length" class="empty">{{ t('暂无流转步骤') }}</div>
          </div>
        </div>
      </div>

      <!-- 右：偏好 + 备注 -->
      <div class="col side">
        <div class="card-clean card-pad pref-card">
          <div class="sec-head">
            <span class="material-symbols-outlined tert">magic_button</span>
            <h3>{{ t('AI 宾客偏好摘要') }}</h3>
          </div>
          <p class="pref-sum">{{ prefSummary }}</p>
          <div class="pref-list">
            <div v-for="(p, i) in preferences" :key="i" class="pref" :class="p.tone">
              <span class="material-symbols-outlined">{{ p.icon }}</span>
              <div>
                <div class="pref-t">{{ p.title }}</div>
                <div class="pref-d">{{ p.desc }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="card-clean card-pad notes-card">
          <h3 class="notes-title">{{ t('内部协作备注') }}</h3>
          <div class="notes-scroll">
            <div v-for="(n, i) in notes" :key="i" class="note">
              <div class="avatar-xs" :class="n.role">{{ n.tag }}</div>
              <div class="note-bubble" :class="n.role">
                <div class="note-meta">{{ n.author }}（{{ n.time }}）</div>
                <p>{{ n.text }}</p>
              </div>
            </div>
            <div v-if="!notes.length" class="empty">{{ t('暂无协作备注') }}</div>
          </div>
          <div class="note-input">
            <input v-model="noteDraft" type="text" :placeholder="t('添加内部备注...')" />
            <button type="button" class="send">
              <span class="material-symbols-outlined">send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 12px;
}
.back-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 8px;
}
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  padding: 0;
  color: var(--primary);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}
.back-link .material-symbols-outlined {
  font-size: 18px;
}
.back-link.muted {
  color: var(--on-surface-variant);
  font-weight: 600;
}
.back-link:hover {
  text-decoration: underline;
}
.head-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
}
.main-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 16px;
}
.col {
  grid-column: span 4;
  min-width: 0;
}
.side {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.source-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 560px;
}
.sec-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.sec-head h2,
.sec-head h3,
.tk-head h3,
.notes-title,
.intent-title {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: var(--on-surface);
  letter-spacing: 0.02em;
}
.intent-title {
  font-size: 13px;
  color: var(--tertiary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.sec-head.muted {
  color: var(--on-surface-variant);
}
.sec-head.muted h2,
.sec-head.muted h3 {
  color: var(--on-surface);
}
.sec-head .tert {
  color: var(--tertiary);
}
.inbox {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 180px;
  overflow-y: auto;
}
.inbox-item {
  text-align: left;
  border: 1px solid var(--outline-variant);
  background: var(--surface-low);
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
}
.inbox-item.active {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 6%, #fff);
}
.inbox-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 12px;
}
.chip {
  background: var(--surface-high);
  color: var(--on-surface-variant);
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 700;
}
.room {
  font-weight: 700;
}
.time {
  margin-left: auto;
  color: var(--on-surface-variant);
}
.inbox-msg {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.focus-bubble {
  background: var(--surface-low);
  border-radius: 12px;
  padding: 14px;
}
.who {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--primary-container);
  color: var(--on-primary-container);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}
.who-name {
  font-weight: 700;
  font-size: 14px;
}
.who-meta {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.bubble {
  margin: 0;
  display: inline-block;
  background: var(--surface-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 14px;
  box-shadow: var(--shadow);
}
.intent-wrap {
  position: relative;
  margin-top: auto;
  padding-top: 18px;
  border-top: 1px solid var(--outline-variant);
}
.intent-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--surface-lowest);
  color: var(--tertiary);
  padding: 0 8px;
}
.intent-badge .material-symbols-outlined {
  font-size: 16px;
}
.intent-box {
  border-radius: 10px;
  padding: 12px;
  background: rgba(140, 51, 179, 0.1);
  border: 1px solid rgba(140, 51, 179, 0.3);
  background-image: linear-gradient(90deg, transparent, rgba(140, 51, 179, 0.12), transparent);
  background-size: 200% 100%;
  animation: shimmer 3s infinite linear;
}
@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}
.intent-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--tertiary);
  font-weight: 800;
  font-size: 13px;
  margin-bottom: 8px;
}
.intent-title .material-symbols-outlined {
  font-size: 16px;
}
.intent-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  font-size: 13px;
}
.intent-grid .k {
  color: var(--on-surface-variant);
}
.intent-grid b {
  font-weight: 700;
}
.timeline-card {
  border-left: 4px solid var(--primary);
  min-height: 560px;
}
.tk-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}
.status-pill {
  display: inline-block;
  background: var(--primary-container);
  color: var(--on-primary-container);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  margin-bottom: 8px;
}
.tk-head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--on-surface);
}
.tk-id {
  margin-top: 4px;
  color: var(--on-surface-variant);
  font-size: 13px;
  font-weight: 600;
}
.icon-btn {
  border: none;
  background: transparent;
  color: var(--on-surface-variant);
  cursor: pointer;
}
.timeline {
  position: relative;
  padding-left: 28px;
}
.rail {
  position: absolute;
  left: 11px;
  top: 4px;
  bottom: 4px;
  width: 2px;
  background: var(--surface-high);
}
.step {
  position: relative;
  padding-bottom: 22px;
}
.dot {
  position: absolute;
  left: -28px;
  top: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--outline-variant);
  background: var(--surface-lowest);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}
.dot.done {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}
.dot.done .material-symbols-outlined {
  font-size: 12px;
}
.dot.current {
  width: 22px;
  height: 22px;
  left: -30px;
  border-color: var(--primary);
}
.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.85);
  }
}
.step-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 4px;
}
.step-label {
  font-weight: 800;
  font-size: 14px;
}
.step-label.current {
  color: var(--primary);
}
.step-label.muted {
  color: var(--on-surface-variant);
  font-weight: 600;
}
.step-time {
  font-size: 12px;
  color: var(--on-surface-variant);
  white-space: nowrap;
}
.step-desc {
  margin: 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.assignee {
  margin-top: 8px;
  display: flex;
  gap: 10px;
  align-items: center;
  background: var(--surface-low);
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 8px 10px;
}
.avatar-sm {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--surface);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}
.as-name {
  font-size: 13px;
  font-weight: 700;
}
.as-loc {
  font-size: 12px;
  color: var(--tertiary);
  display: flex;
  align-items: center;
  gap: 2px;
  font-weight: 600;
}
.as-loc .material-symbols-outlined {
  font-size: 12px;
}
.pref-card {
  border-left: 2px solid var(--tertiary);
}
.pref-sum {
  margin: 0 0 12px;
  font-size: 13px;
  font-weight: 700;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.pref-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.pref {
  display: flex;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-low);
}
.pref.tertiary {
  background: rgba(140, 51, 179, 0.1);
  border-color: rgba(235, 178, 255, 0.5);
}
.pref .material-symbols-outlined {
  margin-top: 2px;
  color: var(--secondary);
}
.pref.tertiary .material-symbols-outlined {
  color: var(--tertiary);
}
.pref-t {
  font-weight: 800;
  font-size: 13px;
  margin-bottom: 2px;
}
.pref.tertiary .pref-t {
  color: var(--tertiary);
}
.pref-d {
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.4;
}
.notes-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 280px;
}
.notes-title {
  margin: 0 0 12px;
  font-size: 17px;
  font-weight: 800;
  color: var(--on-surface);
}
.notes-scroll {
  flex: 1;
  overflow-y: auto;
  max-height: 220px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
  padding-right: 4px;
}
.note {
  display: flex;
  gap: 10px;
}
.avatar-xs {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.avatar-xs.guest {
  background: var(--secondary-container);
  color: var(--on-secondary-container);
}
.avatar-xs.housekeeper {
  background: var(--primary-fixed);
  color: var(--on-primary-fixed);
}
.note-bubble {
  flex: 1;
  padding: 10px 12px;
  border-radius: 10px;
  border-top-left-radius: 2px;
  background: var(--surface-low);
}
.note-bubble.housekeeper {
  background: var(--primary-fixed);
  border: 1px solid color-mix(in srgb, var(--primary) 20%, transparent);
}
.note-meta {
  font-size: 11px;
  font-weight: 700;
  color: var(--on-surface-variant);
  margin-bottom: 4px;
}
.note-bubble p {
  margin: 0;
  font-size: 13px;
}
.note-input {
  position: relative;
  margin-top: auto;
}
.note-input input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--outline-variant);
  background: var(--surface-low);
  border-radius: 10px;
  padding: 10px 40px 10px 14px;
  font-size: 13px;
  font-family: inherit;
}
.note-input .send {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  color: var(--primary);
  cursor: pointer;
}
.empty {
  text-align: center;
  color: var(--on-surface-variant);
  font-size: 13px;
  padding: 16px 0;
}
@media (max-width: 1100px) {
  .col {
    grid-column: span 12;
  }
}
</style>
