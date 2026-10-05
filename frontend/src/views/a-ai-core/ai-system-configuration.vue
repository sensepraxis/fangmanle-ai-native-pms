<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '../../lib/api'
import SystemConfigNav from '../../components/SystemConfigNav.vue'
import ConfigSettingRow from '../../components/ConfigSettingRow.vue'

type ProviderMeta = {
  id: string
  label: string
  kind?: string
  needs_api_key?: boolean
  default_base_url?: string
  default_model?: string
  example_model?: string
  example_base_url?: string
  example_api_key?: string
  hint?: string
  docs_url?: string
}

type ProfileForm = {
  base_url: string
  model: string
  api_key: string
  api_key_set?: boolean
  api_key_display?: string
}

const providers = ref<ProviderMeta[]>([])
const activeProvider = ref('ollama')
const systemPrompt = ref('')
const temperature = ref(0.7)
const maxTokens = ref(2048)
const timeoutSec = ref(120)
const profiles = ref<Record<string, ProfileForm>>({})
const fieldDraft = ref<Record<string, { model: string; base_url: string; api_key: string }>>({})

const loading = ref(true)
const saving = ref(false)
const savingKey = ref('')
const testing = ref(false)
const toast = ref('')
const testResult = ref<any>(null)
const testError = ref('')
const localeTick = ref(0)

const activeMeta = computed(() => providers.value.find((p) => p.id === activeProvider.value))

const uiProviders = computed(() => {
  void localeTick.value
  return providers.value.map((p) => ({
    ...p,
    title: t(p.label),
    hintText: p.hint ? t(p.hint) : '',
  }))
})

function onLocale() {
  localeTick.value++
  load()
}

function ensureDraft(id: string) {
  if (!fieldDraft.value[id]) fieldDraft.value[id] = { model: '', base_url: '', api_key: '' }
}

function ensureProfile(id: string, seed?: Partial<ProfileForm>, meta?: ProviderMeta) {
  if (!profiles.value[id]) {
    profiles.value[id] = {
      base_url: seed?.base_url || meta?.default_base_url || '',
      model: seed?.model || meta?.default_model || '',
      api_key: '',
      api_key_set: !!seed?.api_key_set,
      api_key_display: seed?.api_key_display || '',
    }
  }
  ensureDraft(id)
}

function selectProvider(id: string) {
  activeProvider.value = id
  const meta = providers.value.find((p) => p.id === id)
  ensureProfile(id, undefined, meta)
}

async function load() {
  loading.value = true
  testError.value = ''
  try {
    const [ps, cfg] = await Promise.all([api.llmProviders(), api.llmConfig()])
    providers.value = ps || []
    activeProvider.value = cfg.provider || 'ollama'
    systemPrompt.value = cfg.system_prompt || ''
    temperature.value = cfg.temperature ?? 0.7
    maxTokens.value = cfg.max_tokens ?? 2048
    timeoutSec.value = cfg.timeout_sec ?? 120

    const next: Record<string, ProfileForm> = {}
    for (const p of providers.value) {
      const saved = cfg.profiles?.[p.id] || {}
      next[p.id] = {
        base_url: saved.base_url || p.default_base_url || '',
        model: saved.model || p.default_model || '',
        api_key: '',
        api_key_set: !!(saved.api_key_set ?? cfg.profile_api_key_set?.[p.id]),
        api_key_display: String(saved.api_key || ''),
      }
      fieldDraft.value[p.id] = { model: '', base_url: '', api_key: '' }
    }
    if (!cfg.profiles && next[activeProvider.value]) {
      next[activeProvider.value] = {
        base_url: cfg.base_url || next[activeProvider.value].base_url,
        model: cfg.model || next[activeProvider.value].model,
        api_key: '',
        api_key_set: !!cfg.api_key_set,
        api_key_display: String(cfg.api_key || ''),
      }
    }
    profiles.value = next
    ensureProfile(activeProvider.value)
  } catch (e: any) {
    testError.value = e?.message || t('加载失败')
  } finally {
    loading.value = false
  }
}

async function save(patch?: {
  providerId: string
  field: 'model' | 'base_url' | 'api_key'
  value: string
}) {
  saving.value = true
  if (patch) savingKey.value = `${patch.providerId}:${patch.field}`
  toast.value = ''
  testError.value = ''
  try {
    const profilesPayload: Record<string, Record<string, string>> = {}
    for (const p of providers.value) {
      const pf = profiles.value[p.id]
      if (!pf) continue
      const row: Record<string, string> = {
        base_url: pf.base_url,
        model: pf.model,
      }
      if (patch?.providerId === p.id) {
        if (patch.field === 'base_url') row.base_url = patch.value
        if (patch.field === 'model') row.model = patch.value
        if (patch.field === 'api_key') row.api_key = patch.value
      }
      profilesPayload[p.id] = row
    }
    const saved = await api.saveLlmConfig({
      enabled: true,
      provider: activeProvider.value,
      system_prompt: systemPrompt.value,
      temperature: temperature.value,
      max_tokens: maxTokens.value,
      timeout_sec: timeoutSec.value,
      profiles: profilesPayload,
    })
    for (const p of providers.value) {
      const pf = profiles.value[p.id]
      if (!pf) continue
      const sp = saved.profiles?.[p.id] || {}
      pf.base_url = sp.base_url || pf.base_url
      pf.model = sp.model || pf.model
      pf.api_key = ''
      pf.api_key_set = !!(sp.api_key_set ?? saved.profile_api_key_set?.[p.id])
      pf.api_key_display = String(sp.api_key || '')
      fieldDraft.value[p.id] = { model: '', base_url: '', api_key: '' }
    }
    toast.value = t('已保存 · {name}', {
      name: String(activeMeta.value?.label || activeProvider.value),
    })
  } catch (e: any) {
    testError.value = e?.message || t('保存失败')
  } finally {
    saving.value = false
    savingKey.value = ''
  }
}

