// Phase 2 slice: intent conversation + profile, visual track, need check.
// The profile drives the visual track's sampling; the need check reads the
// segments and the caption cues. Decisions are recorded per segment.

import { create } from 'zustand'
import {
  api,
  uploadImages,
  uploadProject,
  type DescriptionCue,
  type ImageItem,
  type IntentProfile,
  type SegmentsReport,
} from '../api/client'
import { useJobsStore } from './jobs'
import { useProjectStore } from './project'

interface Question {
  id: string
  text: string
  options?: string[]
}

function runJob(projectId: string, type: string): Promise<void> {
  return new Promise((resolve, reject) => {
    void useJobsStore
      .getState()
      .run(projectId, type, {})
      .then((jobId) => {
        const poll = window.setInterval(() => {
          const job = useJobsStore.getState().jobs[jobId]
          if (!job) return
          if (job.state === 'succeeded') {
            window.clearInterval(poll)
            resolve()
          } else if (job.state === 'failed' || job.state === 'cancelled') {
            window.clearInterval(poll)
            reject(new Error(job.error ?? `Job ${job.state}.`))
          }
        }, 400)
      }, reject)
  })
}

interface AnalysisState {
  questions: Question[]
  step: number // index into questions; >= questions.length means done
  answers: Record<string, string>
  intent: IntentProfile | null
  intentBusy: boolean
  report: SegmentsReport | null
  phase: 'idle' | 'visual' | 'need_check' | 'describe'
  descriptions: DescriptionCue[]
  adStyle: string
  addedRunningTime: number
  images: ImageItem[]
  busy: boolean
  error: string | null

  loadIntent: () => Promise<void>
  answerCurrent: (text: string) => void
  skipCurrent: () => void
  buildProfile: () => Promise<void>
  saveIntent: (intent: IntentProfile) => Promise<void>
  restartConversation: () => void
  loadSegments: () => Promise<void>
  runNeedCheck: () => Promise<void>
  setDecision: (segmentId: string, value: 'describe' | 'skip' | 'undecided') => Promise<void>
  loadDescriptions: () => Promise<void>
  runDescribe: () => Promise<void>
  renderDescribed: () => Promise<string | null>
  exportPlayer: () => Promise<{ folder: string; embed_code: string } | null>
  loadImages: () => Promise<void>
  uploadImageBatch: (files: File[]) => Promise<void>
  describeImages: () => Promise<void>
  patchImage: (
    imageId: string,
    body: { alt?: string; long_description?: string; decorative_confirmed?: boolean; approve?: boolean },
  ) => Promise<void>
  patchDescription: (
    cueId: string,
    body: { text?: string; use?: 'suggested' | 'full' | 'short'; approve?: boolean },
  ) => Promise<void>
}

