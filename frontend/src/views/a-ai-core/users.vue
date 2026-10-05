<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 系统配置 · 用户与账号
 */
import { computed, onMounted, ref } from 'vue'
import { api } from '../../lib/api'
import { toast } from '../../lib/ui'
import SystemConfigNav from '../../components/SystemConfigNav.vue'

const ROLE_OPTS = ref<{ code: string; name: string }[]>([])

const rows = ref<any[]>([])
const loading = ref(false)
const loadError = ref('')
const saving = ref(false)
const showForm = ref(false)
const editing = ref<any | null>(null)
const pwdEditing = ref(false)
const form = ref({
  username: '',
  password: '',
  full_name: '',
  role_code: 'fd',
  phone: '',
  is_active: true,
})

function startPwdEdit() {
  pwdEditing.value = true
  form.value.password = ''
}
function cancelPwdEdit() {
  pwdEditing.value = false
  form.value.password = ''
}

const activeCount = computed(() => rows.value.filter((u) => u.is_active).length)

async function loadRoles() {
  try {
    const list = (await api.rbacRoles()) || []
    ROLE_OPTS.value = list.map((r: any) => ({ code: r.code, name: r.name }))
  } catch {
    ROLE_OPTS.value = [
      { code: 'admin', name: '系统管理员' },
      { code: 'gm', name: '店长' },
      { code: 'rm', name: '收益经理' },
      { code: 'fd', name: '前台' },
    ]
  }
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    await loadRoles()
    rows.value = (await api.rbacUsers()) || []
  } catch (e: any) {
    loadError.value = e?.message || t('加载失败')
    rows.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  pwdEditing.value = true
  const defaultRole =
    ROLE_OPTS.value.find((r) => r.code === 'fd')?.code || ROLE_OPTS.value[0]?.code || 'fd'
  form.value = {
    username: '',
    password: '',
    full_name: '',
    role_code: defaultRole,
    phone: '',
    is_active: true,
  }
  showForm.value = true
}

function openEdit(u: any) {
  editing.value = u
  pwdEditing.value = false
  form.value = {
    username: u.username,
    password: '',
    full_name: u.full_name || '',
    role_code: u.role_code || 'fd',
    phone: u.phone || '',
    is_active: !!u.is_active,
  }
  showForm.value = true
}

