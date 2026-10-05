<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 扩展能力 · 地图配置（天地图 / 高德 / 百度 / Google / 手工）
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../../lib/api'
import { toast } from '../../lib/ui'
import SystemConfigNav from '../../components/SystemConfigNav.vue'
import ConfigSettingRow from '../../components/ConfigSettingRow.vue'

type FieldMeta = { key: string; label: string }
type ProviderMeta = {
  id: string
  label: string
  hint?: string
  docs_url?: string
  fields: FieldMeta[]
}

const FALLBACK_PROVIDERS: ProviderMeta[] = [
  {
    id: 'tianditu',
    label: '天地图',
    hint: '自然资源部公共服务底图，适合国内合规场景。',
    docs_url: 'https://cloudcenter.tianditu.gov.cn/',
    fields: [
      { key: 'tianditu_tk', label: '服务端 Key' },
      { key: 'tianditu_js_tk', label: '浏览器 JS Key' },
    ],
  },
  {
    id: 'gaode',
    label: '高德地图',
    hint: '国内 Web 服务 + JS API；周边酒店 POI 检索。',
    docs_url: 'https://console.amap.com/',
    fields: [
      { key: 'amap_web_key', label: 'Web 服务 Key' },
      { key: 'amap_js_key', label: 'JS API Key' },
      { key: 'amap_security_code', label: '安全密钥' },
    ],
  },
  {
    id: 'baidu',
    label: '百度地图',
    hint: '国内图商；地理编码使用服务端 AK，浏览器端可另配 JS AK。',
    docs_url: 'https://lbsyun.baidu.com/',
    fields: [
      { key: 'baidu_ak', label: '服务端 AK' },
      { key: 'baidu_js_ak', label: '浏览器 JS AK' },
    ],
  },
  {
    id: 'google',
    label: 'Google Maps',
    hint: '国际店常用。需启用 Maps JavaScript API / Geocoding API。',
    docs_url: 'https://console.cloud.google.com/google/maps-apis',
    fields: [{ key: 'google_api_key', label: 'API Key' }],
  },
  {
    id: 'noop',
    label: '手工坐标',
    hint: '不接图商，价格助手等场景请手工填写经纬度。',
    docs_url: '',
    fields: [],
  },
]

const loading = ref(true)
const savingKey = ref('')
const testing = ref(false)
const providers = ref<ProviderMeta[]>([...FALLBACK_PROVIDERS])
const activeProvider = ref('tianditu')
const secrets = ref<Record<string, { set: boolean; display: string }>>({})
const draft = ref<Record<string, string>>({})
const status = ref<any>(null)
const testResult = ref<any>(null)
const testAddress = ref('')
const localeTick = ref(0)

function sampleAddress() {
  return t('上海市黄浦区人民广场')
}

function onLocale() {
  localeTick.value++
  const zh = '上海市黄浦区人民广场'
  const en = "People's Square, Huangpu, Shanghai"
  if (!testAddress.value || testAddress.value === zh || testAddress.value === en) {
    testAddress.value = sampleAddress()
  }
  load()
}

const uiProviders = computed(() => {
  void localeTick.value
  return providers.value.map((p) => ({
    ...p,
    title: t(p.label),
    hintText: p.hint ? t(p.hint) : '',
    fieldRows: (p.fields || []).map((f) => ({ ...f, title: t(f.label) })),
  }))
})

const activeMeta = computed(() => providers.value.find((p) => p.id === activeProvider.value))

function applyCfg(cfg: any) {
  if (Array.isArray(cfg.providers) && cfg.providers.length) {
    providers.value = cfg.providers
  } else if (!providers.value.length) {
    providers.value = [...FALLBACK_PROVIDERS]
  }
  activeProvider.value = String(
    cfg.provider || cfg.status?.provider || activeProvider.value || 'tianditu',
  )
  const next: Record<string, { set: boolean; display: string }> = { ...secrets.value }
  const nextDraft: Record<string, string> = { ...draft.value }
  for (const p of providers.value) {
    for (const f of p.fields || []) {
      next[f.key] = {
        set: !!cfg[`${f.key}_set`],
        display: String(cfg[f.key] || ''),
      }
      nextDraft[f.key] = nextDraft[f.key] || ''
    }
  }
  secrets.value = next
  draft.value = nextDraft
  status.value = cfg.status || status.value
}

async function load() {
  loading.value = true
  try {
    const cfg = await api.mapConfig()
    applyCfg(cfg)
  } catch (e: any) {
    toast(e?.message || t('加载失败'), false)
  } finally {
    loading.value = false
  }
}

async function savePayload(payload: Record<string, unknown>) {
  const cfg = await api.mapConfigSave({ enabled: true, provider: activeProvider.value, ...payload })
  applyCfg(cfg)
  return cfg
}

async function selectProvider(id: string) {
  if (id === activeProvider.value) return
  activeProvider.value = id
  savingKey.value = 'provider'
  try {
    await savePayload({ provider: id })
    toast(t('已切换为 {name}', { name: String(activeMeta.value?.label || id) }))
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    savingKey.value = ''
  }
}

