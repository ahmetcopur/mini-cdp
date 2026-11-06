<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { del, get, post, put } from "../api";
import { debounce } from "../debounce";

const FIELDS = ["country", "view_count", "purchase_count", "total_spent_cents", "days_since_last_event"];
const OPS = { eq: "=", gt: ">", gte: "≥", lt: "<", lte: "≤" };

// Without an id this is the form for a new segment, with one it edits that segment.
const props = defineProps({ id: String });

const router = useRouter();
const name = ref("");
const rules = ref([newRule()]);
const error = ref("");
const matchCount = ref(null);
const previewError = ref("");
const confirmingDelete = ref(false);

function newRule() {
  return { field: "purchase_count", op: "gte", value: "" };
}

onMounted(async () => {
  if (!props.id) {
    return;
  }
  try {
    const segment = (await get("/segments")).find((s) => s.id === Number(props.id));
    if (!segment) {
      throw new Error("Segment not found");
    }
    name.value = segment.name;
    rules.value = segment.rules;
  } catch (e) {
    error.value = e.message;
  }
});

function payloadRules() {
  return rules.value.map((r) => ({ ...r, value: r.field === "country" ? r.value : Number(r.value) }));
}

// Ask for a new count once the rules have not changed for 300 ms.
const schedulePreview = debounce(preview);
watch(rules, schedulePreview, { deep: true, immediate: true });
onBeforeUnmount(schedulePreview.cancel);

// Responses can arrive out of order, so only the newest request may update the count.
let latestRequest = 0;

async function preview() {
  const request = ++latestRequest;
  if (rules.value.some((r) => r.value === "")) {
    matchCount.value = null;
    previewError.value = "";
    return;
  }
  try {
    const { count } = await post("/segments/preview", { rules: payloadRules() });
    if (request === latestRequest) {
      matchCount.value = count;
      previewError.value = "";
    }
  } catch (e) {
    if (request === latestRequest) {
      matchCount.value = null;
      previewError.value = e.message;
    }
  }
}

async function save() {
  error.value = "";
  const body = { name: name.value, rules: payloadRules() };
  try {
    const segment = props.id ? await put(`/segments/${props.id}`, body) : await post("/segments", body);
    router.push(`/segments/${segment.id}`);
  } catch (e) {
    error.value = e.message;
  }
}

async function remove() {
  try {
    await del(`/segments/${props.id}`);
    router.push("/segments");
  } catch (e) {
    error.value = e.message;
  }
}
</script>

<template>
  <h1>{{ id ? "Edit segment" : "New segment" }}</h1>
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
        <button type="button" :disabled="rules.length === 1" @click="rules.splice(index, 1)">Remove</button>
      </div>
      <button type="button" @click="rules.push(newRule())">Add rule</button>
    </fieldset>

    <p class="preview">
      <strong v-if="matchCount !== null">{{ matchCount }} {{ matchCount === 1 ? "user matches" : "users match" }}</strong>
      <span v-else-if="previewError" class="error">{{ previewError }}</span>
      <span v-else class="muted">Fill in every rule to see how many users match.</span>
    </p>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="actions">
      <button class="primary">{{ id ? "Save changes" : "Create segment" }}</button>
      <template v-if="id">
        <button v-if="!confirmingDelete" type="button" class="danger" @click="confirmingDelete = true">
          Delete segment
        </button>
        <template v-else>
          <span>Delete this segment for good?</span>
          <button type="button" class="danger" @click="remove">Yes, delete</button>
          <button type="button" @click="confirmingDelete = false">Cancel</button>
        </template>
      </template>
    </div>
  </form>
</template>
