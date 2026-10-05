<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * One ID 档案数据溯源 —— 按 guestId 展示当前客人黄金档案与渠道血缘
 * 入口：one-id-audit「查看OneID档案数据溯源」→ /b-data/data-source-lineage?guestId=
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../lib/api'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const err = ref('')
const audit = ref<any>(null)
const portrait = ref<any>(null)

const guestId = computed(() => {
  const v = route.query.guestId
  return v ? Number(v) : 0
})

const SRC: Record<
  string,
  { cn: string; icon: string; accent: 'primary' | 'tertiary' | 'secondary' }
> = {
  wechat: { cn: t('微信小程序 (WeChat)'), icon: 'chat', accent: 'tertiary' },
  wecom: { cn: t('企业微信'), icon: 'forum', accent: 'tertiary' },
  ctrip: { cn: t('携程旅行 (Ctrip)'), icon: 'flight_takeoff', accent: 'primary' },
  meituan: { cn: t('美团'), icon: 'storefront', accent: 'secondary' },
  fliggy: { cn: t('飞猪'), icon: 'flight', accent: 'primary' },
  douyin: { cn: t('抖音'), icon: 'smart_display', accent: 'tertiary' },
  xiaohongshu: { cn: t('小红书'), icon: 'auto_stories', accent: 'tertiary' },
  official: { cn: t('官网直订'), icon: 'language', accent: 'primary' },
  walkin: { cn: t('散客到店'), icon: 'login', accent: 'secondary' },
  ota: { cn: 'OTA', icon: 'travel_explore', accent: 'primary' },
  agreement: { cn: t('协议客户'), icon: 'handshake', accent: 'secondary' },
  direct: { cn: t('本店直客'), icon: 'home', accent: 'primary' },
}

