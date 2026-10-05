<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 排期甘特图（C10 多形态 · MICE 场地排期）
// 甘特图（大宴会厅/莲花厅/董事会厅）与新建排期侧栏为原型静态结构；
// 底部「近期 MICE 排期」绑定 api.demo('mice') 渲染真实事件列表。
import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import { fmt } from '../../lib/ui'

const events = ref<any[]>([])
onMounted(async () => {
  events.value = await api.demo('mice')
})
function statusPill(s: string) {
  if (s === t('已确认')) return 'text-green-700 bg-green-50'
  if (s === t('洽谈中')) return 'text-primary bg-primary-fixed'
  if (s === t('待排期')) return 'text-on-surface-variant bg-surface-variant'
  return 'text-tertiary bg-tertiary-fixed'
}
</script>

<template>
  <div class="page">
    <div
      class="flex-1 overflow-hidden flex flex-col md:flex-row p-container-padding gap-gutter max-w-max-content-width mx-auto w-full"
    >
      <!-- 甘特图区 -->
      <div
        class="flex-1 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm flex flex-col overflow-hidden relative"
      >
        <!-- AI 分析摘要 -->
        <div
          class="bg-tertiary-fixed/30 border-b border-tertiary-fixed-dim p-3 flex items-start gap-3"
        >
          <div>
            <h4 class="font-label-lg text-label-lg text-on-tertiary-container font-semibold">
              {{ t('AI 分析摘要') }}
            </h4>
            <p class="font-body-md text-body-md text-on-surface-variant text-sm mt-0.5">
              {{
                t(
                  '下周预计会议室使用率较高，受区域科技峰会影响，建议提前预留贵宾通道及设备维护时间。',
                )
              }}
            </p>
          </div>
        </div>
        <!-- 日期导航 -->
        <div
          class="flex items-center justify-between p-4 border-b border-outline-variant bg-surface-bright"
        >
          <div class="flex items-center gap-4">
            <button
              class="text-on-surface-variant hover:bg-surface-container rounded-full p-1 transition-colors"
            ></button>
            <h2 class="font-headline-md text-headline-md font-semibold">
              {{ t('2023年10月25日, 星期三') }}
            </h2>
            <button
              class="text-on-surface-variant hover:bg-surface-container rounded-full p-1 transition-colors"
            ></button>
          </div>
          <div class="flex bg-surface-container-low rounded-lg p-1 border border-outline-variant">
            <button
              class="px-4 py-1.5 font-label-lg text-label-lg text-on-surface bg-surface-container-lowest shadow-sm rounded-md font-medium"
            >
              {{ t('日视图') }}
            </button>
            <button
              class="px-4 py-1.5 font-label-lg text-label-lg text-on-surface-variant hover:text-on-surface rounded-md"
            >
              {{ t('周视图') }}
            </button>
          </div>
        </div>
        <!-- 甘特容器 -->
        <div class="flex-1 overflow-auto relative bg-surface-container-lowest">
          <!-- 表头行 -->
          <div
            class="gantt-grid border-b border-outline-variant sticky top-0 bg-surface-bright z-10 text-on-surface-variant font-label-lg text-label-lg text-xs font-semibold uppercase tracking-wider"
          >
            <div
              class="p-3 border-r border-outline-variant bg-surface-bright z-20 sticky left-0 shadow-[2px_0_4px_rgba(0,0,0,0.02)]"
            >
              {{ t('会议室 / 时间') }}
            </div>
            <div class="p-3 border-r border-outline-variant text-center">08:00</div>
            <div class="p-3 border-r border-outline-variant text-center">09:00</div>
            <div class="p-3 border-r border-outline-variant text-center">10:00</div>
            <div class="p-3 border-r border-outline-variant text-center">11:00</div>
            <div class="p-3 border-r border-outline-variant text-center">12:00</div>
            <div class="p-3 border-r border-outline-variant text-center">13:00</div>
            <div class="p-3 border-r border-outline-variant text-center">14:00</div>
            <div class="p-3 border-r border-outline-variant text-center">15:00</div>
            <div class="p-3 border-r border-outline-variant text-center">16:00</div>
            <div class="p-3 border-r border-outline-variant text-center">17:00</div>
            <div class="p-3 border-r border-outline-variant text-center">18:00</div>
            <div class="p-3 text-center">19:00</div>
          </div>
          <!-- 会议室 1 · 大宴会厅 -->
          <div
            class="gantt-grid border-b border-outline-variant relative group hover:bg-surface-bright transition-colors min-h-[80px]"
          >
            <div
              class="p-3 border-r border-outline-variant sticky left-0 bg-surface-container-lowest group-hover:bg-surface-bright z-20 shadow-[2px_0_4px_rgba(0,0,0,0.02)] transition-colors flex flex-col justify-center"
            >
              <span class="font-body-lg text-body-lg font-semibold">{{ t('大宴会厅') }}</span>
              <span
                class="font-body-md text-body-md text-xs text-on-surface-variant flex items-center gap-1 mt-1"
                >{{ t('500人') }}</span
              >
            </div>
            <div class="border-r border-outline-variant/30 h-full col-start-2"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-3"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-4"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-5"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-6"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-7"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-8"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-9"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-10"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-11"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-12"></div>
            <div class="h-full col-start-13"></div>
            <div class="absolute top-2 bottom-2 left-[200px] right-0 flex pointer-events-none">
              <div
                class="absolute h-full bg-primary-container/20 border-l-4 border-primary rounded-r-md flex flex-col justify-center px-3 pointer-events-auto cursor-pointer hover:bg-primary-container/30 transition-colors"
                style="left: 8.3%; width: 25%"
              >
                <span
                  class="font-label-lg text-label-lg text-on-primary-container text-xs font-bold truncate"
                  >{{ t('年度战略会议 (企业)') }}</span
                >
                <span
                  class="font-body-md text-body-md text-[10px] text-on-surface-variant truncate"
                  >{{ t('09:00 - 12:00 · 科技创新有限...') }}</span
                >
              </div>
              <div
                class="absolute h-full bg-tertiary-fixed border-l-4 border-tertiary rounded-r-md flex flex-col justify-center px-3 pointer-events-auto cursor-pointer hover:bg-tertiary-fixed-dim transition-colors shadow-sm"
                style="left: 50%; width: 33.3%"
              >
                <span
                  class="font-label-lg text-label-lg text-on-tertiary-container text-xs font-bold truncate"
                  >{{ t('张李联姻 (婚礼)') }}</span
                >
                <span
                  class="font-body-md text-body-md text-[10px] text-on-surface-variant truncate"
                  >{{ t('14:00 - 18:00 · 需提前2小时布...') }}</span
                >
              </div>
            </div>
          </div>
          <!-- 会议室 2 · 莲花厅 -->
          <div
            class="gantt-grid border-b border-outline-variant relative group hover:bg-surface-bright transition-colors min-h-[80px]"
          >
            <div
              class="p-3 border-r border-outline-variant sticky left-0 bg-surface-container-lowest group-hover:bg-surface-bright z-20 shadow-[2px_0_4px_rgba(0,0,0,0.02)] transition-colors flex flex-col justify-center"
            >
              <span class="font-body-lg text-body-lg font-semibold">{{ t('莲花厅') }}</span>
              <span
                class="font-body-md text-body-md text-xs text-on-surface-variant flex items-center gap-1 mt-1"
                >{{ t('120人') }}</span
              >
            </div>
            <div class="border-r border-outline-variant/30 h-full col-start-2"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-3"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-4"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-5"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-6"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-7"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-8"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-9"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-10"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-11"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-12"></div>
            <div class="h-full col-start-13"></div>
            <div class="absolute top-2 bottom-2 left-[200px] right-0 flex pointer-events-none">
              <div
                class="absolute h-full bg-[#E6F4EA] border-l-4 border-[#137333] rounded-r-md flex flex-col justify-center px-3 pointer-events-auto cursor-pointer hover:bg-[#CEEAD6] transition-colors"
                style="left: 16.6%; width: 41.6%"
              >
                <span
                  class="font-label-lg text-label-lg text-[#0D652D] text-xs font-bold truncate"
                  >{{ t('设计思维工作坊 (培训)') }}</span
                >
                <span
                  class="font-body-md text-body-md text-[10px] text-on-surface-variant truncate"
                  >{{ t('10:00 - 15:00 · 包含午餐') }}</span
                >
              </div>
              <div
                class="absolute h-full bg-error-container border-l-4 border-error rounded-r-md flex flex-col justify-center px-3 pointer-events-auto cursor-pointer shadow-[0_0_12px_rgba(186,26,26,0.3)] z-10"
                style="left: 54.1%; width: 16.6%"
              >
                <div class="flex items-center gap-1">
                  <span
                    class="font-label-lg text-label-lg text-on-error-container text-xs font-bold truncate"
                    >{{ t('部门周会') }}</span
                  >
                </div>
                <span class="font-body-md text-body-md text-[10px] text-error truncate">{{
                  t('冲突: 转换时间不足15分')
                }}</span>
              </div>
            </div>
          </div>
          <!-- 会议室 3 · 董事会厅 -->
          <div
            class="gantt-grid border-b border-outline-variant relative group hover:bg-surface-bright transition-colors min-h-[80px]"
          >
            <div
              class="p-3 border-r border-outline-variant sticky left-0 bg-surface-container-lowest group-hover:bg-surface-bright z-20 shadow-[2px_0_4px_rgba(0,0,0,0.02)] transition-colors flex flex-col justify-center"
            >
              <span class="font-body-lg text-body-lg font-semibold">{{ t('董事会厅') }}</span>
              <span
                class="font-body-md text-body-md text-xs text-on-surface-variant flex items-center gap-1 mt-1"
                >{{ t('20人 · 视频会议') }}</span
              >
            </div>
            <div class="border-r border-outline-variant/30 h-full col-start-2"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-3"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-4"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-5"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-6"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-7"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-8"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-9"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-10"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-11"></div>
            <div class="border-r border-outline-variant/30 h-full col-start-12"></div>
            <div class="h-full col-start-13"></div>
          </div>
          <!-- 当前时间指示线 -->
          <div
            class="absolute top-0 bottom-0 border-l-2 border-primary z-30 pointer-events-none"
            style="left: calc(200px + 33.3%)"
          >
            <div
              class="absolute top-0 -left-[25px] bg-primary text-on-primary text-[10px] px-1.5 py-0.5 rounded-full font-num-md shadow-sm"
            >
              11:30
            </div>
          </div>
        </div>
      </div>

      <!-- 新建排期侧栏 -->
      <div
        class="w-full md:w-[320px] bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm flex flex-col shrink-0"
      >
        <div
          class="p-4 border-b border-outline-variant bg-surface-bright rounded-t-xl flex justify-between items-center"
        >
          <h3 class="font-headline-md text-headline-md font-semibold text-on-background">
            {{ t('新建排期') }}
          </h3>
          <button
            class="text-on-surface-variant hover:bg-surface-container p-1 rounded-full transition-colors"
          ></button>
        </div>
        <div class="p-4 flex-1 overflow-y-auto flex flex-col gap-5">
          <div class="flex flex-col gap-1.5">
            <label class="font-label-lg text-label-lg text-on-surface-variant">{{
              t('活动名称')
            }}</label
            ><input
              class="w-full border border-outline-variant rounded-md px-3 py-2 text-body-md focus:ring-2 focus:ring-primary focus:border-primary outline-none"
              type="text"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="font-label-lg text-label-lg text-on-surface-variant">{{
              t('活动类型')
            }}</label
            ><select
              class="w-full border border-outline-variant rounded-md px-3 py-2 text-body-md focus:ring-2 focus:ring-primary focus:border-primary outline-none bg-white"
            >
              <option>{{ t('企业会议') }}</option>
              <option>{{ t('婚宴') }}</option>
              <option>{{ t('工作坊') }}</option>
              <option>{{ t('其他') }}</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1.5">
              <label class="font-label-lg text-label-lg text-on-surface-variant">{{
                t('开始时间')
              }}</label
              ><input
                class="w-full border border-outline-variant rounded-md px-3 py-2 text-body-md focus:ring-2 focus:ring-primary focus:border-primary outline-none font-num-md"
                type="time"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-label-lg text-label-lg text-on-surface-variant">{{
                t('结束时间')
              }}</label
              ><input
                class="w-full border border-outline-variant rounded-md px-3 py-2 text-body-md focus:ring-2 focus:ring-primary focus:border-primary outline-none font-num-md"
                type="time"
              />
            </div>
          </div>
          <div class="pt-2 border-t border-outline-variant">
            <h4 class="font-label-lg text-label-lg font-semibold text-on-background mb-3">
              {{ t('场地与设备要求') }}
            </h4>
            <div class="flex flex-col gap-3">
              <div class="flex items-center gap-2">
                <input
                  class="w-full border border-outline-variant rounded-md px-3 py-1.5 text-body-md focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                  type="number"
                />
              </div>
              <div class="flex gap-2 flex-wrap mt-1">
                <label
                  class="flex items-center gap-1.5 bg-surface-container-low border border-outline-variant px-2.5 py-1 rounded-full cursor-pointer hover:bg-surface-container transition-colors"
                  ><input
                    checked
                    class="rounded text-primary focus:ring-primary"
                    type="checkbox"
                  /><span class="font-label-lg text-[12px]">{{ t('投影仪') }}</span></label
                >
                <label
                  class="flex items-center gap-1.5 bg-surface-container-low border border-outline-variant px-2.5 py-1 rounded-full cursor-pointer hover:bg-surface-container transition-colors"
                  ><input class="rounded text-primary focus:ring-primary" type="checkbox" /><span
                    class="font-label-lg text-[12px]"
                    >{{ t('白板') }}</span
                  ></label
                >
                <label
                  class="flex items-center gap-1.5 bg-surface-container-low border border-outline-variant px-2.5 py-1 rounded-full cursor-pointer hover:bg-surface-container transition-colors"
                  ><input
                    checked
                    class="rounded text-primary focus:ring-primary"
                    type="checkbox"
                  /><span class="font-label-lg text-[12px]">{{ t('视频会议系统') }}</span></label
                >
                <label
                  class="flex items-center gap-1.5 bg-surface-container-low border border-outline-variant px-2.5 py-1 rounded-full cursor-pointer hover:bg-surface-container transition-colors"
                  ><input class="rounded text-primary focus:ring-primary" type="checkbox" /><span
                    class="font-label-lg text-[12px]"
                    >{{ t('茶歇服务') }}</span
                  ></label
                >
              </div>
            </div>
          </div>
          <div
            class="bg-primary-fixed/20 border border-primary-fixed-dim rounded-lg p-3 relative overflow-hidden group"
          >
            <div
              class="absolute top-0 left-0 w-1 h-full bg-primary group-hover:w-1.5 transition-all"
            ></div>
            <div class="flex items-center gap-2 mb-1">
              <span
                class="font-label-lg text-label-lg text-on-primary-fixed-variant font-semibold text-sm"
                >{{ t('AI 推荐场地') }}</span
              >
            </div>
            <p class="font-body-md text-body-md text-on-surface-variant text-sm">
              {{ t('基于您的设备需求和预计人数，建议分配至')
              }}<strong class="text-on-background">{{ t('董事会厅') }}</strong
              >。
            </p>
          </div>
        </div>
        <div class="p-4 border-t border-outline-variant bg-surface-bright rounded-b-xl flex gap-3">
          <button
            class="flex-1 px-4 py-2 border border-outline text-on-surface font-label-lg text-label-lg rounded-full hover:bg-surface-container-low transition-colors text-center font-medium"
          >
            {{ t('取消') }}
          </button>
          <button
            class="flex-1 px-4 py-2 bg-primary text-on-primary font-label-lg text-label-lg rounded-full hover:opacity-90 shadow-sm transition-opacity text-center font-medium"
          >
            {{ t('创建预订') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 近期 MICE 排期（绑定 api.demo('mice')） -->
    <div class="max-w-max-content-width mx-auto px-container-padding pb-8">
      <div
        class="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden"
      >
        <div
          class="px-6 py-4 border-b border-outline-variant bg-surface-bright flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-primary">event_available</span>
          <h2 class="font-headline-md text-headline-md text-on-surface">
            {{ t('近期 MICE 排期') }}
          </h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr
                class="border-b border-outline-variant bg-surface-container-low font-label-lg text-label-lg text-on-surface-variant"
              >
                <th class="py-3 px-4">{{ t('活动') }}</th>
                <th class="py-3 px-4">{{ t('场地') }}</th>
                <th class="py-3 px-4 text-right">{{ t('人数') }}</th>
                <th class="py-3 px-4">{{ t('日期') }}</th>
                <th class="py-3 px-4">{{ t('状态') }}</th>
                <th class="py-3 px-4 text-right">{{ t('预计收入') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant">
              <tr v-for="e in events" :key="e.id" class="hover:bg-surface-bright transition-colors">
                <td class="py-3 px-4 font-medium text-on-surface">{{ e.event }}</td>
                <td class="py-3 px-4 text-sm text-on-surface">{{ e.space }}</td>
                <td class="py-3 px-4 text-right font-num-md text-on-surface">{{ e.pax }}</td>
                <td class="py-3 px-4 text-sm text-on-surface">{{ e.date }}</td>
                <td class="py-3 px-4">
                  <span
                    class="inline-flex text-xs font-medium rounded-full px-2 py-1"
                    :class="statusPill(e.status)"
                    >{{ e.status }}</span
                  >
                </td>
                <td class="py-3 px-4 text-right font-num-md text-primary font-bold">
                  {{ fmt(e.revenue) }}
                </td>
              </tr>
              <tr v-if="!events.length">
                <td colspan="6" class="py-8 text-center text-on-surface-variant">
                  {{ t('暂无排期') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
