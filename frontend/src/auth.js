import { reactive } from "vue";

// The login is kept in memory, and copied to sessionStorage so reloading the page keeps
// you logged in. sessionStorage is cleared when the tab is closed.
const saved = JSON.parse(sessionStorage.getItem("auth") || "{}");

export const auth = reactive({ token: saved.token, email: saved.email, role: saved.role });

export function logIn({ access_token, email, role }) {
  Object.assign(auth, { token: access_token, email, role });
  sessionStorage.setItem("auth", JSON.stringify(auth));
}

export function logOut() {
  Object.assign(auth, { token: null, email: null, role: null });
  sessionStorage.removeItem("auth");
}
