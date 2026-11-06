<script setup>
import { useRouter } from "vue-router";
import { auth, logOut } from "./auth";
import UserSearch from "./components/UserSearch.vue";

const router = useRouter();

function leave() {
  logOut();
  router.push("/login");
}
</script>

<template>
  <header v-if="auth.token">
    <strong>Mini CDP</strong>
    <nav>
      <RouterLink to="/">Overview</RouterLink>
      <RouterLink to="/segments">Segments</RouterLink>
      <RouterLink v-if="auth.role === 'admin'" to="/segments/new">New segment</RouterLink>
    </nav>
    <UserSearch />
    <div class="account">
      <span class="muted">{{ auth.email }} · {{ auth.role }}</span>
      <button @click="leave">Log out</button>
    </div>
  </header>
  <main>
    <RouterView />
  </main>
</template>
