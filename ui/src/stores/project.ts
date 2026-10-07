// Current project: upload, transcribe, review, export. One project at a time
// in this slice; the project library view arrives with a later phase.

import { create } from 'zustand'
import { api, uploadProject, type CaptionCue } from '../api/client'
import { useJobsStore } from './jobs'

interface ProjectState {
  project: Record<string, unknown> | null
  projectId: string | null
  jobId: string | null
  cues: CaptionCue[]
  provenance: Record<string, unknown>
  exported: string[]
  exportStatus: string | null
  reviewerName: string
  busy: boolean
  error: string | null

  createFromFile: (file: File, outputs: Record<string, boolean>, model: string) => Promise<void>
  loadCaptions: () => Promise<void>
  editCue: (cueId: string, patch: { text?: string; speaker?: string }) => Promise<void>
  approveCue: (cueId: string, approve: boolean) => Promise<void>
  setReviewerName: (name: string) => void
  exportCaptions: (formats: string[]) => Promise<void>
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  project: null,
  projectId: null,
  jobId: null,
  cues: [],
  provenance: {},
  exported: [],
  exportStatus: null,
  reviewerName: '',
  busy: false,
  error: null,

  async createFromFile(file, outputs, model) {
    set({ busy: true, error: null, exported: [], exportStatus: null })
    try {
      const project = await uploadProject(file, file.name.replace(/\.[^.]+$/, ''), outputs)
      const projectId = String(project.id)
      set({ project, projectId })

      const jobId = await useJobsStore.getState().run(projectId, 'transcribe', { model })
      set({ jobId })

      // Refresh cues when the job reaches a terminal state.
      const poll = window.setInterval(() => {
        const job = useJobsStore.getState().jobs[jobId]
        if (!job) return
        if (job.state === 'succeeded') {
          window.clearInterval(poll)
          void get().loadCaptions()
          set({ busy: false })
        } else if (job.state === 'failed' || job.state === 'cancelled') {
          window.clearInterval(poll)
          set({ busy: false, error: job.error ?? `Job ${job.state}.` })
        }
      }, 400)
    } catch (err) {
      set({ busy: false, error: err instanceof Error ? err.message : String(err) })
    }
  },

  async loadCaptions() {
    const { projectId } = get()
    if (!projectId) return
    const data = await api.getCaptions(projectId)
    set({ cues: data.cues, provenance: data.provenance })
  },

  async editCue(cueId, patch) {
    const { projectId } = get()
    if (!projectId) return
    const cue = await api.patchCue(projectId, cueId, patch)
    set((s) => ({ cues: s.cues.map((c) => (c.id === cueId ? cue : c)) }))
  },

  async approveCue(cueId, approve) {
    const { projectId, reviewerName } = get()
    if (!projectId) return
    const cue = await api.patchCue(projectId, cueId, { approve, reviewer: reviewerName })
    set((s) => ({ cues: s.cues.map((c) => (c.id === cueId ? cue : c)) }))
    await get().loadCaptions() // provenance counts changed
  },

  setReviewerName(name) {
    set({ reviewerName: name })
    void api.putSettings({ reviewer_name: name }).catch(() => {})
  },

  async exportCaptions(formats) {
    const { projectId } = get()
    if (!projectId) return
    set({ error: null })
    try {
      const result = await api.exportCaptions(projectId, formats)
      set({ exported: result.written, exportStatus: result.status })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) })
    }
  },
}))
