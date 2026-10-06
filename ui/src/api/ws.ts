import { getBootstrap, wsBase } from '../lib/bootstrap'
import type { WsMessage } from './types'

// Subscribe to a job's progress stream. Returns an unsubscribe function.
// On a dropped socket the caller re-fetches GET /api/jobs/{id}; nothing is lost
// because the job record carries full state.
export function watchJob(
  jobId: string,
  onMessage: (message: WsMessage) => void,
  onClose?: () => void,
): () => void {
  const { token } = getBootstrap()
  const socket = new WebSocket(`${wsBase()}/ws/jobs/${jobId}?token=${encodeURIComponent(token)}`)

  socket.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data as string) as WsMessage)
    } catch {
      /* ignore malformed frames */
    }
  }
  socket.onclose = () => onClose?.()

  return () => socket.close()
}
