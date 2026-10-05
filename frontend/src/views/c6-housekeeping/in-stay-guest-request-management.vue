<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 客中请求管理：AI 智能解析流 + 主动关怀建议 + 智能调度中心 + 服务状态看板
import { ref, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'
import RoomOpsNav from '../../components/RoomOpsNav.vue'
import HousekeepingTasksSubnav from '../../components/HousekeepingTasksSubnav.vue'

const data = ref<any>({ stream: [], care: null, staff: [], rows: [], tabs: [], dispatch: null })
const rooms = ref<any[]>([])
const onDuty = ref<any[]>([])
const createOpen = ref(false)
const creating = ref(false)
const form = ref({
  room_id: '' as string | number,
  content: '',
  assignee_id: '' as string | number,
  priority: 3,
})

function statusColor(open: boolean, priority?: number) {
  if (!open) return '#1e8e3e'
  if ((priority || 5) <= 2) return 'var(--error)'
  return '#d97706'
}

async function load() {
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId)
    rooms.value = Array.isArray(board?.rooms) ? board.rooms : []
    try {
      onDuty.value = (await api.hkDispatchStaff(hotelStore.hotelId)) || []
    } catch {
      onDuty.value = (board?.staff || []).filter(
        (s: any) => s.status !== 'rest' && s.statusLabel !== t('休息'),
      )
    }
    const srs = board?.service_requests || board?.stream || []
    const openSr = srs.filter((x: any) => x.open)
    data.value = {
      stream: board?.stream || srs.slice(0, 8),
      care: board?.care || null,
      staff: (board?.staff || []).map((s: any) => ({
        tag: (s.name || t('员'))[0],
        name: s.name || t('员工'),
        loc: s.area || '—',
        busy: s.busy ?? Number(s.open || 0) > 0,
        task: t('客需'),
        load: s.load ?? 0,
      })),
      dispatch: openSr[0]
        ? {
            room: openSr[0].room || openSr[0].room_no,
            assignee: (board?.staff || [])[0]?.name || t('机动保洁'),
          }
        : null,
      tabs: [
        { label: t('全部'), active: true },
        { label: `开放 ${openSr.length}`, active: false, danger: openSr.length > 0 },
        { label: t('已完成'), active: false },
      ],
      rows: srs.map((r: any) => ({
        room: r.room || r.room_no || '—',
        req: r.content || r.msg || r.parse || t('客需'),
        cat: r.channel || t('客需'),
        source: r.channel || t('系统'),
        assignee: r.assignee || t('未分配'),
        color: statusColor(!!r.open, r.priority),
        status: r.open ? ((r.priority || 5) <= 2 ? t('紧急处理中') : t('处理中')) : t('已完成'),
        time: r.time || '—',
        action: r.open ? t('催办') : t('查看'),
        waiting: !!r.open && (r.priority || 5) <= 2,
      })),
    }
  } catch {
    data.value = { stream: [], care: null, staff: [], rows: [], tabs: [], dispatch: null }
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)

function openCreate() {
  if (!form.value.room_id && rooms.value[0]?.id) form.value.room_id = rooms.value[0].id
  createOpen.value = true
}

