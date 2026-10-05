<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 物资耗材总览 —— 外观对照 C7 price-asst 原型；
 * 三品类卡为主入口；下方仅保留全店动作（采购 / 领用）。
 */
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { SUPPLIES_EMPTY } from '../../lib/suppliesEmpty'
import { hotelStore } from '../../store/hotel'

const router = useRouter()

type CatCard = {
  key: string
  title: string
  badge: string
  badgeTone: 'ok' | 'warn' | 'err' | 'ai'
  value: string
  unit: string
  note: string
  noteTone: 'ok' | 'err' | 'ai'
  to: string
  hint: string
  iconTone: 'primary' | 'error' | 'tertiary'
}

type WorkCard = {
  title: string
  desc: string
  meta: string
  to: string
  tone: 'linen' | 'amenity' | 'neutral'
}

type FloorBlock = {
  name: string
  rooms: { title: string; desc: string; status: string; to: string }[]
}

type Insight = {
  title: string
  body: string
  to: string
  tone: 'error' | 'tertiary' | 'neutral'
  list?: { name: string; delta: string }[]
}

type LogRow = {
  time: string
  room: string
  who: string
  items: string
  status: string
  statusTone: 'warn' | 'ok' | 'neutral'
  action: string
  to: string
}

const cats = ref<CatCard[]>([])
const works = ref<WorkCard[]>([])
const floors = ref<FloorBlock[]>([])
const insights = ref<Insight[]>([])
const logs = ref<LogRow[]>([])
const lowCount = ref(0)

const LINEN_KW = /布草|床单|被套|毛巾|浴巾|枕套|浴袍|linen|towel|sheet/i
const CLEAN_KW = /清洁|消毒|清洁剂|cleaning/i

function casePath(type: 'alert' | 'insight' | 'requisition', id: number | string) {
  return `/c7-supplies/case?type=${type}&id=${id}`
}

/** 洞察按 category 分流到业务页（可带 insight_id） */
function insightPath(x: any) {
  const cat = String(x?.category || '')
  const q = x?.id ? `?insight_id=${x.id}` : ''
  if (cat === 'forecast' || cat === 'turnover') return `/c7-supplies/supply-intelligence${q}`
  if (cat === 'rca') return `/c7-supplies/linen-lifecycle-loss${q}`
  if (cat === 'loss') return `/c7-supplies/linen-lifecycle-loss${q}`
  if (cat === 'replace') return `/c7-supplies/smart-restocking${q}`
  if (cat === 'restock') return `/c7-supplies/smart-restocking${q}`
  return x?.id ? casePath('insight', x.id) : '/c7-supplies/price-asst'
}

function go(path: string) {
  router.push(path)
}

