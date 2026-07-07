# N-CORE — mobile PWA

Robinhood-feel mobile frontend for Nyarko's Trade Manager. Talks to the
existing FastAPI backend (`api/main.py`) — no backend logic lives here.

## Develop

```
cp .env.example .env   # set VITE_API_URL to your local/deployed API
npm install
npm run dev
```

## Build & run (Railway)

Root directory: `web/`. Build command: `npm run build`. Start command:
`npm start` — serves the built `dist/` on `$PORT` via `serve`.
