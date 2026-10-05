<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'
import { applySession, initHotel } from '../store/hotel'
import { toast } from '../lib/ui'
import { appName, appNameEn, applyBranding } from '../lib/branding'

const router = useRouter()
const route = useRoute()

onMounted(async () => {
  try {
    const b = await api.branding()
    if (b) applyBranding(b)
  } catch {
    /* 登录前拉品牌失败则用默认/env */
  }
})

const tab = ref<'pw' | 'sms'>('pw')
const username = ref('admin')
const password = ref('admin123')
const showPw = ref(false)
const remember = ref(true)
const submitting = ref(false)

const smsPhone = ref('')
const smsCode = ref('')
const sendLeft = ref(0)
let sendTimer: number | undefined

function tip(msg: string) {
  toast(msg)
  return false
}

function togglePw() {
  showPw.value = !showPw.value
}

function sendCode() {
  const phone = smsPhone.value.trim()
  if (!/^1\d{10}$/.test(phone)) {
    toast(t('请输入正确的手机号'))
    return
  }
  if (sendLeft.value > 0) return
  toast(t('验证码登录中，请使用密码登录'))
  sendLeft.value = 60
  sendTimer = window.setInterval(() => {
    sendLeft.value -= 1
    if (sendLeft.value <= 0 && sendTimer) {
      clearInterval(sendTimer)
      sendTimer = undefined
    }
  }, 1000)
}

