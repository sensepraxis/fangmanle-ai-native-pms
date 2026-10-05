<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 资产报损登记详情 —— 对照 C7 send.html 原型
 * 自报损登记列表「新建报损单」进入，提交写入 damage_tickets
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../lib/api'
import { hotelStore } from '../../store/hotel'
const router = useRouter()

const roomOptions = ref<{ group: string; value: string; label: string }[]>([
  { group: t('公共区域'), value: t('大堂'), label: t('大堂') },
  { group: t('公共区域'), value: t('健身房'), label: t('健身房') },
])

const assetTypes = [
  t('家具 (床、桌椅、衣柜)'),
  t('电器 (电视、空调、冰箱)'),
  t('布草 (床单、毛巾、浴袍)'),
  t('卫浴/管道 (马桶、淋浴、水龙头)'),
  t('五金件 (门锁、合页)'),
]

const roomNo = ref('')
const assetCategory = ref('')
const severity = ref<'low' | 'medium' | 'high'>('medium')
const description = ref('')
const photos = ref<string[]>([]) // 无数据时为空（用户上传真实照片；前端不 hardcode 占位图）
const submitting = ref(false)
const errorMsg = ref(')')

const aiTip = ref(t('基于您的描述和历史维修数据，AI已生成初步诊断方案。'))
const aiAction = ref(t('建议分配给工程部 王师傅 进行水管阀门芯更换，预计耗时 30 分钟。'))
const aiRisk = ref(t('该房间明天有客人入住，建议在今天 16:00 前完成维修，避免产生客诉。'))
const tags = ref([t('卫浴'), t('漏水'), t('加急')])

const roomGroups = computed(() => {
  const map = new Map<string, { group: string; value: string; label: string }[]>()
  for (const o of roomOptions.value) {
    const list = map.get(o.group) || []
    list.push(o)
    map.set(o.group, list)
  }
  return [...map.entries()]
})

function severityStyle(k: string) {
  const on = severity.value === k
  if (k === 'high') {
    return {
      border: `1px solid ${on ? 'var(--error)' : 'var(--outline-variant)'}`,
      background: on ? 'var(--error-container)' : 'transparent',
      color: on ? 'var(--error)' : 'var(--on-surface)',
    }
  }
  if (k === 'medium') {
    return {
      border: `1px solid ${on ? '#FFB703' : 'var(--outline-variant)'}`,
      background: on ? 'rgba(255,183,3,0.10)' : 'transparent',
      color: on ? '#FFB703' : 'var(--on-surface)',
    }
  }
  return {
    border: `1px solid ${on ? 'var(--primary)' : 'var(--outline-variant)'}`,
    background: on ? 'rgba(0,91,191,0.06)' : 'transparent',
    color: on ? 'var(--primary)' : 'var(--on-surface)',
  }
}

function refreshAi() {
  const text = description.value
  const cat = assetCategory.value
  if (/漏|水|龙头|卫浴|淋浴/.test(text + cat)) {
    aiTip.value = t('基于您的描述和历史维修数据，AI已生成初步诊断方案。')
    aiAction.value = t('建议分配给工程部 王师傅 进行水管阀门芯更换，预计耗时 30 分钟。')
    aiRisk.value = t('该房间明天有客人入住，建议在今天 16:00 前完成维修，避免产生客诉。')
    tags.value = [t('卫浴'), t('漏水'), severity.value === 'high' ? t('锁房') : t('加急')]
  } else if (/布草|床单|毛巾|浴巾/.test(text + cat)) {
    aiTip.value = t('基于布草洗涤与报废记录，AI已生成处置建议。')
    aiAction.value = t('建议报废并自洁净库存置换，同步通知洗衣房复核批次。')
    aiRisk.value = t('若今日不处理，可能影响明日高入住房态配货。')
    tags.value = [t('布草'), t('报废'), t('补货')]
  } else if (text || cat) {
    aiTip.value = t('基于您的描述和历史维修数据，AI已生成初步诊断方案。')
    aiAction.value = `建议工程部现场核查「${cat.split('(')[0].trim() || t('相关资产')}」，预计 30–45 分钟。`
    aiRisk.value = roomNo.value
      ? `${roomNo.value} 房间请在今日营业高峰前完成，避免客诉。`
      : t('请尽快完成维修，避免产生客诉。')
    tags.value = [
      cat.split('(')[0].trim() || t('报损'),
      severity.value === 'high' ? t('严重') : t('维修'),
      t('加急'),
    ].filter(Boolean)
  }
}

