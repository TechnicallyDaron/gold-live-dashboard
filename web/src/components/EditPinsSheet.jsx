import { useState } from 'react'
import BottomSheet from './BottomSheet.jsx'
import './EditPinsSheet.css'

const MAX_PINS = 4

export default function EditPinsSheet({ names, pinned, onClose, onSave }) {
  // Working copy — nothing persists until Save. Toggling on appends to the
  // end (newest pin ranks last in priority); toggling off preserves the
  // relative order of whatever's left.
  const [draft, setDraft] = useState(pinned)

  const togglePin = (name) => {
    setDraft((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : prev.length < MAX_PINS ? [...prev, name] : prev
    )
  }

  const save = () => {
    onSave(draft)
    onClose()
  }

  return (
    <BottomSheet title="Edit Top 4" onClose={onClose} heightVh={70}>
      <p className="eps-counter">{draft.length} of {MAX_PINS} pinned</p>

      <div className="eps-list">
        {names.map((name) => {
          const isPinned = draft.includes(name)
          const atCap = draft.length >= MAX_PINS && !isPinned
          return (
            <button
              key={name}
              type="button"
              className={isPinned ? 'eps-row eps-row--pinned' : 'eps-row'}
              disabled={atCap}
              onClick={() => togglePin(name)}
            >
              <span className="eps-row-name">{name}</span>
              <span className={isPinned ? 'eps-pin-glyph eps-pin-glyph--active' : 'eps-pin-glyph'}>
                {isPinned ? '📌' : '📍'}
              </span>
            </button>
          )
        })}
      </div>

      <div className="eps-actions">
        <button type="button" className="eps-btn eps-btn--cancel" onClick={onClose}>
          Cancel
        </button>
        <button type="button" className="eps-btn eps-btn--save" onClick={save}>
          Save
        </button>
      </div>
    </BottomSheet>
  )
}
