<script setup>
import UserSearch from "./components/UserSearch.vue";
</script>

<template>
  <header>
    <strong>Mini CDP</strong>
    <nav>
      <RouterLink to="/">Overview</RouterLink>
      <RouterLink to="/segments">Segments</RouterLink>
      <RouterLink to="/segments/new">New segment</RouterLink>
    </nav>
    <UserSearch />
  </header>
  <main>
    <RouterView />
  </main>
</template>
