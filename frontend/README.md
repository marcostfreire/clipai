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
# Edite .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000/api

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

Configure `NEXT_PUBLIC_API_URL` nas variáveis de ambiente.

## 📝 Scripts

```powershell
npm run dev          # Desenvolvimento
npm run build        # Build produção
npm start            # Servidor produção
npm run lint         # ESLint
```
