const BASE_URL = ''

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
}

async function request<T = unknown>(url: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = options

  const token = localStorage.getItem('accessToken')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  if (body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(`${BASE_URL}${url}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    const detailBody = (errorBody as { detail?: unknown; message?: string }).detail
    const detail =
      typeof detailBody === 'string'
        ? detailBody
        : (errorBody as { message?: string }).message || response.statusText
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

export const http = {
  get<T = unknown>(url: string) {
    return request<T>(url)
  },
  post<T = unknown>(url: string, body?: unknown) {
    return request<T>(url, { method: 'POST', body })
  },
  put<T = unknown>(url: string, body?: unknown) {
    return request<T>(url, { method: 'PUT', body })
  },
  patch<T = unknown>(url: string, body?: unknown) {
    return request<T>(url, { method: 'PATCH', body })
  },
  delete<T = unknown>(url: string) {
    return request<T>(url, { method: 'DELETE' })
  },
}
