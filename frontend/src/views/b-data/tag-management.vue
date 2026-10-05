<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'

/**
 * 标签管理：维护 AI 找人可用的标签词表（含规则编辑与应用打标）
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import MasterTagLibrary from './master-tag-library.vue'

const router = useRouter()
const libRef = ref<{ openNewDialog: () => void } | null>(null)

function goCohort() {
  router.push('/b-data/cohort-list')
}
</script>

<template>
  <div class="page tag-mgmt">
    <header class="head">
      <div>
        <h1>{{ t('标签管理') }}</h1>
      </div>
      <div class="head-actions">
        <button type="button" class="btn" @click="goCohort">
          <span class="material-symbols-outlined">arrow_back</span>
          {{ t('客群运营') }}
        </button>
        <button type="button" class="btn primary" @click="libRef?.openNewDialog()">
          <span class="material-symbols-outlined">add</span>
          {{ t('新建标签') }}
        </button>
      </div>
    </header>

    <MasterTagLibrary ref="libRef" embedded />
  </div>
</template>

<style scoped>
.tag-mgmt {
  width: 100%;
  max-width: none;
}
.head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 20px;
}
.head h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 750;
}
.head-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 9px 14px;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  font-size: 13px;
  font-weight: 650;
  color: var(--on-surface);
}
.btn.primary {
  background: var(--primary);
  color: var(--on-primary);
  border-color: transparent;
}
.btn .material-symbols-outlined {
  font-size: 18px;
}
</style>

<style>
.stage > .page.tag-mgmt {
  max-width: none;
  width: 100%;
  padding-left: 20px;
  padding-right: 24px;
}
</style>
