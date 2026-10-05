// Centralized HTTP client for the FastAPI backend (app/main.py mounts the
// API routers at /api). Configure the base URL via VITE_API_BASE_URL
// (see .env.example); defaults to the local dev server.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

export class ApiError extends Error {
  status?: number
  constructor(message: string, status?: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let res: Response
  try {
    // FormData (file uploads) must not get a Content-Type header: the browser
    // sets multipart/form-data with the boundary itself.
    const isForm = options.body instanceof FormData
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: { ...(isForm ? {} : { "Content-Type": "application/json" }), ...options.headers },
    })
  } catch {
    throw new ApiError("Could not reach the server. Is the backend running?")
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      /* no JSON body */
    }
    throw new ApiError(detail, res.status)
  }

  return res.json() as Promise<T>
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  postForm: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
}
