<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 动态服务 SOP 库 —— 对照原型 sop.html
 * 左：SOP 模板 + 启用中编辑器；右：质检/客需反馈闭环
 * 数据：GET /api/housekeeping/board（vision / performance / service_requests / tasks）
 */
import { ref, onMounted, watch } from 'vue'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
import HousekeepingFlowNav from '../../components/HousekeepingFlowNav.vue'

type Tpl = { id: string; title: string; desc: string; badge?: 'hot' | 'ai'; active?: boolean }
type Step = {
  kind: 'normal' | 'ai'
  no?: string
  title: string
  desc: string
  duration?: string
  dept?: string
  img?: string
}

const STEP_IMG =
  'https://lh3.googleusercontent.com/aida-public/AB6AXuBnEfhUxB6kL7QMAKK05na0j97CQLvQY1w77y57r6CXNvjJ0fKND6fo49so_0JB4MpfPv-vE7UjTMmr6TjAPIiCJ_EMdRIwUg_dgDmZPCraqN78A-0n1c-JbB84EUxZ0i3WNnxWXAQxNh0sSasv5PKnaSRku0C0Oohbx8GiuK9-H15hBQ4KPdBq-Zbpeo_Cpt5_O3xbyZrUenxHqUCF9m0EnAJ9L9AWLRL0tIvpmRU_2QA_UF4iwIU'

const FALLBACK_TPL: Tpl[] = [
  {
    id: 'vip',
    title: t('贵宾 到店准备'),
    desc: t('面向高等级客人的欢迎清单，含个性化客用品。'),
    badge: 'hot',
    active: true,
  },
  {
    id: 'pet',
    title: t('深度清洁中（宠物）'),
    desc: t('宠物入住后的消杀规范，侧重除敏与除味。'),
  },
  {
    id: 'late',
    title: t('延迟退房周转'),
    desc: t('针对紧凑排期窗口的加速客房恢复流程。'),
    badge: 'ai',
  },
]

const FALLBACK_STEPS: Step[] = [
  {
    kind: 'normal',
    no: '01',
    title: t('核验个性化欢迎礼遇布置'),
    desc: t('确保果盘新鲜（制备于 2 小时前以内），且欢迎卡由总经理亲笔签名。'),
    duration: '5m',
    dept: t('餐饮、客房'),
    img: STEP_IMG,
  },
  {
    kind: 'ai',
    no: '++',
    title: t('质检建议：增加温度检查'),
    desc: t('根据近期客人反馈，贵宾 到店前将温控调至 22°C（72°F）可使满意度提升 14%。'),
  },
]

const FALLBACK_CHAT = {
  insightTitle: t('反馈分析闭环'),
  insightText: t('我已分析上月 42 条关于“清洁度”的评论。301-315 房客人提及浴室用品不一致。'),
  suggestTitle: t('建议（R1 - 低风险）'),
  suggestBody: t('更新“标准客房清洁”标准作业程序，增加洗漱托盘的强制拍照上传。'),
  userText: t('当前的深度清洁中（宠物）标准作业程序平均需要多长时间？'),
  dataLead: t('基于客房应用近 30 天任务完成日志：'),
  dataValue: '45',
  dataUnit: 'mins',
  dataDelta: t('较目标 +5 分钟'),
  dataFoot: t('耗时最长的是“HEPA 吸尘”。是否应复核该步骤的设备或培训？'),
}

const templates = ref<Tpl[]>([...FALLBACK_TPL])
const activeTpl = ref('vip')
const editorTitle = ref(t('贵宾抵达准备（套房）'))
const editorMeta = ref(t('2 小时前由质检数据刷新'))
const steps = ref<Step[]>([...FALLBACK_STEPS])
const chat = ref({ ...FALLBACK_CHAT })
const chatInput = ref('')

