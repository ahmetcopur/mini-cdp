<script setup>
import { onMounted, ref, watch } from "vue";
import { get } from "../api";
import { auth } from "../auth";

const PAGE_SIZE = 20;

const props = defineProps({ id: String });

const name = ref("");
const count = ref(0);
const users = ref([]);
const offset = ref(0);
const error = ref("");

onMounted(async () => {
  try {
    const segments = await get("/segments");
    name.value = segments.find((s) => s.id === Number(props.id))?.name;
  } catch (e) {
    error.value = e.message;
  }
});

async function loadUsers() {
  try {
    const page = await get(`/segments/${props.id}/users?limit=${PAGE_SIZE}&offset=${offset.value}`);
    count.value = page.count;
    users.value = page.users;
  } catch (e) {
    error.value = e.message;
  }
}

watch(offset, loadUsers, { immediate: true });
</script>

<template>
  <p v-if="error" class="error">{{ error }}</p>
  <template v-else>
    <div class="title-row">
      <h1>{{ name }}</h1>
      <RouterLink v-if="auth.role === 'admin'" :to="`/segments/${id}/edit`">Edit segment</RouterLink>
    </div>
    <p class="muted">{{ count }} users</p>

    <table v-if="users.length">
      <thead>
        <tr><th>User</th><th>Email</th><th>Country</th></tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td><RouterLink :to="`/users/${user.id}`">{{ user.external_id }}</RouterLink></td>
          <td>{{ user.email }}</td>
          <td>{{ user.country }}</td>
        </tr>
      </tbody>
    </table>

    <div v-if="count > PAGE_SIZE" class="pager">
      <button :disabled="offset === 0" @click="offset -= PAGE_SIZE">Previous</button>
      <span>{{ offset + 1 }}–{{ Math.min(offset + PAGE_SIZE, count) }} of {{ count }}</span>
      <button :disabled="offset + PAGE_SIZE >= count" @click="offset += PAGE_SIZE">Next</button>
    </div>
  </template>
</template>
