<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { appName, applyBranding, logoUrl } from '../lib/branding'
import { getLocale, setLocale, type Locale } from '../lib/i18n'
import { api } from '../lib/api'
import { firstAllowedHome } from '../store/rbac'

const CONTACT_EMAIL = 'contact@sensepraxis.com'
const MAILTO = `mailto:${CONTACT_EMAIL}`

const router = useRouter()
const locale = ref<Locale>(getLocale())
const hasToken = ref(!!localStorage.getItem('fml_token'))
const brandTick = ref(0)
const ready = ref(false)

const copy = computed(() => (locale.value === 'en' ? EN : ZH))
const mailSubject = computed(() =>
  locale.value === 'en' ? 'Fangmanle commercial inquiry' : '房满乐商务合作咨询',
)
const mailHref = computed(() => `${MAILTO}?subject=${encodeURIComponent(mailSubject.value)}`)

onMounted(async () => {
  window.addEventListener('fml:locale', onLocale)
  requestAnimationFrame(() => {
    ready.value = true
  })
  try {
    const b = await api.branding()
    if (b) applyBranding(b)
    brandTick.value += 1
  } catch {
    /* ignore */
  }
})

onUnmounted(() => window.removeEventListener('fml:locale', onLocale))

function onLocale(e: Event) {
  locale.value = (e as CustomEvent).detail || getLocale()
}

function switchLocale(next: Locale) {
  setLocale(next)
  locale.value = next
}

function goLogin() {
  router.push({ path: '/login', query: { redirect: '/overview' } })
}

function goApp() {
  if (hasToken.value) {
    router.push(firstAllowedHome() || '/overview')
  } else {
    goLogin()
  }
}

function brandLogo() {
  void brandTick.value
  return logoUrl()
}

const ZH = {
  pill: '开源 AI原生酒店PMS',
  sub: '把预订、房态、收益、财务与私域增长装进一套会思考的系统。',
  ctaPrimary: '立即体验',
  panelTitle: '今日运营快照',
  panelLive: '实时',
  panelRow1: '今日入住',
  panelRow1v: '128 间',
  panelRow2: '渠道同步',
  panelRow2v: '正常',
  panelRow3: '私域触达',
  panelRow3v: '企微 / LINE',
  panelWhy: 'AI 提示：周末需求偏强，建议微调基础房型保留价；私域沉默客人可一键唤醒。',
  featTitle: '为独立酒店与中小连锁而建',
  featSub: '从前台效率到经营决策，用 AI 把日常运营串成闭环。',
  feats: [
    {
      t: '智能前台与房态',
      d: '订单、排房、房态看板一体；入住到退房流程清晰可追溯。',
      icon: 'calendar_view_day',
    },
    {
      t: '收益与经营洞察',
      d: '定价建议、预测与经营分析，把「为什么」说清楚。',
      icon: 'monitoring',
    },
    {
      t: '私域增长双轨',
      d: '国内企微深度运营；海外 LINE / WhatsApp，短信邮件兜底。',
      icon: 'groups',
    },
    {
      t: '财务与合规',
      d: '日结、对账、发票与报表链路打通，权限按角色精细控制。',
      icon: 'payments',
    },
    { t: '客人 OneID', d: '画像、标签与触达一体，服务与营销不再割裂。', icon: 'person_search' },
    { t: '开源可白标', d: '自托管部署，品牌名、主题色与通道包可按酒店配置。', icon: 'tune' },
  ],
  contactTitle: '联系我们',
  contactSub: '商用授权 · 私有化部署 · 渠道对接 · 定制实施',
  contactNote: '来信请注明酒店名称、规模与期望上线时间',
  contactCta: '发送合作意向',
}

