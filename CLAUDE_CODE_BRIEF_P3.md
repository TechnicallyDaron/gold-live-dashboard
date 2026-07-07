# N-CORE PWA — PHASE 3 (4b): AI TIER GOES LIVE

Backend already updated (pull first). Same law: no Python edits.

## New endpoints
- POST /api/ask  body {asset, question} → {answer, usage:{count,limit}}
  Errors: 503 = AI not configured · 429 = daily budget reached (show detail msg)
- GET /api/sentiment/{asset} → {overall:{sentiment,score,summary},
  impacts:[{i,tilt,impact}], items:[{title,link,published}]}
  (impacts[i] indexes into items; {raw} fallback if model returned non-JSON)

## 1. Bias screen — Quick Prompts
- Pill row of canned prompts: "Explain this in simple terms" ·
  "Is now a good entry?" · "What flips this setup?" · "Risk for a beginner"
  plus a free-text input + Ask button (⚡)
- Answer renders in a volt-bordered card (#00E5FF edge, subtle glow),
  with tiny usage line "N/limit AI calls today" from response.usage
- Loading: shimmer in the answer card. 429/503: show the API's detail
  string in an amber notice — never a dead button.

## 2. News screen — AI Macro Read activates
- Replace the disabled Phase-4b pill with "🤖 Analyze" button →
  GET /api/sentiment/{asset}
- Overall block: sentiment + score chip (green/red/gray) + summary
- Each headline card gains an expandable Macro read: tilt badge
  (bullish=long green / bearish=short red / neutral=muted) + impact line
- Cache respect: results persist in component state per asset; don't
  re-fetch on tab switches within the session.

## Tokens & states
volt #00E5FF for AI frames · same card anatomy · skeletons not spinners ·
explicit error states for 429/503 with the server's message.
