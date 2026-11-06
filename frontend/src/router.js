import { createRouter, createWebHistory } from "vue-router";
import { auth } from "./auth";
import LoginPage from "./pages/LoginPage.vue";
import OverviewPage from "./pages/OverviewPage.vue";
import SegmentFormPage from "./pages/SegmentFormPage.vue";
import SegmentsPage from "./pages/SegmentsPage.vue";
import SegmentUsersPage from "./pages/SegmentUsersPage.vue";
import UserPage from "./pages/UserPage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginPage },
    { path: "/", component: OverviewPage },
    { path: "/segments", component: SegmentsPage },
    { path: "/segments/new", component: SegmentFormPage, meta: { admin: true } },
    { path: "/segments/:id/edit", component: SegmentFormPage, props: true, meta: { admin: true } },
    { path: "/segments/:id", component: SegmentUsersPage, props: true },
    { path: "/users/:id", component: UserPage, props: true },
  ],
});

// These checks only decide which pages to show. The API checks the token and the role
// on every request by itself, so skipping them in the browser gets nothing.
router.beforeEach((to) => {
  if (to.path === "/login") {
    return auth.token ? "/" : true;
  }
  if (!auth.token) {
    return { path: "/login", query: { next: to.fullPath } };
  }
  if (to.meta.admin && auth.role !== "admin") {
    return "/";
  }
});

export default router;
