import { create } from 'zustand'
import { api } from '../api/client'
import { watchJob } from '../api/ws'
import type { Job, WsMessage } from '../api/types'

export interface JobView {
  id: string
  state: string
  stage: string
  percent: number
  statusText: string
  etaSeconds: number | null
  error: string | null
}

interface JobsState {
  jobs: Record<string, JobView>
  announce: string
  run: (projectId: string, type: string, params?: Record<string, unknown>) => Promise<string>
  cancel: (jobId: string) => Promise<void>
}

function viewFromJob(job: Job): JobView {
  return {
    id: job.id,
    state: job.state,
    stage: job.stage,
    percent: job.percent,
    statusText: job.status_text,
    etaSeconds: null,
    error: job.error,
  }
}

export const useJobsStore = create<JobsState>((set, get) => ({
  jobs: {},
  announce: '',

  async run(projectId, type, params = {}) {
    const { job_id } = await api.submitJob(projectId, type, params)
    const job = await api.getJob(job_id)
    set((s) => ({ jobs: { ...s.jobs, [job_id]: viewFromJob(job) } }))

    const update = (patch: Partial<JobView>, announce?: string) =>
      set((s) => ({
        jobs: { ...s.jobs, [job_id]: { ...s.jobs[job_id], ...patch } },
        ...(announce !== undefined ? { announce } : {}),
      }))

    watchJob(job_id, (message: WsMessage) => {
      switch (message.type) {
        case 'state':
          update({ state: message.state, stage: message.stage }, `Job ${message.state}.`)
          break
        case 'progress':
          update({ percent: message.percent, etaSeconds: message.eta_seconds })
          break
        case 'status':
          update({ statusText: message.message }, message.message)
          break
        case 'done':
          update({ state: 'succeeded', percent: 100 }, 'Job complete.')
          break
        case 'error':
          update({ state: 'failed', error: message.message }, `Job failed: ${message.message}`)
          break
        default:
          break
      }
    })
    return job_id
  },

  async cancel(jobId) {
    await api.cancelJob(jobId)
    const current = get().jobs[jobId]
    if (current) {
      set((s) => ({ jobs: { ...s.jobs, [jobId]: { ...current, state: 'cancelled' } } }))
    }
  },
}))
