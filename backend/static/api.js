// All fetch calls live here. The API key is attached from localStorage;
// on 401 the user is prompted once, the key is stored, and the call retries.

let apiKey = localStorage.getItem("rozvrh_api_key") ?? "";

async function request(path, options = {}) {
  if (apiKey === "") {
    apiKey = prompt("Enter the API key") ?? "";
    localStorage.setItem("rozvrh_api_key", apiKey);
  }
  const headers = { "X-API-Key": apiKey, ...(options.headers ?? {}) };
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    apiKey = prompt("Invalid API key, enter it again") ?? "";
    localStorage.setItem("rozvrh_api_key", apiKey);
    const retry = await fetch(path, { ...options, headers: { ...options.headers, "X-API-Key": apiKey } });
    if (!retry.ok) {
      throw new Error(`${retry.status} ${retry.statusText}`);
    }
    return retry;
  }
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response;
}

async function json(response) {
  return response.json();
}

export async function fetchWeek(isoYear, isoWeek) {
  const response = await request(`/api/weeks/${isoYear}/${isoWeek}`);
  return response.json();
}

export async function fetchTodo() {
  const response = await request("/api/blocks/todo");
  return response.json();
}

// Mutations funnel through app.js's onMutate; a failed one must not leave the
// user staring at a silent snap-back, so surface it in the toolbar.
function showError(message) {
  const el = document.getElementById("error-banner");
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
  clearTimeout(showError.timer);
  showError.timer = setTimeout(() => {
    el.hidden = true;
  }, 4000);
}

export async function mutate({ method, path, body }) {
  try {
    // GET/HEAD cannot carry a body; only non-GET calls send JSON.
    const response = await request(path, {
      method,
      headers: { "Content-Type": "application/json" },
      ...(method === "GET" ? {} : { body: JSON.stringify(body ?? {}) }),
    });
    if (response.status !== 204) {
      return json(response);
    }
    return null;
  } catch (error) {
    showError(`Save failed: ${error.message}`);
    return null;
  }
}
