<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 系统配置 · 企业微信接入（接入层）
 * 密钥仅在此维护并落库；营销获客只读状态，不展示 Secret。
 */
import { computed, onMounted, ref } from 'vue'
import { api } from '../../lib/api'
import SystemConfigNav from '../../components/SystemConfigNav.vue'
import ConfigSettingRow from '../../components/ConfigSettingRow.vue'

const CALLBACK_SUFFIX = '/api/v1/wecom/callback'

const loading = ref(true)
const savingKey = ref('')
const testing = ref(false)
const toast = ref('')
const error = ref('')
const testResult = ref<any>(null)

/** 库中展示态（敏感字段为掩码） */
const stored = ref({
  status: 'unconfigured',
  enabled: false,
  corp_id: '',
  agent_id: '',
  follow_userid: '',
  public_base_url: '',
  app_secret_display: '',
  callback_token_display: '',
  callback_aes_key_display: '',
  app_secret_set: false,
  callback_token_set: false,
  callback_aes_key_set: false,
})

const draft = ref({
  corp_id: '',
  agent_id: '',
  follow_userid: '',
  public_base_url: '',
  app_secret: '',
  callback_token: '',
  callback_aes_key: '',
  callback_url: '',
})

const busy = computed(() => !!savingKey.value || testing.value)

const callbackUrlDisplay = computed(() => {
  const b = (stored.value.public_base_url || '').replace(/\/$/, '')
  return b ? `${b}${CALLBACK_SUFFIX}` : ''
})

const statusLabel = computed(() => {
  const s = stored.value.status
  if (s === 'enabled') return t('已启用')
  if (s === 'verified') return t('已校验')
  return t('未配置')
})

const statusClass = computed(() => {
  const s = stored.value.status
  if (s === 'enabled') return 'enabled'
  if (s === 'verified') return 'verified'
  return ''
})

function flash(msg: string) {
  toast.value = msg
  window.setTimeout(() => {
    if (toast.value === msg) toast.value = ''
  }, 2800)
}

function applyCfg(w: any) {
  stored.value = {
    status: w.status || (w.enabled ? 'enabled' : 'unconfigured'),
    enabled: !!w.enabled,
    corp_id: w.corp_id || '',
    agent_id: w.agent_id || '',
    follow_userid: w.follow_userid || '',
    public_base_url: w.public_base_url || '',
    app_secret_display: w.app_secret || '',
    callback_token_display: w.callback_token || '',
    callback_aes_key_display: w.callback_aes_key || '',
    app_secret_set: !!w.app_secret_set,
    callback_token_set: !!w.callback_token_set,
    callback_aes_key_set: !!w.callback_aes_key_set,
  }
  draft.value = {
    corp_id: '',
    agent_id: '',
    follow_userid: '',
    public_base_url: '',
    app_secret: '',
    callback_token: '',
    callback_aes_key: '',
    callback_url: '',
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    applyCfg((await api.wecomConfig()) || {})
  } catch (e: any) {
    error.value = e?.message || t('加载失败')
  } finally {
    loading.value = false
  }
}

function basePayload(): Record<string, unknown> {
  return {
    owner_type: 'hotel_tenant',
    enabled: stored.value.enabled,
    corp_id: stored.value.corp_id,
    agent_id: stored.value.agent_id,
    follow_userid: stored.value.follow_userid,
    public_base_url: stored.value.public_base_url,
  }
}

async function saveField(
  key:
    | 'corp_id'
    | 'agent_id'
    | 'follow_userid'
    | 'public_base_url'
    | 'app_secret'
    | 'callback_token'
    | 'callback_aes_key'
    | 'callback_url',
  value: string,
) {
  if (!value) {
    error.value = t('请填写后再保存')
    return
  }
  savingKey.value = key
  error.value = ''
  try {
    const payload = basePayload()
    if (key === 'callback_url') {
      let u = value.replace(/\/$/, '')
      if (u.endsWith(CALLBACK_SUFFIX)) u = u.slice(0, -CALLBACK_SUFFIX.length)
      payload.public_base_url = u.replace(/\/$/, '')
      payload.callback_url = value
    } else {
      payload[key] = value
    }
    const saved = await api.saveWecomConfig(payload)
    applyCfg(saved)
    flash(t('已保存'))
  } catch (e: any) {
    error.value = e?.message || t('保存失败')
  } finally {
    savingKey.value = ''
  }
}

