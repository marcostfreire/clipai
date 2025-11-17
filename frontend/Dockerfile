# Multi-stage build for Next.js
FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set API URL from build args
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_USE_EDGE_PROXY
ARG RUNPOD_DIRECT_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_USE_EDGE_PROXY=${NEXT_PUBLIC_USE_EDGE_PROXY:-true}
ENV RUNPOD_DIRECT_API_URL=$RUNPOD_DIRECT_API_URL

# Build application
RUN npm run build

# Production image
FROM base AS runner
WORKDIR /app

ARG NEXT_PUBLIC_USE_EDGE_PROXY
ARG RUNPOD_DIRECT_API_URL
ENV NODE_ENV=production
ENV NEXT_PUBLIC_USE_EDGE_PROXY=${NEXT_PUBLIC_USE_EDGE_PROXY:-true}
ENV RUNPOD_DIRECT_API_URL=$RUNPOD_DIRECT_API_URL

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })"

CMD ["node", "server.js"]
