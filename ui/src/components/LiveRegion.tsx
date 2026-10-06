// Polite live region for job progress and status changes (spec §12: status
// changes go to a polite live region; announcements are throttled upstream by
// the service's ≤2/sec progress cap and the jobs store announcing only
// status/state changes, not every percent tick).

import { useJobsStore } from '../stores/jobs'

export function LiveRegion() {
  const announce = useJobsStore((s) => s.announce)
  return (
    <p className="sr-only" role="status" aria-live="polite">
      {announce}
    </p>
  )
}
