# ClipAI - Arquitetura e Fluxo Completo do Projeto

> **Documento gerado por análise direta do código-fonte em 23/12/2024**

---

## 📋 Visão Geral

O ClipAI é uma aplicação web que automaticamente:
1. Recebe um vídeo (upload ou URL do YouTube)
2. Analisa o conteúdo com IA (visual + áudio)
3. Identifica "momentos virais"
4. Gera clips verticais (9:16) com legendas dinâmicas

---

## 🏗️ Stack Tecnológica

| Camada | Tecnologia | Função |
|--------|-----------|--------|
| **Frontend** | Next.js 14 (App Router) | Interface web, SSR, API routes |
| **UI** | Tailwind CSS + shadcn/ui | Componentes e estilização |
| **State** | Zustand | Gerenciamento de estado |
| **Backend API** | FastAPI (Python 3.11) | REST API, autenticação, endpoints |
| **Task Queue** | Celery + Redis | Processamento assíncrono |
| **Database** | PostgreSQL 15 | Persistência de dados |
| **Cache/Broker** | Redis 7 | Message broker do Celery |
| **Transcrição** | Faster-Whisper (small) | Speech-to-text com timestamps |
| **Análise Visual** | Google Gemini API | Análise de frames com IA |
| **Processamento Vídeo** | FFmpeg | Corte, conversão, legendas |
| **Storage** | Local / Cloudflare R2 | Armazenamento de arquivos |
| **Auth** | JWT + OAuth2 (Google/GitHub) | Autenticação |
| **Payments** | Stripe | Assinaturas e planos |

---

## 🔄 Fluxo Completo de Processamento

### ETAPA 1: Upload do Vídeo

**Frontend** (`frontend/components/video-uploader.tsx`)

```
Usuário → Drag & Drop / Selecionar arquivo / Colar URL YouTube
         ↓
    uploadVideo() ou uploadVideoFromUrl()
         ↓
    POST /api/videos/upload (via proxy Next.js)
```

**Tipos de Upload:**
- **Arquivo direto**: Upload em chunks de 4MB (para arquivos >4MB)
- **URL YouTube**: Download via `yt-dlp` no backend

**Backend** (`backend/app/api/videos.py`)

```python
# Fluxo do endpoint /videos/upload:
1. Verifica limites de subscription (check_video_upload_allowed)
2. Valida arquivo (extensão: mp4, mov, avi, mkv, webm)
3. Gera UUID para video_id
4. Salva arquivo em storage_path/{video_id}/original.{ext}
5. Extrai metadados com FFmpeg (duração, resolução)
6. Se R2 configurado: faz upload para Cloudflare R2
7. Cria registro no PostgreSQL (tabela: videos)
8. Retorna: { video_id, status: "queued" }
```

**Download YouTube** (`yt-dlp`):
```python
ydl_opts = {
    "format": "best[ext=mp4]",
    "outtmpl": file_path,
    "quiet": True,
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
```

---

### ETAPA 2: Início do Processamento

**Frontend** (`frontend/app/videos/[id]/page.tsx`)

```
Usuário clica "Iniciar Processamento"
         ↓
    processVideo(videoId)
         ↓
    POST /api/videos/{video_id}/process
```

**Backend** (`backend/app/api/videos.py` → `backend/app/tasks/celery_tasks.py`)

```python
# Endpoint /videos/{video_id}/process:
1. Busca vídeo no banco
2. Valida status (não pode estar processando ou já completado)
3. Enfileira task no Celery:
   task = process_video_task.delay(video_id, params...)
4. Retorna: { job_id, video_id, status: "queued" }
```

**Celery Task** (`process_video_task`):
```python
# Configuração:
- task_time_limit: 3600s (1 hora máx)
- worker_concurrency: 1
- worker_prefetch_multiplier: 1
```

---

### ETAPA 3: Pipeline de Processamento (VideoProcessor)

**Serviço** (`backend/app/services/video_processor.py`)

O processamento é orquestrado pela classe `VideoProcessor` em 10 etapas:

#### **Step 1-2: Extração e Análise de Frames** (10% → 25%)

```python
# FFmpegService.extract_frames()
ffmpeg -i video.mp4 -vf "fps=0.1" frame_%04d.jpg
# fps=0.1 = 1 frame a cada 10 segundos

# GeminiService.batch_analyze_frames()
# Para cada frame, envia para Gemini API:
```

