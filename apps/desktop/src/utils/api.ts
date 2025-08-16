const BASE_URL = "http://localhost:8001";

// Helper for fetch with error handling
async function fetchJson(url: string, options: RequestInit = {}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Submit user prompt
export async function submitPrompt(data: any, baseUrl = BASE_URL) {
  return fetchJson(`${baseUrl}/api/prompt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// Approve a step
export async function approveStep(sessionId: string, approval: any, baseUrl = BASE_URL) {
  return fetchJson(`${baseUrl}/api/approve/${sessionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(approval),
  });
}

// List sessions
export async function listSessions(baseUrl = BASE_URL) {
  return fetchJson(`${baseUrl}/api/sessions`);
}

// List files for a session
export async function listSessionFiles(sessionId: string, baseUrl = BASE_URL) {
  return fetchJson(`${baseUrl}/api/files/list/${sessionId}`);
}

// Add more API functions as needed (file upload, download, etc.) 