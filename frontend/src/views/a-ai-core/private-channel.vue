<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
/**
 * 系统配置 · 私域通道（Extensions / messaging）
 * 主 IM（wecom/line/whatsapp/webhook）+ SMS/Email 兜底。
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { t } from '../../lib/i18n'
import { api } from '../../lib/api'
import { toast } from '../../lib/ui'
import SystemConfigNav from '../../components/SystemConfigNav.vue'
import ConfigSettingRow from '../../components/ConfigSettingRow.vue'
import { applyBranding, privateChannelVendor } from '../../lib/branding'

const router = useRouter()
const loading = ref(true)
const saving = ref(false)
const vendor = ref<'wecom' | 'line' | 'whatsapp' | 'webhook'>('wecom')
const fallback = ref<string[]>([])
const status = ref<any>(null)
const localeTick = ref(0)

const line = ref({
  enabled: false,
  channel_id: '',
  channel_secret_set: false,
  channel_access_token_set: false,
  channel_secret_display: '',
  channel_access_token_display: '',
})
const whatsapp = ref({
  enabled: false,
  phone_number_id: '',
  access_token_set: false,
  access_token_display: '',
})
const draft = ref({
  channel_id: '',
  channel_secret: '',
  channel_access_token: '',
  wa_phone_number_id: '',
  wa_access_token: '',
})

const vendors = [
  { value: 'wecom', label: '企业微信' },
  { value: 'line', label: 'LINE' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'webhook', label: 'Webhook' },
] as const

const fallbackOpts = [
  { value: 'sms', label: 'SMS' },
  { value: 'email', label: 'Email' },
] as const

function onLocale() {
  localeTick.value++
}

const statusLabel = computed(() => {
  localeTick.value
  const s = status.value?.status
  if (s === 'enabled' || s === 'verified') return t('已启用')
  if (s === 'pending_credentials') return t('待配置密钥')
  return t('未配置')
})

const activeVendorLabel = computed(() => {
  localeTick.value
  const code = String(status.value?.vendor || vendor.value || '')
  const hit = vendors.find((v) => v.value === code)
  return hit ? t(hit.label) : code
})

const regionLabel = computed(() => {
  localeTick.value
  if (status.value?.region_profile === 'cn') return t('中国深集成')
  if (status.value?.region_profile === 'intl') return t('国际组合')
  return ''
})

function apply(cfg: any) {
  vendor.value = (cfg.effective_vendor || cfg.vendor || 'wecom') as typeof vendor.value
  fallback.value = Array.isArray(cfg.fallback)
    ? cfg.fallback.map(String)
    : Array.isArray(cfg.status?.fallback)
      ? cfg.status.fallback.map(String)
      : []
  status.value = cfg.status || null
  const l = cfg.line || {}
  line.value = {
    enabled: !!l.enabled,
    channel_id: l.channel_id || '',
    channel_secret_set: !!l.channel_secret_set,
    channel_access_token_set: !!l.channel_access_token_set,
    channel_secret_display: l.channel_secret || '',
    channel_access_token_display: l.channel_access_token || '',
  }
  const w = cfg.whatsapp || {}
  whatsapp.value = {
    enabled: !!w.enabled,
    phone_number_id: w.phone_number_id || '',
    access_token_set: !!w.access_token_set,
    access_token_display: w.access_token || '',
  }
  draft.value = {
    channel_id: '',
    channel_secret: '',
    channel_access_token: '',
    wa_phone_number_id: '',
    wa_access_token: '',
  }
}

async function load() {
  loading.value = true
  try {
    const cfg = await api.privateChannelGet()
    apply(cfg)
  } catch (e: any) {
    toast(e?.message || t('加载失败'), false)
  } finally {
    loading.value = false
  }
}

function toggleFallback(key: string) {
  const set = new Set(fallback.value)
  if (set.has(key)) set.delete(key)
  else set.add(key)
  fallback.value = [...set]
}

async function saveVendor() {
  saving.value = true
  try {
    const cfg = await api.privateChannelSave({
      vendor: vendor.value,
      fallback: fallback.value,
    })
    apply(cfg)
    try {
      const branding = await api.branding()
      applyBranding(branding || {})
    } catch {
      /* ignore */
    }
    const label = vendors.find((v) => v.value === vendor.value)?.label || vendor.value
    toast(t('私域通道已切换为 {label}', { label: t(label) }))
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    saving.value = false
  }
}

