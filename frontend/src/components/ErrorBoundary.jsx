import { TriangleAlert } from 'lucide-react'
import { Component } from 'react'
import { Card, Empty } from './ui'

/** Keeps the shell (nav, safety strip) alive if a single screen fails to render. */
export default class ErrorBoundary extends Component {
  state = { error: null }
  static getDerivedStateFromError(error) { return { error } }
  componentDidUpdate(prev) { if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null }) }
  render() {
    if (!this.state.error) return this.props.children
    return (
      <Card>
        <Empty icon={TriangleAlert} title="This screen could not be displayed"
          action={<button className="btn btn-ghost btn-md" onClick={() => this.setState({ error: null })}>Try again</button>}>
          The rest of the app keeps running. Safety alerts still appear in the header.
        </Empty>
      </Card>
    )
  }
}
