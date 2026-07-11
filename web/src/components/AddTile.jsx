import './AddTile.css'

export default function AddTile({ onClick }) {
  return (
    <button type="button" className="add-tile" onClick={onClick} data-tour="add-tile">
      <span className="add-tile-plus">+</span>
      <span className="add-tile-label">Add asset</span>
    </button>
  )
}
