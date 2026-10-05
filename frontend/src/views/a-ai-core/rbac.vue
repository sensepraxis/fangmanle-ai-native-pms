<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 系统配置 · 角色权限（支持新建自定义角色）
 */
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../lib/api'
import { toast } from '../../lib/ui'
import { refreshRbac } from '../../store/hotel'
import SystemConfigNav from '../../components/SystemConfigNav.vue'

const roles = ref<any[]>([])
const tree = ref<any[]>([])
const activeRole = ref('admin')
const checked = ref<Set<string>>(new Set())
const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const showCreate = ref(false)
const creating = ref(false)
const createForm = ref({
  code: '',
  name: '',
  description: '',
  copy_from: '' as string,
})

const activeMeta = computed(() => roles.value.find((r) => r.code === activeRole.value))
const checkedCount = computed(() => checked.value.size)
const isSystemActive = computed(() => !!activeMeta.value?.is_system)

async function loadRoles() {
  roles.value = (await api.rbacRoles()) || []
  if (!roles.value.find((r) => r.code === activeRole.value) && roles.value[0]) {
    activeRole.value = roles.value[0].code
  }
}

async function loadTree() {
  tree.value = (await api.rbacPermissions()) || []
}

async function loadRolePerms() {
  if (!activeRole.value) return
  loading.value = true
  try {
    const r = await api.rbacRolePermissions(activeRole.value)
    checked.value = new Set(r?.codes || [])
  } catch (e: any) {
    toast(e?.message || t('加载权限失败'))
  } finally {
    loading.value = false
  }
}

function toggle(code: string) {
  const next = new Set(checked.value)
  if (next.has(code)) next.delete(code)
  else next.add(code)
  if (activeRole.value === 'admin') {
    ;['menu.system.users', 'menu.system.rbac', 'action.system.users', 'action.system.rbac'].forEach(
      (c) => next.add(c),
    )
  }
  checked.value = next
}

function isOn(code: string) {
  return checked.value.has(code)
}

function moduleAllOn(mod: any) {
  const codes = [...(mod.menus || []), ...(mod.actions || [])].map((x: any) => x.code)
  return codes.length > 0 && codes.every((c: string) => checked.value.has(c))
}

function toggleModule(mod: any) {
  const codes = [...(mod.menus || []), ...(mod.actions || [])].map((x: any) => x.code as string)
  const next = new Set(checked.value)
  if (moduleAllOn(mod)) codes.forEach((c) => next.delete(c))
  else codes.forEach((c) => next.add(c))
  if (activeRole.value === 'admin') {
    ;['menu.system.users', 'menu.system.rbac', 'action.system.users', 'action.system.rbac'].forEach(
      (c) => next.add(c),
    )
  }
  checked.value = next
}

async function save() {
  saving.value = true
  try {
    await api.rbacSaveRolePermissions(activeRole.value, [...checked.value])
    toast(t('已保存，已登录用户将立即生效'))
    await refreshRbac()
    await loadRoles()
  } catch (e: any) {
    toast(e?.message || t('保存失败'))
  } finally {
    saving.value = false
  }
}

async function resetDefaults() {
  const tip = isSystemActive.value
    ? `恢复「${activeMeta.value?.name}」为系统默认矩阵？`
    : `清空「${activeMeta.value?.name}」的全部勾选？`
  if (!confirm(tip)) return
  try {
    const r = await api.rbacResetRoleDefaults(activeRole.value)
    checked.value = new Set(r?.codes || [])
    toast(isSystemActive.value ? t('已恢复默认') : t('已清空权限'))
    await refreshRbac()
    await loadRoles()
  } catch (e: any) {
    toast(e?.message || t('操作失败'))
  }
}

function openCreate() {
  createForm.value = {
    code: '',
    name: '',
    description: '',
    copy_from: activeRole.value === 'admin' ? 'fd' : activeRole.value,
  }
  showCreate.value = true
}

async function submitCreate() {
  creating.value = true
  try {
    const payload: Record<string, unknown> = {
      code: createForm.value.code.trim(),
      name: createForm.value.name.trim(),
      description: createForm.value.description.trim(),
    }
    if (createForm.value.copy_from) payload.copy_from = createForm.value.copy_from
    const r = await api.rbacCreateRole(payload)
    toast(t('角色已创建'))
    showCreate.value = false
    await loadRoles()
    if (r?.code) activeRole.value = r.code
  } catch (e: any) {
    toast(e?.message || t('创建失败'))
  } finally {
    creating.value = false
  }
}

