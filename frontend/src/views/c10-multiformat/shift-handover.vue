<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

// 交接班记录（C10 多形态 · 运营交接）
// 当班营收 / 支付方式 / 备用金 / 待办 / 签名均为原型静态结构（忠实还原）。
// 该页为班次快照表单，无对应后端列表，按原型 1:1 还原。
</script>

<template>
  <div class="page">
    <div class="max-w-max-content-width mx-auto">
      <!-- 页头 -->
      <div class="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
        <div>
          <h2 class="font-display-lg text-display-lg text-on-background mb-1">
            {{ t('交接班记录') }}
          </h2>
          <p class="font-body-md text-body-md text-on-surface-variant">
            {{ t('2023年10月24日 · 早班 (08:00 - 16:00)') }}
          </p>
        </div>
        <div class="flex space-x-3">
          <button
            class="px-4 py-2 border border-outline rounded-lg text-on-surface font-label-lg text-label-lg hover:bg-surface-container-low transition-colors flex items-center"
          >
            <span class="material-symbols-outlined mr-2 text-sm">print</span>
            {{ t('打印小票') }}
          </button>
          <button
            class="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-lg text-label-lg hover:bg-primary/90 transition-colors shadow-sm flex items-center"
          >
            <span class="material-symbols-outlined mr-2 text-sm">check_circle</span>
            {{ t('确认交接') }}
          </button>
        </div>
      </div>
      <!-- 主网格 -->
      <div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        <!-- 左栏：营收与现金 -->
        <div class="md:col-span-8 flex flex-col gap-6">
          <!-- 当班营收总览 -->
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
          >
            <h3 class="font-headline-md text-headline-md text-on-surface mb-6 flex items-center">
              <span class="material-symbols-outlined mr-2 text-primary"
                >account_balance_wallet</span
              >
              {{ t('当班营收总览') }}
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              <div class="p-4 bg-surface-container-low rounded-lg border-l-4 border-primary">
                <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                  {{ t('系统应收 (Expected)') }}
                </p>
                <p class="font-num-xl text-num-xl text-on-surface">¥ 12,450.00</p>
              </div>
              <div class="p-4 bg-surface-container-low rounded-lg border-l-4 border-secondary">
                <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                  {{ t('实际收款 (Actual)') }}
                </p>
                <p class="font-num-xl text-num-xl text-on-surface">¥ 12,450.00</p>
              </div>
              <div class="p-4 bg-surface-container-low rounded-lg border-l-4 border-[#34a853]">
                <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">
                  {{ t('差额 (Variance)') }}
                </p>
                <p class="font-num-xl text-num-xl text-[#34a853]">¥ 0.00</p>
              </div>
            </div>
            <!-- 按支付方式统计 -->
            <h4
              class="font-label-lg text-label-lg text-on-surface-variant mb-3 uppercase tracking-wider"
            >
              {{ t('按支付方式统计') }}
            </h4>
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="border-b border-outline-variant">
                    <th class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant">
                      {{ t('支付方式') }}
                    </th>
                    <th
                      class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant text-right"
                    >
                      {{ t('笔数') }}
                    </th>
                    <th
                      class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant text-right"
                    >
                      {{ t('应收金额') }}
                    </th>
                    <th
                      class="py-3 px-4 font-label-lg text-label-lg text-on-surface-variant text-right"
                    >
                      {{ t('实收金额') }}
                    </th>
                  </tr>
                </thead>
                <tbody class="font-num-md text-num-md text-on-surface">
                  <tr class="border-b border-surface-container">
                    <td class="py-3 px-4 flex items-center font-body-md text-body-md">
                      <span class="material-symbols-outlined text-surface-tint mr-2 text-lg"
                        >qr_code_scanner</span
                      >
                      {{ t('微信支付') }}
                    </td>
                    <td class="py-3 px-4 text-right">42</td>
                    <td class="py-3 px-4 text-right">¥ 8,500.00</td>
                    <td class="py-3 px-4 text-right">¥ 8,500.00</td>
                  </tr>
                  <tr class="border-b border-surface-container">
                    <td class="py-3 px-4 flex items-center font-body-md text-body-md">
                      <span class="material-symbols-outlined text-[#1677FF] mr-2 text-lg"
                        >payment</span
                      >
                      {{ t('支付宝') }}
                    </td>
                    <td class="py-3 px-4 text-right">18</td>
                    <td class="py-3 px-4 text-right">¥ 3,200.00</td>
                    <td class="py-3 px-4 text-right">¥ 3,200.00</td>
                  </tr>
                  <tr class="border-b border-surface-container">
                    <td class="py-3 px-4 flex items-center font-body-md text-body-md">
                      <span class="material-symbols-outlined text-[#F5A623] mr-2 text-lg"
                        >payments</span
                      >
                      {{ t('现金') }}
                    </td>
                    <td class="py-3 px-4 text-right">5</td>
                    <td class="py-3 px-4 text-right">¥ 750.00</td>
                    <td class="py-3 px-4 text-right">¥ 750.00</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <!-- 备用金与发票 -->
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm"
          >
            <h3 class="font-headline-md text-headline-md text-on-surface mb-4 flex items-center">
              <span class="material-symbols-outlined mr-2 text-primary">point_of_sale</span>
              {{ t('备用金与发票清点 (Cash &amp; Float)') }}
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label class="block font-label-lg text-label-lg text-on-surface-variant mb-2">{{
                  t('备用金总额')
                }}</label>
                <div class="relative">
                  <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span class="font-num-md text-on-surface-variant">¥</span>
                  </div>
                  <input
                    class="block w-full pl-8 pr-3 py-2 border border-outline-variant rounded-lg font-num-md text-num-md text-on-surface bg-surface focus:ring-primary focus:border-primary"
                    readonly
                    type="text"
                    value="2,000.00"
                  />
                </div>
              </div>
              <div>
                <label class="block font-label-lg text-label-lg text-on-surface-variant mb-2">{{
                  t('空白发票剩余')
                }}</label>
                <div class="relative">
                  <input
                    class="block w-full pl-3 pr-10 py-2 border border-outline-variant rounded-lg font-num-md text-num-md text-on-surface bg-surface focus:ring-primary focus:border-primary"
                    readonly
                    type="text"
                    value="142"
                  />
                  <div
                    class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"
                  >
                    <span class="font-label-lg text-on-surface-variant">{{ t('张') }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- 右栏：待办与签名 -->
        <div class="md:col-span-4 flex flex-col gap-6">
          <!-- 待办事项 -->
          <div
            class="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden shadow-sm flex flex-col h-full"
          >
            <div
              class="p-4 bg-surface-container-low border-b border-outline-variant flex items-center justify-between"
            >
              <h3 class="font-headline-md text-headline-md text-on-surface flex items-center">
                <span class="material-symbols-outlined mr-2 text-secondary">pending_actions</span>
                {{ t('待办事项 (Pending Tasks)') }}
              </h3>
              <span
                class="bg-error-container text-on-error-container font-num-md text-xs px-2 py-0.5 rounded-full font-bold"
                >{{ t('2 紧急') }}</span
              >
            </div>
            <div class="p-4 flex-1 flex flex-col gap-3 overflow-y-auto">
              <div class="p-3 border border-[#F5A623] bg-[#FFF8E6] rounded-lg flex items-start">
                <span class="material-symbols-outlined text-[#F5A623] mr-3 mt-0.5 text-xl"
                  >warning</span
                >
                <div>
                  <p class="font-label-lg text-label-lg font-bold text-on-surface mb-1">
                    {{ t('302房 延迟退房') }}
                  </p>
                  <p class="font-body-md text-[13px] text-on-surface-variant">
                    {{ t('客人已申请延退至14:00，需通知客房部延后打扫。') }}
                  </p>
                </div>
              </div>
              <div class="p-3 border border-outline-variant bg-surface rounded-lg flex items-start">
                <span class="material-symbols-outlined text-primary mr-3 mt-0.5 text-xl">info</span>
                <div>
                  <p class="font-label-lg text-label-lg font-bold text-on-surface mb-1">
                    {{ t('805房 借用物品') }}
                  </p>
                  <p class="font-body-md text-[13px] text-on-surface-variant">
                    {{ t('借用加湿器一台，押金未收，退房时需确认收回。') }}
                  </p>
                </div>
              </div>
              <div class="mt-auto pt-4">
                <textarea
                  class="w-full border border-outline-variant rounded-lg p-3 font-body-md text-sm bg-surface-container-lowest placeholder-on-surface-variant focus:ring-primary focus:border-primary"
                  :placeholder="t('添加交接班备注...')"
                  rows="3"
                ></textarea>
              </div>
            </div>
          </div>
          <!-- 交接签名 -->
          <div class="bg-[#FFF3E0] border border-[#F5A623] rounded-xl p-5 shadow-sm">
            <h3 class="font-headline-md text-headline-md text-[#D84315] mb-4 flex items-center">
              <span class="material-symbols-outlined mr-2">draw</span>
              {{ t('交接签名') }}
            </h3>
            <div class="space-y-4">
              <div>
                <label class="block font-label-lg text-label-lg text-[#D84315] mb-1">{{
                  t('交班人 (Outgoing)')
                }}</label>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
