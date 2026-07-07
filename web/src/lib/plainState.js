// Mirrors api/analytics.py::plain_state() verbatim — the backend's plain-
// English translator isn't exposed over REST (only used in Telegram
// replies), so this ports the exact same copy for the frontend to reuse.
function money(n) {
  return `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function plainState(b) {
  const state = b.state || ''

  if (state.includes('LONG-REVERSION ARMED')) {
    return {
      emoji: '🟢',
      headline: 'Buy-the-dip setup is LIVE — price is stretched unusually far below its average while the bigger trend still points up.',
      action: `Zone: near ${money(b.arm_level)} · Wrong if it closes past ${money(b.invalidation)} · Target back around ${money(b.target)}`,
    }
  }
  if (state.includes('SHORT-REVERSION ARMED')) {
    return {
      emoji: '🔴',
      headline: 'Fade-the-spike setup is LIVE — price is stretched unusually far above its average while the bigger trend points down.',
      action: `Zone: near ${money(b.arm_level)} · Wrong if it closes past ${money(b.invalidation)} · Target back around ${money(b.target)}`,
    }
  }
  if (state.includes('WATCH')) {
    return {
      emoji: '👀',
      headline: 'Getting interesting — price is drifting toward the edge of its normal range. Not a setup yet; worth watching.',
      action: `A setup would arm near ${money(b.arm_level)}`,
    }
  }
  return {
    emoji: '😴',
    headline: 'No setup — price is inside its normal range. Nothing statistically interesting here. Waiting IS the move.',
    action: `Nearest interesting level: ${money(b.arm_level)} (${b.dist_to_arm_pct >= 0 ? '+' : ''}${b.dist_to_arm_pct.toFixed(1)}% away)`,
  }
}
