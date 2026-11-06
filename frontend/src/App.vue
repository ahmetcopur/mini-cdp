<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const userId = ref("");

function openUser() {
  router.push(`/users/${userId.value}`);
  userId.value = "";
}
</script>

<template>
  <header>
    <strong>Mini CDP</strong>
    <nav>
      <RouterLink to="/">Overview</RouterLink>
      <RouterLink to="/segments">Segments</RouterLink>
      <RouterLink to="/segments/new">New segment</RouterLink>
    </nav>
    <form @submit.prevent="openUser">
      <input v-model="userId" type="number" min="1" placeholder="User ID" required />
      <button>Open user</button>
    </form>
  </header>
  <main>
    <RouterView />
  </main>
</template>
