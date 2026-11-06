<script setup>
import { ref, watch } from "vue";
import { get } from "../api";
import { money } from "../format";

const props = defineProps({ id: String });

const user = ref(null);
const profile = ref(null);
const events = ref([]);
const recommendations = ref([]);
const productNames = ref({});
const error = ref("");

async function load() {
  error.value = "";
  user.value = null;
  try {
    const id = props.id;
    const [u, p, e, r, products] = await Promise.all([
      get(`/users/${id}`),
      get(`/users/${id}/profile`),
      get(`/users/${id}/events?limit=20`),
      get(`/users/${id}/recommendations`),
      get("/products"),
    ]);
    user.value = u;
    profile.value = p;
    events.value = e;
    recommendations.value = r;
    productNames.value = Object.fromEntries(products.map((product) => [product.id, product.name]));
  } catch (e) {
    error.value = e.message;
  }
}

watch(() => props.id, load, { immediate: true });

function time(value) {
  return value ? new Date(value).toLocaleString() : "never";
}
</script>

<template>
  <p v-if="error" class="error">{{ error }}</p>
  <template v-else-if="user">
    <h1>{{ user.external_id }}</h1>
    <p class="muted">User {{ user.id }} · {{ user.email || "no email" }} · {{ user.country || "no country" }}</p>

    <h2>Profile</h2>
    <dl>
      <dt>Views</dt><dd>{{ profile.view_count }}</dd>
      <dt>Added to cart</dt><dd>{{ profile.add_to_cart_count }}</dd>
      <dt>Purchases</dt><dd>{{ profile.purchase_count }}</dd>
      <dt>Total spent</dt><dd>{{ money(profile.total_spent_cents) }}</dd>
      <dt>Last activity</dt><dd>{{ time(profile.last_event_at) }}</dd>
      <dt>Favorite category</dt><dd>{{ profile.favorite_category || "none" }}</dd>
    </dl>

    <h2>Recommendations</h2>
    <p v-if="!recommendations.length" class="muted">No recommendations yet.</p>
    <table v-else>
      <thead>
        <tr><th>Product</th><th>Category</th><th>Reason</th><th class="number">Score</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in recommendations" :key="r.product.id">
          <td>{{ r.product.name }}</td>
          <td>{{ r.product.category }}</td>
          <td>{{ r.reason === "bought_together" ? "Bought together" : "Popular" }}</td>
          <td class="number">{{ r.score }}</td>
        </tr>
      </tbody>
    </table>

    <h2>Recent events</h2>
    <p v-if="!events.length" class="muted">No events yet.</p>
    <table v-else>
      <thead>
        <tr><th>Time</th><th>Type</th><th>Product</th><th class="number">Value</th></tr>
      </thead>
      <tbody>
        <tr v-for="event in events" :key="event.id">
          <td>{{ time(event.created_at) }}</td>
          <td>{{ event.type.replaceAll("_", " ") }}</td>
          <td>{{ productNames[event.product_id] }}</td>
          <td class="number">{{ event.value_cents ? money(event.value_cents) : "" }}</td>
        </tr>
      </tbody>
    </table>
  </template>
</template>
