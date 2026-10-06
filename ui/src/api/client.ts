import { getBootstrap, httpBase } from '../lib/bootstrap'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const { token } = getBootstrap()
  const response = await fetch(`${httpBase()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  })
  if (!response.ok) {
    let detail = `${response.status}`
    try {
      detail = ((await response.json()) as { detail?: string }).detail ?? detail
    } catch {
      /* keep status */
    }
    throw new Error(detail)
  }
  return (await response.json()) as T
}

export const api = {
  health: () => request<{ status: string; app: string; version: string }>('/health'),
  getSettings: () => request<Record<string, string>>('/api/settings'),
  putSettings: (patch: Record<string, string>) =>
    request<Record<string, string>>('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(patch),
    }),
  listProjects: () => request<import('./types').ProjectSummary[]>('/api/projects'),
  createProject: (body: { title?: string; source_path: string; outputs: Record<string, boolean> }) =>
    request<Record<string, unknown>>('/api/projects', { method: 'POST', body: JSON.stringify(body) }),
  submitJob: (projectId: string, type: string, params: Record<string, unknown> = {}) =>
    request<{ job_id: string }>(`/api/projects/${projectId}/jobs`, {
      method: 'POST',
      body: JSON.stringify({ type, params }),
    }),
  getJob: (jobId: string) => request<import('./types').Job>(`/api/jobs/${jobId}`),
  cancelJob: (jobId: string) =>
    request<{ cancelling: boolean }>(`/api/jobs/${jobId}/cancel`, { method: 'POST' }),
}
