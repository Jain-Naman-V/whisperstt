# Whisper ASR API — Render Free Tier

Deploys `openai/whisper-tiny.en` via **faster-whisper** (CTranslate2 INT8) on Render's free plan (512MB RAM, 0.1 CPU).

## Deploy to Render

1. Push this repo to GitHub
2. Go to [dashboard.render.com](https://dashboard.render.com) → **New +** → **Blueprint**
3. Connect your repo — `render.yaml` auto-configures everything

Or manually: **New Web Service** → connect repo → set:
- **Runtime:** Python
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
- **Plan:** Free

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/transcribe` | POST | Upload audio file, get transcription |

### Transcribe

```bash
curl -F "file=@audio.mp3" https://your-app.onrender.com/transcribe
```

Response:
```json
{
  "text": "transcribed text here",
  "duration_seconds": 3.2,
  "language": "en"
}
```

## Limits

- Max file size: **25MB**
- Free tier spins down after **15min idle** (cold start ~30s on first request)
- ~75MB model download on first deploy (cached in ephemeral disk)

## Keep-Alive (prevent spin-down)

A GitHub Actions workflow (`.github/workflows/keep-alive.yml`) pings `/health` every 10 minutes automatically after you push the repo. No setup needed.

**Set custom URL** (if your Render URL isn't the default):
1. Go to repo → **Settings** → **Secrets and variables** → **Actions** → **Variables**
2. Add `RENDER_APP_URL` = `https://your-app.onrender.com`

### Alternative: cron-job.org (no GitHub needed)

1. Go to [cron-job.org](https://cron-job.org) — free, no credit card
2. Create a job: `https://your-app.onrender.com/health` every **10 minutes**
3. Done
