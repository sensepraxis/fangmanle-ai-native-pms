<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 库存分配 Inventory Allocation（收益管理 C1）：物理房量 / 可售 / 超售风险 + 渠道预留矩阵
// 数据：api.dashboard 取总房量与占用；api.listChannels 取渠道预留消耗
import { ref, onMounted, computed } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'

const dash = ref<any>({})
const channels = ref<any[]>([])
onMounted(async () => {
  dash.value = await api.dashboard(hotelStore.hotelId)
  channels.value = await api.listChannels()
})
const totalRooms = computed(() => dash.value.total_rooms || 120)
const occupied = computed(() => dash.value.occupied || 68)
const available = computed(() => Math.max(0, totalRooms.value - occupied.value - 7))
</script>

<template>
  <div class="page">
    <div class="flex justify-between items-end">
      <div>
        <h1 class="font-display-lg text-display-lg text-on-surface">
          {{ t('库存分配') }}
          <span class="font-headline-md text-headline-md text-on-surface-variant font-normal ml-2"
            >Inventory Allocation</span
          >
        </h1>
        <p class="font-body-md text-body-md text-on-surface-variant mt-1">
          {{ t('管理物理房量，预留渠道库存，防范超售风险。') }}
        </p>
      </div>
      <div class="flex items-center gap-3">
        <div class="flex bg-surface-container-lowest border border-outline-variant rounded-lg p-1">
          <button
            class="px-3 py-1.5 font-label-lg text-label-lg text-primary bg-primary-container/10 rounded-md"
          >
            {{ t('14天视图') }}
          </button>
          <button
            class="px-3 py-1.5 font-label-lg text-label-lg text-on-surface-variant hover:bg-surface-container-low rounded-md transition-colors"
          >
            {{ t('30天视图') }}
          </button>
        </div>
        <button
          class="bg-primary text-on-primary font-label-lg text-label-lg px-4 py-2 rounded-lg hover:bg-surface-tint shadow-sm transition-all flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-[18px]">save</span>{{ t('保存分配') }}
        </button>
      </div>
    </div>

    <!-- 顶部指标（绑定 dashboard） -->
    <div class="grid grid-cols-12 gap-gutter mt-6">
      <div
        class="col-span-3 bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col justify-between"
      >
        <div class="flex justify-between items-start">
          <h3 class="font-label-lg text-label-lg text-on-surface-variant">
            {{ t('总物理房量 (今日)') }}
          </h3>
          <span class="material-symbols-outlined text-outline">domain</span>
        </div>
        <div class="mt-4 flex items-baseline gap-2">
          <span class="font-num-xl text-display-lg font-bold text-on-surface"
            >{{ totalRooms }}}</span
          ><span class="font-body-md text-body-md text-on-surface-variant">{{ t('间') }}</span>
        </div>
        <div class="w-full bg-surface-variant h-1.5 rounded-full mt-4 overflow-hidden">
          <div class="bg-primary h-full w-full"></div>
        </div>
      </div>
      <div
        class="col-span-3 bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex flex-col justify-between"
      >
        <div class="flex justify-between items-start">
          <h3 class="font-label-lg text-label-lg text-on-surface-variant">
            {{ t('整体可售 (今日)') }}
          </h3>
          <span class="material-symbols-outlined text-primary">check_circle</span>
        </div>
        <div class="mt-4 flex items-baseline gap-2">
          <span class="font-num-xl text-display-lg font-bold text-primary">{{ available }}}</span
          ><span class="font-body-md text-body-md text-on-surface-variant">{{ t('间') }}</span>
        </div>
        <div class="flex text-xs text-on-surface-variant mt-2 gap-3 font-num-md">
          <span>{{ t('已售:') }} {{ occupied }}}</span><span>{{ t('维修/锁房: 7') }}</span>
        </div>
      </div>
      <div
        class="col-span-6 bg-[#fff8e1] border border-[#ffc107] p-5 rounded-xl shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex items-start gap-4 relative overflow-hidden"
      >
        <div class="absolute right-0 top-0 opacity-10 pointer-events-none text-[#ffc107]">
          <span class="material-symbols-outlined text-[120px] -mt-6 -mr-6">warning</span>
        </div>
        <div class="p-3 bg-white rounded-lg shadow-sm border border-[#ffeb3b]">
          <span class="material-symbols-outlined text-[#f57c00]">analytics</span>
        </div>
        <div class="flex-1">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-headline-md text-[#d84315] flex items-center gap-2">
              <span class="material-symbols-outlined text-[20px]">arrow_back_ios_new</span>
              {{ t('AI 超售风险提示 (Review Suggested)') }}
            </h3>
            <span
              class="font-label-lg text-label-lg bg-[#ffe0b2] text-[#e65100] px-2 py-1 rounded-md"
              >{{ t('中度风险') }}</span
            >
          </div>
          <p class="font-body-md text-body-md text-[#5d4037] mt-1">
            {{ t('未来 7 天内，') }} <strong>{{ t('豪华大床房') }}</strong
            >{{ t('在周五、周六出现超售阈值预警。携程预留配额过高，建议释放 20% 库存至公共池。') }}
          </p>
          <div class="mt-3 flex gap-2">
            <button
              class="bg-[#f57c00] text-white font-label-lg px-3 py-1.5 rounded hover:bg-[#ef6c00] transition-colors"
            >
              {{ t('自动平衡库存') }}
            </button>
            <button
              class="bg-white border border-[#ffcc80] text-[#ef6c00] font-label-lg px-3 py-1.5 rounded hover:bg-[#fff3e0] transition-colors"
            >
              {{ t('查看详情') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 主矩阵（房型 × 日期，忠实栅格） -->
    <div
      class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden flex-1 flex flex-col mt-6"
    >
      <div
        class="grid grid-cols-[200px_repeat(7,_minmax(0,_1fr))] border-b border-outline-variant bg-surface-bright"
      >
        <div
          class="p-4 font-headline-md text-headline-md text-on-surface flex items-center justify-between border-r border-outline-variant"
        >
          {{ t('房型') }}
          <span class="material-symbols-outlined text-outline text-[18px]">filter_list</span>
        </div>
        <div class="p-3 text-center border-r border-outline-variant">
          <div class="font-label-lg text-on-surface-variant">{{ t('周二') }}</div>
          <div class="font-num-md text-on-surface font-bold">10/24</div>
        </div>
        <div class="p-3 text-center border-r border-outline-variant">
          <div class="font-label-lg text-on-surface-variant">{{ t('周三') }}</div>
          <div class="font-num-md text-on-surface font-bold">10/25</div>
        </div>
        <div class="p-3 text-center border-r border-outline-variant bg-[#fff8e1]/30">
          <div class="font-label-lg text-[#f57c00]">{{ t('周四') }}</div>
          <div class="font-num-md text-on-surface font-bold">10/26</div>
        </div>
        <div class="p-3 text-center border-r border-outline-variant bg-[#fff8e1]/50">
          <div class="font-label-lg text-[#f57c00]">{{ t('周五') }}</div>
          <div class="font-num-md text-on-surface font-bold flex items-center justify-center gap-1">
            10/27 <span class="w-1.5 h-1.5 rounded-full bg-error"></span>
          </div>
        </div>
        <div class="p-3 text-center border-r border-outline-variant bg-[#fff8e1]/50">
          <div class="font-label-lg text-[#f57c00]">{{ t('周六') }}</div>
          <div class="font-num-md text-on-surface font-bold flex items-center justify-center gap-1">
            10/28 <span class="w-1.5 h-1.5 rounded-full bg-error"></span>
          </div>
        </div>
        <div class="p-3 text-center border-r border-outline-variant">
          <div class="font-label-lg text-on-surface-variant">{{ t('周日') }}</div>
          <div class="font-num-md text-on-surface font-bold">10/29</div>
        </div>
        <div class="p-3 text-center">
          <div class="font-label-lg text-on-surface-variant">{{ t('周一') }}</div>
          <div class="font-num-md text-on-surface font-bold">10/30</div>
        </div>
      </div>
      <div class="overflow-y-auto flex-1">
        <div
          class="grid grid-cols-[200px_repeat(7,_minmax(0,_1fr))] border-b border-outline-variant hover:bg-surface-container-low transition-colors group"
        >
          <div class="p-4 border-r border-outline-variant flex flex-col justify-center">
            <span class="font-headline-md text-body-md font-semibold text-on-surface">{{
              t('标准大床房')
            }}</span
            ><span class="font-num-md text-xs text-on-surface-variant mt-1">{{
              t('物理: 30间')
            }}</span>
          </div>
          <div
            class="p-2 border-r border-outline-variant flex flex-col justify-center cursor-pointer hover:bg-surface-variant/50"
          >
            <div class="flex justify-between items-end mb-1">
              <span class="font-label-lg text-xs text-on-surface-variant">{{ t('可售') }}</span
              ><span class="font-num-md font-bold text-primary">12</span>
            </div>
            <div class="w-full h-1.5 bg-surface-variant rounded-full flex overflow-hidden">
              <div class="bg-secondary-fixed-dim h-full w-[50%]"></div>
              <div class="bg-[#9e9e9e] h-full w-[10%]"></div>
              <div class="bg-primary-container h-full w-[40%]"></div>
            </div>
          </div>
          <div
            class="p-2 border-r border-outline-variant flex flex-col justify-center cursor-pointer hover:bg-surface-variant/50"
          >
            <div class="flex justify-between items-end mb-1">
              <span class="font-label-lg text-xs text-on-surface-variant">{{ t('可售') }}</span
              ><span class="font-num-md font-bold text-primary">8</span>
            </div>
            <div class="w-full h-1.5 bg-surface-variant rounded-full flex overflow-hidden">
              <div class="bg-secondary-fixed-dim h-full w-[65%]"></div>
              <div class="bg-[#9e9e9e] h-full w-[8%]"></div>
              <div class="bg-primary-container h-full w-[27%]"></div>
            </div>
          </div>
          <div
            class="p-2 border-r border-outline-variant flex flex-col justify-center cursor-pointer hover:bg-surface-variant/50"
          >
            <div class="flex justify-between items-end mb-1">
              <span class="font-label-lg text-xs text-on-surface-variant">{{ t('可售') }}</span
              ><span class="font-num-md font-bold text-primary">2</span>
            </div>
            <div class="w-full h-1.5 bg-surface-variant rounded-full flex overflow-hidden">
              <div class="bg-secondary-fixed-dim h-full w-[85%]"></div>
              <div class="bg-[#9e9e9e] h-full w-[8%]"></div>
              <div class="bg-primary-container h-full w-[7%]"></div>
            </div>
          </div>
          <div
            class="p-2 border-r border-outline-variant flex flex-col justify-center cursor-pointer bg-error-container/20 hover:bg-error-container/40 relative"
          >
            <div class="absolute inset-0 border border-error pointer-events-none rounded"></div>
            <div class="flex justify-between items-end mb-1">
              <span class="font-label-lg text-xs text-error font-semibold">{{ t('超售') }}</span
              ><span class="font-num-md font-bold text-error">-3</span>
            </div>
            <div class="w-full h-1.5 bg-surface-variant rounded-full flex overflow-hidden relative">
              <div class="bg-error h-full w-full"></div>
              <div class="absolute top-0 bottom-0 right-[10%] w-0.5 bg-white"></div>
            </div>
          </div>
          <div
            class="p-2 border-r border-outline-variant flex flex-col justify-center cursor-pointer bg-error-container/20 hover:bg-error-container/40 relative"
          >
            <div class="absolute inset-0 border border-[#ff9800] pointer-events-none rounded"></div>
            <div class="flex justify-between items-end mb-1">
              <span class="font-label-lg text-xs text-[#e65100] font-semibold">{{ t('紧张') }}</span
              ><span class="font-num-md font-bold text-[#e65100]">0</span>
            </div>
            <div class="w-full h-1.5 bg-surface-variant rounded-full flex overflow-hidden">
              <div class="bg-secondary-fixed-dim h-full w-[95%]"></div>
              <div class="bg-[#9e9e9e] h-full w-[5%]"></div>
            </div>
          </div>
          <div
            class="p-2 border-r border-outline-variant flex flex-col justify-center cursor-pointer hover:bg-surface-variant/50"
          >
            <div class="flex justify-between items-end mb-1">
              <span class="font-label-lg text-xs text-on-surface-variant">{{ t('可售') }}</span
              ><span class="font-num-md font-bold text-primary">15</span>
            </div>
            <div class="w-full h-1.5 bg-surface-variant rounded-full flex overflow-hidden">
              <div class="bg-secondary-fixed-dim h-full w-[40%]"></div>
              <div class="bg-[#9e9e9e] h-full w-[10%]"></div>
              <div class="bg-primary-container h-full w-[50%]"></div>
            </div>
          </div>
          <div class="p-2 flex flex-col justify-center cursor-pointer hover:bg-surface-variant/50">
            <div class="flex justify-between items-end mb-1">
              <span class="font-label-lg text-xs text-on-surface-variant">{{ t('可售') }}</span
              ><span class="font-num-md font-bold text-primary">22</span>
            </div>
            <div class="w-full h-1.5 bg-surface-variant rounded-full flex overflow-hidden">
              <div class="bg-secondary-fixed-dim h-full w-[20%]"></div>
              <div class="bg-[#9e9e9e] h-full w-[5%]"></div>
              <div class="bg-primary-container h-full w-[75%]"></div>
            </div>
          </div>
        </div>
        <div
          class="grid grid-cols-[200px_repeat(7,_minmax(0,_1fr))] border-b border-outline-variant hover:bg-surface-container-low transition-colors group"
        >
          <div class="p-4 border-r border-outline-variant flex flex-col justify-center">
            <span class="font-headline-md text-body-md font-semibold text-on-surface">{{
              t('豪华大床房')
            }}</span
            ><span class="font-num-md text-xs text-on-surface-variant mt-1">{{
              t('物理: 20间')
            }}</span>
          </div>
          <div
            class="p-2 border-r border-outline-variant flex flex-col justify-center cursor-pointer bg-primary-container/10 border-l-[3px] border-l-primary relative"
          >
            <div class="flex justify-between items-end mb-1">
              <span class="font-label-lg text-xs text-on-surface">{{ t('可售') }}</span
              ><span class="font-num-md font-bold text-primary">5</span>
            </div>
            <div class="w-full h-1.5 bg-surface-variant rounded-full flex overflow-hidden">
              <div class="bg-secondary-fixed-dim h-full w-[60%]"></div>
              <div class="bg-[#9e9e9e] h-full w-[15%]"></div>
              <div class="bg-primary h-full w-[25%] shadow-[0_0_8px_#1a73e8]"></div>
            </div>
          </div>
          <div
            class="p-2 border-r border-outline-variant flex flex-col justify-center cursor-pointer hover:bg-surface-variant/50"
          >
            <div class="flex justify-between items-end mb-1">
              <span class="font-label-lg text-xs text-on-surface-variant">{{ t('可售') }}</span
              ><span class="font-num-md font-bold text-primary">8</span>
            </div>
            <div class="w-full h-1.5 bg-surface-variant rounded-full flex overflow-hidden">
              <div class="bg-secondary-fixed-dim h-full w-[50%]"></div>
              <div class="bg-[#9e9e9e] h-full w-[10%]"></div>
              <div class="bg-primary-container h-full w-[40%]"></div>
            </div>
          </div>
          <div
            class="col-span-5 flex items-center justify-center border-l border-outline-variant text-on-surface-variant font-label-lg text-xs opacity-50 bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,rgba(0,0,0,0.02)_10px,rgba(0,0,0,0.02)_20px)]"
          >
            {{ t('数据已省略...') }}
          </div>
        </div>
      </div>
      <div
        class="p-3 bg-surface-container-low flex items-center justify-end gap-6 border-t border-outline-variant mt-auto"
      >
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-sm bg-secondary-fixed-dim"></div>
          <span class="font-label-lg text-xs text-on-surface-variant">{{ t('已售 (物理)') }}</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-sm bg-[#9e9e9e]"></div>
          <span class="font-label-lg text-xs text-on-surface-variant">{{ t('维修/锁房') }}</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-sm bg-primary-container"></div>
          <span class="font-label-lg text-xs text-on-surface-variant">{{ t('可售 (物理)') }}</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-sm bg-error"></div>
          <span class="font-label-lg text-xs text-on-surface-variant">{{ t('超售') }}</span>
        </div>
      </div>
    </div>

    <!-- 选中单元格渠道分配详情（v-for 绑定 listChannels） -->
    <div
      class="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-lg p-5 mt-2"
    >
      <div class="flex justify-between items-center mb-4">
        <h2 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
          {{ t('豪华大床房') }}
          <span class="text-on-surface-variant text-body-md font-normal ml-2">{{
            t('10月24日 分配详情')
          }}</span>
        </h2>
        <button class="text-on-surface-variant hover:text-on-surface">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
      <div class="grid grid-cols-3 gap-8">
        <div class="col-span-1 border-r border-outline-variant pr-8">
          <div class="space-y-3">
            <div class="flex justify-between py-1 border-b border-surface-variant">
              <span class="font-label-lg text-on-surface-variant">{{ t('物理房量') }}</span
              ><span class="font-num-md text-on-surface font-semibold">20</span>
            </div>
            <div class="flex justify-between py-1 border-b border-surface-variant">
              <span class="font-label-lg text-on-surface-variant">{{ t('维修/保留') }}}</span
              ><span class="font-num-md text-[#f57c00]">3</span>
            </div>
            <div class="flex justify-between py-1 border-b border-surface-variant">
              <span class="font-label-lg text-on-surface-variant">{{ t('已售出') }}}</span
              ><span class="font-num-md text-on-surface">12</span>
            </div>
            <div class="flex justify-between py-2 mt-2 bg-primary-container/10 rounded px-2">
              <span class="font-label-lg font-bold text-primary">{{ t('当前可售') }}}</span
              ><span class="font-num-md font-bold text-primary text-lg">5</span>
            </div>
          </div>
        </div>
        <div class="col-span-2 pl-4">
          <h3 class="font-label-lg text-label-lg text-on-surface-variant mb-4">
            {{ t('渠道/场景预留与消耗') }}
          </h3>
          <div class="space-y-4">
            <div v-for="(c, i) in channels" :key="c.id">
              <div class="flex justify-between items-center mb-1">
                <span class="font-label-lg text-sm flex items-center gap-1"
                  ><span
                    class="w-2 h-2 rounded-full"
                    :class="
                      i === 0 ? 'bg-[#ffc107]' : i === 1 ? 'bg-[#1e88e5]' : 'bg-primary-container'
                    "
                  ></span>
                  {{ c.name || t('渠道') }}</span
                >
                <span class="font-num-md text-xs text-on-surface-variant"
                  >{{ t('佣金率') }} {{ ((c.commission_rate || 0) * 100).toFixed(1) }}%</span
                >
              </div>
              <div class="w-full h-2 bg-surface-variant rounded-full overflow-hidden flex">
                <div
                  class="h-full"
                  :class="
                    i === 0 ? 'bg-[#ffc107]' : i === 1 ? 'bg-[#1e88e5]' : 'bg-primary-container'
                  "
                  :style="{ width: 60 + i * 10 + '%' }"
                ></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between items-center mb-1">
                <span class="font-label-lg text-sm flex items-center gap-1"
                  ><span class="w-2 h-2 rounded-full bg-primary-container"></span>
                  {{ t('自有渠道 (公共池)') }}</span
                ><span class="font-num-md text-xs text-on-surface-variant">{{
                  t('已用: 2 / 剩余: 2')
                }}</span>
              </div>
              <div class="w-full h-2 bg-surface-variant rounded-full overflow-hidden flex">
                <div class="bg-primary-container h-full w-[50%]"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