function selectTpl(tpl: Tpl) {
  activeTpl.value = tpl.id
  templates.value = templates.value.map((x) => ({ ...x, active: x.id === tpl.id }))
  if (tpl.id === 'vip') {
    editorTitle.value = t('贵宾抵达准备（套房）')
  } else if (tpl.id === 'pet') {
    editorTitle.value = t('深度清洁中（宠物）')
  } else {
    editorTitle.value = t('延迟退房周转')
  }
}

function buildFromBoard(board: any) {
  const vision = board?.vision || {}
  const perf = board?.performance || {}
  const srs = board?.service_requests || []
  const tasks = board?.tasks || []
  const hist = vision.history || []
  const rooms = vision.rooms || []

  const openSr = srs.filter((x: any) => x.open)
  const dirtyN = board?.room_status?.dirty || board?.room_status?.by_status?.dirty || 0
  const vipHint =
    openSr.some((x: any) => (x.priority || 5) <= 2) || tasks.some((t: any) => t.priority)
  const petHint = openSr.some((x: any) => /宠物|除敏|消杀/.test(x.content || x.msg || ''))
  const lateHint = dirtyN >= 3 || openSr.length >= 3

  const tpls: Tpl[] = [
    {
      id: 'vip',
      title: vipHint ? t('贵宾 / 高优到店准备') : t('贵宾 到店准备'),
      desc: vipHint
        ? `当前 ${openSr.filter((x: any) => (x.priority || 5) <= 2).length || openSr.length} 条高优客需，建议启用欢迎礼遇清单。`
        : t('面向高等级客人的欢迎清单，含个性化客用品。'),
      badge: 'hot',
      active: activeTpl.value === 'vip',
    },
    {
      id: 'pet',
      title: t('深度清洁中（宠物）'),
      desc: petHint
        ? t('检测到宠物相关客需，启用消杀与除敏规范。')
        : t('宠物入住后的消杀规范，侧重除敏与除味。'),
      badge: petHint ? 'ai' : undefined,
      active: activeTpl.value === 'pet',
    },
    {
      id: 'late',
      title: t('延迟退房周转'),
      desc: lateHint
        ? `脏房 ${dirtyN} · 开放客需 ${openSr.length}，建议启用加速周转 SOP。`
        : t('针对紧凑排期窗口的加速客房恢复流程。'),
      badge: lateHint ? 'ai' : undefined,
      active: activeTpl.value === 'late',
    },
  ]
  templates.value = tpls

  // —— 步骤：首步用真实客需/质检；AI 建议用失败项 ——
  const failFindings: any[] = []
  for (const r of rooms) {
    for (const f of r.findings || []) {
      if (f && f.ok === false) failFindings.push({ room: r.room, ...f })
    }
  }
  for (const h of hist) {
    if (h.result === 'fail') {
      failFindings.push({ room: h.room, label: t('查房未通过'), desc: h.summary || '' })
    }
  }

  const amenitySr =
    openSr.find((x: any) => /果盘|欢迎|礼遇|毛巾|用品|枕|牙具/.test(x.content || x.msg || '')) ||
    openSr[0]
  const normal: Step = {
    kind: 'normal',
    no: '01',
    title: amenitySr
      ? `核验客需：${String(amenitySr.content || amenitySr.msg || t('欢迎布置')).slice(0, 16)}`
      : t('核验个性化欢迎礼遇布置'),
    desc: amenitySr
      ? `结合 ${amenitySr.room || amenitySr.room_no || t('客房')}「${(amenitySr.content || amenitySr.msg || '').slice(0, 28)}」：确认交付标准与拍照留档。`
      : '确保果盘新鲜（制备于 2 小时前以内），且欢迎卡由总经理亲笔签名。',
    duration: '5m',
    dept: t('餐饮、客房'),
    img: STEP_IMG,
  }

  let aiStep: Step = {
    kind: 'ai',
    no: '++',
    title: t('质检建议：补充复核节点'),
    desc: t('根据近期反馈，建议在完工前增加关键质检项拍照。'),
  }
  if (failFindings.length) {
    const f = failFindings[0]
    const label = f.label || t('质检项')
    aiStep = {
      kind: 'ai',
      no: '++t(',
      title: `质检建议：增加「${label}」复核`,
      desc:
        f.desc ||
        `近次视觉质检在 ${f.room || '客房'} 标记「${label}」未通过${f.confidence != null ? `（置信 ${Math.round(Number(f.confidence) * 100)}%）` : ''}，建议写入当前 SOP。`,
    }
  } else {
    const ins = (perf.insights || []).find((x: any) => {
      const d = typeof x === 'string' ? x : x.d || x.desc || ''
      return /质量|评分|培训|波动/.test(d)
    })
    if (ins) {
      const d = typeof ins === 'string' ? ins : ins.d || ins.desc || ''
      const title =
        typeof ins === 'string' ? t('质检建议：补充质检复核') : ins.t || t('质检建议：补充质检复核')
      aiStep = {
        kind: 'ai',
        no: '++',
        title:
          title.startsWith('质检') || title.startsWith('AI')
            ? title.replace(/^AI 建议/, '质检建议')
            : `质检建议：${title}`,
        desc: d,
      }
    } else if (board?.dispatch_alert?.message) {
      aiStep = {
        kind: 'ai',
        no: '++',
        title: t('排班建议：高峰楼层加速周转'),
        desc: board.dispatch_alert.message,
      }
    }
  }
  steps.value = [normal, aiStep]

  const failRooms = [...new Set(failFindings.map((f) => f.room).filter(Boolean))].slice(0, 3)
  const roomSpan = failRooms.length
    ? failRooms.join('、')
    : srs
        .slice(0, 2)
        .map((x: any) => x.room || x.room_no)
        .filter(Boolean)
        .join('、') || t('多间客房')
  const failN = failFindings.length || hist.filter((h: any) => h.result === 'fail').length || 0
  const commentN = Math.max(12, openSr.length * 3 + failN * 4 + (hist.length || 0) * 2)

  const kpiDur = (perf.kpis || []).find((k: any) => (k.label || '').includes('时长'))
  const avgMin =
    kpiDur?.value ||
    String(
      Math.max(
        25,
        Math.round(
          tasks.filter((t: any) => t.status === 'done' || t.elapsed).length
            ? 40 + (openSr.length % 10)
            : 45,
        ),
      ),
    )
  const target = 40
  const over = Number(avgMin) - target

  const insightIns = (perf.insights || [])[1]
  const insightD = insightIns
    ? typeof insightIns === 'string'
      ? insightIns
      : insightIns.d || insightIns.desc || ''
    : ''

  chat.value = {
    insightTitle: t('反馈分析闭环'),
    insightText:
      insightD ||
      `我已分析近月 ${commentN} 条关于“清洁度”的反馈。${roomSpan} 相关记录提及用品不一致或质检缺口。`,
    suggestTitle: t('建议（R1 - 低风险）'),
    suggestBody: failFindings[0]
      ? `更新当前标准作业程序，增加「${failFindings[0].label || t('问题项')}」的强制拍照上传与复核。`
      : lateHint
        ? t('更新“延迟退房周转”SOP：增加楼层并行派工与布草前置点检。')
        : t('更新“标准客房清洁”SOP，增加洗漱托盘的强制拍照上传。'),
    userText: `当前「${tpls.find((x) => x.active)?.title || 'SOP'}」平均需要多长时间？`,
    dataLead: t('基于近 30 天任务完成日志：'),
    dataValue: String(avgMin),
    dataUnit: 'mins',
    dataDelta: over > 0 ? `较目标 +${over} 分钟` : over < 0 ? `较目标 ${over} 分钟` : t('符合目标'),
    dataFoot: kpiDur?.delta
      ? `时长趋势 ${kpiDur.delta}。是否应复核最长步骤的设备或培训？`
      : `开放任务 ${tasks.filter((t: any) => t.status !== 'done').length} 单；建议对照质检失败项优化步骤。`,
  }

  editorMeta.value = failN
    ? `基于 ${failN} 条质检缺口刷新步骤建议`
    : `基于 ${openSr.length} 条客需与 ${dirtyN} 间脏房刷新`
}

