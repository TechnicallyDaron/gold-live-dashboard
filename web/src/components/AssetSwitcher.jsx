import './AssetSwitcher.css'

export default function AssetSwitcher({ names, selected, onSelect }) {
  return (
    <div className="asset-switcher">
      {names.map((name) => (
        <button
          key={name}
          type="button"
          className={name === selected ? 'asset-pill asset-pill--active' : 'asset-pill'}
          onClick={() => onSelect(name)}
        >
          {name}
        </button>
      ))}
    </div>
  )
}