const EN = {
  pill: 'Open-source AI-native Hotel PMS',
  sub: 'Reservations, room status, revenue, finance, and private-channel growth in one AI-native system.',
  ctaPrimary: 'Try it now',
  panelTitle: "Today's ops snapshot",
  panelLive: 'Live',
  panelRow1: 'Arrivals today',
  panelRow1v: '128 rooms',
  panelRow2: 'Channel sync',
  panelRow2v: 'Healthy',
  panelRow3: 'Private reach',
  panelRow3v: 'WeCom / LINE',
  panelWhy:
    'AI tip: weekend demand is firm — nudge base hold rates; silent private-channel guests can be reactivated in one pass.',
  featTitle: 'Built for independents & small groups',
  featSub:
    'From front-desk speed to ownership decisions — AI stitches daily ops into a closed loop.',
  feats: [
    {
      t: 'Front desk & room status',
      d: 'Orders, assignment, and the room board in one place.',
      icon: 'calendar_view_day',
    },
    {
      t: 'Revenue & insights',
      d: 'Pricing cues, forecast, and analytics that explain the “why”.',
      icon: 'monitoring',
    },
    {
      t: 'Private growth, dual track',
      d: 'Deep WeCom in China; LINE / WhatsApp abroad, SMS & email fallback.',
      icon: 'groups',
    },
    {
      t: 'Finance & compliance',
      d: 'Shift close, reconciliation, invoicing — with fine-grained RBAC.',
      icon: 'payments',
    },
    { t: 'Guest OneID', d: 'Profile, tags, and outreach in one identity.', icon: 'person_search' },
    {
      t: 'Open & white-label',
      d: 'Self-host ready; brand and channel packs per property.',
      icon: 'tune',
    },
  ],
  contactTitle: 'Contact us',
  contactSub: 'Licensing · private deploy · channel integration · custom build',
  contactNote: 'Please include hotel name, size, and target go-live',
  contactCta: 'Email us',
}
</script>

