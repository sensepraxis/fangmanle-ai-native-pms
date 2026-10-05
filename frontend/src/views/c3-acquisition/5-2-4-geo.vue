<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'

// 酒店上下文（固定为 1 号店）
const hotelId = 1
// seed 保留原型示例卡片，保证 1:1 视觉；onMounted 后由真实接口数据覆盖
const seed: any[] = [
  {
    id: 0,
    cls: 'w-full bg-surface-container-highest rounded-full h-2',
    raw: '<div class="bg-primary h-2 rounded-full" style="width: 87%"></div>',
  },
  {
    id: 1,
    cls: 'w-full bg-surface-container-highest rounded-full h-1.5',
    raw: '<div class="bg-outline-variant h-1.5 rounded-full" style="width: 92%"></div>',
  },
  {
    id: 2,
    cls: 'w-full bg-surface-container-highest rounded-full h-1.5',
    raw: '<div class="bg-outline-variant h-1.5 rounded-full" style="width: 74%"></div>',
  },
]
const rows = ref<any[]>(seed)
onMounted(async () => {
  try {
    const r = await api.demo('geo')
    // 仅当接口返回与原型同构（含 raw 字段）时才替换，否则保留原型示例
    if (Array.isArray(r) && r.length && (r[0] as any)?.raw) rows.value = r
  } catch (e) {
    /* 数据兜底：保留原型示例 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="geo" /></div>
    <div class="max-w-[1440px] mx-auto space-y-gutter">
      <!-- Bento Grid Layout -->
      <div class="grid grid-cols-12 gap-gutter h-full min-h-[800px]">
        <!-- Center: GEO Traffic Radar (Map View) -->
        <div
          class="col-span-12 lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant overflow-hidden flex flex-col shadow-sm relative"
        >
          <div
            class="p-4 border-b border-surface-container-highest flex justify-between items-center bg-surface-container-lowest z-10 relative"
          >
            <div>
              <h2 class="font-headline-md text-headline-md text-on-surface">
                {{ t('地理流量雷达') }}
              </h2>
              <p class="font-label-lg text-label-lg text-on-surface-variant">
                {{ t('本地搜索密度与竞对状态的实时热力图。') }}
              </p>
            </div>
            <div class="flex gap-2">
              <button
                class="px-3 py-1.5 text-sm bg-surface-container border border-outline-variant rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors"
              >
                {{ t('筛选条件') }}</button
              ><button
                class="px-3 py-1.5 text-sm bg-primary text-on-primary rounded-lg shadow-sm hover:bg-on-primary-fixed-variant transition-colors flex items-center gap-1"
              >
                {{ t('刷新') }}
              </button>
            </div>
          </div>
          <div class="flex-grow relative w-full h-full bg-surface-container">
            <!-- Map Image Placeholder -->
            <div
              class="absolute inset-0 w-full h-full bg-cover bg-center"
              data-location="Shanghai"
              style="
                background-image: url('https://lh3.googleusercontent.com/aida-public/AB6AXuBRhMtJl4Uoc92rl4jC8W34lQtjaR4twumMgyAMy4pFVE6HbzGRXK9PdJpmqV5wtXV1J-h7Le7Hnc4ginoUO_-slgrBf5S3-WPmE_NF9gAwUOMC3pxuntN7ma1J1fbVmMJlhLBhMW7ScusQ5jli2io5CDQ8UwVRGwqyHh_OL3rzQ4aPMK_BsZ3_kV1Ylcj0do9pjc2y9fddfK6ocxv5KcJEzncLFMsM0VBQ-M1NSXF-FT4eY9tp4Do');
              "
            ></div>
            <!-- Simulated Map Overlays -->
            <div
              class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 flex items-center flex-col"
            >
              <div
                class="w-4 h-4 bg-primary rounded-full border-2 border-white shadow-[0_0_10px_rgba(0,91,191,0.8)] z-20"
              ></div>
              <div
                class="mt-1 bg-surface-container-lowest px-2 py-1 rounded text-xs font-bold text-primary shadow-md border border-outline-variant whitespace-nowrap z-20"
              >
                {{ t('我的酒店') }}
              </div>
            </div>
            <!-- Heat Zone 1 -->
            <div
              class="absolute top-1/4 left-1/4 w-32 h-32 map-heat-overlay rounded-full mix-blend-multiply flex items-center justify-center animate-pulse"
            ></div>
            <div class="absolute top-[28%] left-[28%] z-20">
              <div
                class="bg-surface-container-lowest px-2 py-1 rounded text-[10px] font-bold text-[#d97706] shadow-md border border-[#fcd34d] whitespace-nowrap flex items-center gap-1"
              >
                {{ t('高流量') }}
              </div>
            </div>
            <!-- Competitor Marker -->
            <div class="absolute top-2/3 right-1/3 flex items-center flex-col z-20">
              <div class="w-3 h-3 bg-[#ef4444] rounded-full border-2 border-white shadow-sm"></div>
              <div
                class="mt-1 bg-surface-container-lowest px-1.5 py-0.5 rounded text-[10px] font-medium text-on-surface-variant shadow-md border border-outline-variant whitespace-nowrap"
              >
                {{ t('竞品 A（已售罄）') }}
              </div>
            </div>
          </div>
        </div>
        <!-- Right Column: AI Alerts & Competitors -->
        <div class="col-span-12 lg:col-span-4 flex flex-col gap-gutter">
          <!-- AI Opportunity Alerts -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm flex flex-col flex-grow"
          >
            <div class="p-4 border-b border-surface-container-highest flex items-center gap-2">
              <h2 class="font-headline-md text-headline-md text-on-surface">
                {{ t('AI 机会告警') }}
              </h2>
            </div>
            <div class="p-4 space-y-4 overflow-y-auto">
              <!-- Alert 1 (R1 - Low Risk) -->
              <div
                class="bg-surface-bright border border-[#fde047] rounded-lg p-3 ai-border-tinge shadow-sm"
              >
                <div class="flex items-start justify-between">
                  <div class="flex gap-2">
                    <div>
                      <h4 class="font-label-lg text-label-lg font-bold text-on-surface">
                        {{ t('火车站客流激增') }}
                      </h4>
                      <p class="text-xs text-on-surface-variant mt-0.5">
                        {{ t('检测到 2km 内高搜索流量。') }}
                      </p>
                    </div>
                  </div>
                </div>
                <div
                  class="mt-3 flex items-center justify-between bg-surface-container-low p-2 rounded border border-outline-variant"
                >
                  <span class="text-xs font-medium text-on-surface">{{
                    t('AI 建议：出价 +15%')
                  }}</span
                  ><button
                    class="text-xs bg-primary text-on-primary px-3 py-1 rounded hover:bg-on-primary-fixed-variant transition-colors"
                  >
                    {{ t('应用') }}
                  </button>
                </div>
              </div>
              <!-- Alert 2 (R2 - Medium Risk) -->
              <div class="bg-[#fff7ed] border border-[#fdba74] rounded-lg p-3 shadow-sm">
                <div class="flex items-start justify-between">
                  <div class="flex gap-2">
                    <div>
                      <h4 class="font-label-lg text-label-lg font-bold text-on-surface">
                        {{ t('竞品 A 售罄') }}
                      </h4>
                      <p class="text-xs text-on-surface-variant mt-0.5">
                        {{ t('向 500m 半径内用户推送 LBS 广告。') }}
                      </p>
                    </div>
                  </div>
                </div>
                <div
                  class="mt-3 flex items-center justify-between bg-surface-container-lowest p-2 rounded border border-[#fdba74]"
                >
                  <label
                    class="flex items-center gap-2 text-xs font-medium text-on-surface cursor-pointer"
                    ><input
                      class="rounded text-primary focus:ring-primary border-outline-variant"
                      type="checkbox"
                    />{{ t('确认广告推送') }}</label
                  ><button
                    class="text-xs bg-[#ea580c] text-white px-3 py-1 rounded hover:bg-[#c2410c] transition-colors"
                  >
                    {{ t('执行') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
          <!-- Competitor Benchmarking -->
          <div
            class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-4"
          >
            <h2 class="font-headline-md text-headline-md text-on-surface mb-4">
              {{ t('曝光基准') }}
            </h2>
            <div class="space-y-3">
              <template v-for="(item, i) in rows" :key="i"
                ><div :class="item.cls" v-html="item.raw"></div
              ></template>
            </div>
          </div>
        </div>
        <!-- Bottom Full Width: LBS Campaign Management -->
        <div
          class="col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col min-h-[250px]"
        >
          <div
            class="p-4 border-b border-surface-container-highest flex justify-between items-center bg-surface-container-lowest"
          >
            <h2 class="font-headline-md text-headline-md text-on-surface">
              {{ t('LBS 进行中推广') }}
            </h2>
            <button
              class="text-sm text-primary font-medium hover:underline flex items-center gap-1"
            >
              {{ t('查看全部') }}
            </button>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm text-on-surface">
              <thead
                class="text-xs text-on-surface-variant bg-surface-container-low border-b border-outline-variant uppercase"
              >
                <tr>
                  <th class="px-4 py-3 font-medium" scope="col">{{ t('平台') }}</th>
                  <th class="px-4 py-3 font-medium" scope="col">{{ t('推广目标') }}</th>
                  <th class="px-4 py-3 font-medium text-right" scope="col">{{ t('曝光量') }}</th>
                  <th class="px-4 py-3 font-medium text-right" scope="col">{{ t('门店转化') }}</th>
                  <th class="px-4 py-3 font-medium text-right" scope="col">{{ t('预计营收') }}</th>
                  <th class="px-4 py-3 font-medium text-center" scope="col">{{ t('状态') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-surface-container-highest">
                <tr class="hover:bg-surface-bright transition-colors">
                  <td class="px-4 py-3 font-medium flex items-center gap-2">
                    <div
                      class="w-6 h-6 bg-surface-container rounded flex items-center justify-center text-xs border border-outline-variant"
                    >
                      A
                    </div>
                    {{ t('高德（Amap）') }}
                  </td>
                  <td class="px-4 py-3">
                    {{ t('火车站')
                    }}<span class="text-xs text-on-surface-variant ml-1">{{ t('2km 半径') }}</span>
                  </td>
                  <td class="px-4 py-3 text-right font-num-md text-num-md">12,450</td>
                  <td class="px-4 py-3 text-right font-num-md text-num-md text-[#16a34a]">4.2%</td>
                  <td class="px-4 py-3 text-right font-num-md text-num-md">¥ 3,200</td>
                  <td class="px-4 py-3 text-center">
                    <span
                      class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[#dcfce7] text-[#166534] border border-[#bbf7d0]"
                      >{{ t('启用') }}</span
                    >
                  </td>
                </tr>
                <tr class="hover:bg-surface-bright transition-colors">
                  <td class="px-4 py-3 font-medium flex items-center gap-2">
                    <div
                      class="w-6 h-6 bg-surface-container rounded flex items-center justify-center text-xs border border-outline-variant"
                    >
                      M
                    </div>
                    {{ t('美团 (美团)') }}
                  </td>
                  <td class="px-4 py-3">
                    {{ t('周末游')
                    }}<span class="text-xs text-on-surface-variant ml-1">{{ t('全城') }}</span>
                  </td>
                  <td class="px-4 py-3 text-right font-num-md text-num-md">8,920</td>
                  <td class="px-4 py-3 text-right font-num-md text-num-md text-[#16a34a]">3.8%</td>
                  <td class="px-4 py-3 text-right font-num-md text-num-md">¥ 2,850</td>
                  <td class="px-4 py-3 text-center">
                    <span
                      class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[#dcfce7] text-[#166534] border border-[#bbf7d0]"
                      >{{ t('启用') }}</span
                    >
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
/* 原型自定义工具类（v-html 内联卡片的根节点由 Vue 渲染，可命中） */
.ai-glow {
  box-shadow: 0 0 15px rgba(140, 51, 179, 0.15);
  border-left: 2px solid #8c33b3;
}
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
