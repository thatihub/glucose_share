# Glucose Share

Standalone, isolated glucose dashboard for sharing with friends for testing.

## What it is

A minimal web server that serves **only** the glucose page from the Personal Health Manager:

- `/` — the glucose dashboard (no navigation to other pages)
- `/glucose_data.js` — live glucose data (read directly from the main project)
- `/glucose_view.js` — chart and analysis logic
- `/static/*` — CSS/JS assets
- `/api/dexcom/*` — proxied to the main server so the Sync button works

Everything else returns 404. Friends cannot access labs, weight, medications, or any other part of the health manager.

## Running

```bash
cd ~/Documents/Health/glucose-share
python3 share_server.py
```

Serves on `http://127.0.0.1:3003`.

## Sharing via Tailscale Funnel

```bash
tailscale funnel --bg --https 8444 http://localhost:3003
```

Friends open the printed public URL in any browser — no Tailscale needed.

To stop:

```bash
tailscale funnel --https=8444 off
pkill -f share_server.py
```

## Notes

- `glucose_data.js` is read live from the main project directory, so it stays fresh after each Dexcom sync.
- The Sync button proxies to the main health-manager server (must be running on port 3002).
- `share.log` and `paths.log` are runtime logs (git-ignored).