async function submitCreate() {
  const rid = Number(form.value.room_id)
  if (!rid) {
    toast(t('请选择房间'), false)
    return
  }
  if (!form.value.content.trim()) {
    toast(t('请填写请求内容'), false)
    return
  }
  creating.value = true
  try {
    const aid = Number(form.value.assignee_id)
    const res = await api.createServiceRequest(hotelStore.hotelId, {
      room_id: rid,
      content: form.value.content.trim(),
      assignee_id: Number.isFinite(aid) && aid > 0 ? aid : undefined,
      priority: Number(form.value.priority) || 3,
    })
    toast(t('已录入 {room} 客需', { room: res?.room_no || '' }))
    createOpen.value = false
    form.value.content = ')'
    await load()
  } catch (e: any) {
    toast(e?.message || t('录入失败'), false)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="page">
    <RoomOpsNav />
    <HousekeepingTasksSubnav />
    <div
      class="page-head"
      style="
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        flex-wrap: wrap;
        gap: 12px;
      "
    >
      <div>
        <h1>{{ t('客中请求') }}</h1>
      </div>
      <div
        class="flex gap-3"
        style="flex-wrap: wrap; align-items: center; justify-content: flex-end"
      >
        <button class="btn btn-ghost" type="button">
          <span class="material-symbols-outlined">filter_list</span>{{ t('筛选') }}
        </button>
        <button class="btn btn-primary" type="button" @click="openCreate">
          <span class="material-symbols-outlined">add</span>{{ t('手动录入请求') }}
        </button>
      </div>
    </div>

    <div class="grid" style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px">
      <!-- 左 4：AI 解析流 + 主动关怀 -->
      <div style="grid-column: span 4" class="flex flex-col gap-4">
        <div class="card-clean card-pad shadow-sm flex flex-col" style="height: 400px">
          <div class="flex items-center justify-between mb-4 border-b border-outline-variant pb-3">
            <div class="flex items-center gap-2">
              <span
                class="material-symbols-outlined text-primary"
                style="font-variation-settings: 'FILL' 1"
                >insights</span
              >
              <h2 class="font-semibold text-lg text-on-surface">{{ t('AI 智能解析流') }}</h2>
            </div>
            <span
              class="flex items-center gap-1 text-xs text-primary bg-primary-fixed px-2 py-1 rounded-full font-label-lg"
            >
              <span class="w-1.5 h-1.5 bg-primary rounded-full pulse-dot"></span>
              {{ t('实时监听中') }}</span
            >
          </div>
          <div class="flex-1 overflow-y-auto pr-2 space-y-3">
            <template v-for="(s, i) in data.stream || []" :key="i">
              <div
                class="bg-surface rounded-lg p-3 border border-outline-variant transition-all hover:shadow-md cursor-pointer"
                :style="{ borderLeft: '3px solid var(--tertiary)' }"
              >
                <div class="flex justify-between items-start mb-2">
                  <div class="flex items-center gap-2">
                    <span
                      class="text-xs bg-surface-high px-1.5 py-0.5 rounded text-on-surface-variant"
                      >{{ s.channel }}</span
                    >
                    <span class="font-num-md text-on-surface">Room {{ s.room || s.room_no }}</span>
                  </div>
                  <span class="text-xs text-on-surface-variant">{{ s.time }}</span>
                </div>
                <p class="text-on-surface mb-2">{{ s.msg || s.content }}</p>
                <div
                  class="bg-surface-lowest p-2 rounded border border-outline-variant border-dashed flex items-center justify-between"
                >
                  <div class="flex items-center gap-2">
                    <span class="material-symbols-outlined text-tertiary text-[16px]"
                      >psychology</span
                    >
                    <span class="text-sm font-label-lg text-tertiary"
                      >{{ t('解析为:') }}
                      <span class="text-on-surface font-medium">{{ s.parse }}</span></span
                    >
                  </div>
                  <span
                    class="material-symbols-outlined text-[18px]"
                    :class="s.iot ? 'text-[#1e8e3e]' : 'text-primary'"
                    >{{ s.iot ? 'task_alt' : 'check_circle' }}</span
                  >
                </div>
              </div>
            </template>
          </div>
        </div>
        <div
          class="card-clean card-pad flex flex-col shadow-sm"
          style="border-left: 4px solid var(--tertiary)"
        >
          <div class="flex items-center gap-2 mb-3">
            <span
              class="material-symbols-outlined text-tertiary"
              style="font-variation-settings: 'FILL' 1"
              >favorite</span
            >
            <h2 class="font-semibold text-lg text-on-surface">
              {{ t('主动关怀建议 (Active Care)') }}
            </h2>
          </div>
          <div class="rounded-lg p-4" style="background: rgba(140, 51, 179, 0.12)">
            <div class="flex justify-between items-start mb-2">
              <span class="font-num-md text-on-tertiary-container"
                >Room {{ data.care?.room || '—' }}</span
              >
              <span
                class="px-2 py-0.5 text-tertiary-fixed rounded text-xs font-bold"
                style="background: #0e0017"
                >{{ data.care?.badge || t('主动关怀') }}</span
              >
            </div>
            <p class="text-sm text-on-tertiary-container mb-3">
              {{ data.care?.note || t('暂无主动关怀建议') }}
            </p>
            <div class="flex gap-2">
              <button
                class="flex-1 text-tertiary-fixed py-1.5 rounded-md text-sm font-label-lg hover:opacity-90 transition-opacity"
                style="background: #0e0017"
              >
                {{ t('派送小蛋糕') }}
              </button>
              <button
                class="px-3 border text-on-tertiary-container rounded-md text-sm font-label-lg hover:opacity-80 transition-colors"
                style="border-color: #0e0017"
              >
                {{ t('忽略') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右 8：智能调度中心 + 服务状态看板 -->
      <div style="grid-column: span 8" class="flex flex-col gap-4">
        <div class="card-clean card-pad shadow-sm">
          <div class="flex justify-between items-center mb-4">
            <h2 class="font-semibold text-lg text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">route</span
              >{{ t('智能调度中心 (Smart Dispatch)') }}
            </h2>
            <div class="flex items-center gap-4 text-sm">
              <span class="flex items-center gap-1"
                ><span class="w-3 h-3 rounded-full" style="background: #1e8e3e"></span
                >{{ t('空闲') }}</span
              >
              <span class="flex items-center gap-1"
                ><span class="w-3 h-3 rounded-full" style="background: #d97706"></span
                >{{ t('任务中') }}</span
              >
            </div>
          </div>
          <div class="grid grid-cols-3 gap-4">
            <template v-for="(st, i) in data.staff || []" :key="i">
              <div
                class="border border-outline-variant rounded-lg p-3 bg-surface hover:border-primary transition-colors cursor-pointer relative overflow-hidden"
              >
                <div
                  class="absolute top-0 right-0 w-2 h-full"
                  :style="{ background: st.busy ? '#d97706' : '#1e8e3e' }"
                ></div>
                <div class="flex items-center gap-3 mb-2">
                  <div
                    class="w-10 h-10 rounded-full bg-surface-high flex items-center justify-center text-on-surface-variant font-bold"
                  >
                    {{ st.tag }}
                  </div>
                  <div>
                    <div class="font-label-lg text-on-surface">{{ st.name }}</div>
                    <div class="text-xs text-on-surface-variant flex items-center gap-1">
                      <span class="material-symbols-outlined text-[14px]">location_on</span>
                      {{ st.loc }}
                    </div>
                  </div>
                </div>
                <div
                  class="bg-surface-lowest p-2 rounded mt-2 border border-outline-variant text-sm"
                >
                  <div class="flex justify-between text-on-surface-variant mb-1">
                    <span>{{
                      st.busy ? t('当前任务：{task}', { task: st.task }) : t('当前负荷')
                    }}</span>
                    <span :class="st.busy ? 'text-[#d97706]' : 'text-[#1e8e3e]'">{{
                      st.busy ? t('进行中') : st.load + '%'
                    }}</span>
                  </div>
                  <div class="w-full bg-surface-high rounded-full h-1.5">
                    <div
                      class="h-1.5 rounded-full"
                      :style="{
                        width: (st.busy ? 70 : st.load) + '%',
                        background: st.busy ? '#d97706' : '#1e8e3e',
                      }"
                    ></div>
                  </div>
                </div>
              </div>
            </template>
            <div
              class="border border-outline-variant border-dashed rounded-lg p-3 bg-primary-fixed/20 flex flex-col items-center justify-center text-center"
            >
              <span
                class="material-symbols-outlined text-primary text-[32px] mb-2"
                style="font-variation-settings: 'FILL' 1"
                >add_location_alt</span
              >
              <span class="text-sm text-on-surface font-medium mb-1">{{
                t('AI 正在为 {room} 请求匹配员工', { room: data.dispatch?.room || '—' })
              }}</span>
              <span class="text-xs text-on-surface-variant">{{
                t('预计派单给：{name}', { name: data.dispatch?.assignee || t('待匹配') })
              }}</span>
            </div>
          </div>
        </div>

        <div class="card-clean shadow-sm flex-1 flex flex-col overflow-hidden p-0">
          <div
            class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-lowest"
          >
            <h2 class="font-semibold text-lg text-on-surface">{{ t('服务状态看板') }}</h2>
            <div class="flex gap-2">
              <template v-for="(item, i) in data.tabs || []" :key="i">
                <span
                  class="px-3 py-1 rounded-full text-sm font-label-lg cursor-pointer"
                  :class="
                    t.active
                      ? 'bg-primary-container text-on-primary-container'
                      : 'bg-surface-high text-on-surface-variant'
                  "
                  :style="t.danger ? 'background:#ffdad6;color:#93000a' : ''"
                  >{{ t.label }}</span
                >
              </template>
            </div>
          </div>
          <div class="overflow-x-auto flex-1">
            <table class="table-data w-full text-left border-collapse">
              <thead class="bg-surface-low text-on-surface-variant text-sm font-label-lg">
                <tr>
                  <th class="p-4 font-medium border-b border-outline-variant">{{ t('房间号') }}</th>
                  <th class="p-4 font-medium border-b border-outline-variant">
                    {{ t('请求内容') }}
                  </th>
                  <th class="p-4 font-medium border-b border-outline-variant">{{ t('责任人') }}</th>
                  <th class="p-4 font-medium border-b border-outline-variant">
                    {{ t('状态/耗时') }}
                  </th>
                  <th class="p-4 font-medium border-b border-outline-variant">{{ t('操作') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant">
                <template v-for="(r, i) in data.rows || []" :key="i">
                  <tr
                    :class="
                      r.waiting
                        ? 'hover:bg-surface-lowest transition-colors'
                        : 'hover:bg-surface-lowest transition-colors'
                    "
                    :style="r.waiting ? 'background:rgba(186,26,26,.06)' : ''"
                  >
                    <td class="p-4">
                      <span class="font-num-md text-on-surface font-bold">{{ r.room }}</span>
                    </td>
                    <td class="p-4">
                      <div class="font-medium text-on-surface mb-0.5">{{ r.req }}</div>
                      <div class="text-xs text-on-surface-variant flex gap-2">
                        <span class="bg-surface-container px-1 rounded">{{ r.cat }}</span>
                        <span>来自: {{ r.source }}</span>
                      </div>
                    </td>
                    <td class="p-4 text-sm">{{ r.assignee || t('未分配') }}</td>
                    <td class="p-4">
                      <div class="flex items-center gap-2 mb-1">
                        <span class="w-2 h-2 rounded-full" :style="{ background: r.color }"></span>
                        <span class="text-sm font-medium" :style="{ color: r.color }">{{
                          r.status
                        }}</span>
                      </div>
                      <div class="text-xs text-on-surface-variant">{{ r.time }}</div>
                    </td>
                    <td class="p-4">
                      <button class="text-primary hover:opacity-80 text-sm font-medium">
                        {{ r.action }}
                      </button>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    <div v-if="createOpen" class="mask" @click.self="createOpen = false">
      <div class="panel" role="dialog" :aria-label="t('录入客中请求')">
        <header>
          <h3>{{ t('手动录入请求') }}</h3>
          <button type="button" class="x" @click="createOpen = false">×</button>
        </header>
        <div class="form">
          <label
            >{{ t('房间')
            }}<select v-model="form.room_id">
              <option value="">{{ t('请选择') }}</option>
              <option v-for="r in rooms" :key="r.id" :value="r.id">
                {{ r.room_no }}{{ r.floor ? ` · ${r.floor}F` : '' }}
              </option>
            </select>
          </label>
          <label
            >{{ t('内容')
            }}<textarea
              v-model="form.content"
              rows="3"
              :placeholder="t('例如：305 需要乳胶枕…')"
            ></textarea>
          </label>
          <label
            >{{ t('执行人（在班）')
            }}<select v-model="form.assignee_id">
              <option value="">{{ t('暂不指定') }}</option>
              <option v-for="s in onDuty" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </label>
          <label
            >{{ t('优先级')
            }}<select v-model.number="form.priority">
              <option :value="1">{{ t('紧急') }}</option>
              <option :value="2">{{ t('高') }}</option>
              <option :value="3">{{ t('普通') }}</option>
            </select>
          </label>
        </div>
        <footer>
          <button
            type="button"
            class="btn btn-ghost"
            :disabled="creating"
            @click="createOpen = false"
          >
            {{ t('取消') }}
          </button>
          <button type="button" class="btn btn-primary" :disabled="creating" @click="submitCreate">
            {{ creating ? t('提交中…') : t('一键创建') }}
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pulse-dot {
  animation: pulse-dot-anim 2s infinite;
}
@keyframes pulse-dot-anim {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(0, 91, 191, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 6px rgba(0, 91, 191, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(0, 91, 191, 0);
  }
}
@media (max-width: 900px) {
  .grid > div {
    grid-column: span 12 !important;
  }
}
.mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.panel {
  width: min(440px, 100%);
  background: #fff;
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.25);
}
.panel header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.panel h3 {
  margin: 0;
  font-size: 16px;
}
.panel .x {
  border: none;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
  color: #6b7280;
}
.hint {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}
.form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #4b5563;
}
.form select,
.form textarea {
  border-radius: 8px;
  border: 1px solid #d0d5dd;
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
}
.panel footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
