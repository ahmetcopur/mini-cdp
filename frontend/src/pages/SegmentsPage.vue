<script setup>
import { onMounted, ref } from "vue";
import { get } from "../api";

const OPS = { eq: "=", gt: ">", gte: "≥", lt: "<", lte: "≤" };

const segments = ref([]);
const error = ref("");

onMounted(async () => {
  try {
    const list = await get("/segments");
    const pages = await Promise.all(list.map((s) => get(`/segments/${s.id}/users?limit=1`)));
    segments.value = list.map((s, i) => ({ ...s, count: pages[i].count }));
  } catch (e) {
    error.value = e.message;
  }
});
</script>

<template>
  <h1>Segments</h1>
  <p v-if="error" class="error">{{ error }}</p>
  <table v-else>
    <thead>
      <tr><th>Name</th><th>Rules</th><th class="number">Users</th></tr>
    </thead>
    <tbody>
      <tr v-for="segment in segments" :key="segment.id">
        <td><RouterLink :to="`/segments/${segment.id}`">{{ segment.name }}</RouterLink></td>
        <td>
          <div v-for="rule in segment.rules" :key="rule.field + rule.op">
            <code>{{ rule.field }} {{ OPS[rule.op] }} {{ rule.value }}</code>
          </div>
        </td>
        <td class="number">{{ segment.count }}</td>
      </tr>
    </tbody>
  </table>
</template>
