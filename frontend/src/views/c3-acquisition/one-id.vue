<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, onMounted } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import AcquisitionFlowNav from '../../components/AcquisitionFlowNav.vue'
import AcquisitionLoopPanel from '../../components/AcquisitionLoopPanel.vue'

const meta = ref<any>({
  title: t('小红书获客'),
  subtitle: t('聚光 Webhook 线索入库 · 跟进 · 私域 · 转预订（种草请在小红书 App 发布）'),
})

const interactions = ref<any[]>([
  { label: t('待认领线索'), value: '—', valueClass: 'text-on-surface' },
  { label: t('Webhook 入库'), value: '—', valueClass: 'text-on-surface' },
  { label: t('预计转化率'), value: '—', valueClass: 'text-primary' },
])

const bindingInfo = ref({ ad_account: '—', webhook: t('未配置') })

// 私域流量漏斗 4 步
const steps = ref<any[]>([
  {
    label: t('平台引流'),
    sub: t('小红书私信/评论'),
    dot: 'bg-primary text-on-primary',
    active: false,
  },
  {
    label: t('微信承接'),
    sub: t('添加管家微信'),
    dot: 'bg-primary-container text-on-primary-container border-2 border-surface-container-lowest ring-4 ring-primary/20',
    active: true,
  },
  {
    label: t('身份核验'),
    sub: t('获取预订手机号'),
    dot: 'bg-surface text-on-surface-variant border-2 border-outline-variant',
    active: false,
  },
  {
    label: t('One ID 归因'),
    sub: '自动打标"小红书来源"',
    dot: 'bg-surface text-on-surface-variant border-2 border-outline-variant',
    active: false,
  },
])

