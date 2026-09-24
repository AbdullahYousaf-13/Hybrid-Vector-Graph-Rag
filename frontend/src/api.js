const API_URL = import.meta.env.VITE_API_URL ?? "/api/query";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function askQuestion({ question, mode, signal }) {
  let res;
  try {
    res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, mode }),
      signal,
    });
  } catch (cause) {
    if (cause?.name === "AbortError") throw cause;
    throw new ApiError(
      "Could not reach the backend. If you are running locally, start it with: uvicorn backend.app:app --reload --port 8001",
      0
    );
  }

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    throw new ApiError(data?.detail ?? `Request failed with status ${res.status}.`, res.status);
  }

  return data;
}