**Prompt do Gemini para análise de frame:**
```json
{
  "has_face": true/false,
  "face_count": 0-10,
  "face_position_x": 0-100,  // posição horizontal do rosto
  "expression": "neutral|excited|serious|laughing",
  "scene_type": "talking_head|presentation|action|other",
  "text_on_screen": true/false,
  "engagement_score": 0-10
}
```

#### **Step 3: Extração de Áudio** (40%)

```python
# FFmpegService.extract_audio()
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
# 16kHz mono - otimizado para Whisper
```

#### **Step 4: Transcrição com Whisper** (55%)

```python
# WhisperService.transcribe()
# Usa faster-whisper (model: "small", device: "cpu", compute_type: "int8")

segments, info = model.transcribe(audio_path, language="pt", word_timestamps=True)

# Retorna:
# - Segmentos com timestamps (start, end, text)
# - Word-level timestamps para legendas dinâmicas
```

#### **Step 5: Identificação de Momentos Virais** (70%)

```python
# GeminiService.identify_viral_moments()
```

**Prompt do Gemini:**
```
Analyze this transcript and identify TOP 5 most viral moments.

Look for:
- Questions that create curiosity
- Surprising revelations or facts
- Humorous moments
- Valuable insights/tips
- Compelling stories
- Emotional peaks
- Controversial statements

Return JSON with:
{
  "moments": [{
    "start_time": float,
    "end_time": float,
    "reason": "why this is viral",
    "keywords": ["key", "words"],
    "virality_score": 0-10,
    "hook_type": "question|revelation|humor|insight|story"
  }]
}
```

#### **Step 6: Seleção dos Melhores Segmentos** (75%)

```python
# VideoProcessor.select_best_segments()
1. Pega momentos virais como candidatos
2. Ajusta duração (min: 30s, max: 60s)
3. Ajusta para limites de frases (não cortar no meio)
4. Calcula score combinado:
   final_score = (visual_score * 0.3) + (audio_score * 0.3) + (moment_score * 0.4)
5. Filtra por min_virality_score (default: 5.0)
6. Retorna top 3 segmentos
```

#### **Step 7-10: Geração dos Clips** (75% → 100%)

Para cada segmento selecionado:

```python
# VideoProcessor.generate_clip()

# 1. Cortar segmento do vídeo original
ffmpeg -ss {start} -i video.mp4 -t {duration} -c copy temp_cut.mp4

# 2. Analisar faces no segmento (5 frames)
#    Determina posição do crop baseado na face
#    Se >70% frames tem 1 face: centraliza crop na face
#    Senão: crop centralizado

# 3. Converter para vertical (9:16)
ffmpeg -i temp_cut.mp4 \
  -vf "crop={width}:{height}:{x}:{y},scale=1080:1920" \
  -c:v libx264 -preset ultrafast -crf 26 \
  temp_vertical.mp4

# 4. Criar legendas dinâmicas (ASS format)
#    - Word-by-word (estilo TikTok)
#    - 2 palavras por grupo
#    - Keywords destacadas em amarelo

# 5. Adicionar legendas ao vídeo
ffmpeg -i temp_vertical.mp4 -vf "ass=subtitles.ass" final.mp4

# 6. Gerar thumbnail
ffmpeg -ss {middle} -i final.mp4 -vframes 1 thumb.jpg
```

---

### ETAPA 4: Persistência e Entrega

**Banco de Dados** (`backend/app/models.py`):

```sql
-- Tabela videos
id, user_id, filename, file_path, file_size, duration, 
status (queued|processing|completed|failed), progress, error_message,
created_at, updated_at

-- Tabela clips
id, video_id, start_time, end_time, duration, virality_score,
transcript, keywords (JSON), file_path, thumbnail_path, 
analysis_data (JSON), created_at
```

**Storage** (`backend/app/services/storage_service.py`):

```python
# Local: ./storage/videos/{video_id}/
# R2:    https://{bucket}.r2.dev/{video_id}/

# Arquivos por vídeo:
# - original.mp4
# - audio.wav
# - frames/frame_0001.jpg, ...
# - clips/{video_id}_clip_1_final.mp4
# - clips/{video_id}_clip_1_thumb.jpg
# - clips/{video_id}_clip_1_subs.ass
```

---

### ETAPA 5: Exibição dos Clips

**Frontend** (`frontend/app/videos/[id]/page.tsx`)

```
ProcessingStatus (polling /videos/{id}/status a cada 2s)
         ↓ (quando status === "completed")
    getVideoClips(videoId)
         ↓
    GET /api/videos/{video_id}/clips
         ↓
    Renderiza ClipCard para cada clip
```

