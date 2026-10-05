<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 护栏与写回设置 Guardrails & Sync：价格边界 + 自动化规则 + 系统同步状态
// 说明：本页为配置/状态页，原型无后端列表，忠于原型静态渲染；边框参数与同步状态为展示占位。
</script>

<template>
  <div class="page">
    <!-- 页头 -->
    <div class="mb-8">
      <h1 class="font-display-lg text-display-lg text-on-background mb-2">
        {{ t('护栏与写回设置 (Guardrails &amp; Sync)') }}
      </h1>
      <p class="font-body-md text-body-md text-on-surface-variant max-w-3xl">
        Configure automated pricing rules, define safe boundaries, and manage the synchronization
        status with Property Management Systems and Online Travel Agencies.
      </p>
    </div>
    <!-- 仪表盘网格 -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
      <!-- 左列：价格边界与逻辑 -->
      <div class="col-span-1 lg:col-span-8 flex flex-col gap-6">
        <section
          class="bg-surface rounded-xl border border-outline-variant shadow-sm p-6 relative overflow-hidden"
        >
          <div class="absolute left-0 top-0 bottom-0 w-1 bg-tertiary opacity-80"></div>
          <div class="flex items-center gap-2 mb-6">
            <span class="material-symbols-outlined text-tertiary">tune</span>
            <h2 class="font-headline-lg text-headline-lg text-on-surface">
              {{ t('全局价格边界 (Global Pricing Boundaries)') }}
            </h2>
          </div>
          <p class="font-body-md text-body-md text-secondary mb-6">
            Define the absolute minimum and maximum prices AI is allowed to set across all room
            types. The AI will never recommend prices outside this range unless manually overridden.
          </p>
          <div class="bg-surface-container-low rounded-lg p-6 border border-outline-variant">
            <div class="flex justify-between items-end mb-4">
              <div>
                <label class="block font-label-lg text-label-lg text-on-surface mb-1"
                  >Base Room Range (B_min - B_max)</label
                >
                <div class="flex items-baseline gap-2">
                  <span class="font-num-xl text-num-xl text-primary">¥280</span>
                  <span class="text-secondary">-</span>
                  <span class="font-num-xl text-num-xl text-primary">¥1,200</span>
                </div>
              </div>
              <button
                class="px-4 py-2 bg-surface border border-outline text-primary rounded-lg font-label-lg text-label-lg hover:bg-primary-fixed hover:border-primary transition-colors"
              >
                Edit Range
              </button>
            </div>
            <div class="relative h-2 bg-surface-container-highest rounded-full mt-8 mb-4">
              <div class="absolute left-[15%] right-[25%] h-full bg-primary rounded-full"></div>
              <div
                class="absolute left-[15%] top-1/2 -translate-y-1/2 w-4 h-4 bg-white border-2 border-primary rounded-full shadow"
              ></div>
              <span
                class="absolute left-[15%] -bottom-6 -translate-x-1/2 font-num-md text-sm text-secondary"
                >¥280</span
              >
              <div
                class="absolute right-[25%] top-1/2 -translate-y-1/2 w-4 h-4 bg-white border-2 border-primary rounded-full shadow"
              ></div>
              <span
                class="absolute right-[25%] -bottom-6 -translate-x-1/2 font-num-md text-sm text-secondary"
                >¥1200</span
              >
              <span class="absolute left-0 -bottom-6 font-num-md text-sm text-outline">¥0</span>
              <span class="absolute right-0 -bottom-6 font-num-md text-sm text-outline"
                >¥2000+</span
              >
            </div>
          </div>
        </section>
        <section class="bg-surface rounded-xl border border-outline-variant shadow-sm p-6">
          <div class="flex items-center justify-between mb-6">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">rule</span>
              <h2 class="font-headline-lg text-headline-lg text-on-surface">
                {{ t('自动化规则与审批流 (Automation &amp; Workflows)') }}
              </h2>
            </div>
            <button
              class="flex items-center gap-1 text-primary hover:text-primary-container font-label-lg"
            >
              <span class="material-symbols-outlined text-[20px]">add</span>
              Add Rule
            </button>
          </div>
          <div class="space-y-4">
            <div
              class="p-4 rounded-lg border border-error bg-error-container/20 flex flex-col sm:flex-row gap-4 items-start sm:items-center"
            >
              <div
                class="w-10 h-10 rounded-full bg-error-container text-on-error-container flex items-center justify-center shrink-0"
              >
                <span class="material-symbols-outlined">warning</span>
              </div>
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <h3 class="font-headline-md text-headline-md text-on-surface">
                    Bulk Price Drop (R3 - High Risk)
                  </h3>
                  <span class="px-2 py-0.5 rounded text-xs font-medium bg-error text-on-error"
                    >Requires Auth</span
                  >
                </div>
                <p class="font-body-md text-body-md text-on-surface-variant">
                  If AI suggests dropping prices by &gt;15% across &gt;5 room types.
                </p>
              </div>
              <div class="shrink-0 flex items-center gap-3">
                <span class="text-sm text-secondary">Manual Approval</span>
                <div class="w-12 h-6 bg-primary rounded-full relative cursor-pointer">
                  <div class="absolute right-1 top-1 w-4 h-4 bg-white rounded-full shadow-sm"></div>
                </div>
              </div>
            </div>
            <div
              class="p-4 rounded-lg border border-[#f9a825] bg-[#fff8e1] flex flex-col sm:flex-row gap-4 items-start sm:items-center"
            >
              <div
                class="w-10 h-10 rounded-full bg-[#ffecb3] text-[#f57f17] flex items-center justify-center shrink-0"
              >
                <span class="material-symbols-outlined">rule_folder</span>
              </div>
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <h3 class="font-headline-md text-headline-md text-on-surface">
                    Weekend Premium Adjustment (R2)
                  </h3>
                  <span class="px-2 py-0.5 rounded text-xs font-medium bg-[#f9a825] text-white"
                    >Review Suggested</span
                  >
                </div>
                <p class="font-body-md text-body-md text-on-surface-variant">
                  Increase rates when occupancy is projected &gt;85% for upcoming weekend.
                </p>
              </div>
              <div class="shrink-0 flex items-center gap-3">
                <span class="text-sm text-secondary">Require Checkbox</span>
                <div class="w-12 h-6 bg-primary rounded-full relative cursor-pointer">
                  <div class="absolute right-1 top-1 w-4 h-4 bg-white rounded-full shadow-sm"></div>
                </div>
              </div>
            </div>
            <div
              class="p-4 rounded-lg border border-outline-variant bg-surface flex flex-col sm:flex-row gap-4 items-start sm:items-center"
            >
              <div
                class="w-10 h-10 rounded-full bg-surface-container-high text-on-surface flex items-center justify-center shrink-0"
              >
                <span class="material-symbols-outlined">update</span>
              </div>
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <h3 class="font-headline-md text-headline-md text-on-surface">
                    Update Frequency Limit
                  </h3>
                </div>
                <p class="font-body-md text-body-md text-on-surface-variant">
                  Maximum number of automated price syncs allowed per hour.
                </p>
              </div>
              <div class="shrink-0 flex items-center gap-2">
                <input
                  class="w-16 h-10 rounded-md border-outline-variant focus:border-primary focus:ring-primary text-center font-num-md"
                  type="number"
                  value="4"
                />
                <span class="text-sm text-secondary">times/hr</span>
              </div>
            </div>
          </div>
        </section>
      </div>
      <!-- 右列：同步状态 -->
      <div class="col-span-1 lg:col-span-4 flex flex-col gap-6">
        <section class="bg-surface rounded-xl border border-outline-variant shadow-sm p-6 h-full">
          <div class="flex items-center gap-2 mb-6">
            <span class="material-symbols-outlined text-primary">sync</span>
            <h2 class="font-headline-lg text-headline-lg text-on-surface">
              {{ t('系统同步状态 (Sync Status)') }}
            </h2>
          </div>
          <div class="mb-6">
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 bg-[#e8f5e9] text-[#2e7d32] rounded flex items-center justify-center"
                >
                  <span class="material-symbols-outlined text-[20px]">cloud</span>
                </div>
                <div>
                  <h4 class="font-headline-md text-[16px] text-on-surface">GreenCloud PMS</h4>
                  <span class="text-xs text-secondary">Primary Database</span>
                </div>
              </div>
              <span class="flex items-center gap-1 text-sm font-medium text-[#2e7d32]">
                <span class="w-2 h-2 rounded-full bg-[#4caf50]"></span> Connected
              </span>
            </div>
            <div
              class="bg-surface-container-lowest border border-outline-variant rounded p-3 text-sm font-num-md text-secondary space-y-1"
            >
              <div class="flex justify-between">
                <span>Last Sync:</span><span class="text-on-surface">2 mins ago</span>
              </div>
              <div class="flex justify-between">
                <span>Inventory Status:</span><span class="text-on-surface">Match (100%)</span>
              </div>
            </div>
          </div>
          <div class="mb-6">
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-3">
                <div
                  class="w-8 h-8 bg-error-container text-on-error-container rounded flex items-center justify-center"
                >
                  <span class="material-symbols-outlined text-[20px]">flight_takeoff</span>
                </div>
                <div>
                  <h4 class="font-headline-md text-[16px] text-on-surface">
                    {{ t('别单红 (Biedanhong)') }}
                  </h4>
                  <span class="text-xs text-secondary">Channel Manager</span>
                </div>
              </div>
              <span class="flex items-center gap-1 text-sm font-medium text-primary">
                <span class="material-symbols-outlined text-[16px] animate-spin">sync</span>
                Syncing...
              </span>
            </div>
            <div
              class="bg-surface-container-lowest border border-outline-variant rounded p-3 text-sm font-num-md text-secondary space-y-1"
            >
              <div class="flex justify-between">
                <span>Last Write-back:</span><span class="text-on-surface">15 mins ago</span>
              </div>
              <div class="flex justify-between">
                <span>Pending Updates:</span><span class="text-[#f57f17]">3 Prices</span>
              </div>
            </div>
          </div>
          <div class="mt-8 pt-6 border-t border-outline-variant">
            <button
              class="w-full py-2.5 bg-primary text-on-primary rounded-lg font-label-lg hover:bg-on-primary-fixed-variant transition-colors mb-3 flex items-center justify-center gap-2"
            >
              <span class="material-symbols-outlined text-[18px]">play_arrow</span>
              Force Manual Sync
            </button>
            <button
              class="w-full py-2.5 bg-surface border border-error text-error rounded-lg font-label-lg hover:bg-error-container transition-colors flex items-center justify-center gap-2"
            >
              <span class="material-symbols-outlined text-[18px]">stop_circle</span>
              Halt All Write-backs
            </button>
            <p class="text-xs text-center text-outline mt-3">
              Use halt only in emergency cases to stop all outgoing OTA price updates.
            </p>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
