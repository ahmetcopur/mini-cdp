const API_URL = "http://localhost:8000";

async function request(path, options) {
  const response = await fetch(API_URL + path, options);
  const body = await response.json();
  if (!response.ok) {
    // Validation errors come as a list, other errors as a single message.
    const detail = body.detail;
    throw new Error(Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : detail);
  }
  return body;
}

export function get(path) {
  return request(path);
}

export function post(path, data) {
  return request(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(data),
  });
}
