<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'

// 抖音获客页：忠实移植自 douyin-acquisition.html（仅内容区，外壳由 App.vue 提供）
// 列表用 v-for 渲染；无真实实体接口时用 api.demo('douyin-acquisition') 兜底，
// demo 返回空数组时回退下方原型示例值，保证版式 1:1。

const hotelId = 1

// 页面标题与副标题（绑定 meta，无数据时保留原型示例文）
const meta = ref<any>({ title: t('抖音获客'), subtitle: t('管理 POI、团购券与 AI 内容种草。') })

// 转化漏斗（近 30 天）4 步
const funnel = ref<any[]>([
  {
    label: t('浏览量'),
    value: '45,210',
    sub: '',
    circle: 'bg-surface-container border-2 border-surface',
    valueClass: 'text-primary',
  },
  {
    label: t('点击量'),
    value: '8,432',
    sub: '18.6%',
    circle: 'bg-surface-container border-2 border-surface',
    valueClass: 'text-primary',
  },
  {
    label: t('券销量'),
    value: '1,204',
    sub: '14.2%',
    circle: 'bg-primary-fixed border-2 border-surface',
    valueClass: 'text-primary',
  },
  {
    label: t('已验证'),
    value: '890',
    sub: '73.9%',
    circle: 'bg-tertiary-fixed border-2 border-surface',
    valueClass: 'text-tertiary',
  },
])

// 团购券列表（主列表，受 api.demo 覆盖）
const coupons = ref<any[]>([
  {
    price: '¥299',
    priceClass: 'bg-primary-container text-on-primary-container',
    name: t('1 晚 + 早餐 (周末)'),
    expire: t('有效期至 2024年10月31日'),
    sold: t('已售 842'),
    status: t('启用'),
    statusClass: 'text-green-600',
  },
  {
    price: '¥599',
    priceClass: 'bg-surface-container text-on-surface-variant',
    name: t('2 晚家庭套房套餐'),
    expire: t('有效期至 2024年12月31日'),
    sold: t('已售 362'),
    status: t('即将过期'),
    statusClass: 'text-orange-600',
  },
])

// AI 脚本生成器时间线
const scripts = ref<any[]>([
  {
    title: t('分析趋势'),
    desc: t('已提取本地热门旅游标签。'),
    dot: 'bg-tertiary text-white',
    box: 'bg-surface border-outline-variant',
  },
  {
    title: t('生成钩子'),
    desc: t('“看完这个再订你的周末游……”'),
    dot: 'bg-tertiary-container text-on-tertiary-container',
    box: 'bg-tertiary-fixed border-tertiary-fixed',
  },
])

// 抖音来客 POI 状态
const poi = ref<any>({ account: t('抖音来客'), status: t('已绑定且激活'), tag: t('抖音') })