function closeEditor() {
  showForm.value = false
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      const payload: Record<string, unknown> = {
        full_name: form.value.full_name,
        role_code: form.value.role_code,
        phone: form.value.phone,
        is_active: form.value.is_active,
      }
      if (form.value.password.trim()) payload.password = form.value.password.trim()
      await api.rbacUpdateUser(editing.value.id, payload)
      toast(t('已更新'))
    } else {
      if (!form.value.username.trim() || !form.value.password.trim()) {
        toast(t('用户名与密码必填'))
        return
      }
      await api.rbacCreateUser({
        username: form.value.username.trim(),
        password: form.value.password.trim(),
        full_name: form.value.full_name.trim(),
        role_code: form.value.role_code,
        phone: form.value.phone.trim(),
        is_active: form.value.is_active,
      })
      toast(t('已创建账号'))
    }
    showForm.value = false
    await load()
  } catch (e: any) {
    toast(e?.message || t('保存失败'))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="ua-page">
    <div class="ua-wrap">
      <SystemConfigNav />

      <div class="ua-head">
        <div>
          <h1 class="ua-title">{{ t('用户与账号') }}</h1>
          <p v-if="loadError" class="ua-err">{{ loadError }}</p>
        </div>
      </div>

      <div class="ua-toolbar">
        <button class="btn-primary" type="button" @click="openCreate">
          <span class="material-symbols-outlined">add</span>
          {{ t('创建账号') }}
        </button>
      </div>

      <section class="ua-card">
        <div class="card-head">
          <h2>
            <span class="material-symbols-outlined ico">group</span>
            {{ t('账号列表') }}
            <span class="meta">{{
              t('（{total} 个 · 启用 {active}）', { total: rows.length, active: activeCount })
            }}</span>
          </h2>
        </div>

        <div v-if="loading" class="empty">{{ t('加载中…') }}</div>
        <div v-else class="table-wrap">
          <table class="ua-table">
            <thead>
              <tr>
                <th>{{ t('用户名') }}</th>
                <th>{{ t('姓名') }}</th>
                <th>{{ t('角色') }}</th>
                <th>{{ t('手机') }}</th>
                <th>{{ t('状态') }}</th>
                <th class="right">{{ t('操作') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in rows" :key="u.id">
                <td class="code">{{ u.username }}</td>
                <td class="name">{{ u.full_name ? t(u.full_name) : '—' }}</td>
                <td>
                  <span class="tag">{{ u.role_name ? t(u.role_name) : u.role_code || '—' }}</span>
                </td>
                <td>{{ u.phone || '—' }}</td>
                <td>
                  <span class="status" :class="u.is_active ? 'on' : 'off'">
                    <span class="dot" />
                    {{ u.is_active ? t('启用') : t('停用') }}</span
                  >
                </td>
                <td class="right">
                  <div class="ops">
                    <button class="op" type="button" @click="openEdit(u)">{{ t('编辑') }}</button>
                  </div>
                </td>
              </tr>
              <tr v-if="!rows.length">
                <td colspan="6" class="empty">{{ t('暂无账号，请先创建') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="closeEditor">
      <div class="modal">
        <div class="modal-head">
          <h3>{{ editing ? t('编辑账号') : t('创建账号') }}</h3>
          <button type="button" class="icon-x" @click="closeEditor">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <label
            >{{ t('用户名') }}<input v-model="form.username" type="text" :disabled="!!editing"
          /></label>
          <template v-if="!editing">
            <label
              >{{ t('密码') }}
              <input v-model="form.password" type="password" autocomplete="new-password" />
            </label>
          </template>
          <template v-else>
            <div class="pwd-row">
              <span class="pwd-label">{{ t('密码') }}</span>
              <template v-if="!pwdEditing">
                <span class="pwd-mask">••••••••</span>
                <button type="button" class="btn-primary sm" @click="startPwdEdit">
                  {{ t('重新配置') }}
                </button>
              </template>
              <template v-else>
                <input v-model="form.password" type="password" autocomplete="new-password" />
                <button type="button" class="btn-primary sm" @click="cancelPwdEdit">
                  {{ t('取消') }}
                </button>
              </template>
            </div>
          </template>
          <label>{{ t('姓名') }}<input v-model="form.full_name" type="text" /></label>
          <label
            >{{ t('角色') }}
            <select v-model="form.role_code">
              <option v-for="r in ROLE_OPTS" :key="r.code" :value="r.code">{{ r.name }}</option>
            </select>
          </label>
          <label class="full">{{ t('手机') }}<input v-model="form.phone" type="text" /></label>
          <label class="check">
            <input v-model="form.is_active" type="checkbox" />
            {{ t('启用账号') }}</label
          >
        </div>
        <div class="modal-foot">
          <button class="btn-ghost" type="button" @click="closeEditor">{{ t('取消') }}</button>
          <button class="btn-primary" type="button" :disabled="saving" @click="save">
            {{ saving ? t('保存中…') : t('保存') }}
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.ua-page {
  min-height: 100%;
  padding: 24px 20px 32px;
  background: var(--surface-container-lowest, #fff);
}
.ua-wrap {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.ua-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.ua-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--on-surface, #1f2329);
}
.ua-err {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--error, #ba1a1a);
}
.ua-toolbar {
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
.ua-card {
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
}
.card-head .ico {
  color: var(--primary, #005bbf);
}
.card-head .meta {
  font-size: 12px;
  font-weight: 400;
  color: var(--on-surface-variant, #5b616e);
}
.table-wrap {
  overflow-x: auto;
}
.ua-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}
.ua-table th {
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
  border-bottom: 1px solid var(--outline-variant, #c1c6d6);
  white-space: nowrap;
}
.ua-table td {
  padding: 14px;
  font-size: 14px;
  border-bottom: 1px solid rgba(193, 198, 214, 0.45);
  vertical-align: middle;
}
.ua-table th.right,
.ua-table td.right {
  text-align: right;
}
.ua-table tbody tr:hover {
  background: var(--surface-container-low, #f2f4f5);
}
.name {
  font-weight: 600;
}
.code {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 13px;
}
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--surface-container-high, #e6e8e9);
  font-size: 12px;
  color: var(--on-surface-variant, #5b616e);
}
.status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
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
.status.on {
  background: #eafaf0;
  border-color: #a7e3b8;
  color: #16a34a;
}
.status.on .dot {
  background: #16a34a;
}
.status.off {
  background: #fdecec;
  border-color: #f5b5b5;
  color: #dc2626;
}
.status.off .dot {
  background: #dc2626;
}
.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.op {
  border: none;
  background: none;
  color: var(--primary, #005bbf);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
.empty {
  text-align: center;
  padding: 32px !important;
  color: var(--on-surface-variant, #5b616e);
  font-size: 14px;
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
  width: min(560px, 100%);
  max-height: 90vh;
  overflow: auto;
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
.modal-body label.check {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  padding-top: 22px;
}
.modal-body input,
.modal-body select {
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  outline: none;
  font: inherit;
  color: var(--on-surface, #1f2329);
  background: #fff;
}
.modal-body input:focus,
.modal-body select:focus {
  border-color: var(--primary, #005bbf);
}
.modal-body input:disabled {
  background: #f2f4f5;
}
.pwd-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  grid-column: 1 / -1;
}
.pwd-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant, #5b616e);
  min-width: 48px;
}
.pwd-mask {
  flex: 1;
  min-width: 120px;
  padding: 8px 12px;
  border: 1px solid var(--outline-variant, #c1c6d6);
  border-radius: 8px;
  background: #f8fafc;
  letter-spacing: 0.12em;
}
.pwd-row input {
  flex: 1;
  min-width: 140px;
}
.btn-primary.sm {
  padding: 7px 12px;
  font-size: 12px;
}
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--outline-variant, #e2e5eb);
}
</style>
