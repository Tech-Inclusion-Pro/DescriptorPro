// Shapes shared with the service (service/jobs/models.py, service/ws.py).

export type JobState = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'

export interface Job {
  id: string
  type: string
  project_id: string
  params: Record<string, unknown>
  state: JobState
  stage: string
  percent: number
  status_text: string
  created: string
  started: string | null
  finished: string | null
  error: string | null
  result: Record<string, unknown> | null
}

export interface ProjectSummary {
  id: string
  title: string
  status: string
  created: string
  updated: string
}

export type WsMessage =
  | { type: 'state'; state: JobState; stage: string; percent?: number }
  | { type: 'progress'; percent: number; stage: string; eta_seconds: number | null }
  | { type: 'status'; message: string }
  | { type: 'partial'; payload: Record<string, unknown> }
  | { type: 'done'; result: Record<string, unknown> }
  | { type: 'error'; message: string }
