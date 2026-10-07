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
  patchCue: (projectId: string, cueId: string, body: { text?: string; speaker?: string; approve?: boolean; reviewer?: string }) =>
    request<CaptionCue>(`/api/projects/${projectId}/captions/${cueId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  exportCaptions: (projectId: string, formats: string[]) =>
    request<{ written: string[]; status: string }>(`/api/projects/${projectId}/export`, {
      method: 'POST',
      body: JSON.stringify({ formats }),
    }),
  getIntentQuestions: () =>
    request<{ questions: Array<{ id: string; text: string; options?: string[] }> }>(
      '/api/intent/questions',
    ),
  getIntent: (projectId: string) =>
    request<{ intent: IntentProfile }>(`/api/projects/${projectId}/intent`),
  putIntent: (projectId: string, intent: IntentProfile) =>
    request<{ intent: IntentProfile }>(`/api/projects/${projectId}/intent`, {
      method: 'PUT',
      body: JSON.stringify({ intent }),
    }),
  converseIntent: (projectId: string, answers: Record<string, string>) =>
    request<{ intent: IntentProfile }>(`/api/projects/${projectId}/intent/converse`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    }),
  getSegments: (projectId: string) =>
    request<SegmentsReport>(`/api/projects/${projectId}/segments`),
  patchDecision: (projectId: string, segmentId: string, value: string, by: string | null) =>
    request<SegmentDecision>(`/api/projects/${projectId}/segments/${segmentId}/decision`, {
      method: 'PATCH',
      body: JSON.stringify({ value, by }),
    }),
  getStandards: () => request<StandardsDoc>('/api/standards'),
  exportPlayer: (projectId: string) =>
    request<{ folder: string; files: string[]; embed_code: string }>(
      `/api/projects/${projectId}/export-player`,
      { method: 'POST' },
    ),
  getDescriptions: (projectId: string) =>
    request<{ cues: DescriptionCue[]; ad_style: string; added_running_time: number }>(
      `/api/projects/${projectId}/descriptions`,
    ),
  patchDescription: (
    projectId: string,
    cueId: string,
    body: { text?: string; use?: 'suggested' | 'full' | 'short'; approve?: boolean; reviewer?: string },
  ) =>
    request<DescriptionCue>(`/api/projects/${projectId}/descriptions/${cueId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
}

export interface IntentPerson {
  label: string
  role: string
  self_description: string | null
  source: string
}

export interface IntentProfile {
  audience: string
  purpose: string
  content_type: string
  people: IntentPerson[]
  detail_level: string
  languages: string[]
  key_terms: string[]
  notes: string
}

export interface VisualFact {
  id: string
  text: string
  kind: string
  essential: boolean
  flags: Array<{ type: string; detail?: string }>
  coverage?: { answer: string; evidence: string }
}

export interface SegmentDecision {
  value: 'describe' | 'skip' | 'undecided'
  by: string | null
  at: string | null
}

export interface Segment {
  id: string
  start: number
  end: number
  keyframes: string[]
  ocr_text: string[]
  visual_facts: VisualFact[]
  transcript_window: string
  need: {
    verdict: 'needed' | 'not_needed' | 'uncertain'
    reason: string
    uncovered_facts: string[]
    criteria: string[]
    deictic: string[]
    coach: string | null
  } | null
  decision: SegmentDecision
}

export interface SegmentsReport {
  segments: Segment[]
  tally: { needed: number; not_needed: number; uncertain: number; unchecked: number }
  standards_checked: string[]
  notice: string
}

export interface DescriptionCue {
  id: string
  segment: string
  start: number
  gap: number
  text: string
  full_text: string
  short_text: string
  suggested_text?: string
  est_duration: number
  mode: 'inline' | 'extended'
  placement: 'in_gap' | 'before_content'
  voice: { kind: string; clip: string | null }
  flags: Array<{ type: string; detail?: string }>
  criteria: string[]
  verification?: { checked: boolean; claims: Array<{ text: string; verdict: string }> }
  status: 'draft' | 'approved'
  approved_by: string | null
  approved_at: string | null
  lang: string
}

export interface StandardsDoc {
  version: string
  quotes_verified: boolean
  verification_notice: string
  criteria: Array<{
    id: string
    name: string
    plain_rule: string
    quote: string
    source_ids: string[]
    app_behavior: string
    flag_types: string[]
  }>
  sources: Array<{ id: string; apa: string; led_by: string; leadership_note: string }>
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