<template>
  <div class="lp" :class="{ ready }">
    <div class="ambient" aria-hidden="true" />

    <header class="top">
      <div class="top-inner">
        <div class="brand-lockup">
          <img v-if="brandLogo()" class="brand-logo" :src="brandLogo()" alt="" />
          <span
            v-else
            class="material-symbols-outlined brand-ico"
            style="font-variation-settings: 'FILL' 1"
            aria-hidden="true"
            >cottage</span
          >
          <div class="brand-text">
            <strong>{{ appName() }}</strong>
          </div>
        </div>

        <div class="lang" title="Language">
          <button type="button" :class="{ on: locale === 'zh-CN' }" @click="switchLocale('zh-CN')">
            中文
          </button>
          <button type="button" :class="{ on: locale === 'en' }" @click="switchLocale('en')">
            EN
          </button>
        </div>
      </div>
    </header>

    <section class="hero">
      <div class="hero-inner">
        <div class="hero-copy">
          <span class="pill">{{ copy.pill }}</span>
          <h1 v-if="locale === 'en'">
            <span class="hl">Fill every room</span><br />— intelligently.
          </h1>
          <h1 v-else>让每一间房，<br /><span class="hl">都满起来</span>。</h1>
          <p class="lead">{{ copy.sub }}</p>
          <button type="button" class="btn-cta" @click="goApp">
            {{ copy.ctaPrimary }}
            <span class="material-symbols-outlined arrow">arrow_forward</span>
          </button>
        </div>

        <div class="hero-visual">
          <div class="visual-glow" aria-hidden="true" />
          <div class="panel">
            <div class="panel-head">
              <div class="panel-title">
                <span class="live-dot" />
                <span>{{ copy.panelTitle }}</span>
              </div>
              <span class="live-tag">{{ copy.panelLive }}</span>
            </div>
            <div class="panel-rows">
              <div class="panel-row">
                <span class="row-ico material-symbols-outlined">login</span>
                <span class="row-label">{{ copy.panelRow1 }}</span>
                <b>{{ copy.panelRow1v }}</b>
              </div>
              <div class="panel-row">
                <span class="row-ico material-symbols-outlined">sync</span>
                <span class="row-label">{{ copy.panelRow2 }}</span>
                <b class="ok">{{ copy.panelRow2v }}</b>
              </div>
              <div class="panel-row">
                <span class="row-ico material-symbols-outlined">chat</span>
                <span class="row-label">{{ copy.panelRow3 }}</span>
                <b>{{ copy.panelRow3v }}</b>
              </div>
            </div>
            <div class="panel-why">
              <span class="why-badge">AI</span>
              <p>{{ copy.panelWhy }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="product" class="features">
      <div class="section-inner">
        <div class="section-head">
          <h2>{{ copy.featTitle }}</h2>
          <p>{{ copy.featSub }}</p>
        </div>
        <div class="feat-grid">
          <article
            v-for="(f, i) in copy.feats"
            :key="f.t"
            class="feat"
            :style="{ '--i': String(i) }"
          >
            <div class="feat-ico">
              <span class="material-symbols-outlined">{{ f.icon }}</span>
            </div>
            <h3>{{ f.t }}</h3>
            <p>{{ f.d }}</p>
          </article>
        </div>
      </div>
    </section>

    <section id="contact" class="contact">
      <div class="section-inner contact-inner">
        <div class="contact-bar">
          <div class="contact-meta">
            <span class="contact-title">{{ copy.contactTitle }}</span>
            <p class="contact-sub">{{ copy.contactSub }}</p>
            <p class="contact-note">{{ copy.contactNote }}</p>
          </div>
          <div class="contact-actions">
            <a class="email" :href="mailHref">{{ CONTACT_EMAIL }}</a>
            <a class="btn-mail" :href="mailHref">
              {{ copy.contactCta }}
              <span class="material-symbols-outlined">mail</span>
            </a>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.lp {
  --navy-1: #0f2742;
  --navy-2: #143a5a;
  --teal: #0c5f57;
  --gold: #d4a24e;
  --gold-soft: #e8c27a;
  --ink: #1f2a37;
  --muted: #5f6b7a;
  --line: #e4e9f0;
  --bg: #f4f7fb;
  --blue: #1a5fb4;
  position: relative;
  min-height: 100vh;
  color: var(--ink);
  background: #fbfcfe;
  font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  overflow-x: hidden;
}

.ambient {
  pointer-events: none;
  position: absolute;
  inset: 0 0 auto 0;
  height: 720px;
  background:
    radial-gradient(560px 280px at 12% 0%, rgba(212, 162, 78, 0.14), transparent 70%),
    radial-gradient(640px 320px at 88% 8%, rgba(15, 39, 66, 0.08), transparent 72%),
    linear-gradient(180deg, #eef3f8 0%, #fbfcfe 62%);
  z-index: 0;
}

.top,
.hero,
.features,
.contact {
  position: relative;
  z-index: 1;
}

.top {
  position: sticky;
  top: 0;
  z-index: 30;
  background: rgba(251, 252, 254, 0.82);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid transparent;
}
.lp.ready .top {
  border-bottom-color: rgba(228, 233, 240, 0.9);
}
.top-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 24px;
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.brand-lockup {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-logo {
  width: 30px;
  height: 30px;
  object-fit: contain;
  border-radius: 7px;
}
.brand-ico {
  font-size: 30px;
  color: var(--navy-1);
  line-height: 1;
}
.brand-text strong {
  display: block;
  font-size: 17px;
  line-height: 1.15;
  color: var(--navy-1);
  letter-spacing: 0.01em;
}

.lang {
  display: inline-flex;
  padding: 3px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 39, 66, 0.04);
}
.lang button {
  border: 0;
  background: transparent;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  border-radius: 999px;
  cursor: pointer;
  transition:
    background 0.2s ease,
    color 0.2s ease;
}
.lang button.on {
  background: var(--navy-1);
  color: #fff;
}

.hero-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 48px 24px 72px;
  display: grid;
  gap: 48px;
  align-items: center;
}

.hero-copy {
  opacity: 0;
  transform: translateY(14px);
  transition:
    opacity 0.55s ease,
    transform 0.55s ease;
}
.lp.ready .hero-copy {
  opacity: 1;
  transform: none;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 7px 13px;
  border-radius: 999px;
  border: 1px solid rgba(26, 95, 180, 0.16);
  background: rgba(255, 255, 255, 0.75);
  color: var(--blue);
  font-size: 12.5px;
  font-weight: 650;
  letter-spacing: 0.01em;
  margin-bottom: 18px;
  box-shadow: 0 1px 2px rgba(15, 39, 66, 0.04);
}

.hero-copy h1 {
  margin: 0;
  font-size: clamp(36px, 5vw, 52px);
  line-height: 1.18;
  font-weight: 760;
  color: var(--navy-1);
  letter-spacing: -0.03em;
}
.hero-copy h1 .hl {
  color: var(--gold);
  background: linear-gradient(120deg, #c8913a 0%, var(--gold) 45%, #e8c27a 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.lead {
  margin: 20px 0 0;
  color: var(--muted);
  font-size: 16.5px;
  line-height: 1.8;
  max-width: 32em;
}

.btn-cta {
  margin-top: 30px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 0;
  border-radius: 12px;
  padding: 14px 22px;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  cursor: pointer;
  background: linear-gradient(135deg, var(--navy-2) 0%, var(--navy-1) 55%, #0c5f57 120%);
  box-shadow: 0 12px 28px rgba(15, 39, 66, 0.22);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    filter 0.2s ease;
}
.btn-cta .arrow {
  font-size: 18px;
  transition: transform 0.2s ease;
}
.btn-cta:hover {
  transform: translateY(-1px);
  filter: brightness(1.05);
  box-shadow: 0 16px 34px rgba(15, 39, 66, 0.28);
}
.btn-cta:hover .arrow {
  transform: translateX(3px);
}

.hero-visual {
  position: relative;
  opacity: 0;
  transform: translateY(18px) scale(0.985);
  transition:
    opacity 0.65s ease 0.08s,
    transform 0.65s ease 0.08s;
}
.lp.ready .hero-visual {
  opacity: 1;
  transform: none;
}

.visual-glow {
  position: absolute;
  inset: -8% -6% auto -6%;
  height: 70%;
  border-radius: 28px;
  background: linear-gradient(145deg, var(--navy-1), var(--navy-2) 50%, var(--teal));
  box-shadow: 0 28px 70px rgba(15, 39, 66, 0.28);
  transform: rotate(-1.2deg);
}
.visual-glow::after {
  content: '';
  position: absolute;
  right: -40px;
  top: -50px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(212, 162, 78, 0.35), transparent 68%);
}

.panel {
  position: relative;
  margin: 18px 16px 0;
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 18px;
  padding: 18px 18px 16px;
  box-shadow: 0 18px 40px rgba(15, 39, 66, 0.16);
  backdrop-filter: blur(8px);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--navy-1);
}
.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22a06b;
  box-shadow: 0 0 0 0 rgba(34, 160, 107, 0.45);
  animation: pulse 1.8s ease-out infinite;
}
.live-tag {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #1f7a54;
  background: rgba(34, 160, 107, 0.1);
  border-radius: 999px;
  padding: 3px 8px;
}

