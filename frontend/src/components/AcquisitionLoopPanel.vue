<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

/**
 * 获客闭环：Webhook 入库线索 → 跟进 → 私域 → 人工转预订 → 到店
 */
import { ref, onMounted, watch, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'

const props = withDefaults(
  defineProps<{
    focus?: 'overview' | 'claim' | 'funnel' | 'book'
    /** full=原样；leads=仅线索；funnel=仅漏斗 */
    view?: 'full' | 'leads' | 'funnel'
    /** 嵌入营销获客主页时隐藏大标题与样例按钮 */
    simple?: boolean
    /** 渠道：留空=通用私域；xiaohongshu | douyin 仅兼容旧调用 */
    channel?: 'xiaohongshu' | 'douyin' | ''
  }>(),
  { focus: 'overview', view: 'full', simple: false, channel: '' },
)

const isDouyin = computed(() => props.channel === 'douyin')
const channelLabel = computed(() =>
  isDouyin.value
    ? t('抖音来客')
    : props.channel === 'xiaohongshu'
      ? t('小红书聚光')
      : t('获客渠道'),
)

const router = useRouter()
const loading = ref(false)
const busyId = ref<number | null>(null)
const msg = ref('')
const board = ref<any>(null)
const bindings = ref<any[]>([])
const webhookEvents = ref<any[]>([])
const showBindingForm = ref(false)
const showManualForm = ref(false)
const showConvertForm = ref(false)
const convertLead = ref<any>(null)
const selectedLead = ref<any>(null)
const roomTypes = ref<any[]>([])
const convertForm = reactive({
  guest_name: '',
  phone: '',
  wechat: '',
  room_type_id: '' as string | number,
  check_in: '',
  check_out: '',
  rooms: 1,
  adults: 1,
  unit_price: '' as string | number,
  remark: '',
})

const bindingForm = reactive({
  label: '',
  xhs_ad_account_id: '',
  xhs_professional_id: '',
  xhs_page_ids: '',
  webhook_secret: '',
})

const manualForm = reactive({
  nickname: '',
  phone: '',
  wechat: '',
  note_title: '',
  source_note_url: '',
  intent: 'high',
  remark: '',
})

const primaryBinding = computed(() => bindings.value[0] || null)
const funnelSteps = computed(() => board.value?.funnel_steps || [])
const metrics = computed(() => board.value?.metrics || {})
const leads = computed(() => {
  const list = board.value?.leads || []
  if (props.focus === 'claim')
    return list.filter((x: any) => x.stage === 'new' || x.stage === 'claimed')
  if (props.focus === 'funnel') return list
  if (props.focus === 'book')
    return list.filter(
      (x: any) => x.stage === 'private' || x.stage === 'booked' || x.stage === 'arrived',
    )
  return list
})

function fillBindingForm() {
  const b = primaryBinding.value
  if (!b) return
  bindingForm.label = b.label || ''
  bindingForm.xhs_ad_account_id = b.xhs_ad_account_id || ''
  bindingForm.xhs_professional_id = b.xhs_professional_id || ''
  bindingForm.xhs_page_ids = b.xhs_page_ids || ''
  bindingForm.webhook_secret = ''
}

async function load() {
  loading.value = true
  msg.value = ''
  try {
    const hid = hotelStore.hotelId
    const ch = props.channel || undefined
    const [b, bind, ev] = await Promise.all([
      api.acquisitionBoard(hid, ch),
      api.acquisitionChannelBindings(hid, ch || 'xiaohongshu'),
      api.acquisitionWebhookEvents(hid, 8),
    ])
    board.value = b
    bindings.value = bind
    webhookEvents.value = ev
    fillBindingForm()
  } catch (e: any) {
    msg.value = e?.message || t('加载失败')
  } finally {
    loading.value = false
  }
}

async function saveBinding() {
  busyId.value = -3
  msg.value = ''
  try {
    const hid = hotelStore.hotelId
    const payload = {
      hotel_id: hid,
      channel: props.channel || 'private',
      label:
        bindingForm.label ||
        (isDouyin.value
          ? t('抖音来客绑定')
          : props.channel === 'xiaohongshu'
            ? t('小红书聚光绑定')
            : t('获客渠道绑定')),
      xhs_ad_account_id: bindingForm.xhs_ad_account_id,
      xhs_professional_id: bindingForm.xhs_professional_id,
      xhs_page_ids: bindingForm.xhs_page_ids,
      webhook_secret: bindingForm.webhook_secret || undefined,
    }
    if (primaryBinding.value?.id) {
      await api.acquisitionUpdateChannelBinding(primaryBinding.value.id, payload)
      msg.value = t('绑定配置已更新')
    } else {
      await api.acquisitionCreateChannelBinding(payload)
      msg.value = t('已创建新绑定')
    }
    showBindingForm.value = false
    await load()
  } catch (e: any) {
    msg.value = e?.message || t('保存绑定失败')
  } finally {
    busyId.value = null
  }
}

async function submitManualLead() {
  busyId.value = -4
  msg.value = ''
  try {
    const lead = await api.acquisitionManualLead({
      hotel_id: hotelStore.hotelId,
      channel: props.channel,
      ...manualForm,
    })
    msg.value = `手工录入成功 · 线索 #${lead.id}`
    manualForm.nickname = ''
    manualForm.phone = ''
    manualForm.wechat = ''
    manualForm.note_title = ''
    manualForm.source_note_url = ''
    manualForm.remark = ''
    showManualForm.value = false
    await load()
  } catch (e: any) {
    msg.value = e?.message || t('手工录入失败')
  } finally {
    busyId.value = null
  }
}

async function webhookSimulate() {
  busyId.value = -2
  msg.value = ''
  try {
    const r = await api.acquisitionWebhookSimulate({
      hotel_id: hotelStore.hotelId,
      binding_id: primaryBinding.value?.id,
      nickname: t('Webhook联调客人'),
      intent: 'high',
    })
    const tag = r?.updated ? t('（已更新）') : r?.duplicate ? t('（幂等重复）') : ''
    msg.value = `Webhook 联调成功 · 线索 #${r?.lead_id}${tag}`
    await load()
  } catch (e: any) {
    msg.value = e?.message || t('Webhook 联调失败')
  } finally {
    busyId.value = null
  }
}

async function copyWebhookUrl() {
  const url = primaryBinding.value?.url
  if (!url) {
    msg.value = t('暂无绑定 URL')
    return
  }
  try {
    await navigator.clipboard.writeText(url)
    msg.value = t('Webhook URL 已复制，可粘贴到聚光后台')
  } catch {
    msg.value = url
  }
}

async function mockIngest() {
  busyId.value = -1
  msg.value = ''
  try {
    const rows = await api.acquisitionMockIngest({
      hotel_id: hotelStore.hotelId,
      count: 3,
      channel: props.channel,
    })
    msg.value = `已模拟入库 ${rows.length} 条线索`
    await load()
  } catch (e: any) {
    msg.value = e?.message || t('入库失败')
  } finally {
    busyId.value = null
  }
}

async function claim(id: number) {
  busyId.value = id
  try {
    await api.acquisitionClaimLead(id, {})
    msg.value = `线索 #${id} 已认领，进入跟进`
    await load()
  } catch (e: any) {
    msg.value = e?.message || t('认领失败')
  } finally {
    busyId.value = null
  }
}

async function toPrivate(id: number) {
  busyId.value = id
  try {
    await api.acquisitionToPrivate(id, {})
    msg.value = `线索 #${id} 已进入私域`
    await load()
  } catch (e: any) {
    msg.value = e?.message || t('转入失败')
  } finally {
    busyId.value = null
  }
}

async function openConvert(l: any) {
  convertLead.value = l
  convertForm.guest_name = l.nickname || ''
  convertForm.phone = l.phone || ''
  convertForm.wechat = l.wechat || ''
  convertForm.room_type_id = ''
  convertForm.check_in = ''
  convertForm.check_out = ''
  convertForm.rooms = 1
  convertForm.adults = 1
  convertForm.unit_price = ''
  convertForm.remark = ''
  showConvertForm.value = true
  try {
    roomTypes.value = await api.listRoomTypes(hotelStore.hotelId)
    if (roomTypes.value.length && !convertForm.room_type_id) {
      convertForm.room_type_id = roomTypes.value[0].id
      convertForm.unit_price = roomTypes.value[0].base_price ?? ''
    }
  } catch {
    roomTypes.value = []
  }
}

function onRoomTypeChange() {
  const rt = roomTypes.value.find((x) => x.id === Number(convertForm.room_type_id))
  if (rt?.base_price != null) convertForm.unit_price = rt.base_price
}

async function submitConvert() {
  if (!convertLead.value) return
  busyId.value = convertLead.value.id
  msg.value = ''
  try {
    const r = await api.acquisitionConvertBooking(convertLead.value.id, {
      guest_name: convertForm.guest_name,
      phone: convertForm.phone,
      room_type_id: Number(convertForm.room_type_id),
      check_in: convertForm.check_in,
      check_out: convertForm.check_out,
      rooms: convertForm.rooms,
      adults: convertForm.adults,
      unit_price: convertForm.unit_price === '' ? undefined : Number(convertForm.unit_price),
      remark: convertForm.remark,
    })
    const ono = r?.order?.order_no || ''
    msg.value = r?.already ? `已有预订 ${ono}` : `已转预订 ${ono}，请到订单中心办理`
    showConvertForm.value = false
    convertLead.value = null
    await load()
  } catch (e: any) {
    msg.value = e?.message || t('转预订失败')
  } finally {
    busyId.value = null
  }
}

async function markArrived(id: number) {
  busyId.value = id
  try {
    await api.acquisitionMarkArrived(id, {})
    msg.value = `线索 #${id} 已标记到店`
    await load()
  } catch (e: any) {
    msg.value = e?.message || t('标记失败')
  } finally {
    busyId.value = null
  }
}

function openLead(l: any) {
  selectedLead.value = l
}

function goOrders() {
  router.push('/orders')
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
watch(() => props.channel, load)
</script>

<template>
  <div class="acq-loop" :class="{ simple }">
    <div class="acq-loop-head" v-if="!simple || view === 'full'">
      <div v-if="view === 'full'">
        <h3 class="title">{{ t('获客闭环 · 多租户 Webhook') }}</h3>
        <p class="sub">{{ board?.hint }}</p>
      </div>
      <div v-else-if="!simple" />
      <div class="head-actions">
        <button type="button" class="btn ghost" :disabled="busyId !== null" @click="load">
          {{ t('刷新') }}
        </button>
        <template v-if="view === 'full' || view === 'leads'">
          <button type="button" class="btn ghost" @click="showBindingForm = !showBindingForm">
            {{ t('绑定配置') }}
          </button>
          <button type="button" class="btn ghost" @click="showManualForm = !showManualForm">
            {{ t('手工录入') }}
          </button>
          <button
            v-if="!simple"
            type="button"
            class="btn ghost"
            :disabled="busyId !== null || !primaryBinding"
            @click="copyWebhookUrl"
          >
            {{ t('复制 URL') }}
          </button>
          <button
            v-if="!simple"
            type="button"
            class="btn ghost"
            :disabled="busyId !== null || !primaryBinding"
            @click="webhookSimulate"
          >
            {{ t('Webhook 联调') }}
          </button>
          <button
            v-if="!simple"
            type="button"
            class="btn primary"
            :disabled="busyId !== null"
            @click="mockIngest"
          >
            {{ t('Mock 入库') }}
          </button>
        </template>
        <button v-if="view === 'full'" type="button" class="btn ghost" @click="goOrders">
          {{ t('订单中心') }}
        </button>
      </div>
    </div>
    <div v-else-if="simple && view === 'leads'" class="acq-loop-head compact">
      <div class="head-actions">
        <button type="button" class="btn ghost" :disabled="busyId !== null" @click="load">
          {{ t('刷新') }}
        </button>
        <button type="button" class="btn ghost" @click="showManualForm = !showManualForm">
          {{ t('手工录入') }}
        </button>
        <button type="button" class="btn primary" @click="showBindingForm = !showBindingForm">
          {{ t('连接设置') }}
        </button>
      </div>
    </div>

    <p v-if="msg" class="toast">{{ msg }}</p>
    <p v-if="loading" class="muted">{{ t('加载中…') }}</p>

    <div v-if="showBindingForm && (view === 'full' || view === 'leads')" class="panel-form">
      <h4>
        {{
          isDouyin
            ? t('抖音来客 / OAuth 绑定')
            : props.channel === 'xiaohongshu'
              ? t('聚光 / 专业号绑定配置')
              : t('获客渠道绑定配置')
        }}
      </h4>
      <div class="form-grid">
        <label
          >{{ t('绑定名称')
          }}<input
            v-model="bindingForm.label"
            :placeholder="isDouyin ? t('如：西湖店来客主账户') : t('如：西湖店主账户')"
        /></label>
        <label
          >{{ isDouyin ? t('来客商家 ID') : t('广告账户 ID')
          }}<input
            v-model="bindingForm.xhs_ad_account_id"
            :placeholder="isDouyin ? 'life_account_id' : 'advertiser_id'"
        /></label>
        <label v-if="!isDouyin"
          >{{ t('专业号 ID')
          }}<input v-model="bindingForm.xhs_professional_id" :placeholder="t('可选')"
        /></label>
        <label v-if="!isDouyin"
          >{{ t('落地页 ID（逗号分隔）')
          }}<input v-model="bindingForm.xhs_page_ids" :placeholder="t('表单场景 page_id')"
        /></label>
        <label
          >{{ t('Webhook 验签 Token')
          }}<input
            v-model="bindingForm.webhook_secret"
            type="password"
            :placeholder="t('留空则不修改')"
        /></label>
      </div>
      <div class="form-actions">
        <button type="button" class="btn primary" :disabled="busyId !== null" @click="saveBinding">
          {{ t('保存绑定') }}
        </button>
        <button type="button" class="btn ghost" @click="showBindingForm = false">
          {{ t('取消') }}
        </button>
      </div>
    </div>

    <div v-if="showManualForm && (view === 'full' || view === 'leads')" class="panel-form">
      <h4>手工录入线索（{{ isDouyin ? t('直播/私信/本地推') : t('未投流 / 自然私信') }}）</h4>
      <div class="form-grid">
        <label>{{ t('昵称') }}<input v-model="manualForm.nickname" /></label>
        <label>{{ t('手机') }}<input v-model="manualForm.phone" /></label>
        <label>{{ t('微信') }}<input v-model="manualForm.wechat" /></label>
        <label
          >{{ isDouyin ? t('来源视频/直播') : t('来源笔记')
          }}<input v-model="manualForm.note_title"
        /></label>
        <label>{{ t('笔记链接') }}<input v-model="manualForm.source_note_url" /></label>
        <label
          >{{ t('意向') }}
          <select v-model="manualForm.intent">
            <option value="high">{{ t('高') }}</option>
            <option value="mid">{{ t('中') }}</option>
            <option value="low">{{ t('低') }}</option>
          </select>
        </label>
        <label class="span2">{{ t('备注') }}<input v-model="manualForm.remark" /></label>
      </div>
      <div class="form-actions">
        <button
          type="button"
          class="btn primary"
          :disabled="busyId !== null"
          @click="submitManualLead"
        >
          {{ t('提交线索') }}
        </button>
        <button type="button" class="btn ghost" @click="showManualForm = false">
          {{ t('取消') }}
        </button>
      </div>
    </div>

    <div v-if="primaryBinding && simple && view === 'leads' && showBindingForm" class="webhook-box">
      <h4>Webhook 地址（填到{{ isDouyin ? t('来客「线索推送」') : t('聚光「线索推送」') }}）</h4>
      <code class="webhook-url">{{ primaryBinding.url || primaryBinding.path }}</code>
      <div class="webhook-meta">
        <button type="button" class="btn sm ghost" @click="copyWebhookUrl">
          {{ t('复制 URL') }}
        </button>
        <button
          type="button"
          class="btn sm ghost"
          :disabled="busyId !== null || !primaryBinding"
          @click="webhookSimulate"
        >
          {{ t('Webhook 联调') }}
        </button>
      </div>
    </div>

    <div v-if="primaryBinding && !simple && view === 'full'" class="webhook-box">
      <h4>{{ t('本酒店 Webhook（填到聚光「线索推送」）') }}</h4>
      <code class="webhook-url">{{ primaryBinding.url || primaryBinding.path }}</code>
      <div class="webhook-meta">
        <span>广告账户：{{ primaryBinding.xhs_ad_account_id || '—' }}</span>
        <span>验签：{{ primaryBinding.webhook_secret_set ? t('已配置') : t('未配置') }}</span>
        <span>新线索：{{ metrics.new_leads ?? 0 }}</span>
        <span>Webhook 入库：{{ metrics.webhook_leads ?? 0 }}</span>
      </div>
    </div>

    <div v-if="webhookEvents.length && view === 'full' && !simple" class="webhook-events">
      <h4>{{ t('最近 Webhook 事件') }}</h4>
      <ul>
        <li v-for="e in webhookEvents" :key="e.id">
          #{{ e.id }} · {{ e.status }} · {{ e.external_event_id }}
          <span v-if="e.lead_id"> → 线索 #{{ e.lead_id }}</span>
        </li>
      </ul>
    </div>

    <div v-if="board && (view === 'full' || view === 'funnel')" class="funnel">
      <div v-for="s in funnelSteps" :key="s.stage" class="funnel-item">
        <div class="num">{{ s.count }}</div>
        <div class="lab">{{ s.label }}</div>
      </div>
      <div class="funnel-item metric">
        <div class="num">¥{{ metrics.booked_rev || 0 }}</div>
        <div class="lab">{{ t('预订金额') }}</div>
      </div>
      <div class="funnel-item metric">
        <div class="num">{{ metrics.roi != null ? metrics.roi + 'x' : '—' }}</div>
        <div class="lab">{{ t('闭环 ROI') }}</div>
      </div>
    </div>

    <div v-if="view === 'full' || view === 'leads'" class="leads">
      <h4>{{ t('线索列表') }}</h4>
      <table>
        <thead>
          <tr>
            <th>{{ t('客人') }}</th>
            <th>{{ t('类型') }}</th>
            <th>{{ t('联系') }}</th>
            <th>{{ t('归因') }}</th>
            <th>{{ t('阶段') }}</th>
            <th>{{ t('操作') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in leads" :key="l.id">
            <td>
              <div class="name">{{ l.nickname || '—' }}</div>
              <div class="id">#{{ l.id }} · {{ l.external_id }}</div>
            </td>
            <td>
              <span class="pill">{{ l.lead_type_label }}</span>
            </td>
            <td class="contact">
              <div v-if="l.phone">📱 {{ l.phone }}</div>
              <div v-if="l.wechat">💬 {{ l.wechat }}</div>
              <span v-if="!l.phone && !l.wechat" class="muted">—</span>
            </td>
            <td class="note">
              <div>{{ l.note_title || '—' }}</div>
              <div v-if="l.xhs_plan_id" class="id">计划 {{ l.xhs_plan_id }}</div>
              <a
                v-if="l.source_note_url"
                :href="l.source_note_url"
                target="_blank"
                rel="noopener"
                class="link"
                >{{ t('笔记链接') }}</a
              >
            </td>
            <td>
              <span class="stage">{{ l.stage_label }}</span>
            </td>
            <td class="ops">
              <button type="button" class="btn sm ghost" @click="openLead(l)">
                {{ t('详情') }}
              </button>
              <button
                v-if="l.stage === 'new'"
                type="button"
                class="btn sm"
                :disabled="busyId === l.id"
                @click="claim(l.id)"
              >
                {{ t('认领跟进') }}
              </button>
              <button
                v-if="l.stage === 'claimed'"
                type="button"
                class="btn sm"
                :disabled="busyId === l.id"
                @click="toPrivate(l.id)"
              >
                {{ t('进私域') }}
              </button>
              <button
                v-if="l.stage === 'private'"
                type="button"
                class="btn sm primary"
                :disabled="busyId === l.id"
                @click="openConvert(l)"
              >
                {{ t('转预订') }}
              </button>
              <button
                v-if="l.stage === 'booked'"
                type="button"
                class="btn sm"
                :disabled="busyId === l.id"
                @click="markArrived(l.id)"
              >
                {{ t('标记到店') }}
              </button>
              <button v-if="l.order_id" type="button" class="btn sm ghost" @click="goOrders">
                {{ t('查看订单') }}
              </button>
            </td>
          </tr>
          <tr v-if="!leads.length">
            <td colspan="6" class="muted">
              {{ t('暂无线索，可手工录入或等待渠道 Webhook 推送') }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="showConvertForm && convertLead"
      class="lead-drawer"
      @click.self="showConvertForm = false"
    >
      <div class="drawer-card convert-card">
        <h4>一键转预订 · 线索 #{{ convertLead.id }}</h4>
        <p class="convert-tip">
          {{ t('聚光 API 仅提供留资信息；房型、日期、房价须与客人确认后填写。') }}
        </p>
        <div class="form-grid">
          <label>{{ t('客人姓名') }}<input v-model="convertForm.guest_name" /></label>
          <label>{{ t('手机') }}<input v-model="convertForm.phone" /></label>
          <label
            >{{ t('微信') }}<input v-model="convertForm.wechat" readonly class="readonly"
          /></label>
          <label
            >{{ t('房型') }}
            <select v-model="convertForm.room_type_id" @change="onRoomTypeChange">
              <option v-for="rt in roomTypes" :key="rt.id" :value="rt.id">{{ rt.name }}</option>
            </select>
          </label>
          <label>{{ t('入住日') }}<input v-model="convertForm.check_in" type="date" /></label>
          <label>{{ t('离店日') }}<input v-model="convertForm.check_out" type="date" /></label>
          <label
            >{{ t('间数') }}<input v-model.number="convertForm.rooms" type="number" min="1"
          /></label>
          <label
            >{{ t('成人数') }}<input v-model.number="convertForm.adults" type="number" min="1"
          /></label>
          <label
            >{{ t('房价/晚')
            }}<input v-model="convertForm.unit_price" type="number" min="0" step="0.01"
          /></label>
          <label class="span2"
            >{{ t('备注')
            }}<input v-model="convertForm.remark" :placeholder="t('与客人确认的预订说明')"
          /></label>
        </div>
        <div class="form-actions">
          <button
            type="button"
            class="btn primary"
            :disabled="busyId !== null"
            @click="submitConvert"
          >
            {{ t('确认转预订') }}
          </button>
          <button type="button" class="btn ghost" @click="showConvertForm = false">
            {{ t('取消') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="selectedLead" class="lead-drawer" @click.self="selectedLead = null">
      <div class="drawer-card">
        <h4>线索 #{{ selectedLead.id }} 归因详情</h4>
        <dl>
          <dt>{{ t('昵称') }}</dt>
          <dd>{{ selectedLead.nickname || '—' }}</dd>
          <dt>{{ t('类型') }}</dt>
          <dd>{{ selectedLead.lead_type_label }}</dd>
          <dt>{{ t('手机 / 微信') }}</dt>
          <dd>{{ selectedLead.phone || '—' }} / {{ selectedLead.wechat || '—' }}</dd>
          <dt>{{ t('笔记') }}</dt>
          <dd>{{ selectedLead.note_title || '—' }}</dd>
          <dt>{{ t('计划 ID') }}</dt>
          <dd>{{ selectedLead.xhs_plan_id || '—' }}</dd>
          <dt>{{ t('创意 ID') }}</dt>
          <dd>{{ selectedLead.xhs_creative_id || '—' }}</dd>
          <dt>{{ t('单元 ID') }}</dt>
          <dd>{{ selectedLead.xhs_unit_id || '—' }}</dd>
          <dt>{{ t('推送类型') }}</dt>
          <dd>{{ selectedLead.payload_type || 'new' }}</dd>
          <dt>{{ t('阶段') }}</dt>
          <dd>{{ selectedLead.stage_label }}</dd>
          <dt>{{ t('备注') }}</dt>
          <dd>{{ selectedLead.remark || '—' }}</dd>
        </dl>
        <button type="button" class="btn ghost" @click="selectedLead = null">
          {{ t('关闭') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.acq-loop {
  border: 1px solid var(--outline-variant, #e2e5eb);
  border-radius: 12px;
  background: var(--surface-container-lowest, #fff);
  padding: 16px 18px;
  margin-bottom: 16px;
}
.acq-loop.simple {
  border: none;
  padding: 0;
  margin-bottom: 0;
  background: transparent;
}
.acq-loop-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
  margin-bottom: 12px;
}
.acq-loop-head.compact {
  justify-content: flex-end;
  margin-bottom: 12px;
}
.title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}
.sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--on-surface-variant, #5b616e);
}
.head-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.btn {
  border: 1px solid var(--outline-variant, #c9ced8);
  background: var(--surface, #fff);
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 0.15s,
    opacity 0.15s;
}
.btn:hover:not(:disabled) {
  background: var(--surface-container-low, #f5f6f8);
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn.primary {
  background: var(--primary, #1a56db);
  border-color: var(--primary, #1a56db);
  color: var(--on-primary, #fff);
}
.btn.primary:hover:not(:disabled) {
  opacity: 0.9;
  background: var(--primary, #1a56db);
}
.btn.ghost {
  background: transparent;
  color: var(--on-surface, #1f2329);
}
.btn.sm {
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 6px;
}
.acq-loop.simple .leads h4 {
  display: none;
}
.acq-loop.simple table {
  font-size: 13px;
}
.acq-loop.simple thead tr {
  background: var(--surface-container-low, #f5f6f8);
  color: var(--on-surface-variant, #5b616e);
}
.acq-loop.simple th {
  padding: 12px 10px;
  font-weight: 500;
  border-bottom: 1px solid var(--outline-variant, #e2e5eb);
}
.acq-loop.simple td {
  padding: 12px 10px;
  border-bottom: 1px solid color-mix(in srgb, var(--outline-variant, #e2e5eb) 50%, transparent);
}
.acq-loop.simple tbody tr:hover {
  background: var(--surface-container-lowest, #fafafa);
}
.acq-loop.simple .pill {
  background: color-mix(in srgb, var(--primary, #1a56db) 10%, transparent);
  color: var(--primary, #1a56db);
}
.acq-loop.simple .panel-form {
  background: var(--surface-container-low, #f8f9fb);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}
.acq-loop.simple .webhook-box {
  background: var(--surface-container-low, #f8f9fb);
  border-style: solid;
  border-radius: 12px;
  padding: 14px 16px;
}
.acq-loop.simple .funnel-item {
  background: var(--surface-container-lowest, #fff);
  border-radius: 12px;
  padding: 14px;
}
.toast {
  margin: 0 0 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #eef6ff;
  color: #1d4ed8;
  font-size: 13px;
}
.muted {
  color: var(--on-surface-variant, #5b616e);
  font-size: 13px;
}
.panel-form {
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid var(--outline-variant, #e2e5eb);
  border-radius: 10px;
  background: #fcfcfd;
}
.panel-form h4 {
  margin: 0 0 10px;
  font-size: 13px;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}
.form-grid label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #5b616e;
}
.form-grid label.span2 {
  grid-column: span 2;
}
.form-grid input,
.form-grid select {
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
}
.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
.webhook-box {
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 10px;
  background: #fafbff;
}
.webhook-box h4,
.webhook-events h4 {
  margin: 0 0 6px;
  font-size: 13px;
}
.webhook-url {
  display: block;
  font-size: 12px;
  word-break: break-all;
  padding: 6px 8px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid var(--outline-variant, #e2e5eb);
}
.webhook-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
}
.webhook-events {
  margin-bottom: 12px;
}
.webhook-events ul {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #5b616e;
}
.funnel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 8px;
  margin-bottom: 14px;
}
.funnel-item {
  border: 1px solid var(--outline-variant, #e2e5eb);
  border-radius: 10px;
  padding: 10px;
  background: var(--surface-container-low, #f5f6f8);
}
.funnel-item .num {
  font-size: 22px;
  font-weight: 700;
}
.funnel-item .lab {
  font-size: 12px;
  color: #5b616e;
  margin-top: 4px;
}
.leads h4 {
  margin: 0 0 8px;
  font-size: 14px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th,
td {
  text-align: left;
  padding: 8px 6px;
  border-bottom: 1px solid var(--outline-variant, #eef0f3);
  vertical-align: top;
}
.name {
  font-weight: 600;
}
.id {
  font-size: 11px;
  color: #5b616e;
}
.note {
  max-width: 200px;
}
.contact {
  font-size: 12px;
}
.link {
  font-size: 11px;
  color: #1d4ed8;
}
.pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: #f3f4f6;
}
.stage {
  font-weight: 600;
}
.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.lead-drawer {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.drawer-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  width: min(420px, 92vw);
  max-height: 80vh;
  overflow: auto;
}
.drawer-card h4 {
  margin: 0 0 12px;
}
.drawer-card dl {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 8px;
  font-size: 13px;
  margin: 0 0 16px;
}
.drawer-card dt {
  color: #5b616e;
}
.drawer-card dd {
  margin: 0;
}
.convert-card {
  width: min(520px, 94vw);
}
.convert-tip {
  font-size: 12px;
  color: #5b616e;
  margin: 0 0 12px;
  line-height: 1.5;
}
.readonly {
  background: #f3f4f6;
}
</style>