async function saveField(field: string, value: string) {
  if (!value) {
    toast(secrets.value[field]?.set ? t('请输入新密钥') : t('请输入密钥'), false)
    return
  }
  savingKey.value = field
  try {
    await savePayload({ [field]: value })
    draft.value[field] = ''
    toast(t('已保存'))
  } catch (e: any) {
    toast(e?.message || t('保存失败'), false)
  } finally {
    savingKey.value = ''
  }
}

async function testGeocode() {
  testing.value = true
  testResult.value = null
  try {
    const r = await api.mapConfigTest({ address: testAddress.value })
    testResult.value = r
    status.value = r.status || status.value
    toast(r.ok ? t('解析成功') : r.error || t('解析失败'), !!r.ok)
  } catch (e: any) {
    toast(e?.message || t('测试失败'), false)
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  window.addEventListener('fml:locale', onLocale)
  testAddress.value = sampleAddress()
  load()
})
onUnmounted(() => window.removeEventListener('fml:locale', onLocale))
</script>

<template>
  <main class="map-page">
    <SystemConfigNav />
    <div class="head">
      <h1>{{ t('地图配置') }}</h1>
    </div>

    <div v-if="loading" class="empty">{{ t('加载中…') }}</div>
    <template v-else>
      <section class="card">
        <h2>{{ t('地图服务商') }}</h2>
        <div class="provider-list">
          <div
            v-for="p in uiProviders"
            :key="p.id"
            class="provider-card"
            :class="{ on: activeProvider === p.id }"
            role="button"
            tabindex="0"
            @click="selectProvider(p.id)"
            @keydown.enter.prevent="selectProvider(p.id)"
            @keydown.space.prevent="selectProvider(p.id)"
          >
            <div class="provider-card-head">
              <input
                type="radio"
                name="map-provider"
                :value="p.id"
                :checked="activeProvider === p.id"
                tabindex="-1"
                @click.stop
                @change="selectProvider(p.id)"
              />
              <div class="provider-card-title">
                <span class="provider-name">{{ p.title }}</span>
                <span v-if="activeProvider === p.id" class="active-pill">{{ t('当前使用') }}</span>
              </div>
            </div>
            <p v-if="p.hintText" class="provider-hint">{{ p.hintText }}</p>
            <p v-if="p.docs_url && activeProvider === p.id" class="provider-hint">
              <a :href="p.docs_url" target="_blank" rel="noopener" @click.stop>{{
                t('打开密钥申请页')
              }}</a>
            </p>

            <div
              v-if="activeProvider === p.id && p.fieldRows.length"
              class="provider-fields"
              @click.stop
            >
              <ConfigSettingRow
                v-for="f in p.fieldRows"
                :key="f.key"
                :label="f.title"
                :configured="!!secrets[f.key]?.set"
                :display-value="secrets[f.key]?.display || ''"
                sensitive
                v-model="draft[f.key]"
                :saving="savingKey === f.key"
                @save="(v) => saveField(f.key, v)"
              />
            </div>
          </div>
        </div>
      </section>

      <section class="card">
        <h2>{{ t('连通性测试') }}</h2>
        <div class="test-row">
          <input v-model="testAddress" type="text" :placeholder="t('试解析地址')" />
          <button class="btn-ghost" type="button" :disabled="testing" @click="testGeocode">
            {{ testing ? t('测试中…') : t('试解析') }}
          </button>
        </div>
        <pre v-if="testResult" class="test-out">{{ JSON.stringify(testResult, null, 2) }}</pre>
      </section>
    </template>
  </main>
</template>

<style scoped>
.map-page {
  min-height: 100%;
  padding: 24px 20px 32px;
  background: var(--surface-container-lowest, #fff);
  max-width: none;
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.head h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
}
.card {
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  padding: 18px 20px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
  box-sizing: border-box;
}
.card h2 {
  margin: 0;
  font-size: 16px;
}
.provider-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.provider-card {
  display: block;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 10px;
  padding: 12px 14px;
  background: #fff;
  cursor: pointer;
}
.provider-card.on {
  border-color: var(--primary, #005bbf);
  background: color-mix(in srgb, var(--primary, #005bbf) 5%, #fff);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--primary, #005bbf) 35%, transparent);
}
.provider-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.provider-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.provider-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--on-surface);
}
.active-pill {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--primary, #005bbf);
  color: #fff;
}
.provider-hint {
  margin: 6px 0 0 26px;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.provider-hint a {
  color: var(--primary, #005bbf);
}
.provider-fields {
  margin: 12px 0 0 26px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.btn-ghost {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--outline, #727785);
  background: transparent;
}
.test-row {
  display: flex;
  gap: 8px;
}
.test-row input {
  flex: 1;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
  font-size: 14px;
}
.test-out {
  margin: 0;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 12px;
  overflow: auto;
  max-height: 240px;
}
.empty {
  padding: 40px;
  text-align: center;
  color: #5b616e;
}
</style>
