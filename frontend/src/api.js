import { auth, logOut } from "./auth";
import router from "./router";

// Set at build time for a deployed dashboard. Docker Compose and `npm run dev` use the default.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const headers = { ...options.headers };
  if (auth.token) {
    headers.Authorization = `Bearer ${auth.token}`;
  }
  const response = await fetch(API_URL + path, { ...options, headers });
  if (response.status === 401 && auth.token) {
    // The token has expired or is no longer valid, so log in again.
    logOut();
    router.push({ path: "/login", query: { next: router.currentRoute.value.fullPath } });
  }
  if (response.status === 204) {
    return null;
  }
  const body = await response.json();
  if (!response.ok) {
    // Validation errors come as a list, other errors as a single message.
    const detail = body.detail;
    throw new Error(Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : detail);
  }
  return body;
}

function send(method, path, data) {
  return request(path, {
    method,
    headers: { "content-type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function get(path) {
  return request(path);
}

export function post(path, data) {
  return send("POST", path, data);
}

export function put(path, data) {
  return send("PUT", path, data);
}

export function del(path) {
  return request(path, { method: "DELETE" });
}