.panel-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.panel-row {
  display: grid;
  grid-template-columns: 28px 1fr auto;
  align-items: center;
  gap: 8px;
  padding: 11px 12px;
  border-radius: 12px;
  background: linear-gradient(180deg, #fff, #f7f9fc);
  border: 1px solid var(--line);
}
.row-ico {
  font-size: 18px;
  color: var(--navy-2);
  opacity: 0.75;
}
.row-label {
  font-size: 13.5px;
  color: var(--muted);
}
.panel-row b {
  font-size: 13.5px;
  color: var(--ink);
  font-weight: 740;
}
.panel-row b.ok {
  color: #1f7a54;
}

.panel-why {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 13px;
  border-radius: 12px;
  background: linear-gradient(120deg, rgba(212, 162, 78, 0.12), rgba(26, 95, 180, 0.08));
  border: 1px solid rgba(212, 162, 78, 0.18);
}
.why-badge {
  flex: 0 0 auto;
  margin-top: 1px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: var(--navy-1);
  background: var(--gold-soft);
  border-radius: 6px;
  padding: 3px 6px;
}
.panel-why p {
  margin: 0;
  font-size: 12.8px;
  line-height: 1.6;
  color: var(--navy-2);
}

.features {
  background: #fff;
  border-top: 1px solid var(--line);
}
.section-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 64px 24px;
}
.section-head {
  text-align: center;
  max-width: 36em;
  margin: 0 auto;
}
.section-head h2 {
  margin: 0;
  font-size: clamp(24px, 3vw, 30px);
  color: var(--navy-1);
  letter-spacing: -0.02em;
}
.section-head p {
  margin: 12px 0 0;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.7;
}