**ClipCard** (`frontend/components/clip-card.tsx`):
- Thumbnail via `/api/clips/{clip_id}/thumbnail`
- Download via `/api/clips/{clip_id}/download`
- Badge com virality_score
- Preview de transcript
- Keywords como badges

---

## 🔐 Autenticação e Autorização

**Fluxo OAuth** (`backend/app/api/auth.py`):
```
1. Frontend redireciona para /api/auth/{provider} (google/github)
2. Backend gera URL de autorização do provider
3. Usuário autoriza no provider
4. Provider redireciona para /api/auth/callback
5. Backend troca code por token, obtém dados do usuário
6. Cria/atualiza User no banco
7. Gera JWT e redireciona para frontend com token
```

**JWT** (`backend/app/services/auth_service.py`):
```python
# Token gerado com:
- secret: JWT_SECRET (env)
- algorithm: HS256
- expires: 30 minutos
```

---

## 💰 Sistema de Planos

**Planos** (`backend/app/services/subscription_service.py`):

| Plano | Vídeos/mês | Clips/vídeo | Duração máx | Watermark | Fila prioritária |
|-------|-----------|-------------|-------------|-----------|------------------|
| Free | 3 | 3 | 10 min | Sim | Não |
| Starter | 10 | 10 | 30 min | Não | Não |
| Pro | 50 | ilimitado | 60 min | Não | Sim |

**Stripe Webhooks** (`backend/app/api/webhooks.py`):
- `checkout.session.completed` → Ativa subscription
- `invoice.paid` → Renova subscription
- `customer.subscription.deleted` → Cancela subscription

---

## 🐳 Infraestrutura Docker

**docker-compose.dev.yml** (desenvolvimento local):
```yaml
services:
  postgres    # PostgreSQL 15 (localhost:5432)
  redis       # Redis 7 (localhost:6379)
  api         # FastAPI (localhost:8000)
  worker      # Celery worker
  frontend    # Next.js (localhost:3000)
```

**Produção**:
- **Frontend**: Vercel (Next.js detectado automaticamente)
- **Backend API**: Railway (Dockerfile)
- **Worker**: Railway (Dockerfile.worker separado)
- **Database**: Railway PostgreSQL
- **Cache**: Railway Redis
- **Storage**: Cloudflare R2

---

## 📊 Métricas de Performance

```python
# Estimativa para vídeo de 10 minutos:
- Frames extraídos: ~60 (fps=0.1)
- Chamadas Gemini: ~60 (análise) + 1 (viral moments) + ~15 (crop analysis)
- Tempo Whisper: ~2-3 minutos (CPU)
- Tempo FFmpeg: ~5-10 minutos (encoding)
- Total: ~15-20 minutos de processamento
```

---

## 🔧 Variáveis de Ambiente Importantes

```bash
# Obrigatórias
GOOGLE_API_KEY=         # Gemini API
DATABASE_URL=           # PostgreSQL
REDIS_URL=              # Redis

# Modelos Gemini
GEMINI_MODEL_DEFAULT=gemini-2.5-flash
GEMINI_MODEL_STRICT=gemini-2.5-flash

# Whisper
WHISPER_MODEL=small     # tiny, base, small, medium, large-v3
WHISPER_DEVICE=cpu      # cpu ou cuda
WHISPER_COMPUTE_TYPE=int8

# FFmpeg
FFMPEG_PRESET=ultrafast # ultrafast → slow
FFMPEG_CRF=26           # 0-51 (menor = melhor qualidade)

# Processamento
FRAMES_PER_SECOND=0.1   # 1 frame a cada 10s
CLIP_MIN_DURATION=30
CLIP_MAX_DURATION=60
MIN_VIRALITY_SCORE=5.0
```

---

## 🚨 Limitações Conhecidas

1. **Rate Limit Gemini Free Tier**: 20 requests/minuto por modelo
   - Vídeos longos podem demorar muito ou falhar
   - Solução: Usar API key com billing ou vídeos curtos

2. **Whisper CPU**: Modelo "small" em CPU é lento
   - ~2-3 minutos para 10 min de áudio
   - Solução em prod: GPU ou serviço externo

3. **Storage Local**: Sem R2, arquivos ficam no container
   - Perdidos em restart/redeploy
   - Solução: Configurar Cloudflare R2

---

*Documento gerado automaticamente pela análise do código-fonte.*
