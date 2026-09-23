import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { api } from './api'
import { useApp } from './store'

const Ctx = createContext(null)
export const useCamera = () => useContext(Ctx)

const FRAME_W = 480
const MIN_INTERVAL_MS = 220

/** Streams webcam frames to POST /api/vision/frame while the person source is "camera". */
export function CameraProvider({ children }) {
  const { state } = useApp()
  const wanted = state?.shift?.active && state?.vision?.source === 'camera'
  const [stream, setStream] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [fps, setFps] = useState(0)
  const videoRef = useRef(null)

  useEffect(() => {
    if (!wanted) return
    let alive = true
    let media
    const video = document.createElement('video')
    video.muted = true
    video.playsInline = true
    videoRef.current = video
    const canvas = document.createElement('canvas')
    setError(null)

    const loop = async () => {
      let frames = 0
      let windowStart = performance.now()
      while (alive) {
        const t0 = performance.now()
        if (video.videoWidth) {
          canvas.width = FRAME_W
          canvas.height = Math.round((video.videoHeight / video.videoWidth) * FRAME_W)
          canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
          try {
            const r = await api.post('/vision/frame', { image: canvas.toDataURL('image/jpeg', 0.7) })
            if (alive) setResult(r)
            frames += 1
          } catch (e) {
            if (alive) setError(e.message)
          }
        }
        const now = performance.now()
        if (now - windowStart > 2000) {
          if (alive) setFps(frames / ((now - windowStart) / 1000))
          frames = 0
          windowStart = now
        }
        const wait = Math.max(0, MIN_INTERVAL_MS - (performance.now() - t0))
        await new Promise((r) => setTimeout(r, wait))
      }
    }

    navigator.mediaDevices
      ?.getUserMedia({ video: { width: 640, height: 480 }, audio: false })
      .then(async (m) => {
        if (!alive) { m.getTracks().forEach((t) => t.stop()); return }
        media = m
        video.srcObject = m
        await video.play()
        setStream(m)
        loop()
      })
      .catch((e) => setError(e?.name === 'NotAllowedError' ? 'Camera permission denied' : 'No camera available'))

    return () => {
      alive = false
      media?.getTracks().forEach((t) => t.stop())
      setStream(null)
      setResult(null)
      setFps(0)
    }
  }, [wanted])

  return <Ctx.Provider value={{ wanted, stream, result, error, fps }}>{children}</Ctx.Provider>
}
