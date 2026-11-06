<script setup>
import Chart from "chart.js/auto";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { get } from "../api";
import { money } from "../format";

const days = ref(30);
const funnel = ref(null);
const topProducts = ref([]);
const error = ref("");
const canvas = ref(null);
let chart;

async function load() {
  error.value = "";
  try {
    const [daily, funnelData, top] = await Promise.all([
      get(`/analytics/daily?days=${days.value}`),
      get(`/analytics/funnel?days=${days.value}`),
      get(`/analytics/top-products?days=${days.value}&limit=10`),
    ]);
    drawChart(daily);
    funnel.value = funnelData;
    topProducts.value = top;
  } catch (e) {
    error.value = e.message;
  }
}

onMounted(load);
watch(days, load);
onBeforeUnmount(() => chart?.destroy());

function drawChart(daily) {
  const style = getComputedStyle(document.documentElement);
  const color = (name) => style.getPropertyValue(name).trim();
  Chart.defaults.color = color("--muted");
  Chart.defaults.borderColor = color("--border");

  chart?.destroy();
  chart = new Chart(canvas.value, {
    type: "line",
    data: {
      labels: daily.map((d) =>
        new Date(d.date).toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" }),
      ),
      datasets: [
        {
          label: "Events",
          data: daily.map((d) => d.events),
          borderColor: color("--accent"),
          backgroundColor: color("--accent"),
          yAxisID: "events",
        },
        {
          label: "Revenue",
          data: daily.map((d) => d.revenue_cents / 100),
          borderColor: color("--revenue"),
          backgroundColor: color("--revenue"),
          yAxisID: "revenue",
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        events: { position: "left", beginAtZero: true, title: { display: true, text: "Events" } },
        revenue: {
          position: "right",
          beginAtZero: true,
          title: { display: true, text: "Revenue" },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

const steps = computed(() => [
  { label: "Viewed", users: funnel.value.viewed },
  { label: "Added to cart", users: funnel.value.added_to_cart, rate: funnel.value.view_to_cart_rate },
  { label: "Purchased", users: funnel.value.purchased, rate: funnel.value.cart_to_purchase_rate },
]);

function barWidth(users) {
  const widest = Math.max(...steps.value.map((step) => step.users));
  return widest ? `${(users / widest) * 100}%` : "0";
}

function percent(rate) {
  return rate === null ? "—" : `${(rate * 100).toFixed(1)}%`;
}
</script>

<template>
  <div class="title-row">
    <h1>Overview</h1>
    <select v-model="days">
      <option :value="7">Last 7 days</option>
      <option :value="30">Last 30 days</option>
      <option :value="90">Last 90 days</option>
    </select>
  </div>
  <p v-if="error" class="error">{{ error }}</p>

  <h2>Daily activity</h2>
  <div class="chart"><canvas ref="canvas"></canvas></div>

  <template v-if="funnel">
    <h2>Funnel</h2>
    <p class="muted">Users who did a step and every step before it.</p>
    <div class="funnel">
      <template v-for="(step, index) in steps" :key="step.label">
        <div v-if="index > 0" class="conversion">↓ {{ percent(step.rate) }} of the step above</div>
        <div class="funnel-row">
          <span>{{ step.label }}</span>
          <div class="funnel-track"><div class="funnel-bar" :style="{ width: barWidth(step.users) }"></div></div>
          <span class="number">{{ step.users }}</span>
        </div>
      </template>
    </div>
  </template>

  <h2>Top products</h2>
  <p v-if="!topProducts.length" class="muted">No purchases in this period.</p>
  <table v-else>
    <thead>
      <tr><th class="number">#</th><th>Product</th><th>Category</th><th class="number">Purchases</th><th class="number">Revenue</th></tr>
    </thead>
    <tbody>
      <tr v-for="(row, index) in topProducts" :key="row.product.id">
        <td class="number">{{ index + 1 }}</td>
        <td>{{ row.product.name }}</td>
        <td>{{ row.product.category }}</td>
        <td class="number">{{ row.purchases }}</td>
        <td class="number">{{ money(row.revenue_cents) }}</td>
      </tr>
    </tbody>
  </table>
</template>
