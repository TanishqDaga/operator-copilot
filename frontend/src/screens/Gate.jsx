import { ClipboardCheck, FileText, Lock } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, Empty } from '../components/ui'
import { useApp } from '../lib/store'

/** Blocks a screen's content until the pre-start checklist is complete. */
export default function Gate({ children, allowEnded = false, what = 'this screen' }) {
  const { state } = useApp()
  if (!state) return null
  const sh = state.shift
  if (sh.active || (allowEnded && sh.ended)) return children
  if (sh.ended) {
    return (
      <Card>
        <Empty icon={FileText} title="Shift ended" action={<Link className="btn btn-primary btn-md" to="/summary">Open shift summary</Link>}>
          The shift has been closed. The handoff report is ready.
        </Empty>
      </Card>
    )
  }
  return (
    <Card className="grid-bg">
      <Empty icon={Lock} title="Locked until the pre-start checklist is complete"
        action={<Link className="btn btn-primary btn-lg" to="/start"><ClipboardCheck size={18} /> Go to pre-start checklist</Link>}>
        Sign in and confirm every pre-start item to release the machine and unlock {what}.
      </Empty>
    </Card>
  )
}