async function doLogin() {
  if (tab.value === 'sms') {
    toast(t('短信验证码登录即将接入，请先使用密码登录'))
    return
  }
  submitting.value = true
  try {
    const r = await api.login({
      username: username.value.trim(),
      password: password.value.trim(),
    })
    applySession(r)
    await initHotel()
    toast(t('欢迎，{name}', { name: r.user?.name || r.hotel_name || appName() }))
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/overview'
    router.push(redirect === '/' ? '/overview' : redirect || '/overview')
  } catch (e: any) {
    toast(t('登录失败：') + (e.message || e))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="wrap">
    <aside class="brand">
      <div class="logo">
        <div class="mark" aria-hidden="true" />
        <div class="name">
          {{ appName() }} <small>{{ appNameEn().toUpperCase() }} · AI PMS</small>
        </div>
      </div>

      <div class="hero">
        <h1>
          {{ t('让每一间房，') }}<br /><span class="hl">{{ t('都满起来') }}</span
          >。
        </h1>
        <p>{{ t('配置大模型后，入住、房态、收益与私域增长才能由 AI 基于数据给出建议。') }}</p>
      </div>

      <div class="values">
        <div class="value">
          <div class="ic">◎</div>
          <div>
            <b>{{ t('私域获客') }}</b
            ><span>{{ t('企微触达，沉淀复购') }}</span>
          </div>
        </div>
        <div class="value">
          <div class="ic">◈</div>
          <div>
            <b>{{ t('AI 指导经营') }}</b
            ><span>{{ t('数据洞察，辅助决策') }}</span>
          </div>
        </div>
        <div class="value">
          <div class="ic">⚡</div>
          <div>
            <b>AI Agent</b><span>{{ t('接上大模型后，用经营数据生成建议') }}</span>
          </div>
        </div>
        <div class="value">
          <div class="ic">¥</div>
          <div>
            <b>{{ t('智能定价') }}</b
            ><span>{{ t('动态收益最大化') }}</span>
          </div>
        </div>
      </div>

      <div class="assistant">
        <div class="ava" aria-hidden="true" />
        <div class="txt">
          <b>{{ t('我是小满 ◐') }}</b
          ><br />
          <span>{{ t('登录后可调度规则看板；对话能力需配置大模型。') }}</span>
        </div>
      </div>
    </aside>

    <main class="panel">
      <div class="card">
        <div class="top">
          <h2>{{ t('登录') }}{{ appName() }}</h2>
        </div>

        <div class="tabs">
          <button type="button" :class="{ active: tab === 'pw' }" @click="tab = 'pw'">
            {{ t('密码登录') }}
          </button>
          <button type="button" :class="{ active: tab === 'sms' }" @click="tab = 'sms'">
            {{ t('验证码登录') }}
          </button>
        </div>

        <form v-if="tab === 'pw'" @submit.prevent="doLogin">
          <div class="field">
            <label>{{ t('账号 / 手机号') }}</label>
            <input
              v-model="username"
              type="text"
              :placeholder="t('请输入账号或注册手机号')"
              autocomplete="username"
            />
          </div>
          <div class="field">
            <label>{{ t('密码') }}</label>
            <div class="pw">
              <input
                v-model="password"
                :type="showPw ? 'text' : 'password'"
                :placeholder="t('请输入密码')"
                autocomplete="current-password"
              />
              <span class="eye" @click="togglePw">{{ showPw ? t('隐藏') : t('显示') }}</span>
            </div>
          </div>
          <div class="row">
            <label><input v-model="remember" type="checkbox" /> {{ t('记住我') }}</label>
            <a href="#" @click.prevent="tip(t('请联系系统管理员重置密码'))">{{
              t('忘记密码？')
            }}</a>
          </div>
          <button class="btn-primary" type="submit" :disabled="submitting">
            {{ submitting ? t('校验中…') : t('登 录') }}
          </button>
        </form>

        <form v-else @submit.prevent="doLogin">
          <div class="field">
            <label>{{ t('手机号') }}</label>
            <input
              v-model="smsPhone"
              type="tel"
              :placeholder="t('请输入手机号')"
              autocomplete="username"
            />
          </div>
          <div class="field">
            <label>{{ t('短信验证码') }}</label>
            <div class="code-row">
              <input v-model="smsCode" type="text" :placeholder="t('6 位验证码')" />
              <button type="button" class="send" :disabled="sendLeft > 0" @click="sendCode">
                {{ sendLeft > 0 ? `${sendLeft}s` : t('获取验证码') }}
              </button>
            </div>
          </div>
          <div class="row">
            <label><input v-model="remember" type="checkbox" /> {{ t('记住我') }}</label>
            <a href="#" @click.prevent="tip(t('请联系系统管理员重置密码'))">{{
              t('忘记密码？')
            }}</a>
          </div>
          <button class="btn-primary" type="submit" :disabled="submitting">{{ t('登 录') }}</button>
        </form>
      </div>
    </main>
  </div>
</template>

<style scoped>
:root,
.wrap {
  --navy-1: #0f2742;
  --navy-2: #143a5a;
  --teal: #0f766e;
  --gold: #d4a24e;
  --ink: #1f2a37;
  --muted: #6b7785;
  --line: #e6eaf0;
  --bg: #f6f8fb;
  --blue: #1a5fb4;
  --blue-d: #134a8e;
}

.wrap {
  display: flex;
  min-height: 100vh;
  font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Segoe UI', sans-serif;
  color: var(--ink);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
}

.brand {
  position: relative;
  flex: 0 0 46%;
  max-width: 560px;
  background: linear-gradient(150deg, var(--navy-1) 0%, var(--navy-2) 60%, #0c5f57 100%);
  color: #fff;
  padding: 56px 52px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
}
.brand::after {
  content: '';
  position: absolute;
  right: -120px;
  top: -120px;
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, rgba(212, 162, 78, 0.22), transparent 70%);
  border-radius: 50%;
}
.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 1;
}
.logo .mark {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: conic-gradient(var(--gold) 0 50%, rgba(255, 255, 255, 0.18) 50% 100%);
  position: relative;
}
.logo .mark::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--navy-1);
  transform: translate(-50%, -50%);
}
.logo .name {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.logo .name small {
  display: block;
  font-size: 12px;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.6);
  letter-spacing: 2px;
}
.hero {
  z-index: 1;
  margin-top: 40px;
}
.hero h1 {
  font-size: 30px;
  line-height: 1.4;
  font-weight: 700;
}
.hero h1 .hl {
  color: var(--gold);
}
.hero p {
  margin-top: 14px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 15px;
  line-height: 1.8;
}
.values {
  z-index: 1;
  margin-top: 36px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 22px;
}
.value {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.value .ic {
  flex: 0 0 30px;
  height: 30px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: var(--gold);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
}
.value b {
  font-size: 14px;
  display: block;
}
.value span {
  font-size: 12.5px;
  color: rgba(255, 255, 255, 0.62);
}
.assistant {
  z-index: 1;
  margin-top: 34px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  padding: 12px 14px;
}
.assistant .ava {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: conic-gradient(var(--gold) 0 50%, #fff 50% 100%);
  position: relative;
  flex: 0 0 34px;
}
.assistant .ava::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: var(--navy-1);
  transform: translate(-50%, -50%);
}
.assistant .txt b {
  color: #fff;
  font-size: 13.5px;
}
.assistant .txt span {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}

.panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.card {
  width: 100%;
  max-width: 380px;
}
.card .top {
  text-align: center;
  margin-bottom: 22px;
}
.card .top h2 {
  font-size: 24px;
  font-weight: 700;
}

.tabs {
  display: flex;
  gap: 4px;
  background: #eef1f6;
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 18px;
}
.tabs button {
  flex: 1;
  border: 0;
  background: transparent;
  border-radius: 8px;
  padding: 9px;
  font-size: 13px;
  color: var(--muted);
  cursor: pointer;
}
.tabs button.active {
  background: #fff;
  color: var(--ink);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(15, 39, 66, 0.08);
}

.field {
  margin-bottom: 16px;
}
.field label {
  display: block;
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 7px;
}
.field input {
  width: 100%;
  height: 46px;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0 14px;
  font-size: 14px;
  color: var(--ink);
  background: #fff;
  outline: none;
  transition: 0.15s;
  font: inherit;
}
.field input:focus {
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(26, 95, 180, 0.12);
}
.field .pw {
  position: relative;
}
.field .pw input {
  padding-right: 46px;
}
.field .pw .eye {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  color: var(--muted);
  font-size: 13px;
  user-select: none;
}
.code-row {
  display: flex;
  gap: 10px;
}
.code-row input {
  flex: 1;
}
.code-row .send {
  flex: 0 0 116px;
  border: 1px solid var(--blue);
  color: var(--blue);
  background: #fff;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
  height: 46px;
}
.code-row .send:disabled {
  color: var(--muted);
  border-color: var(--line);
  cursor: not-allowed;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 4px 0 22px;
  font-size: 13px;
}
.row label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  cursor: pointer;
}
.row a {
  color: var(--blue);
  text-decoration: none;
}
.row a:hover {
  text-decoration: underline;
}
.btn-primary {
  width: 100%;
  height: 48px;
  border: 0;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--blue) 0%, var(--blue-d) 100%);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: 0.15s;
}
.btn-primary:hover {
  filter: brightness(1.05);
}
.btn-primary:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

@media (max-width: 880px) {
  .brand {
    display: none;
  }
  .panel {
    padding: 28px 20px;
  }
}
</style>