onMounted(async () => {
  try {
    const hid = hotelStore.hotelId
    const [board, bindings] = await Promise.all([
      api.acquisitionBoard(hid),
      api.acquisitionChannelBindings(hid),
    ])
    const m = board?.metrics || {}
    const funnel = board?.funnel || {}
    const booked = funnel.booked || 0
    const total = m.leads || 0
    const cvr = total > 0 ? `${Math.round((booked / total) * 1000) / 10}%` : '—'
    interactions.value = [
      { label: t('待认领线索'), value: String(funnel.new ?? 0), valueClass: 'text-on-surface' },
      {
        label: t('Webhook 入库'),
        value: String(m.webhook_leads ?? 0),
        valueClass: 'text-on-surface',
      },
      { label: t('闭环转化率'), value: cvr, valueClass: 'text-primary' },
    ]
    const b = bindings?.[0]
    bindingInfo.value = {
      ad_account: b?.xhs_ad_account_id || t('样例账户'),
      webhook: b?.webhook_secret_set ? t('已配置验签') : t('未配置验签'),
    }
  } catch {
    /* 兜底 */
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-4 flex justify-end"><AcquisitionFlowNav mode="main" /></div>
    <AcquisitionLoopPanel focus="claim" />
    <div class="max-w-[1440px] mx-auto w-full">
      <!-- 页头 -->
      <div class="mb-8 flex items-end justify-between">
        <div>
          <h1 class="font-display-lg text-display-lg text-on-surface mb-2">{{ meta.title }}</h1>
          <p class="font-body-md text-body-md text-on-surface-variant">{{ meta.subtitle }}</p>
        </div>
      </div>

      <div class="grid grid-cols-12 gap-6">
        <!-- 企业号状态 -->
        <div
          class="col-span-12 md:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm flex flex-col justify-between"
        >
          <div>
            <div class="flex items-center gap-3 mb-4">
              <div
                class="w-10 h-10 rounded-full bg-[#ff2442]/10 flex items-center justify-center text-[#ff2442]"
              ></div>
              <h2 class="font-headline-md text-headline-md text-on-surface">
                {{ t('企业号状态') }}
              </h2>
            </div>
            <div class="flex items-center gap-2 mb-2">
              <span class="font-body-lg text-body-lg text-on-surface font-semibold">{{
                t('已绑定')
              }}</span>
            </div>
            <p class="font-body-md text-body-md text-on-surface-variant mb-2">
              {{ t('聚光账户 ID：')
              }}<span class="text-on-surface">{{ bindingInfo.ad_account }}</span>
            </p>
            <p class="font-body-md text-body-md text-on-surface-variant mb-6">
              {{ t('Webhook 验签：')
              }}<span class="text-on-surface">{{ bindingInfo.webhook }}</span>
            </p>
          </div>
          <div class="bg-surface-container-low rounded-lg p-4 flex justify-between items-center">
            <div>
              <p class="font-label-lg text-label-lg text-on-surface-variant">
                {{ t('本周新增粉丝') }}
              </p>
              <p class="font-num-xl text-num-xl text-primary mt-1">+128</p>
            </div>
          </div>
        </div>

        <!-- 互动与转化 -->
        <div
          class="col-span-12 md:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <h2
            class="font-headline-md text-headline-md text-on-surface mb-6 flex items-center gap-2"
          >
            {{ t('互动与转化') }}
          </h2>
          <div class="grid grid-cols-3 gap-4 mb-6">
            <div
              v-for="m in interactions"
              :key="m.label"
              class="p-4 border border-outline-variant rounded-lg"
            >
              <p class="font-label-lg text-label-lg text-on-surface-variant mb-1">{{ m.label }}</p>
              <p class="font-num-xl text-num-xl" :class="m.valueClass">{{ m.value }}</p>
            </div>
          </div>
          <div class="bg-[#e8f0fe] rounded-lg p-4 flex items-start gap-3 border border-[#d2e3fc]">
            <div>
              <h4 class="font-label-lg text-label-lg text-primary mb-1">
                {{ t('平台私域引流限制提示') }}
              </h4>
              <p class="font-body-md text-body-md text-on-surface-variant">
                {{
                  t(
                    '检测到小红书平台近期对直接发送微信号的限制增强。建议使用"预约表单组件"或引导用户查看企业号主页配置的联系方式，避免账号被限流。',
                  )
                }}
              </p>
            </div>
          </div>
        </div>

        <!-- 私域流量漏斗 (One ID 归因) -->
        <div
          class="col-span-12 bg-surface-container-lowest rounded-xl border border-outline-variant p-6 shadow-sm"
        >
          <h2
            class="font-headline-md text-headline-md text-on-surface mb-6 flex items-center gap-2"
          >
            {{ t('私域流量漏斗 (One ID 归因)') }}
          </h2>
          <p class="font-body-md text-body-md text-on-surface-variant mb-8 max-w-3xl">
            {{
              t(
                '对于从小红书引流至微信私域或直接到店的客户，请依照以下流程进行人工核销与 One ID 系统打标，以便准确追踪获客ROI。',
              )
            }}
          </p>
          <div class="relative flex items-center justify-between w-full max-w-4xl mx-auto mb-4">
            <div
              class="absolute left-0 top-1/2 -translate-y-1/2 w-full h-0.5 bg-surface-variant z-0"
            ></div>
            <div class="absolute left-0 top-1/2 -translate-y-1/2 w-1/3 h-0.5 bg-primary z-0"></div>
            <div
              v-for="s in steps"
              :key="s.label"
              class="relative z-10 flex flex-col items-center gap-2"
            >
              <div
                class="w-10 h-10 rounded-full flex items-center justify-center shadow-md"
                :class="s.dot"
              ></div>
              <span
                class="font-label-lg text-label-lg whitespace-nowrap"
                :class="s.active ? 'text-primary font-bold' : 'text-on-surface'"
                >{{ s.label }}</span
              >
              <span
                class="font-body-md text-[12px] text-on-surface-variant absolute -bottom-6 whitespace-nowrap"
                >{{ s.sub }}</span
              >
            </div>
          </div>
          <div class="mt-16 bg-surface-container-low rounded-lg p-5 border border-outline-variant">
            <div class="flex items-start gap-4">
              <div>
                <h4 class="font-label-lg text-label-lg text-on-surface mb-2">
                  {{ t('手动归因操作指南') }}
                </h4>
                <p class="font-body-md text-body-md text-on-surface-variant mb-4">
                  {{
                    t(
                      '当客户通过微信预订并在 PMS 落单后，客服需在「客源」模块中，将客户的微信ID/手机号与小红书昵称进行手动关联。系统 AI 将在关联后自动计算转化周期与客单价。',
                    )
                  }}
                </p>
                <button
                  class="border border-outline hover:bg-surface-variant text-on-surface font-label-lg text-label-lg px-4 py-2 rounded-lg transition-colors"
                >
                  {{ t('立即前往客源打标') }}
                </button>
              </div>
            </div>
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
</style>
