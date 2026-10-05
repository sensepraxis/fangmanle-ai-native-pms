<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'

// OTA 流量商圈分析与排名优化页：忠实移植自 ota.html 内容区
// 列表用 v-for；无数据时用 api.demo('ota') 兜底，缺失回退原型示例。

const hotelId = 1
const meta = ref<any>({
  title: t('OTA 流量商圈分析与排名优化'),
  subtitle: t('美团 / 携程 表现仪表盘'),
})

// 流量漏斗 3 根柱
const funnel = ref<any[]>([
  {
    label: t('曝光量'),
    sub: t('(曝光)'),
    value: '12.5k',
    height: 'h-[100%]',
    bar: 'bg-primary-container/20 hover:bg-primary-container/30',
  },
  {
    label: t('点击量'),
    sub: t('(点击)'),
    value: '5.6k',
    height: 'h-[45%]',
    bar: 'bg-primary-container/50 hover:bg-primary-container/60',
  },
  {
    label: t('预订'),
    sub: t('(订单)'),
    value: '184',
    height: 'h-[15%]',
    bar: 'bg-primary hover:bg-on-primary-fixed-variant',
  },
])

// AI 优化建议 2 张卡
const suggestions = ref<any[]>([
  {
    tag: t('高影响'),
    tagClass: 'bg-error-container/50 text-on-error-container',
    icon: 'bg-primary/10',
    title: '提升"美团超级会员"曝光',
    desc: t('开启会员专属价预计可提升搜索曝光约 15%。'),
    btn: t('应用策略'),
    btnClass: 'border-primary text-primary hover:bg-primary/5',
  },
  {
    tag: t('中影响'),
    tagClass: 'bg-surface-container-high text-on-surface-variant',
    icon: 'bg-secondary-container',
    title: t('更新房型照片以提升点击率'),
    desc: t('您的豪华房照片已超过 12 个月。新照片可提升点击率。'),
    btn: t('上传照片'),
    btnClass: 'border-outline text-on-surface hover:bg-surface-container-highest',
  },
])

// 竞品对标表
const competitors = ref<any[]>([
  {
    self: true,
    name: t('欢乐客房'),
    price: '¥450',
    score: '4.7',
    scoreNote: '(1.2k)',
    conv: '3.2%',
    convClass: 'text-on-surface',
    op: false,
  },
  {
    self: false,
    name: t('精品住宿 A'),
    price: '¥420',
    score: '4.8',
    scoreNote: '(800)',
    conv: '4.1%',
    convClass: 'text-success',
    op: true,
  },
  {
    self: false,
    name: t('市中心旅馆'),
    price: '¥480',
    score: '4.6',
    scoreNote: '(2.1k)',
    conv: '2.9%',
    convClass: 'text-on-surface',
    op: true,
  },
  {
    self: false,
    name: t('禅意设计酒店'),
    price: '¥520',
    score: '4.9',
    scoreNote: '(450)',
    conv: '3.5%',
    convClass: 'text-on-surface',
    op: true,
  },
])

