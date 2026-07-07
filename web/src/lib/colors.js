// Maps the API's bias `color` field to design-token CSS vars.
export const BIAS_COLOR_VAR = {
  green: 'var(--long)',
  red: 'var(--short)',
  orange: 'var(--watch)',
  gray: 'var(--muted)',
}

export function biasColorVar(color) {
  return BIAS_COLOR_VAR[color] || 'var(--muted)'
}

// Maps /api/backtest viability.class to design-token CSS vars.
export const VIABILITY_COLOR_VAR = {
  good: 'var(--long)',
  mid: 'var(--watch)',
  bad: 'var(--short)',
}

export function viabilityColorVar(cls) {
  return VIABILITY_COLOR_VAR[cls] || 'var(--muted)'
}