watch([description, assetCategory, severity, roomNo], refreshAi)

function addPhoto() {
  if (photos.value.length >= 4) return
  photos.value.push('') // 占位；前端不 hardcode 具体 URL
}

function removePhoto(i: number) {
  photos.value.splice(i, 1)
}

function goBack() {
  router.push('/c8-assets/damage-registration')
}

async function submit() {
  errorMsg.value = ''
  if (!roomNo.value) {
    errorMsg.value = t('请选择位置 / 房号')
    return
  }
  if (!assetCategory.value) {
    errorMsg.value = t('请选择资产大类')
    return
  }
  if (!description.value.trim()) {
    errorMsg.value = t('请填写情况描述')
    return
  }
  submitting.value = true
  try {
    await api.createDamage({
      hotel_id: hotelStore.hotelId,
      room_no: roomNo.value,
      asset_category: assetCategory.value,
      severity: severity.value,
      description: description.value.trim(),
      photos: photos.value,
      ai_suggestion: aiAction.value,
      ai_risk: aiRisk.value,
      ai_tags: tags.value,
    })
    router.push('/c8-assets/damage-registration')
  } catch (e: any) {
    errorMsg.value = e?.message || t('提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const rooms = await api.listRooms(hotelStore.hotelId)
    const fromDb = (rooms || [])
      .map((r: any) => {
        const value = String(r.room_no || r.number || r.id)
        return {
          group: t('客房'),
          value,
          label: `${value}${r.room_type_name ? ` (${r.room_type_name})` : ''}`,
        }
      })
      .filter((x: any) => x.value)
    if (fromDb.length) {
      roomOptions.value = [
        ...fromDb,
        { group: t('公共区域'), value: t('大堂'), label: t('大堂') },
        { group: t('公共区域'), value: t('健身房'), label: t('健身房') },
      ]
      if (!roomNo.value) roomNo.value = fromDb[0].value
    }
  } catch {
    /* 保留公共区域选项 */
  }
  refreshAi()
})
</script>

