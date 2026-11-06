<script setup>
import { onBeforeUnmount, ref, watch } from "vue";
import { get } from "../api";
import { debounce } from "../debounce";

const query = ref("");
const results = ref([]);
const open = ref(false);
const loading = ref(false);
const error = ref("");

// Responses can arrive out of order, so only the newest request may update the list.
let latestRequest = 0;

async function search() {
  const request = ++latestRequest;
  const q = query.value.trim();
  if (!q) {
    results.value = [];
    loading.value = false;
    return;
  }
  try {
    const users = await get(`/users/search?q=${encodeURIComponent(q)}&limit=8`);
    if (request === latestRequest) {
      results.value = users;
      error.value = "";
    }
  } catch (e) {
    if (request === latestRequest) {
      error.value = e.message;
    }
  }
  if (request === latestRequest) {
    loading.value = false;
  }
}

const scheduleSearch = debounce(search);
watch(query, () => {
  loading.value = true;
  open.value = true;
  scheduleSearch();
});
onBeforeUnmount(scheduleSearch.cancel);

function close() {
  query.value = "";
  open.value = false;
}

// Close the list when focus moves somewhere outside the search box and its results.
function onFocusOut(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) {
    open.value = false;
  }
}
</script>

<template>
  <div class="search" @focusout="onFocusOut" @keydown.esc="open = false">
    <input v-model="query" type="search" placeholder="Search users by email or ID" @focus="open = true" />
    <ul v-if="open && query.trim()" class="search-results">
      <li v-for="user in results" :key="user.id">
        <!-- mousedown.prevent keeps focus in the input, so focusout doesn't close the list before the click -->
        <RouterLink :to="`/users/${user.id}`" @mousedown.prevent @click="close">
          <strong>{{ user.external_id }}</strong>
          <span class="muted">{{ user.email }}</span>
        </RouterLink>
      </li>
      <li v-if="error" class="error">{{ error }}</li>
      <li v-else-if="!results.length" class="muted">{{ loading ? "Searching…" : "No users found" }}</li>
    </ul>
  </div>
</template>