async function load() {
  if (!guestId.value) {
    audit.value = null
    portrait.value = null
    err.value = t('缺少 guestId，请从 OneID 归并审计页进入。')
    return
  }
  loading.value = true
  err.value = ''
  try {
    const [a, p] = await Promise.all([
      api.guestOneidAudit(guestId.value),
      api.guest360(guestId.value),
    ])
    audit.value = a
    portrait.value = p
  } catch (e: any) {
    audit.value = null
    portrait.value = null
    err.value = e?.message || t('加载失败')
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(guestId, load)

const guest = computed(() => audit.value?.guest || portrait.value?.guest || null)
const summary = computed(() => audit.value?.summary || {})
const identities = computed(() => audit.value?.identities || [])
const tags = computed(() => portrait.value?.tags || [])

const oneIdLabel = computed(
  () =>
    summary.value.one_id || guest.value?.one_id || `ONE${String(guestId.value).padStart(6, '0')}`,
)
const confPct = computed(() => Math.round(Number(summary.value.avg_confidence ?? 1) * 1000) / 10)

function phoneMask(p: string) {
  const s = String(p || '').replace(/\D/g, '')
  if (s.length >= 7) return `${s.slice(0, 3)}****${s.slice(-4)}`
  return p || '—'
}

const prefsText = computed(() => {
  const names = tags.value.map((t: any) => t.name).filter(Boolean)
  return names.length ? names.slice(0, 3).join('、') : t('暂无偏好标签')
})

const sources = computed(() => {
  const list = identities.value
  if (!list.length) {
    return [
      {
        key: 'direct',
        cn: t('本店主档'),
        icon: 'home',
        accent: 'primary' as const,
        weight: 100,
        at: guest.value?.created_at || '',
        fields: [
          { k: 'GuestID', v: String(guest.value?.id || guestId.value) },
          { k: 'Name', v: guest.value?.name || '—' },
          { k: 'Phone', v: phoneMask(guest.value?.phone) },
          { k: 'Status', v: 'Master' },
        ],
        drill: t('下钻查看主档订单'),
      },
    ]
  }
  const totalConf = list.reduce(
    (s: number, i: any) => s + Math.max(0.05, Number(i.confidence || 0.5)),
    0,
  )
  return list.map((i: any) => {
    const meta = SRC[(i.source || '').toLowerCase()] || {
      cn: i.source || t('未知渠道'),
      icon: 'link',
      accent: 'secondary' as const,
    }
    const w = Math.round((Math.max(0.05, Number(i.confidence || 0.5)) / totalConf) * 100)
    const at = String(i.linked_at || '')
      .replace('T', ' ')
      .slice(0, 19)
    return {
      key: i.id,
      cn: meta.cn,
      icon: meta.icon,
      accent: meta.accent,
      weight: w,
      at,
      fields: [
        { k: 'External', v: i.external_id || '—' },
        { k: 'Name', v: guest.value?.name || '—' },
        { k: 'Phone', v: phoneMask(guest.value?.phone) },
        { k: 'Conf', v: `${Math.round(Number(i.confidence || 0) * 100)}%` },
      ],
      drill: meta.accent === 'tertiary' ? t('下钻查看交互日志') : t('下钻查看原始订单'),
    }
  })
})

const insightText = computed(() => {
  const srcs = sources.value
  if (srcs.length >= 2) {
    return `系统检测到高度一致的身份特征。${srcs[0].cn} 与 ${srcs[1].cn} 等渠道数据已归并至黄金档案。总体合并置信度：`
  }
  if (srcs.length === 1) {
    return `当前档案以 ${srcs[0].cn} 为主数据源构建黄金档案。总体合并置信度：`
  }
  return t('暂无跨渠道身份，黄金档案即本店主档。总体合并置信度：')
})

function goBack() {
  if (guestId.value) router.push({ path: `/guests/${guestId.value}`, query: { oneid: 'open' } })
  else router.push('/b-data/global-guest-directory')
}
</script>

<template>
  <div class="page lineage">
    <div v-if="loading" class="muted">{{ t('正在加载档案数据溯源…') }}</div>
    <div v-else-if="err" class="err-box">{{ err }}</div>
    <template v-else-if="guest">
      <header
        class="mb-8 flex items-end justify-between border-b border-outline-variant pb-4 flex-wrap gap-4"
      >
        <div>
          <button type="button" class="back-link" @click="goBack">
            <span class="material-symbols-outlined text-sm">arrow_back</span>
            {{ t('返回 360 画像') }}
          </button>
          <h1
            class="font-display-lg text-display-lg text-on-background flex items-center gap-3 flex-wrap m-0 mt-2"
          >
            {{ t('One ID 档案数据溯源') }}
            <span class="id-badge">ID: {{ oneIdLabel }}</span>
          </h1>
          <p class="font-body-md text-body-md text-on-surface-variant mt-2 max-w-3xl m-0">
            {{ t('此视图展示') }} AI {{ t('如何合并「') }}{{ guest.name }}」{{
              t('多渠道数据，构建黄金档案（')
            }}Golden Profile）。{{ t('每个节点含原始凭证与对最终档案的贡献权重。') }}
          </p>
        </div>
        <button type="button" class="export-btn">
          <span class="material-symbols-outlined">download</span>
          {{ t('导出报告') }}
        </button>
      </header>

      <div class="panel">
        <div class="insight">
          <div class="insight-glow" />
          <span class="material-symbols-outlined text-tertiary mt-0.5">psychology</span>
          <div>
            <h4 class="font-headline-md text-headline-md text-on-background mb-1 m-0">
              {{ t('AI 溯源分析 (AI Lineage Insight)') }}
            </h4>
            <p class="font-body-md text-body-md text-on-surface-variant m-0">
              {{ insightText }}<span class="text-primary font-bold">{{ confPct }}%</span>。
            </p>
          </div>
        </div>

        <div class="grid grid-cols-12 gap-4 flex-1">
          <!-- Golden Profile -->
          <div
            class="col-span-12 md:col-span-4 flex flex-col justify-center items-center md:border-r border-outline-variant md:pr-4"
          >
            <div class="golden w-full">
              <div class="golden-avatar">
                <span class="material-symbols-outlined text-4xl">admin_panel_settings</span>
              </div>
              <h3 class="font-headline-lg text-headline-lg text-on-background mb-2 m-0">
                {{ t('黄金档案 (Golden Profile)') }}
              </h3>
              <div class="oneid-num mb-4">{{ oneIdLabel }}</div>
              <div class="golden-fields">
                <div class="gf-row">
                  <span class="gf-k">{{ t('姓名:') }}</span>
                  <span class="gf-v">{{ guest.name }}</span>
                </div>
                <div class="gf-row">
                  <span class="gf-k">{{ t('手机号:') }}</span>
                  <span class="gf-v mono">{{ phoneMask(guest.phone) }}</span>
                </div>
                <div class="gf-row last">
                  <span class="gf-k">{{ t('偏好:') }}</span>
                  <span class="gf-v">{{ prefsText }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Sources -->
          <div
            class="col-span-12 md:col-span-8 flex flex-col justify-center gap-4 md:pl-4 relative"
          >
            <div class="conn-rail hidden md:block" aria-hidden="true" />
            <div
              v-for="s in sources"
              :key="s.key"
              class="src-card group"
              :class="'accent-' + s.accent"
            >
              <div class="src-bar" />
              <div class="flex justify-between items-start mb-3 pl-2 gap-3 flex-wrap">
                <div class="flex items-center gap-3 min-w-0">
                  <div class="src-ico" :class="'ico-' + s.accent">
                    <span class="material-symbols-outlined">{{ s.icon }}</span>
                  </div>
                  <div class="min-w-0">
                    <h5 class="font-headline-md text-headline-md m-0">{{ s.cn }}</h5>
                    <div class="text-sm text-on-surface-variant flex items-center gap-1 mt-0.5">
                      <span class="material-symbols-outlined text-xs">schedule</span>
                      {{ s.at || '—' }}
                    </div>
                  </div>
                </div>
                <div class="text-right shrink-0">
                  <div class="font-label-lg text-label-lg text-on-surface-variant">
                    {{ t('贡献权重') }}
                  </div>
                  <div class="weight" :class="'w-' + s.accent">{{ s.weight }}%</div>
                </div>
              </div>
              <div class="src-grid">
                <div v-for="f in s.fields" :key="f.k">
                  <span class="text-outline">{{ f.k }}:</span> {{ f.v }}
                </div>
              </div>
              <div class="flex justify-end pr-2 mt-3">
                <span
                  class="text-primary font-label-lg text-label-lg flex items-center gap-1 text-sm"
                >
                  {{ s.drill }}
                  <span class="material-symbols-outlined text-sm">arrow_forward</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.lineage {
  max-width: 1100px;
}
.muted {
  color: var(--on-surface-variant);
  font-size: 13px;
}
.err-box {
  padding: 12px 14px;
  border-radius: 10px;
  background: #fef3f2;
  border: 1px solid #fecaca;
  color: #b42318;
  font-size: 13px;
}
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  padding: 0;
  color: var(--primary);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
}
.back-link:hover {
  opacity: 0.85;
}
.id-badge {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 14px;
  font-weight: 700;
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, transparent);
  padding: 4px 12px;
  border-radius: 8px;
}
.export-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 999px;
  cursor: pointer;
  border: 1px solid var(--outline, #727785);
  background: var(--surface-container-lowest);
  color: var(--primary);
  font-size: 14px;
  font-weight: 650;
}
.export-btn:hover {
  background: var(--surface-container-low);
}

.panel {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.insight {
  position: relative;
  overflow: hidden;
  margin-bottom: 24px;
  padding: 16px;
  background: var(--surface-bright, #f8fafb);
  border-left: 2px solid var(--tertiary, #8c33b3);
  border-radius: 0 8px 8px 0;
  display: flex;
  gap: 16px;
  align-items: flex-start;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
}
.insight-glow {
  position: absolute;
  right: -40px;
  top: -40px;
  width: 128px;
  height: 128px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--tertiary-fixed-dim, #ebb2ff) 20%, transparent);
  filter: blur(24px);
  pointer-events: none;
}

.golden {
  text-align: center;
  background: color-mix(in srgb, var(--primary-fixed, #d8e2ff) 30%, transparent);
  border: 1px solid color-mix(in srgb, var(--primary) 20%, transparent);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 0 15px rgba(26, 115, 232, 0.15);
}
.golden-avatar {
  width: 80px;
  height: 80px;
  border-radius: 999px;
  margin: 0 auto 16px;
  background: var(--primary);
  color: var(--on-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 10px rgba(0, 91, 191, 0.25);
}
.oneid-num {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 20px;
  font-weight: 700;
  color: var(--primary);
}
.golden-fields {
  text-align: left;
  background: var(--surface-container-lowest);
  border: 1px solid color-mix(in srgb, var(--outline-variant) 50%, transparent);
  border-radius: 8px;
  padding: 14px;
}
.gf-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 6px;
  margin-bottom: 6px;
  border-bottom: 1px solid color-mix(in srgb, var(--outline-variant) 30%, transparent);
}
.gf-row.last {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}
.gf-k {
  font-size: 13px;
  color: var(--on-surface-variant);
  font-weight: 650;
}
.gf-v {
  font-size: 14px;
  color: var(--on-surface);
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.conn-rail {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translate(-100%, -50%);
  width: 16px;
  height: 80%;
  border-left: 2px solid color-mix(in srgb, var(--primary) 30%, transparent);
  border-top: 2px solid color-mix(in srgb, var(--primary) 30%, transparent);
  border-bottom: 2px solid color-mix(in srgb, var(--primary) 30%, transparent);
  border-radius: 12px 0 0 12px;
}

.src-card {
  position: relative;
  overflow: hidden;
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 16px;
  transition: box-shadow 0.15s;
}
.src-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}
.src-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--primary);
  transition: width 0.15s;
}
.src-card:hover .src-bar {
  width: 6px;
}
.accent-tertiary .src-bar {
  background: var(--tertiary, #8c33b3);
}
.accent-secondary .src-bar {
  background: var(--secondary, #5b5f64);
}

.src-ico {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ico-primary {
  background: var(--secondary-container, #dde0e6);
  color: var(--primary);
}
.ico-tertiary {
  background: var(--tertiary-fixed, #f8d8ff);
  color: var(--tertiary, #8c33b3);
}
.ico-secondary {
  background: var(--surface-container-high);
  color: var(--secondary);
}

.weight {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 22px;
  font-weight: 700;
  color: var(--primary);
}
.w-tertiary {
  color: var(--tertiary, #8c33b3);
}
.w-secondary {
  color: var(--secondary);
}

.src-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  background: var(--surface-container-low);
  border-radius: 6px;
  padding: 12px;
  font-size: 13px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color: var(--on-secondary-fixed-variant, #43474c);
}
.text-outline {
  color: var(--outline, #727785);
}

.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
</style>
