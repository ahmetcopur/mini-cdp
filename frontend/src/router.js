import { createRouter, createWebHistory } from "vue-router";
import NewSegmentPage from "./pages/NewSegmentPage.vue";
import OverviewPage from "./pages/OverviewPage.vue";
import SegmentsPage from "./pages/SegmentsPage.vue";
import SegmentUsersPage from "./pages/SegmentUsersPage.vue";
import UserPage from "./pages/UserPage.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: OverviewPage },
    { path: "/segments", component: SegmentsPage },
    { path: "/segments/new", component: NewSegmentPage },
    { path: "/segments/:id", component: SegmentUsersPage, props: true },
    { path: "/users/:id", component: UserPage, props: true },
  ],
});