.feat-grid {
  margin-top: 36px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}
.feat {
  position: relative;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 22px 20px 20px;
  background: linear-gradient(180deg, #fff 0%, #fbfcfe 100%);
  transition:
    border-color 0.2s ease,
    transform 0.2s ease,
    box-shadow 0.2s ease;
}
.feat:hover {
  border-color: rgba(15, 39, 66, 0.18);
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(15, 39, 66, 0.07);
}
.feat-ico {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
  color: var(--gold);
  background: linear-gradient(145deg, rgba(15, 39, 66, 0.92), rgba(20, 58, 90, 0.95));
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}
.feat-ico .material-symbols-outlined {
  font-size: 20px;
}
.feat h3 {
  margin: 0;
  font-size: 16px;
  color: var(--navy-1);
  letter-spacing: -0.01em;
}
.feat p {
  margin: 8px 0 0;
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--muted);
}

.contact {
  border-top: 1px solid var(--line);
  background: #f7f9fc;
}
.contact-inner {
  padding-top: 28px !important;
  padding-bottom: 32px !important;
}
.contact-bar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 20px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
}
.contact-title {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--navy-1);
  letter-spacing: 0.01em;
}
.contact-sub {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}
.contact-note {
  margin: 4px 0 0;
  font-size: 11px;
  line-height: 1.5;
  color: #8a94a3;
}
.contact-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
}
.email {
  color: var(--navy-2);
  font-size: 13px;
  font-weight: 650;
  text-decoration: none;
  border-bottom: 1px solid rgba(212, 162, 78, 0.55);
  padding-bottom: 1px;
}
.email:hover {
  color: var(--navy-1);
  border-bottom-color: var(--gold);
}
.btn-mail {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 12px;
  border-radius: 8px;
  background: var(--navy-1);
  color: #fff;
  font-size: 12px;
  font-weight: 650;
  text-decoration: none;
  transition: background 0.15s ease;
}
.btn-mail .material-symbols-outlined {
  font-size: 15px;
}
.btn-mail:hover {
  background: var(--navy-2);
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(34, 160, 107, 0.45);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(34, 160, 107, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(34, 160, 107, 0);
  }
}

@media (min-width: 900px) {
  .hero-inner {
    grid-template-columns: 1.05fr 0.95fr;
    padding: 72px 24px 88px;
    gap: 56px;
  }
  .feat-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .contact-bar {
    flex-direction: row;
    align-items: center;
  }
  .contact-actions {
    flex-shrink: 0;
  }
}

@media (max-width: 640px) {
  .hero-inner {
    padding-top: 28px;
    padding-bottom: 48px;
  }
  .visual-glow {
    transform: none;
  }
  .panel {
    margin: 14px 8px 0;
  }
}
</style>
