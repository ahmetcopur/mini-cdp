<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { post } from "../api";

const FIELDS = ["country", "view_count", "purchase_count", "total_spent_cents", "days_since_last_event"];
const OPS = { eq: "=", gt: ">", gte: "≥", lt: "<", lte: "≤" };

const router = useRouter();
const name = ref("");
const rules = ref([{ field: "purchase_count", op: "gte", value: "" }]);
const error = ref("");

function addRule() {
  rules.value.push({ field: "purchase_count", op: "gte", value: "" });
}

function removeRule(index) {
  rules.value.splice(index, 1);
}

async function save() {
  error.value = "";
  try {
    await post("/segments", {
      name: name.value,
      rules: rules.value.map((r) => ({ ...r, value: r.field === "country" ? r.value : Number(r.value) })),
    });
    router.push("/segments");
  } catch (e) {
    error.value = e.message;
  }
}
</script>

<template>
  <h1>New segment</h1>
  <form class="segment-form" @submit.prevent="save">
    <label>
      Name
      <input v-model="name" required />
    </label>

    <fieldset>
      <legend>Users must match all rules</legend>
      <div v-for="(rule, index) in rules" :key="index" class="rule">
        <select v-model="rule.field">
          <option v-for="field in FIELDS" :key="field">{{ field }}</option>
        </select>
        <select v-model="rule.op">
          <option v-for="(symbol, op) in OPS" :key="op" :value="op">{{ symbol }}</option>
        </select>
        <input v-model="rule.value" :placeholder="rule.field === 'country' ? 'TR' : '0'" required />
        <button type="button" :disabled="rules.length === 1" @click="removeRule(index)">Remove</button>
      </div>
      <button type="button" @click="addRule">Add rule</button>
    </fieldset>

    <p v-if="error" class="error">{{ error }}</p>
    <button class="primary">Create segment</button>
  </form>
</template>