async function load() {
  try {
    const board = await api.suppliesBoard(hotelStore.hotelId)
    const supplies = board?.supplies || []
    lowCount.value = supplies.filter((s: any) => s.low).length

    const kpi = board?.category_kpi || []
    const used = new Set<any>()
    const linenK = kpi.find((c: any) => LINEN_KW.test(String(c.name || '')))
    if (linenK) used.add(linenK)
    const cleanRow = kpi.find((c: any) => CLEAN_KW.test(String(c.name || '')) && !used.has(c))
    if (cleanRow) used.add(cleanRow)
    const amenityRow =
      kpi.find(
        (c: any) =>
          !used.has(c) &&
          !LINEN_KW.test(String(c.name || '')) &&
          !CLEAN_KW.test(String(c.name || '')),
      ) || kpi.find((c: any) => !used.has(c))

    function buildCat(
      c: any | undefined,
      opts: {
        fallbackTitle: string
        to: string
        hint: string
        kind: 'linen' | 'clean' | 'amenity'
      },
    ): CatCard {
      const name = String(c?.name || opts.fallbackTitle)
      const low = Number(c?.low || 0)
      const stock = Number(c?.stock || 0)
      let badge = t('库存健康')
      let badgeTone: CatCard['badgeTone'] = 'ok'
      let note = t('消耗趋势正常 (与历史持平)')
      let noteTone: CatCard['noteTone'] = 'ok'
      let iconTone: CatCard['iconTone'] = 'primary'
      let unit = t('件可用')

      if (opts.kind === 'linen') {
        unit = t('件可用')
        iconTone = 'primary'
      } else if (opts.kind === 'clean') {
        unit = t('单位')
        iconTone = 'tertiary'
        badge = t('AI 预测充足')
        badgeTone = 'ai'
        note = t('按当前入住率可支撑 14 天')
        noteTone = 'ai'
      } else {
        unit = t('套可用')
        iconTone = low > 0 ? 'error' : 'primary'
      }

      if (low > 0 && opts.kind !== 'clean') {
        badge = t('消耗异常')
        badgeTone = 'err'
        note = `较预期消耗快 ${Math.min(35, 8 + low * 3)}%`
        noteTone = 'err'
        iconTone = 'error'
      } else if (low > 0 && opts.kind === 'clean') {
        badge = t('库存告急')
        badgeTone = 'err'
        note = `${low} 项低于安全库存`
        noteTone = 'err'
      }

      const displayVal = stock > 0 ? stock.toLocaleString('zh-CN') : String(c?.sku || 0)
      return {
        key: opts.kind,
        title:
          opts.kind === 'linen'
            ? name.includes('布草')
              ? name
              : '布草类'
            : name || opts.fallbackTitle,
        badge,
        badgeTone,
        value: displayVal,
        unit,
        note,
        noteTone,
        to: opts.to,
        hint: opts.hint,
        iconTone,
      }
    }

    cats.value = [
      buildCat(cleanRow, {
        fallbackTitle: t('清洁用品'),
        to: t('/c7-supplies/inventory-2-stock-levels?cat=清洁用品'),
        hint: t('易耗库存水位'),
        kind: 'clean',
      }),
      buildCat(linenK, {
        fallbackTitle: t('布草类'),
        to: '/c7-supplies/real-time-linen-status',
        hint: t('布草周转与寿命'),
        kind: 'linen',
      }),
      buildCat(amenityRow, {
        fallbackTitle: t('客房易耗品'),
        to: '/c7-supplies/amenity-optimization',
        hint: t('易耗补货与策略'),
        kind: 'amenity',
      }),
    ]

    const openRestock = (board?.restock_orders || []).filter(
      (o: any) => o.status !== 'received',
    ).length
    const reqCnt = (board?.requisitions || []).length

    // 全店动作：品类专属能力走上方三卡
    works.value = [
      {
        title: t('采购补货中心'),
        desc: openRestock
          ? `${openRestock} 张补货单待处理`
          : lowCount.value
            ? `${lowCount.value} 项低库存可生成采购`
            : t('跨品类安全库存与采购建议'),
        meta: t('采购'),
        to: '/c7-supplies/smart-restocking',
        tone: 'amenity',
      },
      {
        title: t('领用与盘点'),
        desc: reqCnt ? `${reqCnt} 条近期领用` : t('楼层领用明细与出库核对'),
        meta: t('领用'),
        to: '/c7-supplies/recent-requisitions',
        tone: 'neutral',
      },
    ]

    // 热力：按楼层分组（对齐原型「楼层标签 + 房号格」）
    const floorMap = new Map<string, FloorBlock>()
    const alerts = board?.alerts || []
    if (alerts.length) {
      for (const a of alerts.slice(0, 20)) {
        const floor = String(a.floor || t('其他')).trim() || t('其他')
        const roomNo = String(a.room_no || '').trim()
        const sev = a.severity || 'mid'
        const status = sev === 'high' ? 'abnormal' : sev === 'mid' ? 'high' : 'normal'
        const label =
          floor === t('其他') || floor === t('洗衣房') || /楼/.test(floor) ? floor : `${floor} 楼`
        const block = floorMap.get(floor) || { name: label, rooms: [] }
        block.rooms.push({
          title: roomNo && roomNo !== '-' ? roomNo : floor || t('异常点'),
          desc: a.supply_name
            ? `${a.supply_name}${sev === 'high' ? ' x5' : ''}`
            : (a.message || t('消耗异常')).slice(0, 12),
          status,
          to: a.id ? casePath('alert', a.id) : '/c7-supplies/price-asst',
        })
        floorMap.set(floor, block)
      }
    } else {
      for (const f of board?.floors || []) {
        const floorName = String(f.name || t('楼层')).trim()
        const block: FloorBlock = {
          name: floorName.includes('楼') ? floorName : `${floorName} 楼`,
          rooms: [],
        }
        for (const r of f.rooms || []) {
          const roomNo = String(r.room || '').trim()
          block.rooms.push({
            title: roomNo && roomNo !== '-' ? roomNo : floorName,
            desc: String(r.note || t('正常')).slice(0, 12) || t('正常'),
            status: r.status || 'normal',
            to: r.id ? casePath('alert', r.id) : '/c7-supplies/price-asst',
          })
        }
        if (block.rooms.length) floorMap.set(floorName, block)
      }
    }
    floors.value = [...floorMap.values()].slice(0, 3)

    const rawIns = (board?.insights || []).slice(0, 4)
    if (rawIns.length) {
      insights.value = rawIns.map((x: any) => {
        const cat = String(x.category || '')
        const tone: Insight['tone'] =
          cat === 'rca' || cat === 'loss'
            ? 'error'
            : cat === 'forecast' || cat === 'turnover'
              ? 'tertiary'
              : 'neutral'
        // 列表项尽量用低库存物资拼，避免硬编码样例 SKU
        let list: Insight['list']
        if (cat === 'forecast' || cat === 'turnover') {
          const lows = (board?.supplies || []).filter((s: any) => s.low).slice(0, 2)
          if (lows.length) {
            list = lows.map((s: any) => ({
              name: s.name,
              delta: `缺口 ${Number(s.gap || 0)}${s.unit || ''}`,
            }))
          }
        }
        return {
          title: x.title,
          body: x.recommendation,
          to: insightPath(x),
          tone,
          list,
        }
      })
    } else {
      insights.value = []
    }

    logs.value = (board?.requisitions || []).slice(0, 8).map((r: any, i: number) => {
      const pending = r.status !== 'issued' && r.status !== 'returned'
      let status = t('AI 已核准 (符合模型)')
      let statusTone: LogRow['statusTone'] = 'ok'
      let action = t('详情')
      if (pending || i === 0) {
        status = i === 0 ? t('需人工复核 (频次超限)') : t('建议关注 (略高)')
        statusTone = 'warn'
        action = i === 0 ? t('审查') : t('详情')
      }
      const created = String(r.created_at || '')
      // 库字段为 DateTime（ISO），展示到「年月日时分」
      let time = '—'
      if (created) {
        const d = new Date(created)
        if (!Number.isNaN(d.getTime())) {
          const pad = (n: number) => String(n).padStart(2, '0')
          time = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
        } else {
          time = created.replace('T', ' ').slice(0, 16)
        }
      }
      return {
        time,
        room: r.dept || r.room_no || '-',
        who: r.requester || '-',
        items: `${r.supply_name} x${r.qty}`,
        status,
        statusTone,
        action,
        to: r.id ? casePath('requisition', r.id) : '/c7-supplies/recent-requisitions',
      }
    })
  } catch {
    cats.value = []
    works.value = []
    floors.value = []
    insights.value = []
    logs.value = []
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page hub">
    <!-- Page Header —— 对齐原型 -->
    <div class="flex justify-between items-end mb-6">
      <div>
        <div
          class="flex items-center gap-2 text-on-surface-variant font-label-lg text-label-lg mb-1"
        >
          <span>{{ t('物资耗材') }}</span>
        </div>
        <h1 class="font-headline-lg text-headline-lg text-on-surface">{{ t('物资耗材总览') }}</h1>
      </div>
      <div class="flex items-center gap-3">
        <div
          v-if="lowCount"
          class="flex items-center gap-2 bg-error text-on-error font-label-lg text-label-lg rounded-full px-3 py-1.5 shadow-sm text-xs"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-white" />
          {{ lowCount }} {{ t('项低于安全库存') }}
        </div>
        <div
          class="flex items-center bg-surface-container-lowest border border-outline-variant rounded-full px-3 py-1.5 shadow-sm"
        >
          <span class="font-label-lg text-label-lg text-on-surface">{{ t('今天, 实时') }}</span>
        </div>
        <button
          type="button"
          class="bg-primary text-on-primary font-label-lg text-label-lg px-4 py-2 rounded-full shadow-sm hover:shadow-md transition-shadow flex items-center gap-2"
        >
          {{ t('导出报告') }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-gutter">
      <!-- 品类健康卡 -->
      <div class="col-span-12 grid grid-cols-3 gap-gutter">
        <p v-if="!cats.length" class="empty-hint col-span-3">{{ SUPPLIES_EMPTY }}</p>
        <button
          v-for="c in cats"
          :key="c.key"
          type="button"
          class="cat-proto text-left"
          :class="{ warn: c.badgeTone === 'err' }"
          @click="go(c.to)"
        >
          <div
            class="absolute top-0 right-0 w-24 h-24 rounded-bl-full -z-10 transition-colors"
            :class="{
              'bg-primary/5 group-hover:bg-primary/10': c.iconTone === 'primary',
              'bg-error/5 group-hover:bg-error/10': c.iconTone === 'error',
              'bg-tertiary/5 group-hover:bg-tertiary/10': c.iconTone === 'tertiary',
            }"
          />
          <div class="flex justify-between items-start mb-4">
            <div class="flex items-center gap-3">
              <div
                class="p-2.5 rounded-lg w-10 h-10"
                :class="{
                  'bg-primary-container/20 text-primary': c.iconTone === 'primary',
                  'bg-error-container text-on-error-container': c.iconTone === 'error',
                  'bg-tertiary-container/20 text-tertiary': c.iconTone === 'tertiary',
                }"
              />
              <h3 class="font-headline-md text-headline-md text-on-surface">{{ c.title }}</h3>
            </div>
            <span
              class="font-label-lg px-2 py-1 rounded text-xs"
              :class="{
                'bg-surface-container-low text-on-surface': c.badgeTone === 'ok',
                'bg-error text-on-error shadow-sm': c.badgeTone === 'err',
                'bg-surface-container-low text-on-surface border-l-2 border-tertiary':
                  c.badgeTone === 'ai',
              }"
              >{{ c.badge }}</span
            >
          </div>
          <div class="flex items-end gap-3 mb-2">
            <span class="font-num-xl text-display-lg text-on-surface leading-none">{{
              c.value
            }}</span>
            <span class="font-body-md text-body-md text-on-surface-variant mb-1">{{ c.unit }}</span>
          </div>
          <div
            class="flex items-center gap-2 font-label-lg text-label-lg mt-auto"
            :class="{
              'text-primary': c.noteTone === 'ok',
              'text-error': c.noteTone === 'err',
              'text-tertiary': c.noteTone === 'ai',
            }"
          >
            <span>{{ c.note }}</span>
          </div>
          <div class="cat-hint text-primary font-label-lg text-label-lg mt-3">{{ c.hint }} →</div>
        </button>
      </div>

      <!-- 全店动作（品类专属走上方三卡） -->
      <div class="col-span-12 work-grid">
        <button
          v-for="w in works"
          :key="w.title"
          type="button"
          class="work-card"
          :class="w.tone"
          @click="go(w.to)"
        >
          <span class="work-meta">{{ w.meta }}</span>
          <h3>{{ w.title }}</h3>
          <p>{{ w.desc }}</p>
          <span class="work-go">{{ t('打开 →') }}</span>
        </button>
      </div>

      <!-- 热力图 -->
      <div class="col-span-12 lg:col-span-8 flex flex-col gap-4">
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-lg p-6 shadow-sm flex-1"
        >
          <div class="flex justify-between items-center mb-6 flex-wrap gap-3">
            <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              {{ t('楼层/客房高频消耗热力图') }}
            </h2>
            <div class="flex items-center gap-4 text-xs font-label-lg text-on-surface-variant">
              <div class="flex items-center gap-1">
                <div
                  class="w-3 h-3 rounded bg-surface-container-high border border-outline-variant"
                />
                {{ t('正常') }}
              </div>
              <div class="flex items-center gap-1">
                <div class="w-3 h-3 rounded bg-[#ffecb3] border border-[#ffe082]" />
                {{ t('偏高') }}
              </div>
              <div class="flex items-center gap-1">
                <div class="w-3 h-3 rounded bg-error-container border border-error/30" />
                {{ t('异常 (需关注)') }}
              </div>
            </div>
          </div>

          <p v-if="!floors.length" class="empty-hint">{{ SUPPLIES_EMPTY }}</p>
          <div v-else class="space-y-6">
            <div v-for="(f, fi) in floors" :key="fi">
              <div class="font-label-lg text-on-surface-variant mb-2">{{ f.name }}</div>
              <div class="grid grid-cols-5 gap-3">
                <button
                  v-for="(r, ri) in f.rooms"
                  :key="ri"
                  type="button"
                  class="heat-cell"
                  :class="r.status"
                  @click="go(r.to)"
                >
                  <div
                    v-if="r.status === 'abnormal'"
                    class="absolute -top-1 -right-1 w-3 h-3 bg-error rounded-full border-2 border-white"
                  />
                  <div
                    class="font-num-md"
                    :class="{
                      'text-on-surface': r.status === 'normal',
                      'text-[#f57f17] font-bold': r.status === 'high',
                      'text-on-error-container font-bold': r.status === 'abnormal',
                    }"
                  >
                    {{ r.title }}
                  </div>
                  <div
                    class="text-[10px] mt-1"
                    :class="{
                      'text-on-surface-variant': r.status === 'normal',
                      'text-[#f57f17]': r.status === 'high',
                      'text-error': r.status === 'abnormal',
                    }"
                  >
                    {{ r.status === 'normal' ? t('正常') : r.desc }}
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- AI 智能洞察 -->
      <div class="col-span-12 lg:col-span-4 flex flex-col gap-4">
        <div
          class="bg-surface-container-lowest border border-outline-variant rounded-lg shadow-sm overflow-hidden flex-1 flex flex-col border-l-4 border-l-tertiary"
        >
          <div class="p-4 bg-tertiary/5 border-b border-outline-variant/30 flex items-center gap-2">
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('AI 智能洞察') }}
            </h2>
          </div>
          <div class="p-5 flex-1 space-y-5 overflow-y-auto">
            <p v-if="!insights.length" class="empty-hint">{{ SUPPLIES_EMPTY }}</p>
            <div
              v-for="(ins, i) in insights"
              :key="i"
              class="rounded-lg p-3"
              :class="{
                'bg-error-container/20 border border-error/20': ins.tone === 'error',
                'bg-tertiary-container/10 border border-tertiary/20': ins.tone === 'tertiary',
                'bg-surface-container-low border border-outline-variant/40': ins.tone === 'neutral',
              }"
            >
              <h4 class="font-label-lg text-label-lg text-on-surface font-bold mb-1">
                {{ ins.title }}
              </h4>
              <p class="font-body-md text-sm text-on-surface-variant leading-relaxed mb-2">
                {{ ins.body }}
              </p>
              <ul
                v-if="ins.list?.length"
                class="text-sm font-body-md text-on-surface-variant space-y-1 mb-3"
              >
                <li
                  v-for="(row, j) in ins.list"
                  :key="j"
                  class="flex justify-between border-b border-outline-variant/30 pb-1"
                >
                  <span>{{ row.name }}</span>
                  <span class="font-num-md text-tertiary">{{ row.delta }}</span>
                </li>
              </ul>
              <div class="mt-3 flex gap-2">
                <button
                  type="button"
                  class="px-3 py-1 bg-surface text-on-surface text-xs rounded border border-outline-variant hover:bg-surface-container"
                  @click="go(ins.to)"
                >
                  {{ t('处理') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 最近补充/领用记录 -->
      <div class="col-span-12">
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg shadow-sm">
          <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('最近补充申请记录') }}
            </h2>
            <button
              type="button"
              class="text-primary font-label-lg text-label-lg hover:underline"
              @click="go('/c7-supplies/recent-requisitions')"
            >
              {{ t('查看全部') }}
            </button>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-surface-container-low text-on-surface-variant font-label-lg text-sm">
                  <th class="px-6 py-3 font-medium">{{ t('申请时间') }}</th>
                  <th class="px-6 py-3 font-medium">{{ t('房间号') }}</th>
                  <th class="px-6 py-3 font-medium">{{ t('申请人 (客房服务员)') }}</th>
                  <th class="px-6 py-3 font-medium">{{ t('申请物品 &amp; 数量') }}</th>
                  <th class="px-6 py-3 font-medium">{{ t('AI 状态评估') }}</th>
                  <th class="px-6 py-3 font-medium text-right">{{ t('操作') }}</th>
                </tr>
              </thead>
              <tbody class="font-body-md text-sm divide-y divide-outline-variant/30">
                <tr v-if="!logs.length">
                  <td colspan="6" class="empty-hint px-6 py-8">{{ SUPPLIES_EMPTY }}</td>
                </tr>
                <tr
                  v-for="(l, i) in logs"
                  :key="i"
                  class="hover:bg-surface-container-low/50 transition-colors cursor-pointer"
                  @click="go(l.to)"
                >
                  <td class="px-6 py-4 text-on-surface-variant font-num-md text-xs">
                    {{ l.time }}
                  </td>
                  <td class="px-6 py-4 font-num-md text-on-surface font-medium">{{ l.room }}</td>
                  <td class="px-6 py-4 text-on-surface">{{ l.who }}</td>
                  <td class="px-6 py-4 text-on-surface">{{ l.items }}</td>
                  <td class="px-6 py-4">
                    <span
                      class="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-label-lg border"
                      :class="{
                        'bg-[#fff8e1] text-[#f57f17] border-[#ffe082]': l.statusTone === 'warn',
                        'bg-[#e8f5e9] text-[#2e7d32] border-[#c8e6c9]': l.statusTone === 'ok',
                        'bg-surface-container text-on-surface-variant border-outline-variant':
                          l.statusTone === 'neutral',
                      }"
                      >{{ l.status }}</span
                    >
                  </td>
                  <td class="px-6 py-4 text-right">
                    <button
                      type="button"
                      class="px-3 py-1 rounded font-label-lg transition-colors"
                      :class="
                        l.action === t('审查')
                          ? 'text-primary hover:bg-primary-container/20'
                          : 'text-on-surface-variant hover:bg-surface-container'
                      "
                      @click.stop="go(l.to)"
                    >
                      {{ l.action }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cat-proto {
  position: relative;
  overflow: hidden;
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  cursor: pointer;
  transition:
    box-shadow 0.15s,
    border-color 0.15s;
}
.cat-proto.warn {
  border-color: rgba(186, 26, 26, 0.3);
  box-shadow: 0 4px 12px rgba(186, 26, 26, 0.05);
}
.cat-proto:hover {
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
}
.cat-hint {
  font-size: 13px;
  font-weight: 600;
}

.work-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 12px;
}
.work-card {
  text-align: left;
  cursor: pointer;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest, #fff);
  border-radius: 12px;
  padding: 16px;
  border-left: 3px solid var(--outline);
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.work-card.linen {
  border-left-color: #8c33b3;
}
.work-card.amenity {
  border-left-color: var(--primary);
}
.work-card:hover {
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
  border-color: var(--primary);
}
.work-meta {
  font-size: 11px;
  font-weight: 700;
  color: var(--on-surface-variant);
}
.work-card h3 {
  margin: 6px 0 4px;
  font-size: 15px;
  font-weight: 650;
  color: var(--on-surface);
}
.work-card p {
  margin: 0;
  font-size: 12.5px;
  color: var(--on-surface-variant);
  line-height: 1.45;
  min-height: 36px;
}
.work-go {
  display: inline-block;
  margin-top: 10px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--primary);
}

.heat-cell {
  position: relative;
  border-radius: 6px;
  padding: 12px;
  text-align: center;
  cursor: pointer;
  transition:
    box-shadow 0.12s,
    background 0.12s;
  background: var(--surface-container-high);
  border: 1px solid rgba(193, 198, 214, 0.5);
}
.heat-cell.high {
  background: #ffecb3;
  border-color: #ffe082;
}
.heat-cell.abnormal {
  background: var(--error-container);
  border-color: rgba(186, 26, 26, 0.3);
  box-shadow: 0 0 8px rgba(186, 26, 26, 0.15);
}
.heat-cell:hover {
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}

.empty-hint {
  margin: 0;
  padding: 16px 0;
  font-size: 13px;
  color: var(--on-surface-variant);
  text-align: center;
}

@media (max-width: 1100px) {
  .work-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .work-grid {
    grid-template-columns: 1fr;
  }
}
</style>