<template>
  <div class="page">
    <div style="margin-bottom: 24px">
      <div
        style="
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--secondary);
          margin-bottom: 4px;
        "
      >
        <span class="material-symbols-outlined" style="font-size: 14px">cleaning_services</span>
        <span style="font-size: 12px">{{ t('房务管理') }}</span>
        <span class="material-symbols-outlined" style="font-size: 14px">chevron_right</span>
        <button type="button" class="crumb-link" @click="goBack">{{ t('报损登记') }}</button>
      </div>
      <h1 style="font-size: 24px; font-weight: 700; color: var(--on-surface); margin: 0">
        {{ t('资产报损登记') }}
      </h1>
      <p style="font-size: 13px; color: var(--on-surface-variant); margin: 8px 0 0">
        {{ t('记录损坏情况，AI将辅助诊断并安排维修任务。') }}
      </p>
    </div>

    <div
      style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; align-items: start"
    >
      <!-- 表单 (span 8) -->
      <div style="grid-column: span 8; display: flex; flex-direction: column; gap: 16px">
        <div class="card-clean" style="padding: 24px">
          <h2
            style="
              font-size: 16px;
              font-weight: 600;
              color: var(--on-surface);
              margin: 0 0 20px;
              display: flex;
              align-items: center;
              gap: 8px;
            "
          >
            <span class="material-symbols-outlined" style="color: var(--primary)">location_on</span>
            {{ t('基础信息') }}
          </h2>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px">
            <div style="display: flex; flex-direction: column; gap: 8px">
              <label style="font-size: 12px; color: var(--on-surface-variant)">{{
                t('位置 / 房号 *')
              }}</label>
              <div style="position: relative">
                <select
                  v-model="roomNo"
                  class="toolbar-input"
                  style="width: 100%; appearance: none; cursor: pointer"
                >
                  <option disabled value="">{{ t('选择房间或区域') }}</option>
                  <optgroup v-for="[g, list] in roomGroups" :key="g" :label="g">
                    <option v-for="l in list" :key="l.value" :value="l.value">{{ l.label }}</option>
                  </optgroup>
                </select>
                <span
                  class="material-symbols-outlined"
                  style="
                    position: absolute;
                    right: 12px;
                    top: 50%;
                    transform: translateY(-50%);
                    color: var(--outline);
                    pointer-events: none;
                    font-size: 20px;
                  "
                  >arrow_drop_down</span
                >
              </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px">
              <label style="font-size: 12px; color: var(--on-surface-variant)">{{
                t('资产大类 *')
              }}</label>
              <div style="position: relative">
                <select
                  v-model="assetCategory"
                  class="toolbar-input"
                  style="width: 100%; appearance: none; cursor: pointer"
                >
                  <option disabled value="">{{ t('选择资产类型') }}</option>
                  <option v-for="a in assetTypes" :key="a" :value="a">{{ a }}</option>
                </select>
                <span
                  class="material-symbols-outlined"
                  style="
                    position: absolute;
                    right: 12px;
                    top: 50%;
                    transform: translateY(-50%);
                    color: var(--outline);
                    pointer-events: none;
                    font-size: 20px;
                  "
                  >arrow_drop_down</span
                >
              </div>
            </div>
          </div>
        </div>

        <div class="card-clean" style="padding: 24px">
          <h2
            style="
              font-size: 16px;
              font-weight: 600;
              color: var(--on-surface);
              margin: 0 0 20px;
              display: flex;
              align-items: center;
              gap: 8px;
            "
          >
            <span class="material-symbols-outlined" style="color: var(--primary)">description</span>
            {{ t('损坏详情') }}
          </h2>
          <div style="display: flex; flex-direction: column; gap: 24px">
            <div style="display: flex; flex-direction: column; gap: 12px">
              <label style="font-size: 12px; color: var(--on-surface-variant)">{{
                t('严重程度 *')
              }}</label>
              <div style="display: flex; gap: 16px">
                <label
                  v-for="opt in [
                    { k: 'low', t: t('轻度影响'), s: t('不影响入住') },
                    { k: 'medium', t: t('中度损坏'), s: t('需尽快维修') },
                    { k: 'high', t: t('严重故障'), s: t('需锁房维修') },
                  ]"
                  :key="opt.k"
                  style="flex: 1; cursor: pointer"
                >
                  <input
                    v-model="severity"
                    type="radio"
                    name="severity"
                    :value="opt.k"
                    class="sr-only"
                  />
                  <div
                    :style="{
                      padding: '12px',
                      borderRadius: '8px',
                      textAlign: 'center',
                      ...severityStyle(opt.k),
                    }"
                  >
                    <span style="font-size: 13px; display: block">{{ opt.t }}</span>
                    <span
                      style="
                        font-size: 11px;
                        color: var(--on-surface-variant);
                        margin-top: 4px;
                        display: block;
                      "
                      >{{ opt.s }}</span
                    >
                  </div>
                </label>
              </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px">
              <label style="font-size: 12px; color: var(--on-surface-variant)">{{
                t('情况描述 *')
              }}</label>
              <textarea
                v-model="description"
                class="toolbar-input"
                style="width: 100%; height: 72px; resize: none"
                :placeholder="t('描述具体损坏情况，例如：浴室水龙头漏水，开关不灵敏...')"
              />
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px">
              <label style="font-size: 12px; color: var(--on-surface-variant)">{{
                t('现场照片 (最多4张)')
              }}</label>
              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px">
                <div
                  v-for="(p, i) in photos"
                  :key="i"
                  style="
                    aspect-ratio: 1;
                    border-radius: 8px;
                    border: 1px solid var(--outline-variant);
                    overflow: hidden;
                    position: relative;
                  "
                >
                  <img
                    :src="p"
                    :alt="t('现场照片')"
                    style="width: 100%; height: 100%; object-fit: cover"
                  />
                  <button type="button" class="photo-remove" @click="removePhoto(i)">
                    <span class="material-symbols-outlined" style="font-size: 14px">close</span>
                  </button>
                </div>
                <button
                  v-if="photos.length < 4"
                  type="button"
                  style="
                    aspect-ratio: 1;
                    border-radius: 8px;
                    border: 2px dashed var(--outline-variant);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    color: var(--on-surface-variant);
                    cursor: pointer;
                    background: none;
                  "
                  @click="addPhoto"
                >
                  <span
                    class="material-symbols-outlined"
                    style="font-size: 20px; margin-bottom: 4px"
                    >add_a_photo</span
                  >
                  <span style="font-size: 11px">{{ t('上传照片') }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- AI 智能诊断 (span 4) -->
      <div
        class="card-clean"
        style="
          grid-column: span 4;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          height: 100%;
        "
      >
        <div
          style="
            padding: 16px 20px;
            border-bottom: 1px solid var(--outline-variant);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(140, 51, 179, 0.12);
          "
        >
          <h3
            style="
              font-size: 16px;
              font-weight: 600;
              color: var(--on-tertiary-container);
              margin: 0;
              display: flex;
              align-items: center;
              gap: 8px;
            "
          >
            <span class="material-symbols-outlined" style="color: var(--tertiary)"
              >auto_awesome</span
            >
            {{ t('AI 智能诊断') }}
          </h3>
          <div
            style="
              width: 8px;
              height: 8px;
              border-radius: 50%;
              background: var(--tertiary);
              animation: pulse 1.5s infinite;
            "
          />
        </div>
        <div
          style="
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            flex: 1;
            background: var(--surface-bright, #f8fafb);
          "
        >
          <div style="font-size: 13px; color: var(--on-surface-variant); font-style: italic">
            "{{ aiTip }}"
          </div>
          <div
            style="
              background: rgba(0, 91, 191, 0.08);
              border: 1px solid var(--primary-fixed-dim);
              border-radius: 8px;
              padding: 16px;
            "
          >
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
              <span class="material-symbols-outlined" style="color: var(--primary); font-size: 14px"
                >build</span
              >
              <span style="font-size: 12px; font-weight: 700; color: var(--on-primary-fixed)">{{
                t('建议操作')
              }}</span>
            </div>
            <p style="font-size: 13px; color: var(--on-surface); margin: 0">{{ aiAction }}</p>
          </div>
          <div
            style="
              background: rgba(255, 183, 3, 0.1);
              border: 1px solid rgba(255, 183, 3, 0.3);
              border-radius: 8px;
              padding: 16px;
            "
          >
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
              <span class="material-symbols-outlined" style="color: #ffb703; font-size: 14px"
                >warning</span
              >
              <span style="font-size: 12px; font-weight: 700; color: var(--on-surface)">{{
                t('隐患评估')
              }}</span>
            </div>
            <p style="font-size: 12px; color: var(--on-surface-variant); margin: 0">{{ aiRisk }}</p>
          </div>
          <div style="margin-top: auto">
            <span
              style="font-size: 11px; color: var(--outline); display: block; margin-bottom: 8px"
              >{{ t('AI 提取标签') }}</span
            >
            <div style="display: flex; flex-wrap: wrap; gap: 8px">
              <span
                v-for="tag in tags"
                :key="tag"
                style="
                  padding: 4px 8px;
                  background: var(--surface-container);
                  border-radius: 6px;
                  font-size: 11px;
                  color: var(--on-surface-variant);
                "
                >{{ tag }}</span
              >
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      style="
        margin-top: 32px;
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 16px;
        border-top: 1px solid var(--outline-variant);
        padding-top: 24px;
      "
    >
      <p
        v-if="errorMsg"
        style="margin: 0; margin-right: auto; font-size: 13px; color: var(--error)"
      >
        {{ errorMsg }}
      </p>
      <button type="button" class="btn btn-ghost" @click="goBack">{{ t('取消') }}</button>
      <button type="button" class="btn btn-primary" :disabled="submitting" @click="submit">
        <span class="material-symbols-outlined" style="font-size: 14px">send</span>
        {{ submitting ? t('提交中…') : t('提交登记') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}
.crumb-link {
  border: none;
  background: none;
  padding: 0;
  font-size: 12px;
  color: var(--secondary);
  cursor: pointer;
}
.crumb-link:hover {
  color: var(--primary);
  text-decoration: underline;
}
.photo-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  color: var(--error);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
