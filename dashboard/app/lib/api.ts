const API_URL = "http://72.61.225.168:8100";

export class AuthError extends Error {
  constructor() {
    super("Unauthorized");
    this.name = "AuthError";
  }
}

export async function authFetch(path: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("jwt") : null;
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("jwt");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    throw new AuthError();
  }
  return res;
}

// Auth
export async function login(email: string, password: string) {
  const res = await fetch(`${API_URL}/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Login failed");
  return res.json();
}

export async function register(email: string, password: string, display_name: string) {
  const res = await fetch(`${API_URL}/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Registration failed");
  return res.json();
}

// Agents
export async function getMyAgents() {
  const res = await authFetch("/v1/agents/me");
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

export async function getAgent(slug: string) {
  const res = await authFetch(`/v1/agents/${slug}`);
  if (!res.ok) throw new Error("Failed to fetch agent");
  return res.json();
}

export async function createAgent(data: Record<string, unknown>) {
  const res = await authFetch("/v1/agents", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Failed to create agent");
  return res.json();
}

export async function searchAgents(skill?: string) {
  const params = new URLSearchParams();
  if (skill) params.set("skill", skill);
  const res = await authFetch(`/v1/agents?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to search agents");
  return res.json();
}

// Tasks
export async function getTasks(params?: string) {
  const res = await authFetch(`/v1/tasks${params ? `?${params}` : ""}`);
  if (!res.ok) throw new Error("Failed to fetch tasks");
  return res.json();
}

export async function getTask(id: string) {
  const res = await authFetch(`/v1/tasks/${id}`);
  if (!res.ok) throw new Error("Failed to fetch task");
  return res.json();
}

export async function createTask(data: {
  provider_agent_id: string;
  skill_requested: string;
  description?: string;
  payload?: Record<string, unknown>;
  max_wait_seconds?: number;
}) {
  const res = await authFetch("/v1/tasks", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Failed to create task");
  return res.json();
}

export async function rateTask(taskId: string, overall_score: number, feedback?: string) {
  const res = await authFetch("/v1/ratings", {
    method: "POST",
    body: JSON.stringify({ task_id: taskId, overall_score, feedback }),
  });
  if (!res.ok) throw new Error("Failed to rate task");
  return res.json();
}

// Credits
export async function getBalance() {
  const res = await authFetch("/v1/credits/balance");
  if (!res.ok) throw new Error("Failed to fetch balance");
  return res.json();
}

export async function getTransactions() {
  const res = await authFetch("/v1/credits/transactions");
  if (!res.ok) throw new Error("Failed to fetch transactions");
  return res.json();
}

export async function topUp(amount: number) {
  const res = await authFetch("/v1/credits/topup", {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
  if (!res.ok) throw new Error("Failed to top up");
  return res.json();
}

// Agent ratings
export async function getAgentRatings(slug: string) {
  const res = await authFetch(`/v1/agents/${slug}/ratings`);
  if (!res.ok) throw new Error("Failed to fetch ratings");
  return res.json();
}
