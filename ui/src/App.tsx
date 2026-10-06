import { useEffect, useState } from 'react'
import { AppBar } from './components/AppBar'
import { DisplaySettings } from './components/DisplaySettings'
import { LiveRegion } from './components/LiveRegion'
import { ModeSwitch, type Mode } from './components/ModeSwitch'
import { StepTabs, type StepId, type StepInfo } from './components/StepTabs'
import { MediaPane } from './panes/MediaPane'
import { IntentPane } from './panes/IntentPane'
import { NeedCheckPane } from './panes/NeedCheckPane'
import { ReviewPane } from './panes/ReviewPane'
import { ExportPane } from './panes/ExportPane'
import { LivePane } from './panes/LivePane'
import { StandardsPane } from './panes/StandardsPane'
import { useSessionStore } from './stores/session'
import { useProjectStore } from './stores/project'
import { api } from './api/client'
import { t, useI18n } from './i18n'

export default function App() {
  useI18n()
  const [mode, setMode] = useState<Mode>('recorded')
  const [step, setStep] = useState<StepId>('media')
  const checkHealth = useSessionStore((s) => s.checkHealth)
  const connected = useSessionStore((s) => s.connected)
  const project = useProjectStore()

  useEffect(() => {
    void checkHealth()
    const interval = window.setInterval(() => void checkHealth(), 10000)
    return () => window.clearInterval(interval)
  }, [checkHealth])

  // Load the saved reviewer name once the service is reachable.
  useEffect(() => {
    if (!connected || project.reviewerName) return
    void api
      .getSettings()
      .then((s) => {
        if (s.reviewer_name) useProjectStore.setState({ reviewerName: s.reviewer_name })
      })
      .catch(() => {})
  }, [connected, project.reviewerName])

  const approved = project.cues.filter((c) => c.status === 'approved').length
  const steps: StepInfo[] = [
    {
      id: 'media',
      label: t('steps.media'),
      state: project.projectId ? t('steps.state.done') : t('steps.state.not_started'),
    },
    { id: 'intent', label: t('steps.intent'), state: t('steps.state.phase2') },
    { id: 'need', label: t('steps.need'), state: t('steps.state.phase2') },
    {
      id: 'review',
      label: t('steps.review'),
      state: project.cues.length
        ? `${approved}/${project.cues.length} ${t('steps.state.approved')}`
        : t('steps.state.not_started'),
    },
    {
      id: 'export',
      label: t('steps.export'),
      state: project.exported.length
        ? t('steps.state.done')
        : project.cues.length
          ? t('steps.state.ready')
          : t('steps.state.not_started'),
    },
  ]

  return (
    <>
      <a className="skip" href="#main">
        {t('app.skip')}
      </a>
      <AppBar />
      <main id="main" className="wrap" style={{ paddingBlockStart: '1.25rem' }}>
        <ModeSwitch mode={mode} onChange={setMode} />

        <div hidden={mode !== 'recorded'}>
          <StepTabs steps={steps} active={step} onSelect={setStep} />
          <MediaPane hidden={step !== 'media'} onDrafted={() => setStep('review')} />
          <IntentPane hidden={step !== 'intent'} />
          <NeedCheckPane hidden={step !== 'need'} />
          <ReviewPane hidden={step !== 'review'} />
          <ExportPane hidden={step !== 'export'} />
        </div>

        <LivePane hidden={mode !== 'live'} />
        <StandardsPane hidden={mode !== 'standards'} />

        <p className="foot">{t('app.foot')}</p>
      </main>
      <DisplaySettings />
      <LiveRegion />
    </>
  )
}
