<script setup>
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { post } from "../api";
import { logIn } from "../auth";

// Public on purpose: the demo account can only view, so anyone can look around.
const DEMO = { email: "demo@mini-cdp.dev", password: "demo1234" };

const route = useRoute();
const router = useRouter();
const email = ref("");
const password = ref("");
const error = ref("");

async function submit(credentials) {
  error.value = "";
  try {
    logIn(await post("/auth/login", credentials));
    router.push(route.query.next || "/");
  } catch (e) {
    error.value = e.message;
  }
}
</script>

<template>
  <div class="login">
    <h1>Log in to Mini CDP</h1>
    <form @submit.prevent="submit({ email, password })">
      <label>
        Email
        <input v-model="email" type="email" autocomplete="username" required />
      </label>
      <label>
        Password
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="primary">Log in</button>
    </form>

    <div class="demo">
      <h2>Just looking around?</h2>
      <p>The demo viewer account can see everything but can't change anything.</p>
      <p><code>{{ DEMO.email }}</code> / <code>{{ DEMO.password }}</code></p>
      <button type="button" @click="submit(DEMO)">Log in as demo viewer</button>
    </div>
  </div>
</template>