onMounted(async () => {
  try {
    const r: any = await api.demo('ota')
    if (Array.isArray(r) && r.length) competitors.value = r // 主列表：竞品对标
  } catch (e) {
    /* 兜底：保留原型示例竞品 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="ota" /></div>
    <div class="max-w-max-content-width mx-auto">
      <!-- 页头 -->
      <div class="flex justify-between items-end mb-8">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-background mb-2">{{ meta.title }}</h1>
          <p class="font-body-lg text-body-lg text-on-surface-variant">{{ meta.subtitle }}</p>
        </div>
        <div class="flex gap-4">
          <select
            class="bg-surface border border-outline-variant rounded-lg px-4 py-2 font-label-lg text-label-lg text-on-surface focus:ring-primary focus:border-primary"
          >
            <option>{{ t('近 7 天') }}</option>
            <option>{{ t('近 30 天') }}</option>
          </select>
          <button
            class="bg-primary text-on-primary font-label-lg text-label-lg px-6 py-2 rounded-lg hover:bg-on-primary-fixed-variant transition-colors flex items-center gap-2"
          >
            {{ t('刷新数据') }}
          </button>
        </div>
      </div>

      <div class="grid grid-cols-12 gap-gutter">
        <!-- 商圈流量排名 -->
        <div
          class="col-span-12 md:col-span-4 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant relative overflow-hidden group"
        >
          <div
            class="absolute -right-10 -top-10 w-32 h-32 bg-primary-container/10 rounded-full blur-2xl group-hover:bg-primary-container/20 transition-all duration-500"
          ></div>
          <h2
            class="font-headline-md text-headline-md text-on-background mb-4 flex items-center gap-2"
          >
            {{ t('商圈流量排名') }}
          </h2>
          <div class="flex items-baseline gap-2 mb-2">
            <span class="font-num-xl text-[48px] leading-tight text-primary">{{ t('前 5%') }}</span>
            <span class="font-label-lg text-label-lg text-on-surface-variant">{{
              t('区域内（CBD）')
            }}</span>
          </div>
          <div class="flex items-center gap-2 text-success" style="color: #146c2e">
            <span class="font-label-lg text-label-lg">{{ t('较上周 +2 位') }}</span>
          </div>
          <div class="mt-6 pt-6 border-t border-outline-variant">
            <p class="font-body-md text-body-md text-on-surface-variant mb-2">
              {{ t('平台拆分') }}
            </p>
            <div class="flex justify-between items-center mb-2">
              <span class="font-label-lg text-label-lg text-on-surface">{{ t('美团') }}</span>
              <span class="font-num-md text-num-md text-on-surface">#4</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="font-label-lg text-label-lg text-on-surface">Ctrip</span>
              <span class="font-num-md text-num-md text-on-surface">#7</span>
            </div>
          </div>
        </div>

        <!-- 流量漏斗分析 -->
        <div
          class="col-span-12 md:col-span-8 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant ai-border-tinge shadow-[0_4px_12px_rgba(0,0,0,0.03)]"
        >
          <div class="flex justify-between items-start mb-6">
            <h2
              class="font-headline-md text-headline-md text-on-background flex items-center gap-2"
            >
              {{ t('流量漏斗分析') }}
            </h2>
            <div
              class="bg-tertiary-container/10 text-tertiary font-label-lg text-label-lg px-3 py-1 rounded-full flex items-center gap-1"
            >
              {{ t('AI 洞察已启用') }}
            </div>
          </div>
          <div class="flex gap-8 items-end h-[180px] relative">
            <div
              v-for="f in funnel"
              :key="f.label"
              class="flex flex-col flex-1 items-center justify-end h-full"
            >
              <div
                class="w-full rounded-t-lg flex flex-col justify-end p-2 relative group cursor-pointer"
                :class="[f.height, f.bar]"
              >
                <span
                  class="absolute -top-8 left-1/2 -translate-x-1/2 font-num-xl text-num-xl text-on-surface"
                  >{{ f.value }}</span
                >
              </div>
              <span class="mt-4 font-label-lg text-label-lg text-on-surface-variant text-center"
                >{{ f.label }}<br />{{ f.sub }}</span
              >
            </div>
          </div>
          <div
            class="mt-8 bg-surface-bright rounded-lg p-4 border border-tertiary/20 flex gap-4 items-start"
          >
            <div>
              <p class="font-label-lg text-label-lg text-on-surface mb-1">
                {{ t('点击到预订的流失高于区域均值。') }}
              </p>
              <p class="font-body-md text-body-md text-on-surface-variant">
                {{
                  t(
                    '客人在点击您的房源但未下单。这通常表明期望（封面图/价格）与现实（评价/房型详情）之间存在偏差。',
                  )
                }}
              </p>
            </div>
          </div>
        </div>

        <!-- AI 优化建议 -->
        <div class="col-span-12 md:col-span-4 flex flex-col gap-gutter">
          <h2
            class="font-headline-md text-headline-md text-on-background flex items-center gap-2 mb-2"
          >
            {{ t('AI 优化建议') }}
          </h2>
          <div
            v-for="s in suggestions"
            :key="s.title"
            class="bg-surface-container-lowest rounded-xl p-5 border border-outline-variant hover:shadow-[0_4px_12px_rgba(0,0,0,0.05)] transition-shadow"
          >
            <div class="flex justify-between items-start mb-3">
              <div class="p-2 rounded-lg" :class="s.icon"></div>
              <span
                class="px-2 py-1 rounded text-xs font-label-lg text-label-lg"
                :class="s.tagClass"
                >{{ s.tag }}</span
              >
            </div>
            <h3 class="font-label-lg text-label-lg text-on-surface mb-2">{{ s.title }}</h3>
            <p class="font-body-md text-[14px] leading-tight text-on-surface-variant mb-4">
              {{ s.desc }}
            </p>
            <button
              class="w-full py-2 border rounded-lg font-label-lg text-label-lg transition-colors"
              :class="s.btnClass"
            >
              {{ s.btn }}
            </button>
          </div>
        </div>

        <!-- 竞品对标 -->
        <div
          class="col-span-12 md:col-span-8 bg-surface-container-lowest rounded-xl p-6 border border-outline-variant"
        >
          <h2
            class="font-headline-md text-headline-md text-on-background flex items-center gap-2 mb-6"
          >
            {{ t('竞品对标') }}
          </h2>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant">
                  <th
                    class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant font-medium"
                  >
                    {{ t('酒店') }}
                  </th>
                  <th
                    class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant font-medium"
                  >
                    {{ t('平均价格') }}
                  </th>
                  <th
                    class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant font-medium"
                  >
                    {{ t('评分') }}
                  </th>
                  <th
                    class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant font-medium"
                  >
                    {{ t('转化率') }}
                  </th>
                  <th
                    class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant font-medium"
                  >
                    {{ t('操作') }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="c in competitors"
                  :key="c.name"
                  :class="[
                    c.self
                      ? 'bg-primary/5 border-b border-outline-variant'
                      : 'border-b border-outline-variant hover:bg-surface-container-lowest transition-colors',
                  ]"
                >
                  <td
                    class="py-4 px-4 font-label-lg text-label-lg"
                    :class="
                      c.self ? 'text-primary font-bold flex items-center gap-2' : 'text-on-surface'
                    "
                  >
                    <template v-if="c.self"
                      ><div
                        class="w-8 h-8 rounded bg-primary-container/20 flex items-center justify-center"
                      ></div>
                      {{ t('欢乐客房') }}</template
                    >
                    <template v-else>{{ c.name }}</template>
                  </td>
                  <td class="py-4 px-4 font-num-md text-num-md text-on-surface">{{ c.price }}</td>
                  <td class="py-4 px-4 font-num-md text-num-md text-on-surface">
                    {{ c.score }}<span class="text-tertiary text-sm" v-if="c.self">(1.2k)</span
                    ><span class="text-on-surface-variant text-sm" v-else>{{ c.scoreNote }}</span>
                  </td>
                  <td
                    class="py-4 px-4 font-num-md text-num-md"
                    :class="c.convClass"
                    style="color: #146c2e"
                  >
                    {{ c.conv }}
                  </td>
                  <td class="py-4 px-4 text-on-surface-variant">
                    {{ c.self ? '-' : ''
                    }}<button
                      v-if="c.op"
                      class="text-primary hover:bg-primary/10 p-1 rounded transition-colors"
                    ></button>
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
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
.ai-border-tinge {
  border-left: 2px solid #a84fce;
}
</style>