async function saveLineField(
  field: 'channel_id' | 'channel_secret' | 'channel_access_token',
  value: string,
) {
  if (!value && field !== 'channel_id') {
    toast(t('请输入密钥'), false)
    return
  }
  saving.value = true
  try {
    const cfg = await api.privateChannelSave({
      vendor: 'line',
      line: { enabled: true, [field]: value },
    })
    apply(cfg)
    toast(t('已保存'))
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    saving.value = false
  }
}

async function saveWaField(field: 'phone_number_id' | 'access_token', value: string) {
  if (!value) {
    toast(t('请输入密钥'), false)
    return
  }
  saving.value = true
  try {
    const cfg = await api.privateChannelSave({
      vendor: 'whatsapp',
      whatsapp: { enabled: true, [field]: value },
    })
    apply(cfg)
    toast(t('已保存'))
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    saving.value = false
  }
}

function openWecomDeep() {
  router.push('/a-ai-core/wecom-integration')
}

onMounted(() => {
  window.addEventListener('fml:locale', onLocale)
  load()
})
onUnmounted(() => window.removeEventListener('fml:locale', onLocale))
</script>

<template>
  <main class="pc-page" :data-locale="localeTick">
    <SystemConfigNav />
    <div class="head">
      <h1>{{ t('私域通道') }}</h1>
    </div>

    <div v-if="loading" class="empty">{{ t('加载中…') }}</div>
    <template v-else>
      <section class="card">
        <div class="row-between">
          <h2>{{ t('当前通道') }}</h2>
          <span class="badge" :class="{ ok: status?.connected }">{{ statusLabel }}</span>
        </div>
        <p class="hint">
          {{ t('生效厂商') }}：
          <strong>{{ activeVendorLabel }}</strong>
          <template v-if="regionLabel"> · {{ regionLabel }}</template>
          <template v-if="status?.hint"> · {{ status.hint }}</template>
        </p>
        <div class="vendor-grid">
          <label
            v-for="v in vendors"
            :key="v.value"
            class="vendor-opt"
            :class="{ active: vendor === v.value }"
          >
            <input v-model="vendor" type="radio" :value="v.value" />
            <span>{{ t(v.label) }}</span>
          </label>
        </div>

        <h3 class="subh">{{ t('触达兜底') }}</h3>
        <p class="hint">
          {{ t('主 IM 未配置或仅 demo 时，可降级到 SMS / Email（骨架可接 Twilio / SMTP）。') }}
        </p>
        <div class="vendor-grid">
          <label
            v-for="f in fallbackOpts"
            :key="f.value"
            class="vendor-opt"
            :class="{ active: fallback.includes(f.value) }"
          >
            <input
              type="checkbox"
              :checked="fallback.includes(f.value)"
              @change="toggleFallback(f.value)"
            />
            <span>{{ t(f.label) }}</span>
          </label>
        </div>

        <div class="actions">
          <button type="button" class="btn primary" :disabled="saving" @click="saveVendor">
            {{ t('保存选型') }}
          </button>
        </div>
      </section>

      <section v-if="vendor === 'wecom'" class="card">
        <h2>{{ t('企业微信') }}</h2>
        <p class="hint">
          {{ t('企微 CorpID / Secret / 回调等专属配置请在接入页维护；此处只负责通道选型。') }}
        </p>
        <button type="button" class="btn" @click="openWecomDeep">
          {{ t('打开企微接入配置') }}
        </button>
      </section>

      <section v-else-if="vendor === 'line'" class="card">
        <h2>{{ t('LINE Messaging API') }}</h2>
        <p class="hint">
          {{ t('在') }}
          <a href="https://developers.line.biz/console/" target="_blank" rel="noopener"
            >LINE Developers</a
          >
          {{
            t(
              '创建 Channel，填入 Channel Access Token。未配密钥时以 demo 模式运行（看板可用、消息不上送）。',
            )
          }}
        </p>
        <div class="fields">
          <ConfigSettingRow
            :label="t('Channel ID')"
            :configured="!!line.channel_id"
            :display-value="line.channel_id"
            v-model="draft.channel_id"
            :saving="saving"
            @save="(v) => saveLineField('channel_id', v)"
          />
          <ConfigSettingRow
            :label="t('Channel Secret')"
            :configured="line.channel_secret_set"
            :display-value="line.channel_secret_display"
            sensitive
            v-model="draft.channel_secret"
            :saving="saving"
            @save="(v) => saveLineField('channel_secret', v)"
          />
          <ConfigSettingRow
            :label="t('Channel Access Token')"
            :configured="line.channel_access_token_set"
            :display-value="line.channel_access_token_display"
            sensitive
            v-model="draft.channel_access_token"
            :saving="saving"
            @save="(v) => saveLineField('channel_access_token', v)"
          />
        </div>
      </section>

      <section v-else-if="vendor === 'whatsapp'" class="card">
        <h2>{{ t('WhatsApp Cloud API') }}</h2>
        <p class="hint">
          {{ t('在') }}
          <a href="https://developers.facebook.com/" target="_blank" rel="noopener"
            >Meta for Developers</a
          >
          {{
            t(
              '创建 WhatsApp Business App，填入 Phone Number ID 与 Access Token。未配密钥时 demo 模式可用。',
            )
          }}
        </p>
        <div class="fields">
          <ConfigSettingRow
            :label="t('Phone Number ID')"
            :configured="!!whatsapp.phone_number_id"
            :display-value="whatsapp.phone_number_id"
            v-model="draft.wa_phone_number_id"
            :saving="saving"
            @save="(v) => saveWaField('phone_number_id', v)"
          />
          <ConfigSettingRow
            :label="t('Access Token')"
            :configured="whatsapp.access_token_set"
            :display-value="whatsapp.access_token_display"
            sensitive
            v-model="draft.wa_access_token"
            :saving="saving"
            @save="(v) => saveWaField('access_token', v)"
          />
        </div>
      </section>

      <section v-else class="card">
        <h2>{{ t('Webhook') }}</h2>
        <p class="hint">
          {{ t('事件回执通道：适合 ISV / 自建中间件订阅私域事件。无需腾讯、LINE 或 Meta 账号。') }}
        </p>
        <p class="hint">{{ t('当前运行时厂商') }}：{{ privateChannelVendor() || 'webhook' }}</p>
      </section>
    </template>
  </main>
