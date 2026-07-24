FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

ARG VITE_PUBLIC_API_BASE
ARG VITE_SECURED_API_BASE
ARG VITE_KEYCLOAK_URL
ARG VITE_KEYCLOAK_REALM=basyx
ARG VITE_KEYCLOAK_CLIENT_ID=basyx-web
ARG VITE_AAS_ID=https://example.org/aas/schunk/pgn-plus-p-64-1
ARG VITE_TIMESERIES_ID=https://example.org/submodels/schunk/pgn-plus-p-64-1/timeseries
ARG VITE_POLL_INTERVAL_MS=2000
ARG VITE_REQUEST_TIMEOUT_MS=8000

ENV VITE_PUBLIC_API_BASE=$VITE_PUBLIC_API_BASE \
    VITE_SECURED_API_BASE=$VITE_SECURED_API_BASE \
    VITE_KEYCLOAK_URL=$VITE_KEYCLOAK_URL \
    VITE_KEYCLOAK_REALM=$VITE_KEYCLOAK_REALM \
    VITE_KEYCLOAK_CLIENT_ID=$VITE_KEYCLOAK_CLIENT_ID \
    VITE_AAS_ID=$VITE_AAS_ID \
    VITE_TIMESERIES_ID=$VITE_TIMESERIES_ID \
    VITE_POLL_INTERVAL_MS=$VITE_POLL_INTERVAL_MS \
    VITE_REQUEST_TIMEOUT_MS=$VITE_REQUEST_TIMEOUT_MS

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 443

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-check-certificate -q -O /dev/null https://127.0.0.1/health || exit 1
