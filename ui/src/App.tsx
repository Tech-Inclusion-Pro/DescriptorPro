import { useEffect, useState } from 'react'
import { AppBar } from './components/AppBar'
import { DisplaySettings } from './components/DisplaySettings'
import { LiveRegion } from './components/LiveRegion'
import { ModeSwitch, type Mode } from './components/ModeSwitch'
import { StepTabs, useSteps, type StepId } from './components/StepTabs'
import { MediaPane } from './panes/MediaPane'
import { IntentPane } from './panes/IntentPane'
import { NeedCheckPane } from './panes/NeedCheckPane'
import { ReviewPane } from './panes/ReviewPane'
import { ExportPane } from './panes/ExportPane'
import { LivePane } from './panes/LivePane'
import { StandardsPane } from './panes/StandardsPane'
import { useSessionStore } from './stores/session'
import { t, useI18n } from './i18n'

export default function App() {
  useI18n()
  const [mode, setMode] = useState<Mode>('recorded')
  const [step, setStep] = useState<StepId>('media')
  const steps = useSteps()
  const checkHealth = useSessionStore((s) => s.checkHealth)

  useEffect(() => {
    void checkHealth()
    const interval = window.setInterval(() => void checkHealth(), 10000)
    return () => window.clearInterval(interval)
  }, [checkHealth])

  return (
    <>
      <a className="skip" href="#main">
        {t('app.skip')}
      </a>
      <AppBar />
      <main id="main" className="wrap">
        <ModeSwitch mode={mode} onChange={setMode} />

        <div hidden={mode !== 'recorded'}>
          <StepTabs steps={steps} active={step} onSelect={setStep} />
          <MediaPane hidden={step !== 'media'} />
          <IntentPane hidden={step !== 'intent'} />
          <NeedCheckPane hidden={step !== 'need'} />
          <ReviewPane hidden={step !== 'review'} />
          <ExportPane hidden={step !== 'export'} />
        </div>

        <LivePane hidden={mode !== 'live'} />
        <StandardsPane hidden={mode !== 'standards'} />

        <p className="foot">
          Phase 0 shell. The display settings button changes how this app looks and stores your choices
          on your own device.
        </p>
      </main>
      <DisplaySettings />
      <LiveRegion />
    </>
  )
}
