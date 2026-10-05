<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../../lib/i18n'
defineProps<{ title: string; phase: string; desc: string }>()
</script>

<template>
  <div class="ph card-clean">
    <span class="badge">{{ phase }}</span>
    <h1>{{ title }}</h1>
    <p>{{ desc }}</p>
  </div>
</template>

<style scoped>
.ph {
  padding: 28px 24px;
}
.badge {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 8px;
  background: #fef3c7;
  color: #b45309;
  font-weight: 600;
}
h1 {
  margin: 10px 0 8px;
  font-size: 22px;
}
p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
  max-width: 560px;
  line-height: 1.6;
}
</style>