onMounted(async () => {
  try {
    const r: any = await api.demo('douyin-acquisition')
    if (Array.isArray(r) && r.length) coupons.value = r // demo 返回数组直接 v-for
  } catch (e) {
    /* 兜底：保留原型示例团购券 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="douyin" /></div>
    <div class="max-w-[1440px] mx-auto space-y-6">
      <!-- 页头 -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="font-headline-lg text-headline-lg text-on-background">{{ meta.title }}</h1>
          <p class="font-body-md text-body-md text-on-surface-variant mt-1">{{ meta.subtitle }}</p>
        </div>
        <button
          class="bg-primary text-on-primary px-4 py-2 rounded-lg font-label-lg text-label-lg hover:opacity-90 transition-opacity flex items-center gap-2"
        >
          {{ t('新建推广') }}
        </button>
      </div>

      <!-- Bento 网格 -->
      <div class="grid grid-cols-12 gap-6">
        <!-- 转化漏斗（跨 8 列） -->
        <div
          class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <h2
            class="font-headline-md text-headline-md text-on-surface flex items-center gap-2 mb-6"
          >
            {{ t('转化漏斗（近 30 天）') }}
          </h2>
          <div class="flex justify-between items-center px-4 relative">
            <template v-for="(s, i) in funnel" :key="s.label">
              <div class="flex flex-col items-center z-10">
                <div
                  class="w-16 h-16 rounded-full flex items-center justify-center mb-2"
                  :class="s.circle"
                ></div>
                <span class="font-label-lg text-label-lg text-on-surface">{{ s.label }}</span>
                <span class="font-num-md text-num-md font-bold mt-1" :class="s.valueClass">{{
                  s.value
                }}</span>
                <span v-if="s.sub" class="text-xs text-on-surface-variant">{{ s.sub }}</span>
              </div>
              <div
                v-if="i < funnel.length - 1"
                class="flex-1 h-[2px] bg-outline-variant mx-2 mt-[-30px] z-0"
              ></div>
            </template>
          </div>
        </div>

        <!-- POI 状态 & 私域流量（跨 4 列） -->
        <div class="col-span-12 lg:col-span-4 flex flex-col gap-6">
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex items-center gap-4"
          >
            <div
              class="w-12 h-12 rounded-full bg-[#1A1A1A] flex items-center justify-center shrink-0"
            ></div>
            <div class="flex-1">
              <h3 class="font-label-lg text-label-lg font-bold text-on-surface">
                {{ poi.account }}
              </h3>
              <div class="flex items-center gap-2 mt-1">
                <span class="w-2 h-2 rounded-full bg-green-500"></span>
                <span class="text-sm text-on-surface-variant">{{ poi.status }}</span>
              </div>
            </div>
            <button class="text-primary font-label-lg text-label-lg hover:underline">
              {{ t('管理') }}
            </button>
          </div>
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col items-center text-center"
          >
            <h3 class="font-label-lg text-label-lg font-bold text-on-surface mb-2">
              {{ t('私域流量捕获') }}
            </h3>
            <p class="text-sm text-on-surface-variant mb-4">
              企业微信二维码用于现场入住。自动给客人打"{{ poi.tag }}"标签。
            </p>
            <div
              class="w-32 h-32 bg-surface-container border border-outline-variant rounded-lg flex items-center justify-center mb-4 overflow-hidden"
            >
              <img
                class="w-full h-full object-cover opacity-80 mix-blend-multiply"
                alt="企微二维码"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuCqHFWvMFDlyjih26ScSVCelBwAVloBqPbVH7UhPcIg7jusB4W07rGXNzSkGwr1fEMkjsPIkoffjByLPsg-UqVpMqoRYjYOvaGFr7F-UhFvzILAYR_D8iRQM4F3EbawyFskSfYZCN9FQslS-IPBrjIWLaAxbZtsZSlXhvxgdSSaUaOIKsWVDddyTI8UbCHjlM6pShZEBF2S_rT5O9gyoQxg72AExXgc_XZGsL99k6RpHZEoKZkWjz0"
              />
            </div>
            <button
              class="w-full bg-surface-container-low border border-outline-variant text-on-surface py-2 rounded-lg font-label-lg text-label-lg hover:bg-surface-variant transition-colors flex items-center justify-center gap-2"
            >
              {{ t('下载素材') }}
            </button>
          </div>
        </div>

        <!-- 团购券（跨 7 列） -->
        <div
          class="col-span-12 lg:col-span-7 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <div class="flex items-center justify-between mb-6">
            <h2 class="font-headline-md text-headline-md text-on-surface">{{ t('团购券') }}</h2>
            <button
              class="text-primary font-label-lg text-label-lg hover:bg-primary-fixed p-2 rounded-md transition-colors"
            >
              {{ t('查看全部') }}
            </button>
          </div>
          <div class="space-y-4">
            <div
              v-for="c in coupons"
              :key="c.name"
              class="border border-outline-variant rounded-lg p-4 flex items-center justify-between hover:bg-surface-container-low transition-colors"
            >
              <div class="flex items-center gap-4">
                <div
                  class="w-12 h-12 rounded-md flex items-center justify-center font-num-md text-num-md font-bold"
                  :class="c.priceClass"
                >
                  {{ c.price }}
                </div>
                <div>
                  <h4 class="font-label-lg text-label-lg text-on-surface">{{ c.name }}</h4>
                  <p class="text-sm text-on-surface-variant mt-1">{{ c.expire }}</p>
                </div>
              </div>
              <div class="text-right">
                <div class="font-num-md text-num-md font-bold text-on-surface">{{ c.sold }}</div>
                <div
                  class="text-sm mt-1 flex items-center justify-end gap-1"
                  :class="c.statusClass"
                >
                  {{ c.status }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- AI 脚本生成器（跨 5 列） -->
        <div
          class="col-span-12 lg:col-span-5 bg-tertiary-fixed/10 rounded-xl border border-tertiary-fixed p-6 shadow-sm relative overflow-hidden"
        >
          <div class="absolute top-0 left-0 w-1 h-full bg-tertiary"></div>
          <div class="flex items-center gap-2 mb-4">
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('AI 脚本生成器') }}
            </h2>
          </div>
          <p class="text-sm text-on-surface-variant mb-6">
            {{ t('基于当前房量与时下标签，为抖音生成高转化视频脚本与钩子。') }}
          </p>
          <div
            class="space-y-4 relative before:absolute before:inset-0 before:ml-[11px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-tertiary/20 before:to-transparent"
          >
            <div
              v-for="(s, i) in scripts"
              :key="s.title"
              class="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active"
            >
              <div
                class="flex items-center justify-center w-6 h-6 rounded-full border-2 border-white shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10"
                :class="s.dot"
              ></div>
              <div
                class="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-3 rounded-lg border shadow-sm text-sm"
                :class="s.box"
              >
                <div class="font-label-lg font-bold text-on-surface mb-1">{{ s.title }}</div>
                <span class="text-on-surface-variant">{{ s.desc }}</span>
              </div>
            </div>
          </div>
          <button
            class="w-full mt-6 bg-tertiary text-on-tertiary py-2 rounded-lg font-label-lg text-label-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
          >
            {{ t('生成新脚本') }}
          </button>
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
</style>
