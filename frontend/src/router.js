import { createRouter, createWebHistory } from "vue-router";
import OverviewPage from "./pages/OverviewPage.vue";
import SegmentFormPage from "./pages/SegmentFormPage.vue";
import SegmentsPage from "./pages/SegmentsPage.vue";
import SegmentUsersPage from "./pages/SegmentUsersPage.vue";
import UserPage from "./pages/UserPage.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: OverviewPage },
    { path: "/segments", component: SegmentsPage },
    { path: "/segments/new", component: SegmentFormPage },
    { path: "/segments/:id/edit", component: SegmentFormPage, props: true },
    { path: "/segments/:id", component: SegmentUsersPage, props: true },
    { path: "/users/:id", component: UserPage, props: true },
  ],
});
