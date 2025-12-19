# ClipAI Backend

AI-powered video clipping service - FastAPI backend with Celery workers.

## Railway Hobby Plan Optimization

This project is optimized for Railway Hobby plan (8 GB RAM, 8 vCPU, 100 GB disk):

### AI Service
- **Gemini API**: Uses `gemini-2.5-flash-lite` (default) and `gemini-2.5-flash` (for complex tasks)
- No local GPU required - all AI processing via Google Cloud

### Processing
- **Frames**: 1 frame every 10 seconds (`fps=0.1`) to reduce API calls
- **AI Batch**: 2 frames per batch to limit memory usage
- **FFmpeg**: `ultrafast` preset, CRF 26, 96k audio for faster processing

### Whisper
- **Model**: `small` (good balance of speed/accuracy)
- **Device**: CPU with `int8` compute type for lower memory

### Celery Worker
- Single worker with `--concurrency=1 --pool=solo`
- `--prefetch-multiplier=1` to process one task at a time

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
GOOGLE_API_KEY=your-google-api-key
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Gemini models
GEMINI_MODEL_DEFAULT=gemini-2.5-flash-lite
GEMINI_MODEL_STRICT=gemini-2.5-flash

# Storage (use /data/videos on Railway)
STORAGE_PATH=/data/videos
```

## Railway Deployment

### API Service
- Use `railway.json` or set start command:
  ```
  uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --limit-concurrency 50 --limit-max-requests 200
  ```

### Worker Service
- Create separate service with start command:
  ```
  celery -A app.tasks.celery_tasks worker --loglevel=info --concurrency=1 --pool=solo --prefetch-multiplier=1
  ```

### Required Plugins
- PostgreSQL
- Redis

### Environment Variables on Railway
- Set all variables from `.env.example`
- Use Railway's managed Postgres/Redis URLs
- Set `STORAGE_PATH=/data/videos` for persistent disk

## Local Development

```bash
# Start dependencies
docker-compose up -d

# Install requirements
pip install -r requirements.txt

# Run API
uvicorn app.main:app --reload

# Run worker (separate terminal)
celery -A app.tasks.celery_tasks worker --loglevel=info
```

## Memory Budget (8 GB total)

| Component | Estimated RAM |
|-----------|---------------|
| API (uvicorn) | ~500 MB |
| Celery Worker | ~500 MB |
| Whisper (small) | ~1.5 GB |
| FFmpeg (processing) | ~1-2 GB |
| OS/Buffer | ~2-3 GB |
| **Total** | ~6-7 GB |
