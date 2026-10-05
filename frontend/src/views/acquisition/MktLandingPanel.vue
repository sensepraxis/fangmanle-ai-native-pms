<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
import { authHeaders } from '../../lib/api/client'

/**
 * 落地页装修器：领券页 / 老客回访 / 会员中心（禁止自由 HTML）
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import { toast } from '../../lib/ui'

const CLAIM_BLOCKS = [
  'banner',
  'coupon_card',
  'button',
  'text',
  'image',
  'form_phone',
  'countdown',
  'cs',
] as const
const MEMBER_BLOCKS = [
  'banner',
  'member_header',
  'nav_tabs',
  'coupon_wallet',
  'order_list',
  'benefit_list',
  'text',
  'image',
  'button',
  'cs',
] as const
const RETURNING_BLOCKS = [
  'banner',
  'member_header',
  'coupon_wallet',
  'text',
  'image',
  'button',
  'cs',
] as const

const LABEL: Record<string, string> = {
  banner: 'Banner',
  coupon_card: t('优惠券卡片'),
  button: t('主按钮'),
  text: t('文本'),
  image: t('图片'),
  form_phone: t('手机号表单'),
  countdown: t('倒计时'),
  cs: t('客服'),
  member_header: t('会员头卡'),
  coupon_wallet: t('私域券包'),
  order_list: t('历史订单'),
  benefit_list: t('权益中心'),
  nav_tabs: t('页内 Tab'),
}

const pages = ref<any[]>([])
const templates = ref<any[]>([])
const coupons = ref<any[]>([])
const current = ref<any>(null)
const selectedId = ref<string | null>(null)
const blocks = ref<any[]>([])

const pageRole = computed(() => {
  const r = current.value?.page_role
  if (r === 'member' || r === 'returning') return r
  return 'claim'
})
const allowedBlocks = computed(() => {
  if (pageRole.value === 'member') return MEMBER_BLOCKS
  if (pageRole.value === 'returning') return RETURNING_BLOCKS
  return CLAIM_BLOCKS
})
const selected = computed(() => blocks.value.find((b) => b.id === selectedId.value) || null)

const previewing = ref(false)
const dirty = ref(false)
let hydrating = false
const locationOrigin = typeof location !== 'undefined' ? location.origin : ''

/** 画布机型：用于预览不同主流分辨率 */
const DEVICE_PRESETS = [
  { id: 'iphone15', label: 'iPhone 15', w: 393, h: 852, os: 'ios' as const },
  { id: 'iphoneSe', label: 'iPhone SE', w: 375, h: 667, os: 'ios' as const },
  { id: 'pixel8', label: 'Pixel 8', w: 412, h: 915, os: 'android' as const },
  { id: 'android360', label: t('安卓主流'), w: 360, h: 800, os: 'android' as const },
]
const deviceId = ref('iphone15')
const device = computed(
  () => DEVICE_PRESETS.find((d) => d.id === deviceId.value) || DEVICE_PRESETS[0],
)
const deviceScale = computed(() => Math.min(1, 620 / device.value.h, 360 / device.value.w))
const scaledW = computed(() => Math.round(device.value.w * deviceScale.value))
const scaledH = computed(() => Math.round(device.value.h * deviceScale.value))

function statusLabel(p: any) {
  if (p.status === 'published') {
    return p.has_unpublished_changes ? t('已发布·待更新') : t('已发布')
  }
  return t('草稿')
}

function roleText(p: any) {
  if (p.page_role === 'member') return t('会员中心')
  if (p.page_role === 'returning') return t('老客回访')
  return t('领券页')
}

function roleHintText() {
  if (pageRole.value === 'member') return t('会员中心')
  if (pageRole.value === 'returning') return t('老客回访')
  return t('领券页')
}

function fmtTime(s?: string) {
  if (!s) return '—'
  return String(s).replace('T', ' ').slice(0, 16)
}

