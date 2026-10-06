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

export async function uploadProject(
  file: File,
  title: string,
  outputs: Record<string, boolean>,
): Promise<Record<string, unknown>> {
  const { token } = getBootstrap()
  const form = new FormData()
  form.append('file', file)
  form.append('title', title)
  form.append('outputs', JSON.stringify(outputs))
  const response = await fetch(`${httpBase()}/api/projects/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  })
  if (!response.ok) throw new Error(`Upload failed (${response.status})`)
  return (await response.json()) as Record<string, unknown>
}

export function mediaUrl(projectId: string): string {
  const { token } = getBootstrap()
  return `${httpBase()}/media/${projectId}?token=${encodeURIComponent(token)}`
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
  getCaptions: (projectId: string) =>
    request<{ cues: CaptionCue[]; provenance: Record<string, unknown>; source: Record<string, unknown>; status: string }>(
      `/api/projects/${projectId}/captions`,
    ),
  patchCue: (projectId: string, cueId: string, body: { text?: string; approve?: boolean; reviewer?: string }) =>
    request<CaptionCue>(`/api/projects/${projectId}/captions/${cueId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  exportCaptions: (projectId: string, formats: string[]) =>
    request<{ written: string[]; status: string }>(`/api/projects/${projectId}/export`, {
      method: 'POST',
      body: JSON.stringify({ formats }),
    }),
}

export interface CaptionCue {
  id: string
  start: number
  end: number
  speaker: string | null
  text: string
  kind: string
  words: Array<{ w: string; s: number; e: number; p: number }>
  flags: Array<{ type: string; detail?: string; span?: [number, number] | null }>
  status: 'draft' | 'approved'
  approved_by: string | null
  approved_at: string | null
}