</template>

<style scoped>
.pc-page {
  padding: 0 0 40px;
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}
.head {
  margin: 8px 0 16px;
}
.head h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}
.subh {
  margin: 8px 0 6px;
  font-size: 14px;
}
.empty {
  padding: 24px;
  color: var(--on-surface-variant, #5b616e);
}
.card {
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant, #c9ced8);
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 14px;
}
.card h2 {
  margin: 0 0 8px;
  font-size: 16px;
}
.row-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.hint {
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--on-surface-variant, #5b616e);
  line-height: 1.55;
}
.hint a {
  color: var(--primary, #005bbf);
}
.badge {
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f1f3f6;
  color: #5b616e;
}
.badge.ok {
  background: rgba(16, 140, 80, 0.12);
  color: #0d7a45;
}
.vendor-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}
.vendor-opt {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid var(--outline-variant, #c9ced8);
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
}
.vendor-opt.active {
  border-color: var(--primary, #005bbf);
  background: rgba(0, 91, 191, 0.08);
  color: var(--primary, #005bbf);
}
.actions {
  display: flex;
  gap: 8px;
}
.btn {
  border: 1px solid var(--outline-variant, #c9ced8);
  background: #fff;
  border-radius: 8px;
  padding: 8px 14px;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}
.btn.primary {
  background: var(--primary, #005bbf);
  border-color: var(--primary, #005bbf);
  color: #fff;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