async function openHtmlPreview(html: string) {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const w = window.open(url, '_blank')
  if (!w) {
    URL.revokeObjectURL(url)
    toast(t('请允许弹窗以打开预览'), false)
    return
  }
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

async function previewCanvas() {
  if (!current.value) return
  previewing.value = true
  try {
    const couponId = blocks.value.find((b) => b.type === 'coupon_card')?.props?.coupon_id
    const r = await fetch(`/api/mkt/landing-pages/preview?hotel_id=${hotelStore.hotelId}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        page_id: current.value.id,
        title: current.value.title,
        page_role: pageRole.value,
        blocks: blocks.value,
        coupon_id: pageRole.value === 'claim' ? couponId || current.value.coupon_id : null,
        demo: pageRole.value === 'member' || pageRole.value === 'returning',
      }),
    })
    if (r.status === 401) {
      toast(t('登录已失效，请重新登录'), false)
      return
    }
    if (!r.ok) {
      const j = await r.json().catch(() => ({}))
      throw new Error(typeof j.detail === 'string' ? j.detail : t('预览失败'))
    }
    await openHtmlPreview(await r.text())
  } catch (e: any) {
    toast(e?.message || t('预览失败'), false)
  } finally {
    previewing.value = false
  }
}

async function previewSaved(p: any) {
  previewing.value = true
  try {
    const demo = p.page_role === 'member' || p.page_role === 'returning' ? 1 : 0
    const r = await fetch(
      `/api/mkt/landing-pages/${p.id}/preview?hotel_id=${hotelStore.hotelId}&demo=${demo}`,
      { headers: authHeaders() },
    )
    if (!r.ok) {
      const j = await r.json().catch(() => ({}))
      throw new Error(typeof j.detail === 'string' ? j.detail : t('预览失败'))
    }
    await openHtmlPreview(await r.text())
  } catch (e: any) {
    toast(e?.message || t('预览失败'), false)
  } finally {
    previewing.value = false
  }
}

async function load() {
  const hid = hotelStore.hotelId
  ;[pages.value, templates.value, coupons.value] = await Promise.all([
    api.mktLandingPages(hid),
    api.mktLandingTemplates(),
    api.mktCoupons(hid, 'active'),
  ])
  if (!current.value && pages.value[0]) openPage(pages.value[0])
  else if (current.value) {
    const fresh = pages.value.find((p) => p.id === current.value.id)
    if (fresh) openPage(fresh)
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)

function markClean() {
  hydrating = true
  dirty.value = false
  nextTick(() => {
    dirty.value = false
    hydrating = false
  })
}

function openPage(p: any) {
  hydrating = true
  current.value = p
  blocks.value = JSON.parse(JSON.stringify(p.blocks || []))
  selectedId.value = blocks.value[0]?.id || null
  dirty.value = false
  nextTick(() => {
    // 深拷贝赋值可能异步触发 deep watch，再清一次避免误标 dirty
    dirty.value = false
    hydrating = false
  })
}

watch(
  [blocks, () => current.value?.title],
  () => {
    if (!hydrating && current.value) dirty.value = true
  },
  { deep: true },
)

function addBlock(type: string) {
  if (!(allowedBlocks.value as readonly string[]).includes(type)) return
  const id = 'b_' + Math.random().toString(36).slice(2, 8)
  const props: any = {}
  if (type === 'banner') {
    if (pageRole.value === 'member') props.title = t('我的会员中心')
    else if (pageRole.value === 'returning') {
      props.badge = t('欢迎回来')
      props.title = t('{guest_name}，您的私域礼遇')
      props.subtitle = t('欢迎回来！以下是您在本店私域领取的全部优惠券')
    } else props.title = t('活动标题')
  }
  if (type === 'button') {
    if (pageRole.value === 'returning') {
      props.text = t('进入专属会员中心')
      props.action = 'go_portal'
    } else if (pageRole.value === 'member') {
      props.text = t('刷新页面')
      props.action = 'reload'
    } else {
      props.text = t('提交并领取')
      props.action = 'submit_bind'
    }
  }
  if (type === 'text') props.text = t('说明文案')
  if (type === 'form_phone') {
    props.label = t('手机号')
    props.placeholder = t('请输入手机号')
  }
  if (type === 'coupon_card') {
    props.bind_pool = true
    props.coupon_id = current.value?.coupon_id || coupons.value[0]?.id || null
  }
  if (type === 'member_header') props.show_stats = true
  if (type === 'coupon_wallet') {
    props.title = t('私域优惠券')
    if (pageRole.value === 'returning') props.sum_style = 'returning'
    else props.tab = 'coupon'
  }
  if (type === 'order_list') {
    props.tab = 'order'
    props.title = t('历史订单')
    props.limit = 12
  }
  if (type === 'benefit_list') {
    props.tab = 'benefit'
    props.title = t('权益中心')
  }
  if (type === 'nav_tabs') {
    props.tabs = [
      { key: 'coupon', label: t('我的券') },
      { key: 'order', label: t('历史订单') },
      { key: 'benefit', label: t('权益中心') },
    ]
  }
  blocks.value.push({ id, type, props })
  selectedId.value = id
}

async function save() {
  if (!current.value) return
  try {
    const couponId = blocks.value.find((b) => b.type === 'coupon_card')?.props?.coupon_id
    const saved = await api.mktUpdateLanding(hotelStore.hotelId, current.value.id, {
      title: current.value.title,
      page_role: pageRole.value,
      blocks: blocks.value,
      coupon_id: pageRole.value === 'claim' ? couponId || current.value.coupon_id : null,
    })
    if (saved.status === 'published') {
      toast(
        saved.has_unpublished_changes
          ? t('已保存（草稿）。客人仍看旧版，请点「更新发布」上线')
          : t('已保存'),
      )
    } else {
      toast(t('已保存'))
    }
    hydrating = true
    current.value = saved
    dirty.value = false
    await load()
    const fresh = pages.value.find((p) => p.id === saved.id) || saved
    openPage(fresh)
    markClean()
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  }
}

async function publish() {
  if (!current.value) return
  if (dirty.value) {
    toast(t('请先保存后再发布'), false)
    return
  }
  try {
    const r = await api.mktPublishLanding(hotelStore.hotelId, current.value.id)
    toast(t('已发布，客人可看到当前内容'))
    await load()
    openPage(pages.value.find((p) => p.id === r.id) || r)
    markClean()
  } catch (e: any) {
    toast(e?.message || t('发布失败'), false)
  }
}

async function republish() {
  if (!current.value) return
  if (dirty.value) {
    toast(t('请先保存后再更新发布'), false)
    return
  }
  if (!current.value.has_unpublished_changes) {
    toast(t('没有待上线的修改'), false)
    return
  }
  try {
    const r = await api.mktPublishLanding(hotelStore.hotelId, current.value.id)
    toast(t('已更新发布，客人现在可以看到最新内容'))
    await load()
    openPage(pages.value.find((p) => p.id === r.id) || r)
    markClean()
  } catch (e: any) {
    toast(e?.message || t('更新发布失败'), false)
  }
}

async function unpublish() {
  if (!current.value) return
  if (current.value.status !== 'published') return
  if (dirty.value) {
    toast(t('有未保存修改，请先保存或放弃修改后再下架'), false)
    return
  }
  try {
    const r = await api.mktUnpublishLanding(hotelStore.hotelId, current.value.id)
    current.value = r
    toast(t('已下架，页面回到草稿'))
    await load()
    openPage(pages.value.find((p) => p.id === r.id) || r)
  } catch (e: any) {
    toast(e?.message || t('下架失败'), false)
  }
}

async function setAsWelcomeLanding() {
  if (!current.value) return
  if (current.value.status !== 'published') {
    toast(t('请先发布，再设为企微扫码领券页'), false)
    return
  }
  try {
    await api.mktSaveSettings(hotelStore.hotelId, {
      welcome_landing_page_id: current.value.id,
    })
    toast(t('已设为企微扫码领券页：客人加好友后将打开此页'))
    await load()
    openPage(pages.value.find((p) => p.id === current.value.id) || current.value)
  } catch (e: any) {
    toast(e?.message || t('设置失败'), false)
  }
}

async function setAsMemberLanding() {
  if (!current.value) return
  if (current.value.status !== 'published') {
    toast(t('请先发布，再设为企微会员中心页'), false)
    return
  }
  try {
    await api.mktUpdateLanding(hotelStore.hotelId, current.value.id, { page_role: 'member' })
    await api.mktSaveSettings(hotelStore.hotelId, {
      member_landing_page_id: current.value.id,
    })
    toast(t('已设为企微会员中心页：领券成功后将打开此页'))
    await load()
    openPage(pages.value.find((p) => p.id === current.value.id) || current.value)
  } catch (e: any) {
    toast(e?.message || t('设置失败'), false)
  }
}

async function setAsReturningLanding() {
  if (!current.value) return
  if (current.value.status !== 'published') {
    toast(t('请先发布，再设为老客回访页'), false)
    return
  }
  try {
    await api.mktUpdateLanding(hotelStore.hotelId, current.value.id, { page_role: 'returning' })
    await api.mktSaveSettings(hotelStore.hotelId, {
      returning_landing_page_id: current.value.id,
    })
    toast(t('已设为老客回访页：老客扫码先看此页，再进会员中心'))
    await load()
    openPage(pages.value.find((p) => p.id === current.value.id) || current.value)
  } catch (e: any) {
    toast(e?.message || t('设置失败'), false)
  }
}

async function createFromTpl(tplKey: string) {
  try {
    const isMember = tplKey === 'tpl_member_center'
    const isReturning = tplKey === 'tpl_returning'
    const couponId = isMember || isReturning ? undefined : coupons.value[0]?.id
    const p = await api.mktCreateLanding(hotelStore.hotelId, {
      page_key: `page_${Date.now().toString(36)}`,
      title: isMember ? t('新会员中心') : isReturning ? t('新老客回访页') : t('新落地页'),
      template_id: tplKey,
      page_role: isMember ? 'member' : isReturning ? 'returning' : 'claim',
      coupon_id: couponId,
    })
    toast(t('已从模板创建'))
    await load()
    openPage(p)
  } catch (e: any) {
    toast(e?.message || t('创建失败'), false)
  }
}

function removeSelected() {
  if (!selectedId.value) return
  blocks.value = blocks.value.filter((b) => b.id !== selectedId.value)
  selectedId.value = blocks.value[0]?.id || null
}

function roleLabel(p: any) {
  if (p.is_member_landing) return t(' · 会员中心')
  if (p.is_returning_landing) return t(' · 老客回访')
  if (p.is_welcome_landing) return t(' · 扫码领券')
  if (p.page_role === 'member') return t(' · 会员页')
  if (p.page_role === 'returning') return t(' · 回访页')
  return ''
}
</script>

<template>
  <div class="page">
    <div class="head">
      <div>
        <h1>{{ t('页面装修器') }}</h1>
      </div>
    </div>

    <div class="page-list panel-box">
      <div class="list-head">
        <h2>{{ t('页面列表') }}</h2>
        <div class="tpl-actions">
          <button
            v-for="tpl in templates"
            :key="tpl.template_key"
            type="button"
            class="btn tpl-add"
            @click="createFromTpl(tpl.template_key)"
          >
            <span class="tpl-add-prefix">{{ t('添加新页面：') }}</span
            >{{ tpl.name }}
          </button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ t('标题') }}</th>
              <th>page_key</th>
              <th>{{ t('角色') }}</th>
              <th>{{ t('状态') }}</th>
              <th>{{ t('闭环入口') }}</th>
              <th>{{ t('更新时间') }}</th>
              <th>{{ t('操作') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="p in pages"
              :key="p.id"
              :class="{ active: current?.id === p.id }"
              @click="openPage(p)"
            >
              <td class="title">{{ p.title || t('未命名') }}</td>
              <td>
                <code>{{ p.page_key }}</code>
              </td>
              <td>{{ roleText(p) }}</td>
              <td>
                <span class="tag" :class="p.status === 'published' ? 'ok' : 'draft'">{{
                  statusLabel(p)
                }}</span>
              </td>
              <td>
                <span v-if="p.is_welcome_landing" class="tag entry">{{ t('扫码领券') }}</span>
                <span v-if="p.is_member_landing" class="tag entry blue">{{ t('会员中心') }}</span>
                <span v-if="p.is_returning_landing" class="tag entry amber">{{
                  t('老客回访')
                }}</span>
                <span
                  v-if="!p.is_welcome_landing && !p.is_member_landing && !p.is_returning_landing"
                  class="muted"
                  >—</span
                >
              </td>
              <td class="muted">{{ fmtTime(p.updated_at) }}</td>
              <td class="ops" @click.stop>
                <button type="button" class="link" @click="openPage(p)">{{ t('编辑') }}</button>
                <button type="button" class="link" @click="previewSaved(p)">{{ t('预览') }}</button>
                <a
                  v-if="p.status === 'published'"
                  class="link"
                  :href="`${locationOrigin}/wecom/landing/${p.page_key}?hotel_id=${hotelStore.hotelId}`"
                  target="_blank"
                  rel="noopener"
                  >{{ t('正式链接') }}</a
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!pages.length" class="empty">{{ t('暂无页面，请从下方模板创建') }}</p>
    </div>

    <div class="edit-zone">
      <div class="edit-zone-label">{{ t('编辑区') }}</div>

      <div v-if="current && pageRole === 'claim'" class="welcome-bar panel-box">
        <div class="welcome-tx">
          <template v-if="current.is_welcome_landing">
            <b>{{ t('当前页已是企微扫码领券页') }}</b>
            · {{ t('欢迎语卡片打开本页') }}（page_key={{ current.page_key }}）
          </template>
          <template v-else>
            <b>{{ t('尚未设为扫码领券页') }}</b>
            · {{ t('发布后还需点右侧按钮，扫码才会打开本页') }}</template
          >
        </div>
        <button
          type="button"
          class="btn ok"
          :disabled="!current || current.status !== 'published' || current.is_welcome_landing"
          @click="setAsWelcomeLanding"
        >
          {{ current.is_welcome_landing ? t('已是扫码领券页') : t('设为企微扫码领券页') }}
        </button>
      </div>

      <div v-if="current && pageRole === 'member'" class="welcome-bar member-bar panel-box">
        <div class="welcome-tx">
          <template v-if="current.is_member_landing">
            <b>{{ t('当前页已是企微会员中心页') }}</b>
            · {{ t('客人点「进入专属会员中心」后打开本页') }}（page_key={{ current.page_key }}）
          </template>
          <template v-else>
            <b>{{ t('尚未设为会员中心页') }}</b>
            · {{ t('发布后点右侧按钮，客人从回访页进入本装修页') }}</template
          >
        </div>
        <button
          type="button"
          class="btn ok"
          :disabled="!current || current.status !== 'published' || current.is_member_landing"
          @click="setAsMemberLanding"
        >
          {{ current.is_member_landing ? t('已是会员中心页') : t('设为企微会员中心页') }}
        </button>
      </div>

      <div v-if="current && pageRole === 'returning'" class="welcome-bar returning-bar panel-box">
        <div class="welcome-tx">
          <template v-if="current.is_returning_landing">
            <b>{{ t('当前页已是老客回访页') }}</b>
            · {{ t('老客扫码领券链接会先打开本页') }}（page_key={{ current.page_key }}）
          </template>
          <template v-else>
            <b>{{ t('尚未设为老客回访页') }}</b>
            · {{ t('发布后点右侧按钮；老客扫码先看此页，再点按钮进会员中心') }}</template
          >
        </div>
        <button
          type="button"
          class="btn ok"
          :disabled="!current || current.status !== 'published' || current.is_returning_landing"
          @click="setAsReturningLanding"
        >
          {{ current.is_returning_landing ? t('已是老客回访页') : t('设为老客回访页') }}
        </button>
      </div>

      <div v-if="current" class="editor">
        <aside class="left panel">
          <h3>{{ t('组件库') }} · {{ roleHintText() }}</h3>
          <p class="panel-hint">{{ t('点击添加到画布') }}</p>
          <button
            v-for="blockKey in allowedBlocks"
            :key="blockKey"
            type="button"
            class="comp"
            @click="addBlock(blockKey)"
          >
            <span class="comp-name">{{ LABEL[blockKey] }}</span>
            <span class="comp-add">+</span>
          </button>
        </aside>

        <main class="center">
          <div class="device-bar">
            <button
              v-for="d in DEVICE_PRESETS"
              :key="d.id"
              type="button"
              class="device-chip"
              :class="{ on: deviceId === d.id }"
              @click="deviceId = d.id"
            >
              {{ d.label }}
            </button>
            <span class="device-meta"
              >{{ device.w }}×{{ device.h }} · {{ device.os === 'ios' ? 'iOS' : 'Android' }}</span
            >
          </div>
          <div class="device-stage">
            <div
              class="device-scale-wrap"
              :style="{ width: scaledW + 'px', height: scaledH + 'px' }"
            >
              <div
                class="device-shell"
                :class="device.os"
                :style="{
                  width: device.w + 'px',
                  height: device.h + 'px',
                  transform: `scale(${deviceScale})`,
                }"
              >
                <div class="device-bezel">
                  <div class="status-bar" :class="device.os">
                    <span>9:41</span>
                    <span v-if="device.os === 'ios'" class="notch" aria-hidden="true" />
                    <span class="status-icons">{{ device.os === 'ios' ? '▮▮▮' : '5G ▮▮' }}</span>
                  </div>
                  <div
                    class="phone-screen"
                    :class="{ member: pageRole === 'member' || pageRole === 'returning' }"
                  >
                    <div
                      v-for="b in blocks"
                      :key="b.id"
                      class="block"
                      :class="{ on: selectedId === b.id, [b.type]: true }"
                      @click="selectedId = b.id"
                    >
                      <template v-if="b.type === 'banner'">
                        <div class="badge">{{ b.props.badge || t('活动') }}</div>
                        <div class="t">{{ b.props.title }}</div>
                        <div class="s">{{ b.props.subtitle }}</div>
                      </template>
                      <template v-else-if="b.type === 'coupon_card'">
                        <div class="offer">
                          {{ t('券卡') }} · {{ t('批次') }} #{{ b.props.coupon_id || t('未绑') }}
                        </div>
                      </template>
                      <template v-else-if="b.type === 'form_phone'">
                        <div class="lbl">{{ b.props.label }}</div>
                        <div class="fake-input">{{ b.props.placeholder }}</div>
                      </template>
                      <template v-else-if="b.type === 'button'">
                        <div class="btn-prev">{{ b.props.text }}</div>
                      </template>
                      <template v-else-if="b.type === 'text'">
                        <div class="txt">{{ b.props.text }}</div>
                      </template>
                      <template v-else-if="b.type === 'member_header'">
                        <div class="offer">{{ t('会员头卡 · 姓名/等级/统计') }}</div>
                      </template>
                      <template v-else-if="b.type === 'coupon_wallet'">
                        <div class="offer">{{ t('私域券包 · 可使用/已核销/已过期') }}</div>
                      </template>
                      <template v-else-if="b.type === 'order_list'">
                        <div class="offer">{{ t('历史订单列表') }}</div>
                      </template>
                      <template v-else-if="b.type === 'benefit_list'">
                        <div class="offer">{{ t('权益中心列表') }}</div>
                      </template>
                      <template v-else-if="b.type === 'nav_tabs'">
                        <div class="txt">
                          Tab · {{ (b.props.tabs || []).map((x: any) => x.label).join(' / ') }}
                        </div>
                      </template>
                      <template v-else>
                        <div class="txt">{{ LABEL[b.type] }}</div>
                      </template>
                    </div>
                  </div>
                  <div v-if="device.os === 'android'" class="android-nav" aria-hidden="true">
                    <span /><span /><span />
                  </div>
                  <div v-else class="home-indicator" aria-hidden="true" />
                </div>
              </div>
            </div>
          </div>
        </main>

        <aside class="right panel">
          <h3>{{ t('属性') }}</h3>
          <div class="props-body">
            <template v-if="selected">
              <p class="type-tag">{{ LABEL[selected.type] }}</p>
              <label v-if="selected.type === 'banner'" class="field">
                {{ t('标题') }}
                <input v-model="selected.props.title" />
              </label>
              <label v-if="selected.type === 'banner'" class="field">
                {{ t('副标题') }}
                <input v-model="selected.props.subtitle" />
              </label>
              <label v-if="selected.type === 'banner'" class="field">
                {{ t('角标') }}
                <input v-model="selected.props.badge" />
              </label>
              <label v-if="selected.type === 'coupon_card'" class="field">
                {{ t('绑定券批次') }}
                <select v-model="selected.props.coupon_id">
                  <option :value="null">{{ t('请选择') }}</option>
                  <option v-for="c in coupons" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
              </label>
              <label v-if="selected.type === 'button'" class="field">
                {{ t('按钮文案') }}
                <input v-model="selected.props.text" />
              </label>
              <label v-if="selected.type === 'button' && pageRole === 'returning'" class="field">
                {{ t('动作') }}
                <select v-model="selected.props.action">
                  <option value="go_portal">{{ t('进入会员中心') }}</option>
                  <option value="reload">{{ t('刷新页面') }}</option>
                </select>
              </label>
              <label
                v-if="selected.type === 'banner' && pageRole === 'returning'"
                class="field hint-field"
              >
                <span class="muted">{{ t('标题可用占位符 guest_name 显示客人姓名') }}</span>
              </label>
              <label v-if="selected.type === 'text' || selected.type === 'cs'" class="field">
                {{ t('文案') }}
                <textarea v-model="selected.props.text" rows="3" />
              </label>
              <label v-if="selected.type === 'form_phone'" class="field">
                {{ t('标签') }}
                <input v-model="selected.props.label" />
              </label>
              <label v-if="selected.type === 'form_phone'" class="field">
                {{ t('占位') }}
                <input v-model="selected.props.placeholder" />
              </label>
              <label
                v-if="['coupon_wallet', 'order_list', 'benefit_list'].includes(selected.type)"
                class="field"
              >
                {{ t('区块标题') }}
                <input v-model="selected.props.title" />
              </label>
              <label
                v-if="['coupon_wallet', 'order_list', 'benefit_list'].includes(selected.type)"
                class="field"
              >
                {{ t('归属 Tab key') }}
                <input v-model="selected.props.tab" placeholder="coupon / order / benefit" />
              </label>
            </template>
            <p v-else class="empty">{{ t('点选画布中的组件') }}</p>

            <div class="page-meta">
              <label class="field">
                {{ t('页面标题') }}
                <input v-model="current.title" />
              </label>
              <p class="role-hint">{{ t('页面角色') }}：{{ roleHintText() }}</p>
            </div>
          </div>
          <div v-if="selected" class="props-footer">
            <button type="button" class="btn danger" @click="removeSelected">
              {{ t('删除组件') }}
            </button>
          </div>
        </aside>
      </div>
      <p v-else class="empty edit-empty">{{ t('请选择或从模板创建页面') }}</p>

      <div class="edit-actions">
        <button type="button" class="btn" @click="previewCanvas" :disabled="!current || previewing">
          {{ previewing ? t('预览中…') : t('预览') }}
        </button>
        <button
          type="button"
          class="btn"
          @click="save"
          :disabled="!current || !dirty"
          :title="!dirty ? t('没有未保存的修改') : t('仅保存到编辑区，不会立刻改客人看到的页面')"
        >
          {{ t('保存') }}
        </button>
        <template v-if="current?.status === 'published'">
          <span v-if="current.has_unpublished_changes && !dirty" class="pub-hint">{{
            t('有已保存未上线的修改')
          }}</span>
          <button
            type="button"
            class="btn pri"
            @click="republish"
            :disabled="!current || dirty || !current.has_unpublished_changes"
            :title="
              dirty
                ? t('请先保存后再更新发布')
                : !current.has_unpublished_changes
                  ? t('当前线上已是最新')
                  : t('把已保存内容推给客人（正式链接生效）')
            "
          >
            {{ t('更新发布') }}
          </button>
          <button
            type="button"
            class="btn danger"
            @click="unpublish"
            :disabled="!current || dirty"
            :title="dirty ? t('请先保存或处理未保存修改') : t('下架后变为草稿，正式链接将不可访问')"
          >
            {{ t('下架') }}
          </button>
        </template>
        <button
          v-else
          type="button"
          class="btn pri"
          @click="publish"
          :disabled="!current || dirty"
          :title="dirty ? t('请先保存后再发布') : t('发布后客人可通过正式链接访问')"
        >
          {{ t('发布') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.head {
  margin-bottom: 16px;
}
h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
  line-height: 1.2;
}
.subhead {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--on-surface-variant, #5b616e);
}
.panel-box {
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  overflow: hidden;
}
.page-list {
  padding: 12px 14px;
  margin-bottom: 12px;
}
.list-head {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}
.list-head h2 {
  margin: 0;
  font-size: 14px;
  flex: 0 0 auto;
}
.tpl-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.edit-zone {
  background: var(--surface-container-low, #f2f4f5);
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  padding: 14px 14px 16px;
  margin-bottom: 8px;
}
.edit-zone-label {
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
  margin-bottom: 10px;
  letter-spacing: 0.02em;
}
.edit-empty {
  padding: 24px 0;
  text-align: center;
}
.edit-actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  align-items: center;
  border-top: 1px solid #e5e7eb;
}
.pub-hint {
  font-size: 12px;
  color: #b45309;
  background: #fef3c7;
  padding: 4px 10px;
  border-radius: 6px;
  margin-right: 4px;
}
.table-wrap {
  overflow: auto;
}
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.btn.tpl-add {
  padding: 8px 14px;
  font-size: 13px;
  color: var(--on-surface, #1f2329);
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  box-shadow: none;
}
.btn.tpl-add:hover:not(:disabled) {
  background: color-mix(in srgb, var(--primary, #005bbf) 8%, #fff);
  border-color: color-mix(in srgb, var(--primary, #005bbf) 35%, var(--outline-variant, #c1c6d6));
  color: var(--primary, #005bbf);
}
.tpl-add-prefix {
  color: var(--primary, #005bbf);
  font-weight: 700;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th,
td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid #f3f4f6;
  white-space: nowrap;
}
th {
  font-size: 12px;
  color: #6b7280;
  font-weight: 650;
}
tbody tr {
  cursor: pointer;
}
tbody tr:hover {
  background: #f9fafb;
}
tbody tr.active {
  background: #eef2ff;
}
td.title {
  font-weight: 650;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
}
code {
  font-size: 12px;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
}
.tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #4b5563;
}
.tag.ok {
  background: #dcfce7;
  color: #166534;
}
.tag.draft {
  background: #f3f4f6;
  color: #6b7280;
}
.tag.entry {
  background: #dcfce7;
  color: #166534;
  margin-right: 4px;
}
.tag.entry.blue {
  background: #dbeafe;
  color: #1e40af;
}
.ops {
  display: flex;
  gap: 8px;
  align-items: center;
}
.link {
  border: none;
  background: none;
  color: var(--primary, #005bbf);
  cursor: pointer;
  font-size: 12px;
  padding: 0;
  text-decoration: none;
}
.muted {
  color: #9ca3af;
  font-size: 12px;
}
.welcome-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  margin-bottom: 12px;
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  border-radius: 12px;
}
.member-bar {
  border-color: #bfdbfe;
  background: #eff6ff;
}
.member-bar .welcome-tx {
  color: #1e40af;
}
.member-bar .welcome-tx b {
  color: #1e3a8a;
}
.returning-bar {
  border-color: #fcd34d;
  background: #fffbeb;
}
.returning-bar .welcome-tx {
  color: #92400e;
}
.returning-bar .welcome-tx b {
  color: #78350f;
}
.tag.entry.amber {
  background: #fef3c7;
  color: #92400e;
}
.welcome-tx {
  font-size: 13px;
  color: #166534;
  line-height: 1.45;
  flex: 1;
  min-width: 220px;
}
.welcome-tx b {
  color: #14532d;
}
.btn {
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn.pri {
  background: var(--primary, #005bbf);
  color: #fff;
  border-color: var(--primary, #005bbf);
}
.btn.ok {
  background: #16a34a;
  color: #fff;
  border-color: #16a34a;
}
.btn.sm {
  padding: 6px 10px;
  font-size: 12px;
}
.btn.danger {
  color: #dc2626;
  border-color: #fecaca;
  font-weight: 600;
}
.btn.danger:hover:not(:disabled) {
  background: #fef2f2;
}
.preview {
  font-size: 13px;
  color: var(--primary, #005bbf);
}
.editor {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 280px;
  gap: 12px;
  min-height: 640px;
  align-items: stretch;
}
@media (max-width: 1100px) {
  .editor {
    grid-template-columns: 1fr;
  }
}

.panel {
  display: flex;
  flex-direction: column;
  background: #f2f4f5;
  border: 1.5px solid #c1c6d6;
  border-radius: 12px;
  box-shadow: none;
  padding: 12px;
  min-height: 0;
}
.panel h3 {
  margin: 0 0 4px;
  font-size: 13px;
  color: #111827;
}
.panel-hint {
  margin: 0 0 10px;
  font-size: 11px;
  color: #6b7280;
}

.comp {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  text-align: left;
  margin-bottom: 8px;
  padding: 10px 12px;
  border: 1.5px solid #c1c6d6;
  border-radius: 8px;
  background: #fff;
  box-shadow: none;
  cursor: pointer;
  font-size: 13px;
  color: #111827;
  transition:
    border-color 0.12s,
    background 0.12s,
    box-shadow 0.12s;
}
.comp:hover {
  border-color: var(--primary, #005bbf);
  background: color-mix(in srgb, var(--primary, #005bbf) 8%, #fff);
  box-shadow: 0 2px 6px rgba(0, 91, 191, 0.08);
}
.comp-name {
  font-weight: 600;
}
.comp-add {
  color: var(--primary, #005bbf);
  font-weight: 700;
  font-size: 16px;
  line-height: 1;
}

.center {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}
.device-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  padding: 8px 10px;
  background: #fff;
  border: 1.5px solid #c1c6d6;
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}
.device-chip {
  border: 1px solid var(--outline-variant, #c1c6d6);
  background: var(--surface-container-high, #e8eaed);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 650;
  color: var(--on-surface-variant, #5b616e);
  cursor: pointer;
}
.device-chip:hover {
  color: var(--on-surface, #1f2329);
}
.device-chip.on {
  border-color: color-mix(in srgb, var(--primary, #005bbf) 35%, var(--outline-variant, #c1c6d6));
  background: color-mix(in srgb, var(--primary, #005bbf) 12%, #fff);
  color: var(--primary, #005bbf);
}
.device-meta {
  margin-left: auto;
  font-size: 11px;
  color: #6b7280;
  font-variant-numeric: tabular-nums;
}
.device-stage {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  overflow: auto;
  padding: 18px 12px 22px;
  background: #e6e8e9;
  border: 1.5px solid #c1c6d6;
  border-radius: 12px;
  box-shadow: inset 0 1px 2px rgba(16, 24, 40, 0.04);
  min-height: 560px;
}
.device-scale-wrap {
  position: relative;
}
.device-shell {
  transform-origin: top left;
  background: #111827;
  border-radius: 36px;
  padding: 10px;
  box-shadow:
    0 18px 48px rgba(15, 23, 42, 0.28),
    0 0 0 1px rgba(255, 255, 255, 0.08) inset;
}
.device-shell.android {
  border-radius: 28px;
  padding: 8px;
}
.device-bezel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0b1220;
  border-radius: 28px;
  overflow: hidden;
}
.device-shell.android .device-bezel {
  border-radius: 20px;
}
.status-bar {
  position: relative;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px 6px;
  font-size: 11px;
  font-weight: 650;
  color: #ecf8f1;
  background: transparent;
  z-index: 2;
}
.status-bar.android {
  color: #e5e7eb;
  padding-top: 8px;
}
.notch {
  position: absolute;
  left: 50%;
  top: 6px;
  transform: translateX(-50%);
  width: 96px;
  height: 22px;
  border-radius: 14px;
  background: #000;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08);
}
.status-icons {
  letter-spacing: 1px;
  font-size: 10px;
  opacity: 0.9;
}
.phone-screen {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 8px 12px 16px;
  background: linear-gradient(165deg, #0f3d2e 0%, #1a5c45 22%, #eef3f0 22%);
}
.phone-screen.member {
  background: linear-gradient(165deg, #0f3d2e 0%, #1a5c45 18%, #eef3f0 18%);
}
.android-nav {
  flex: 0 0 28px;
  display: flex;
  align-items: center;
  justify-content: space-evenly;
  background: #111827;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.android-nav span {
  display: block;
  width: 14px;
  height: 14px;
  border: 1.5px solid #9ca3af;
  border-radius: 2px;
  opacity: 0.85;
}
.android-nav span:nth-child(2) {
  border-radius: 50%;
  width: 12px;
  height: 12px;
}
.android-nav span:nth-child(3) {
  width: 0;
  height: 0;
  border: none;
  border-top: 7px solid transparent;
  border-bottom: 7px solid transparent;
  border-right: 11px solid #9ca3af;
  border-radius: 0;
}
.home-indicator {
  flex: 0 0 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
}
.home-indicator::after {
  content: '';
  width: 108px;
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.45);
}

.block {
  background: rgba(255, 255, 255, 0.97);
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 10px;
  cursor: pointer;
  border: 2px solid transparent;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);
}
.block.on {
  border-color: var(--primary, #005bbf);
  box-shadow: 0 0 0 1px var(--primary, #005bbf);
}
.block.banner {
  background: transparent;
  color: #ecf8f1;
  box-shadow: none;
}
.badge {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  margin-bottom: 6px;
}
.t {
  font-size: 18px;
  font-weight: 700;
}
.s {
  font-size: 12px;
  opacity: 0.85;
  margin-top: 4px;
}
.offer {
  background: #ecfdf3;
  color: #085d3a;
  padding: 12px;
  border-radius: 10px;
  font-weight: 650;
  border: 1px solid #bbf7d0;
}
.lbl {
  font-size: 12px;
  color: #475467;
  margin-bottom: 4px;
}
.fake-input {
  border: 1.5px solid #c1c6d6;
  border-radius: 8px;
  padding: 10px;
  color: #9ca3af;
  font-size: 13px;
  background: #fff;
}
.btn-prev {
  background: #099250;
  color: #fff;
  text-align: center;
  padding: 12px;
  border-radius: 10px;
  font-weight: 700;
}
.txt {
  font-size: 12px;
  color: #475467;
  line-height: 1.5;
}

.right {
  background: #fff;
}
.right .props-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-right: 2px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 12px;
  color: #4b5563;
  margin-bottom: 12px;
  font-weight: 600;
}
.field input,
.field select,
.field textarea {
  padding: 9px 10px;
  border: 1.5px solid #c1c6d6;
  border-radius: 8px;
  font-size: 13px;
  background: #f8fafb;
  color: #111827;
  font-weight: 500;
  box-shadow: inset 0 1px 1px rgba(16, 24, 40, 0.03);
}
.field input:focus,
.field select:focus,
.field textarea:focus {
  outline: none;
  border-color: var(--primary, #005bbf);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(0, 91, 191, 0.15);
}
.type-tag {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 700;
  margin: 0 0 12px;
  padding: 4px 10px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--primary, #005bbf) 10%, #fff);
  color: var(--primary, #005bbf);
  border: 1px solid color-mix(in srgb, var(--primary, #005bbf) 28%, var(--outline-variant, #c1c6d6));
}
.page-meta {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid #c1c6d6;
}
.role-hint {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
  font-weight: 500;
}
.props-footer {
  flex: 0 0 auto;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1.5px solid #e5e7eb;
}
.props-footer .btn.danger {
  width: 100%;
  padding: 9px 12px;
  border-width: 1.5px;
}
.empty {
  color: #6b7280;
  font-size: 13px;
  padding: 8px 0 12px;
}
select {
  padding: 7px 10px;
  border-radius: 7px;
  border: 1px solid #e5e7eb;
}
</style>
