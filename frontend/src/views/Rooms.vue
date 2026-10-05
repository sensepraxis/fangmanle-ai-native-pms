<!-- SPDX-License-Identifier: Apache-2.0 -->
<script setup lang="ts">
import { t } from '../lib/i18n'

import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'
import { hotelStore } from '../store/hotel'
import { STATUS_CN } from '../lib/ui'

const router = useRouter()
const rooms = ref<any[]>([])

async function load() {
  rooms.value = await api.listRooms(hotelStore.hotelId)
}
onMounted(load)
watch(() => hotelStore.hotelId, load)

function openRoom(r: any) {
  router.push(`/rooms/${r.id}`)
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>{{ t('客房管理') }}</h1>
      <p>{{ t('客房库存台账。点击任意客房进入详情（状态变更记录与关联房务任务）。') }}</p>
    </div>

    <div class="card-clean" style="overflow: hidden">
      <table class="data">
        <thead>
          <tr>
            <th style="width: 120px">{{ t('房号') }}</th>
            <th style="width: 160px">{{ t('房型') }}</th>
            <th style="width: 100px">{{ t('楼层') }}</th>
            <th style="width: 120px">{{ t('楼栋') }}</th>
            <th style="width: 140px">{{ t('状态') }}</th>
            <th class="center" style="width: 100px">{{ t('操作') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rooms" :key="r.id" class="clickable" @click="openRoom(r)">
            <td style="font-weight: 600">{{ r.room_no }}</td>
            <td>{{ r.room_type_name }}</td>
            <td>{{ r.floor }}F</td>
            <td>{{ r.building || '—' }}</td>
            <td>
              <span
                class="pill"
                :class="{
                  'pill-green': r.status === 'vacant',
                  'pill-blue': r.status === 'occupied',
                  'pill-amber': r.status === 'dirty' || r.status === 'cleaning',
                  'pill-slate': r.status === 'maintenance' || r.status === 'ooo',
                }"
                >{{ STATUS_CN[r.status] || r.status }}</span
              >
            </td>
            <td class="center">
              <span class="btn-link" @click.stop="openRoom(r)">{{ t('查看') }}</span>
            </td>
          </tr>
          <tr v-if="!rooms.length">
            <td colspan="6" style="text-align: center; color: #9aa1ad; padding: 30px">
              {{ t('暂无客房') }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