async function removeRole() {
  if (!activeMeta.value || activeMeta.value.is_system) return
  const name = activeMeta.value.name
  if (!confirm(`删除角色「${name}」？此操作不可恢复。`)) return
  try {
    await api.rbacDeleteRole(activeRole.value)
    toast(t('已删除'))
    activeRole.value = 'admin'
    await loadRoles()
  } catch (e: any) {
    toast(e?.message || t('删除失败'))
  }
}

watch(activeRole, () => loadRolePerms())

onMounted(async () => {
  try {
    await Promise.all([loadRoles(), loadTree()])
    await loadRolePerms()
  } catch (e: any) {
    loadError.value = e?.message || t('加载失败')
  }
})
</script>

<template>
  <main class="rb-page">
    <div class="rb-wrap">
      <SystemConfigNav />

      <div class="rb-head">
        <div>
          <h1 class="rb-title">{{ t('角色权限') }}</h1>
          <p v-if="loadError" class="rb-err">{{ loadError }}</p>
        </div>
      </div>

      <div class="rb-toolbar">
        <button class="btn-primary" type="button" @click="openCreate">
          <span class="material-symbols-outlined">add</span>
          {{ t('新建角色') }}
        </button>
        <button class="btn-ghost" type="button" @click="resetDefaults">
          {{ isSystemActive ? t('恢复默认') : t('清空权限') }}
        </button>
        <button
          v-if="activeMeta && !activeMeta.is_system"
          class="btn-ghost danger"
          type="button"
          @click="removeRole"
        >
          {{ t('删除角色') }}
        </button>
        <button class="btn-primary" type="button" :disabled="saving" @click="save">
          <span class="material-symbols-outlined">save</span>
          {{ saving ? t('保存中…') : t('保存') }}
        </button>
      </div>

      <div class="layout">
        <aside class="roles-card">
          <div class="card-head">
            <h2>
              <span class="material-symbols-outlined ico">badge</span>
              {{ t('角色') }}
              <span class="meta">（{{ roles.length }}）</span>
            </h2>
          </div>
          <button
            v-for="r in roles"
            :key="r.code"
            type="button"
            class="role"
            :class="{ on: activeRole === r.code }"
            @click="activeRole = r.code"
          >
            <div class="role-top">
              <b>{{ t(r.name) }}</b>
              <span class="pill">{{ r.permission_count || 0 }}</span>
            </div>
            <span class="role-code">
              {{ r.code }}
              <span v-if="r.is_system" class="sys">{{ t('系统') }}</span>
              <span v-else class="custom">{{ t('自定义') }}</span>
            </span>
          </button>
        </aside>

        <section class="perms-card">
          <div class="card-head">
            <h2>
              <span class="material-symbols-outlined ico">admin_panel_settings</span>
              {{ activeMeta?.name ? t(activeMeta.name) : t('权限') }}
              <span class="meta">（{{ t('已选') }} {{ checkedCount }} {{ t('项）') }}</span>
            </h2>
          </div>

          <div v-if="loading" class="empty">{{ t('加载中…') }}</div>
          <template v-else>
            <div v-for="mod in tree" :key="mod.module" class="mod">
              <div class="mod-head">
                <label class="chk">
                  <input type="checkbox" :checked="moduleAllOn(mod)" @change="toggleModule(mod)" />
                  <strong>{{ t(mod.label) }}</strong>
                </label>
              </div>
              <div class="grid">
                <div>
                  <div class="cap">{{ t('二级菜单') }}</div>
                  <label v-for="m in mod.menus" :key="m.code" class="chk item">
                    <input type="checkbox" :checked="isOn(m.code)" @change="toggle(m.code)" />
                    <span>{{ t(m.name) }}</span>
                  </label>
                </div>
                <div>
                  <div class="cap">{{ t('操作权限') }}</div>
                  <label v-for="a in mod.actions" :key="a.code" class="chk item">
                    <input type="checkbox" :checked="isOn(a.code)" @change="toggle(a.code)" />
                    <span>{{ t(a.name) }}</span>
                  </label>
                  <div v-if="!(mod.actions || []).length" class="hint">{{ t('无独立操作点') }}</div>
                </div>
              </div>
            </div>
          </template>
        </section>
      </div>
    </div>

    <div v-if="showCreate" class="modal-mask" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-head">
          <h3>{{ t('新建角色') }}</h3>
          <button type="button" class="icon-x" @click="showCreate = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <label
            >{{ t('角色名称') }}
            <input v-model="createForm.name" type="text" :placeholder="t('如：客房主管')" />
          </label>
          <label
            >{{ t('角色编码') }}
            <input
              v-model="createForm.code"
              type="text"
              :placeholder="t('如：hk（小写字母开头）')"
            />
          </label>
          <label class="full"
            >{{ t('说明') }}
            <input v-model="createForm.description" type="text" :placeholder="t('可选')" />
          </label>
          <label class="full"
            >{{ t('复制权限自') }}
            <select v-model="createForm.copy_from">
              <option value="">{{ t('不复制（空白权限）') }}</option>
              <option v-for="r in roles" :key="r.code" :value="r.code">
                {{ r.name }}（{{ r.code }}）
              </option>
            </select>
          </label>
        </div>
        <div class="modal-foot">
          <button class="btn-ghost" type="button" @click="showCreate = false">
            {{ t('取消') }}
          </button>
          <button class="btn-primary" type="button" :disabled="creating" @click="submitCreate">
            {{ creating ? t('创建中…') : t('创建') }}
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.rb-page {
  min-height: 100%;
  padding: 24px 20px 32px;
  background: var(--surface-container-lowest, #fff);
}
.rb-wrap {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.rb-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.rb-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
}
.rb-err {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--error, #ba1a1a);
}
.rb-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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
}
.btn-ghost.danger {
  border-color: #f5b5b5;
  color: #dc2626;
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
.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.btn-primary .material-symbols-outlined {
  font-size: 18px;
}
.layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 16px;
  align-items: start;
}
.roles-card,
.perms-card {
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
.card-head .meta {
  font-size: 12px;
  font-weight: 400;
  color: var(--on-surface-variant, #5b616e);
}
.role {
  width: 100%;
  text-align: left;
  border: 1px solid var(--outline-variant, #c1c6d6);
  background: #fff;
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  margin-bottom: 8px;
}
.role:last-child {
  margin-bottom: 0;
}
.role-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.role b {
  font-size: 14px;
  color: var(--on-surface, #1f2329);
}
.role-code {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.sys,
.custom {
  font-family: inherit;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
}
.sys {
  background: #eef2ff;
  color: #4338ca;
}
.custom {
  background: #ecfdf5;
  color: #047857;
}
.pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-container-high, #e6e8e9);
  color: var(--on-surface-variant, #5b616e);
}
.role.on {
  border-color: var(--primary, #005bbf);
  background: rgba(0, 91, 191, 0.06);
}
.role.on .pill {
  background: rgba(0, 91, 191, 0.12);
  color: var(--primary, #005bbf);
}
.mod {
  padding: 14px 0;
  border-bottom: 1px solid rgba(193, 198, 214, 0.45);
}
.mod:last-child {
  border-bottom: 0;
}
.mod-head {
  margin-bottom: 10px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 24px;
}
.cap {
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
  margin-bottom: 8px;
  font-weight: 600;
}
.chk {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--on-surface, #1f2329);
}
.item {
  margin: 6px 0;
}
.hint,
.empty {
  color: var(--on-surface-variant, #5b616e);
  font-size: 13px;
}
.empty {
  text-align: center;
  padding: 32px 0;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.modal {
  width: min(520px, 100%);
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--outline-variant, #e2e5eb);
}
.modal-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}
.icon-x {
  border: none;
  background: none;
  cursor: pointer;
  color: var(--on-surface-variant, #5b616e);
}
.modal-body {
  padding: 16px 20px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.modal-body label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
}
.modal-body label.full {
  grid-column: 1 / -1;
}
.modal-body input,
.modal-body select {
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  font: inherit;
  color: var(--on-surface, #1f2329);
  background: #fff;
}
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--outline-variant, #e2e5eb);
}
@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
