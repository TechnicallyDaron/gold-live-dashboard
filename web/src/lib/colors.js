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
