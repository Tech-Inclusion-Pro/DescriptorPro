// Phase 2 slice: intent conversation + profile, visual track, need check.
// The profile drives the visual track's sampling; the need check reads the
// segments and the caption cues. Decisions are recorded per segment.

import { create } from 'zustand'
import { api, type IntentProfile, type SegmentsReport } from '../api/client'
import { useJobsStore } from './jobs'
import { useProjectStore } from './project'

interface Question {
  id: string
  text: string
  options?: string[]
}

interface AnalysisState {
  questions: Question[]
  step: number // index into questions; >= questions.length means done
  answers: Record<string, string>
  intent: IntentProfile | null
  intentBusy: boolean
  report: SegmentsReport | null
  phase: 'idle' | 'visual' | 'need_check'
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
}

export const useAnalysisStore = create<AnalysisState>((set, get) => ({
  questions: [],
  step: 0,
  answers: {},
  intent: null,
  intentBusy: false,
  report: null,
  phase: 'idle',
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

    const runJob = (type: string) =>
      new Promise<void>((resolve, reject) => {
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

    try {
      await runJob('visual_track')
      set({ phase: 'need_check' })
      await runJob('need_check')
      await get().loadSegments()
      set({ busy: false, phase: 'idle' })
    } catch (err) {
      set({ busy: false, phase: 'idle', error: err instanceof Error ? err.message : String(err) })
    }
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
