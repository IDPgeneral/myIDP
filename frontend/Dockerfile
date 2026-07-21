FROM node:24.14-bookworm-slim AS deps
ENV NPM_CONFIG_REGISTRY=https://registry.npmjs.org/ \
    NPM_CONFIG_REPLACE_REGISTRY_HOST=always
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:24.14-bookworm-slim AS builder
WORKDIR /app

ARG NEXT_PUBLIC_BACKEND_URL

ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL}

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24.14-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=10000 HOSTNAME=0.0.0.0 NEXT_TELEMETRY_DISABLED=1
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 10000
CMD ["node", "server.js"]
