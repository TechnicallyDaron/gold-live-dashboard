import { useRef, useState } from 'react'
import './BottomSheet.css'

const DISMISS_THRESHOLD = 90

export default function BottomSheet({ title, onClose, children, heightVh = 85 }) {
  const [dragY, setDragY] = useState(0)
  const dragState = useRef(null)

  const onTouchStart = (e) => {
    dragState.current = { startY: e.touches[0].clientY }
  }
  const onTouchMove = (e) => {
    if (!dragState.current) return
    const delta = e.touches[0].clientY - dragState.current.startY
    setDragY(Math.max(0, delta))
  }
  const onTouchEnd = () => {
    if (dragY > DISMISS_THRESHOLD) {
      onClose()
    } else {
      setDragY(0)
    }
    dragState.current = null
  }

  return (
    <div className="bs-overlay" onClick={onClose}>
      <div
        className="bs-sheet"
        style={{ height: `${heightVh}vh`, transform: `translateY(${dragY}px)` }}
        onClick={(e) => e.stopPropagation()}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <div className="bs-handle" />
        {title && <span className="bs-title">{title}</span>}
        <div className="bs-body">{children}</div>
      </div>
    </div>
  )
}