export const useAnalysisStore = create<AnalysisState>((set, get) => ({
  questions: [],
  step: 0,
  answers: {},
  intent: null,
  intentBusy: false,
  report: null,
  phase: 'idle',
  descriptions: [],
  adStyle: 'standard',
  addedRunningTime: 0,
  images: [],
  busy: false,
  error: null,

  async loadIntent() {
    const { projectId } = useProjectStore.getState()
    const [{ questions }, intent] = await Promise.all([
      api.getIntentQuestions(),
      projectId ? api.getIntent(projectId).then((r) => r.intent) : Promise.resolve(null),
    ])
    set({ questions, intent })
  },

  answerCurrent(text) {
    const { questions, step, answers } = get()
    const question = questions[step]
    if (!question) return
    set({
      answers: text.trim() ? { ...answers, [question.id]: text.trim() } : answers,
      step: step + 1,
    })
  },

  skipCurrent() {
    set({ step: get().step + 1 })
  },

  async buildProfile() {
    const { projectId } = useProjectStore.getState()
    if (!projectId) return
    set({ intentBusy: true, error: null })
    try {
      const { intent } = await api.converseIntent(projectId, get().answers)
      set({ intent, intentBusy: false })
    } catch (err) {
      set({ intentBusy: false, error: err instanceof Error ? err.message : String(err) })
    }
  },

  async saveIntent(intent) {
    const { projectId } = useProjectStore.getState()
    if (!projectId) return
    const saved = await api.putIntent(projectId, intent)
    set({ intent: saved.intent })
  },

  restartConversation() {
    set({ step: 0, answers: {} })
  },

  async loadSegments() {
    const { projectId } = useProjectStore.getState()
    if (!projectId) return
    set({ report: await api.getSegments(projectId) })
  },

  async runNeedCheck() {
    const { projectId } = useProjectStore.getState()
    if (!projectId) return
    set({ busy: true, error: null, phase: 'visual' })
    try {
      await runJob(projectId, 'visual_track')
      set({ phase: 'need_check' })
      await runJob(projectId, 'need_check')
      await get().loadSegments()
      set({ busy: false, phase: 'idle' })
    } catch (err) {
      set({ busy: false, phase: 'idle', error: err instanceof Error ? err.message : String(err) })
    }
  },

  async loadDescriptions() {
    const { projectId } = useProjectStore.getState()
    if (!projectId) return
    const data = await api.getDescriptions(projectId)
    set({ descriptions: data.cues, adStyle: data.ad_style, addedRunningTime: data.added_running_time })
  },

  async runDescribe() {
    const { projectId } = useProjectStore.getState()
    if (!projectId) return
    set({ busy: true, error: null, phase: 'describe' })
    try {
      await runJob(projectId, 'describe')
      await get().loadDescriptions()
      set({ busy: false, phase: 'idle' })
    } catch (err) {
      set({ busy: false, phase: 'idle', error: err instanceof Error ? err.message : String(err) })
    }
  },

  async renderDescribed() {
    const { projectId } = useProjectStore.getState()
    if (!projectId) return null
    set({ busy: true, error: null, phase: 'describe' })
    try {
      await runJob(projectId, 'render_described')
      set({ busy: false, phase: 'idle' })
      return 'done'
    } catch (err) {
      set({ busy: false, phase: 'idle', error: err instanceof Error ? err.message : String(err) })
      return null
    }
  },

  async exportPlayer() {
    const { projectId } = useProjectStore.getState()
    if (!projectId) return null
    try {
      return await api.exportPlayer(projectId)
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) })
      return null
    }
  },

  async loadImages() {
    const { projectId } = useProjectStore.getState()
    if (!projectId) return
    const data = await api.getImages(projectId)
    set({ images: data.images })
  },

  async uploadImageBatch(files) {
    if (!files.length) return
    set({ busy: true, error: null })
    try {
      let { projectId } = useProjectStore.getState()
      if (!projectId) {
        // Image-only batch: the first file becomes the project source;
        // no transcription runs.
        const title = files[0].name.replace(/\.[^.]+$/, '')
        const project = await uploadProject(files[0], title, { image_description: true })
        projectId = String(project.id)
        useProjectStore.setState({ project, projectId })
      }
      const result = await uploadImages(projectId, files)
      set({ images: result.images, busy: false })
    } catch (err) {
      set({ busy: false, error: err instanceof Error ? err.message : String(err) })
    }
  },

  async describeImages() {
    const { projectId } = useProjectStore.getState()
    if (!projectId) return
    set({ busy: true, error: null, phase: 'describe' })
    try {
      await runJob(projectId, 'describe_images')
      await get().loadImages()
      set({ busy: false, phase: 'idle' })
    } catch (err) {
      set({ busy: false, phase: 'idle', error: err instanceof Error ? err.message : String(err) })
    }
  },

  async patchImage(imageId, body) {
    const { projectId, reviewerName } = useProjectStore.getState()
    if (!projectId) return
    const item = await api.patchImage(projectId, imageId, {
      ...body,
      reviewer: body.approve ? reviewerName : undefined,
    })
    set((s) => ({ images: s.images.map((i) => (i.id === imageId ? item : i)) }))
  },

  async patchDescription(cueId, body) {
    const { projectId, reviewerName } = useProjectStore.getState()
    if (!projectId) return
    const cue = await api.patchDescription(projectId, cueId, {
      ...body,
      reviewer: body.approve ? reviewerName : undefined,
    })
    set((s) => ({ descriptions: s.descriptions.map((c) => (c.id === cueId ? cue : c)) }))
  },

  async setDecision(segmentId, value) {
    const { projectId, reviewerName } = useProjectStore.getState()
    if (!projectId) return
    const decision = await api.patchDecision(projectId, segmentId, value, reviewerName || null)
    set((s) => ({
      report: s.report
        ? {
            ...s.report,
            segments: s.report.segments.map((seg) =>
              seg.id === segmentId ? { ...seg, decision } : seg,
            ),
          }
        : s.report,
    }))
  },
}))
