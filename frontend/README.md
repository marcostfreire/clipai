# ClipAI Frontend

Frontend moderno para o ClipAI - Gerador de Clips Virais com IA.

## 🚀 Tecnologias

- **Next.js 14** - Framework React com App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **shadcn/ui** - Componentes UI
- **Zustand** - State management
- **Axios** - HTTP client

## 📋 Pré-requisitos

- Node.js 18+
- Backend ClipAI rodando (ver `../backend/README.md`)

## 🛠️ Instalação e Execução

```powershell
# Instalar dependências
npm install

# Configurar variáveis de ambiente
cp .env.local .env.local
# Edite .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8000/api        # usado somente se o proxy for desativado
# NEXT_PUBLIC_USE_EDGE_PROXY=true                      # encaminha tudo via /api/proxy
# RUNPOD_DIRECT_API_URL=http://localhost:8000/api      # destino real do backend (localhost, direct.runpod, etc.)

# Executar desenvolvimento
npm run dev
```

Acesse: http://localhost:3000

## 📁 Estrutura

```
frontend/
├── app/                     # Pages (App Router)
│   ├── page.tsx            # Home
│   ├── videos/[id]/        # Processamento
│   └── clips/[id]/         # Player
├── components/             # Componentes
│   ├── ui/                 # shadcn/ui
│   ├── video-uploader.tsx
│   ├── processing-status.tsx
│   ├── clip-card.tsx
│   └── clip-player.tsx
└── lib/                    # API client e utils
```

## 🎯 Fluxo

1. **Home**: Upload de vídeo
2. **Processamento**: Status em tempo real
3. **Clips**: Grid com clips gerados
4. **Player**: Visualização individual

## 🔐 Proxy Anti-CORS

1. As chamadas do browser vão para `https://<frontend>/api/proxy/*`.
2. O handler em `app/api/proxy/[[...path]]/route.ts` reenvia para o valor de `RUNPOD_DIRECT_API_URL` e adiciona os headers `Access-Control-Allow-*`.
3. Para testar manualmente:
	 ```powershell
	 curl -X OPTIONS https://localhost:3000/api/proxy/health/cors ^
		 -H "Origin: https://frontend-xi-hazel-22.vercel.app" ^
		 -H "Access-Control-Request-Method: POST" -v
	 ```
4. Caso precise de um proxy 100% Cloudflare, use `frontend/workers/cloudflare-cors-proxy.js` e aponte `NEXT_PUBLIC_API_URL` para a URL do Worker.

## 🚀 Deploy

### Vercel
```powershell
npm install -g vercel
vercel
```

### Railway
```powershell
railway up
```

Configure as variáveis a seguir no provider (Vercel, Render, etc.):

- `NEXT_PUBLIC_USE_EDGE_PROXY=true`
- `RUNPOD_DIRECT_API_URL=https://<pod-id>-8000.direct.runpod.net/api`
- `NEXT_PUBLIC_API_URL` só é necessário se quiser ignorar o proxy (ex.: builds locais)

## 📝 Scripts

```powershell
npm run dev          # Desenvolvimento
npm run build        # Build produção
npm start            # Servidor produção
npm run lint         # ESLint
```
# Deployment trigger
