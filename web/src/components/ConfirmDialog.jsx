import './ConfirmDialog.css'

export default function ConfirmDialog({ title, body, confirmLabel = 'Remove', onConfirm, onCancel }) {
  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-box" onClick={(e) => e.stopPropagation()}>
        <span className="confirm-title">{title}</span>
        {body && <p className="confirm-body">{body}</p>}
        <div className="confirm-actions">
          <button type="button" className="confirm-btn confirm-btn--cancel" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="confirm-btn confirm-btn--danger" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