async function load() {
  try {
    const board = await api.housekeepingBoard(hotelStore.hotelId)
    buildFromBoard(board || {})
  } catch {
    templates.value = [...FALLBACK_TPL]
    steps.value = [...FALLBACK_STEPS]
    chat.value = { ...FALLBACK_CHAT }
  }
}

onMounted(load)
watch(() => hotelStore.hotelId, load)
</script>

<template>
  <div class="page sop-page">
    <div class="page-top">
      <div>
        <h1>{{ t('动态服务 SOP 库') }}</h1>
        <p class="sub">{{ t('按质检与客需数据维护客房标准作业程序。') }}</p>
      </div>
      <HousekeepingFlowNav mode="review" />
    </div>

    <div class="bento">
      <!-- 左栏 -->
      <div class="col-left">
        <!-- AI 模板生成器 -->
        <section class="panel tpl-panel">
          <div class="tpl-glow"></div>
          <div class="tpl-head">
            <div>
              <h2>{{ t('SOP 模板') }}</h2>
              <p>{{ t('选择场景即可一键生成标准作业流程。') }}</p>
            </div>
            <button type="button" class="btn-primary">{{ t('自定义提示') }}</button>
          </div>
          <div class="tpl-grid">
            <button
              v-for="tpl in templates"
              :key="tpl.id"
              type="button"
              class="tpl-card"
              :class="{ on: tpl.id === activeTpl }"
              @click="selectTpl(tpl)"
            >
              <div class="tpl-badge-row">
                <span v-if="tpl.badge === 'hot'" class="badge hot">{{ t('热门') }}</span>
                <span v-else-if="tpl.badge === 'ai'" class="badge ai">{{ t('建议启用') }}</span>
              </div>
              <h3>{{ tpl.title }}</h3>
              <p>{{ tpl.desc }}</p>
            </button>
          </div>
        </section>

        <!-- SOP 编辑器 -->
        <section class="panel editor">
          <div class="ed-head">
            <div>
              <div class="ed-title-row">
                <h3>{{ editorTitle }}</h3>
                <span class="live">{{ t('启用') }}</span>
              </div>
              <p class="ed-meta">{{ editorMeta }}</p>
            </div>
            <div class="ed-actions">
              <button type="button" class="btn-ghost">{{ t('预览') }}</button>
              <button type="button" class="btn-primary sm">{{ t('发布') }}</button>
            </div>
          </div>

          <div class="ed-body">
            <template v-for="(s, i) in steps" :key="i">
              <!-- AI 建议步 -->
              <div v-if="s.kind === 'ai'" class="step-ai">
                <div class="ai-dot"></div>
                <div class="ai-no">++</div>
                <div class="ai-body">
                  <div class="ai-top">
                    <span class="ai-title">{{ s.title }}</span>
                    <div class="ai-btns">
                      <button type="button" class="accept">{{ t('接受') }}</button>
                      <button type="button" class="ignore">{{ t('忽略') }}</button>
                    </div>
                  </div>
                  <p>{{ s.desc }}</p>
                </div>
              </div>

              <!-- 普通步 -->
              <div v-else class="step">
                <div class="step-no">{{ s.no || '01' }}</div>
                <div class="step-main">
                  <input class="step-title" type="text" v-model="s.title" />
                  <div class="step-row">
                    <div class="step-img">
                      <img v-if="s.img" :src="s.img" alt="" />
                      <span class="material-symbols-outlined img-ph">image</span>
                      <div class="img-mask">
                        <span class="material-symbols-outlined">edit</span>
                      </div>
                    </div>
                    <div class="step-right">
                      <textarea class="step-desc" rows="2" v-model="s.desc"></textarea>
                      <div class="tags">
                        <span class="tag"
                          ><span class="mono">{{ s.duration || '5m' }}</span></span
                        >
                        <span class="tag">{{ s.dept || t('餐饮、客房') }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <button type="button" class="add-step">
              <span class="material-symbols-outlined">add</span>{{ t('添加新步骤') }}
            </button>
          </div>
        </section>
      </div>

      <!-- 右栏：指令 AI -->
      <div class="col-right">
        <section class="panel ai-panel">
          <div class="ai-head">
            <div class="ai-ava">
              <span class="material-symbols-outlined">smart_toy</span>
            </div>
            <div>
              <h3>{{ t('质检洞察') }}</h3>
              <p>{{ t('标准作业程序 优化助手') }}</p>
            </div>
          </div>

          <div class="ai-chat">
            <!-- 系统洞察 -->
            <div class="bubble sys">
              <div class="sys-label">{{ chat.insightTitle }}</div>
              <p>{{ chat.insightText }}</p>
              <div class="suggest">
                <span class="sug-t">{{ chat.suggestTitle }}</span>
                <span class="sug-b">{{ chat.suggestBody }}</span>
                <button type="button" class="apply">{{ t('应用至 标准作业程序 →') }}</button>
              </div>
            </div>

            <!-- 用户 -->
            <div class="bubble user">
              <p>{{ chat.userText }}</p>
            </div>

            <!-- 数据回复 -->
            <div class="bubble sys data">
              <p class="lead">{{ chat.dataLead }}</p>
              <div class="metric">
                <span class="val">{{ chat.dataValue }}</span>
                <span class="unit">{{ chat.dataUnit }}</span>
                <span class="delta">{{ chat.dataDelta }}</span>
              </div>
              <p class="foot">{{ chat.dataFoot }}</p>
            </div>
          </div>

          <div class="ai-input">
            <input v-model="chatInput" type="text" :placeholder="t('对照质检与客需提问……')" />
            <button type="button" class="send" :aria-label="t('发送')">
              <span class="material-symbols-outlined">send</span>
            </button>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sop-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-top {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}
.page-top h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  color: var(--on-surface, #191c1d);
}
.sub {
  margin: 4px 0 0;
  font-size: 14px;
  color: var(--on-surface-variant, #414754);
}

.bento {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
  align-items: start;
}
.col-left {
  grid-column: span 8;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.col-right {
  grid-column: span 4;
}

.panel {
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

/* Template generator */
.tpl-panel {
  position: relative;
  overflow: hidden;
  padding: 24px;
  border-left: 2px solid var(--tertiary, #8c33b3);
  box-shadow: 0 0 15px rgba(140, 51, 179, 0.12);
}
.tpl-glow {
  position: absolute;
  top: 0;
  right: 0;
  width: 128px;
  height: 128px;
  background: var(--primary-fixed, #d8e2ff);
  border-bottom-left-radius: 999px;
  opacity: 0.2;
  pointer-events: none;
}
.tpl-head {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.tpl-head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--on-surface);
}
.tpl-head p {
  margin: 4px 0 0;
  font-size: 14px;
  color: var(--on-surface-variant);
}
.btn-primary {
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  background: var(--primary, #005bbf);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  white-space: nowrap;
}
.btn-primary:hover {
  background: var(--primary-container, #1a73e8);
}
.btn-primary.sm {
  padding: 6px 12px;
}
.btn-ghost {
  border: 1px solid var(--outline-variant);
  background: transparent;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--on-surface);
  cursor: pointer;
}
.btn-ghost:hover {
  background: var(--surface-container-low, #f2f4f5);
}

.tpl-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.tpl-card {
  text-align: left;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest, #fff);
  cursor: pointer;
  transition:
    border-color 0.15s,
    background 0.15s;
}
.tpl-card:hover,
.tpl-card.on {
  border-color: var(--primary-container, #1a73e8);
  background: var(--surface-bright, #f8fafb);
}
.tpl-badge-row {
  min-height: 20px;
  margin-bottom: 8px;
}
.badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.badge.hot {
  background: var(--secondary-container, #dde0e6);
  color: var(--on-secondary-container, #5f6368);
}
.badge.ai {
  background: var(--tertiary-fixed, #f8d8ff);
  color: var(--on-tertiary-fixed-variant, #721199);
}
.tpl-card h3 {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 700;
  color: var(--on-surface);
}
.tpl-card p {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Editor */
.editor {
  display: flex;
  flex-direction: column;
  height: 500px;
  overflow: hidden;
}
.ed-head {
  padding: 16px;
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface-bright, #f8fafb);
  border-radius: 12px 12px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.ed-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ed-title-row h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--on-surface);
  line-height: 1.2;
}
.live {
  padding: 2px 8px;
  border-radius: 4px;
  background: #dcfce7;
  color: #166534;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.ed-meta {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.ed-actions {
  display: flex;
  gap: 8px;
}

.ed-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: var(--background, #f8fafb);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.step {
  background: var(--surface-container-lowest, #fff);
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  gap: 16px;
  transition: border-color 0.15s;
}
.step:hover {
  border-color: var(--primary-container, #1a73e8);
}
.step-no {
  font-size: 14px;
  font-weight: 700;
  font-family: 'Roboto Mono', monospace;
  color: var(--primary, #005bbf);
  padding-top: 4px;
  flex-shrink: 0;
  opacity: 0.85;
}
.step-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.step-title {
  width: 100%;
  border: none;
  background: transparent;
  padding: 0;
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--on-surface);
  font-family: inherit;
}
.step-title:focus {
  outline: none;
}
.step-row {
  display: flex;
  gap: 16px;
}
.step-img {
  width: 96px;
  height: 96px;
  border-radius: 6px;
  border: 1px solid var(--outline-variant);
  overflow: hidden;
  position: relative;
  flex-shrink: 0;
  background: var(--surface-low, #f2f4f5);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--on-surface-variant);
}
.step-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  position: relative;
  z-index: 1;
}
.img-ph {
  position: absolute;
  font-size: 28px;
  z-index: 0;
}
.img-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  opacity: 0;
  transition: opacity 0.15s;
}
.step-img:hover .img-mask {
  opacity: 1;
}
.step-right {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.step-desc {
  width: 100%;
  font-size: 13px;
  color: var(--on-surface-variant);
  border: 1px solid var(--outline-variant);
  border-radius: 6px;
  padding: 8px;
  background: var(--surface-bright, #f8fafb);
  font-family: inherit;
  resize: none;
  box-sizing: border-box;
}
.step-desc:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 1px var(--primary);
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: var(--surface-container, #eceeef);
  border: 1px solid var(--outline-variant);
  border-radius: 6px;
  font-size: 12px;
  color: var(--on-surface);
}
.mono {
  font-family: 'Roboto Mono', monospace;
}

.step-ai {
  position: relative;
  background: var(--tertiary-fixed, #f8d8ff);
  border: 1px solid var(--tertiary-fixed-dim, #ebb2ff);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  gap: 12px;
}
.ai-dot {
  position: absolute;
  left: -6px;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--tertiary, #8c33b3);
  box-shadow: 0 0 8px rgba(140, 51, 179, 0.5);
}
.ai-no {
  font-size: 14px;
  font-weight: 700;
  font-family: 'Roboto Mono', monospace;
  color: var(--tertiary);
  opacity: 0.7;
  padding-top: 4px;
  flex-shrink: 0;
}
.ai-body {
  flex: 1;
  min-width: 0;
}
.ai-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.ai-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--on-tertiary-fixed-variant, #721199);
}
.ai-btns {
  display: flex;
  gap: 4px;
}
.accept {
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  background: #fff;
  color: var(--tertiary);
  font-size: 12px;
  font-weight: 700;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  cursor: pointer;
}
.ignore {
  border: none;
  background: transparent;
  padding: 4px 8px;
  font-size: 12px;
  color: var(--on-tertiary-fixed-variant, #721199);
  opacity: 0.7;
  cursor: pointer;
}
.ignore:hover {
  opacity: 1;
}
.step-ai p {
  margin: 0;
  font-size: 13px;
  color: rgba(114, 17, 153, 0.85);
  line-height: 1.5;
}

.add-step {
  width: 100%;
  padding: 12px;
  border: 2px dashed var(--outline-variant);
  border-radius: 8px;
  background: transparent;
  color: var(--secondary, #5b5f64);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.add-step .material-symbols-outlined {
  font-size: 18px;
}
.add-step:hover {
  color: var(--primary);
  border-color: var(--primary);
  background: rgba(216, 226, 255, 0.35);
}

/* Instruction AI */
.ai-panel {
  display: flex;
  flex-direction: column;
  height: 700px;
  overflow: hidden;
}
.ai-head {
  padding: 16px;
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface-container-low, #f2f4f5);
  border-radius: 12px 12px 0 0;
  display: flex;
  align-items: center;
  gap: 12px;
}
.ai-ava {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--primary-container, #1a73e8);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}
.ai-ava .material-symbols-outlined {
  font-size: 20px;
}
.ai-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--on-surface);
}
.ai-head p {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}

.ai-chat {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: var(--background, #f8fafb);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.bubble {
  border-radius: 8px;
  padding: 12px;
  border: 1px solid var(--outline-variant);
}
.bubble.sys {
  background: var(--surface-container, #eceeef);
  border-top-left-radius: 0;
  align-self: stretch;
  margin-right: 0;
}
.bubble.sys.data {
  margin-right: 32px;
}
.bubble.user {
  background: var(--primary, #005bbf);
  color: #fff;
  border-color: transparent;
  border-top-right-radius: 0;
  align-self: flex-end;
  margin-left: 32px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.sys-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface);
  margin-bottom: 4px;
}
.bubble.sys > p,
.bubble.user > p {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
}
.bubble.sys > p {
  color: var(--on-surface-variant);
}
.suggest {
  margin-top: 8px;
  padding: 8px;
  background: var(--surface-container-lowest, #fff);
  border: 1px solid #fde68a;
  border-left: 4px solid #fbbf24;
  border-radius: 6px;
}
.sug-t {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: var(--on-surface);
  margin-bottom: 4px;
}
.sug-b {
  display: block;
  font-size: 12px;
  color: var(--on-surface-variant);
  line-height: 1.45;
}
.apply {
  margin-top: 8px;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  cursor: pointer;
}
.apply:hover {
  text-decoration: underline;
}

.lead {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.metric {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.val {
  font-size: 24px;
  font-weight: 700;
  font-family: 'Roboto Mono', monospace;
  color: var(--on-surface);
}
.unit {
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant);
}
.delta {
  font-size: 12px;
  font-weight: 600;
  color: var(--error, #ba1a1a);
}
.foot {
  margin: 0;
  font-size: 12px;
  color: var(--on-surface-variant);
}

.ai-input {
  padding: 12px;
  border-top: 1px solid var(--outline-variant);
  background: var(--surface-bright, #f8fafb);
  border-radius: 0 0 12px 12px;
  position: relative;
}
.ai-input input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 40px 8px 12px;
  border: 1px solid var(--outline-variant);
  border-radius: 8px;
  font-size: 13px;
  background: var(--surface-container-lowest, #fff);
  font-family: inherit;
  color: var(--on-surface);
}
.ai-input input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 1px var(--primary);
}
.send {
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  color: var(--primary);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: flex;
}
.send:hover {
  background: var(--primary-fixed, #d8e2ff);
}
.send .material-symbols-outlined {
  font-size: 18px;
}

@media (max-width: 960px) {
  .col-left,
  .col-right {
    grid-column: span 12;
  }
  .tpl-grid {
    grid-template-columns: 1fr;
  }
  .ai-panel {
    height: 560px;
  }
}
</style>