async function saveField(
  providerId: string,
  field: 'model' | 'base_url' | 'api_key',
  value: string,
) {
  if (!value) {
    testError.value = t('请填写后再保存')
    return
  }
  await save({ providerId, field, value })
}

async function testConn() {
  testing.value = true
  testError.value = ''
  testResult.value = null
  try {
    await save()
    if (testError.value) return
    testResult.value = await api.testLlmConfig()
    toast.value = t('LLM 连接测试成功')
  } catch (e: any) {
    testError.value = e?.message || t('连接测试失败')
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  window.addEventListener('fml:locale', onLocale)
  load()
})
onUnmounted(() => window.removeEventListener('fml:locale', onLocale))
</script>

<template>
  <div class="page">
    <SystemConfigNav />
    <header class="sys-head">
      <div>
        <h1 class="sys-title">{{ t('大语言模型') }}</h1>
      </div>
    </header>

    <div v-if="loading" class="text-sm text-on-surface-variant">{{ t('加载配置…') }}</div>

    <template v-else>
      <section class="llm-card">
        <div class="llm-head">
          <h2 class="card-title">
            <span class="material-symbols-outlined text-tertiary">psychology</span>
            {{ t('大语言模型 (LLM)') }}
          </h2>
        </div>

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
                name="llm-provider"
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

            <div v-if="activeProvider === p.id" class="provider-fields" @click.stop>
              <ConfigSettingRow
                :label="t('模型名称')"
                :configured="!!profiles[p.id]?.model"
                :display-value="profiles[p.id]?.model || ''"
                v-model="fieldDraft[p.id].model"
                :saving="savingKey === `${p.id}:model`"
                @save="(v) => saveField(p.id, 'model', v)"
              />
              <ConfigSettingRow
                :label="t('服务地址')"
                :configured="!!profiles[p.id]?.base_url"
                :display-value="profiles[p.id]?.base_url || ''"
                v-model="fieldDraft[p.id].base_url"
                :saving="savingKey === `${p.id}:base_url`"
                @save="(v) => saveField(p.id, 'base_url', v)"
              />
              <ConfigSettingRow
                v-if="p.needs_api_key"
                label="API Key"
                :configured="!!profiles[p.id]?.api_key_set"
                :display-value="profiles[p.id]?.api_key_display || ''"
                sensitive
                v-model="fieldDraft[p.id].api_key"
                :saving="savingKey === `${p.id}:api_key`"
                @save="(v) => saveField(p.id, 'api_key', v)"
              />
            </div>
          </div>
        </div>

        <label class="prompt-label">
          <span>{{ t('系统提示词（全局）') }}</span>
          <textarea v-model="systemPrompt" rows="3" />
          <button
            type="button"
            class="btn-primary"
            style="margin-top: 8px; align-self: flex-start"
            :disabled="saving"
            @click="save()"
          >
            {{ t('保存') }}
          </button>
        </label>

        <div v-if="testResult" class="test-ok">
          <div class="font-semibold text-sm">
            {{
              t('测试通过 · {provider} / {model}', {
                provider: testResult.provider,
                model: testResult.model,
              })
            }}
          </div>
          <div v-if="testResult.sample_reply" class="test-sample">
            {{ testResult.sample_reply }}
          </div>
        </div>
        <p v-if="testError" class="test-err">{{ testError }}</p>
        <p v-if="toast" class="toast-msg">{{ toast }}</p>
        <div class="llm-actions">
          <button type="button" class="btn-ghost" :disabled="testing || saving" @click="testConn">
            {{ testing ? t('测试中…') : t('测试当前模型') }}
          </button>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
  padding: 24px 20px 32px;
  width: 100%;
  max-width: none;
  margin: 0;
  box-sizing: border-box;
  background: #fff;
}
.sys-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.sys-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
}
.llm-card {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  padding: 20px 22px;
}
.llm-head {
  margin-bottom: 16px;
}
.card-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--on-surface);
  display: flex;
  align-items: center;
  gap: 8px;
}
.provider-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
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
.provider-fields {
  margin: 12px 0 0 26px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 720px;
}
.prompt-label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.prompt-label textarea {
  padding: 9px 11px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
  color: var(--on-surface);
  font-family: inherit;
}
.field-eg {
  margin: 0;
  font-style: normal;
  font-size: 11px;
  color: var(--outline, #7b8794);
  line-height: 1.4;
}
.prompt-label {
  margin-bottom: 4px;
}
.llm-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 16px;
}
.btn-ghost,
.btn-primary {
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
}
.btn-ghost {
  border: 1px solid var(--outline-variant, #c1c6d6);
  background: #fff;
}
.btn-primary {
  border: 1px solid var(--primary, #005bbf);
  background: var(--primary, #005bbf);
  color: #fff;
}
.btn-ghost:disabled,
.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.test-ok {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #ecfdf3;
  color: #027a48;
  border: 1px solid #a6f4c5;
}
.test-sample {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.9;
}
.test-err {
  margin: 10px 0 0;
  font-size: 12px;
  color: #b91c1c;
}
.toast-msg {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--primary, #005bbf);
}
@media (max-width: 720px) {
  .provider-fields {
    margin-left: 0;
  }
  .provider-hint {
    margin-left: 0;
  }
}
</style>