async function toggleEnabled() {
  savingKey.value = 'enabled'
  error.value = ''
  try {
    const payload = { ...basePayload(), enabled: !stored.value.enabled }
    const saved = await api.saveWecomConfig(payload)
    applyCfg(saved)
    flash(saved.enabled ? t('已启用接入') : t('已关闭接入'))
  } catch (e: any) {
    error.value = e?.message || t('保存失败')
  } finally {
    savingKey.value = ''
  }
}

async function testConn() {
  testing.value = true
  error.value = ''
  testResult.value = null
  try {
    testResult.value = await api.testWecomConfig()
    stored.value.status = 'enabled'
    stored.value.enabled = true
    flash(t('连通性校验通过 · 已启用'))
  } catch (e: any) {
    error.value = e?.message || t('连通性校验失败')
  } finally {
    testing.value = false
  }
}

function exportJson() {
  const safe = {
    status: stored.value.status,
    enabled: stored.value.enabled,
    corp_id: stored.value.corp_id,
    agent_id: stored.value.agent_id,
    follow_userid: stored.value.follow_userid,
    public_base_url: stored.value.public_base_url,
    callback_url: callbackUrlDisplay.value,
  }
  const blob = new Blob([JSON.stringify(safe, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `wecom-integration-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(a.href)
  flash(t('已导出配置 JSON（不含密钥）'))
}

async function copyCallback() {
  try {
    await navigator.clipboard.writeText(callbackUrlDisplay.value)
    flash(t('回调 URL 已复制'))
  } catch {
    flash(t('复制失败，请手动选中'))
  }
}

onMounted(load)
</script>

<template>
  <main class="wc-page">
    <div class="wc-wrap">
      <SystemConfigNav />

      <div class="wc-head">
        <div>
          <h1 class="wc-title">{{ t('企业微信接入') }}</h1>
          <p v-if="error && loading" class="wc-err">{{ error }}</p>
        </div>
        <span class="status" :class="statusClass">
          <span class="dot" />
          {{ statusLabel }}</span
        >
      </div>

      <div v-if="loading" class="muted">{{ t('加载配置…') }}</div>

      <template v-else>
        <div class="banner">
          <div class="ic">!</div>
          <div class="tx">
            <b>{{ t('接入层红线：') }}</b
            >{{ t('企业微信密钥（应用 Secret / Token / EncodingAESKey）') }}
            <b>{{ t('仅在此处、由酒店维护') }}</b
            >{{
              t(
                '，以密文落库，绝不出现在营销获客模块与任何前端日志。 回调需先验签后解密，防伪造注入。',
              )
            }}
          </div>
        </div>

        <section class="wc-card">
          <div class="card-head">
            <h2>
              <span class="material-symbols-outlined ico">hub</span>
              {{ t('企业微信接入配置') }}
            </h2>
          </div>

          <div class="form-rows">
            <ConfigSettingRow
              :label="t('企业 ID')"
              :configured="!!stored.corp_id"
              :display-value="stored.corp_id"
              v-model="draft.corp_id"
              :saving="savingKey === 'corp_id'"
              @save="(v) => saveField('corp_id', v)"
            />
            <ConfigSettingRow
              :label="t('应用 Secret')"
              :configured="stored.app_secret_set"
              :display-value="stored.app_secret_display"
              sensitive
              v-model="draft.app_secret"
              :saving="savingKey === 'app_secret'"
              @save="(v) => saveField('app_secret', v)"
            />
            <ConfigSettingRow
              :label="t('应用 AgentId')"
              :configured="!!stored.agent_id"
              :display-value="stored.agent_id"
              v-model="draft.agent_id"
              :saving="savingKey === 'agent_id'"
              @save="(v) => saveField('agent_id', v)"
            />
            <ConfigSettingRow
              :label="t('回调 Token')"
              :configured="stored.callback_token_set"
              :display-value="stored.callback_token_display"
              sensitive
              v-model="draft.callback_token"
              :saving="savingKey === 'callback_token'"
              @save="(v) => saveField('callback_token', v)"
            />
            <ConfigSettingRow
              label="EncodingAESKey"
              :configured="stored.callback_aes_key_set"
              :display-value="stored.callback_aes_key_display"
              sensitive
              v-model="draft.callback_aes_key"
              :saving="savingKey === 'callback_aes_key'"
              @save="(v) => saveField('callback_aes_key', v)"
            />
            <ConfigSettingRow
              :label="t('回调接收 URL')"
              :configured="!!callbackUrlDisplay"
              :display-value="callbackUrlDisplay"
              input-type="url"
              v-model="draft.callback_url"
              :saving="savingKey === 'callback_url'"
              :hint="t('在企业微信后台「接收事件服务器」填写，需公网 HTTPS。')"
              @save="(v) => saveField('callback_url', v)"
            />
            <ConfigSettingRow
              :label="t('默认跟进人')"
              :configured="!!stored.follow_userid"
              :display-value="stored.follow_userid"
              v-model="draft.follow_userid"
              :saving="savingKey === 'follow_userid'"
              @save="(v) => saveField('follow_userid', v)"
            />

            <div class="cfg-enable">
              <div class="cfg-label">{{ t('启用接入') }}</div>
              <div class="cfg-enable-body">
                <span class="cfg-value">{{ stored.enabled ? t('已开启') : t('已关闭') }}</span>
                <button type="button" class="btn-primary" :disabled="busy" @click="toggleEnabled">
                  {{ stored.enabled ? t('关闭') : t('开启') }}
                </button>
                <button
                  v-if="callbackUrlDisplay"
                  type="button"
                  class="btn-ghost"
                  @click="copyCallback"
                >
                  {{ t('复制回调 URL') }}
                </button>
              </div>
            </div>
          </div>

          <div v-if="testResult" class="ok-box">
            {{ t('连通成功') }}
            <template v-if="testResult.follow_userid"> · {{ testResult.follow_userid }}</template>
            <template v-if="testResult.external_contact_count != null">
              · {{ t('外部客户') }} {{ testResult.external_contact_count }} {{ t('人') }}</template
            >
          </div>
          <p v-if="error" class="wc-err">{{ error }}</p>
          <p v-if="toast" class="wc-toast">{{ toast }}</p>

          <div class="actions">
            <button type="button" class="btn-ghost" :disabled="busy" @click="testConn">
              {{ testing ? t('校验中…') : t('校验连通性') }}
            </button>
            <button type="button" class="btn-ghost" :disabled="busy" @click="exportJson">
              {{ t('导出 JSON') }}
            </button>
          </div>
        </section>
      </template>
    </div>

    <div class="toast" :class="{ show: !!toast }">{{ toast }}</div>
  </main>
</template>

<style scoped>
.wc-page {
  min-height: 100%;
  padding: 24px 20px 32px;
  background: var(--surface-container-lowest, #fff);
}
.wc-wrap {
  width: 100%;
  max-width: none;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.wc-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.wc-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
}
.wc-err {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--error, #ba1a1a);
}
.status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  background: var(--surface-container-low, #f2f4f5);
  color: var(--on-surface-variant, #5b616e);
}
.status .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}
.status.enabled {
  background: #eafaf0;
  border-color: #a7e3b8;
  color: #16a34a;
}
.status.enabled .dot {
  background: #16a34a;
}
.status.verified {
  background: #fff6e6;
  border-color: #f0d4a0;
  color: #d97706;
}
.status.verified .dot {
  background: #d97706;
}
.banner {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: #fdecec;
  border: 1px solid #f5b5b5;
  border-radius: 12px;
  padding: 14px 16px;
}
.banner .ic {
  flex: 0 0 22px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #dc2626;
  color: #fff;
  text-align: center;
  line-height: 22px;
  font-weight: 700;
  font-size: 13px;
}
.banner .tx {
  font-size: 13px;
  color: #7f1d1d;
  line-height: 1.55;
}
.banner .tx b {
  color: #dc2626;
}
.wc-card {
  background: #fff;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  padding: 20px 24px;
}
.card-head h2 {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--on-surface, #1f2329);
}
.card-head .ico {
  color: var(--primary, #005bbf);
  font-size: 22px;
}
.form-rows {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.cfg-enable {
  display: grid;
  grid-template-columns: minmax(120px, 180px) 1fr;
  gap: 10px 16px;
  align-items: center;
}
.cfg-enable .cfg-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
}
.cfg-enable-body {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.cfg-enable .cfg-value {
  padding: 8px 12px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  background: #f8fafc;
  font-size: 14px;
  min-width: 100px;
}
.wc-toast {
  margin: 8px 0 0;
  font-size: 13px;
  color: #047857;
}
.form {
  display: grid;
  grid-template-columns: 168px 1fr;
  gap: 14px 16px;
  align-items: start;
}
.form > label {
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
  padding-top: 9px;
}
.req {
  color: var(--error, #ba1a1a);
}
.ctl input[type='text'],
.ctl input[type='url'],
.ctl input[type='password'] {
  width: 100%;
  box-sizing: border-box;
  padding: 9px 11px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
  color: var(--on-surface, #1f2329);
}
.ctl input:focus {
  outline: none;
  border-color: var(--primary, #005bbf);
  box-shadow: 0 0 0 3px rgba(0, 91, 191, 0.12);
}
.secret {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  letter-spacing: 1px;
}
.secret-row {
  display: flex;
  align-items: stretch;
  gap: 0;
  position: relative;
}
.secret-row input {
  flex: 1;
  padding-right: 42px;
}
.eye-btn {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  border: 0;
  background: transparent;
  color: var(--on-surface-variant, #5b616e);
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 6px;
}
.eye-btn:hover {
  color: var(--primary, #005bbf);
  background: rgba(0, 91, 191, 0.08);
}
.eye-btn .material-symbols-outlined {
  font-size: 20px;
}
.hint {
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  margin: 5px 0 0;
  line-height: 1.45;
}
.hint.inline {
  margin: 0 0 0 8px;
}
.row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  padding-top: 4px;
}
.sw {
  position: relative;
  width: 38px;
  height: 22px;
  display: inline-block;
  vertical-align: middle;
}
.sw input {
  opacity: 0;
  width: 0;
  height: 0;
}
.sw .sl {
  position: absolute;
  inset: 0;
  background: #cbd5e1;
  border-radius: 22px;
  transition: 0.2s;
  cursor: pointer;
}
.sw .sl:before {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  left: 3px;
  top: 3px;
  background: #fff;
  border-radius: 50%;
  transition: 0.2s;
}
.sw input:checked + .sl {
  background: #16a34a;
}
.sw input:checked + .sl:before {
  transform: translateX(16px);
}
.copy-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.copy-row input {
  flex: 1;
}
.btn-ghost {
  padding: 8px 16px;
  border: 1px solid var(--outline, #727785);
  border-radius: 8px;
  background: transparent;
  color: var(--on-surface, #1f2329);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.btn-ghost:hover:not(:disabled) {
  background: var(--surface-container-low, #f2f4f5);
}
.btn-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  background: var(--primary, #005bbf);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary:hover:not(:disabled) {
  filter: brightness(0.95);
}
.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  flex-wrap: wrap;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid rgba(193, 198, 214, 0.45);
}
.ok-box {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #a7e3b8;
  background: #eafaf0;
  color: #166534;
  font-size: 13px;
}
.muted {
  font-size: 13px;
  color: var(--on-surface-variant, #5b616e);
}
.toast {
  position: fixed;
  bottom: 26px;
  left: 50%;
  transform: translateX(-50%) translateY(20px);
  background: #0f172a;
  color: #fff;
  padding: 11px 20px;
  border-radius: 10px;
  font-size: 13px;
  opacity: 0;
  transition: 0.25s;
  pointer-events: none;
  z-index: 99;
}
.toast.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
@media (max-width: 720px) {
  .form {
    grid-template-columns: 1fr;
  }
  .form > label {
    padding-top: 0;
  }
}
</style>
